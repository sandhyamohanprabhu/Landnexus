"""
SURVI / LANDNEXUS — Purpose-Aware Acquisition Privacy Guard Routes
RESTful endpoints for sensitive data detection, visibility evaluation, temporary access workflows,
privacy-safe PDF streaming, and authority governance.
"""

import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Header, HTTPException, Body, Query, Response
from backend.core import conn, current_user, audit, enforce_district_scope, check_resource_district
from backend.services.privacy_service import (
    detect_sensitive_entities,
    evaluate_document_privacy,
    calculate_privacy_risk_score,
    PURPOSES,
    CAT_CRITICAL,
    CAT_SENSITIVE,
    CAT_CONTROLLED,
    CAT_OPERATIONAL,
    VIS_VISIBLE,
    VIS_MASKED,
    VIS_REDACTED,
    VIS_AUTHORIZED
)
from backend.services.pdf_report import generate_privacy_safe_pdf
from backend.services.ocr_service import process_document_for_ocr

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# HELPER: FETCH ACTIVE TEMPORARY ACCESS GRANTS
# ═══════════════════════════════════════════════════════════════

def _get_active_grants(c, document_id: str, user_email: str) -> list:
    """Retrieve non-expired approved temporary access grants for user on document."""
    now_iso = datetime.now(timezone.utc).isoformat()
    # Mark expired grants
    c.execute(
        "UPDATE privacy_access_requests SET status='Expired' WHERE status='Approved' AND expires_at IS NOT NULL AND expires_at < ?",
        (now_iso,)
    )
    c.commit()

    rows = c.execute("""
        SELECT field_key, expires_at, purpose, reason FROM privacy_access_requests
        WHERE document_id=? AND lower(requested_by)=lower(?) AND status='Approved'
    """, (document_id, user_email)).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# 1. ANALYZE DOCUMENT PRIVACY
# ═══════════════════════════════════════════════════════════════

@router.post("/{document_id}/analyze")
def analyze_document_privacy(
    document_id: str,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    """
    Run sensitive data detection and privacy classification on a document.
    Saves detection records and privacy analysis scores to the database.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    c = conn()
    doc = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not doc:
        c.close()
        raise HTTPException(404, "Document not found")

    # Scoping check
    if doc["parcel_id"]:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (doc["parcel_id"],)).fetchone()
        if p:
            check_resource_district(u, p["district"], "Document Privacy Analysis")

    # Fetch OCR extractions
    extractions_rows = c.execute("SELECT field_name, value FROM ocr_extractions WHERE document_id=?", (document_id,)).fetchall()
    extractions = {r["field_name"]: r["value"] for r in extractions_rows}

    # Fetch raw text or run OCR if file exists on disk
    raw_text = ""
    file_path = doc["path"]
    if file_path and os.path.exists(file_path):
        ocr_res = process_document_for_ocr(file_path)
        if ocr_res.get("success"):
            raw_text = ocr_res.get("raw_text", "")
            extractions = ocr_res.get("extracted", {})
            for fk, fv in extractions.items():
                if fv:
                    c.execute(
                        "INSERT INTO ocr_extractions (document_id, field_name, value, confidence, validation_status) VALUES (?, ?, ?, ?, ?)",
                        (document_id, fk, str(fv), ocr_res.get("confidence", 0.9), "Pending")
                    )
            c.execute("UPDATE documents SET ocr_status='Verified' WHERE document_id=?", (document_id,))
            c.commit()

    combined_text = f"{raw_text} {doc['remarks'] or ''}".strip()
    if not combined_text:
        combined_text = f"Document {doc['document_name']} for parcel {doc['parcel_id']}"

    # Detect Sensitive Entities
    detections = detect_sensitive_entities(combined_text, extractions)

    # Calculate risk score
    risk_info = calculate_privacy_risk_score(detections)

    # Save to privacy_analyses
    c.execute("""
        INSERT OR REPLACE INTO privacy_analyses 
        (document_id, parcel_id, project_id, risk_score, risk_level, total_detected, critical_count, sensitive_count, controlled_count, operational_count, raw_summary, analyzed_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        document_id,
        doc["parcel_id"],
        doc["project_id"],
        risk_info["score"],
        risk_info["level"],
        len(detections),
        risk_info["counts"]["critical"],
        risk_info["counts"]["sensitive"],
        risk_info["counts"]["controlled"],
        risk_info["counts"]["operational"],
        f"Score {risk_info['score']}/100 ({risk_info['level']}): {risk_info['description']}",
        u["email"]
    ))

    # Save detections
    c.execute("DELETE FROM privacy_detections WHERE document_id=?", (document_id,))
    for d in detections:
        c.execute("""
            INSERT INTO privacy_detections 
            (document_id, field_key, field_label, detected_value_masked, detected_value_hash, category, default_visibility, confidence, detection_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            d["field_key"],
            d["field_label"],
            d["masked_value"],
            d["hash_ref"],
            d["category"],
            VIS_MASKED if d["category"] in (CAT_CRITICAL, CAT_SENSITIVE) else VIS_VISIBLE,
            d.get("confidence", 1.0),
            d.get("detection_method", "ocr")
        ))

    c.commit()

    # Log audit event without logging ANY sensitive raw values!
    audit(
        u["email"],
        "PRIVACY_ANALYZED",
        "documents",
        document_id,
        f"Risk Score={risk_info['score']} ({risk_info['level']}) | Sensitive Fields={risk_info['counts']['critical'] + risk_info['counts']['sensitive']}"
    )

    purpose = payload.get("purpose", "land_acquisition_processing")
    active_grants = _get_active_grants(c, document_id, u["email"])
    c.close()

    evaluation = evaluate_document_privacy(
        document_id=document_id,
        detections=detections,
        user_role=u["role"],
        user_email=u["email"],
        purpose=purpose,
        active_grants=active_grants
    )

    return evaluation


# ═══════════════════════════════════════════════════════════════
# 2. GET DOCUMENT PRIVACY EVALUATION
# ═══════════════════════════════════════════════════════════════

@router.get("/document/{document_id}")
def get_document_privacy(
    document_id: str,
    purpose: str = Query("land_acquisition_processing"),
    is_external: bool = Query(False),
    recipient_type: str = Query(None),
    authorization: str = Header(None)
):
    """
    Retrieve purpose-evaluated privacy details and field visibility for the current user.
    Server-side masking is strictly applied.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    c = conn()
    doc = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not doc:
        c.close()
        raise HTTPException(404, "Document not found")

    # Check resource scope
    if doc["parcel_id"]:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (doc["parcel_id"],)).fetchone()
        if p:
            check_resource_district(u, p["district"], "Document Privacy")

    # Check if analysis already exists
    detections_rows = c.execute("SELECT * FROM privacy_detections WHERE document_id=?", (document_id,)).fetchall()
    
    extractions_rows = c.execute("SELECT field_name, value FROM ocr_extractions WHERE document_id=?", (document_id,)).fetchall()
    extractions = {r["field_name"]: r["value"] for r in extractions_rows}

    if not detections_rows:
        # Run detection on the fly
        raw_text = doc["remarks"] or f"Document {doc['document_name']} for parcel {doc['parcel_id']}"
        detections = detect_sensitive_entities(raw_text, extractions)
    else:
        detections = []
        for r in detections_rows:
            f_key = r["field_key"]
            raw_val = extractions.get(f_key, r["detected_value_masked"])
            detections.append({
                "field_key": r["field_key"],
                "field_label": r["field_label"],
                "category": r["category"],
                "raw_detected": raw_val,
                "masked_value": r["detected_value_masked"],
                "hash_ref": r["detected_value_hash"],
                "confidence": r["confidence"],
                "detection_method": r["detection_method"]
            })

    active_grants = _get_active_grants(c, document_id, u["email"])
    c.close()

    evaluation = evaluate_document_privacy(
        document_id=document_id,
        detections=detections,
        user_role=u["role"],
        user_email=u["email"],
        purpose=purpose,
        active_grants=active_grants,
        is_external=is_external,
        recipient_type=recipient_type
    )

    return evaluation


# ═══════════════════════════════════════════════════════════════
# 3. REQUEST TEMPORARY ACCESS
# ═══════════════════════════════════════════════════════════════

@router.post("/access-request")
def create_access_request(
    payload: dict = Body(...),
    authorization: str = Header(None)
):
    """
    Request temporary access to a masked sensitive field for a legitimate operational purpose.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    document_id = payload.get("document_id")
    field_key = payload.get("field_key")
    purpose = payload.get("purpose", "land_acquisition_processing")
    reason = payload.get("reason", "").strip()
    duration_hours = int(payload.get("duration_hours", 24))

    if not document_id or not field_key:
        raise HTTPException(400, "document_id and field_key are required")
    if not reason:
        raise HTTPException(400, "A valid justification reason is required for temporary access")

    c = conn()
    doc = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not doc:
        c.close()
        raise HTTPException(404, "Document not found")

    # Check if a pending request already exists for this field
    existing = c.execute("""
        SELECT id FROM privacy_access_requests 
        WHERE document_id=? AND field_key=? AND lower(requested_by)=lower(?) AND status='Pending'
    """, (document_id, field_key, u["email"])).fetchone()
    if existing:
        c.close()
        return {"success": True, "request_id": existing["id"], "status": "Pending", "message": "Access request is already pending review"}

    c.execute("""
        INSERT INTO privacy_access_requests 
        (document_id, parcel_id, project_id, field_key, requested_by, requested_role, purpose, reason, duration_hours, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (
        document_id,
        doc["parcel_id"],
        doc["project_id"],
        field_key,
        u["email"],
        u["role"],
        purpose,
        reason,
        duration_hours
    ))
    request_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()

    # Audit log (no raw PII!)
    audit(
        u["email"],
        "ACCESS_REQUESTED",
        "privacy_access_requests",
        str(request_id),
        f"Document={document_id} | Field={field_key} | Purpose={purpose} | Duration={duration_hours}h"
    )

    return {
        "success": True,
        "request_id": request_id,
        "status": "Pending",
        "message": "Temporary access request submitted for District Authority review"
    }


# ═══════════════════════════════════════════════════════════════
# 4. LIST ACCESS REQUESTS
# ═══════════════════════════════════════════════════════════════

@router.get("/access-requests")
def list_access_requests(
    status: str = Query(None),
    document_id: str = Query(None),
    district: str = Query(None),
    authorization: str = Header(None)
):
    """
    List access requests with filtering. Authorities can view and act on pending requests.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    c = conn()
    
    # Refresh expired requests
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute(
        "UPDATE privacy_access_requests SET status='Expired' WHERE status='Approved' AND expires_at IS NOT NULL AND expires_at < ?",
        (now_iso,)
    )
    c.commit()

    query = """
        SELECT r.*, d.document_name, p.survey_no, p.village, p.district 
        FROM privacy_access_requests r
        LEFT JOIN documents d ON r.document_id = d.document_id
        LEFT JOIN parcels p ON r.parcel_id = p.id
        WHERE 1=1
    """
    params = []

    # Role-based visibility
    if u["role"] not in ("authority", "national_authority", "admin", "state_authority", "district_authority"):
        query += " AND lower(r.requested_by) = lower(?)"
        params.append(u["email"])
    elif u.get("district_scope"):
        query += " AND (lower(p.district) = lower(?) OR p.district IS NULL)"
        params.append(u["district_scope"])

    if status and status.lower() != "all":
        query += " AND r.status = ?"
        params.append(status.title())

    if document_id:
        query += " AND r.document_id = ?"
        params.append(document_id)

    query += " ORDER BY r.id DESC LIMIT 200"

    rows = [dict(r) for r in c.execute(query, tuple(params)).fetchall()]
    c.close()
    return rows


# ═══════════════════════════════════════════════════════════════
# 5. APPROVE ACCESS REQUEST
# ═══════════════════════════════════════════════════════════════

@router.post("/access-request/{request_id}/approve")
def approve_access_request(
    request_id: int,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    """
    Approve temporary access request. Grants time-bound access.
    """
    u = current_user(authorization)
    if not u or u["role"] not in ("authority", "national_authority", "admin", "state_authority", "district_authority"):
        raise HTTPException(403, "Authority or Admin role required to approve access requests")

    c = conn()
    req = c.execute("SELECT * FROM privacy_access_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        c.close()
        raise HTTPException(404, "Access request not found")

    duration_hours = int(payload.get("duration_hours") or req["duration_hours"] or 24)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=duration_hours)).isoformat()
    now_iso = now.isoformat()

    c.execute("""
        UPDATE privacy_access_requests 
        SET status='Approved', reviewed_by=?, reviewed_at=?, expires_at=?, duration_hours=?
        WHERE id=?
    """, (u["email"], now_iso, expires_at, duration_hours, request_id))
    c.commit()
    c.close()

    # Audit log (no raw PII!)
    audit(
        u["email"],
        "ACCESS_APPROVED",
        "privacy_access_requests",
        str(request_id),
        f"Grantee={req['requested_by']} | Field={req['field_key']} | Duration={duration_hours}h | Expires={expires_at}"
    )

    return {
        "success": True,
        "request_id": request_id,
        "status": "Approved",
        "expires_at": expires_at,
        "message": f"Temporary access granted for {duration_hours} hours"
    }


# ═══════════════════════════════════════════════════════════════
# 6. REJECT ACCESS REQUEST
# ═══════════════════════════════════════════════════════════════

@router.post("/access-request/{request_id}/reject")
def reject_access_request(
    request_id: int,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    """
    Reject temporary access request with a reason.
    """
    u = current_user(authorization)
    if not u or u["role"] not in ("authority", "national_authority", "admin", "state_authority", "district_authority"):
        raise HTTPException(403, "Authority or Admin role required to reject access requests")

    reason = payload.get("reason", "Access denied under data minimisation policy").strip()
    c = conn()
    req = c.execute("SELECT * FROM privacy_access_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        c.close()
        raise HTTPException(404, "Access request not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
        UPDATE privacy_access_requests 
        SET status='Rejected', reviewed_by=?, reviewed_at=?, rejection_reason=?
        WHERE id=?
    """, (u["email"], now_iso, reason, request_id))
    c.commit()
    c.close()

    audit(
        u["email"],
        "ACCESS_REJECTED",
        "privacy_access_requests",
        str(request_id),
        f"Grantee={req['requested_by']} | Field={req['field_key']} | Reason={reason}"
    )

    return {
        "success": True,
        "request_id": request_id,
        "status": "Rejected",
        "message": "Access request rejected"
    }


# ═══════════════════════════════════════════════════════════════
# 7. GENERATE PRIVACY-SAFE PDF
# ═══════════════════════════════════════════════════════════════

@router.post("/{document_id}/safe-pdf")
@router.get("/{document_id}/safe-pdf")
def download_privacy_safe_pdf(
    document_id: str,
    purpose: str = Query("land_acquisition_processing"),
    is_external: bool = Query(False),
    recipient_type: str = Query(None),
    authorization: str = Header(None)
):
    """
    Generate and stream a formal Government-style Privacy-Safe PDF with masked sensitive fields
    and full privacy processing audit summary.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    c = conn()
    doc = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not doc:
        c.close()
        raise HTTPException(404, "Document not found")

    parcel_id = doc["parcel_id"]
    parcel_info = {}
    if parcel_id:
        p = c.execute("SELECT * FROM parcels WHERE id=?", (parcel_id,)).fetchone()
        if p:
            parcel_info = dict(p)
            check_resource_district(u, p["district"], "Privacy PDF")

    # Fetch extractions & detections
    extractions_rows = c.execute("SELECT field_name, value FROM ocr_extractions WHERE document_id=?", (document_id,)).fetchall()
    extractions = {r["field_name"]: r["value"] for r in extractions_rows}

    detections_rows = c.execute("SELECT * FROM privacy_detections WHERE document_id=?", (document_id,)).fetchall()
    if not detections_rows:
        raw_text = doc["remarks"] or f"Document {doc['document_name']} for parcel {doc['parcel_id']}"
        detections = detect_sensitive_entities(raw_text, extractions)
    else:
        detections = []
        for r in detections_rows:
            f_key = r["field_key"]
            raw_val = extractions.get(f_key, r["detected_value_masked"])
            detections.append({
                "field_key": r["field_key"],
                "field_label": r["field_label"],
                "category": r["category"],
                "raw_detected": raw_val,
                "masked_value": r["detected_value_masked"],
                "hash_ref": r["detected_value_hash"],
                "confidence": r["confidence"],
                "detection_method": r["detection_method"]
            })

    active_grants = _get_active_grants(c, document_id, u["email"])
    c.close()

    evaluation = evaluate_document_privacy(
        document_id=document_id,
        detections=detections,
        user_role=u["role"],
        user_email=u["email"],
        purpose=purpose,
        active_grants=active_grants,
        is_external=is_external,
        recipient_type=recipient_type
    )

    doc_metadata = {
        "document_id": document_id,
        "document_name": doc["document_name"],
        "project_id": doc["project_id"] or parcel_info.get("project_id", "N/A"),
        "parcel_id": doc["parcel_id"] or parcel_info.get("id", "N/A"),
        "survey_no": parcel_info.get("survey_no", extractions.get("survey_number", "N/A")),
        "village": parcel_info.get("village", extractions.get("village", "N/A")),
        "taluk": parcel_info.get("taluk", extractions.get("taluk", "N/A")),
        "district": parcel_info.get("district", extractions.get("district", "N/A")),
        "document_date": extractions.get("document_date", datetime.now().strftime("%Y-%m-%d"))
    }

    try:
        pdf_bytes = generate_privacy_safe_pdf(
            doc_info=doc_metadata,
            privacy_eval=evaluation,
            purpose=purpose,
            user_info=u
        )
    except Exception as e:
        raise HTTPException(500, f"Privacy PDF generation failed: {str(e)}")

    # Audit log (no raw PII!)
    audit(
        u["email"],
        "SAFE_PDF_GENERATED",
        "documents",
        document_id,
        f"Purpose={purpose} | External={is_external} | MaskedCount={evaluation['summary']['masked']}"
    )

    safe_filename = f"PrivacySafe_Doc_{document_id[:8]}_{purpose}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


# ═══════════════════════════════════════════════════════════════
# 8. PRIVACY GOVERNANCE & METRICS
# ═══════════════════════════════════════════════════════════════

@router.get("/governance")
def get_privacy_governance_metrics(
    district: str = Query(None),
    authorization: str = Header(None)
):
    """
    Returns platform-wide privacy governance metrics for Authority Command Centers.
    All numbers are computed live from the actual database without fabrication.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    district = enforce_district_scope(u, district)
    c = conn()

    # Expire old grants
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute(
        "UPDATE privacy_access_requests SET status='Expired' WHERE status='Approved' AND expires_at IS NOT NULL AND expires_at < ?",
        (now_iso,)
    )
    c.commit()

    # Documents analyzed count
    docs_analyzed = c.execute("SELECT COUNT(*) as cnt FROM privacy_analyses").fetchone()["cnt"]

    # Sensitive fields detected
    sens_detected = c.execute("""
        SELECT COUNT(*) as cnt FROM privacy_detections 
        WHERE category IN ('CRITICAL', 'SENSITIVE')
    """).fetchone()["cnt"]

    # Fields automatically masked
    auto_masked = c.execute("""
        SELECT COUNT(*) as cnt FROM privacy_detections 
        WHERE default_visibility = 'MASKED'
    """).fetchone()["cnt"]

    # Safe PDFs generated (from audit ledger)
    safe_pdfs = c.execute("""
        SELECT COUNT(*) as cnt FROM audit WHERE action = 'SAFE_PDF_GENERATED'
    """).fetchone()["cnt"]

    # Access request breakdown
    pending_reqs = c.execute("SELECT COUNT(*) as cnt FROM privacy_access_requests WHERE status='Pending'").fetchone()["cnt"]
    approved_reqs = c.execute("SELECT COUNT(*) as cnt FROM privacy_access_requests WHERE status='Approved'").fetchone()["cnt"]
    rejected_reqs = c.execute("SELECT COUNT(*) as cnt FROM privacy_access_requests WHERE status='Rejected'").fetchone()["cnt"]
    expired_reqs = c.execute("SELECT COUNT(*) as cnt FROM privacy_access_requests WHERE status='Expired'").fetchone()["cnt"]

    # Recent access requests
    recent_reqs = c.execute("""
        SELECT r.*, d.document_name, p.survey_no, p.village, p.district
        FROM privacy_access_requests r
        LEFT JOIN documents d ON r.document_id = d.document_id
        LEFT JOIN parcels p ON r.parcel_id = p.id
        ORDER BY r.id DESC LIMIT 15
    """).fetchall()

    # Recent privacy audit events
    recent_audits = c.execute("""
        SELECT * FROM audit 
        WHERE action IN ('PRIVACY_ANALYZED', 'SAFE_PDF_GENERATED', 'ACCESS_REQUESTED', 'ACCESS_APPROVED', 'ACCESS_REJECTED')
        ORDER BY id DESC LIMIT 20
    """).fetchall()

    c.close()

    return {
        "metrics": {
            "documents_analyzed": docs_analyzed,
            "sensitive_fields_detected": sens_detected,
            "fields_automatically_masked": auto_masked,
            "privacy_safe_pdfs_generated": safe_pdfs,
            "pending_access_requests": pending_reqs,
            "approved_access_requests": approved_reqs,
            "rejected_access_requests": rejected_reqs,
            "expired_access_requests": expired_reqs
        },
        "recent_requests": [dict(r) for r in recent_reqs],
        "recent_audits": [dict(r) for r in recent_audits],
        "policy_info": {
            "framework": "Tamil Nadu Purpose-Aware Land Acquisition Privacy Guard",
            "version": "v2.0-TN-GOV-PRIVACY-GUARD",
            "status": "Active & Enforced",
            "principle": "Purpose-Based Data Minimisation & Controlled Disclosure"
        }
    }


# ═══════════════════════════════════════════════════════════════
# 9. PRIVACY AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════

@router.get("/audit")
def get_privacy_audit_trail(
    limit: int = Query(100),
    authorization: str = Header(None)
):
    """
    Retrieve privacy audit trail without raw PII.
    """
    u = current_user(authorization)
    if not u or u["role"] not in ("authority", "national_authority", "admin", "state_authority", "district_authority"):
        raise HTTPException(403, "Authority access required to view privacy audit ledger")

    c = conn()
    rows = c.execute("""
        SELECT * FROM audit 
        WHERE action IN ('PRIVACY_ANALYZED', 'SAFE_PDF_GENERATED', 'ACCESS_REQUESTED', 'ACCESS_APPROVED', 'ACCESS_REJECTED', 'FIELD_MASKED', 'FIELD_REDACTED')
        ORDER BY id DESC LIMIT ?
    """, (min(limit, 500),)).fetchall()
    c.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# 10. OPERATIONAL PURPOSES LIST
# ═══════════════════════════════════════════════════════════════

@router.get("/purposes")
def get_purposes():
    """Return standard operational purposes list."""
    return PURPOSES
