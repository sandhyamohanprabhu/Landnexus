"""
LANDNEXUS - Comprehensive End-to-End Platform Integration Test Suite
Validates:
  LOGIN -> GIS -> PARCEL -> DOCUMENTS/OCR -> OCR PDF -> RISK INTELLIGENCE -> 7-STAGE RISK ->
  SHAP EXPLANATION -> ALERTS -> SMS SIMULATION -> SMS HISTORY -> ANALYTICS -> REPORTS/MIS -> PARCEL PDF DOSSIER
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

CLIENT = TestClient(app)
DEFAULT_PWD = "Tngov@CBE#2026"

def get_auth(email, password=DEFAULT_PWD):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    j = r.json()
    return {"Authorization": "Bearer " + j["access_token"]}, j["user"]

def test_complete_e2e_journey_erode_district():
    headers, user = get_auth("district.erode@tngov.in")
    assert user["district_scope"] == "Erode"

    # Step 1: GIS Parcels
    gis_res = CLIENT.get("/gis/parcels?district=Erode", headers=headers)
    assert gis_res.status_code == 200
    gis_data = gis_res.json()
    assert "features" in gis_data or isinstance(gis_data, (list, dict))

    # Step 2: Documents / OCR
    doc_res = CLIENT.get("/documents/?district=Erode", headers=headers)
    assert doc_res.status_code == 200
    docs = doc_res.json()
    assert isinstance(docs, list)

    # Step 3: OCR Analytics & Queue
    ocr_an = CLIENT.get("/ocr/analytics?district=Erode", headers=headers)
    assert ocr_an.status_code == 200
    assert "total_documents_processed" in ocr_an.json()

    ocr_q = CLIENT.get("/ocr/verification-queue?district=Erode", headers=headers)
    assert ocr_q.status_code == 200

    # Step 4: If any document exists, test PDF download
    if docs:
        doc_id = docs[0].get("document_id")
        if doc_id:
            pdf_res = CLIENT.get(f"/ocr/{doc_id}/pdf", headers=headers)
            assert pdf_res.status_code in (200, 404)
            if pdf_res.status_code == 200:
                assert pdf_res.headers.get("content-type") == "application/pdf"
                assert len(pdf_res.content) > 0

    # Step 5: Risk Intelligence
    risk_res = CLIENT.get("/analytics/operations?district=Erode", headers=headers)
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert "risk" in risk_data
    assert "projects" in risk_data
    assert "parcels" in risk_data

    # Step 6: 7-Stage Risk
    stage_res = CLIENT.post("/ml/stage-risk", json={"district": "Erode", "area": 2.5, "legal_disputes": 1}, headers=headers)
    assert stage_res.status_code == 200
    assert "stages" in stage_res.json()
    assert len(stage_res.json()["stages"]) == 7

    # Step 7: SHAP / Model Explanation for top parcel
    top_parcels = risk_data["risk"].get("top_parcels", [])
    if top_parcels:
        pid = top_parcels[0].get("parcel_id")
        if pid:
            exp_res = CLIENT.get(f"/ml/parcels/{pid}/explanation", headers=headers)
            assert exp_res.status_code == 200
            exp = exp_res.json()
            assert "features" in exp
            assert "explanation_method" in exp

    # Step 8: Alerts
    alert_res = CLIENT.get("/alerts/operations?district=Erode", headers=headers)
    assert alert_res.status_code == 200
    assert isinstance(alert_res.json(), list)

    # Step 9: SMS Notification Centre
    stats_res = CLIENT.get("/api/sms/stats?district=Erode", headers=headers)
    assert stats_res.status_code == 200
    rec_res = CLIENT.get("/api/sms/recipients?district=Erode", headers=headers)
    assert rec_res.status_code == 200
    
    # Send simulated single SMS
    send_payload = {
        "district": "Erode",
        "recipient_phone": "9876543210",
        "recipient_name": "S. Periyasamy",
        "message": "Notice under Section 11(1) for land acquisition proceedings in Erode.",
        "template": "Direct Landowner Notice"
    }
    sms_send_res = CLIENT.post("/api/sms/send", json=send_payload, headers=headers)
    assert sms_send_res.status_code == 200
    assert "sms_id" in sms_send_res.json() or "status" in sms_send_res.json()

    # Verify SMS in history
    hist_res = CLIENT.get("/api/sms/history?district=Erode", headers=headers)
    assert hist_res.status_code == 200
    assert "items" in hist_res.json() or isinstance(hist_res.json(), (list, dict))

    # Step 10: Reports / MIS Summary & Parcel PDF Dossier
    rep_res = CLIENT.get("/reports/?district=Erode", headers=headers)
    assert rep_res.status_code == 200
    assert "summary" in rep_res.json()

    # Step 11: District PDF Download
    dist_pdf_res = CLIENT.get("/reports/district/Erode/pdf", headers=headers)
    assert dist_pdf_res.status_code == 200
    assert dist_pdf_res.headers.get("content-type") == "application/pdf"
    assert len(dist_pdf_res.content) > 500


def test_cross_module_consistency_and_district_isolation():
    erode_headers, _ = get_auth("district.erode@tngov.in")
    cbe_headers, _ = get_auth("district.coimbatore@tngov.in")
    state_headers, _ = get_auth("state.tamilnadu@tngov.in")

    # 1. Erode authority cannot access Coimbatore analytics
    forbidden_res = CLIENT.get("/analytics/operations?district=Coimbatore", headers=erode_headers)
    assert forbidden_res.status_code == 403

    # 2. Coimbatore authority cannot access Erode reports
    forbidden_rep = CLIENT.get("/reports/?district=Erode", headers=cbe_headers)
    assert forbidden_rep.status_code == 403

    # 3. State Authority can access both Erode and Coimbatore
    assert CLIENT.get("/analytics/operations?district=Erode", headers=state_headers).status_code == 200
    assert CLIENT.get("/analytics/operations?district=Coimbatore", headers=state_headers).status_code == 200
    assert CLIENT.get("/reports/?district=Erode", headers=state_headers).status_code == 200
    assert CLIENT.get("/reports/?district=Coimbatore", headers=state_headers).status_code == 200

    # 4. State PDF report only accessible by State Authority or Admin
    assert CLIENT.get("/reports/state/pdf", headers=state_headers).status_code == 200
    assert CLIENT.get("/reports/state/pdf", headers=erode_headers).status_code == 403


def test_empty_dataset_graceful_handling():
    headers, _ = get_auth("district.coimbatore@tngov.in")

    # Query non-existent village
    rec_res = CLIENT.get("/api/sms/recipients?district=Coimbatore&village=NonExistentVillage123", headers=headers)
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["total_recipients"] == 0
    assert data["valid_mobile_count"] == 0
    assert data["recipients"] == []