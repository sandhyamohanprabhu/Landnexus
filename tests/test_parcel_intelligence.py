import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import conn

CLIENT = TestClient(app)

def get_auth(email="Tngov@cbe.ac.in", password="Tngov@CBE#2026"):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}

def test_parcel_search_and_filters():
    h = get_auth()
    
    # 1. Base list
    r = CLIENT.get("/land-records/?limit=20&district=Coimbatore", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "count" in data
    assert data["limit"] == 20
    
    if data["items"]:
        first = data["items"][0]
        # 2. Search by survey_no using q
        q_term = first["survey_no"]
        q_res = CLIENT.get(f"/land-records/?district=Coimbatore&q={q_term}", headers=h)
        assert q_res.status_code == 200
        matches = q_res.json()["items"]
        assert len(matches) > 0
        assert any(q_term.lower() in (m.get("survey_no") or "").lower() for m in matches)

        # 3. Filter by risk_category
        risk = first.get("risk_category") or "LOW"
        risk_res = CLIENT.get(f"/land-records/?district=Coimbatore&risk_category={risk}", headers=h)
        assert risk_res.status_code == 200
        for item in risk_res.json()["items"]:
            assert item["risk_category"].upper() == risk.upper()

def test_individual_parcel_intelligence_by_id_and_record_id():
    h = get_auth()
    pid = "PRJ-TEST-" + uuid.uuid4().hex[:6]
    CLIENT.post("/projects/", headers=h, json={
        "project_id": pid,
        "project_name": "Parcel Intelligence Unit Test Highway",
        "project_type": "Road",
        "district": "Coimbatore",
        "taluk": "Coimbatore North"
    })

    unique_rec = "REC-TST-" + uuid.uuid4().hex[:8].upper()
    survey = "SRV-" + uuid.uuid4().hex[:5]
    parcel_payload = {
        "record_id": unique_rec,
        "survey_no": survey,
        "subdivision": "2A",
        "village": "Kurichi",
        "taluk": "Coimbatore South",
        "district": "Coimbatore",
        "area": 3.75,
        "classification": "Ryotwari Wet",
        "land_use": "Agricultural Paddy",
        "project_id": pid,
        "latitude": 10.9654,
        "longitude": 76.9782,
        "training_label": "MEDIUM",
        "project_type": "Road",
        "legal_disputes": 0,
        "compensation_pending": 1,
        "approval_pending": 0,
        "documentation_pending": 0,
        "rehabilitation_pending": 0,
        "affected_families": 2
    }
    create_res = CLIENT.post("/land-records/", headers=h, json=parcel_payload)
    assert create_res.status_code == 200
    created_id = create_res.json()["parcel_id"]

    # Add a mock compensation record with exact survi.db columns
    c = conn()
    c.execute("""
        INSERT INTO compensation(project_id, parcel_id, assessed_amount, approved_amount, paid_amount, pending_amount, status)
        VALUES(?, ?, ?, ?, ?, ?, ?)
    """, (pid, created_id, 1500000.0, 3000000.0, 1000000.0, 2000000.0, "In Progress"))
    # Add a mock document
    doc_id = "DOC-TST-" + uuid.uuid4().hex[:8].upper()
    c.execute("""
        INSERT INTO documents(document_id, project_id, parcel_id, document_type, document_name, path, format, uploaded_by, sha256)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, pid, created_id, "Sale Deed", "Original_Sale_Deed.pdf", "safe_path.pdf", "pdf", "officer@tngov.in", "dummy_sha"))
    # Add mock field verification
    c.execute("""
        INSERT INTO field_verifications(parcel_id, officer_email, gps_lat, gps_lon, status, remarks)
        VALUES(?, ?, ?, ?, ?, ?)
    """, (created_id, "officer@tngov.in", 10.9654, 76.9782, "Completed", "DGPS boundary matched"))
    # Add mock grievance
    c.execute("""
        INSERT INTO grievances(project_id, parcel_id, submitted_by, type, description, status)
        VALUES(?, ?, ?, ?, ?, ?)
    """, (pid, created_id, "citizen@example.com", "Compensation Mismatch", "Market rate discrepancy claimed", "Submitted"))
    c.commit()
    c.close()

    # 1. Fetch by numeric ID
    res_num = CLIENT.get(f"/land-records/{created_id}", headers=h)
    assert res_num.status_code == 200
    p1 = res_num.json()
    assert p1["id"] == created_id
    assert p1["record_id"] == unique_rec
    assert p1["survey_no"] == survey
    assert p1["village"] == "Kurichi"
    assert p1["project"]["project_id"] == pid
    assert len(p1["compensation"]) >= 1
    assert p1["compensation"][0]["approved_amount"] == 3000000.0
    assert len(p1["documents"]) >= 1
    assert p1["documents"][0]["document_id"] == doc_id
    assert len(p1["field_verifications"]) >= 1
    assert len(p1["grievances"]) >= 1

    # Check GIS and Google Maps link
    assert p1["gis"]["has_coordinates"] is True
    assert p1["gis"]["latitude"] == 10.9654
    assert p1["gis"]["longitude"] == 76.9782
    assert "https://www.google.com/maps/search/?api=1&query=10.9654,76.9782" == p1["gis"]["google_maps_url"]
    assert "Demonstration GIS geometry — not an authoritative cadastral boundary." in p1["gis"]["disclaimer"]

    # 2. Fetch by string record_id
    res_str = CLIENT.get(f"/land-records/{unique_rec}", headers=h)
    assert res_str.status_code == 200
    p2 = res_str.json()
    assert p2["id"] == created_id
    assert p2["record_id"] == unique_rec

def test_missing_coordinates_truthful_gis():
    h = get_auth()
    unique_rec = "REC-NOGPS-" + uuid.uuid4().hex[:8].upper()
    c = conn()
    c.execute("""
        INSERT INTO parcels(record_id, survey_no, subdivision, village, taluk, district, area, classification, acquisition_status, latitude, longitude, risk_category, risk_score)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (unique_rec, "999/X", "1", "Perur", "Perur", "Coimbatore", 1.5, "Dry Land", "Proposal", None, None, "LOW", 15.0))
    pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()

    res = CLIENT.get(f"/land-records/{pid}", headers=h)
    assert res.status_code == 200
    p = res.json()
    assert p["gis"]["has_coordinates"] is False
    assert p["gis"]["latitude"] is None
    assert p["gis"]["longitude"] is None
    assert p["gis"]["google_maps_url"] is None
    assert "Demonstration GIS geometry — not an authoritative cadastral boundary." in p["gis"]["disclaimer"]

def test_parcel_dossier_pdf_generation():
    h = get_auth()
    # Fetch first parcel in Coimbatore
    r = CLIENT.get("/land-records/?limit=1&district=Coimbatore", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0
    parcel_id = items[0]["id"]

    pdf_res = CLIENT.get(f"/land-records/{parcel_id}/pdf", headers=h)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")
    assert "attachment; filename=" in pdf_res.headers["content-disposition"]
    assert len(pdf_res.content) > 1000

def test_parcel_not_found_404():
    h = get_auth()
    res = CLIENT.get("/land-records/999999999", headers=h)
    assert res.status_code == 404
    assert "Parcel not found" in res.json()["detail"]

def test_district_scope_cross_access_prohibition():
    # User with Coimbatore scope cannot access Salem parcel if strictly scoped
    h_cbe = get_auth()
    
    # Create or find a parcel in Salem
    c = conn()
    c.execute("""
        INSERT INTO parcels(record_id, survey_no, subdivision, village, taluk, district, area, classification, acquisition_status, latitude, longitude)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("REC-SLM-" + uuid.uuid4().hex[:6].upper(), "55/1", "A", "Salem Village", "Salem West", "Salem", 2.0, "Patta", "Proposal", 11.6643, 78.1460))
    salem_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()

    # Coimbatore officer should be rejected with 403 Forbidden
    res = CLIENT.get(f"/land-records/{salem_id}", headers=h_cbe)
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower() or "forbidden" in res.json()["detail"].lower() or "district" in res.json()["detail"].lower()
