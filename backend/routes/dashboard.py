from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from backend.core import conn, current_user, enforce_district_scope
router = APIRouter()

def get_base_metrics(c, district: Optional[str] = None):
    has_dist = district and district.strip().lower() not in ("all", "all districts")
    p_where = f"WHERE lower(district) = '{district.strip().lower()}'" if has_dist else ""
    pa_where = f"WHERE lower(district) = '{district.strip().lower()}'" if has_dist else ""
    comp_where = f"WHERE lower(p.district) = '{district.strip().lower()}'" if has_dist else ""
    g_where = f"JOIN parcels p ON p.id = g.parcel_id WHERE lower(p.district) = '{district.strip().lower()}'" if has_dist else ""
    
    q = lambda sql: c.execute(sql).fetchone()[0] or 0
    
    return {
        "total_projects": q(f"SELECT count(*) FROM projects {p_where}"),
        "active_projects": q(f"SELECT count(*) FROM projects {p_where} {'AND' if p_where else 'WHERE'} project_status IN ('Active','In Progress')"),
        "completed_projects": q(f"SELECT count(*) FROM projects {p_where} {'AND' if p_where else 'WHERE'} project_status='Completed'"),
        "delayed_projects": q(f"SELECT count(*) FROM projects {p_where} {'AND' if p_where else 'WHERE'} project_status='Delayed'"),
        "total_parcels": q(f"SELECT count(*) FROM parcels {pa_where}"),
        "affected_families": q(f"SELECT COALESCE(sum(affected_families),0) FROM projects {p_where}"),
        "total_compensation": q(f"SELECT sum(c.assessed_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "approved_compensation": q(f"SELECT sum(c.approved_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "paid_compensation": q(f"SELECT sum(c.paid_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "pending_compensation": q(f"SELECT sum(c.pending_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "legal_disputes": q(f"SELECT count(*) FROM grievances g {g_where} {'AND' if g_where else 'WHERE'} g.status != 'Resolved'"),
        "sla_breaches": q(f"SELECT count(DISTINCT m.project_id) FROM project_milestones m JOIN projects pr ON pr.project_id=m.project_id {('WHERE lower(pr.district)=' + repr(district.strip().lower()) + ' AND') if has_dist else 'WHERE'} m.delay_days > 0"),
        "ocr_verification_pending": q(f"SELECT count(*) FROM documents d {'JOIN parcels pa ON pa.id=d.parcel_id WHERE lower(pa.district)=' + repr(district.strip().lower()) + ' AND' if has_dist else 'WHERE'} d.ocr_status='Verification Required'"),
        "selected_district": district if has_dist else "All Districts"
    }

@router.get("/")
def dashboard(district: Optional[str] = None, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")
    district = enforce_district_scope(u, district)
    c = conn()
    d = get_base_metrics(c, district)
    
    has_dist = district and district.strip().lower() not in ("all", "all districts")
    p_where = f"WHERE lower(district) = '{district.strip().lower()}'" if has_dist else ""
    pa_where = f"WHERE lower(district) = '{district.strip().lower()}'" if has_dist else ""
    
    d["risk_distribution"] = [dict(r) for r in c.execute(f"SELECT COALESCE(risk_category,'UNKNOWN') category, count(*) count FROM parcels {pa_where} GROUP BY risk_category").fetchall()]
    d["projects_by_stage"] = [dict(r) for r in c.execute(f"SELECT current_stage stage, count(*) count FROM projects {p_where} GROUP BY current_stage").fetchall()]
    d["delay_causes"] = [dict(r) for r in c.execute(f"SELECT delay_reason reason, count(*) count FROM (SELECT 'Compensation' delay_reason FROM parcels {pa_where} {'AND' if pa_where else 'WHERE'} compensation_pending>0 UNION ALL SELECT 'Legal' FROM parcels {pa_where} {'AND' if pa_where else 'WHERE'} legal_disputes>0 UNION ALL SELECT 'Documentation' FROM parcels {pa_where} {'AND' if pa_where else 'WHERE'} documentation_pending>0 UNION ALL SELECT 'Approval' FROM parcels {pa_where} {'AND' if pa_where else 'WHERE'} approval_pending>0) GROUP BY delay_reason").fetchall()]
    d["high_risk_projects"] = sum(x["count"] for x in d["risk_distribution"] if x["category"] in ("HIGH","CRITICAL"))
    d["critical_projects"] = sum(x["count"] for x in d["risk_distribution"] if x["category"] == "CRITICAL")
    
    m_join = f"JOIN projects pr ON pr.project_id=m.project_id WHERE lower(pr.district)='{district.strip().lower()}' AND" if has_dist else "WHERE"
    priority_actions = [dict(r) for r in c.execute(f"SELECT m.stage as action, m.delay_days as severity, m.project_id FROM project_milestones m {m_join} m.delay_days > 15 ORDER BY m.delay_days DESC LIMIT 5").fetchall()]
    d["priority_actions"] = [{"task": f"SLA Breached ({p['severity']} days) at {p['action']}", "project_id": p["project_id"]} for p in priority_actions]
    
    workload = [dict(r) for r in c.execute("SELECT assigned_to, count(*) as count FROM alerts WHERE status='Open' AND assigned_to IS NOT NULL GROUP BY assigned_to").fetchall()]
    d["officer_workload"] = workload
    c.close()
    return d

STATE_DISTRICTS = {
    "Tamil Nadu": ["Coimbatore", "Tiruppur", "Erode", "Salem", "Namakkal"],
    "Kerala": ["Palakkad", "Ernakulam", "Thrissur", "Thiruvananthapuram"]
}

@router.get("/state")
def state_dashboard(state: Optional[str] = "Tamil Nadu", district: Optional[str] = None, authorization: str = Header(None)):
    from backend.core import enforce_state_scope
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")
    state = enforce_state_scope(u, state or "Tamil Nadu")
    if district:
        district = enforce_district_scope(u, district)
    
    valid_districts = STATE_DISTRICTS.get(state, STATE_DISTRICTS["Tamil Nadu"])
    dist_placeholders = ",".join(f"'{d}'" for d in valid_districts)
    
    c = conn()
    
    if district and district in valid_districts:
        p_where = f"WHERE district = '{district}'"
        pa_where = f"WHERE district = '{district}'"
        comp_where = f"WHERE p.district = '{district}'"
        g_where = f"JOIN parcels p ON p.id = g.parcel_id WHERE p.district = '{district}'"
        rr_where = f"WHERE district = '{district}'"
        m_where = f"WHERE p.district = '{district}' AND"
    else:
        p_where = f"WHERE district IN ({dist_placeholders})"
        pa_where = f"WHERE district IN ({dist_placeholders})"
        comp_where = f"WHERE p.district IN ({dist_placeholders})"
        g_where = f"JOIN parcels p ON p.id = g.parcel_id WHERE p.district IN ({dist_placeholders})"
        rr_where = f"WHERE district IN ({dist_placeholders})"
        m_where = f"WHERE p.district IN ({dist_placeholders}) AND"

    q = lambda sql: c.execute(sql).fetchone()[0] or 0
    
    d = {
        "state": state,
        "selected_state": state,
        "total_projects": q(f"SELECT count(*) FROM projects {p_where}"),
        "active_projects": q(f"SELECT count(*) FROM projects {p_where} AND project_status IN ('Active','In Progress')"),
        "completed_projects": q(f"SELECT count(*) FROM projects {p_where} AND project_status='Completed'"),
        "delayed_projects": q(f"SELECT count(*) FROM projects {p_where} AND project_status='Delayed'"),
        "total_parcels": q(f"SELECT count(*) FROM parcels {pa_where}"),
        "affected_families": q(f"SELECT COALESCE(sum(affected_families),0) FROM projects {p_where}"),
        "total_compensation": q(f"SELECT sum(c.assessed_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "approved_compensation": q(f"SELECT sum(c.approved_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "paid_compensation": q(f"SELECT sum(c.paid_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "pending_compensation": q(f"SELECT sum(c.pending_amount) FROM compensation c JOIN parcels p ON p.id=c.parcel_id {comp_where}") or 0,
        "legal_disputes": q(f"SELECT count(*) FROM grievances g {g_where} AND g.status != 'Resolved'"),
        "sla_breaches": q(f"SELECT count(DISTINCT m.project_id) FROM project_milestones m JOIN projects pr ON pr.project_id=m.project_id WHERE pr.district IN ({dist_placeholders}) AND m.delay_days > 0"),
        "ocr_verification_pending": q(f"SELECT count(*) FROM documents d JOIN parcels pa ON pa.id=d.parcel_id WHERE pa.district IN ({dist_placeholders}) AND d.ocr_status='Verification Required'"),
        "selected_district": district or f"All {state} Districts"
    }
    
    d["escalated_cases"] = c.execute(f"SELECT count(*) FROM grievances g {g_where} AND g.status = 'Escalated'").fetchone()[0] or 0
    d["high_risk_projects"] = c.execute(f"SELECT count(*) FROM parcels {pa_where} AND risk_category IN ('HIGH', 'CRITICAL')").fetchone()[0] or 0
    d["critical_projects"] = c.execute(f"SELECT count(*) FROM parcels {pa_where} AND risk_category = 'CRITICAL'").fetchone()[0] or 0
    
    # State specific aggregations
    d["district_performance"] = [dict(r) for r in c.execute(f"SELECT district, count(*) as projects, ROUND(avg(progress),1) as avg_progress FROM projects {p_where} GROUP BY district ORDER BY projects DESC").fetchall()]
    
    d["bottlenecks"] = [dict(r) for r in c.execute(f"""
        SELECT stage, COUNT(*) AS count FROM (
            SELECT CASE
                WHEN m.stage IN ('Survey','SIA / Survey') THEN 'Survey'
                WHEN m.stage='Legal Dispute / Resolution' THEN 'Objections'
                WHEN m.stage='Rehabilitation & Resettlement' THEN 'R&R'
                ELSE m.stage END AS stage
            FROM projects p
            JOIN project_milestones m ON m.project_id=p.project_id
                AND (m.stage=p.current_stage
                     OR (p.current_stage='Survey' AND m.stage='SIA / Survey')
                     OR (p.current_stage='Rehabilitation & Resettlement' AND m.stage='Rehabilitation'))
            {m_where} p.project_status NOT IN ('Completed','Closed')
              AND m.status != 'Completed'
              AND (m.status IN ('Pending','In Progress')
                   OR (m.expected_date IS NOT NULL AND julianday(m.expected_date) < julianday('now')))
            UNION ALL
            SELECT 'Field Verification' AS stage
            FROM field_assignments fa
            JOIN parcels p ON p.id=fa.parcel_id
            {m_where} fa.status IN ('Pending Verification','In Progress')
        ) GROUP BY stage ORDER BY count DESC
    """).fetchall()]
    
    rr_families_cnt = c.execute(f"SELECT count(*) FROM rr_families {rr_where}").fetchone()[0]
    if rr_families_cnt > 0:
        d["rr_progress"] = [dict(r) for r in c.execute(f"SELECT exceptional_state as status, count(*) as count FROM rr_families {rr_where} GROUP BY exceptional_state ORDER BY count DESC").fetchall()]
    else:
        d["rr_progress"] = [dict(r) for r in c.execute("SELECT status, count(*) as count FROM r_and_r GROUP BY status").fetchall()]
        
    d["projects_by_stage"] = [dict(r) for r in c.execute(f"SELECT current_stage stage, count(*) count FROM projects {p_where} GROUP BY current_stage ORDER BY count DESC").fetchall()]
    d["risk_distribution"] = [dict(r) for r in c.execute(f"SELECT COALESCE(risk_category,'UNKNOWN') category, count(*) count FROM parcels {pa_where} GROUP BY risk_category").fetchall()]

    c.close()
    return d

@router.get("/district")
def district_dashboard(district: Optional[str] = None, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u: raise HTTPException(401, "Authentication required")
    district = enforce_district_scope(u, district)
    c = conn()
    d = get_base_metrics(c, district)
    
    g_where = f"JOIN parcels p ON p.id = g.parcel_id WHERE p.district = '{district}' AND" if district else "WHERE"
    pa_where = f"WHERE district = '{district}' AND" if district else "WHERE"
    p_where = f"WHERE district = '{district}'" if district else ""
    
    d["escalated_cases"] = c.execute(f"SELECT count(*) FROM grievances g {g_where} g.status = 'Escalated'").fetchone()[0] or 0
    d["high_risk_projects"] = c.execute(f"SELECT count(*) FROM parcels {pa_where} risk_category IN ('HIGH', 'CRITICAL')").fetchone()[0] or 0
    d["critical_projects"] = c.execute(f"SELECT count(*) FROM parcels {pa_where} risk_category = 'CRITICAL'").fetchone()[0] or 0
    
    fa_where = f"JOIN parcels p ON p.id=fa.parcel_id WHERE p.district='{district}' AND" if district else "WHERE"
    d["pending_verification"] = c.execute(f"SELECT count(*) FROM field_assignments fa {fa_where} fa.status = 'Pending Verification'").fetchone()[0] or 0

    d["taluk_overview"] = [dict(r) for r in c.execute(f"SELECT taluk, count(*) as projects, ROUND(avg(progress),1) as avg_progress FROM projects {p_where} GROUP BY taluk ORDER BY projects DESC").fetchall()]
    
    m_join = f"JOIN projects pr ON pr.project_id=m.project_id WHERE pr.district='{district}' AND" if district else "WHERE"
    priority_actions = [dict(r) for r in c.execute(f"SELECT m.stage as action, m.delay_days as severity, m.project_id FROM project_milestones m {m_join} m.delay_days > 15 ORDER BY m.delay_days DESC LIMIT 5").fetchall()]
    d["priority_actions"] = [{"task": f"SLA Breached ({p['severity']} days) at {p['action']}", "project_id": p["project_id"]} for p in priority_actions]
    
    fa_wl_where = f"JOIN parcels p ON p.id=fa.parcel_id WHERE lower(p.district)=lower('{district}') AND" if district else "WHERE"
    d["officer_workload"] = [dict(r) for r in c.execute(f"SELECT fa.officer_email as assigned_to, count(*) as count FROM field_assignments fa {fa_wl_where} fa.status NOT IN ('Completed', 'Verified') GROUP BY fa.officer_email").fetchall()]
    d["payment_completion"] = round((d["paid_compensation"] / d["total_compensation"] * 100) if d["total_compensation"] > 0 else 0, 1)
    
    # Reports
    comp_join = f"AND p.district='{district}'" if district else ""
    d["compensation_paid_report"] = [dict(r) for r in c.execute(f"SELECT c.project_id, p.survey_no, p.taluk, p.owner_reference, c.approved_amount, c.paid_amount, c.status FROM compensation c JOIN parcels p ON c.parcel_id = p.id WHERE c.status = 'Paid' {comp_join} LIMIT 10").fetchall()]
    d["compensation_pending_report"] = [dict(r) for r in c.execute(f"SELECT c.project_id, p.survey_no, p.taluk, p.owner_reference, c.assessed_amount, c.pending_amount, c.status FROM compensation c JOIN parcels p ON c.parcel_id = p.id WHERE c.status != 'Paid' {comp_join} LIMIT 10").fetchall()]

    # ── R&R metrics from rr_families ──────────────────────────────────────
    rr_where = f"WHERE district = '{district}'" if district else ""
    rr_row = c.execute(f"""
        SELECT
            COUNT(*) as rr_total_families,
            ROUND(AVG(readiness_percentage), 1) as rr_avg_readiness,
            SUM(CASE WHEN exceptional_state = 'Completed' THEN 1 ELSE 0 END) as rr_completed,
            SUM(CASE WHEN readiness_band = 'Delayed' THEN 1 ELSE 0 END) as rr_delayed,
            SUM(CASE WHEN readiness_band = 'Critical' THEN 1 ELSE 0 END) as rr_critical,
            SUM(CASE WHEN readiness_band = 'Attention Required' THEN 1 ELSE 0 END) as rr_attention,
            SUM(CASE WHEN readiness_band = 'On Track' THEN 1 ELSE 0 END) as rr_on_track,
            SUM(CASE WHEN verification_status = 'Not Started' OR verification_status = 'Pending' OR verification_status = 'Scheduled' THEN 1 ELSE 0 END) as rr_pending_verification,
            SUM(CASE WHEN verification_status = 'Verified' THEN 1 ELSE 0 END) as rr_verified,
            SUM(CASE WHEN grievance_status != 'No Grievance' AND grievance_status != 'Resolved' THEN 1 ELSE 0 END) as rr_open_grievances,
            SUM(CASE WHEN is_vulnerable = 1 THEN 1 ELSE 0 END) as rr_vulnerable
        FROM rr_families {rr_where}
    """).fetchone()
    d["rr_summary"] = dict(rr_row) if rr_row else {}

    # Latest 5 verified families with officer info
    rr_verified_where = f"WHERE district = '{district}' AND verified_by IS NOT NULL" if district else "WHERE verified_by IS NOT NULL"
    d["rr_recent_verifications"] = [dict(r) for r in c.execute(f"""
        SELECT family_id, family_head, survey_no, village, verification_status,
               verified_by, verified_at, readiness_percentage, readiness_band, rr_stage
        FROM rr_families {rr_verified_where}
        ORDER BY verified_at DESC LIMIT 5
    """).fetchall()]

    c.close()
    return d
