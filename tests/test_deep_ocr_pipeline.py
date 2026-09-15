import io
import uuid
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image

from backend.main import app
from backend.core import conn, UPLOADS

CLIENT = TestClient(app)

def auth(email="Tngov@cbe.ac.in", password="Tngov@CBE#2026"):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}

def create_sample_pdf_bytes(survey_no="142/3B", owner_name="Ramasamy Gounder", village="Sulur", district="Coimbatore"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Page 1
    c.drawString(72, 750, "GOVERNMENT OF TAMIL NADU - REVENUE DEPARTMENT")
    c.drawString(72, 730, "LAND ACQUISITION TITLE DEED AND PATTA EXTRACT")
    c.drawString(72, 700, "Document Number: DOC-CBE-2026-SAMPLE-001")
    c.drawString(72, 680, "Document Date: 12-Jan-2026")
    c.drawString(72, 650, f"District: {district}")
    c.drawString(72, 630, "Taluk: Sulur")
    c.drawString(72, 610, f"Village: {village}")
    c.drawString(72, 590, f"Survey Number: {survey_no}")
    c.drawString(72, 570, "Sub-Division No: 3B")
    c.drawString(72, 550, f"Pattadar / Owner Name: {owner_name}")
    c.drawString(72, 530, "Extent / Land Area: 2.45 Acres")
    c.drawString(72, 510, "Land Classification: Dry Agricultural")
    c.drawString(72, 480, "This is an authentic certified revenue extract for Land Acquisition Project NH-544.")
    c.showPage()
    
    # Page 2
    c.drawString(72, 750, "PAGE 2 - BOUNDARY SCHEDULE AND ENCUMBRANCE PARTICULARS")
    c.drawString(72, 720, "North: SF No. 142/2 (Panchayat Road)")
    c.drawString(72, 700, "South: SF No. 143/1 (Agricultural Land)")
    c.drawString(72, 680, "East: SF No. 142/4 (Canal)")
    c.drawString(72, 660, "West: Sulur Village Boundary")
    c.drawString(72, 630, "No registered encumbrances or court injunctions found for the subject parcel.")
    c.showPage()
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def test_deep_ocr_digital_pdf_pipeline():
    headers = auth()
    c = conn()
    parcel = c.execute("SELECT id, record_id, survey_no, owner_name, village, district, project_id FROM parcels WHERE district='Coimbatore' LIMIT 1").fetchone()
    c.close()
    
    survey_no = parcel["survey_no"] if parcel else "142/3B"
    owner_name = parcel["owner_name"] if parcel else "Ramasamy Gounder"
    village = parcel["village"] if parcel else "Sulur"
    district = parcel["district"] if parcel else "Coimbatore"
    project_id = parcel["project_id"] if parcel else "PRJ-001"
    parcel_db_id = parcel["id"] if parcel else ""
    
    pdf_bytes = create_sample_pdf_bytes(survey_no=survey_no, owner_name=owner_name, village=village, district=district)
    
    files = {"file": ("deed_sulur_sample.pdf", pdf_bytes, "application/pdf")}
    data = {"project_id": project_id, "parcel_id": str(parcel_db_id)}
    upload_res = CLIENT.post("/documents/", headers=headers, data=data, files=files)
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    doc_id = upload_res.json()["document_id"]
    assert doc_id
    
    proc_res = CLIENT.post(f"/ocr/{doc_id}/process", headers=headers, json={"language": "en", "mode": "auto"})
    assert proc_res.status_code == 200, f"OCR processing failed: {proc_res.text}"
    proc_data = proc_res.json()
    
    assert proc_data["document_id"] == doc_id
    assert proc_data["ocr_mode"] == "real"
    assert proc_data["is_mock_fallback"] is False
    assert proc_data["pages_processed"] == 2
    
    raw_text = proc_data.get("raw_text", "")
    assert "--- Page 1 ---" in raw_text
    assert "--- Page 2 ---" in raw_text
    assert "GOVERNMENT OF TAMIL NADU" in raw_text
    
    match = proc_data.get("match", {})
    assert match.get("status") in ["MATCHED", "PARTIAL MATCH"]
    
    get_res = CLIENT.get(f"/ocr/{doc_id}", headers=headers)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["document_id"] == doc_id
    assert get_data["raw_text"] == raw_text
    assert get_data["ocr_mode"] == "real"
    assert get_data["match"]["status"] == match["status"]
    
    pdf_res = CLIENT.get(f"/ocr/{doc_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers.get("content-type") == "application/pdf"
    assert len(pdf_res.content) > 1000
    
    verify_res = CLIENT.post(f"/ocr/{doc_id}/verify", headers=headers, json={
        "fields": {
            "survey_no": survey_no,
            "owner_name": owner_name,
            "village": village,
            "district": district
        },
        "notes": "Verified against revenue records during automated test."
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["success"] is True

def test_image_ocr_fallback_handling():
    headers = auth()
    img = Image.new("RGB", (300, 300), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    
    files = {"file": ("patta_scan.png", img_bytes.getvalue(), "image/png")}
    upload_res = CLIENT.post("/documents/", headers=headers, data={"project_id": "PRJ-001"}, files=files)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]
    
    proc_res = CLIENT.post(f"/ocr/{doc_id}/process", headers=headers, json={"language": "auto", "mode": "auto"})
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    
    assert proc_data["document_id"] == doc_id
    assert proc_data["ocr_mode"] in ["real", "synthetic"]
    assert "extractions" in proc_data
    assert "match" in proc_data

def test_invalid_document_upload():
    headers = auth()
    files = {"file": ("malicious_script.exe", b"binary content", "application/octet-stream")}
    res = CLIENT.post("/documents/", headers=headers, files=files)
    assert res.status_code == 400
    assert "Unsupported document type" in res.json().get("detail", "")
    
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = CLIENT.post("/documents/", headers=headers, files=files)
    assert res.status_code == 400
    assert "empty" in res.json().get("detail", "").lower()

def test_ocr_rejection_workflow():
    headers = auth()
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("deed_reject_test.pdf", pdf_bytes, "application/pdf")}
    upload_res = CLIENT.post("/documents/", headers=headers, files=files)
    doc_id = upload_res.json()["document_id"]
    
    CLIENT.post(f"/ocr/{doc_id}/process", headers=headers, json={})
    
    reject_res = CLIENT.post(f"/ocr/{doc_id}/reject", headers=headers, json={"reason": "Document scan is corrupted and illegible."})
    assert reject_res.status_code == 200
    assert reject_res.json()["success"] is True
    
    doc_data = CLIENT.get(f"/ocr/{doc_id}", headers=headers).json()
    assert doc_data["ocr_status"] == "Rejected"
    assert doc_data["rejection_reason"] == "Document scan is corrupted and illegible."