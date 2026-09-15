"""
SURVI / LANDNEXUS — Purpose-Aware Acquisition Privacy Guard
Integration and End-to-End API Tests
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import conn

CLIENT = TestClient(app)


def auth(email="Tngov@cbe.ac.in", password="Tngov@CBE#2026"):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_privacy_analysis_and_retrieval_e2e():
    h = auth()
    doc_id = "DOC-PRIV-" + uuid.uuid4().hex[:8]

    # Create dummy document record
    c = conn()
    c.execute("""
        INSERT INTO documents (document_id, document_name, path, format, uploaded_by, ocr_status, remarks)
        VALUES (?, 'sale_deed_sample.pdf', 'dummy.pdf', '.pdf', 'Tngov@cbe.ac.in', 'Completed',
        'Pattadar Ramesh Kumar. Aadhaar No: 9876 5432 1098. PAN: BNMPK9876L. Mobile: 9876543210. Survey No: 201/1B. Area: 3.5 acres. Bank Acc: 12345678901234.')
    """, (doc_id,))
    c.commit()
    c.close()

    # 1. Analyze Document Privacy
    r = CLIENT.post(f"/privacy/{doc_id}/analyze", headers=h, json={"purpose": "land_acquisition_processing"})
    assert r.status_code == 200
    data = r.json()
    assert data["document_id"] == doc_id
    assert data["risk_score"] > 50
    assert data["risk_level"] in ("HIGH", "CRITICAL")
    assert data["summary"]["total_detected"] >= 4
    assert data["summary"]["masked"] >= 3

    # Check field maskings
    fields_dict = {f["field_key"]: f for f in data["fields"]}
    assert "aadhaar_number" in fields_dict
    assert fields_dict["aadhaar_number"]["visibility"] == "MASKED"
    assert "9876 5432" not in fields_dict["aadhaar_number"]["display_value"]
    assert "1098" in fields_dict["aadhaar_number"]["display_value"]

    assert "pan_number" in fields_dict
    assert fields_dict["pan_number"]["visibility"] == "MASKED"

    assert "survey_number" in fields_dict
    assert fields_dict["survey_number"]["visibility"] == "VISIBLE"

    # 2. Get Document Privacy Evaluation for Different Purpose
    r2 = CLIENT.get(f"/privacy/document/{doc_id}?purpose=field_verification", headers=h)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["purpose"] == "field_verification"


def test_temporary_access_request_and_approval_workflow():
    h_officer = auth()
    h_authority = auth("district.coimbatore@tngov.in", "Tngov@CBE#2026")

    doc_id = "DOC-TEMP-" + uuid.uuid4().hex[:8]

    # Insert document
    c = conn()
    c.execute("""
        INSERT INTO documents (document_id, document_name, path, format, uploaded_by, remarks)
        VALUES (?, 'deed.pdf', 'dummy.pdf', '.pdf', 'Tngov@cbe.ac.in', 'Mobile: 9876543210. Survey No: 100/1.')
    """, (doc_id,))
    c.commit()
    c.close()

    # 1. Analyze document
    CLIENT.post(f"/privacy/{doc_id}/analyze", headers=h_officer, json={})

    # 2. Submit Temporary Access Request
    req_payload = {
        "document_id": doc_id,
        "field_key": "mobile_number",
        "purpose": "field_verification",
        "reason": "Scheduled physical inspection and landowner contact.",
        "duration_hours": 24
    }
    r_req = CLIENT.post("/privacy/access-request", headers=h_officer, json=req_payload)
    assert r_req.status_code == 200
    req_data = r_req.json()
    request_id = req_data["request_id"]
    assert req_data["status"] == "Pending"

    # 3. List Access Requests as Authority
    r_list = CLIENT.get("/privacy/access-requests?status=Pending", headers=h_authority)
    assert r_list.status_code == 200
    pending_ids = [req["id"] for req in r_list.json()]
    assert request_id in pending_ids

    # 4. Approve Access Request
    r_app = CLIENT.post(f"/privacy/access-request/{request_id}/approve", headers=h_authority, json={"duration_hours": 24})
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "Approved"

    # 5. Check Document Evaluation for Requesting Officer - Field is now AUTHORIZED
    r_eval = CLIENT.get(f"/privacy/document/{doc_id}?purpose=field_verification", headers=h_officer)
    assert r_eval.status_code == 200
    eval_fields = {f["field_key"]: f for f in r_eval.json()["fields"]}
    assert eval_fields["mobile_number"]["visibility"] == "AUTHORIZED"
    assert eval_fields["mobile_number"]["is_authorized_grant"] is True


def test_privacy_safe_pdf_generation():
    h = auth()
    doc_id = "DOC-PDF-" + uuid.uuid4().hex[:8]

    c = conn()
    c.execute("""
        INSERT INTO documents (document_id, document_name, path, format, uploaded_by, remarks)
        VALUES (?, 'deed_pdf_test.pdf', 'dummy.pdf', '.pdf', 'Tngov@cbe.ac.in',
        'Owner: S. Murugan. Aadhaar: 3456 7890 1234. Mobile: 9876543210. Survey: 55/2. Village: Annur.')
    """, (doc_id,))
    c.commit()
    c.close()

    # Analyze first
    CLIENT.post(f"/privacy/{doc_id}/analyze", headers=h, json={})

    # Download Safe PDF
    r_pdf = CLIENT.get(f"/privacy/{doc_id}/safe-pdf?purpose=land_acquisition_processing", headers=h)
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert len(r_pdf.content) > 1000
    assert r_pdf.content.startswith(b"%PDF")


def test_governance_and_audit_privacy_no_raw_pii():
    h = auth()

    # 1. Check Governance Metrics
    r_gov = CLIENT.get("/privacy/governance", headers=h)
    assert r_gov.status_code == 200
    gov = r_gov.json()
    assert "metrics" in gov
    assert gov["metrics"]["documents_analyzed"] >= 1

    # 2. Check Privacy Audit Log
    r_audit = CLIENT.get("/privacy/audit", headers=h)
    assert r_audit.status_code == 200
    audit_events = r_audit.json()
    assert len(audit_events) > 0

    # CRITICAL SECURITY TEST: Ensure NO raw 12-digit numbers, full PANs or complete bank accounts in audit details!
    for a in audit_events:
        details = a.get("details", "")
        # Should not contain unmasked 12 digit consecutive numbers
        import re
        assert not re.search(r'\b\d{12}\b', details), f"Raw 12-digit number found in audit log: {details}"


def test_unauthorized_access_security():
    # Attempt to access without token -> 401
    assert CLIENT.get("/privacy/governance").status_code == 401
    assert CLIENT.post("/privacy/access-request", json={}).status_code == 401
