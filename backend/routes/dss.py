"""
FastAPI Router for LandNexus Role-Based Decision Support System (RB-DSS).
Enforces strict RBAC, integrates human-in-the-loop decisions, and logs all audit trails.
"""

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import uuid

from backend.core import conn, current_user, audit, check_resource_district, enforce_district_scope
from backend.dss_engine import (
    compute_parcel_score,
    compute_project_score,
    compute_district_score,
    compute_state_score,
    compute_bottlenecks,
    compute_early_warnings,
    get_priority_parcels
)
from backend.dss_rules import (
    generate_parcel_recommendation,
    generate_project_recommendation,
    explain_dss_assessment
)

router = APIRouter()

class HumanDecisionIn(BaseModel):
    recommendation_id: Optional[str] = None
    entity_type: str  # "parcel", "project", "district"
    entity_id: str
    action: str       # "accept", "modify", "reject"
    modified_notes: Optional[str] = ""
    target_action: Optional[str] = None

class AskAiIn(BaseModel):
    entity_type: str  # "parcel", "project", "state"
    entity_id: str
    question: Optional[str] = "Summarize this record"

def _verify_officer_access(u: dict, allow_citizen=False):
    if not u:
        raise HTTPException(401, "Authentication required")
    if u.get("role") == "citizen" and not allow_citizen:
        raise HTTPException(403, "Citizen accounts cannot access internal Decision Support intelligence")

@router.get("/parcel/{parcel_id}")
def get_parcel_dss(parcel_id: int, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)

    c = conn()
    p_row = c.execute("SELECT district, project_id FROM parcels WHERE id=?", (parcel_id,)).fetchone()
    c.close()
    if not p_row:
        raise HTTPException(404, "Parcel not found")

    if u.get("role") == "field_officer" and u.get("district_scope"):
        check_resource_district(u, p_row["district"], "Parcel DSS Assessment")

    score_data = compute_parcel_score(parcel_id)
    if not score_data:
        raise HTTPException(404, "Unable to compute DSS assessment for parcel")

    rec_data = generate_parcel_recommendation(score_data)
    explanation = explain_dss_assessment("parcel", parcel_id, score_data, rec_data)

    rec_id = f"REC-PARCEL-{parcel_id}"

    return {
        "recommendation_id": rec_id,
        "assessment": score_data,
        "recommendation": rec_data,
        "explanation": explanation
    }

@router.get("/project/{project_id}")
def get_project_dss(project_id: str, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)

    c = conn()
    p_row = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
    c.close()
    if not p_row:
        raise HTTPException(404, "Project not found")

    if u.get("district_scope"):
        check_resource_district(u, p_row["district"], "Project DSS Assessment")

    score_data = compute_project_score(project_id)
    if not score_data:
        raise HTTPException(404, "Unable to compute DSS assessment for project")

    rec_data = generate_project_recommendation(score_data)
    explanation = explain_dss_assessment("project", project_id, score_data, rec_data)

    return {
        "recommendation_id": f"REC-PROJ-{project_id}",
        "assessment": score_data,
        "recommendation": rec_data,
        "explanation": explanation
    }

@router.get("/district/{district_id}")
def get_district_dss(district_id: str, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)
    district = enforce_district_scope(u, district_id)

    data = compute_district_score(district)
    return data

@router.get("/state")
def get_state_dss(authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)
    if u.get("role") not in ("state_authority", "authority", "admin"):
        raise HTTPException(403, "State Authority or Admin clearance required for Statewide DSS Overview")

    state_name = u.get("state_scope") or "Tamil Nadu"
    return compute_state_score(state_name)

@router.get("/priority-parcels")
def list_priority_parcels(
    district: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    authorization: str = Header(None)
):
    u = current_user(authorization)
    _verify_officer_access(u)
    effective_district = enforce_district_scope(u, district)

    data = get_priority_parcels(district=effective_district, limit=limit, offset=offset)

    # Attach recommendations
    for item in data.get("items", []):
        rec = generate_parcel_recommendation(item)
        item["recommendation"] = rec["recommendation"]
        item["suggested_actions"] = rec["suggested_actions"]
        item["recommendation_id"] = f"REC-PARCEL-{item['parcel_id']}"

    return data

@router.get("/bottlenecks")
def get_dss_bottlenecks(district: Optional[str] = None, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)
    effective_district = enforce_district_scope(u, district)
    return compute_bottlenecks(district=effective_district)

@router.get("/early-warnings")
def get_dss_early_warnings(district: Optional[str] = None, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)
    effective_district = enforce_district_scope(u, district)
    return compute_early_warnings(district=effective_district)

@router.post("/decision")
def record_human_decision(d: HumanDecisionIn, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)

    if d.action not in ("accept", "modify", "reject"):
        raise HTTPException(400, "Action must be 'accept', 'modify', or 'reject'")

    c = conn()
    decision_uuid = f"DSS-DEC-{uuid.uuid4().hex[:8].upper()}"

    # Verify resource
    parcel_id = None
    project_id = None
    district = None

    if d.entity_type == "parcel":
        try:
            parcel_id = int(d.entity_id)
        except:
            p_find = c.execute("SELECT id, district, project_id FROM parcels WHERE record_id=?", (d.entity_id,)).fetchone()
            if p_find:
                parcel_id = p_find["id"]
                district = p_find["district"]
                project_id = p_find["project_id"]
        if parcel_id and not district:
            p_find = c.execute("SELECT district, project_id FROM parcels WHERE id=?", (parcel_id,)).fetchone()
            if p_find:
                district = p_find["district"]
                project_id = p_find["project_id"]
    elif d.entity_type == "project":
        project_id = d.entity_id
        p_find = c.execute("SELECT district FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if p_find:
            district = p_find["district"]

    # Enforce district boundary
    if district and u.get("district_scope"):
        check_resource_district(u, district, f"DSS Decision for {d.entity_type}")

    # Compute snapshot of score
    score_val = 0
    risk_lvl = "LOW"
    rec_text = ""
    reasons_str = ""

    if d.entity_type == "parcel" and parcel_id:
        p_sc = compute_parcel_score(parcel_id)
        if p_sc:
            score_val = p_sc.get("priority_score", 0)
            risk_lvl = p_sc.get("risk_level", "LOW")
            p_rec = generate_parcel_recommendation(p_sc)
            rec_text = p_rec.get("recommendation", "")
            reasons_str = "; ".join(p_sc.get("reasons", []))

    workflow_action_executed = "No automatic workflow transition"

    # If action is ACCEPT and it's a parcel verification recommendation, trigger assignment workflow
    if d.action == "accept" and d.entity_type == "parcel" and parcel_id:
        existing_assign = c.execute(
            "SELECT id, status FROM field_assignments WHERE parcel_id=? AND status NOT IN ('Cancelled','Revoked','Rejected')",
            (parcel_id,)
        ).fetchone()

        if not existing_assign:
            # Create field assignment automatically for the field officer in this district
            target_officer = u["email"] if u.get("role") == "field_officer" else None
            if not target_officer:
                fo_row = c.execute("SELECT email FROM users WHERE role='field_officer' AND lower(district_scope)=lower(?) AND active=1 LIMIT 1", (district,)).fetchone()
                target_officer = fo_row["email"] if fo_row else u["email"]

            c.execute("""
                INSERT INTO field_assignments (parcel_id, officer_email, assigned_by, status, project_id, district, state)
                VALUES (?, ?, ?, 'Pending Verification', ?, ?, ?)
            """, (parcel_id, target_officer, u["email"], project_id, district, u.get("state_scope") or "Tamil Nadu"))
            workflow_action_executed = f"Field verification assignment dispatched to {target_officer}"
        else:
            workflow_action_executed = f"Assignment already active (Status: {existing_assign['status']})"

    c.execute("""
        INSERT INTO dss_decisions (
            decision_id, user_email, user_role, entity_type, entity_id,
            project_id, parcel_id, district, recommendation_id,
            recommendation, risk_score, risk_level, reasons,
            human_action, modified_notes, workflow_action
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        decision_uuid, u["email"], u["role"], d.entity_type, str(d.entity_id),
        project_id, parcel_id, district, d.recommendation_id or f"REC-{d.entity_id}",
        rec_text, score_val, risk_lvl, reasons_str,
        d.action, d.modified_notes, workflow_action_executed
    ))
    c.commit()
    c.close()

    audit(
        u["email"],
        f"DSS_DECISION_{d.action.upper()}",
        f"{d.entity_type}:{d.entity_id}",
        f"decision_id={decision_uuid} | action={d.action} | notes={d.modified_notes} | workflow={workflow_action_executed}"
    )

    return {
        "status": "success",
        "decision_id": decision_uuid,
        "action": d.action,
        "workflow_action": workflow_action_executed,
        "message": f"Recommendation successfully {d.action}ed. Full audit record created."
    }

@router.get("/decision-history")
def get_dss_decision_history(
    district: Optional[str] = None,
    limit: int = 50,
    authorization: str = Header(None)
):
    u = current_user(authorization)
    _verify_officer_access(u)
    effective_district = enforce_district_scope(u, district)

    c = conn()
    where = "WHERE 1=1"
    args = []
    if effective_district and effective_district.lower() != "all":
        where += " AND lower(district)=lower(?)"
        args.append(effective_district)

    args.append(min(limit, 200))
    rows = c.execute(f"SELECT * FROM dss_decisions {where} ORDER BY id DESC LIMIT ?", args).fetchall()
    c.close()

    return [dict(r) for r in rows]

@router.post("/ask")
def ask_dss_ai(payload: AskAiIn, authorization: str = Header(None)):
    u = current_user(authorization)
    _verify_officer_access(u)

    if payload.entity_type == "parcel":
        pid = None
        c = conn()
        try:
            val_int = int(payload.entity_id)
            row = c.execute("SELECT id FROM parcels WHERE id=?", (val_int,)).fetchone()
            if row: pid = row["id"]
        except:
            pass
        if not pid:
            row = c.execute("SELECT id FROM parcels WHERE record_id=? OR id=?", (payload.entity_id, payload.entity_id)).fetchone()
            if row: pid = row["id"]
        c.close()

        if not pid:
            raise HTTPException(404, f"Parcel '{payload.entity_id}' not found")

        score_data = compute_parcel_score(pid)
        if not score_data:
            raise HTTPException(404, "Parcel not found")
        rec_data = generate_parcel_recommendation(score_data)
        return explain_dss_assessment("parcel", pid, score_data, rec_data, question=payload.question)

    elif payload.entity_type == "project":
        score_data = compute_project_score(payload.entity_id)
        if not score_data:
            raise HTTPException(404, "Project not found")
        rec_data = generate_project_recommendation(score_data)
        return explain_dss_assessment("project", payload.entity_id, score_data, rec_data, question=payload.question)

    raise HTTPException(400, "Unsupported entity type for Ask AI")
