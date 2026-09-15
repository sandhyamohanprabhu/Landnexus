"""
SMS Routes — SURVI / LANDNEXUS (Multi-District Government SMPP Notification Centre)
===================================================================================
Enforces strict district scoping via `enforce_district_scope`.
A District Authority can NEVER view or send SMS to another district's records.
"""

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.core import current_user, enforce_district_scope, audit, conn
from backend.services.sms_service import (
    send_sms,
    send_bulk_sms,
    get_sms_history,
    get_sms_stats,
    get_state_sms_stats,
    get_matching_recipients,
    smpp_health,
    GOVT_TEMPLATES
)

router = APIRouter()

# ─── Pydantic Request Models ─────────────────────────────────────────────────
class SendSingleSMSRequest(BaseModel):
    recipient_phone: str
    message: str
    recipient_name: Optional[str] = "Landowner"
    parcel_id: Optional[int] = None
    project_id: Optional[str] = None
    template: Optional[str] = "Custom"
    district: Optional[str] = None

class BulkSMSRequest(BaseModel):
    project_id: Optional[str] = ""
    village: Optional[str] = ""
    taluk: Optional[str] = ""
    status: Optional[str] = ""
    stage: Optional[str] = ""
    template_name: Optional[str] = "General Notice"
    message_text: str
    district: Optional[str] = None
    selected_parcel_ids: Optional[List[int]] = None

class WorkflowTriggerRequest(BaseModel):
    event_type: str  # "field_verification", "compensation_approved", "rr_update"
    parcel_id: int
    custom_note: Optional[str] = ""

# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/health")
def api_sms_health():
    """Returns SMPP gateway status (Demo Mode vs Live SMPP)."""
    return smpp_health()

@router.get("/templates")
def api_sms_templates():
    """Returns official reusable government-style SMS notification templates."""
    return {"templates": GOVT_TEMPLATES}

@router.get("/stats")
def api_sms_stats(district: str = "", authorization: str = Header(None)):
    """
    Returns live database-backed SMS performance metrics for the authenticated district.
    District Authorities are strictly locked to their assigned district.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    
    # Enforce district scoping
    scoped_district = enforce_district_scope(u, district)
    stats = get_sms_stats(scoped_district)
    return stats

@router.get("/state-stats")
def api_sms_state_stats(authorization: str = Header(None)):
    """
    Returns aggregated SMS communication statistics across all 5 districts.
    Accessible to State Authorities and Administrators.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    if u["role"] not in ("state_authority", "authority", "admin", "national_authority"):
        raise HTTPException(403, "State authority or administrative access required")
    
    return get_state_sms_stats()

@router.get("/recipients")
def api_sms_recipients(
    district: str = "",
    project_id: str = "",
    village: str = "",
    taluk: str = "",
    status: str = "",
    authorization: str = Header(None)
):
    """
    Identifies matching landowners and parcels from the CURRENT district based on filters.
    Returns counts of valid mobile numbers and missing mobile numbers.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    scoped_district = enforce_district_scope(u, district)
    data = get_matching_recipients(
        district=scoped_district,
        project_id=project_id,
        village=village,
        taluk=taluk,
        status=status
    )
    return data

@router.post("/send")
def api_send_sms(req: SendSingleSMSRequest, authorization: str = Header(None)):
    """
    Send an individual SMS to a landowner.
    Strictly verifies that if parcel_id is given, it belongs to the authenticated district.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    if u["role"] not in ("district_authority", "authority", "admin", "state_authority"):
        raise HTTPException(403, "District Authority access required")

    scoped_district = enforce_district_scope(u, req.district)

    # Security check: verify parcel belongs to this district if parcel_id is provided
    if req.parcel_id:
        c = conn()
        p = c.execute("SELECT district, project_id FROM parcels WHERE id = ?", (req.parcel_id,)).fetchone()
        c.close()
        if not p:
            raise HTTPException(404, "Parcel not found")
        if p["district"].strip().lower() != scoped_district.strip().lower():
            raise HTTPException(403, f"Cross-district access forbidden: Parcel belongs to {p['district']}, not {scoped_district}")

    metadata = {
        "district": scoped_district,
        "project_id": req.project_id,
        "parcel_id": req.parcel_id,
        "recipient_name": req.recipient_name,
        "template": req.template,
        "message_type": "Individual",
        "created_by": u["email"]
    }

    res = send_sms(req.recipient_phone, req.message, metadata)
    
    # Audit log
    audit(
        user=u["email"],
        action="SEND_SMS",
        target=f"Parcel {req.parcel_id or 'General'}",
        details=f"Individual SMS to {req.recipient_phone} in {scoped_district} | Status: {res.get('status')}"
    )

    return res

@router.post("/bulk-send")
def api_send_bulk_sms(req: BulkSMSRequest, authorization: str = Header(None)):
    """
    Send bulk SMS to affected landowners in the current district.
    Requires confirmation from the District Authority.
    Creates an audit entry for the bulk operation.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")
    if u["role"] not in ("district_authority", "authority", "admin"):
        raise HTTPException(403, "District Authority access required for Bulk SMS")

    scoped_district = enforce_district_scope(u, req.district)

    # Query matching recipients for this district
    matched = get_matching_recipients(
        district=scoped_district,
        project_id=req.project_id,
        village=req.village,
        taluk=req.taluk,
        status=req.status
    )

    recipients = matched.get("recipients", [])
    
    # If specific parcel IDs were selected, filter down
    if req.selected_parcel_ids:
        recipients = [r for r in recipients if r["parcel_id"] in req.selected_parcel_ids]

    if not recipients:
        raise HTTPException(400, f"No eligible recipients with valid mobile numbers found in {scoped_district} for the selected criteria.")

    metadata = {
        "district": scoped_district,
        "project_id": req.project_id,
        "template": req.template_name,
        "created_by": u["email"]
    }

    result = send_bulk_sms(recipients, req.message_text, metadata)

    # Audit Trail Entry
    audit(
        user=u["email"],
        action="BULK_SMS_SENT",
        target=f"Project: {req.project_id or 'District-wide'}",
        details=f"DISTRICT AUTHORITY {scoped_district} | Bulk SMS sent | Recipients: {len(recipients)} | Project: {req.project_id or 'All'} | Template: {req.template_name} | Time: {datetime.now().strftime('%d %b %Y %H:%M')}"
    )

    return {
        "success": True,
        "message": f"Bulk SMS successfully processed for {len(recipients)} landowners in {scoped_district}.",
        "summary": result
    }

@router.get("/history")
def api_sms_history(
    district: str = "",
    project_id: str = "",
    village: str = "",
    status: str = "",
    message_type: str = "",
    search: str = "",
    limit: int = 100,
    offset: int = 0,
    authorization: str = Header(None)
):
    """
    Returns district-scoped SMS delivery history logs.
    Supports filtering by project, status, message type, or search term.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    scoped_district = enforce_district_scope(u, district)
    return get_sms_history(
        district=scoped_district,
        project_id=project_id,
        village=village,
        status=status,
        message_type=message_type,
        search=search,
        limit=limit,
        offset=offset
    )

@router.post("/workflow-trigger")
def api_workflow_trigger(req: WorkflowTriggerRequest, authorization: str = Header(None)):
    """
    Trigger an automated workflow SMS notification.
    Example: Field verification completed -> District authority approves sending SMS.
    """
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    c = conn()
    p = c.execute("SELECT * FROM parcels WHERE id = ?", (req.parcel_id,)).fetchone()
    c.close()
    if not p:
        raise HTTPException(404, "Parcel not found")

    scoped_district = enforce_district_scope(u, p["district"])
    phone = p.get("mobile_number")
    if not phone:
        raise HTTPException(400, "Parcel does not have a registered mobile number")

    template_text = f"Government of Tamil Nadu: Land record update for Survey No {p['survey_no']}, Village {p['village']}. Status updated: {req.event_type.replace('_', ' ').title()}. Ref: TN-{scoped_district[:3].upper()}-{p['id']}."
    if req.custom_note:
        template_text += f" Note: {req.custom_note}"

    metadata = {
        "district": scoped_district,
        "project_id": p["project_id"],
        "parcel_id": p["id"],
        "recipient_name": p.get("owner_name") or p.get("owner_reference") or "Landowner",
        "template": f"Workflow-{req.event_type}",
        "message_type": "Workflow Trigger",
        "created_by": u["email"]
    }

    res = send_sms(phone, template_text, metadata)
    return res
