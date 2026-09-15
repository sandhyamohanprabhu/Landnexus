import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Body, Response
from backend.core import conn, current_user, audit, UPLOADS, ROOT, enforce_district_scope, check_resource_district
from backend.services.ocr_service import process_document_for_ocr, SUPPORTED_LANGUAGES
from backend.services.pdf_report import generate_multilingual_ocr_report

router = APIRouter()

ALLOWED_ROLES = ("authority", "admin", "acquisition_officer", "district_authority", "state_authority", "field_officer", "national_authority", "citizen")
OFFICER_ROLES = ("authority", "admin", "acquisition_officer", "district_authority", "state_authority", "field_officer", "national_authority")

@router.post("/{document_id}/process")
def process(document_id: str, payload: dict = Body(default={}), authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] not in ALLOWED_ROLES:
        raise HTTPException(403, "Insufficient permissions")
    
    language = payload.get("language", "auto")
    mode = payload.get("mode", "auto")
    
    c = conn()
    d = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not d:
        c.close()
        raise HTTPException(404, "Document not found")
        
    # Check authorization
    if u["role"] == "citizen":
        # Check that the citizen uploaded or owns this document
        is_owner = False
        if d["uploaded_by"] and d["uploaded_by"].lower() == u["email"].lower():
            is_owner = True
        elif d["parcel_id"]:
            p = c.execute("SELECT owner_reference FROM parcels WHERE id=?", (d["parcel_id"],)).fetchone()
            if p and p["owner_reference"] and p["owner_reference"].lower() == u["email"].lower():
                is_owner = True
        if not is_owner:
            c.close()
            raise HTTPException(403, "Citizen can only process their own documents")
    elif d["parcel_id"]:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (d["parcel_id"],)).fetchone()
        if p and p["district"]:
            check_resource_district(u, p["district"], "Document OCR Record")
        
    file_path = d["path"]
    
    # Process Multilingual OCR
    result = process_document_for_ocr(file_path, language=language, mode=mode)
    
    if not result["success"]:
        c.execute("UPDATE documents SET ocr_status='Failed', remarks=? WHERE document_id=?", (result["message"], document_id))
        c.commit()
        c.close()
        if result.get("error_code") == "HANDWRITTEN_MODEL_UNAVAILABLE":
            raise HTTPException(400, result["message"])
        raise HTTPException(500, f"OCR failed: {result['message']}")
        
    det_lang = result.get("language", "en")
    lang_conf = result.get("language_confidence", 1.0)
    ocr_engine = result.get("ocr_engine", "Tesseract OCR")
    proc_mode = result.get("processing_mode", mode)
    proc_path = result.get("preprocessed_image")
    dup_flag = 1 if result.get("duplicate_detection", {}).get("is_duplicate") else 0
    overall_status = result.get("ocr_status", "Verification Required")

    c.execute("""
        UPDATE documents 
        SET ocr_status=?, ocr_confidence=?, remarks=?, language=?, language_confidence=?, ocr_engine=?, processing_mode=?, processed_path=?, duplicate_flag=?
        WHERE document_id=?
    """, (overall_status, result.get("confidence", 0.0), result.get("message", ""), det_lang, lang_conf, ocr_engine, proc_mode, proc_path, dup_flag, document_id))
              
    # Delete old extractions for this document if re-running
    c.execute("DELETE FROM ocr_extractions WHERE document_id=?", (document_id,))
    
    extracted = result.get("extracted", {})
    detailed = result.get("detailed_extractions", {})
    for field_name, value in extracted.items():
        if value:
            f_conf = detailed.get(field_name, {}).get("confidence", result.get("confidence", 0.0))
            f_uncert = detailed.get(field_name, {}).get("uncertainty_label", "Engine confidence")
            c.execute("""
                INSERT INTO ocr_extractions (document_id, field_name, value, original_value, confidence, field_confidence, uncertainty_label, validation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (document_id, field_name, value, value, f_conf, f_conf, f_uncert, 'Pending'))
                      
    c.commit()
    c.close()
    
    audit(u["email"], "OCR_PROCESS", "documents", document_id, f"Language={det_lang} | Engine={ocr_engine} | Mode={proc_mode}", overall_status, "success")
    
    return {
        "document_id": document_id,
        "ocr_status": overall_status,
        "human_verification_required": True,
        "language": det_lang,
        "language_name": result.get("language_name", "English"),
        "script": result.get("script", "Latin"),
        "language_confidence": lang_conf,
        "ocr_engine": ocr_engine,
        "processing_mode": proc_mode,
        "is_mock_fallback": result.get("is_mock_fallback", False),
        "preprocessed_image": proc_path,
        "extractions": extracted,
        "detailed_extractions": detailed,
        "duplicate_detection": result.get("duplicate_detection"),
        "message": result.get("message", "Multilingual OCR processing complete")
    }

@router.get("/verification-queue")
def get_verification_queue(district: str = None, authorization: str = Header(None)):
    """Fetch all documents requiring human verification, scoped by district."""
    u = current_user(authorization)
    if not u or u["role"] not in ALLOWED_ROLES:
        raise HTTPException(403, "Insufficient permissions")
    
    if u.get("role") == "citizen":
        return {"queue": [], "count": 0, "district_scope": "citizen"}
        
    district = enforce_district_scope(u, district)
    c = conn()
    
    query = """
        SELECT d.*, p.record_id as parcel_record_id, p.survey_no as parcel_survey, p.district as parcel_district, pr.project_name
        FROM documents d
        LEFT JOIN parcels p ON d.parcel_id = p.id
        LEFT JOIN projects pr ON d.project_id = pr.project_id
        WHERE d.ocr_status IN ('Verification Required', 'Pending Verification', 'Flagged for Review')
    """
    params = []
    if district and district.lower() != "all":
        query += " AND (LOWER(COALESCE(p.district, pr.district, '')) = LOWER(?))"
        params.extend([district])
    query += " ORDER BY d.id DESC LIMIT 100"
    
    rows = [dict(r) for r in c.execute(query, tuple(params)).fetchall()]
    c.close()
    return {"queue": rows, "count": len(rows), "district_scope": district}

@router.get("/analytics")
def get_ocr_analytics(district: str = None, authorization: str = Header(None)):
    """Aggregate multilingual OCR operational statistics from database."""
    u = current_user(authorization)
    if not u or u["role"] not in ALLOWED_ROLES:
        raise HTTPException(403, "Insufficient permissions")
        
    if u.get("role") == "citizen":
        district = "citizen"
    else:
        district = enforce_district_scope(u, district)
    c = conn()
    
    # 1. Total processed documents
    tot_row = c.execute("SELECT COUNT(*) as total, AVG(ocr_confidence) as avg_conf FROM documents WHERE ocr_status != 'Not Started'").fetchone()
    total_processed = tot_row["total"] if tot_row else 0
    avg_confidence = round(float(tot_row["avg_conf"] or 0.85) * 100, 1)

    # 2. Breakdown by language
    lang_rows = c.execute("SELECT COALESCE(language, 'en') as lang, COUNT(*) as cnt FROM documents WHERE ocr_status != 'Not Started' GROUP BY lang").fetchall()
    language_breakdown = {r["lang"]: r["cnt"] for r in lang_rows}

    # 3. Mode breakdown
    mode_rows = c.execute("SELECT COALESCE(processing_mode, 'auto') as mode, COUNT(*) as cnt FROM documents WHERE ocr_status != 'Not Started' GROUP BY mode").fetchall()
    mode_breakdown = {r["mode"]: r["cnt"] for r in mode_rows}

    # 4. Status breakdown
    status_rows = c.execute("SELECT ocr_status, COUNT(*) as cnt FROM documents GROUP BY ocr_status").fetchall()
    status_breakdown = {r["ocr_status"]: r["cnt"] for r in status_rows}

    # 5. Corrections count in active learning
    learn_count = c.execute("SELECT COUNT(*) as cnt FROM ocr_learning_records").fetchone()["cnt"]

    # 6. Duplicates detected count
    dup_count = c.execute("SELECT COUNT(*) as cnt FROM documents WHERE duplicate_flag = 1").fetchone()["cnt"]

    c.close()
    return {
        "total_documents_processed": total_processed,
        "average_confidence": avg_confidence,
        "language_breakdown": language_breakdown,
        "mode_breakdown": mode_breakdown,
        "status_breakdown": status_breakdown,
        "active_learning_corrections": learn_count,
        "duplicates_detected": dup_count,
        "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        "district_scope": district
    }

@router.get("/{document_id}")
def get_ocr_details(document_id: str, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
        
    c = conn()
    d = c.execute("""
        SELECT d.*, pa.survey_no, pa.owner_name, pa.village, pa.taluk, pa.area, 
               COALESCE(pa.district, pr.district) as district, pa.record_id as parcel_record_id,
               pr.project_name
        FROM documents d
        LEFT JOIN parcels pa ON d.parcel_id = pa.id
        LEFT JOIN projects pr ON d.project_id = pr.project_id
        WHERE d.document_id=?
    """, (document_id,)).fetchone()
    if not d:
        c.close()
        raise HTTPException(404, "Document not found")
        
    # Check district authorization
    if d["district"]:
        check_resource_district(u, d["district"], "Document OCR Record")

    extractions = c.execute("SELECT * FROM ocr_extractions WHERE document_id=?", (document_id,)).fetchall()
    c.close()
    
    return {
        "document_id": document_id,
        "document_name": d["document_name"],
        "project_id": d["project_id"],
        "project_name": d["project_name"],
        "parcel_id": d["parcel_id"],
        "survey_no": d["survey_no"],
        "owner_name": d["owner_name"],
        "village": d["village"],
        "taluk": d["taluk"],
        "district": d["district"],
        "area": d["area"],
        "parcel_record_id": d["parcel_record_id"],
        "ocr_status": d["ocr_status"],
        "verification_status": d["verification_status"],
        "ocr_confidence": d["ocr_confidence"],
        "language": d["language"] or "en",
        "language_confidence": d["language_confidence"] or 1.0,
        "ocr_engine": d["ocr_engine"] or "Tesseract OCR",
        "processing_mode": d["processing_mode"] or "auto",
        "preprocessed_image": d["processed_path"],
        "duplicate_flag": bool(d["duplicate_flag"]),
        "rejection_reason": d["rejection_reason"],
        "remarks": d["remarks"],
        "extractions": [dict(e) for e in extractions]
    }

@router.post("/{document_id}/verify")
def verify_ocr(document_id: str, payload: dict = Body(...), authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] not in ALLOWED_ROLES:
        raise HTTPException(403, "Insufficient permissions")
        
    c = conn()
    d = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not d:
        c.close()
        raise HTTPException(404, "Document not found")
        
    if d["parcel_id"]:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (d["parcel_id"],)).fetchone()
        if p:
            check_resource_district(u, p["district"], "Document OCR Record")

    verified_fields = payload.get("fields", {})
    notes = payload.get("notes", "")
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Existing extractions to detect human corrections for active learning
    existing_rows = c.execute("SELECT field_name, value FROM ocr_extractions WHERE document_id=?", (document_id,)).fetchall()
    existing_map = {r["field_name"]: r["value"] for r in existing_rows}
    
    c.execute("DELETE FROM ocr_extractions WHERE document_id=?", (document_id,))
    
    corrections_logged = 0
    for field_name, value in verified_fields.items():
        if value:
            orig_val = existing_map.get(field_name, value)
            c.execute("""
                INSERT INTO ocr_extractions (document_id, field_name, value, original_value, corrected_value, confidence, field_confidence, validation_status, human_verified, notes)
                VALUES (?, ?, ?, ?, ?, 1.0, 1.0, 'Verified', 1, ?)
            """, (document_id, field_name, value, orig_val, value, notes))

            # If user modified the field, persist to active learning records
            if orig_val and orig_val.strip() != value.strip():
                c.execute("""
                    INSERT INTO ocr_learning_records 
                    (document_id, parcel_id, project_id, field_name, original_value, corrected_value, language, script, ocr_engine, processing_mode, verified_by, verifier_role, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending Retraining')
                """, (document_id, d["parcel_id"], d["project_id"], field_name, orig_val, value, d["language"], "Unicode", d["ocr_engine"], d["processing_mode"], u["email"], u["role"]))
                corrections_logged += 1
                      
    c.execute("""
        UPDATE documents 
        SET ocr_status='Verified', verification_status='Verified', verified_by=?, verified_at=?, remarks=?
        WHERE document_id=?
    """, (u["email"], now_iso, notes or "Verified by officer", document_id))
    
    c.commit()
    c.close()
    
    audit(u["email"], "OCR_VERIFY", "documents", document_id, f"Verified with {corrections_logged} corrections | notes={notes}", "Verified", "success")
    
    return {
        "success": True, 
        "message": "OCR data verified successfully and logged to active learning repository",
        "corrections_logged": corrections_logged
    }

@router.post("/{document_id}/reject")
def reject_ocr(document_id: str, payload: dict = Body(...), authorization: str = Header(None)):
    """Reject OCR extraction with reason (e.g. unreadable, incorrect document)."""
    u = current_user(authorization)
    if not u or u["role"] not in ALLOWED_ROLES:
        raise HTTPException(403, "Insufficient permissions")
        
    reason = payload.get("reason", "Marked unreadable or rejected by officer")
    c = conn()
    d = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not d:
        c.close()
        raise HTTPException(404, "Document not found")
        
    c.execute("""
        UPDATE documents 
        SET ocr_status='Rejected', verification_status='Rejected', rejection_reason=?, verified_by=?, verified_at=CURRENT_TIMESTAMP
        WHERE document_id=?
    """, (reason, u["email"], document_id))
    
    c.execute("UPDATE ocr_extractions SET validation_status='Rejected' WHERE document_id=?", (document_id,))
    c.commit()
    c.close()
    
    audit(u["email"], "OCR_REJECT", "documents", document_id, f"Reason: {reason}", "Rejected", "success")
    return {"success": True, "message": f"Document OCR rejected: {reason}"}

@router.get("/{document_id}/pdf")
def download_ocr_pdf(document_id: str, authorization: str = Header(None)):
    """Stream official ReportLab Multilingual OCR Intelligence PDF Report."""
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
        
    c = conn()
    d = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not d:
        c.close()
        raise HTTPException(404, "Document not found")
        
    if d["parcel_id"]:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (d["parcel_id"],)).fetchone()
        if p:
            check_resource_district(u, p["district"], "Document OCR PDF")

    try:
        pdf_bytes = generate_multilingual_ocr_report(c, document_id, user_info=u)
    finally:
        c.close()

    audit(u["email"], "OCR_PDF_EXPORT", "documents", document_id, "Exported Multilingual OCR Intelligence Report", "success")

    safe_name = f"LANDNEXUS_OCR_{document_id[:8].upper()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'}
    )

@router.get("/{document_id}/preview")
def get_document_preview(document_id: str, version: str = "original", authorization: str = Header(None)):
    """Serve original or preprocessed document image for side-by-side inspection."""
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    c = conn()
    d = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    c.close()
    if not d:
        raise HTTPException(404, "Document not found")

    target_file = Path(d["path"])
    if not target_file.is_absolute() or not target_file.exists():
        candidates = [
            UPLOADS / target_file.name,
            ROOT / target_file,
            ROOT / "uploads" / target_file.name,
            target_file
        ]
        for cand in candidates:
            if cand.exists():
                target_file = cand
                break

    if version == "preprocessed":
        proc_cand = target_file.parent / f"proc_{target_file.stem}.png"
        if proc_cand.exists():
            target_file = proc_cand

    if not target_file.exists():
        import io
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (800, 1000), color=(248, 250, 252))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(20, 20), (780, 980)], outline=(203, 213, 225), width=2)
        draw.rectangle([(40, 40), (760, 100)], fill=(15, 108, 112))
        draw.text((60, 55), f"LANDNEXUS DOCUMENT: {d['document_name'] or document_id}", fill=(255, 255, 255))
        draw.text((60, 130), f"Document ID: {document_id}", fill=(51, 65, 85))
        draw.text((60, 160), f"Status: {d['ocr_status']} | Format: {d['format']}", fill=(51, 65, 85))
        draw.text((60, 190), f"Uploaded By: {d['uploaded_by'] or 'Official Authority'}", fill=(51, 65, 85))
        draw.text((60, 220), f"Engine: {d['ocr_engine'] or 'Auto-Detection Active'}", fill=(51, 65, 85))
        draw.text((60, 260), "Official Land Record - Digital Copy Processed", fill=(100, 116, 139))
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")

    ext = target_file.suffix.lower()
    media_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf"}
    media_type = media_map.get(ext, "application/octet-stream")

    return Response(content=target_file.read_bytes(), media_type=media_type)


