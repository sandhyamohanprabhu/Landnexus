"""
Comprehensive Login & Authentication QA Suite
100% Accuracy Verification for LANDNEXUS / SURVI
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import conn, AUTH_PASSWORD, init_db

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()

ALL_AUTHENTICATED_USERS = [
    # 1. National Authority & Admins
    ("national.admin@landnexus.gov", "national_authority", None, None, True),
    ("Tngov@cbe.ac.in", "authority", "Coimbatore", "Tamil Nadu", True),
    ("admin@survi.gov.in", "admin", None, None, True),
    ("admin@cbe.ac.in", "admin", None, None, True),

    # 2. State Authorities
    ("state.tamilnadu@tngov.in", "state_authority", None, "Tamil Nadu", True),
    ("state.kerala@kerala.gov.in", "state_authority", None, "Kerala", True),
    ("state@cbe.ac.in", "state_authority", None, "Tamil Nadu", True),

    # 3. District Authorities (All 5 Districts + Demo)
    ("district.coimbatore@tngov.in", "district_authority", "Coimbatore", "Tamil Nadu", True),
    ("district.tiruppur@tngov.in", "district_authority", "Tiruppur", "Tamil Nadu", True),
    ("district.erode@tngov.in", "district_authority", "Erode", "Tamil Nadu", True),
    ("district.salem@tngov.in", "district_authority", "Salem", "Tamil Nadu", True),
    ("district.namakkal@tngov.in", "district_authority", "Namakkal", "Tamil Nadu", True),
    ("district@cbe.ac.in", "district_authority", "Coimbatore", "Tamil Nadu", True),

    # 4. Acquisition Officers (All 5 Districts)
    ("officer.coimbatore@tngov.in", "acquisition_officer", "Coimbatore", "Tamil Nadu", False),
    ("officer.tiruppur@tngov.in", "acquisition_officer", "Tiruppur", "Tamil Nadu", False),
    ("officer.erode@tngov.in", "acquisition_officer", "Erode", "Tamil Nadu", False),
    ("officer.salem@tngov.in", "acquisition_officer", "Salem", "Tamil Nadu", False),
    ("officer.namakkal@tngov.in", "acquisition_officer", "Namakkal", "Tamil Nadu", False),

    # 5. Field Officers (All 5 Districts + Demo)
    ("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu", False),
    ("field.tiruppur@tngov.in", "field_officer", "Tiruppur", "Tamil Nadu", False),
    ("field.erode@tngov.in", "field_officer", "Erode", "Tamil Nadu", False),
    ("field.salem@tngov.in", "field_officer", "Salem", "Tamil Nadu", False),
    ("field.namakkal@tngov.in", "field_officer", "Namakkal", "Tamil Nadu", False),
    ("field@cbe.ac.in", "field_officer", "Coimbatore", "Tamil Nadu", False),

    # 6. Citizen Accounts (Demo & Synthetic)
    ("citizen@cbe.ac.in", "citizen", "Coimbatore", "Tamil Nadu", False),
    ("citizen@demo.in", "citizen", "Coimbatore", "Tamil Nadu", False),
    ("citizen.demo.syn001@example.com", "citizen", "Coimbatore", "Tamil Nadu", False),
    ("citizen.demo.syn002@example.com", "citizen", "Coimbatore", "Tamil Nadu", False),
    ("citizen.demo.syn003@example.com", "citizen", "Coimbatore", "Tamil Nadu", False),
    ("citizen.demo.syn004@example.com", "citizen", "Coimbatore", "Tamil Nadu", False),
    ("citizen.demo.syn005@example.com", "citizen", "Coimbatore", "Tamil Nadu", False),
]

@pytest.mark.parametrize("email,expected_role,expected_dist,expected_state,expected_auth", ALL_AUTHENTICATED_USERS)
def test_all_official_and_citizen_logins(email, expected_role, expected_dist, expected_state, expected_auth):
    """Verify that every single predefined account can log in and retrieve its session."""
    res = client.post("/auth/login", json={"email": email, "password": AUTH_PASSWORD})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    u = data["user"]
    assert u["email"].lower() == email.lower()
    assert u["role"] == expected_role
    assert u["district_scope"] == expected_dist
    assert u["state_scope"] == expected_state
    assert u["is_authority"] == expected_auth

    # Verify /auth/me returns identical verified information
    token = data["access_token"]
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"].lower() == email.lower()
    assert me_data["role"] == expected_role
    assert me_data["district_scope"] == expected_dist
    assert me_data["state_scope"] == expected_state
    assert me_data["is_authority"] == expected_auth


def test_login_whitespace_and_case_insensitivity():
    """Verify login handles uppercase emails and leading/trailing whitespace with 100% accuracy."""
    # Uppercase with spaces
    res = client.post("/auth/login", json={"email": "  DISTRICT.COIMBATORE@TNGOV.IN  ", "password": AUTH_PASSWORD})
    assert res.status_code == 200
    assert res.json()["user"]["email"].lower() == "district.coimbatore@tngov.in"

    res2 = client.post("/auth/login", json={"email": "  National.Admin@LandNexus.GOV  ", "password": AUTH_PASSWORD})
    assert res2.status_code == 200
    assert res2.json()["user"]["email"].lower() == "national.admin@landnexus.gov"


def test_login_invalid_credentials():
    """Verify rejection of invalid credentials."""
    # Wrong password
    res = client.post("/auth/login", json={"email": "district.coimbatore@tngov.in", "password": "WrongPassword!2026"})
    assert res.status_code == 401
    assert "Invalid credentials" in res.text

    # Non-existent user
    res2 = client.post("/auth/login", json={"email": "nonexistent.user@random.com", "password": AUTH_PASSWORD})
    assert res2.status_code == 401


def test_citizen_self_registration_and_login_flow():
    """Verify end-to-end citizen registration against an existing verified parcel."""
    c = conn()
    # Find a valid parcel in Coimbatore
    parcel = c.execute("SELECT id, survey_no, district FROM parcels WHERE district='Coimbatore' LIMIT 1").fetchone()
    c.close()
    assert parcel is not None, "A parcel in Coimbatore must exist for testing"

    import time
    test_citizen_email = f"auto.citizen.{int(time.time())}@example.com"
    reg_payload = {
        "full_name": "Thiru K. Muthusamy",
        "email": f"  {test_citizen_email}  ",
        "password": "SecurePassword123",
        "phone": "+91 98401 23456",
        "survey_no": parcel["survey_no"],
        "district": parcel["district"]
    }

    reg_res = client.post("/auth/citizen/register", json=reg_payload)
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_citizen_email
    assert reg_data["user"]["role"] == "citizen"
    assert reg_data["user"]["district_scope"] == parcel["district"]

    # Now verify this newly registered citizen can log in normally
    login_res = client.post("/auth/login", json={"email": test_citizen_email, "password": "SecurePassword123"})
    assert login_res.status_code == 200
    assert login_res.json()["user"]["role"] == "citizen"
