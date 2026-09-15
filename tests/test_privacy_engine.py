"""
SURVI / LANDNEXUS — Purpose-Aware Acquisition Privacy Guard
Unit Tests for Detection, Masking, Risk Scoring, and Purpose-Aware Decision Engine
"""

import pytest
from backend.services.privacy_service import (
    detect_sensitive_entities,
    calculate_privacy_risk_score,
    resolve_field_visibility,
    evaluate_document_privacy,
    mask_aadhaar,
    mask_pan,
    mask_mobile,
    mask_bank_account,
    mask_ifsc,
    mask_email,
    hash_sensitive_value,
    CAT_CRITICAL,
    CAT_SENSITIVE,
    CAT_CONTROLLED,
    CAT_OPERATIONAL,
    VIS_VISIBLE,
    VIS_MASKED,
    VIS_REDACTED,
    VIS_AUTHORIZED
)


def test_masking_functions():
    # Aadhaar masking
    assert mask_aadhaar("123456789012") == "XXXX XXXX 9012"
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    assert mask_aadhaar("123456789012", full_mask=True) == "XXXXXXXXXXXX"
    assert mask_aadhaar("") == "XXXX XXXX XXXX"

    # PAN masking
    assert mask_pan("ABCDE1234F") == "XXXXXX1234F"
    assert mask_pan("") == "XXXXXXXXXX"

    # Mobile masking
    assert mask_mobile("9876543210") == "XXXXXX3210"
    assert mask_mobile("+91-9876543210") == "XXXXXX3210"

    # Bank Account masking
    assert mask_bank_account("1234567890123456") == "XXXXXXXXXXXX3456"

    # IFSC masking
    assert mask_ifsc("SBIN0001234") == "SBIN000XXXX"

    # Email masking
    assert mask_email("john.doe@example.com") == "j***e@example.com"


def test_sensitive_entity_detection_critical():
    raw_text = """
    GOVERNMENT OF TAMIL NADU - LAND ACQUISITION
    Pattadar: Ramesh Kumar
    Survey No: 142/3A
    Village: Sulur, Taluk: Sulur, District: Coimbatore
    Aadhaar Number: 4523 7891 2345
    PAN: ABCDE1234F
    Bank Account: 50100234567891
    IFSC: HDFC0001234
    Mobile: 9845123456
    """
    detections = detect_sensitive_entities(raw_text)
    detected_keys = {d["field_key"]: d for d in detections}

    assert "aadhaar_number" in detected_keys
    assert detected_keys["aadhaar_number"]["category"] == CAT_CRITICAL
    assert detected_keys["aadhaar_number"]["masked_value"] == "XXXX XXXX 2345"

    assert "pan_number" in detected_keys
    assert detected_keys["pan_number"]["category"] == CAT_CRITICAL
    assert detected_keys["pan_number"]["masked_value"] == "XXXXXX1234F"

    assert "bank_account_number" in detected_keys
    assert detected_keys["bank_account_number"]["category"] == CAT_CRITICAL
    assert "7891" in detected_keys["bank_account_number"]["masked_value"]

    assert "ifsc_code" in detected_keys
    assert detected_keys["ifsc_code"]["category"] == CAT_CRITICAL

    assert "mobile_number" in detected_keys
    assert detected_keys["mobile_number"]["category"] == CAT_SENSITIVE
    assert detected_keys["mobile_number"]["masked_value"] == "XXXXXX3456"

    assert "survey_number" in detected_keys
    assert detected_keys["survey_number"]["category"] == CAT_OPERATIONAL


def test_deterministic_privacy_risk_score():
    # Document with Critical + Sensitive fields
    detections = [
        {"category": CAT_CRITICAL, "field_key": "aadhaar_number"},
        {"category": CAT_CRITICAL, "field_key": "pan_number"},
        {"category": CAT_CRITICAL, "field_key": "bank_account_number"},
        {"category": CAT_SENSITIVE, "field_key": "mobile_number"},
        {"category": CAT_CONTROLLED, "field_key": "owner_name"},
        {"category": CAT_OPERATIONAL, "field_key": "survey_number"}
    ]
    risk = calculate_privacy_risk_score(detections)
    assert risk["score"] >= 75
    assert risk["level"] == "CRITICAL"
    assert risk["counts"]["critical"] == 3
    assert risk["counts"]["sensitive"] == 1

    # Low risk operational-only document
    op_detections = [
        {"category": CAT_OPERATIONAL, "field_key": "survey_number"},
        {"category": CAT_OPERATIONAL, "field_key": "land_area"},
        {"category": CAT_OPERATIONAL, "field_key": "village"}
    ]
    low_risk = calculate_privacy_risk_score(op_detections)
    assert low_risk["score"] == 0
    assert low_risk["level"] == "LOW"


def test_purpose_and_role_visibility_rules():
    # Acquisition Officer in standard processing: Aadhaar is MASKED, Survey No is VISIBLE
    res_aadhaar = resolve_field_visibility(
        field_key="aadhaar_number",
        category=CAT_CRITICAL,
        user_role="acquisition_officer",
        purpose="land_acquisition_processing"
    )
    assert res_aadhaar["visibility"] == VIS_MASKED
    assert res_aadhaar["requires_authorization"] is True
    assert "minimisation" in res_aadhaar["explain_mask"].lower() or "not required" in res_aadhaar["reason_why"].lower()

    res_survey = resolve_field_visibility(
        field_key="survey_number",
        category=CAT_OPERATIONAL,
        user_role="acquisition_officer",
        purpose="land_acquisition_processing"
    )
    assert res_survey["visibility"] == VIS_VISIBLE
    assert res_survey["requires_authorization"] is False

    # Field Officer for Field Verification: Mobile is MASKED by default until approved
    res_mobile_fo = resolve_field_visibility(
        field_key="mobile_number",
        category=CAT_SENSITIVE,
        user_role="field_officer",
        purpose="field_verification"
    )
    assert res_mobile_fo["visibility"] == VIS_MASKED
    assert res_mobile_fo["requires_authorization"] is True

    # Active temporary access grant overrides to AUTHORIZED
    res_grant = resolve_field_visibility(
        field_key="mobile_number",
        category=CAT_SENSITIVE,
        user_role="field_officer",
        purpose="field_verification",
        has_active_grant=True
    )
    assert res_grant["visibility"] == VIS_AUTHORIZED
    assert res_grant["requires_authorization"] is False


def test_external_sharing_and_public_report_modes():
    # Public reporting mode: all sensitive/critical fields are REDACTED, operational visible
    res_pub_aadhaar = resolve_field_visibility(
        field_key="aadhaar_number",
        category=CAT_CRITICAL,
        user_role="acquisition_officer",
        purpose="public_reporting",
        is_external=True,
        recipient_type="public_report"
    )
    assert res_pub_aadhaar["visibility"] == VIS_REDACTED

    res_pub_survey = resolve_field_visibility(
        field_key="survey_number",
        category=CAT_OPERATIONAL,
        user_role="acquisition_officer",
        purpose="public_reporting",
        is_external=True,
        recipient_type="public_report"
    )
    assert res_pub_survey["visibility"] == VIS_VISIBLE


def test_full_document_privacy_evaluation_never_exposes_raw_unauthorized():
    detections = [
        {
            "field_key": "aadhaar_number",
            "field_label": "Aadhaar Number",
            "category": CAT_CRITICAL,
            "raw_detected": "4523 7891 2345",
            "masked_value": "XXXX XXXX 2345",
            "hash_ref": hash_sensitive_value("4523 7891 2345")
        },
        {
            "field_key": "survey_number",
            "field_label": "Survey Number",
            "category": CAT_OPERATIONAL,
            "raw_detected": "142/3A",
            "masked_value": "142/3A",
            "hash_ref": hash_sensitive_value("142/3A")
        }
    ]

    eval_result = evaluate_document_privacy(
        document_id="DOC-TEST-001",
        detections=detections,
        user_role="acquisition_officer",
        user_email="officer@tngov.in",
        purpose="land_acquisition_processing"
    )

    aadhaar_field = next(f for f in eval_result["fields"] if f["field_key"] == "aadhaar_number")
    survey_field = next(f for f in eval_result["fields"] if f["field_key"] == "survey_number")

    # CRITICAL TEST: Unauthorized client must NOT receive raw Aadhaar in display_value!
    assert aadhaar_field["visibility"] == VIS_MASKED
    assert aadhaar_field["display_value"] == "XXXX XXXX 2345"
    assert "4523 7891" not in aadhaar_field["display_value"]

    # Operational field is visible
    assert survey_field["visibility"] == VIS_VISIBLE
    assert survey_field["display_value"] == "142/3A"
