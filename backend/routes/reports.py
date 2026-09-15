from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response
from backend.core import conn, current_user, enforce_district_scope, check_resource_district

router = APIRouter()

# ─── Existing MIS Reports JSON Endpoint ───
@router.get("")
@router.get("/")
@router.get("/summary")
def get_reports(district: str = None, authorization: str = Header(None)):
    u = current_user(authorization)
    if u:
        district = enforce_district_scope(u, district)
    c = conn()
    if district and district.lower() != "all":
        dist = district.strip()
        projects = c.execute("SELECT COUNT(*) as cnt FROM projects WHERE lower(district)=lower(?)", (dist,)).fetchone()["cnt"]
        try:
            delayed_milestones = c.execute("""
                SELECT COUNT(*) as cnt FROM project_milestones m
                JOIN projects p ON m.project_id=p.project_id
                WHERE m.delay_days > 0 AND lower(p.district)=lower(?)
            """, (dist,)).fetchone()["cnt"]
        except Exception:
            delayed_milestones = 0
        try:
            total_compensation = c.execute("""
                SELECT SUM(co.pending_amount) as total FROM compensation co
                JOIN parcels p ON co.parcel_id=p.id
                WHERE lower(p.district)=lower(?)
            """, (dist,)).fetchone()["total"] or 0
        except Exception:
            total_compensation = 0
        try:
            total_rr = c.execute("""
                SELECT COUNT(*) as cnt FROM r_and_r rr
                JOIN projects p ON rr.project_id=p.project_id
                WHERE rr.status='Pending' AND lower(p.district)=lower(?)
            """, (dist,)).fetchone()["cnt"]
        except Exception:
            total_rr = 0

        active_projects = c.execute("""
            SELECT COUNT(*) as cnt FROM projects
            WHERE lower(district)=lower(?) AND (project_status IS NULL OR project_status NOT IN ('Completed','Closed'))
        """, (dist,)).fetchone()["cnt"]
        completed_projects = c.execute("""
            SELECT COUNT(*) as cnt FROM projects
            WHERE lower(district)=lower(?) AND project_status='Completed'
        """, (dist,)).fetchone()["cnt"]

        project_wise = c.execute("""
            SELECT project_id, project_name, current_stage, progress
            FROM projects WHERE lower(district)=lower(?) LIMIT 50
        """, (dist,)).fetchall()
    else:
        projects = c.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()["cnt"]
        try:
            delayed_milestones = c.execute("SELECT COUNT(*) as cnt FROM project_milestones WHERE delay_days > 0").fetchone()["cnt"]
        except Exception:
            delayed_milestones = 0
        try:
            total_compensation = c.execute("SELECT SUM(pending_amount) as total FROM compensation").fetchone()["total"] or 0
        except Exception:
            total_compensation = 0
        try:
            total_rr = c.execute("SELECT COUNT(*) as cnt FROM r_and_r WHERE status='Pending'").fetchone()["cnt"]
        except Exception:
            total_rr = 0

        active_projects = c.execute("""
            SELECT COUNT(*) as cnt FROM projects
            WHERE project_status IS NULL OR project_status NOT IN ('Completed','Closed')
        """).fetchone()["cnt"]
        completed_projects = c.execute("""
            SELECT COUNT(*) as cnt FROM projects WHERE project_status='Completed'
        """).fetchone()["cnt"]

        project_wise = c.execute("SELECT project_id, project_name, current_stage, progress FROM projects LIMIT 50").fetchall()

    c.close()

    return {
        "summary": {
            "total_projects": projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "delayed_cases": delayed_milestones,
            "total_pending_compensation": total_compensation,
            "pending_rr": total_rr
        },
        "project_wise": [dict(p) for p in project_wise]
    }


# ─── Project list for selector ───
@router.get("/project-list")
def project_list(district: str = None, authorization: str = Header(None)):
    """Return a lightweight project list for the UI selector."""
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    if u.get("role") == "citizen":
        raise HTTPException(403, "Citizens cannot access internal reports")
    district = enforce_district_scope(u, district)
    c = conn()
    if district and district.lower() != "all":
        rows = c.execute("""
            SELECT project_id, project_name, district, current_stage
            FROM projects WHERE lower(district)=lower(?) ORDER BY project_id
        """, (district.strip(),)).fetchall()
    else:
        rows = c.execute("""
            SELECT project_id, project_name, district, current_stage
            FROM projects ORDER BY project_id LIMIT 500
        """).fetchall()
    c.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  PDF REPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

def _check_not_citizen(u):
    """Raise 403 if user is citizen or not authenticated."""
    if not u:
        raise HTTPException(401, "Authentication required")
    if u.get("role") == "citizen":
        raise HTTPException(403, "Citizens cannot access internal government reports")


@router.get("/project/{project_id}/pdf")
def download_project_pdf(project_id: str, authorization: str = Header(None)):
    """Download a detailed PDF report for a single project."""
    u = current_user(authorization)
    _check_not_citizen(u)
    c = conn()
    proj = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not proj:
        c.close()
        raise HTTPException(404, "Project not found")
    check_resource_district(u, proj["district"], "Project Report")
    try:
        from backend.services.pdf_report import generate_project_report
        pdf_bytes = generate_project_report(c, project_id)
    except ValueError as e:
        c.close()
        raise HTTPException(404, str(e))
    except Exception as e:
        c.close()
        raise HTTPException(500, f"PDF generation failed: {str(e)}")
    c.close()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="LANDNEXUS_Project_{project_id}.pdf"'}
    )


@router.get("/project/{project_id}/bottlenecks/pdf")
def download_project_bottleneck_pdf(project_id: str, authorization: str = Header(None)):
    """Download a bottleneck-focused PDF report for a single project."""
    u = current_user(authorization)
    _check_not_citizen(u)
    c = conn()
    proj = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not proj:
        c.close()
        raise HTTPException(404, "Project not found")
    check_resource_district(u, proj["district"], "Project Bottleneck Report")
    try:
        from backend.services.pdf_report import generate_project_bottleneck_report
        pdf_bytes = generate_project_bottleneck_report(c, project_id)
    except ValueError as e:
        c.close()
        raise HTTPException(404, str(e))
    except Exception as e:
        c.close()
        raise HTTPException(500, f"PDF generation failed: {str(e)}")
    c.close()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="LANDNEXUS_Bottleneck_{project_id}.pdf"'}
    )


@router.get("/district/{district}/pdf")
def download_district_pdf(district: str, authorization: str = Header(None)):
    """Download a comprehensive PDF report for a single district."""
    u = current_user(authorization)
    _check_not_citizen(u)
    district = enforce_district_scope(u, district)
    c = conn()
    try:
        from backend.services.pdf_report import generate_district_report
        pdf_bytes = generate_district_report(c, district)
    except Exception as e:
        c.close()
        raise HTTPException(500, f"PDF generation failed: {str(e)}")
    c.close()
    safe_name = district.replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="LANDNEXUS_District_{safe_name}.pdf"'}
    )


@router.get("/state/pdf")
def download_state_pdf(authorization: str = Header(None)):
    """Download a state-level district-wise comparison PDF report."""
    u = current_user(authorization)
    _check_not_citizen(u)
    # Only state_authority, authority, and admin can access state reports
    if u.get("role") not in ("state_authority", "authority", "admin"):
        raise HTTPException(403, "State-level reports require State Authority access")
    c = conn()
    try:
        from backend.services.pdf_report import generate_state_report
        pdf_bytes = generate_state_report(c)
    except Exception as e:
        c.close()
        raise HTTPException(500, f"PDF generation failed: {str(e)}")
    c.close()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="LANDNEXUS_State_Report_TamilNadu.pdf"'}
    )
