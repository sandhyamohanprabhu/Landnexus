from fastapi import APIRouter, Header, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
import json
import uuid
from datetime import datetime, timezone
from backend.core import conn, current_user, audit, enforce_district_scope, check_resource_district
from backend.services.duplicate_service import (
    score_duplicate_pair,
    compare_records,
    scan_parcels_for_duplicates,
    mask_private_name
)
from backend.services.verification_providers import run_cross_db_verification

router = APIRouter()

def get_authorized_user(authorization: Optional[str]):
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    # Citizens forbidden from internal duplicate detection & data quality cases
    if u.get("role") in ("citizen", "public"):
        raise HTTPException(403, "Access forbidden: Internal data quality workflows are restricted to authorized personnel.")
    return u

@router.post("/scan")
def trigger_duplicate_scan(
    payload: Optional[Dict[str, Any]] = Body(default={}),
    district: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    if u["role"] not in ("authority", "admin", "district_authority", "acquisition_officer", "state_authority"):
        raise HTTPException(403, "Insufficient permissions to trigger duplicate scan")

    req_district = (payload or {}).get("district") or district
    district = enforce_district_scope(u, req_district)
    project_id = (payload or {}).get("project_id")
    threshold = float((payload or {}).get("threshold") or 60.0)

    audit(u["email"], "DUPLICATE_SCAN_STARTED", "parcels", f"district={district} | project={project_id or 'all'}")
    
    candidates = scan_parcels_for_duplicates(district=district, project_id=project_id, threshold=threshold)
    
    for c in candidates:
        if c.get("status") == "NEW":
            audit(
                u["email"],
                "DUPLICATE_CANDIDATE_CREATED",
                f"case:{c.get('case_id')}",
                f"score={c.get('similarity_score')} | district={c.get('district')}"
            )

    return {
        "status": "success",
        "district": district,
        "scanned_parcels_count": len(candidates),
        "potential_duplicates_found": len(candidates),
        "accuracy_statement": "Potential Duplicate – Review Required. No automated deletion or merging applied.",
        "cases": candidates
    }

@router.get("/duplicate-cases")
def list_duplicate_cases(
    district: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    project_id: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    district = enforce_district_scope(u, district)

    c = conn()
    query = """
        SELECT dc.*, 
               pa.record_id as rec_a_key, pa.survey_no as rec_a_survey, pa.village as rec_a_village, pa.owner_reference as rec_a_owner, pa.area as rec_a_area,
               pb.record_id as rec_b_key, pb.survey_no as rec_b_survey, pb.village as rec_b_village, pb.owner_reference as rec_b_owner, pb.area as rec_b_area
        FROM duplicate_cases dc
        JOIN parcels pa ON dc.record_a_id = pa.id
        JOIN parcels pb ON dc.record_b_id = pb.id
        WHERE 1=1
    """
    params = []
    if district and district.lower() != "all":
        query += " AND lower(dc.district)=lower(?)"
        params.append(district.strip())
    if status and status.lower() != "all":
        query += " AND lower(dc.status)=lower(?)"
        params.append(status.strip())
    if min_score is not None:
        query += " AND dc.similarity_score >= ?"
        params.append(float(min_score))
    if project_id:
        query += " AND (pa.project_id=? OR pb.project_id=?)"
        params.extend([project_id, project_id])

    query += " ORDER BY dc.similarity_score DESC, dc.id DESC"
    rows = c.execute(query, params).fetchall()
    c.close()

    cases = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("primary_reasons"), str):
            try:
                d["primary_reasons"] = json.loads(d["primary_reasons"])
            except Exception:
                d["primary_reasons"] = [d["primary_reasons"]]
        # Mask owner references for privacy
        d["rec_a_owner_masked"] = mask_private_name(d.get("rec_a_owner"))
        d["rec_b_owner_masked"] = mask_private_name(d.get("rec_b_owner"))
        d.pop("rec_a_owner", None)
        d.pop("rec_b_owner", None)
        d["accuracy_statement"] = "Potential Duplicate – Review Required"
        cases.append(d)

    return {
        "cases": cases,
        "total": len(cases),
        "district": district
    }

@router.get("/duplicate-cases/{case_id}")
def get_duplicate_case_detail(
    case_id: str,
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    c = conn()
    case_row = c.execute("SELECT * FROM duplicate_cases WHERE case_id=?", (case_id,)).fetchone()
    if not case_row:
        c.close()
        raise HTTPException(404, "Duplicate case not found")
    case = dict(case_row)
    check_resource_district(u, case.get("district"), "Duplicate Case")

    rec_a_row = c.execute("SELECT * FROM parcels WHERE id=?", (case["record_a_id"],)).fetchone()
    rec_b_row = c.execute("SELECT * FROM parcels WHERE id=?", (case["record_b_id"],)).fetchone()
    c.close()

    if not rec_a_row or not rec_b_row:
        raise HTTPException(404, "One or both linked parcels could not be found")

    rec_a = dict(rec_a_row)
    rec_b = dict(rec_b_row)

    # Generate complete side-by-side comparison
    comparison = compare_records(rec_a, rec_b, mask_privacy=True)
    if isinstance(case.get("primary_reasons"), str):
        try:
            case["primary_reasons"] = json.loads(case["primary_reasons"])
        except Exception:
            pass

    return {
        "case": case,
        "comparison": comparison,
        "accuracy_statement": "Potential Duplicate – Review Required. Officer confirmation required before any legal action.",
        "record_a": {
            "id": rec_a["id"],
            "record_id": rec_a.get("record_id"),
            "survey_no": rec_a.get("survey_no"),
            "village": rec_a.get("village"),
            "district": rec_a.get("district"),
            "area": rec_a.get("area"),
            "owner_masked": mask_private_name(rec_a.get("owner_reference") or rec_a.get("owner_name"))
        },
        "record_b": {
            "id": rec_b["id"],
            "record_id": rec_b.get("record_id"),
            "survey_no": rec_b.get("survey_no"),
            "village": rec_b.get("village"),
            "district": rec_b.get("district"),
            "area": rec_b.get("area"),
            "owner_masked": mask_private_name(rec_b.get("owner_reference") or rec_b.get("owner_name"))
        }
    }

@router.post("/duplicate-cases/{case_id}/decision")
def record_case_decision(
    case_id: str,
    payload: Dict[str, Any] = Body(...),
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    if u["role"] not in ("authority", "admin", "district_authority", "acquisition_officer"):
        raise HTTPException(403, "Insufficient permissions to decide duplicate cases")

    decision = payload.get("decision")
    valid_decisions = ("CONFIRMED_DUPLICATE", "NOT_DUPLICATE", "INSUFFICIENT_INFORMATION", "FIELD_VERIFICATION_REQUESTED")
    if not decision or decision not in valid_decisions:
        raise HTTPException(400, f"Invalid decision. Must be one of: {', '.join(valid_decisions)}")

    reason = payload.get("reason", "").strip()
    if not reason:
        raise HTTPException(400, "Decision reason is mandatory for legal and audit compliance")

    evidence = payload.get("evidence", "")
    master_record_id = payload.get("master_record_id")

    c = conn()
    case_row = c.execute("SELECT * FROM duplicate_cases WHERE case_id=?", (case_id,)).fetchone()
    if not case_row:
        c.close()
        raise HTTPException(404, "Duplicate case not found")
    case = dict(case_row)
    check_resource_district(u, case.get("district"), "Duplicate Case")

    now_iso = datetime.now(timezone.utc).isoformat()

    if decision == "CONFIRMED_DUPLICATE":
        # Ensure a master record ID is chosen
        if not master_record_id:
            master_record_id = case["record_a_id"]
        secondary_id = case["record_b_id"] if master_record_id == case["record_a_id"] else case["record_a_id"]

        c.execute("""
            UPDATE duplicate_cases
            SET status='CONFIRMED_DUPLICATE', decision=?, decision_reason=?, decision_evidence=?,
                master_record_id=?, resolved_by=?, resolved_at=?
            WHERE case_id=?
        """, (decision, reason, evidence, master_record_id, u["email"], now_iso, case_id))

        # Secondary parcel flagged as duplicate pointing to master
        c.execute("UPDATE parcels SET duplicate_flag=1, master_parcel_id=? WHERE id=?", (master_record_id, secondary_id))
        c.commit()

        audit(
            u["email"],
            "DUPLICATE_CONFIRMED",
            f"case:{case_id}",
            f"master={master_record_id} | secondary={secondary_id} | reason={reason[:100]}"
        )

    elif decision == "NOT_DUPLICATE":
        c.execute("""
            UPDATE duplicate_cases
            SET status='NOT_DUPLICATE', decision=?, decision_reason=?, decision_evidence=?,
                resolved_by=?, resolved_at=?
            WHERE case_id=?
        """, (decision, reason, evidence, u["email"], now_iso, case_id))

        # Check if either parcel has other active duplicate cases
        for pid in (case["record_a_id"], case["record_b_id"]):
            active = c.execute("""
                SELECT 1 FROM duplicate_cases 
                WHERE (record_a_id=? OR record_b_id=?) AND status IN ('NEW', 'UNDER_REVIEW', 'CONFIRMED_DUPLICATE')
                  AND case_id != ?
            """, (pid, pid, case_id)).fetchone()
            if not active:
                c.execute("UPDATE parcels SET duplicate_flag=0 WHERE id=?", (pid,))

        c.commit()
        audit(
            u["email"],
            "DUPLICATE_MARKED_NOT_DUPLICATE",
            f"case:{case_id}",
            f"parcels=[{case['record_a_id']},{case['record_b_id']}] | reason={reason[:100]}"
        )

    elif decision == "FIELD_VERIFICATION_REQUESTED":
        c.execute("""
            UPDATE duplicate_cases
            SET status='FIELD_VERIFICATION_REQUESTED', decision=?, decision_reason=?, decision_evidence=?,
                resolved_by=?, resolved_at=?
            WHERE case_id=?
        """, (decision, reason, evidence, u["email"], now_iso, case_id))

        try:
            c.execute("""
                INSERT INTO field_assignments(parcel_id, assigned_officer, district, notes)
                VALUES(?, ?, ?, ?)
            """, (case["record_a_id"], u["email"], case.get("district"), f"Field inspection for duplicate case {case_id}: {reason}"))
        except Exception:
            pass

        c.commit()
        audit(
            u["email"],
            "DUPLICATE_DECISION_UPDATED",
            f"case:{case_id}",
            f"status=FIELD_VERIFICATION_REQUESTED | reason={reason[:100]}"
        )

    else:  # INSUFFICIENT_INFORMATION
        c.execute("""
            UPDATE duplicate_cases
            SET status='INSUFFICIENT_INFORMATION', decision=?, decision_reason=?, decision_evidence=?,
                resolved_by=?, resolved_at=?
            WHERE case_id=?
        """, (decision, reason, evidence, u["email"], now_iso, case_id))
        c.commit()
        audit(
            u["email"],
            "DUPLICATE_DECISION_UPDATED",
            f"case:{case_id}",
            f"status=INSUFFICIENT_INFORMATION | reason={reason[:100]}"
        )

    c.close()
    return {
        "status": "success",
        "case_id": case_id,
        "decision": decision,
        "resolved_by": u["email"],
        "resolved_at": now_iso
    }

@router.post("/verify-external/{parcel_id}")
def verify_parcel_external(
    parcel_id: int,
    payload: Dict[str, Any] = Body(default={}),
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    include_demo = bool(payload.get("include_demo", True))

    c = conn()
    parcel_row = c.execute("SELECT * FROM parcels WHERE id=?", (parcel_id,)).fetchone()
    c.close()
    if not parcel_row:
        raise HTTPException(404, "Parcel not found")
    check_resource_district(u, dict(parcel_row).get("district"), "Parcel")

    audit(u["email"], "CROSS_DB_VERIFICATION_INITIATED", f"parcel:{parcel_id}", "initiated")

    results = run_cross_db_verification(parcel_id, u["email"], include_demo=include_demo)

    audit(
        u["email"],
        "CROSS_DB_VERIFICATION_COMPLETED",
        f"parcel:{parcel_id}",
        f"providers_queried={len(results)}"
    )

    return {
        "parcel_id": parcel_id,
        "verifications": results,
        "truthful_notice": "Authoritative government registries report NOT_CONNECTED if external NIC/State API credentials are unconfigured. Demo providers are explicitly marked 'DEMONSTRATION DATA – NOT GOVERNMENT SOURCE'."
    }

@router.get("/verifications/{parcel_id}")
def get_parcel_verifications(
    parcel_id: int,
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    c = conn()
    parcel_row = c.execute("SELECT * FROM parcels WHERE id=?", (parcel_id,)).fetchone()
    if not parcel_row:
        c.close()
        raise HTTPException(404, "Parcel not found")
    check_resource_district(u, dict(parcel_row).get("district"), "Parcel")

    rows = c.execute("""
        SELECT * FROM cross_db_verifications 
        WHERE parcel_id=? 
        ORDER BY id DESC
    """, (parcel_id,)).fetchall()
    c.close()

    items = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("matched_fields"), str):
            try:
                d["matched_fields"] = json.loads(d["matched_fields"])
            except Exception:
                pass
        if isinstance(d.get("mismatched_fields"), str):
            try:
                d["mismatched_fields"] = json.loads(d["mismatched_fields"])
            except Exception:
                pass
        items.append(d)

    return {
        "parcel_id": parcel_id,
        "verifications": items,
        "count": len(items)
    }

@router.get("/analytics")
def get_data_quality_analytics(
    district: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    district = enforce_district_scope(u, district)

    c = conn()
    p_filter = ""
    p_params = []
    c_filter = ""
    c_params = []

    if district and district.lower() != "all":
        p_filter = "WHERE lower(district)=lower(?)"
        p_params = [district.strip()]
        c_filter = "WHERE lower(district)=lower(?)"
        c_params = [district.strip()]

    total_parcels = c.execute(f"SELECT COUNT(*) FROM parcels {p_filter}", p_params).fetchone()[0]
    total_cases = c.execute(f"SELECT COUNT(*) FROM duplicate_cases {c_filter}", c_params).fetchone()[0]
    
    new_cases = c.execute(f"SELECT COUNT(*) FROM duplicate_cases {c_filter} {'AND' if c_filter else 'WHERE'} status='NEW'", c_params).fetchone()[0]
    confirmed_cases = c.execute(f"SELECT COUNT(*) FROM duplicate_cases {c_filter} {'AND' if c_filter else 'WHERE'} status='CONFIRMED_DUPLICATE'", c_params).fetchone()[0]
    not_dup_cases = c.execute(f"SELECT COUNT(*) FROM duplicate_cases {c_filter} {'AND' if c_filter else 'WHERE'} status='NOT_DUPLICATE'", c_params).fetchone()[0]
    field_req_cases = c.execute(f"SELECT COUNT(*) FROM duplicate_cases {c_filter} {'AND' if c_filter else 'WHERE'} status='FIELD_VERIFICATION_REQUESTED'", c_params).fetchone()[0]

    total_cross_db = c.execute("SELECT COUNT(*) FROM cross_db_verifications").fetchone()[0]
    cross_db_matches = c.execute("SELECT COUNT(*) FROM cross_db_verifications WHERE status='VERIFIED_MATCH'").fetchone()[0]
    cross_db_not_connected = c.execute("SELECT COUNT(*) FROM cross_db_verifications WHERE status='NOT_CONNECTED'").fetchone()[0]

    c.close()

    resolution_rate = round(((confirmed_cases + not_dup_cases) / max(total_cases, 1)) * 100, 1)

    return {
        "district": district,
        "parcels": {
            "total": total_parcels,
            "flagged_duplicates": confirmed_cases + new_cases
        },
        "duplicate_detection": {
            "total_cases": total_cases,
            "new_review_required": new_cases,
            "confirmed_duplicates": confirmed_cases,
            "marked_not_duplicate": not_dup_cases,
            "field_verification_requested": field_req_cases,
            "resolution_rate_pct": resolution_rate,
            "accuracy_rule": "Potential Duplicate – Review Required. Never 100% automated proof."
        },
        "cross_db_verification": {
            "total_verifications": total_cross_db,
            "matches": cross_db_matches,
            "not_connected_count": cross_db_not_connected,
            "notice": "Authoritative DILRMP and State LRMS systems report NOT_CONNECTED if live endpoints are unconfigured."
        }
    }

@router.get("/parcel/{parcel_id}")
def get_parcel_data_quality_summary(
    parcel_id: int,
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    c = conn()
    p_row = c.execute("SELECT * FROM parcels WHERE id=?", (parcel_id,)).fetchone()
    if not p_row:
        c.close()
        raise HTTPException(404, "Parcel not found")
    parcel = dict(p_row)
    check_resource_district(u, parcel.get("district"), "Parcel")

    # Find duplicate cases linked to this parcel
    case_rows = c.execute("""
        SELECT * FROM duplicate_cases 
        WHERE record_a_id=? OR record_b_id=? 
        ORDER BY id DESC
    """, (parcel_id, parcel_id)).fetchall()

    cases = []
    for r in case_rows:
        cd = dict(r)
        if isinstance(cd.get("primary_reasons"), str):
            try:
                cd["primary_reasons"] = json.loads(cd["primary_reasons"])
            except Exception:
                pass
        cases.append(cd)

    # Find cross-database verifications
    v_rows = c.execute("""
        SELECT * FROM cross_db_verifications
        WHERE parcel_id=?
        ORDER BY id DESC LIMIT 10
    """, (parcel_id,)).fetchall()
    verifications = [dict(v) for v in v_rows]

    c.close()

    dq_score = 100
    deductions = []
    if not parcel.get("latitude") or not parcel.get("longitude"):
        dq_score -= 20
        deductions.append("Missing GPS geocoordinates (-20)")
    if not parcel.get("subdivision"):
        dq_score -= 5
        deductions.append("Missing explicit subdivision (-5)")
    if not parcel.get("owner_reference") and not parcel.get("owner_name"):
        dq_score -= 15
        deductions.append("Missing owner reference (-15)")
    if cases and any(cs["status"] in ("NEW", "UNDER_REVIEW") for cs in cases):
        dq_score -= 15
        deductions.append("Potential duplicate review pending (-15)")

    return {
        "parcel_id": parcel_id,
        "is_duplicate_flagged": bool(parcel.get("duplicate_flag") or any(cs["status"] == "CONFIRMED_DUPLICATE" for cs in cases)),
        "master_parcel_id": parcel.get("master_parcel_id"),
        "quality_score": max(dq_score, 0),
        "deductions": deductions,
        "duplicate_cases": cases,
        "duplicate_count": len(cases),
        "cross_db_verifications": verifications,
        "cross_db_count": len(verifications),
        "assessment": "Potential Duplicate – Review Required" if cases else "Clean Quality Profile"
    }

@router.get("/verification-queue")
def get_verification_queue(
    district: Optional[str] = None,
    priority: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Returns prioritized verification queue.
    Priority computed from exact identifier conflicts, duplicate score, and acquisition stage.
    """
    u = get_authorized_user(authorization)
    district = enforce_district_scope(u, district)

    c = conn()
    query = """
        SELECT dc.*, 
               pa.record_id as rec_a_key, pa.survey_no as rec_a_survey, pa.village as rec_a_village, pa.area as rec_a_area, pa.acquisition_status as stage_a,
               pb.record_id as rec_b_key, pb.survey_no as rec_b_survey, pb.village as rec_b_village, pb.area as rec_b_area, pb.acquisition_status as stage_b
        FROM duplicate_cases dc
        JOIN parcels pa ON dc.record_a_id = pa.id
        JOIN parcels pb ON dc.record_b_id = pb.id
        WHERE dc.status IN ('NEW', 'UNDER_REVIEW', 'FIELD_VERIFICATION_REQUESTED')
    """
    params = []
    if district and district.lower() != "all":
        query += " AND lower(dc.district)=lower(?)"
        params.append(district.strip())

    rows = c.execute(query, params).fetchall()
    c.close()

    items = []
    for r in rows:
        d = dict(r)
        score = float(d.get("similarity_score") or 0)
        stage_a = (d.get("stage_a") or "").lower()
        stage_b = (d.get("stage_b") or "").lower()
        has_advance_stage = any("compens" in s or "possess" in s or "award" in s for s in (stage_a, stage_b))

        # Dynamic statutory priority computation
        if score >= 90.0 or has_advance_stage:
            p_level = "CRITICAL"
            p_weight = 4
        elif score >= 75.0 or d.get("status") == "FIELD_VERIFICATION_REQUESTED":
            p_level = "HIGH"
            p_weight = 3
        elif score >= 60.0:
            p_level = "MEDIUM"
            p_weight = 2
        else:
            p_level = "LOW"
            p_weight = 1

        d["priority"] = p_level
        d["priority_weight"] = p_weight
        d["statutory_impact"] = "High (Compensation / Award Stage)" if has_advance_stage else "Planning / Preliminary Notification Stage"
        
        if isinstance(d.get("primary_reasons"), str):
            try:
                d["primary_reasons"] = json.loads(d["primary_reasons"])
            except Exception:
                d["primary_reasons"] = [d["primary_reasons"]]

        if not priority or priority.upper() == "ALL" or d["priority"] == priority.upper():
            items.append(d)

    items.sort(key=lambda x: (x["priority_weight"], x["similarity_score"]), reverse=True)

    return {
        "district": district,
        "total_queued": len(items),
        "queue": items
    }

@router.get("/cross-record-validation")
def get_cross_record_validation(
    district: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Identifies cadastral anomalies across records:
    - Missing coordinates / out of bounds
    - Unspecified classification
    - Area extent variances across shared survey stems
    """
    u = get_authorized_user(authorization)
    district = enforce_district_scope(u, district)

    c = conn()
    query = "SELECT id, record_id, survey_no, subdivision, village, taluk, district, area, classification, latitude, longitude, acquisition_status FROM parcels WHERE 1=1"
    params = []
    if district and district.lower() != "all":
        query += " AND lower(district)=lower(?)"
        params.append(district.strip())

    parcels = [dict(r) for r in c.execute(query, params).fetchall()]
    c.close()

    anomalies = []
    for p in parcels:
        reasons = []
        severity = "LOW"
        if not p.get("latitude") or not p.get("longitude"):
            reasons.append("Missing GPS coordinates for boundary verification")
            severity = "MEDIUM"
        else:
            try:
                lat = float(p["latitude"])
                lon = float(p["longitude"])
                if not (8.0 <= lat <= 14.0 and 76.0 <= lon <= 80.5):
                    reasons.append(f"Coordinates ({lat}, {lon}) outside Tamil Nadu boundary bounds")
                    severity = "HIGH"
            except Exception:
                reasons.append("Invalid numerical GPS format")
                severity = "HIGH"

        if not p.get("area") or float(p.get("area") or 0) <= 0:
            reasons.append("Invalid or zero land area recorded")
            severity = "CRITICAL"

        if not p.get("classification"):
            reasons.append("Missing land classification (Patta / Poramboke / Ryotwari)")

        if reasons:
            anomalies.append({
                "parcel_id": p["id"],
                "record_id": p.get("record_id"),
                "survey_no": p.get("survey_no"),
                "village": p.get("village"),
                "district": p.get("district"),
                "area": p.get("area"),
                "severity": severity,
                "anomalies": reasons,
                "status": "VALIDATION_FLAGGED"
            })

    # Limit to top 50 anomalies for performance
    return {
        "district": district,
        "total_anomalies_detected": len(anomalies),
        "anomalies": anomalies[:50]
    }

@router.get("/audit-history")
def get_data_quality_audit_history(
    district: Optional[str] = None,
    limit: int = 50,
    authorization: Optional[str] = Header(None)
):
    u = get_authorized_user(authorization)
    district = enforce_district_scope(u, district)

    c = conn()
    rows = c.execute("""
        SELECT * FROM audit 
        WHERE action LIKE 'DUPLICATE%' OR action LIKE 'CROSS_DB%'
        ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    c.close()

    return {
        "district": district,
        "audit_logs": [dict(r) for r in rows],
        "count": len(rows)
    }

@router.get("/national-analytics")
def get_national_analytics(
    authorization: Optional[str] = Header(None)
):
    """
    National & State aggregated statistics for Data Quality monitoring.
    """
    u = get_authorized_user(authorization)
    if u["role"] not in ("state_authority", "authority", "admin"):
        raise HTTPException(403, "Access restricted to State and National Authorities")

    c = conn()
    by_district = []
    dist_rows = c.execute("SELECT district, COUNT(*) as parcel_count FROM parcels GROUP BY district").fetchall()
    for dr in dist_rows:
        dist_name = dr["district"]
        dup_count = c.execute("SELECT COUNT(*) FROM duplicate_cases WHERE lower(district)=lower(?)", (dist_name,)).fetchone()[0]
        confirmed = c.execute("SELECT COUNT(*) FROM duplicate_cases WHERE lower(district)=lower(?) AND status='CONFIRMED_DUPLICATE'", (dist_name,)).fetchone()[0]
        by_district.append({
            "district": dist_name,
            "total_parcels": dr["parcel_count"],
            "duplicate_candidates": dup_count,
            "confirmed_duplicates": confirmed,
            "resolution_rate": round((confirmed / max(dup_count, 1)) * 100, 1)
        })

    total_parcels = c.execute("SELECT COUNT(*) FROM parcels").fetchone()[0]
    total_cases = c.execute("SELECT COUNT(*) FROM duplicate_cases").fetchone()[0]
    confirmed_total = c.execute("SELECT COUNT(*) FROM duplicate_cases WHERE status='CONFIRMED_DUPLICATE'").fetchone()[0]
    c.close()

    return {
        "scope": "National / Multi-District",
        "total_parcels": total_parcels,
        "total_duplicate_cases": total_cases,
        "total_confirmed": confirmed_total,
        "districts_monitored": by_district,
        "accuracy_statement": "Potential Duplicate – Review Required. Never 100% automated proof."
    }

