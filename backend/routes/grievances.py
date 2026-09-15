from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from backend.core import conn, current_user, enforce_district_scope, check_resource_district

router = APIRouter()

class GrievanceCreate(BaseModel):
    parcel_id: int
    project_id: str
    submitted_by: str
    type: str
    description: str


@router.get('/all')
def get_all_grievances(district: str = None, authorization: str = Header(None)):
    u = current_user(authorization)
    if u:
        district = enforce_district_scope(u, district)
    c = conn()
    if district and district.lower() != "all":
        res = c.execute("""
            SELECT g.* FROM grievances g
            LEFT JOIN projects pr ON g.project_id=pr.project_id
            LEFT JOIN parcels pa ON g.parcel_id=pa.id
            WHERE lower(pr.district)=lower(?) OR lower(pa.district)=lower(?)
            ORDER BY g.created_at DESC LIMIT 100
        """, (district.strip(), district.strip())).fetchall()
    else:
        res = c.execute("SELECT * FROM grievances ORDER BY created_at DESC LIMIT 100").fetchall()
    c.close()
    return [dict(r) for r in res]

@router.get('/mine')
def get_my_grievances(authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] != "citizen":
        raise HTTPException(403, "Citizen access required")
    c = conn()
    res = c.execute("""
        SELECT g.*, p.survey_no, p.village, p.taluk, p.district
        FROM grievances g
        LEFT JOIN parcels p ON p.id = g.parcel_id
        WHERE lower(g.submitted_by) = lower(?) OR lower(p.owner_reference) = lower(?)
        ORDER BY g.created_at DESC
    """, (u["email"], u["email"])).fetchall()
    c.close()
    return [dict(r) for r in res]

@router.get("/{project_id}")
def get_grievances(project_id: str, authorization: str = Header(None)):
    c = conn()
    u = current_user(authorization)
    if u:
        p = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if p:
            check_resource_district(u, p["district"], "Project Grievances")
    res = c.execute("SELECT * FROM grievances WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
    c.close()
    return [dict(r) for r in res]

@router.post("/")
def create_grievance(g: GrievanceCreate, authorization: str = Header(None)):
    c = conn()
    u = current_user(authorization)
    if u:
        p = c.execute("SELECT district FROM projects WHERE project_id=?", (g.project_id,)).fetchone()
        if p:
            check_resource_district(u, p["district"], "Project Grievances")
    c.execute("INSERT INTO grievances(parcel_id, project_id, submitted_by, type, description) VALUES(?, ?, ?, ?, ?)", (g.parcel_id, g.project_id, g.submitted_by, g.type, g.description))
    c.commit()
    c.close()
    return {"status": "success", "message": "Grievance submitted"}

@router.post("/{grievance_id}/resolve")
def resolve_grievance(grievance_id: int, resolution: dict, authorization: str = Header(None)):
    c = conn()
    u = current_user(authorization)
    if u:
        g = c.execute("""
            SELECT pr.district as pr_dist, pa.district as pa_dist 
            FROM grievances g 
            LEFT JOIN projects pr ON g.project_id=pr.project_id 
            LEFT JOIN parcels pa ON g.parcel_id=pa.id 
            WHERE g.id=?
        """, (grievance_id,)).fetchone()
        if g:
            check_resource_district(u, g["pr_dist"] or g["pa_dist"], "Grievance")
    c.execute("UPDATE grievances SET status='Resolved', resolution=? WHERE id=?", (resolution.get("resolution", ""), grievance_id))
    c.commit()
    c.close()
    return {"status": "success"}
