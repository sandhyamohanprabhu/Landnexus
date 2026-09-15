import os
import uuid
import shutil
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from backend.core import current_user, conn, UPLOADS, enforce_district_scope, check_resource_district

router = APIRouter()

@router.get("/")
def docs(authorization: str = Header(None), parcel_id: int = None, project_id: str = None, district: str = None):
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")
    district = enforce_district_scope(u, district)
    c = conn()
    if parcel_id:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (parcel_id,)).fetchone()
        if p: check_resource_district(u, p["district"], "Parcel Documents")
        rows = [dict(x) for x in c.execute("SELECT * FROM documents WHERE parcel_id=? ORDER BY id DESC", (parcel_id,)).fetchall()]
    elif project_id:
        pr = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if pr: check_resource_district(u, pr["district"], "Project Documents")
        rows = [dict(x) for x in c.execute("SELECT * FROM documents WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()]
    elif district and district.lower() != "all":
        rows = [dict(x) for x in c.execute("""
            SELECT d.* FROM documents d
            LEFT JOIN projects pr ON d.project_id=pr.project_id
            LEFT JOIN parcels pa ON d.parcel_id=pa.id
            WHERE lower(pr.district)=lower(?) OR lower(pa.district)=lower(?)
            ORDER BY d.id DESC LIMIT 500
        """, (district.strip(), district.strip())).fetchall()]
    else:
        rows = [dict(x) for x in c.execute("SELECT * FROM documents ORDER BY id DESC LIMIT 500").fetchall()]
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

@router.post("/")
async def upload_doc(
    authorization: str = Header(None),
    file: UploadFile = File(...),
    project_id: str = Form(None),
    parcel_id: int = Form(None)
):
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")
    
    c = conn()
    if parcel_id:
        p = c.execute("SELECT district FROM parcels WHERE id=?", (parcel_id,)).fetchone()
        if p: check_resource_district(u, p["district"], "Parcel Documents")
    if project_id:
        pr = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if pr: check_resource_district(u, pr["district"], "Project Documents")
        
    doc_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{doc_id}{file_ext}"
    file_path = UPLOADS / safe_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    c.execute("""
        INSERT INTO documents (document_id, project_id, parcel_id, document_name, path, format, uploaded_by, verification_status, ocr_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', 'Not Started')
    """, (doc_id, project_id, parcel_id, file.filename, str(file_path), file_ext, u["email"]))
    c.commit()
    c.close()
    
    return {"document_id": doc_id, "message": "Uploaded successfully"}
