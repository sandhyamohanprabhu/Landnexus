"""
SURVI / LANDNEXUS — Purpose-Aware Acquisition Privacy Guard Service
Core detection, classification, server-side masking, and explainability engine.
"""

import re
import hashlib
import json
from datetime import datetime, timezone

# ─── Categories ───
CAT_CRITICAL = "CRITICAL"
CAT_SENSITIVE = "SENSITIVE"
CAT_CONTROLLED = "CONTROLLED"
CAT_OPERATIONAL = "OPERATIONAL"

# ─── Visibility Decisions ───
VIS_VISIBLE = "VISIBLE"
VIS_MASKED = "MASKED"
VIS_REDACTED = "REDACTED"
VIS_AUTHORIZED = "AUTHORIZED"

# ─── Standard Operational Purposes ───
PURPOSES = [
    {"code": "land_acquisition_processing", "label": "Land Acquisition Processing"},
    {"code": "field_verification", "label": "Field Verification"},
    {"code": "citizen_contact", "label": "Citizen Contact & Outreach"},
    {"code": "compensation_verification", "label": "Compensation & DBT Verification"},
    {"code": "legal_proceedings", "label": "Legal Proceedings & Dispute Review"},
    {"code": "document_validation", "label": "Document Validation & Title Search"},
    {"code": "audit", "label": "Audit & Governance Compliance"},
    {"code": "external_sharing", "label": "External Agency / Contractor Sharing"},
    {"code": "public_reporting", "label": "Public-Safe Reporting"},
    {"code": "general_review", "label": "General Operational Review"}
]


# ═══════════════════════════════════════════════════════════════
# 1. SENSITIVE DATA PATTERNS & REGEX (INDIAN CONTEXT)
# ═══════════════════════════════════════════════════════════════

# Aadhaar: 12 digits, cannot start with 0 or 1, optionally separated by space or hyphen
AADHAAR_REGEX = re.compile(r'\b[2-9]\d{3}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b')

# PAN: 5 uppercase letters, 4 digits, 1 uppercase letter
PAN_REGEX = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')

# Indian Mobile: 10 digits starting with 6, 7, 8, 9, optional +91 or 0 prefix
MOBILE_REGEX = re.compile(r'(?:(?:\+91[\-\s]?)|(?:\b0))?[6-9]\d{9}\b')

# Email Address
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b')

# IFSC Code: 4 alphabetic chars, 0, 6 alphanumeric chars
IFSC_REGEX = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')

# Bank Account: 9 to 18 digits in typical banking context
BANK_ACCOUNT_CONTEXT_REGEX = re.compile(
    r'(?:A/C|Account(?:\s*No\.?)?|Acc(?:\s*No\.?)?|Bank\s*Account|SB\s*A/C|Savings\s*A/c|Current\s*A/c)[\s:]*([0-9]{9,18})\b',
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════
# 2. SERVER-SIDE MASKING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def mask_aadhaar(val: str, full_mask: bool = False) -> str:
    """Mask Aadhaar to 'XXXX XXXX 9012' or 'XXXXXXXXXXXX'."""
    if not val:
        return "XXXX XXXX XXXX"
    digits = re.sub(r'\D', '', val)
    if len(digits) >= 12:
        if full_mask:
            return "XXXXXXXXXXXX"
        return f"XXXX XXXX {digits[-4:]}"
    return "XXXX XXXX XXXX"


def mask_pan(val: str) -> str:
    """Mask PAN to 'XXXXXX1234F'."""
    if not val:
        return "XXXXXXXXXX"
    clean = val.strip().upper()
    if len(clean) == 10:
        return f"XXXXXX{clean[5:]}"
    return "XXXXXXXXXX"


def mask_mobile(val: str) -> str:
    """Mask Mobile to 'XXXXXX3210'."""
    if not val:
        return "XXXXXXXXXX"
    digits = re.sub(r'\D', '', val)
    if len(digits) >= 10:
        return f"XXXXXX{digits[-4:]}"
    return "XXXXXXXXXX"


def mask_bank_account(val: str) -> str:
    """Mask Bank Account to 'XXXXXXXXXXXX3456'."""
    if not val:
        return "XXXXXXXXXXXX"
    digits = re.sub(r'\D', '', val)
    if len(digits) >= 4:
        return "X" * max(len(digits) - 4, 8) + digits[-4:]
    return "XXXXXXXXXXXX"


def mask_ifsc(val: str) -> str:
    """Mask IFSC to 'SBIN000XXXX'."""
    if not val:
        return "XXXXXXXXXXX"
    clean = val.strip().upper()
    if len(clean) == 11:
        return f"{clean[:7]}XXXX"
    return "XXXXXXXXXXX"


def mask_email(val: str) -> str:
    """Mask Email to 'j***e@domain.com'."""
    if not val or "@" not in val:
        return "***@***.***"
    parts = val.split("@", 1)
    local, domain = parts[0], parts[1]
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def mask_text(val: str, label: str = "CONFIDENTIAL") -> str:
    """Generic text masking."""
    if not val:
        return "[REDACTED]"
    if len(val) <= 4:
        return "████"
    return f"{val[:2]}████████{val[-2:]}"


def hash_sensitive_value(val: str) -> str:
    """Generate non-reversible salt-hashed fingerprint for audit references."""
    if not val:
        return ""
    salt = "LANDNEXUS-PRIVACY-SALT-2026"
    return hashlib.sha256((salt + val.strip()).encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════
# 3. SENSITIVE ENTITY DETECTOR
# ═══════════════════════════════════════════════════════════════

def detect_sensitive_entities(text: str, extractions: dict = None) -> list:
    """
    Scans raw OCR text and structured extractions for sensitive, controlled,
    and operational entities. Returns structured list of detections.
    """
    detections = []
    seen_keys = set()

    text_to_scan = text or ""
    extracted = extractions or {}

    # 1. Aadhaar Detection
    aadhaar_match = AADHAAR_REGEX.search(text_to_scan)
    aadhaar_val = extracted.get("aadhaar") or extracted.get("aadhaar_number") or (aadhaar_match.group(0) if aadhaar_match else None)
    if aadhaar_val:
        detections.append({
            "field_key": "aadhaar_number",
            "field_label": "Aadhaar Number",
            "category": CAT_CRITICAL,
            "raw_detected": aadhaar_val,
            "masked_value": mask_aadhaar(aadhaar_val),
            "hash_ref": hash_sensitive_value(aadhaar_val),
            "confidence": 0.95 if aadhaar_match else 0.90,
            "detection_method": "regex_pattern + contextual label"
        })
        seen_keys.add("aadhaar_number")

    # 2. PAN Detection
    pan_match = PAN_REGEX.search(text_to_scan)
    pan_val = extracted.get("pan") or extracted.get("pan_number") or (pan_match.group(0) if pan_match else None)
    if pan_val:
        detections.append({
            "field_key": "pan_number",
            "field_label": "Income Tax PAN",
            "category": CAT_CRITICAL,
            "raw_detected": pan_val,
            "masked_value": mask_pan(pan_val),
            "hash_ref": hash_sensitive_value(pan_val),
            "confidence": 0.95 if pan_match else 0.88,
            "detection_method": "regex_pattern"
        })
        seen_keys.add("pan_number")

    # 3. Bank Account Detection
    bank_match = BANK_ACCOUNT_CONTEXT_REGEX.search(text_to_scan)
    bank_val = extracted.get("bank_account") or extracted.get("account_number") or (bank_match.group(1) if bank_match else None)
    if bank_val:
        detections.append({
            "field_key": "bank_account_number",
            "field_label": "Bank Account Number",
            "category": CAT_CRITICAL,
            "raw_detected": bank_val,
            "masked_value": mask_bank_account(bank_val),
            "hash_ref": hash_sensitive_value(bank_val),
            "confidence": 0.92 if bank_match else 0.85,
            "detection_method": "contextual_regex + extraction"
        })
        seen_keys.add("bank_account_number")

    # 4. IFSC Code
    ifsc_match = IFSC_REGEX.search(text_to_scan)
    ifsc_val = extracted.get("ifsc") or extracted.get("ifsc_code") or (ifsc_match.group(0) if ifsc_match else None)
    if ifsc_val:
        detections.append({
            "field_key": "ifsc_code",
            "field_label": "Bank IFSC Code",
            "category": CAT_CRITICAL,
            "raw_detected": ifsc_val,
            "masked_value": mask_ifsc(ifsc_val),
            "hash_ref": hash_sensitive_value(ifsc_val),
            "confidence": 0.90,
            "detection_method": "regex_pattern"
        })
        seen_keys.add("ifsc_code")

    # 5. Mobile Number
    mobile_match = MOBILE_REGEX.search(text_to_scan)
    mobile_val = extracted.get("mobile") or extracted.get("phone") or (mobile_match.group(0) if mobile_match else None)
    if mobile_val:
        detections.append({
            "field_key": "mobile_number",
            "field_label": "Primary Contact / Mobile",
            "category": CAT_SENSITIVE,
            "raw_detected": mobile_val,
            "masked_value": mask_mobile(mobile_val),
            "hash_ref": hash_sensitive_value(mobile_val),
            "confidence": 0.90,
            "detection_method": "regex_pattern"
        })
        seen_keys.add("mobile_number")

    # 6. Personal Email
    email_match = EMAIL_REGEX.search(text_to_scan)
    email_val = extracted.get("email") or (email_match.group(0) if email_match else None)
    if email_val:
        detections.append({
            "field_key": "personal_email",
            "field_label": "Personal Email",
            "category": CAT_SENSITIVE,
            "raw_detected": email_val,
            "masked_value": mask_email(email_val),
            "hash_ref": hash_sensitive_value(email_val),
            "confidence": 0.95,
            "detection_method": "regex_pattern"
        })
        seen_keys.add("personal_email")

    # 7. Signature / Biometric Indicators
    sig_search = re.search(r'(?:Signature|Sign|Thumb\s*Impression|Digitally\s*Signed|Left\s*Thumb)', text_to_scan, re.IGNORECASE)
    if sig_search or extracted.get("signature_present"):
        detections.append({
            "field_key": "signature_biometric",
            "field_label": "Signature / Biometric Stamp",
            "category": CAT_SENSITIVE,
            "raw_detected": "Signature / Stamp Present",
            "masked_value": "████████ [SIGNATURE SEALED]",
            "hash_ref": hash_sensitive_value("SIGNATURE_STAMP"),
            "confidence": 0.85,
            "detection_method": "contextual_indicator"
        })
        seen_keys.add("signature_biometric")

    # 8. Heir / Family Relations
    heir_match = re.search(r'(?:S/o|D/o|W/o|H/o|Son of|Daughter of|Wife of|Legal Heir)[\s:]*([A-Za-z\s]+)', text_to_scan, re.IGNORECASE)
    if heir_match or extracted.get("family_relation"):
        h_val = extracted.get("family_relation") or heir_match.group(1).strip().split('\n')[0]
        detections.append({
            "field_key": "family_heir_details",
            "field_label": "Family / Legal Heir Info",
            "category": CAT_SENSITIVE,
            "raw_detected": h_val,
            "masked_value": mask_text(h_val, "FAMILY HEIR"),
            "hash_ref": hash_sensitive_value(h_val),
            "confidence": 0.80,
            "detection_method": "contextual_relation"
        })
        seen_keys.add("family_heir_details")

    # 9. Owner Name (Controlled)
    owner_val = extracted.get("owner_name")
    if not owner_val:
        owner_match = re.search(r'(?:Owner Name|Owner|Name of Pattadhar|Pattadar)[\s:]*([A-Za-z\s\.]+)', text_to_scan, re.IGNORECASE)
        if owner_match:
            owner_val = owner_match.group(1).strip().split('\n')[0]
    if owner_val:
        detections.append({
            "field_key": "owner_name",
            "field_label": "Registered Landowner Name",
            "category": CAT_CONTROLLED,
            "raw_detected": owner_val,
            "masked_value": owner_val,
            "hash_ref": hash_sensitive_value(owner_val),
            "confidence": 0.90,
            "detection_method": "ocr_extraction + contextual label"
        })
        seen_keys.add("owner_name")

    # 10. Compensation Details (Controlled)
    comp_match = re.search(r'(?:Compensation|Award Amount|Disbursement|Total Amount)[\s:]*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{1,2})?)', text_to_scan, re.IGNORECASE)
    comp_val = extracted.get("compensation_amount") or (comp_match.group(1) if comp_match else None)
    if comp_val:
        detections.append({
            "field_key": "compensation_details",
            "field_label": "Awarded Compensation Amount",
            "category": CAT_CONTROLLED,
            "raw_detected": f"₹ {comp_val}",
            "masked_value": "₹ ██████ [CONTROLLED DISCLOSURE]",
            "hash_ref": hash_sensitive_value(str(comp_val)),
            "confidence": 0.88,
            "detection_method": "contextual_amount"
        })
        seen_keys.add("compensation_details")

    # 11. Operational Fields (Survey Number, Land Area, Village, Taluk, District, Doc Date, Doc No)
    op_mapping = [
        ("survey_number", "Survey Number", extracted.get("survey_number") or _search_op(text_to_scan, r'(?:Survey No|Survey Number|S\.No)[\s:]*([0-9A-Za-z/]+)')),
        ("land_area", "Acquisition Area / Extent", extracted.get("land_area") or _search_op(text_to_scan, r'(?:Land Area|Area|Extent)[\s:]*([0-9.]+\s*(?:acres|sqft|hectares|cents|acre))')),
        ("village", "Village", extracted.get("village") or _search_op(text_to_scan, r'(?:Village)[\s:]*([A-Za-z]+)')),
        ("taluk", "Taluk", extracted.get("taluk") or _search_op(text_to_scan, r'(?:Taluk)[\s:]*([A-Za-z]+)')),
        ("district", "District", extracted.get("district") or _search_op(text_to_scan, r'(?:District)[\s:]*([A-Za-z]+)')),
        ("document_number", "Document / Deed Number", extracted.get("document_number") or _search_op(text_to_scan, r'(?:Document No|Doc No)[\s:]*([0-9A-Za-z-]+)')),
        ("document_date", "Document Registration Date", extracted.get("document_date") or _search_op(text_to_scan, r'(?:Date)[\s:]*([0-9]{2,4}[-/][0-9]{2}[-/][0-9]{2,4})'))
    ]

    for key, label, val in op_mapping:
        if val and key not in seen_keys:
            detections.append({
                "field_key": key,
                "field_label": label,
                "category": CAT_OPERATIONAL,
                "raw_detected": str(val).strip(),
                "masked_value": str(val).strip(),
                "hash_ref": hash_sensitive_value(str(val)),
                "confidence": 0.90,
                "detection_method": "ocr_extraction"
            })
            seen_keys.add(key)

    return detections


def _search_op(text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


# ═══════════════════════════════════════════════════════════════
# 4. DETERMINISTIC PRIVACY RISK SCORING
# ═══════════════════════════════════════════════════════════════

def calculate_privacy_risk_score(detections: list, is_external: bool = False, sharing_recipient: str = None) -> dict:
    """
    Computes a deterministic, application-level decision-support privacy risk score (0-100).
    Not a legal rating; provided for objective purpose-based risk assessment.
    """
    crit_count = sum(1 for d in detections if d["category"] == CAT_CRITICAL)
    sens_count = sum(1 for d in detections if d["category"] == CAT_SENSITIVE)
    ctrl_count = sum(1 for d in detections if d["category"] == CAT_CONTROLLED)
    oper_count = sum(1 for d in detections if d["category"] == CAT_OPERATIONAL)

    # Base weighted formula
    raw_score = (crit_count * 25) + (sens_count * 15) + (ctrl_count * 5)

    if is_external:
        raw_score += 15
        if sharing_recipient in ("public_report", "contractor", "consultant"):
            raw_score += 10

    score = min(max(raw_score, 0), 100)

    if score >= 75:
        level = "CRITICAL"
        desc = "Contains high-risk financial or national identity numbers (Aadhaar/PAN/Bank). Strict masking mandatory."
    elif score >= 50:
        level = "HIGH"
        desc = "Contains direct contact or personal identifiers. Purpose-aware masking enforced."
    elif score >= 25:
        level = "MEDIUM"
        desc = "Contains controlled landowner or compensation data. Standard government disclosure rules apply."
    else:
        level = "LOW"
        desc = "Primarily operational land survey & geospatial identifiers. Low risk of individual privacy breach."

    return {
        "score": score,
        "level": level,
        "description": desc,
        "counts": {
            "critical": crit_count,
            "sensitive": sens_count,
            "controlled": ctrl_count,
            "operational": oper_count,
            "total": len(detections)
        },
        "factors": [
            f"{crit_count} Critical National / Financial Identifiers (Aadhaar, PAN, Bank)",
            f"{sens_count} Sensitive Personal Identifiers (Mobile, Email, Signature)",
            f"{ctrl_count} Controlled Landowner / Compensation Records",
            f"{oper_count} Operational Land & Geospatial Fields"
        ]
    }


# ═══════════════════════════════════════════════════════════════
# 5. PURPOSE-AWARE VISIBILITY & EXPLAINABILITY ENGINE
# ═══════════════════════════════════════════════════════════════

def resolve_field_visibility(
    field_key: str,
    category: str,
    user_role: str,
    purpose: str,
    has_active_grant: bool = False,
    is_external: bool = False,
    recipient_type: str = None
) -> dict:
    """
    Determines whether a field should be VISIBLE, MASKED, REDACTED, or AUTHORIZED,
    and provides explainable reasons for 'Why is this masked?' and 'Why can I see this?'.
    
    FAIL-SAFE: Defaults to MASKED for any ambiguous or unauthorized sensitive field.
    """
    # 1. Active temporary access grant overrides for specific field
    if has_active_grant:
        return {
            "visibility": VIS_AUTHORIZED,
            "reason_why": f"Temporary access explicitly granted and authorized for purpose '{purpose}'.",
            "requires_authorization": False,
            "explain_mask": "Authorized under approved temporary access request.",
            "explain_visible": f"Disclosed under approved temporary access for purpose '{purpose}'."
        }

    # 2. Public-Safe Reporting Mode
    if is_external and recipient_type == "public_report":
        if category == CAT_OPERATIONAL:
            return {
                "visibility": VIS_VISIBLE,
                "reason_why": "Operational land data permitted for public transparency.",
                "requires_authorization": False,
                "explain_mask": "N/A",
                "explain_visible": "Required for public notice & project transparency."
            }
        return {
            "visibility": VIS_REDACTED,
            "reason_why": "Redacted: Personal & sensitive data strictly prohibited from public reports.",
            "requires_authorization": True,
            "explain_mask": "Public disclosure prohibited under data minimisation guidelines.",
            "explain_visible": "N/A"
        }

    # 3. External Agency / Contractor Sharing Mode
    if is_external:
        if category == CAT_OPERATIONAL:
            return {
                "visibility": VIS_VISIBLE,
                "reason_why": "Operational parcel details required for contractor boundary work.",
                "requires_authorization": False,
                "explain_mask": "N/A",
                "explain_visible": "Required for site alignment and survey work."
            }
        elif category == CAT_CONTROLLED and recipient_type == "interdepartmental":
            return {
                "visibility": VIS_VISIBLE,
                "reason_why": "Interdepartmental review permitted for land title verification.",
                "requires_authorization": False,
                "explain_mask": "N/A",
                "explain_visible": "Shared under interdepartmental land acquisition coordination."
            }
        else:
            return {
                "visibility": VIS_MASKED,
                "reason_why": "Personal & financial identifiers masked for external distribution.",
                "requires_authorization": True,
                "explain_mask": "External parties do not have legitimate need for citizen personal identifiers.",
                "explain_visible": "N/A"
            }

    # 4. Role + Purpose Based Rules (Internal Platform)

    # Operational fields are always visible to authenticated government users
    if category == CAT_OPERATIONAL:
        return {
            "visibility": VIS_VISIBLE,
            "reason_why": "Required for parcel identification and land acquisition workflow.",
            "requires_authorization": False,
            "explain_mask": "N/A",
            "explain_visible": "Essential operational metadata required for all acquisition stages."
        }

    # Controlled fields (Owner Name, Compensation)
    if category == CAT_CONTROLLED:
        if user_role in ("authority", "admin", "state_authority", "district_authority", "acquisition_officer"):
            return {
                "visibility": VIS_VISIBLE,
                "reason_why": f"Visible to {user_role.replace('_', ' ').title()} for acquisition management.",
                "requires_authorization": False,
                "explain_mask": "N/A",
                "explain_visible": "Necessary for official land title and compensation determination."
            }
        elif user_role == "field_officer":
            if field_key == "owner_name":
                return {
                    "visibility": VIS_VISIBLE,
                    "reason_why": "Visible to Field Officer for on-ground parcel owner identification.",
                    "requires_authorization": False,
                    "explain_mask": "N/A",
                    "explain_visible": "Required to verify identity during physical site inspection."
                }
            else:
                return {
                    "visibility": VIS_MASKED,
                    "reason_why": "Compensation disbursement data not required for physical field survey.",
                    "requires_authorization": True,
                    "explain_mask": "Financial awards are managed by District Authority / SLA cell.",
                    "explain_visible": "N/A"
                }
        elif user_role == "citizen":
            return {
                "visibility": VIS_VISIBLE,
                "reason_why": "Landowner entitlement & compensation status.",
                "requires_authorization": False,
                "explain_mask": "N/A",
                "explain_visible": "Citizen transparent view of own parcel records."
            }

    # Sensitive fields (Mobile, Email, Signature, Family)
    if category == CAT_SENSITIVE:
        if purpose in ("citizen_contact", "field_verification") and user_role in ("authority", "admin", "district_authority", "acquisition_officer"):
            return {
                "visibility": VIS_VISIBLE,
                "reason_why": f"Authorized for active purpose '{purpose.replace('_', ' ').title()}'.",
                "requires_authorization": False,
                "explain_mask": "N/A",
                "explain_visible": f"Citizen contact information permitted for '{purpose.replace('_', ' ')}'."
            }
        elif purpose == "field_verification" and user_role == "field_officer" and field_key == "mobile_number":
            return {
                "visibility": VIS_MASKED,
                "reason_why": "Masked by default. Request temporary 24h access for field verification.",
                "requires_authorization": True,
                "explain_mask": "Direct phone number requires temporary access request for audit logging.",
                "explain_visible": "N/A"
            }
        else:
            return {
                "visibility": VIS_MASKED,
                "reason_why": f"Not required for current operational purpose '{purpose.replace('_', ' ')}'. Data minimisation applied.",
                "requires_authorization": True,
                "explain_mask": f"Personal contact & biometric identifiers are masked to prevent unauthorized disclosure during {purpose.replace('_', ' ')}.",
                "explain_visible": "N/A"
            }

    # Critical fields (Aadhaar, PAN, Bank Account, IFSC)
    if category == CAT_CRITICAL:
        if purpose == "compensation_verification" and user_role in ("authority", "admin", "district_authority"):
            return {
                "visibility": VIS_MASKED,
                "reason_why": "Critical financial identifiers masked by default. Controlled unmasking requires temporary access grant.",
                "requires_authorization": True,
                "explain_mask": "National & Banking identifiers are masked by default under strict data minimisation.",
                "explain_visible": "N/A"
            }
        elif purpose == "audit" and user_role in ("authority", "admin"):
            return {
                "visibility": VIS_MASKED,
                "reason_why": "Audit review uses masked records and cryptographic hash fingerprints.",
                "requires_authorization": True,
                "explain_mask": "Audit ledgers must not display raw unmasked national identifiers.",
                "explain_visible": "N/A"
            }
        else:
            return {
                "visibility": VIS_MASKED,
                "reason_why": f"Critical identity identifier not required for operational purpose '{purpose.replace('_', ' ')}'.",
                "requires_authorization": True,
                "explain_mask": "National ID & Bank account numbers are strictly masked unless temporary access is approved by District Authority.",
                "explain_visible": "N/A"
            }

    # Fail-closed default
    return {
        "visibility": VIS_MASKED,
        "reason_why": "Defaulting to secure masked state (fail-closed policy).",
        "requires_authorization": True,
        "explain_mask": "Security fail-safe applied.",
        "explain_visible": "N/A"
    }


# ═══════════════════════════════════════════════════════════════
# 6. COMPLETE DOCUMENT PRIVACY EVALUATOR
# ═══════════════════════════════════════════════════════════════

def evaluate_document_privacy(
    document_id: str,
    detections: list,
    user_role: str,
    user_email: str,
    purpose: str = "land_acquisition_processing",
    active_grants: list = None,
    is_external: bool = False,
    recipient_type: str = None
) -> dict:
    """
    Evaluates privacy classifications and visibility decisions for a document's detections,
    returning server-side masked payload and governance statistics.
    """
    active_fields = set()
    if active_grants:
        for g in active_grants:
            active_fields.add(g.get("field_key"))

    evaluated_fields = []
    visible_count = 0
    masked_count = 0
    redacted_count = 0
    authorized_count = 0

    for d in detections:
        f_key = d["field_key"]
        has_grant = f_key in active_fields

        decision = resolve_field_visibility(
            field_key=f_key,
            category=d["category"],
            user_role=user_role,
            purpose=purpose,
            has_active_grant=has_grant,
            is_external=is_external,
            recipient_type=recipient_type
        )

        vis = decision["visibility"]

        # Server-side disclosure protection
        if vis in (VIS_VISIBLE, VIS_AUTHORIZED):
            display_value = d["raw_detected"]
        elif vis == VIS_REDACTED:
            display_value = "████████ [REDACTED]"
        else:
            display_value = d["masked_value"]

        if vis == VIS_VISIBLE:
            visible_count += 1
        elif vis == VIS_MASKED:
            masked_count += 1
        elif vis == VIS_REDACTED:
            redacted_count += 1
        elif vis == VIS_AUTHORIZED:
            authorized_count += 1

        evaluated_fields.append({
            "field_key": f_key,
            "field_label": d["field_label"],
            "category": d["category"],
            "visibility": vis,
            "display_value": display_value,
            "masked_value": d["masked_value"],
            "hash_ref": d["hash_ref"],
            "confidence": d.get("confidence", 1.0),
            "detection_method": d.get("detection_method", "ocr"),
            "reason_why": decision["reason_why"],
            "requires_authorization": decision["requires_authorization"],
            "explain_mask": decision["explain_mask"],
            "explain_visible": decision["explain_visible"],
            "is_authorized_grant": has_grant
        })

    risk_info = calculate_privacy_risk_score(detections, is_external, recipient_type)

    return {
        "document_id": document_id,
        "purpose": purpose,
        "user_role": user_role,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "risk_score": risk_info["score"],
        "risk_level": risk_info["level"],
        "risk_description": risk_info["description"],
        "risk_factors": risk_info["factors"],
        "summary": {
            "total_detected": len(detections),
            "visible": visible_count,
            "masked": masked_count,
            "redacted": redacted_count,
            "authorized": authorized_count,
            "critical_count": risk_info["counts"]["critical"],
            "sensitive_count": risk_info["counts"]["sensitive"],
            "controlled_count": risk_info["counts"]["controlled"],
            "operational_count": risk_info["counts"]["operational"]
        },
        "fields": evaluated_fields
    }
