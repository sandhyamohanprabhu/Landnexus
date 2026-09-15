"""
End-to-end Field Officer and Admin journey using controlled synthetic data.
Tests:
1. Field Officer Login
2. Retrieve assigned tasks including SYN-PARCEL-001
3. Retrieve parcel details and verify synthetic polygon boundary
4. Submit field verification
5. Confirm status transitions to 'Verified'
6. Admin Login & PDF Dossier export
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

CLIENT = TestClient(app)

def get_token(email, password="Tngov@CBE#2026"):
    res = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

def test_field_officer_synthetic_workflow():
    # 1. Field Officer Login
    fo_token = get_token("field.coimbatore@tngov.in")
    h_fo = {"Authorization": f"Bearer {fo_token}"}

    # 2. Retrieve assigned tasks
    res_tasks = CLIENT.get("/field/assigned", headers=h_fo)
    assert res_tasks.status_code == 200
    tasks = res_tasks.json()
    syn1 = next((t for t in tasks if t.get("record_id") == "SYN-PARCEL-001"), None)
    assert syn1 is not None, "SYN-PARCEL-001 must be present in field officer assignments"

    parcel_id = syn1["parcel_id"]

    # 3. Retrieve parcel details and check synthetic GIS boundary
    res_parcel = CLIENT.get(f"/land-records/{parcel_id}", headers=h_fo)
    assert res_parcel.status_code == 200
    p_data = res_parcel.json()
    assert p_data["record_id"] == "SYN-PARCEL-001"
    assert p_data["gis"]["has_coordinates"] is True
    assert p_data["gis"]["has_boundary"] is True
    assert p_data["gis"]["boundary_label"] == "Synthetic demonstration boundary"
    assert len(p_data["gis"]["boundary"]) >= 4

    # 4. Submit field verification
    verify_payload = {
        "gps_lat": 11.0250,
        "gps_lon": 77.1250,
        "remarks": "Synthetic field ground verification completed successfully."
    }
    res_verify = CLIENT.post(f"/field/{parcel_id}/verify", headers=h_fo, json=verify_payload)
    assert res_verify.status_code == 200
    v_body = res_verify.json()
    assert v_body["status"] == "Verified"

    # 5. Verify updated assignment list
    res_tasks_after = CLIENT.get("/field/assigned", headers=h_fo)
    assert res_tasks_after.status_code == 200
    syn1_after = next((t for t in res_tasks_after.json() if t.get("record_id") == "SYN-PARCEL-001"), None)
    assert syn1_after is not None
    assert syn1_after["assignment_status"] == "Verified"

def test_admin_synthetic_parcel_pdf_report():
    # 1. District Authority Login
    admin_token = get_token("district.coimbatore@tngov.in")
    h_admin = {"Authorization": f"Bearer {admin_token}"}

    # 2. Retrieve SYN-PARCEL-001 details
    res_p = CLIENT.get("/land-records/SYN-PARCEL-001", headers=h_admin)
    assert res_p.status_code == 200
    pid = res_p.json()["id"]

    # 3. Generate and export PDF Dossier
    res_pdf = CLIENT.get(f"/land-records/{pid}/pdf", headers=h_admin)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000
    assert res_pdf.content[:4] == b"%PDF"
