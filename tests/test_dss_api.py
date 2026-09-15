import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import token, AUTH_PASSWORD

client = TestClient(app)

def test_dss_auth_and_rbac():
    # 1. Unauthenticated request must fail
    res = client.get("/api/dss/priority-parcels")
    assert res.status_code == 401

    # 2. Citizen access must be forbidden (HTTP 403)
    c_token = token("citizen@cbe.ac.in", "citizen", "Coimbatore", "Tamil Nadu")
    res_citizen = client.get("/api/dss/priority-parcels", headers={"Authorization": f"Bearer {c_token}"})
    assert res_citizen.status_code == 403

    # 3. Field officer access allowed for priority parcels
    fo_token = token("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu")
    res_fo = client.get("/api/dss/priority-parcels", headers={"Authorization": f"Bearer {fo_token}"})
    assert res_fo.status_code == 200
    data = res_fo.json()
    assert "items" in data

    # 4. State authority access to /api/dss/state
    st_token = token("state.tamilnadu@tngov.in", "state_authority", None, "Tamil Nadu")
    res_state = client.get("/api/dss/state", headers={"Authorization": f"Bearer {st_token}"})
    assert res_state.status_code == 200
    assert "priority_score" in res_state.json()

def test_dss_human_decision_flow():
    # Field Officer accepts recommendation for a parcel
    fo_token = token("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu")
    
    # Fetch first parcel
    res_p = client.get("/api/dss/priority-parcels?district=Coimbatore", headers={"Authorization": f"Bearer {fo_token}"})
    assert res_p.status_code == 200
    items = res_p.json()["items"]
    assert len(items) > 0
    target_p = items[0]
    pid = target_p["parcel_id"]

    # Record decision
    payload = {
        "recommendation_id": f"REC-PARCEL-{pid}",
        "entity_type": "parcel",
        "entity_id": str(pid),
        "action": "accept",
        "modified_notes": "Automated test acceptance"
    }
    res_dec = client.post("/api/dss/decision", json=payload, headers={"Authorization": f"Bearer {fo_token}"})
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "success"
    assert "decision_id" in res_dec.json()

    # Verify decision appears in audit / decision history
    res_hist = client.get("/api/dss/decision-history?district=Coimbatore", headers={"Authorization": f"Bearer {fo_token}"})
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert len(hist) > 0
    assert any(h["decision_id"] == res_dec.json()["decision_id"] for h in hist)

def test_dss_ask_ai():
    fo_token = token("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu")
    # Get an existing parcel ID
    res_p = client.get("/api/dss/priority-parcels?district=Coimbatore", headers={"Authorization": f"Bearer {fo_token}"})
    assert res_p.status_code == 200
    items = res_p.json()["items"]
    assert len(items) > 0
    target_pid = str(items[0]["parcel_id"])

    res = client.post("/api/dss/ask", json={"entity_type": "parcel", "entity_id": target_pid, "question": "Why is this parcel high priority?"}, headers={"Authorization": f"Bearer {fo_token}"})
    assert res.status_code == 200
    ans = res.json()
    assert "summary" in ans
    assert "recommendation" in ans
    assert ans["human_review_required"] is True
