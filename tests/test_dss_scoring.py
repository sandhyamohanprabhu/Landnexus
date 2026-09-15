import pytest
from backend.dss_engine import (
    compute_data_quality,
    compute_gis_risk,
    compute_parcel_score,
    compute_project_score,
    compute_district_score,
    compute_state_score,
    compute_bottlenecks,
    compute_early_warnings
)
from backend.dss_rules import generate_parcel_recommendation, explain_dss_assessment

def test_data_quality_scoring():
    # 1. Complete parcel
    p_full = {
        "record_id": "P-101", "survey_no": "12/1", "village": "Othakkalmandapam",
        "taluk": "Madukkarai", "district": "Coimbatore", "area": 1.5,
        "classification": "Dry Land", "project_id": "PRJ-001",
        "latitude": 10.89, "longitude": 76.99, "validation_status": "Valid",
        "owner_reference": "Murugan"
    }
    score, missing = compute_data_quality(p_full)
    assert score == 100.0
    assert len(missing) == 0

    # 2. Incomplete parcel
    p_inc = {"record_id": "P-102", "district": "Coimbatore"}
    score_inc, missing_inc = compute_data_quality(p_inc)
    assert score_inc < 30.0
    assert "latitude" in missing_inc
    assert "longitude" in missing_inc

def test_gis_risk_scoring():
    # 1. Missing coordinates & missing boundary
    p_risky = {"latitude": None, "longitude": None, "boundary_geojson": None, "area": 0}
    score, reasons = compute_gis_risk(p_risky)
    assert score >= 70.0
    assert any("GPS coordinates" in r for r in reasons)
    assert any("Boundary" in r for r in reasons)

    # 2. Valid coordinates & closed polygon boundary
    valid_poly = "[[10.9, 77.0], [10.91, 77.0], [10.91, 77.01], [10.9, 77.0]]"
    p_safe = {"latitude": 10.90, "longitude": 77.00, "boundary_geojson": valid_poly, "area": 2.5}
    score_safe, reasons_safe = compute_gis_risk(p_safe)
    assert score_safe <= 30.0

def test_parcel_score_computation():
    res = compute_parcel_score(1)
    if res:
        assert "priority_score" in res
        assert res["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
        assert "components" in res
        assert "confidence" in res
        rec = generate_parcel_recommendation(res)
        assert "recommendation" in rec
        assert "suggested_actions" in rec

def test_bottleneck_detection():
    btn = compute_bottlenecks()
    assert "stages" in btn
    assert "primary_bottleneck" in btn

def test_early_warnings():
    ew = compute_early_warnings()
    assert "warnings" in ew
    assert isinstance(ew["warnings"], list)
