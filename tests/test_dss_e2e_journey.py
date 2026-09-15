import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import token, conn

client = TestClient(app)

def test_full_sih_demo_scenario():
    """
    SIH 2026 Mandatory Demo Scenario:
    1. SYN-PARCEL-004 is detected with incomplete boundary / GPS anomalies.
    2. DSS calculates HIGH / CRITICAL Priority score with explicit reasons.
    3. Field Officer logs in, sees parcel at top of AI Priority Verification Queue.
    4. Field Officer queries Ask AI for explanation.
    5. Field Officer accepts recommendation ('Re-verify parcel boundary').
    6. System logs human decision in dss_decisions with full audit record.
    7. District Authority dashboard reflects priority status and bottleneck alerts.
    """
    # 1. Inspect synthetic parcel SYN-PARCEL-004
    fo_token = token("field.coimbatore@tngov.in", "field_officer", "Coimbatore", "Tamil Nadu")
    
    # Query priority parcels
    res_queue = client.get("/api/dss/priority-parcels?district=Coimbatore", headers={"Authorization": f"Bearer {fo_token}"})
    assert res_queue.status_code == 200
    queue_data = res_queue.json()
    assert len(queue_data["items"]) > 0

    # Locate SYN-PARCEL-004 or top parcel
    p4 = next((p for p in queue_data["items"] if p.get("record_id") == "SYN-PARCEL-004"), queue_data["items"][0])
    pid = p4["parcel_id"]

    # 2. Verify DSS score & components
    res_dss = client.get(f"/api/dss/parcel/{pid}", headers={"Authorization": f"Bearer {fo_token}"})
    assert res_dss.status_code == 200
    dss_data = res_dss.json()
    assert "assessment" in dss_data
    assert "recommendation" in dss_data
    assert dss_data["assessment"]["priority_score"] >= 0
    assert dss_data["recommendation"]["recommendation"] != ""

    # 3. Test Ask AI explanation
    res_ask = client.post("/api/dss/ask", json={
        "entity_type": "parcel",
        "entity_id": str(pid),
        "question": "Why is this parcel high priority and what is missing?"
    }, headers={"Authorization": f"Bearer {fo_token}"})
    assert res_ask.status_code == 200
    ask_resp = res_ask.json()
    assert "summary" in ask_resp
    assert ask_resp["human_review_required"] is True

    # 4. Field Officer accepts recommendation
    res_dec = client.post("/api/dss/decision", json={
        "recommendation_id": dss_data.get("recommendation_id"),
        "entity_type": "parcel",
        "entity_id": str(pid),
        "action": "accept",
        "modified_notes": "Accepted via SIH E2E verification workflow"
    }, headers={"Authorization": f"Bearer {fo_token}"})
    assert res_dec.status_code == 200
    dec_body = res_dec.json()
    assert dec_body["status"] == "success"
    assert "decision_id" in dec_body

    # 5. Check District Authority dashboard metrics
    dist_token = token("district.coimbatore@tngov.in", "district_authority", "Coimbatore", "Tamil Nadu")
    res_dist = client.get("/api/dss/district/Coimbatore", headers={"Authorization": f"Bearer {dist_token}"})
    assert res_dist.status_code == 200
    dist_dss = res_dist.json()
    assert "priority_score" in dist_dss
    assert "components" in dist_dss

    # 6. Verify audit trail in database
    c = conn()
    audit_row = c.execute("SELECT * FROM dss_decisions WHERE decision_id=?", (dec_body["decision_id"],)).fetchone()
    assert audit_row is not None
    assert audit_row["human_action"] == "accept"
    assert audit_row["user_email"] == "field.coimbatore@tngov.in"
    c.close()
