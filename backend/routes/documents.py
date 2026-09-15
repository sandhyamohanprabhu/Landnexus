import os
import uuid
import shutil
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from backend.core import current_user, conn, UPLOADS, enforce_district_scope, check_resource_district

router = APIRouter()

@router.get("")
@router.get("/")
def docs(authorization: str = Header(None), parcel_id: int = None, project_id: str = None, district: str = None, search: str = None):
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")

    # If citizen, return citizen's own documents
    if u.get("role") == "citizen":
        c = conn()
        rows = [dict(x) for x in c.execute("""
            SELECT d.*, p.survey_no, p.owner_name, p.village, p.taluk, p.district, p.area, p.record_id as parcel_record_id, pr.project_name
            FROM documents d
            LEFT JOIN parcels p ON p.id = d.parcel_id
            LEFT JOIN projects pr ON pr.project_id = d.project_id
            WHERE lower(p.owner_reference) = lower(?) OR lower(d.uploaded_by) = lower(?)
            ORDER BY d.id DESC
        """, (u["email"], u["email"])).fetchall()]
        c.close()
        return rows

    district = enforce_district_scope(u, district)
    c = conn()
    
    base_query = """
        SELECT d.*, pa.survey_no, pa.owner_name, pa.village, pa.taluk, 
               COALESCE(pa.district, pr.district) as district, pa.area, 
               pa.record_id as parcel_record_id, pr.project_name
        FROM documents d
        LEFT JOIN projects pr ON d.project_id = pr.project_id
        LEFT JOIN parcels pa ON d.parcel_id = pa.id
        WHERE 1=1
    """
    params = []
    
    if parcel_id:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (parcel_id,)).fetchone()
        if p: check_resource_district(u, p["district"], "Parcel Documents")
        base_query += " AND d.parcel_id = ?"
        params.append(parcel_id)
    elif project_id:
        pr = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if pr: check_resource_district(u, pr["district"], "Project Documents")
        base_query += " AND d.project_id = ?"
        params.append(project_id)
    elif district and district.lower() != "all":
        base_query += " AND (lower(pr.district) = lower(?) OR lower(pa.district) = lower(?))"
        params.extend([district.strip(), district.strip()])

    if search:
        s_term = f"%{search.strip().lower()}%"
        base_query += """ AND (
            lower(d.document_id) LIKE ? OR
            lower(d.document_name) LIKE ? OR
            lower(COALESCE(pa.survey_no, '')) LIKE ? OR
            lower(COALESCE(pa.owner_name, '')) LIKE ? OR
            lower(COALESCE(pa.village, '')) LIKE ? OR
            lower(COALESCE(pa.taluk, '')) LIKE ? OR
            lower(COALESCE(pr.project_name, '')) LIKE ?
        )"""
        params.extend([s_term, s_term, s_term, s_term, s_term, s_term, s_term])
        
    base_query += " ORDER BY d.id DESC LIMIT 500"
    rows = [dict(x) for x in c.execute(base_query, tuple(params)).fetchall()]
    c.close()
    return rows

@router.get("/mine")
def my_docs(authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] != "citizen":
        raise HTTPException(403, "Citizen access required")
    c = conn()
    rows = [dict(x) for x in c.execute("""
        SELECT d.*, p.survey_no, p.village, p.district
        FROM documents d
        JOIN parcels p ON p.id = d.parcel_id
        WHERE lower(p.owner_reference) = lower(?)
        ORDER BY d.id DESC
    """, (u["email"],)).fetchall()]
    c.close()
    return rows

@router.post("")
@router.post("/")
async def upload_doc(
    authorization: str = Header(None),
    file: UploadFile = File(...),
    project_id: str = Form(None),
    parcel_id: int = Form(None)
):
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")

    file_ext = os.path.splitext(file.filename or "")[1].lower()
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    if file_ext not in allowed_exts:
        raise HTTPException(400, f"Unsupported document type '{file_ext}'. Please upload PDF, PNG, JPG/JPEG, or TIFF.")
    
    c = conn()
    if parcel_id:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (parcel_id,)).fetchone()
        if p: check_resource_district(u, p["district"], "Parcel Documents")
    if project_id:
        pr = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if pr: check_resource_district(u, pr["district"], "Project Documents")
        
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}{file_ext}"
    file_path = UPLOADS / safe_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Validate non-zero file size
    if not file_path.exists() or file_path.stat().st_size == 0:
        if file_path.exists(): file_path.unlink()
        c.close()
        raise HTTPException(400, "Uploaded file is empty (0 bytes). Please upload a valid document.")
        
    c.execute("""
        INSERT INTO documents (document_id, project_id, parcel_id, document_name, path, format, uploaded_by, verification_status, ocr_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', 'Not Started')
    """, (doc_id, project_id, parcel_id, file.filename, str(file_path), file_ext, u["email"]))
    c.commit()
    c.close()
    
    return {
        "success": True,
        "document_id": doc_id,
        "document_name": file.filename,
        "format": file_ext,
        "message": "Uploaded successfully. Ready for OCR processing."
    }
