"""
SMS Service — SURVI / LANDNEXUS (Multi-District Government SMPP Gateway)
========================================================================
Supports:
  1. Production SMPP v3.4 Gateway Protocol (via smpplib) when SMPP_ENABLED=true
  2. Safe Demo / Mock Gateway ("SMS Gateway: DEMO MODE") when disabled or unconfigured
  3. District-scoped SMS logging and audit trail integration
  4. Real-time delivery tracking: Queued -> Submitted -> Delivered / Failed
"""

import os
import re
import time
import uuid
import logging
from datetime import datetime, date
from pathlib import Path
import sqlite3

logger = logging.getLogger("survi.sms")

# ─── Environment Configuration ───────────────────────────────────────────────
SMPP_HOST = os.getenv("SMPP_HOST", "").strip()
SMPP_PORT = int(os.getenv("SMPP_PORT", "2775"))
SMPP_SYSTEM_ID = os.getenv("SMPP_SYSTEM_ID", "").strip()
SMPP_PASSWORD = os.getenv("SMPP_PASSWORD", "").strip()
SMPP_SYSTEM_TYPE = os.getenv("SMPP_SYSTEM_TYPE", "").strip()
SMPP_SOURCE_ADDR = os.getenv("SMPP_SOURCE_ADDR", "TNSURVI").strip()
SMPP_SOURCE_TON = int(os.getenv("SMPP_SOURCE_TON", "5"))   # Alphanumeric
SMPP_SOURCE_NPI = int(os.getenv("SMPP_SOURCE_NPI", "0"))
SMPP_DEST_TON = int(os.getenv("SMPP_DEST_TON", "1"))       # International (e.g. 91...)
SMPP_DEST_NPI = int(os.getenv("SMPP_DEST_NPI", "1"))
SMPP_ENABLED = os.getenv("SMPP_ENABLED", "false").strip().lower() in ("true", "1", "yes")

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "survi.db"

def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

# ─── Standard Government SMS Templates ───────────────────────────────────────
GOVT_TEMPLATES = [
    {
        "id": "TPL-01",
        "title": "Land Acquisition Notification",
        "category": "Statutory Notice",
        "template": "Government of Tamil Nadu, {district} District Administration: Land acquisition proceedings initiated for Project {project_id}. Survey No: {survey_no}, Village: {village}. You may inspect preliminary assessment records at the Taluk Office.",
    },
    {
        "id": "TPL-02",
        "title": "Field Verification Scheduled",
        "category": "Field Operation",
        "template": "TN Land Acquisition Notice: Joint field verification scheduled for Survey No {survey_no}, Village {village} on {date}. Landowner {owner_name} or authorized representative is requested to be present with boundary records.",
    },
    {
        "id": "TPL-03",
        "title": "Document Verification Required",
        "category": "Documentation",
        "template": "Urgent — {district} District Land Office: Landowner {owner_name}, please submit Patta, Chitta & ownership deeds for Survey No {survey_no}, Project {project_id} within 7 working days to expedite compensation determination.",
    },
    {
        "id": "TPL-04",
        "title": "Compensation Approved",
        "category": "Compensation",
        "template": "TN Revenue Dept: Compensation award of Rs. {amount} has been approved by District Collector, {district} for Survey No {survey_no}, Project {project_id}. Award proceedings ref: {ref_no}.",
    },
    {
        "id": "TPL-05",
        "title": "Compensation Payment Processed",
        "category": "Disbursement",
        "template": "Direct Benefit Transfer Alert: Compensation amount of Rs. {amount} for Survey No {survey_no} has been credited to your verified bank account. UTR Ref: {ref_no}. Revenue Dept, {district}.",
    },
    {
        "id": "TPL-06",
        "title": "R&R Assistance Update",
        "category": "Rehabilitation",
        "template": "R&R Rehabilitation & Resettlement Wing, {district}: Your family resettlement entitlement package for Project {project_id} has been verified and passed for disbursement. Case ID: {ref_no}.",
    },
    {
        "id": "TPL-07",
        "title": "Hearing / Grievance Notification",
        "category": "Grievance",
        "template": "Notice of Hearing: Grievance regarding Survey No {survey_no} in {village} will be heard by District Revenue Officer (DRO), {district} on {date} at 11:00 AM at the Collectorate.",
    },
    {
        "id": "TPL-08",
        "title": "Parcel Verification Completed",
        "category": "Verification",
        "template": "Land Records Update: Ground survey and boundary verification for Survey No {survey_no}, Village {village} has been successfully completed and tagged in LANDNEXUS GIS. Ref: {ref_no}.",
    },
    {
        "id": "TPL-09",
        "title": "Project Status Update",
        "category": "Public Information",
        "template": "{district} District Information: Acquisition milestone completed for {project_id}. 80% boundary demarcations done. Track transparent real-time status on LANDNEXUS portal.",
    },
    {
        "id": "TPL-10",
        "title": "General District Notification",
        "category": "General",
        "template": "Official Notice from District Collectorate, {district}: All affected landholders for Project {project_id} are invited for stakeholder consultation at Taluk Office on {date}.",
    }
]

# ─── Mobile Normalization ───────────────────────────────────────────────────
def normalize_indian_mobile(mobile: str) -> str:
    """Normalize phone number to 10-digit Indian standard format or empty string if invalid."""
    if not mobile:
        return ""
    digits = re.sub(r"\D", "", str(mobile))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return ""

# ─── SMPP Low-Level Transport ────────────────────────────────────────────────
def _send_via_smpp(dest_phone: str, message: str) -> dict:
    """Send single SMS via real SMPP protocol using smpplib."""
    try:
        import smpplib.client
        import smpplib.consts
        import smpplib.gsm

        int_phone = "91" + dest_phone if not dest_phone.startswith("91") else dest_phone
        client = smpplib.client.Client(SMPP_HOST, SMPP_PORT, allow_unknown_opt_params=True)
        client.connect()
        client.bind_transceiver(system_id=SMPP_SYSTEM_ID, password=SMPP_PASSWORD, system_type=SMPP_SYSTEM_TYPE)

        # Handle GSM-7 / UCS-2 Encoding
        try:
            parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(message)
        except Exception:
            parts = [message.encode("utf-16-be")]
            encoding_flag = smpplib.consts.SMPP_ENCODING_ISO10646
            msg_type_flag = 0

        pdu_ids = []
        for part in parts:
            pdu = client.send_message(
                source_addr_ton=SMPP_SOURCE_TON,
                source_addr_npi=SMPP_SOURCE_NPI,
                source_addr=SMPP_SOURCE_ADDR,
                dest_addr_ton=SMPP_DEST_TON,
                dest_addr_npi=SMPP_DEST_NPI,
                destination_addr=int_phone,
                short_message=part,
                data_coding=encoding_flag,
                esm_class=msg_type_flag,
                registered_delivery=True,
            )
            pdu_ids.append(str(pdu.sequence))

        client.unbind()
        client.disconnect()

        return {
            "success": True,
            "provider": "SMPP v3.4",
            "provider_message_id": f"SMPP-{pdu_ids[0] if pdu_ids else uuid.uuid4().hex[:8].upper()}",
            "status": "Delivered",
            "error": None
        }
    except Exception as e:
        logger.error(f"SMPP send failure to {dest_phone}: {e}")
        return {
            "success": False,
            "provider": "SMPP v3.4",
            "provider_message_id": None,
            "status": "Failed",
            "error": str(e)
        }

# ─── High-Level SMS Sending Function ─────────────────────────────────────────
def send_sms(recipient_phone: str, message: str, metadata: dict = None) -> dict:
    """
    Send an SMS message.
    Uses real SMPP when SMPP_ENABLED=True and credentials are configured.
    Otherwise uses safe DEMO simulation mode.
    Logs result to database `sms_logs`.
    """
    metadata = metadata or {}
    clean_phone = normalize_indian_mobile(recipient_phone)
    if not clean_phone:
        return {
            "success": False,
            "status": "Failed",
            "failure_reason": "Invalid or missing mobile number",
            "provider": "Validation",
            "provider_message_id": None
        }

    is_live = SMPP_ENABLED and bool(SMPP_HOST and SMPP_SYSTEM_ID)
    if is_live:
        result = _send_via_smpp(clean_phone, message)
    else:
        # Safe simulated delivery (DEMO MODE)
        msg_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        result = {
            "success": True,
            "provider": "DEMO (Safe Simulation)",
            "provider_message_id": msg_id,
            "status": "Delivered",
            "error": None
        }

    # Log to SQLite sms_logs table
    try:
        c = get_db()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO sms_logs (
                district, project_id, parcel_id, recipient_name, recipient_phone,
                message, template, message_type, provider, status,
                provider_message_id, created_by, created_at, delivered_at, failure_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("district", "Coimbatore"),
            metadata.get("project_id"),
            metadata.get("parcel_id"),
            metadata.get("recipient_name", "Landowner"),
            clean_phone,
            message,
            metadata.get("template", "Custom"),
            metadata.get("message_type", "Individual"),
            result.get("provider", "DEMO"),
            result.get("status", "Delivered"),
            result.get("provider_message_id"),
            metadata.get("created_by", "system"),
            now_str,
            now_str if result.get("status") == "Delivered" else None,
            result.get("error")
        ))
        c.commit()
        c.close()
    except Exception as e:
        logger.warning(f"Failed to log SMS to database: {e}")

    return result

# ─── Bulk SMS Sending Function ───────────────────────────────────────────────
def send_bulk_sms(recipients: list, message_template: str, metadata: dict = None) -> dict:
    """
    Send bulk SMS to an identified list of recipients.
    Each recipient is a dict with: parcel_id, survey_no, village, taluk, owner_name, phone, project_id, etc.
    Message placeholders are dynamically formatted per recipient.
    """
    metadata = metadata or {}
    district = metadata.get("district", "Coimbatore")
    created_by = metadata.get("created_by", "district_authority")
    template_name = metadata.get("template", "Bulk Notification")

    total_submitted = 0
    delivered_count = 0
    failed_count = 0
    skipped_no_phone = 0
    results_list = []

    for r in recipients:
        phone = normalize_indian_mobile(r.get("phone") or r.get("mobile_number", ""))
        if not phone:
            skipped_no_phone += 1
            continue

        # Format message placeholders dynamically
        formatted_msg = message_template.replace("{owner_name}", str(r.get("owner_name") or "Landowner"))\
                                         .replace("{survey_no}", str(r.get("survey_no") or "N/A"))\
                                         .replace("{village}", str(r.get("village") or district))\
                                         .replace("{taluk}", str(r.get("taluk") or district))\
                                         .replace("{district}", str(district))\
                                         .replace("{project_id}", str(r.get("project_id") or metadata.get("project_id") or "PROJECT"))\
                                         .replace("{amount}", str(r.get("compensation_amount") or "As Per Award"))\
                                         .replace("{ref_no}", f"TN-{district[:3].upper()}-{r.get('parcel_id', '001')}")\
                                         .replace("{date}", datetime.now().strftime("%d-%m-%Y"))

        item_meta = {
            "district": district,
            "project_id": r.get("project_id") or metadata.get("project_id"),
            "parcel_id": r.get("parcel_id") or r.get("id"),
            "recipient_name": r.get("owner_name") or "Landowner",
            "template": template_name,
            "message_type": "Bulk",
            "created_by": created_by
        }

        res = send_sms(phone, formatted_msg, item_meta)
        total_submitted += 1
        if res.get("status") == "Delivered":
            delivered_count += 1
        else:
            failed_count += 1

        results_list.append({
            "parcel_id": item_meta["parcel_id"],
            "survey_no": r.get("survey_no"),
            "owner_name": item_meta["recipient_name"],
            "phone": phone,
            "status": res.get("status"),
            "message_id": res.get("provider_message_id"),
            "error": res.get("error")
        })

    return {
        "total_recipients_selected": len(recipients),
        "total_submitted": total_submitted,
        "delivered": delivered_count,
        "failed": failed_count,
        "skipped_missing_phone": skipped_no_phone,
        "results": results_list[:50]  # Return preview of results
    }

# ─── Query & Recipient Identification Helper ─────────────────────────────────
def get_matching_recipients(district: str, project_id: str = "", village: str = "", taluk: str = "",
                           status: str = "", stage: str = "", compensation_status: str = "", rr_status: str = "") -> dict:
    """
    Identifies matching landowners and parcels strictly within the given district.
    Calculates total parcels, valid mobile numbers, missing mobile numbers, and recipient list.
    """
    c = get_db()
    where_clauses = ["lower(district) = ?"]
    params = [district.strip().lower()]

    if project_id and project_id != "all":
        where_clauses.append("project_id = ?")
        params.append(project_id)
    if village and village != "all":
        where_clauses.append("lower(village) = ?")
        params.append(village.strip().lower())
    if taluk and taluk != "all":
        where_clauses.append("lower(taluk) = ?")
        params.append(taluk.strip().lower())
    if status and status != "all":
        where_clauses.append("lower(acquisition_status) = ?")
        params.append(status.strip().lower())

    sql = f"""
        SELECT id, survey_no, subdivision, village, taluk, district, project_id,
               area, acquisition_status, owner_reference,
               COALESCE(owner_name, owner_reference, 'Landowner') as owner_name,
               mobile_number
        FROM parcels
        WHERE {' AND '.join(where_clauses)}
        ORDER BY id ASC
        LIMIT 1000
    """
    rows = [dict(r) for r in c.execute(sql, params).fetchall()]
    c.close()

    valid_recipients = []
    missing_mobile_list = []

    for r in rows:
        clean_phone = normalize_indian_mobile(r.get("mobile_number"))
        item = {
            "parcel_id": r["id"],
            "survey_no": r["survey_no"],
            "subdivision": r.get("subdivision", "1"),
            "village": r["village"],
            "taluk": r["taluk"],
            "district": r["district"],
            "project_id": r["project_id"],
            "owner_name": r["owner_name"],
            "raw_phone": r.get("mobile_number") or "",
            "phone": clean_phone,
            "has_phone": bool(clean_phone)
        }
        if clean_phone:
            valid_recipients.append(item)
        else:
            missing_mobile_list.append(item)

    return {
        "district": district,
        "total_parcels": len(rows),
        "valid_mobile_count": len(valid_recipients),
        "missing_mobile_count": len(missing_mobile_list),
        "recipients": valid_recipients,
        "missing_recipients": missing_mobile_list[:20]
    }

# ─── History & Statistics Queries ────────────────────────────────────────────
def get_sms_history(district: str, project_id: str = "", village: str = "", status: str = "",
                    message_type: str = "", search: str = "", limit: int = 100, offset: int = 0) -> dict:
    """Retrieve district-scoped SMS history logs with optional filtering."""
    c = get_db()
    where = ["lower(district) = ?"]
    args = [district.strip().lower()]

    if project_id and project_id != "all":
        where.append("project_id = ?")
        args.append(project_id)
    if status and status != "all":
        where.append("status = ?")
        args.append(status)
    if message_type and message_type != "all":
        where.append("message_type = ?")
        args.append(message_type)
    if search:
        where.append("(recipient_name LIKE ? OR recipient_phone LIKE ? OR message LIKE ?)")
        q = f"%{search}%"
        args.extend([q, q, q])

    count_sql = f"SELECT count(*) FROM sms_logs WHERE {' AND '.join(where)}"
    total = c.execute(count_sql, args).fetchone()[0]

    sql = f"""
        SELECT id, district, project_id, parcel_id, recipient_name, recipient_phone,
               message, template, message_type, provider, status, provider_message_id,
               created_by, created_at, delivered_at, failure_reason
        FROM sms_logs
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """
    rows = [dict(r) for r in c.execute(sql, args + [min(limit, 500), max(offset, 0)]).fetchall()]
    c.close()

    return {
        "district": district,
        "total": total,
        "items": rows,
        "logs": rows
    }

def get_sms_stats(district: str) -> dict:
    """Return live database-backed SMS performance metrics for the given district."""
    c = get_db()
    d_lower = district.strip().lower()
    today_str = date.today().strftime("%Y-%m-%d")

    total_sent = c.execute("SELECT count(*) FROM sms_logs WHERE lower(district) = ?", (d_lower,)).fetchone()[0]
    sent_today = c.execute("SELECT count(*) FROM sms_logs WHERE lower(district) = ? AND created_at >= ?", (d_lower, today_str)).fetchone()[0]
    delivered = c.execute("SELECT count(*) FROM sms_logs WHERE lower(district) = ? AND status = 'Delivered'", (d_lower,)).fetchone()[0]
    pending = c.execute("SELECT count(*) FROM sms_logs WHERE lower(district) = ? AND status IN ('Pending', 'Queued', 'Submitted')", (d_lower,)).fetchone()[0]
    failed = c.execute("SELECT count(*) FROM sms_logs WHERE lower(district) = ? AND status = 'Failed'", (d_lower,)).fetchone()[0]

    # Total parcels & mobile breakdown
    total_parcels = c.execute("SELECT count(*) FROM parcels WHERE lower(district) = ?", (d_lower,)).fetchone()[0]
    valid_mobile_parcels = c.execute("SELECT count(*) FROM parcels WHERE lower(district) = ? AND mobile_number IS NOT NULL AND length(mobile_number) >= 10", (d_lower,)).fetchone()[0]
    missing_mobile_parcels = max(0, total_parcels - valid_mobile_parcels)

    # Recipients in current district (count distinct valid mobile numbers)
    recipients_count = c.execute("SELECT count(DISTINCT mobile_number) FROM parcels WHERE lower(district) = ? AND mobile_number IS NOT NULL AND length(mobile_number) >= 10", (d_lower,)).fetchone()[0]

    success_rate = round((delivered / total_sent * 100), 1) if total_sent > 0 else 100.0

    c.close()

    return {
        "district": district,
        "total_sent": total_sent,
        "sent_today": sent_today,
        "delivered": delivered,
        "pending": pending,
        "failed": failed,
        "success_rate": success_rate,
        "delivery_rate": f"{success_rate}%",
        "district_recipients": recipients_count,
        "total_district_parcels": total_parcels,
        "valid_mobile_parcels": valid_mobile_parcels,
        "missing_mobile_parcels": missing_mobile_parcels,
        "gateway_status": "LIVE SMPP" if (SMPP_ENABLED and SMPP_HOST) else "DEMO MODE",
        "smpp_enabled": SMPP_ENABLED
    }

def get_state_sms_stats() -> dict:
    """Return aggregated SMS statistics across all 5 districts for State Authority."""
    c = get_db()
    districts = ["Coimbatore", "Tiruppur", "Namakkal", "Erode", "Salem"]
    breakdown = {}
    districts_list = []
    grand_total = grand_delivered = grand_pending = grand_failed = 0
    grand_parcels = grand_valid_mobile = 0

    for d in districts:
        st = get_sms_stats(d)
        breakdown[d] = st
        districts_list.append(st)
        grand_total += st["total_sent"]
        grand_delivered += st["delivered"]
        grand_pending += st["pending"]
        grand_failed += st["failed"]
        grand_parcels += st.get("total_district_parcels", 0)
        grand_valid_mobile += st.get("valid_mobile_parcels", 0)

    c.close()
    overall_rate = round((grand_delivered / grand_total * 100), 1) if grand_total > 0 else 100.0
    return {
        "grand_total": grand_total,
        "grand_delivered": grand_delivered,
        "grand_pending": grand_pending,
        "grand_failed": grand_failed,
        "success_rate": overall_rate,
        "delivery_rate": f"{overall_rate}%",
        "state_totals": {
            "total_sent": grand_total,
            "delivered": grand_delivered,
            "pending": grand_pending,
            "failed": grand_failed,
            "delivery_rate": f"{overall_rate}%",
            "total_parcels": grand_parcels,
            "valid_mobile_parcels": grand_valid_mobile
        },
        "districts": districts_list,
        "districts_breakdown": breakdown
    }

def smpp_health() -> dict:
    """Check SMPP gateway status and configuration."""
    return {
        "smpp_enabled": SMPP_ENABLED,
        "configured": bool(SMPP_HOST and SMPP_SYSTEM_ID),
        "host": SMPP_HOST or "Unconfigured",
        "port": SMPP_PORT,
        "source_addr": SMPP_SOURCE_ADDR,
        "mode": "LIVE_SMPP" if (SMPP_ENABLED and SMPP_HOST) else "DEMO_MODE",
        "provider": "SMPP v3.4" if (SMPP_ENABLED and SMPP_HOST) else "DEMO (Safe Simulation)",
        "notice": "SMS Gateway: DEMO MODE (Safe Simulation)" if not (SMPP_ENABLED and SMPP_HOST) else "SMS Gateway: LIVE SMPP Active"
    }
