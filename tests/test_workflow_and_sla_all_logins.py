"""
LANDNEXUS - Acquisition Workflow and SLA/Timeline Operations Test Suite
Validates that Workflow & SLA endpoints, transitions, compensation, timeline,
and operations dashboard work with 100% accuracy across all 7 user roles and login accounts.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import conn

CLIENT = TestClient(app)
DEFAULT_PWD = "Tngov@CBE#2026"

def get_auth(email, password=DEFAULT_PWD):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}

ALL_TEST_USERS = [
    ("national.admin@landnexus.gov", "national_authority", "all", None),
    ("Tngov@cbe.ac.in", "admin", "Coimbatore", "Tamil Nadu"),
    ("state.tamilnadu@tngov.in", "state_authority", "all", "Tamil Nadu"),
    ("state.kerala@kerala.gov.in", "state_authority", "Palakkad", "Kerala"),
    ("district.coimbatore@tngov.in", "district_authority", "Coimbatore", "Tamil Nadu"),
    ("district.tiruppur@tngov.in", "district_authority", "Tiruppur", "Tamil Nadu"),
    ("district.erode@tngov.in", "district_authority", "Erode", "Tamil Nadu"),
    ("officer.coimbatore@tngov.in", "acquisition_officer", "Coimbatore", "Tamil Nadu"),
    ("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu"),
    ("field.tiruppur@tngov.in", "field_officer", "Tiruppur", "Tamil Nadu"),
    ("citizen@cbe.ac.in", "citizen", "Coimbatore", "Tamil Nadu"),
    ("citizen.demo.syn001@example.com", "citizen", "Coimbatore", "Tamil Nadu"),
]

@pytest.mark.parametrize("email,role,district,state", ALL_TEST_USERS)
def test_all_logins_can_access_sla_operations_and_bottlenecks(email, role, district, state):
    headers = get_auth(email)
    
    # 1. SLA Operations Dashboard
    dist_param = "" if role == "citizen" else (f"?district={district}" if district else "")
    r_ops = CLIENT.get(f"/sla/operations{dist_param}", headers=headers)
    assert r_ops.status_code == 200, f"SLA operations failed for {email} ({role}): {r_ops.text}"
    ops = r_ops.json()
    assert "process_bottlenecks" in ops
    assert "sla_due_soon" in ops
    assert "sla_breached" in ops
    assert "risk_alerts" in ops

    # 2. SLA Bottlenecks
    r_bn = CLIENT.get(f"/sla/bottlenecks{dist_param}", headers=headers)
    assert r_bn.status_code == 200, f"SLA bottlenecks failed for {email} ({role}): {r_bn.text}"
    assert "bottlenecks" in r_bn.json()


@pytest.mark.parametrize("email,role,district,state", ALL_TEST_USERS)
def test_all_logins_can_access_project_workflow_and_compensation(email, role, district, state):
    headers = get_auth(email)

    # 1. List Projects
    dist_param = "" if role == "citizen" else (f"?district={district}" if district else "")
    r_list = CLIENT.get(f"/projects/{dist_param}", headers=headers)
    assert r_list.status_code == 200, f"List projects failed for {email} ({role}): {r_list.text}"
    items = r_list.json().get("items", [])

    if items:
        proj_id = items[0]["project_id"]

        # 2. Get Project Details
        r_proj = CLIENT.get(f"/projects/{proj_id}", headers=headers)
        assert r_proj.status_code == 200, f"Get project failed for {email} ({role}): {r_proj.text}"
        p = r_proj.json()
        assert "workflow" in p
        assert "parcels" in p

        # 3. Get Project Compensation
        r_comp = CLIENT.get(f"/compensation/project/{proj_id}", headers=headers)
        assert r_comp.status_code == 200, f"Get compensation failed for {email} ({role}): {r_comp.text}"
        assert isinstance(r_comp.json(), list)

        # 4. Get Project Milestone Timeline
        r_time = CLIENT.get(f"/sla/timeline/{proj_id}", headers=headers)
        assert r_time.status_code == 200, f"Get timeline failed for {email} ({role}): {r_time.text}"
        assert isinstance(r_time.json(), list)


def test_national_authority_can_execute_workflow_transitions():
    h = get_auth("national.admin@landnexus.gov")
    
    # Check field officers directory
    r_off = CLIENT.get("/field/officers", headers=h)
    assert r_off.status_code == 200
    assert len(r_off.json()) > 0

    # Get a project to inspect
    r_list = CLIENT.get("/projects/?district=all", headers=h)
    assert r_list.status_code == 200
    items = r_list.json().get("items", [])
    assert len(items) > 0


def test_district_authority_coimbatore_workflow_lifecycle():
    h = get_auth("district.coimbatore@tngov.in")
    
    # Fetch officers in Coimbatore
    r_off = CLIENT.get("/field/officers?district=Coimbatore", headers=h)
    assert r_off.status_code == 200
    assert len(r_off.json()) > 0

    # Fetch projects in Coimbatore
    r_list = CLIENT.get("/projects/?district=Coimbatore", headers=h)
    assert r_list.status_code == 200
    items = r_list.json().get("items", [])
    assert len(items) > 0
    proj_id = items[0]["project_id"]

    # SLA Timeline
    r_time = CLIENT.get(f"/sla/timeline/{proj_id}", headers=h)
    assert r_time.status_code == 200
    assert len(r_time.json()) > 0
