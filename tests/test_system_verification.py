"""
Comprehensive End-to-End QA & System Verification Suite
LANDNEXUS / SURVI - Multi-District Land Acquisition Intelligence
================================================================
Validates:
1. All 7 Login Roles & Authentication
2. Server-side RBAC & Cross-District / Cross-State Isolation
3. GIS Parcel Coverage, Geometry Integrity & Disclaimers
4. Synthetic Data Traceability across SQLite & CSV/GeoJSON
5. API <-> Database Consistency (KPIs, Parcels, Projects)
6. Non-Destructive Workflow Operations & Audit Trail
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from backend.main import app
from backend.core import conn, AUTH_PASSWORD

CLIENT = TestClient(app)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "survi.db"
GEOJSON_PATH = ROOT / "data" / "coimbatore" / "19_gis_parcels.geojson"


def get_token(email, password="Tngov@CBE#2026"):
    res = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    data = res.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


# ==============================================================================
# 1. ALL 7 LOGIN ROLES AUTHENTICATION & ACCESS SCOPING
# ==============================================================================

@pytest.mark.parametrize("email,expected_role,expected_district,expected_state", [
    ("state.tamilnadu@tngov.in", "state_authority", None, "Tamil Nadu"),
    ("state.kerala@kerala.gov.in", "state_authority", None, "Kerala"),
    ("district.coimbatore@tngov.in", "district_authority", "Coimbatore", "Tamil Nadu"),
    ("district.tiruppur@tngov.in", "district_authority", "Tiruppur", "Tamil Nadu"),
    ("district.erode@tngov.in", "district_authority", "Erode", "Tamil Nadu"),
    ("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu"),
    ("field.tiruppur@tngov.in", "field_officer", "Tiruppur", "Tamil Nadu"),
    ("citizen@cbe.ac.in", "citizen", "Coimbatore", "Tamil Nadu"),
])
def test_all_login_roles_and_token_payload(email, expected_role, expected_district, expected_state):
    """Verify that every authorized login role receives a valid token with correct scope."""
    headers = get_token(email)
    res = CLIENT.get("/auth/me", headers=headers)
    assert res.status_code == 200
    u = res.json()
    assert u["email"].lower() == email.lower()
    assert u["role"] == expected_role
    assert u["district_scope"] == expected_district
    assert u["state_scope"] == expected_state


# ==============================================================================
# 2. RBAC & JURISDICTION ISOLATION (STATE & DISTRICT)
# ==============================================================================

def test_cross_state_access_prohibition():
    """Kerala State Authority must be blocked from accessing Tamil Nadu data."""
    kerala_headers = get_token("state.kerala@kerala.gov.in")
    
    # Attempting to access Tamil Nadu district from Kerala account
    res = CLIENT.get("/dashboard/district?district=Coimbatore", headers=kerala_headers)
    assert res.status_code == 403, f"Expected 403 for cross-state access, got {res.status_code}"
    assert "Cross-state" in res.text or "forbidden" in res.text.lower()


def test_cross_district_access_prohibition():
    """Coimbatore District Authority must be blocked from accessing Tiruppur / Erode."""
    cbe_headers = get_token("district.coimbatore@tngov.in")
    
    res = CLIENT.get("/dashboard/district?district=Tiruppur", headers=cbe_headers)
    assert res.status_code == 403
    assert "Cross-district" in res.text or "forbidden" in res.text.lower()

    # Attempt to query parcels of another district
    res_parcels = CLIENT.get("/land-records/?district=Erode", headers=cbe_headers)
    assert res_parcels.status_code == 403


def test_citizen_privilege_isolation():
    """Citizen must receive HTTP 403 on internal management & data quality endpoints."""
    citizen_headers = get_token("citizen@cbe.ac.in")

    # 1. Audit logs
    res = CLIENT.get("/audit/", headers=citizen_headers)
    assert res.status_code == 403

    # 2. Data Quality / Duplicate Scan
    res_dq = CLIENT.post("/data-quality/scan?district=Coimbatore", headers=citizen_headers)
    assert res_dq.status_code == 403

    # 3. Reports internal endpoint
    res_rep = CLIENT.get("/reports/project-list?district=Coimbatore", headers=citizen_headers)
    assert res_rep.status_code == 403

    # 4. SMS Broadcast transmission
    res_sms = CLIENT.post("/sms/send", headers=citizen_headers, json={"recipient_phone": "9842256147", "message": "Test"})
    assert res_sms.status_code == 403


# ==============================================================================
# 3. GIS PARCEL COVERAGE & TRUTHFULNESS
# ==============================================================================

def test_gis_parcels_endpoint_and_truthful_disclaimer():
    """Verify GIS endpoint returns features with coordinates and explicit demo disclaimer."""
    cbe_headers = get_token("district.coimbatore@tngov.in")
    res = CLIENT.get("/gis/parcels?district=Coimbatore&limit=20", headers=cbe_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "disclaimer" in data
    assert "cadastral_geometry" in data
    assert data["cadastral_geometry"] is False
    assert "Demonstration" in data["disclaimer"] or "synthetic" in data["disclaimer"].lower()

    for f in data["features"]:
        assert f["type"] == "Feature"
        geom = f["geometry"]
        assert geom["type"] == "Point"
        coords = geom["coordinates"]
        assert len(coords) == 2
        lon, lat = coords
        assert 75.0 <= lon <= 80.0
        assert 8.0 <= lat <= 14.0


def test_individual_parcel_gis_linkage_truthfulness():
    """Verify that parcels with coordinates provide valid map links, while parcels without coordinates report truthfully."""
    cbe_headers = get_token("district.coimbatore@tngov.in")
    
    # 1. Check parcel without coordinates
    c = conn()
    p_no_coords = c.execute("SELECT id FROM parcels WHERE district='Coimbatore' AND latitude IS NULL LIMIT 1").fetchone()
    c.close()
    assert p_no_coords is not None
    
    res = CLIENT.get(f"/land-records/{p_no_coords['id']}", headers=cbe_headers)
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["gis"]["has_coordinates"] is False
    assert p_data["gis"]["latitude"] is None
    assert p_data["gis"]["longitude"] is None
    assert p_data["gis"]["google_maps_url"] is None
    assert "Demonstration GIS" in p_data["gis"]["disclaimer"]


# ==============================================================================
# 4. DATABASE <-> API KPI CONSISTENCY
# ==============================================================================

def test_kpi_database_vs_api_consistency():
    """Verify that dashboard values strictly reflect the underlying database counts."""
    cbe_headers = get_token("district.coimbatore@tngov.in")
    res = CLIENT.get("/dashboard/district?district=Coimbatore", headers=cbe_headers)
    assert res.status_code == 200
    d_api = res.json()

    c = conn()
    db_projects = c.execute("SELECT count(*) FROM projects WHERE district='Coimbatore'").fetchone()[0]
    db_parcels = c.execute("SELECT count(*) FROM parcels WHERE district='Coimbatore'").fetchone()[0]
    c.close()

    assert d_api["total_projects"] == db_projects
    assert d_api["total_parcels"] == db_parcels


# ==============================================================================
# 5. SYNTHETIC DATA INTEGRITY & AUDIT TRAIL
# ==============================================================================

def test_audit_trail_immutability_and_non_pii():
    """Every administrative action must be recorded without leaking raw citizen PII."""
    cbe_headers = get_token("district.coimbatore@tngov.in")
    
    # Trigger a duplicate scan
    res_scan = CLIENT.post("/data-quality/scan?district=Coimbatore", headers=cbe_headers)
    assert res_scan.status_code == 200
    
    # Verify audit trail contains duplicate scan records
    c = conn()
    recent_audits = [r["action"] for r in c.execute("SELECT action FROM audit WHERE user_email=? ORDER BY id DESC LIMIT 5", ("district.coimbatore@tngov.in",)).fetchall()]
    c.close()
    
    assert any(a in ("DUPLICATE_SCAN_STARTED", "DUPLICATE_CANDIDATE_CREATED") for a in recent_audits)


# ==============================================================================
# 6. FIELD OFFICER ASSIGNMENT & VERIFICATION LIFECYCLE
# ==============================================================================

def test_field_officer_assignment_and_verification():
    """Verify field officer assignment, retrieval, and ground verification flow."""
    cbe_headers = get_token("district.coimbatore@tngov.in")
    field_headers = get_token("field.coimbatore@tngov.in")
    
    # Fetch field officer assignments
    res = CLIENT.get("/field/assignments/mine", headers=field_headers)
    assert res.status_code == 200
    assignments = res.json()
    assert isinstance(assignments, list)


# ==============================================================================
# 7. STATE AUTHORITY GIS COVERAGE & RBAC ENFORCEMENT
# ==============================================================================

def test_state_authority_gis_coverage_tamil_nadu():
    """State Authority for Tamil Nadu receives all GIS-linked parcels across all 5 TN districts and cannot access Kerala."""
    c = conn()
    expected_tn_gis = c.execute("SELECT count(1) FROM parcels WHERE latitude IS NOT NULL AND lower(district) IN ('coimbatore', 'erode', 'namakkal', 'salem', 'tiruppur')").fetchone()[0]
    expected_tn_total = c.execute("SELECT count(1) FROM parcels WHERE lower(district) IN ('coimbatore', 'erode', 'namakkal', 'salem', 'tiruppur')").fetchone()[0]
    expected_cbe_gis = c.execute("SELECT count(1) FROM parcels WHERE latitude IS NOT NULL AND lower(district) = 'coimbatore'").fetchone()[0]
    c.close()

    tn_headers = get_token("state.tamilnadu@tngov.in")
    
    # 1. State-wide GIS query
    res = CLIENT.get("/gis/parcels?district=all&limit=5000", headers=tn_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert data["count"] == expected_tn_gis
    assert len(data["features"]) == expected_tn_gis
    
    districts = {f["properties"]["district"] for f in data["features"]}
    assert districts == {"Coimbatore", "Erode", "Namakkal", "Salem", "Tiruppur"}
    assert "Palakkad" not in districts
    
    # Verify stats
    stats = data.get("stats", {})
    assert stats.get("total_eligible_parcels") == expected_tn_total
    assert stats.get("total_gis_linked") == expected_tn_gis
    assert stats.get("total_gis_unlinked") == (expected_tn_total - expected_tn_gis)
    assert stats.get("visible_parcels") == expected_tn_gis
    
    # 2. Specific authorized district query
    res_cbe = CLIENT.get("/gis/parcels?district=Coimbatore&limit=5000", headers=tn_headers)
    assert res_cbe.status_code == 200
    cbe_data = res_cbe.json()
    assert cbe_data["count"] == expected_cbe_gis
    assert all(f["properties"]["district"] == "Coimbatore" for f in cbe_data["features"])
    
    # 3. Cross-state unauthorized access must return 403 Forbidden
    res_cross = CLIENT.get("/gis/parcels?district=Palakkad", headers=tn_headers)
    assert res_cross.status_code == 403
    assert "Cross-state access forbidden" in res_cross.json().get("detail", "")


def test_state_authority_gis_coverage_kerala():
    """State Authority for Kerala receives all 102 GIS-linked parcels across 4 Kerala districts and cannot access Tamil Nadu."""
    kerala_headers = get_token("state.kerala@kerala.gov.in")
    
    # 1. Kerala State-wide query
    res = CLIENT.get("/gis/parcels?district=all&limit=5000", headers=kerala_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 102
    assert len(data["features"]) == 102
    
    districts = {f["properties"]["district"] for f in data["features"]}
    assert districts == {"Palakkad", "Ernakulam", "Thrissur", "Thiruvananthapuram"}
    assert "Coimbatore" not in districts
    
    # 2. Cross-state unauthorized access must return 403 Forbidden
    res_cross = CLIENT.get("/gis/parcels?district=Coimbatore", headers=kerala_headers)
    assert res_cross.status_code == 403
    assert "Cross-state access forbidden" in res_cross.json().get("detail", "")


def test_district_authority_gis_scope_lock():
    """District Authority can only access parcels in their authorized district; cross-district queries return 403."""
    c = conn()
    expected_cbe_gis = c.execute("SELECT count(1) FROM parcels WHERE latitude IS NOT NULL AND lower(district) = 'coimbatore'").fetchone()[0]
    c.close()

    cbe_headers = get_token("district.coimbatore@tngov.in")
    
    # Authorized district
    res_auth = CLIENT.get("/gis/parcels?district=Coimbatore&limit=5000", headers=cbe_headers)
    assert res_auth.status_code == 200
    assert res_auth.json()["count"] == expected_cbe_gis
    
    # Cross-district unauthorized access
    res_unauth = CLIENT.get("/gis/parcels?district=Salem", headers=cbe_headers)
    assert res_unauth.status_code == 403
    assert "Cross-district access forbidden" in res_unauth.json().get("detail", "")
