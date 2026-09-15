"""
R&R (Rehabilitation & Resettlement) API Routes
===============================================
Provides state dashboard, district dashboard, family-level detail,
citizen portal view, and field officer verification endpoints.
"""

from fastapi import APIRouter, Header, HTTPException, Query, UploadFile, File, Form
from backend.core import conn, current_user, enforce_district_scope, check_resource_district, audit
from typing import Optional
import datetime
import os
import hashlib

router = APIRouter()


def _require_auth(authorization: str, roles: tuple = None):
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    if roles and u["role"] not in roles:
        raise HTTPException(403, "Insufficient permissions")
    return u


# ── State Dashboard ──────────────────────────────────────────────────────────
@router.get("/state-dashboard")
def state_rr_dashboard(authorization: str = Header(None)):
    """
    State-level R&R dashboard: aggregated metrics across all 5 districts.
    Role: state_authority, authority, admin
    """
    _require_auth(authorization, ("state_authority", "authority", "admin"))
    c = conn()
    q = lambda sql, args=(): c.execute(sql, args).fetchone()[0]

    total_families = q("SELECT COUNT(*) FROM rr_families")
    completed = q("SELECT COUNT(*) FROM rr_families WHERE exceptional_state='Completed'")
    in_progress = q("SELECT COUNT(*) FROM rr_families WHERE exceptional_state NOT IN ('Completed','Blocked','On Hold')")
    delayed = q("SELECT COUNT(*) FROM rr_families WHERE readiness_band='Delayed'")
    critical = q("SELECT COUNT(*) FROM rr_families WHERE readiness_band='Critical'")
    avg_readiness = c.execute("SELECT ROUND(AVG(readiness_percentage),1) FROM rr_families").fetchone()[0] or 0
    open_grievances = q("SELECT COUNT(*) FROM rr_families WHERE grievance_status IN ('Open','Reopened','Escalated','Under Review','Field Investigation')")
    escalated_grievances = q("SELECT COUNT(*) FROM rr_families WHERE grievance_status='Escalated'")
    awaiting_verification = q("SELECT COUNT(*) FROM rr_families WHERE verification_status IN ('Not Started','Scheduled','Pending')")
    awaiting_benefits = q("SELECT COUNT(*) FROM rr_families WHERE compensation_status IN ('Not Started','Processing','Approved') OR housing_status IN ('Pending','Approved','Site Identified') OR livelihood_status IN ('Not Assessed','Assessment Pending','Eligible','Plan Prepared','Sanctioned')")
    at_risk = q("SELECT COUNT(*) FROM rr_families WHERE risk_level IN ('High','Critical')")
    vulnerable = q("SELECT COUNT(*) FROM rr_families WHERE is_vulnerable=1")
    blocked = q("SELECT COUNT(*) FROM rr_families WHERE exceptional_state IN ('Blocked','On Hold')")

    # District-wise readiness comparison
    district_breakdown = [dict(r) for r in c.execute("""
        SELECT
            district,
            COUNT(*) AS total_families,
            ROUND(AVG(readiness_percentage), 1) AS avg_readiness,
            SUM(CASE WHEN exceptional_state='Completed' THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN readiness_band='On Track' THEN 1 ELSE 0 END) AS on_track,
            SUM(CASE WHEN readiness_band='Attention Required' THEN 1 ELSE 0 END) AS attention,
            SUM(CASE WHEN readiness_band='Delayed' THEN 1 ELSE 0 END) AS delayed,
            SUM(CASE WHEN readiness_band='Critical' THEN 1 ELSE 0 END) AS critical,
            SUM(CASE WHEN grievance_status IN ('Open','Reopened','Escalated') THEN 1 ELSE 0 END) AS open_grievances,
            SUM(CASE WHEN risk_level IN ('High','Critical') THEN 1 ELSE 0 END) AS at_risk,
            SUM(CASE WHEN is_vulnerable=1 THEN 1 ELSE 0 END) AS vulnerable_families
        FROM rr_families
        GROUP BY district
        ORDER BY avg_readiness DESC
    """).fetchall()]

    # Stage-wise distribution
    stage_distribution = [dict(r) for r in c.execute("""
        SELECT rr_stage AS stage, COUNT(*) AS count
        FROM rr_families
        GROUP BY rr_stage
        ORDER BY count DESC
    """).fetchall()]

    # Exceptional state distribution
    exceptional_distribution = [dict(r) for r in c.execute("""
        SELECT exceptional_state AS state, COUNT(*) AS count
        FROM rr_families
        WHERE exceptional_state IS NOT NULL
        GROUP BY exceptional_state
        ORDER BY count DESC
    """).fetchall()]

    # Compensation overview
    comp_overview = [dict(r) for r in c.execute("""
        SELECT compensation_status AS status, COUNT(*) AS count
        FROM rr_families
        GROUP BY compensation_status
        ORDER BY count DESC
    """).fetchall()]

    # Housing overview
    housing_overview = [dict(r) for r in c.execute("""
        SELECT housing_status AS status, COUNT(*) AS count
        FROM rr_families
        GROUP BY housing_status
        ORDER BY count DESC
    """).fetchall()]

    # Livelihood overview
    livelihood_overview = [dict(r) for r in c.execute("""
        SELECT livelihood_status AS status, COUNT(*) AS count
        FROM rr_families
        GROUP BY livelihood_status
        ORDER BY count DESC
    """).fetchall()]

    # Readiness band summary
    readiness_bands = [dict(r) for r in c.execute("""
        SELECT readiness_band AS band, COUNT(*) AS count
        FROM rr_families
        GROUP BY readiness_band
        ORDER BY CASE readiness_band
            WHEN 'Completed' THEN 1
            WHEN 'On Track' THEN 2
            WHEN 'Attention Required' THEN 3
            WHEN 'Delayed' THEN 4
            WHEN 'Critical' THEN 5
            ELSE 6 END
    """).fetchall()]

    # Top pending actions across districts
    top_pending_actions = [dict(r) for r in c.execute("""
        SELECT pending_action, COUNT(*) AS count
        FROM rr_families
        WHERE exceptional_state != 'Completed'
        GROUP BY pending_action
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()]

    c.close()
    return {
        "summary": {
            "total_families": total_families,
            "overall_readiness_percentage": round(avg_readiness, 1),
            "completed_rehabilitation": completed,
            "in_progress": in_progress,
            "delayed": delayed,
            "critical": critical,
            "blocked": blocked,
            "open_grievances": open_grievances,
            "escalated_grievances": escalated_grievances,
            "awaiting_verification": awaiting_verification,
            "awaiting_benefits": awaiting_benefits,
            "at_risk_families": at_risk,
            "vulnerable_families": vulnerable,
        },
        "district_comparison": district_breakdown,
        "stage_distribution": stage_distribution,
        "exceptional_state_distribution": exceptional_distribution,
        "compensation_overview": comp_overview,
        "housing_overview": housing_overview,
        "livelihood_overview": livelihood_overview,
        "readiness_bands": readiness_bands,
        "top_pending_actions": top_pending_actions,
    }


# ── District Dashboard ───────────────────────────────────────────────────────
@router.get("/district-dashboard")
def district_rr_dashboard(
    district: Optional[str] = None,
    authorization: str = Header(None),
):
    """
    District-level R&R dashboard: family-level records with filters.
    Role: district_authority, authority, admin, state_authority, field_officer
    """
    u = _require_auth(authorization, ("district_authority", "authority", "admin", "state_authority", "field_officer"))
    district = enforce_district_scope(u, district)
    c = conn()

    where = "WHERE 1=1"
    args = []
    if district and district.lower() != "all":
        where += " AND district=?"
        args.append(district)

    q = lambda sql, a=(): c.execute(sql, a).fetchone()[0]

    total_families = q(f"SELECT COUNT(*) FROM rr_families {where}", args)
    avg_readiness = c.execute(
        f"SELECT ROUND(AVG(readiness_percentage),1) FROM rr_families {where}", args
    ).fetchone()[0] or 0
    completed = q(f"SELECT COUNT(*) FROM rr_families {where} AND exceptional_state='Completed'", args)
    delayed = q(f"SELECT COUNT(*) FROM rr_families {where} AND readiness_band='Delayed'", args)
    critical_fam = q(f"SELECT COUNT(*) FROM rr_families {where} AND readiness_band='Critical'", args)
    open_griev = q(f"SELECT COUNT(*) FROM rr_families {where} AND grievance_status IN ('Open','Reopened','Escalated')", args)
    pending_verif = q(f"SELECT COUNT(*) FROM rr_families {where} AND verification_status IN ('Not Started','Scheduled','Pending')", args)
    at_risk = q(f"SELECT COUNT(*) FROM rr_families {where} AND risk_level IN ('High','Critical')", args)

    # Taluk overview
    taluk_overview = [dict(r) for r in c.execute(f"""
        SELECT taluk, COUNT(*) families, ROUND(AVG(readiness_percentage),1) avg_readiness,
               SUM(CASE WHEN exceptional_state='Completed' THEN 1 ELSE 0 END) completed,
               SUM(CASE WHEN risk_level IN ('High','Critical') THEN 1 ELSE 0 END) at_risk
        FROM rr_families {where}
        GROUP BY taluk ORDER BY taluk
    """, args).fetchall()]

    # Stage breakdown
    stage_breakdown = [dict(r) for r in c.execute(f"""
        SELECT rr_stage, COUNT(*) cnt
        FROM rr_families {where}
        GROUP BY rr_stage ORDER BY cnt DESC
    """, args).fetchall()]

    c.close()
    return {
        "summary": {
            "total_families": total_families,
            "avg_readiness": round(avg_readiness, 1),
            "completed": completed,
            "delayed": delayed,
            "critical": critical_fam,
            "open_grievances": open_griev,
            "pending_verification": pending_verif,
            "at_risk": at_risk,
        },
        "taluk_overview": taluk_overview,
        "stage_breakdown": stage_breakdown,
        "district": district or "All Districts",
    }


# ── Family List (with filters) ───────────────────────────────────────────────
@router.get("/families")
def list_rr_families(
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    rr_stage: Optional[str] = None,
    readiness_band: Optional[str] = None,
    risk_level: Optional[str] = None,
    compensation_status: Optional[str] = None,
    housing_status: Optional[str] = None,
    livelihood_status: Optional[str] = None,
    verification_status: Optional[str] = None,
    grievance_status: Optional[str] = None,
    is_vulnerable: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(None),
):
    """
    Paginated, filtered list of R&R families.
    Role: district_authority, state_authority, authority, admin, acquisition_officer, field_officer
    """
    u = _require_auth(authorization, ("district_authority", "state_authority", "authority", "admin", "acquisition_officer", "field_officer"))
    district = enforce_district_scope(u, district)
    c = conn()

    where = "WHERE 1=1"
    args = []
    filters = [
        ("district", district if district and district.lower() != "all" else None),
        ("taluk", taluk),
        ("rr_stage", rr_stage),
        ("readiness_band", readiness_band),
        ("risk_level", risk_level),
        ("compensation_status", compensation_status),
        ("housing_status", housing_status),
        ("livelihood_status", livelihood_status),
        ("verification_status", verification_status),
        ("grievance_status", grievance_status),
    ]
    for col, val in filters:
        if val:
            where += f" AND {col}=?"
            args.append(val)

    if is_vulnerable is not None:
        where += " AND is_vulnerable=?"
        args.append(is_vulnerable)

    if search:
        where += " AND (family_head LIKE ? OR family_id LIKE ? OR survey_no LIKE ? OR village LIKE ?)"
        s = f"%{search}%"
        args += [s, s, s, s]

    count_args = args[:]
    total = c.execute(f"SELECT COUNT(*) FROM rr_families {where}", count_args).fetchone()[0]

    args += [limit, offset]
    rows = [dict(r) for r in c.execute(f"""
        SELECT
            family_id, district, taluk, village, survey_no, project_id,
            family_head, members, impact_type, displacement_status, is_vulnerable,
            rr_stage, exceptional_state,
            compensation_status, housing_status, livelihood_status,
            verification_status, grievance_status,
            readiness_percentage, readiness_band, risk_level,
            compensation_entitled, compensation_paid,
            pending_action, identified_date, last_updated
        FROM rr_families {where}
        ORDER BY readiness_percentage ASC, risk_level DESC
        LIMIT ? OFFSET ?
    """, args).fetchall()]

    c.close()
    return {
        "total": total,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "families": rows,
    }


# ── Project Parcels Detail for R&R ──────────────────────────────────────────
@router.get("/projects/{project_id}/parcels")
def list_project_rr_parcels(
    project_id: str,
    authorization: str = Header(None),
):
    """
    District Authority / Field Officer: list all parcels linked to an R&R-enabled project,
    joined with household/family R&R status.
    """
    u = _require_auth(authorization, ("district_authority", "state_authority", "field_officer", "authority", "admin", "acquisition_officer"))
    c = conn()

    project = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not project:
        c.close()
        raise HTTPException(404, "Project not found")

    check_resource_district(u, project["district"], "Project")

    # Fetch all parcels for this project, joined with rr_families
    rows = [dict(r) for r in c.execute("""
        SELECT
            p.id AS parcel_id,
            p.record_id,
            p.survey_no,
            p.district,
            p.taluk,
            p.village,
            p.owner_reference,
            p.area,
            p.classification,
            p.acquisition_status,
            rf.family_id,
            rf.family_head,
            rf.members,
            rf.displacement_status,
            rf.compensation_status,
            rf.compensation_entitled,
            rf.compensation_paid,
            rf.housing_status,
            rf.livelihood_status,
            rf.rr_stage,
            rf.exceptional_state,
            rf.readiness_percentage,
            rf.readiness_band,
            rf.grievance_status,
            rf.verification_status,
            rf.risk_level,
            rf.pending_action,
            rf.verified_at
        FROM parcels p
        LEFT JOIN rr_families rf ON (rf.parcel_id = p.id OR (rf.survey_no = p.survey_no AND rf.district = p.district))
        WHERE p.project_id = ?
        ORDER BY p.id ASC
    """, (project_id,)).fetchall()]

    # Format address and standardized display values for each parcel
    for r in rows:
        r["full_address"] = f"Survey No. {r['survey_no']}, {r['village']} Village, {r['taluk']} Taluk, {r['district']} District"
        r["landowner"] = r["owner_reference"] or "Not Registered"
        r["affected_family"] = r["family_head"] or (f"Family {r['family_id']}" if r.get("family_id") else "Unassigned")
        r["rr_id"] = f"RR-{r['family_id']}" if r.get("family_id") else f"RR-P{r['parcel_id']}"
        r["project_name"] = project["project_name"]
        r["project_display"] = f"{project_id} - {project['project_name']}"
        r["priority"] = "High" if (r.get("risk_level") in ('Critical', 'High') or (r.get("readiness_percentage") or 0) < 50) else "Normal"
        r["rr_stage"] = r["rr_stage"] or "Impact Assessment"
        r["exceptional_state"] = r["exceptional_state"] or "Pending"
        r["readiness_percentage"] = r["readiness_percentage"] if r["readiness_percentage"] is not None else 0.0
        r["other_benefits_status"] = "Sanctioned" if r["readiness_percentage"] >= 70 else ("In Progress" if r["readiness_percentage"] >= 40 else "Pending")

    c.close()
    return {
        "project_id": project_id,
        "project_name": project["project_name"],
        "district": project["district"],
        "total_parcels": len(rows),
        "parcels": rows
    }


# ── Family Detail ────────────────────────────────────────────────────────────
@router.get("/families/{family_id}")
def get_rr_family(family_id: str, authorization: str = Header(None)):
    """
    Full detail for a single R&R family.
    Role: district_authority, state_authority, field_officer, authority, admin, acquisition_officer
    """
    u = _require_auth(authorization, ("district_authority", "state_authority", "field_officer", "authority", "admin", "acquisition_officer"))
    c = conn()

    family = c.execute("SELECT * FROM rr_families WHERE family_id=?", (family_id,)).fetchone()
    if not family:
        c.close()
        raise HTTPException(404, "Family not found")
    check_resource_district(u, family["district"], "R&R Family")

    d = dict(family)
    d["full_address"] = f"Survey No. {d['survey_no']}, {d['village']} Village, {d['taluk']} Taluk, {d['district']} District"
    d["landowner"] = d.get("family_head") or "Landowner"

    # Linked grievances
    d["grievances"] = [dict(r) for r in c.execute("""
        SELECT * FROM rr_grievances WHERE family_id=? ORDER BY created_at DESC
    """, (family_id,)).fetchall()]

    # Linked field verifications
    d["field_verifications"] = [dict(r) for r in c.execute("""
        SELECT * FROM rr_field_verifications WHERE family_id=? ORDER BY created_at DESC
    """, (family_id,)).fetchall()]

    # Linked parcel (if any)
    if d.get("parcel_id"):
        parcel = c.execute("""
            SELECT id, record_id, survey_no, village, taluk, district,
                   area, classification, owner_reference, acquisition_status
            FROM parcels WHERE id=?
        """, (d["parcel_id"],)).fetchone()
        if parcel:
            p_dict = dict(parcel)
            p_dict["full_address"] = f"Survey No. {p_dict['survey_no']}, {p_dict['village']} Village, {p_dict['taluk']} Taluk, {p_dict['district']} District"
            d["parcel"] = p_dict
            d["landowner"] = p_dict["owner_reference"] or d["landowner"]
        else:
            d["parcel"] = None
    else:
        d["parcel"] = None

    # Linked project
    if d.get("project_id"):
        project = c.execute("""
            SELECT project_id, project_name, project_type, current_stage, project_status
            FROM projects WHERE project_id=?
        """, (d["project_id"],)).fetchone()
        d["project"] = dict(project) if project else None
    else:
        d["project"] = None

    # Construct R&R Timeline based on progress
    timeline = [
        {"step": "Affected Family Identified", "date": d.get("identified_date") or "2025-01-10", "status": "Completed"},
        {"step": "Impact Assessment Completed", "date": d.get("survey_date") or "2025-02-15", "status": "Completed"},
        {"step": "Eligibility & Entitlement Determined", "date": "2025-03-01", "status": "Completed" if d.get("compensation_status") != "Not Started" else "In Progress"},
        {"step": "Compensation Award / Disbursement", "date": "2025-04-10", "status": "Completed" if d.get("compensation_status") in ("Fully Paid", "Approved") else ("In Progress" if d.get("compensation_status") == "Partially Paid" else "Pending")},
        {"step": "Housing & Resettlement Allocation", "date": "2025-05-20", "status": "Completed" if d.get("housing_status") in ("Ready", "Handed Over", "Not Required") else ("In Progress" if d.get("housing_status") == "Construction in Progress" else "Pending")},
        {"step": "Livelihood Assistance & Skill Grant", "date": "2025-06-15", "status": "Completed" if d.get("livelihood_status") in ("Completed", "Support Delivered") else ("In Progress" if d.get("livelihood_status") in ("Sanctioned", "Plan Prepared") else "Pending")},
        {"step": "Field Verification & Ground Audit", "date": "2025-07-01", "status": "Completed" if d.get("verification_status") == "Verified" else ("Action Required" if d.get("verification_status") in ("Failed", "Re-verification Required") else "Pending")},
        {"step": "District Approval & Full Rehabilitation", "date": "2025-08-01", "status": "Completed" if d.get("exceptional_state") == "Completed" else "Pending"}
    ]
    d["timeline"] = timeline

    c.close()
    return d


# ── Citizen Portal — My R&R Status ──────────────────────────────────────────
@router.get("/citizen/my-status")
def citizen_my_rr_status(
    family_id: Optional[str] = None,
    authorization: str = Header(None),
):
    """
    Citizen-safe view of their own R&R record.
    Returns only the citizen's own family — no internal risk scores or other families.
    Role: citizen (or provide family_id for demo)
    """
    c = conn()
    u = current_user(authorization)

    if u and u["role"] == "citizen":
        # Find family by linked parcel owner_reference
        family = c.execute("""
            SELECT rf.*
            FROM rr_families rf
            JOIN parcels p ON p.id = rf.parcel_id
            WHERE lower(p.owner_reference) = lower(?)
            LIMIT 1
        """, (u["email"],)).fetchone()

        if not family and family_id:
            # Fallback to explicit family_id for demo citizen
            family = c.execute(
                "SELECT * FROM rr_families WHERE family_id=?", (family_id,)
            ).fetchone()
    elif family_id:
        # Demo mode — no auth required if family_id provided
        family = c.execute(
            "SELECT * FROM rr_families WHERE family_id=?", (family_id,)
        ).fetchone()
    else:
        c.close()
        raise HTTPException(400, "Provide family_id or authenticate as citizen")

    if not family:
        c.close()
        if u and u["role"] == "citizen":
            return {"family_id": None, "rr_stage": "Not Applicable", "overall_status": "No R&R Required", "readiness_percentage": 100, "message": "No Rehabilitation & Resettlement claims currently filed for this parcel."}
        raise HTTPException(404, "R&R record not found")

    f = dict(family)

    # Grievances (citizen-safe)
    grievances = [dict(r) for r in c.execute("""
        SELECT grievance_type, description, status, raised_date, resolved_date
        FROM rr_grievances WHERE family_id=? ORDER BY created_at DESC
    """, (f["family_id"],)).fetchall()]

    c.close()

    # Return only citizen-safe fields — no risk_level, edge_case_tag, internal notes
    return {
        "family_id": f["family_id"],
        "family_head": f["family_head"],
        "members": f["members"],
        "district": f["district"],
        "taluk": f["taluk"],
        "village": f["village"],
        "survey_no": f["survey_no"],
        "impact_type": f["impact_type"],
        "displacement_status": f["displacement_status"],
        "rr_stage": f["rr_stage"],
        "overall_status": f["exceptional_state"],
        "readiness_percentage": f["readiness_percentage"],
        "readiness_band": f["readiness_band"],
        "compensation": {
            "status": f["compensation_status"],
            "entitled_amount": f["compensation_entitled"],
            "paid_amount": f["compensation_paid"],
            "balance": round((f["compensation_entitled"] or 0) - (f["compensation_paid"] or 0), 2),
        },
        "housing": {
            "status": f["housing_status"],
        },
        "livelihood_support": {
            "status": f["livelihood_status"],
        },
        "verification": {
            "status": f["verification_status"],
        },
        "grievances": grievances,
        "next_action": f["pending_action"],
        "identified_date": f["identified_date"],
        "last_updated": f["last_updated"],
    }


# ── Field Officer — R&R Verifications ───────────────────────────────────────
@router.get("/field-assignments")
def list_rr_field_assignments(
    district: Optional[str] = None,
    status: Optional[str] = None,
    authorization: str = Header(None),
):
    """
    Field officer: list R&R verification assignments.
    Role: field_officer, district_authority, authority, admin
    """
    u = _require_auth(authorization, ("field_officer", "district_authority", "authority", "admin"))
    district = enforce_district_scope(u, district)
    c = conn()

    where = "WHERE 1=1"
    args = []

    if u["role"] == "field_officer":
        officer_emails = [u["email"].lower()]
        if u["email"].lower() in ("field.coimbatore@tngov.in", "field@cbe.ac.in"):
            officer_emails.extend(["field.coimbatore@tngov.in", "field@cbe.ac.in"])
        officer_emails = list(dict.fromkeys(officer_emails))
        placeholders = ",".join("?" for _ in officer_emails)
        where += f" AND (lower(rv.officer_email) IN ({placeholders}) OR rf.parcel_id IN (SELECT parcel_id FROM field_assignments WHERE lower(officer_email) IN ({placeholders})))"
        args.extend(officer_emails)
        args.extend(officer_emails)
    elif district and district.lower() != "all":
        where += " AND (lower(rv.district)=lower(?) OR lower(rf.district)=lower(?))"
        args.extend([district, district])

    if status:
        where += " AND rv.status=?"
        args.append(status)

    rows = [dict(r) for r in c.execute(f"""
        SELECT
            rv.id AS verification_id, rv.family_id, rv.status AS verification_status,
            rv.verification_type, rv.assigned_date, rv.completed_date, rv.remarks, rv.evidence_notes,
            rf.family_head, rf.members, rf.district, rf.taluk, rf.village,
            rf.survey_no, rf.parcel_id, rf.project_id, pr.project_name,
            p.owner_reference AS landowner,
            rf.displacement_status, rf.verified_at,
            rf.rr_stage, rf.exceptional_state, rf.readiness_percentage, rf.readiness_band,
            rf.risk_level, rf.compensation_status, rf.housing_status, rf.livelihood_status,
            rf.grievance_status, rf.pending_action,
            CASE WHEN rf.risk_level IN ('Critical', 'High') THEN 'High' WHEN rf.readiness_percentage < 50 THEN 'High' ELSE 'Normal' END AS priority
        FROM rr_field_verifications rv
        JOIN rr_families rf ON rf.family_id = rv.family_id
        LEFT JOIN parcels p ON p.id = rf.parcel_id
        LEFT JOIN projects pr ON pr.project_id = rf.project_id
        {where}
        ORDER BY rv.created_at DESC
        LIMIT 250
    """, args).fetchall()]

    for r in rows:
        r["full_address"] = f"Survey No. {r['survey_no']}, {r['village']} Village, {r['taluk']} Taluk, {r['district']} District"
        r["landowner"] = r["landowner"] or r["family_head"]
        r["rr_id"] = f"RR-{r['family_id']}"
        r["project_display"] = f"{r['project_id'] or 'PRJ-GEN'} - {r.get('project_name') or 'Infrastructure'}"

    c.close()
    return {"count": len(rows), "assignments": rows}

@router.post("/families/{family_id}/verify")
def verify_rr_family(
    family_id: str,
    payload: dict,
    authorization: str = Header(None),
):
    """
    Field officer submits R&R family verification.
    Role: field_officer
    """
    u = _require_auth(authorization, ("field_officer", "district_authority", "authority", "admin"))
    c = conn()

    family = c.execute("SELECT * FROM rr_families WHERE family_id=?", (family_id,)).fetchone()
    if not family:
        c.close()
        raise HTTPException(404, "Family not found")
    check_resource_district(u, family["district"], "R&R Family")

    status = payload.get("status", "Verified")
    remarks = payload.get("remarks", "")
    evidence_notes = payload.get("evidence_notes", "")

    if status not in ("Verified", "Failed", "Re-verification Required"):
        c.close()
        raise HTTPException(422, "Invalid verification status")

    import datetime
    today = datetime.date.today().isoformat()

    existing = c.execute(
        "SELECT id FROM rr_field_verifications WHERE family_id=? ORDER BY id DESC LIMIT 1",
        (family_id,)
    ).fetchone()

    if existing:
        c.execute("""
            UPDATE rr_field_verifications
            SET status=?, remarks=?, evidence_notes=?, completed_date=?, officer_email=?
            WHERE id=?
        """, (status, remarks, evidence_notes, today, u["email"], existing["id"]))
    else:
        c.execute("""
            INSERT INTO rr_field_verifications(family_id, district, officer_email,
                verification_type, status, remarks, evidence_notes, assigned_date, completed_date)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (family_id, family["district"], u["email"],
              "Family R&R Verification", status, remarks, evidence_notes, today, today))

    # Optional updates from verification checklist
    house_condition = payload.get("house_condition")
    family_relocated = payload.get("family_relocated") # bool or 'Yes'/'No'
    comp_received = payload.get("compensation_received")
    housing_received = payload.get("housing_benefit_received")
    livelihood_received = payload.get("livelihood_assistance_received")
    other_benefit = payload.get("other_benefit_verified")
    has_grievance = payload.get("grievance_exists") # bool or 'Yes'/'No'

    new_verif = status
    comp = family["compensation_status"]
    housing = family["housing_status"]
    livelihood = family["livelihood_status"]
    grievance = family["grievance_status"]
    rr_stage = family["rr_stage"]
    exceptional = family["exceptional_state"]

    if comp_received in (True, "Yes", "yes", "true", "True"):
        comp = "Fully Paid"
    elif comp_received in (False, "No", "no", "false", "False") and comp == "Not Started":
        comp = "Not Started"

    if housing_received in (True, "Yes", "yes", "true", "True"):
        housing = "Handed Over"
    elif housing_received in (False, "No", "no", "false", "False") and housing in ("Pending", "Not Started"):
        housing = "Pending"

    if livelihood_received in (True, "Yes", "yes", "true", "True"):
        livelihood = "Completed"
    elif livelihood_received in (False, "No", "no", "false", "False") and livelihood in ("Not Assessed", "Pending"):
        livelihood = "Not Assessed"

    if has_grievance in (False, "No", "no", "false", "False"):
        grievance = "No Grievance"
    elif has_grievance in (True, "Yes", "yes", "true", "True"):
        grievance = "Open"

    # Auto-calculate readiness & band
    _cs = {"Not Started":0,"Processing":15,"Approved":25,"Partially Paid":60,"Fully Paid":100,"Payment Failed":5,"Disputed":15}
    _hs = {"Not Required":100,"Pending":5,"Approved":20,"Site Identified":35,"Construction in Progress":60,"Ready":85,"Handed Over":100,"Verification Failed":20}
    _ls = {"Not Assessed":0,"Assessment Pending":10,"Eligible":25,"Plan Prepared":40,"Sanctioned":55,"Training Pending":65,"Support Delivered":85,"Monitoring":90,"Completed":100}
    _vs = {"Not Started":0,"Scheduled":20,"Pending":35,"Verified":100,"Failed":0,"Re-verification Required":15}
    _gs = {"No Grievance":100,"Open":20,"Under Review":35,"Assigned":45,"Field Investigation":55,"Resolved":100,"Reopened":10,"Escalated":0}
    
    new_readiness = round(_cs.get(comp,0)*0.30 + _hs.get(housing,0)*0.25 + _ls.get(livelihood,0)*0.20 + _vs.get(new_verif,0)*0.15 + _gs.get(grievance,0)*0.10, 1)
    new_band = "Completed" if new_readiness>=90 else "On Track" if new_readiness>=75 else "Attention Required" if new_readiness>=50 else "Delayed" if new_readiness>=25 else "Critical"

    # Auto-advance R&R stage & exceptional state
    if status == "Verified":
        if housing in ("Ready", "Handed Over", "Not Required") and livelihood in ("Support Delivered", "Completed", "Monitoring") and comp in ("Approved", "Partially Paid", "Fully Paid"):
            rr_stage = "Completed"
            exceptional = "Completed"
        elif housing in ("Ready", "Handed Over") or livelihood in ("Completed", "Support Delivered"):
            rr_stage = "Verification"
            exceptional = "On Track"
        else:
            rr_stage = "Verification"
            exceptional = "On Track"
    elif status == "Failed":
        rr_stage = "Verification"
        exceptional = "Verification Failed"
    elif status == "Re-verification Required":
        rr_stage = "Verification"
        exceptional = "Re-verification Required"

    c.execute("""
        UPDATE rr_families
        SET verification_status=?, compensation_status=?, housing_status=?, livelihood_status=?,
            grievance_status=?, rr_stage=?, exceptional_state=?, readiness_percentage=?, readiness_band=?,
            remarks=COALESCE(?, remarks), verified_by=?, verified_at=?, last_updated=CURRENT_TIMESTAMP
        WHERE family_id=?
    """, (new_verif, comp, housing, livelihood, grievance, rr_stage, exceptional, new_readiness, new_band, remarks, u["email"], today, family_id))

    c.commit()
    c.close()

    audit(u["email"], "RR_FIELD_VERIFICATION", "rr_family", family_id,
          f"status={new_verif} | stage={rr_stage} | readiness={new_readiness}% | band={new_band} | remarks={remarks}")

    return {
        "message": f"R&R field verification successfully submitted as '{new_verif}'",
        "family_id": family_id,
        "verification_status": new_verif,
        "rr_stage": rr_stage,
        "exceptional_state": exceptional,
        "compensation_status": comp,
        "housing_status": housing,
        "livelihood_status": livelihood,
        "grievance_status": grievance,
        "readiness_percentage": new_readiness,
        "readiness_band": new_band,
        "officer": u["email"],
        "timestamp": today,
    }


# ── Upload Evidence / Documentation ──────────────────────────────────────────
@router.post("/families/{family_id}/evidence")
async def upload_rr_evidence(
    family_id: str,
    file: Optional[UploadFile] = File(None),
    description: Optional[str] = Form(None),
    authorization: str = Header(None),
):
    """
    Upload field evidence photo or document for an R&R family.
    Role: field_officer, district_authority, authority, admin
    """
    u = _require_auth(authorization, ("field_officer", "district_authority", "authority", "admin"))
    c = conn()

    family = c.execute("SELECT * FROM rr_families WHERE family_id=?", (family_id,)).fetchone()
    if not family:
        c.close()
        raise HTTPException(404, "Family not found")
    check_resource_district(u, family["district"], "R&R Family")

    today = datetime.date.today().isoformat()
    evidence_text = description or "Field verification photo / ground evidence document"
    filename = ""
    file_path = ""

    if file and file.filename:
        upload_dir = os.path.join(os.getcwd(), "UPLOADS")
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._-")
        filename = f"rr_{family_id}_{int(datetime.datetime.utcnow().timestamp())}_{safe_name}"
        dest = os.path.join(upload_dir, filename)
        content = await file.read()
        with open(dest, "wb") as f_out:
            f_out.write(content)
        file_hash = hashlib.sha256(content).hexdigest()
        file_path = f"/uploads/{filename}"

        # Register in documents table
        doc_id = f"DOC-RR-{family_id}-{int(datetime.datetime.utcnow().timestamp())}"
        ext = os.path.splitext(file.filename or "")[1].lstrip(".").lower() or "bin"
        c.execute("""
            INSERT INTO documents (document_id, project_id, parcel_id, document_type, document_name, path, format, uploaded_by, verification_status, sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            family["project_id"],
            family["parcel_id"],
            "R&R Field Evidence",
            file.filename,
            file_path,
            ext,
            u["email"],
            "Verified",
            file_hash
        ))

    entry_str = f"[{today}] {u['email']}: {evidence_text}"
    if filename:
        entry_str += f" (File: {filename})"

    existing = c.execute(
        "SELECT id, evidence_notes FROM rr_field_verifications WHERE family_id=? ORDER BY id DESC LIMIT 1",
        (family_id,)
    ).fetchone()

    if existing:
        curr = existing["evidence_notes"] or ""
        updated_notes = (curr + "\n" + entry_str).strip()
        c.execute("UPDATE rr_field_verifications SET evidence_notes=? WHERE id=?", (updated_notes, existing["id"]))
    else:
        c.execute("""
            INSERT INTO rr_field_verifications (family_id, district, officer_email, verification_type, status, remarks, evidence_notes, assigned_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (family_id, family["district"], u["email"], "Field Verification", "In Progress", "Evidence Uploaded", entry_str, today))

    c.commit()
    c.close()

    audit(u["email"], "RR_EVIDENCE_UPLOAD", "rr_family", family_id, entry_str)

    return {
        "message": "Evidence uploaded successfully",
        "family_id": family_id,
        "file_path": file_path,
        "evidence_entry": entry_str
    }



# ── Internal helpers exposed for reuse ───────────────────────────────────────
COMP_SCORES = {
    "Not Started": 0, "Processing": 15, "Approved": 25,
    "Partially Paid": 60, "Fully Paid": 100, "Payment Failed": 5, "Disputed": 15
}
HOUSING_SCORES = {
    "Not Required": 100, "Pending": 5, "Approved": 20, "Site Identified": 35,
    "Construction in Progress": 60, "Ready": 85, "Handed Over": 100, "Verification Failed": 20
}
LIVELIHOOD_SCORES = {
    "Not Assessed": 0, "Assessment Pending": 10, "Eligible": 25, "Plan Prepared": 40,
    "Sanctioned": 55, "Training Pending": 65, "Support Delivered": 85,
    "Monitoring": 90, "Completed": 100
}
VERIF_SCORES = {
    "Not Started": 0, "Scheduled": 20, "Pending": 35,
    "Verified": 100, "Failed": 0, "Re-verification Required": 15
}
GRIEVANCE_SCORES = {
    "No Grievance": 100, "Open": 20, "Under Review": 35, "Assigned": 45,
    "Field Investigation": 55, "Resolved": 100, "Reopened": 10, "Escalated": 0
}


def _recalc_readiness(comp, housing, livelihood, verif, grievance):
    score = (
        COMP_SCORES.get(comp, 0) * 0.30 +
        HOUSING_SCORES.get(housing, 0) * 0.25 +
        LIVELIHOOD_SCORES.get(livelihood, 0) * 0.20 +
        VERIF_SCORES.get(verif, 0) * 0.15 +
        GRIEVANCE_SCORES.get(grievance, 0) * 0.10
    )
    return round(score, 1)


def _readiness_band(pct):
    if pct >= 90:
        return "Completed"
    elif pct >= 75:
        return "On Track"
    elif pct >= 50:
        return "Attention Required"
    elif pct >= 25:
        return "Delayed"
    else:
        return "Critical"

# ── Analytics: Readiness Trend (for charts) ──────────────────────────────────
@router.get("/analytics/readiness")
def rr_readiness_analytics(
    district: Optional[str] = None,
    authorization: str = Header(None),
):
    """Readiness distribution and band breakdown for charts."""
    u = _require_auth(authorization, ("district_authority", "state_authority", "authority", "admin", "acquisition_officer", "field_officer"))
    district = enforce_district_scope(u, district)
    c = conn()

    where = "WHERE 1=1"
    args = []
    if district and district.lower() != "all":
        where += " AND district=?"
        args.append(district)

    bands = [dict(r) for r in c.execute(f"""
        SELECT readiness_band AS band, COUNT(*) AS count,
               ROUND(AVG(readiness_percentage),1) AS avg_readiness
        FROM rr_families {where}
        GROUP BY readiness_band
        ORDER BY CASE readiness_band
            WHEN 'Completed' THEN 1 WHEN 'On Track' THEN 2
            WHEN 'Attention Required' THEN 3 WHEN 'Delayed' THEN 4
            WHEN 'Critical' THEN 5 ELSE 6 END
    """, args).fetchall()]

    stages = [dict(r) for r in c.execute(f"""
        SELECT rr_stage AS stage, COUNT(*) AS count,
               ROUND(AVG(readiness_percentage),1) AS avg_readiness
        FROM rr_families {where}
        GROUP BY rr_stage
        ORDER BY count DESC
    """, args).fetchall()]

    risk = [dict(r) for r in c.execute(f"""
        SELECT risk_level, COUNT(*) AS count
        FROM rr_families {where}
        GROUP BY risk_level
        ORDER BY CASE risk_level WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END
    """, args).fetchall()]

    grievance_dist = [dict(r) for r in c.execute(f"""
        SELECT grievance_status AS status, COUNT(*) AS count
        FROM rr_families {where}
        GROUP BY grievance_status
        ORDER BY count DESC
    """, args).fetchall()]

    comp_dist = [dict(r) for r in c.execute(f"""
        SELECT compensation_status AS status, COUNT(*) AS count
        FROM rr_families {where}
        GROUP BY compensation_status
        ORDER BY count DESC
    """, args).fetchall()]

    housing_dist = [dict(r) for r in c.execute(f"""
        SELECT housing_status AS status, COUNT(*) AS count
        FROM rr_families {where}
        GROUP BY housing_status
        ORDER BY count DESC
    """, args).fetchall()]

    livelihood_dist = [dict(r) for r in c.execute(f"""
        SELECT livelihood_status AS status, COUNT(*) AS count
        FROM rr_families {where}
        GROUP BY livelihood_status
        ORDER BY count DESC
    """, args).fetchall()]

    c.close()
    return {
        "readiness_bands": bands,
        "stage_distribution": stages,
        "risk_distribution": risk,
        "grievance_distribution": grievance_dist,
        "compensation_distribution": comp_dist,
        "housing_distribution": housing_dist,
        "livelihood_distribution": livelihood_dist,
    }


# ── Ensure extended columns exist (idempotent, safe migration) ───────────────
def _ensure_rr_columns():
    """Adds genuinely missing columns to rr_families without affecting existing data."""
    NEW_COLS = [
        # Affected family details
        ("family_members_json", "TEXT"),
        ("vulnerable_members", "TEXT"),
        ("special_assistance", "TEXT"),
        ("family_affected_status", "TEXT"),
        # Displacement
        ("displacement_required", "TEXT DEFAULT 'Yes'"),
        ("current_residence_status", "TEXT"),
        ("relocation_completed", "TEXT DEFAULT 'No'"),
        ("new_location", "TEXT"),
        ("relocation_date", "TEXT"),
        ("relocation_type", "TEXT"),
        ("pending_relocation_issues", "TEXT"),
        # Compensation verification
        ("comp_eligible", "TEXT DEFAULT 'Yes'"),
        ("comp_sanctioned", "TEXT DEFAULT 'Yes'"),
        ("comp_amount_received", "REAL DEFAULT 0"),
        ("comp_payment_date", "TEXT"),
        ("comp_pending_amount", "REAL DEFAULT 0"),
        ("comp_payment_verified", "TEXT DEFAULT 'No'"),
        ("comp_payment_issue", "TEXT"),
        # Housing
        ("housing_entitlement", "TEXT"),
        ("housing_sanctioned", "TEXT DEFAULT 'Yes'"),
        ("housing_received", "TEXT DEFAULT 'No'"),
        ("house_construction_status", "TEXT"),
        ("new_house_provided", "TEXT DEFAULT 'No'"),
        ("housing_completion_status", "TEXT"),
        ("housing_issue", "TEXT"),
        # Livelihood
        ("existing_occupation", "TEXT"),
        ("livelihood_affected", "TEXT DEFAULT 'Yes'"),
        ("livelihood_eligible", "TEXT DEFAULT 'Yes'"),
        ("livelihood_sanctioned_bool", "TEXT DEFAULT 'No'"),
        ("livelihood_received_bool", "TEXT DEFAULT 'No'"),
        ("assistance_type", "TEXT"),
        ("alternative_livelihood", "TEXT"),
        ("training_provided", "TEXT DEFAULT 'No'"),
        ("employment_support", "TEXT"),
        ("livelihood_restoration_status", "TEXT"),
        ("pending_livelihood_support", "TEXT"),
        ("livelihood_issue", "TEXT"),
        # Other benefits
        ("benefit_transportation", "TEXT DEFAULT 'Pending'"),
        ("benefit_subsistence", "TEXT DEFAULT 'Pending'"),
        ("benefit_education", "TEXT DEFAULT 'Pending'"),
        ("benefit_medical", "TEXT DEFAULT 'Pending'"),
        ("benefit_skill_development", "TEXT DEFAULT 'Pending'"),
        ("benefit_other_statutory", "TEXT"),
        ("benefit_received_status", "TEXT"),
        ("pending_benefits", "TEXT"),
        ("benefits_remarks", "TEXT"),
        # Grievance verification
        ("field_grievance_id", "TEXT"),
        ("field_grievance_category", "TEXT"),
        ("field_grievance_description", "TEXT"),
        ("field_grievance_status", "TEXT"),
        ("officer_observation", "TEXT"),
        ("resolution_required", "TEXT DEFAULT 'No'"),
        # Evidence / site visit
        ("site_visit_date", "TEXT"),
        ("house_observations", "TEXT"),
        ("evidence_description", "TEXT"),
        ("officer_remarks", "TEXT"),
        # Section completion flags
        ("sec_parcel_done", "INTEGER DEFAULT 0"),
        ("sec_family_done", "INTEGER DEFAULT 0"),
        ("sec_displacement_done", "INTEGER DEFAULT 0"),
        ("sec_compensation_done", "INTEGER DEFAULT 0"),
        ("sec_housing_done", "INTEGER DEFAULT 0"),
        ("sec_livelihood_done", "INTEGER DEFAULT 0"),
        ("sec_other_benefits_done", "INTEGER DEFAULT 0"),
        ("sec_grievance_done", "INTEGER DEFAULT 0"),
        ("sec_evidence_done", "INTEGER DEFAULT 0"),
        ("final_verification_status", "TEXT"),
        ("field_readiness_percentage", "REAL DEFAULT 0"),
    ]
    c = conn()
    existing = {r[1] for r in c.execute("PRAGMA table_info(rr_families)").fetchall()}
    for col, col_def in NEW_COLS:
        if col not in existing:
            try:
                c.execute(f"ALTER TABLE rr_families ADD COLUMN {col} {col_def}")
            except Exception:
                pass
    c.commit()
    c.close()


try:
    _ensure_rr_columns()
except Exception:
    pass


# ── Full R&R Field Verification Endpoint ─────────────────────────────────────
@router.post("/families/{family_id}/full-verify")
def full_verify_rr_family(
    family_id: str,
    payload: dict,
    authorization: str = Header(None),
):
    """
    Complete ground-level R&R data capture and verification by Field Officer.
    Verifies RBAC: field_officer, district scope.
    Updates rr_families, rr_field_verifications, recalculates readiness_percentage,
    records audit log, and returns updated family object.
    """
    u = _require_auth(authorization, ("field_officer", "district_authority", "authority", "admin"))
    c = conn()

    raw_family = c.execute("SELECT * FROM rr_families WHERE family_id=?", (family_id,)).fetchone()
    if not raw_family:
        c.close()
        raise HTTPException(404, "R&R Family not found")
    family = dict(raw_family)

    # Scope enforcement
    check_resource_district(u, family["district"], "R&R Family")
    if u["role"] == "field_officer" and u.get("district_scope"):
        check_resource_district(u, family["district"], "Field Verification")

    today = datetime.date.today().isoformat()
    final_status = payload.get("final_status", "Partially Verified")
    valid_statuses = ("Verified", "Partially Verified", "Re-verification Required", "Blocked")
    if final_status not in valid_statuses:
        c.close()
        raise HTTPException(422, f"final_status must be one of: {valid_statuses}")

    # Section completion booleans
    sec_parcel = int(bool(payload.get("sec_parcel_done", False)))
    sec_family = int(bool(payload.get("sec_family_done", False)))
    sec_displacement = int(bool(payload.get("sec_displacement_done", False)))
    sec_compensation = int(bool(payload.get("sec_compensation_done", False)))
    sec_housing = int(bool(payload.get("sec_housing_done", False)))
    sec_livelihood = int(bool(payload.get("sec_livelihood_done", False)))
    sec_other_benefits = int(bool(payload.get("sec_other_benefits_done", False)))
    sec_grievance = int(bool(payload.get("sec_grievance_done", False)))
    sec_evidence = int(bool(payload.get("sec_evidence_done", False)))

    sections_done = sec_parcel + sec_family + sec_displacement + sec_compensation + sec_housing + sec_livelihood + sec_other_benefits + sec_grievance + sec_evidence
    field_readiness = round((sections_done / 9.0) * 100, 1)

    # Status propagation
    comp_status = family["compensation_status"]
    if payload.get("comp_paid_bool") in (True, "Yes", "yes", "true", "True", 1):
        comp_status = "Fully Paid"
    elif payload.get("comp_sanctioned") in (True, "Yes", "yes", "true", "True", 1) and comp_status in ("Not Started", "Processing"):
        comp_status = "Approved"

    housing_status = family["housing_status"]
    if payload.get("housing_received") in (True, "Yes", "yes", "true", "True", 1):
        housing_status = "Handed Over"
    elif payload.get("housing_sanctioned") in (True, "Yes", "yes", "true", "True", 1) and housing_status == "Pending":
        housing_status = "Approved"

    livelihood_status = family["livelihood_status"]
    restoration_status = payload.get("livelihood_restoration_status", "")
    if restoration_status and restoration_status in LIVELIHOOD_SCORES:
        livelihood_status = restoration_status
    elif payload.get("livelihood_received_bool") in (True, "Yes", "yes", "true", "True", 1):
        livelihood_status = "Support Delivered"
    elif payload.get("livelihood_sanctioned_bool") in (True, "Yes", "yes", "true", "True", 1) and livelihood_status in ("Not Assessed", "Assessment Pending"):
        livelihood_status = "Sanctioned"

    grievance_status = family["grievance_status"]
    if payload.get("grievance_exists") in (False, "No", "no", "false", "False", 0):
        grievance_status = "No Grievance"
    elif payload.get("grievance_exists") in (True, "Yes", "yes", "true", "True", 1):
        grievance_status = "Open" if grievance_status == "No Grievance" else grievance_status

    displacement_status = family["displacement_status"]
    if payload.get("family_relocated") in (True, "Yes", "yes", "true", "True", 1) or payload.get("relocation_completed") in (True, "Yes", "yes", "true", "True", 1):
        displacement_status = "Relocated"
    elif payload.get("displacement_required") in (False, "No", "no", "false", "False", 0):
        displacement_status = "Not Required"

    # Dynamic readiness percentage recalculation
    formula_readiness = _recalc_readiness(comp_status, housing_status, livelihood_status, final_status if final_status == "Verified" else "Pending", grievance_status)
    # Blend: 65% weighted domain progress + 35% ground verification sections completed
    blended_readiness = round(formula_readiness * 0.65 + field_readiness * 0.35, 1)
    new_band = _readiness_band(blended_readiness)

    # R&R Stage and Exceptional State
    rr_stage = family["rr_stage"]
    exceptional = family["exceptional_state"]
    if final_status == "Verified":
        if blended_readiness >= 90:
            rr_stage = "Completed"
            exceptional = "Completed"
        else:
            rr_stage = "Verification"
            exceptional = "On Track"
    elif final_status == "Re-verification Required":
        rr_stage = "Verification"
        exceptional = "Re-verification Required"
    elif final_status == "Blocked":
        exceptional = "Blocked"
    elif final_status == "Partially Verified":
        rr_stage = "Verification"
        exceptional = exceptional if exceptional and exceptional != "Completed" else "In Progress"

    # Only save verified_by & verified_at when officially submitted as Verified/Re-verification/Blocked, or keep prior
    verified_by = u["email"] if final_status in ("Verified", "Re-verification Required", "Blocked") else family["verified_by"]
    verified_at = today if final_status in ("Verified", "Re-verification Required", "Blocked") else family["verified_at"]

    officer_remarks = payload.get("officer_remarks", "")
    evidence_desc = payload.get("evidence_description", "")

    # Execute atomic UPDATE on rr_families
    c.execute("""
        UPDATE rr_families SET
            verification_status=?, compensation_status=?, housing_status=?,
            livelihood_status=?, grievance_status=?, displacement_status=?,
            rr_stage=?, exceptional_state=?,
            readiness_percentage=?, readiness_band=?,
            verified_by=?, verified_at=?, last_updated=CURRENT_TIMESTAMP,
            remarks=COALESCE(NULLIF(?, ''), remarks),
            family_members_json=?, vulnerable_members=?, special_assistance=?, family_affected_status=?,
            displacement_required=?, current_residence_status=?, relocation_completed=?,
            new_location=?, relocation_date=?, relocation_type=?, pending_relocation_issues=?,
            comp_eligible=?, comp_sanctioned=?, comp_amount_received=?,
            comp_payment_date=?, comp_pending_amount=?, comp_payment_verified=?, comp_payment_issue=?,
            housing_entitlement=?, housing_sanctioned=?, housing_received=?,
            house_construction_status=?, new_house_provided=?, housing_completion_status=?, housing_issue=?,
            existing_occupation=?, livelihood_affected=?, livelihood_eligible=?,
            livelihood_sanctioned_bool=?, livelihood_received_bool=?, assistance_type=?,
            alternative_livelihood=?, training_provided=?, employment_support=?,
            livelihood_restoration_status=?, pending_livelihood_support=?, livelihood_issue=?,
            benefit_transportation=?, benefit_subsistence=?, benefit_education=?,
            benefit_medical=?, benefit_skill_development=?, benefit_other_statutory=?,
            benefit_received_status=?, pending_benefits=?, benefits_remarks=?,
            field_grievance_id=?, field_grievance_category=?, field_grievance_description=?,
            field_grievance_status=?, officer_observation=?, resolution_required=?,
            site_visit_date=?, house_observations=?, evidence_description=?, officer_remarks=?,
            sec_parcel_done=?, sec_family_done=?, sec_displacement_done=?,
            sec_compensation_done=?, sec_housing_done=?, sec_livelihood_done=?,
            sec_other_benefits_done=?, sec_grievance_done=?, sec_evidence_done=?,
            final_verification_status=?, field_readiness_percentage=?
        WHERE family_id=?
    """, (
        final_status, comp_status, housing_status,
        livelihood_status, grievance_status, displacement_status,
        rr_stage, exceptional,
        blended_readiness, new_band,
        verified_by, verified_at,
        officer_remarks,
        str(payload.get("family_members_json") or ""),
        str(payload.get("vulnerable_members") or ""),
        str(payload.get("special_assistance") or ""),
        str(payload.get("family_affected_status") or ""),
        str(payload.get("displacement_required") or "Yes"),
        str(payload.get("current_residence_status") or ""),
        str(payload.get("relocation_completed") or "No"),
        str(payload.get("new_location") or ""),
        str(payload.get("relocation_date") or ""),
        str(payload.get("relocation_type") or "Permanent"),
        str(payload.get("pending_relocation_issues") or ""),
        str(payload.get("comp_eligible") or "Yes"),
        str(payload.get("comp_sanctioned") or "Yes"),
        float(payload.get("comp_amount_received") or 0),
        str(payload.get("comp_payment_date") or ""),
        float(payload.get("comp_pending_amount") or 0),
        str(payload.get("comp_payment_verified") or "No"),
        str(payload.get("comp_payment_issue") or ""),
        str(payload.get("housing_entitlement") or ""),
        str(payload.get("housing_sanctioned") or "Yes"),
        str(payload.get("housing_received") or "No"),
        str(payload.get("house_construction_status") or ""),
        str(payload.get("new_house_provided") or "No"),
        str(payload.get("housing_completion_status") or ""),
        str(payload.get("housing_issue") or ""),
        str(payload.get("existing_occupation") or ""),
        str(payload.get("livelihood_affected") or "Yes"),
        str(payload.get("livelihood_eligible") or "Yes"),
        str(payload.get("livelihood_sanctioned_bool") or "No"),
        str(payload.get("livelihood_received_bool") or "No"),
        str(payload.get("assistance_type") or ""),
        str(payload.get("alternative_livelihood") or ""),
        str(payload.get("training_provided") or "No"),
        str(payload.get("employment_support") or ""),
        str(payload.get("livelihood_restoration_status") or livelihood_status),
        str(payload.get("pending_livelihood_support") or ""),
        str(payload.get("livelihood_issue") or ""),
        str(payload.get("benefit_transportation") or "Pending"),
        str(payload.get("benefit_subsistence") or "Pending"),
        str(payload.get("benefit_education") or "Pending"),
        str(payload.get("benefit_medical") or "Pending"),
        str(payload.get("benefit_skill_development") or "Pending"),
        str(payload.get("benefit_other_statutory") or ""),
        str(payload.get("benefit_received_status") or ""),
        str(payload.get("pending_benefits") or ""),
        str(payload.get("benefits_remarks") or ""),
        str(payload.get("field_grievance_id") or ""),
        str(payload.get("field_grievance_category") or ""),
        str(payload.get("field_grievance_description") or ""),
        str(payload.get("field_grievance_status") or ""),
        str(payload.get("officer_observation") or ""),
        str(payload.get("resolution_required") or "No"),
        str(payload.get("site_visit_date") or today),
        str(payload.get("house_observations") or ""),
        evidence_desc,
        officer_remarks,
        sec_parcel, sec_family, sec_displacement,
        sec_compensation, sec_housing, sec_livelihood,
        sec_other_benefits, sec_grievance, sec_evidence,
        final_status, field_readiness,
        family_id,
    ))

    # Update or insert into existing rr_field_verifications table
    existing_verif = c.execute(
        "SELECT id FROM rr_field_verifications WHERE family_id=? ORDER BY id DESC LIMIT 1",
        (family_id,)
    ).fetchone()
    if existing_verif:
        c.execute("""
            UPDATE rr_field_verifications
            SET status=?, remarks=?, evidence_notes=?, completed_date=?, officer_email=?
            WHERE id=?
        """, (final_status, officer_remarks, evidence_desc, today, u["email"], existing_verif["id"]))
    else:
        c.execute("""
            INSERT INTO rr_field_verifications
                (family_id, district, officer_email, verification_type, status, remarks, evidence_notes, assigned_date, completed_date)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (family_id, family["district"], u["email"],
              "Ground R&R Verification", final_status, officer_remarks, evidence_desc, today, today))

    # Sync field_assignments if parcel_id linked
    if family.get("parcel_id"):
        c.execute("""
            UPDATE field_assignments
            SET status=?
            WHERE parcel_id=? AND (officer_email=? OR 1=1)
        """, (final_status if final_status == "Verified" else "In Progress", family["parcel_id"], u["email"]))

    c.commit()

    # Re-fetch updated family
    updated_family = dict(c.execute("SELECT * FROM rr_families WHERE family_id=?", (family_id,)).fetchone())
    c.close()

    # Audit record
    audit(
        u["email"],
        "RR_FULL_FIELD_VERIFICATION",
        "rr_family",
        family_id,
        f"parcel_id={family.get('parcel_id')} | project_id={family.get('project_id')} | "
        f"status={final_status} | readiness={blended_readiness}% | sections={sections_done}/9 | "
        f"livelihood={livelihood_status} | remarks={officer_remarks[:50]}"
    )

    return {
        "message": f"R&R field verification saved successfully as '{final_status}'",
        "family_id": family_id,
        "parcel_id": family.get("parcel_id"),
        "project_id": family.get("project_id"),
        "final_status": final_status,
        "verification_status": final_status,
        "rr_stage": rr_stage,
        "exceptional_state": exceptional,
        "compensation_status": comp_status,
        "housing_status": housing_status,
        "livelihood_status": livelihood_status,
        "grievance_status": grievance_status,
        "displacement_status": displacement_status,
        "readiness_percentage": blended_readiness,
        "readiness_band": new_band,
        "field_readiness_percentage": field_readiness,
        "sections_completed": sections_done,
        "sections_total": 9,
        "verified_by": verified_by,
        "verified_at": verified_at,
        "officer": u["email"],
        "family": updated_family,
    }

