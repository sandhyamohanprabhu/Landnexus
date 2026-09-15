from fastapi import APIRouter, HTTPException, Header
from backend.core import conn, current_user, audit

router = APIRouter()

ALLOWED_ROLES = ("authority", "admin", "state_authority", "acquisition_officer", "district_authority")


def ensure_columns(c):
    """Backward-compatible migration for existing SURVI SQLite databases."""
    columns = {row[1] for row in c.execute("PRAGMA table_info(projects)").fetchall()}
    if "fixed_cent_rate" not in columns:
        c.execute("ALTER TABLE projects ADD COLUMN fixed_cent_rate REAL DEFAULT 0")
    if "total_land_area_cost" not in columns:
        c.execute("ALTER TABLE projects ADD COLUMN total_land_area_cost REAL DEFAULT 0")
    if "estimated_land_cost" not in columns:
        c.execute("ALTER TABLE projects ADD COLUMN estimated_land_cost REAL DEFAULT 0")


def require_user(authorization):
    user = current_user(authorization)
    if not user:
        raise HTTPException(401, "Authentication required")
    if user["role"] not in ALLOWED_ROLES:
        raise HTTPException(403, "Insufficient permissions")
    return user


def _numeric(value, field):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, f"{field} must be numeric")
    if number < 0:
        raise HTTPException(400, f"{field} cannot be negative")
    return number


@router.post("/{project_id}/compensation")
def set_project_compensation(project_id: str, payload: dict, authorization: str = Header(None)):
    user = require_user(authorization)
    rate = _numeric(payload.get("fixed_cent_rate", 0), "Fixed cent rate")

    c = conn()
    try:
        ensure_columns(c)
        project = c.execute(
            "SELECT project_id, land_required FROM projects WHERE project_id=?",
            (project_id,),
        ).fetchone()
        if not project:
            raise HTTPException(404, "Project not found")

        acres = _numeric(project["land_required"], "Land area")
        cents = acres * 100
        total = cents * rate

        # Backend calculates the payable estimate from authoritative project acreage.
        c.execute(
            "UPDATE projects SET fixed_cent_rate=?, total_land_area_cost=?, estimated_land_cost=? WHERE project_id=?",
            (rate, total, total, project_id),
        )
        c.commit()
    finally:
        c.close()

    audit(user["email"], "SET_PROJECT_COMPENSATION", "project", f"{project_id}: rate={rate}; total={total}")
    return {
        "message": "Project compensation rate saved",
        "project_id": project_id,
        "land_area_acres": acres,
        "land_area_cents": cents,
        "fixed_cent_rate": rate,
        "total_land_area_cost": total,
        "formula": "acres × 100 cents × fixed rate per cent",
    }


@router.get("/{project_id}/compensation")
def get_project_compensation(project_id: str, authorization: str = Header(None)):
    require_user(authorization)
    c = conn()
    try:
        ensure_columns(c)
        row = c.execute(
            "SELECT project_id, fixed_cent_rate, total_land_area_cost, estimated_land_cost, land_required FROM projects WHERE project_id=?",
            (project_id,),
        ).fetchone()
        c.commit()
    finally:
        c.close()
    if not row:
        raise HTTPException(404, "Project not found")

    acres = float(row["land_required"] or 0)
    rate = float(row["fixed_cent_rate"] or 0)
    total = acres * 100 * rate

    return {
        "project_id": row["project_id"],
        "land_area_acres": acres,
        "land_area_cents": acres * 100,
        "fixed_cent_rate": rate,
        "total_land_area_cost": total,
        "estimated_land_cost": total,
        "formula": "acres × 100 cents × fixed rate per cent",
    }
