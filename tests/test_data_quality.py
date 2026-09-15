import uuid
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import conn, token
from backend.services.duplicate_service import (
    normalize_survey_no,
    normalize_subdivision,
    compute_name_similarity,
    score_duplicate_pair,
    compare_records
)

CLIENT = TestClient(app)

def get_auth(email="Tngov@cbe.ac.in", password="Tngov@CBE#2026"):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}

def test_survey_normalization_and_scoring_unit():
    # 1. Normalization
    assert normalize_survey_no(" 124 / 2 ") == "124/2"
    assert normalize_survey_no("0124-02") == "124/2"
    assert normalize_survey_no("124_02") == "124/2"
    assert normalize_survey_no("005") == "5"
    assert normalize_subdivision(" 02A ") == "2A"
    assert normalize_subdivision("01") == "1"

    # 2. Name similarity
    assert compute_name_similarity("Thiru K. Ramanathan", "Ramanathan K") >= 0.9
    assert compute_name_similarity("Smt. Lakshmi Devi", "Lakshmi Devi") >= 0.9
    assert compute_name_similarity("Ramesh Kumar", "Suresh Kumar") < 0.6

    # 3. Duplicate Scoring unit
    p1 = {
        "id": 1, "survey_no": "124/2", "subdivision": "2", "village": "Kurichi",
        "taluk": "Coimbatore South", "district": "Coimbatore",
        "owner_reference": "K. Ramanathan", "area": 2.50, "latitude": 10.965, "longitude": 76.978
    }
    p2 = {
        "id": 2, "survey_no": " 0124-02 ", "subdivision": " 02 ", "village": "kurichi",
        "taluk": "coimbatore south", "district": "coimbatore",
        "owner_reference": "Ramanathan K", "area": 2.52, "latitude": 10.96505, "longitude": 76.97805
    }
    scored = score_duplicate_pair(p1, p2)
    assert scored["similarity_score"] >= 90.0
    assert scored["confidence_band"] == "HIGH"
    assert scored["assessment"] == "Potential Duplicate – Review Required"
    assert any("Survey Number" in r for r in scored["reasons"])
    assert any("tolerance" in r for r in scored["reasons"])

    # 4. False-positive prevention: same owner, same village, but DIFFERENT survey number
    p3 = {
        "id": 3, "survey_no": "88/1", "subdivision": "1", "village": "Kurichi",
        "taluk": "Coimbatore South", "district": "Coimbatore",
        "owner_reference": "K. Ramanathan", "area": 5.0, "latitude": 10.960, "longitude": 76.970
    }
    scored_diff = score_duplicate_pair(p1, p3)
    assert scored_diff["similarity_score"] < 60.0
    assert not scored_diff["is_potential_duplicate"]
    assert any("Guarded" in r for r in scored_diff["reasons"])

def test_side_by_side_comparison_badges():
    p1 = {
        "id": 101, "record_id": "REC-A", "survey_no": "100/1", "subdivision": "1",
        "village": "Kurichi", "taluk": "Coimbatore South", "district": "Coimbatore",
        "owner_reference": "Murugan S", "area": 3.0, "classification": "Wet",
        "project_id": "PRJ-01", "latitude": 10.95, "longitude": 76.95
    }
    p2 = {
        "id": 102, "record_id": "REC-B", "survey_no": "100/1", "subdivision": "2",
        "village": "Kurichi", "taluk": "Coimbatore South", "district": "Coimbatore",
        "owner_reference": "Murugan S", "area": 3.01, "classification": "Wet",
        "project_id": "PRJ-01", "latitude": 10.95002, "longitude": 76.95002
    }
    comp = compare_records(p1, p2, mask_privacy=True)
    fields_by_key = {f["key"]: f for f in comp["fields"]}
    
    assert fields_by_key["survey_no"]["status"] == "MATCH"
    assert fields_by_key["subdivision"]["status"] == "MISMATCH"
    assert fields_by_key["village"]["status"] == "MATCH"
    assert fields_by_key["area"]["status"] == "MATCH"
    assert fields_by_key["coordinates"]["status"] == "MATCH"
    assert "*" in fields_by_key["owner_reference"]["record_a"]

def test_duplicate_scan_and_cases_lifecycle():
    h = get_auth()
    
    # 1. Create a project and two candidate duplicate parcels
    pid = "PRJ-DUP-" + uuid.uuid4().hex[:6]
    CLIENT.post("/projects/", headers=h, json={
        "project_id": pid,
        "project_name": "Duplicate Test Bypass",
        "project_type": "Road",
        "district": "Coimbatore",
        "taluk": "Coimbatore North"
    })

    rec_a = "REC-DUP-A-" + uuid.uuid4().hex[:6].upper()
    rec_b = "REC-DUP-B-" + uuid.uuid4().hex[:6].upper()
    survey = "SRV-" + uuid.uuid4().hex[:4]

    p1_res = CLIENT.post("/land-records/", headers=h, json={
        "record_id": rec_a, "survey_no": survey, "subdivision": "1A", "village": "Perur",
        "taluk": "Coimbatore South", "district": "Coimbatore", "area": 4.5, "classification": "Dry",
        "owner_reference": "Sundaram P", "project_id": pid, "latitude": 10.91, "longitude": 76.92,
        "training_label": "LOW"
    })
    assert p1_res.status_code == 200
    p1_id = p1_res.json()["parcel_id"]

    # Insert second parcel directly into DB to simulate cross-source duplicate
    c = conn()
    c.execute("""
        INSERT INTO parcels(record_id, survey_no, subdivision, village, taluk, district, owner_reference, area, classification, project_id, latitude, longitude, validation_status, created_by)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALID', 'test@tngov.in')
    """, (rec_b, survey, "1A", "Perur", "Coimbatore South", "Coimbatore", "P. Sundaram", 4.52, "Dry", pid, 10.9101, 76.9201))
    p2_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()

    # 2. Trigger scan
    scan_res = CLIENT.post("/data-quality/scan", headers=h, json={"district": "Coimbatore", "threshold": 60.0})
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert "cases" in scan_data
    assert scan_data["accuracy_statement"] == "Potential Duplicate – Review Required. No automated deletion or merging applied."

    # 3. List cases
    cases_res = CLIENT.get("/data-quality/duplicate-cases?district=Coimbatore", headers=h)
    assert cases_res.status_code == 200
    cases = cases_res.json()["cases"]
    matching_case = next((c for c in cases if (c["record_a_id"] in (p1_id, p2_id) and c["record_b_id"] in (p1_id, p2_id))), None)
    assert matching_case is not None
    case_id = matching_case["case_id"]
    assert matching_case["similarity_score"] >= 80.0

    # 4. Get case detail
    detail_res = CLIENT.get(f"/data-quality/duplicate-cases/{case_id}", headers=h)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "comparison" in detail
    assert "accuracy_statement" in detail
    assert detail["comparison"]["similarity_score"] >= 80.0

    # 5. Officer Decision: CONFIRMED_DUPLICATE
    dec_res = CLIENT.post(f"/data-quality/duplicate-cases/{case_id}/decision", headers=h, json={
        "decision": "CONFIRMED_DUPLICATE",
        "reason": "Deed verified by Sub-Registrar records. Identical agricultural plot.",
        "master_record_id": p1_id
    })
    assert dec_res.status_code == 200
    assert dec_res.json()["decision"] == "CONFIRMED_DUPLICATE"

    # Check parcel duplicate flag
    c = conn()
    row_p2 = dict(c.execute("SELECT duplicate_flag, master_parcel_id FROM parcels WHERE id=?", (p2_id,)).fetchone())
    c.close()
    assert row_p2["duplicate_flag"] == 1
    assert row_p2["master_parcel_id"] == p1_id

    # 6. Officer Decision: Change to NOT_DUPLICATE with reason
    not_dup_res = CLIENT.post(f"/data-quality/duplicate-cases/{case_id}/decision", headers=h, json={
        "decision": "NOT_DUPLICATE",
        "reason": "Subdivision partitioned by family partition deed 45/2024."
    })
    assert not_dup_res.status_code == 200
    assert not_dup_res.json()["decision"] == "NOT_DUPLICATE"

    # 7. Parcel intelligence endpoint includes data_quality
    p_info = CLIENT.get(f"/land-records/{p1_id}", headers=h).json()
    assert "data_quality" in p_info
    assert p_info["data_quality"]["duplicate_cases_count"] >= 1

def test_cross_database_verification_truthfulness():
    h = get_auth()
    
    c = conn()
    row = c.execute("SELECT id FROM parcels WHERE district='Coimbatore' LIMIT 1").fetchone()
    c.close()
    parcel_id = row[0] if row else 1

    # Call cross-db verification
    v_res = CLIENT.post(f"/data-quality/verify-external/{parcel_id}", headers=h, json={"include_demo": True})
    assert v_res.status_code == 200
    data = v_res.json()
    assert "verifications" in data
    assert "truthful_notice" in data
    
    dilrmp = next((v for v in data["verifications"] if "DILRMP" in v["provider_name"]), None)
    assert dilrmp is not None
    assert dilrmp["status"] in ("NOT_CONNECTED", "SOURCE_UNAVAILABLE")
    assert dilrmp["is_demo"] is False
    assert "not configured" in dilrmp["details"].lower() or "unreachable" in dilrmp["details"].lower()

    demo = next((v for v in data["verifications"] if v["is_demo"] is True), None)
    assert demo is not None
    assert "DEMONSTRATION DATA" in demo["disclaimer"]
    assert "DEMONSTRATION DATA" in demo["details"]

    hist_res = CLIENT.get(f"/data-quality/verifications/{parcel_id}", headers=h)
    assert hist_res.status_code == 200
    assert hist_res.json()["count"] >= 1

def test_rbac_and_district_scoping():
    h = get_auth()
    
    # 1. Citizen forbidden
    c_token = token("citizen@cbe.ac.in", "citizen")
    c_head = {"Authorization": f"Bearer {c_token}"}
    
    r_cit = CLIENT.get("/data-quality/duplicate-cases", headers=c_head)
    assert r_cit.status_code == 403

    r_cit_scan = CLIENT.post("/data-quality/scan", headers=c_head, json={"district": "Coimbatore"})
    assert r_cit_scan.status_code == 403

    # 2. District scope enforcement for district authority
    tiruppur_token = CLIENT.post("/auth/login", json={"email": "district.tiruppur@tngov.in", "password": "Tngov@CBE#2026"}).json()["access_token"]
    tiruppur_head = {"Authorization": f"Bearer {tiruppur_token}"}

    # Cross-district access forbidden
    r_cross = CLIENT.get("/data-quality/duplicate-cases?district=Coimbatore", headers=tiruppur_head)
    assert r_cross.status_code == 403

def test_data_quality_analytics_and_audit():
    h = get_auth()
    
    res = CLIENT.get("/data-quality/analytics?district=Coimbatore", headers=h)
    assert res.status_code == 200
    data = res.json()
    assert "parcels" in data
    assert "duplicate_detection" in data
    assert "cross_db_verification" in data
    assert data["duplicate_detection"]["accuracy_rule"] == "Potential Duplicate – Review Required. Never 100% automated proof."

    # Verify audit entries exist for data quality actions
    c = conn()
    logs = c.execute("SELECT * FROM audit WHERE action LIKE 'DUPLICATE%' OR action LIKE 'CROSS_DB%'").fetchall()
    c.close()
    assert len(logs) > 0
    for l in logs:
        details_str = l["details"] or ""
        assert "aadhaar" not in details_str.lower()

def test_verification_queue_and_national_analytics():
    h = get_auth()

    # 1. Verification queue
    q_res = CLIENT.get("/data-quality/verification-queue?district=Coimbatore", headers=h)
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert "queue" in q_data
    assert "total_queued" in q_data

    # 2. Cross-record consistency validation
    v_res = CLIENT.get("/data-quality/cross-record-validation?district=Coimbatore", headers=h)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert "anomalies" in v_data

    # 3. Audit history
    a_res = CLIENT.get("/data-quality/audit-history?district=Coimbatore", headers=h)
    assert a_res.status_code == 200
    assert "audit_logs" in a_res.json()

    # 4. National analytics (requires State Authority or National)
    state_token = CLIENT.post("/auth/login", json={"email": "state.tamilnadu@tngov.in", "password": "Tngov@CBE#2026"}).json()["access_token"]
    state_head = {"Authorization": f"Bearer {state_token}"}
    nat_res = CLIENT.get("/data-quality/national-analytics", headers=state_head)
    assert nat_res.status_code == 200
    nat_data = nat_res.json()
    assert "total_parcels" in nat_data
    assert "districts_monitored" in nat_data

