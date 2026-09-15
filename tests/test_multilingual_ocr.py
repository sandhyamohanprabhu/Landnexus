"""
LANDNEXUS - Multilingual Indian-Language Land Record OCR Test Suite
Compliant with SIH Problem Statement 26018
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.main import app
from backend.core import conn, UPLOADS
from backend.services.ocr_service import (
    detect_script_and_language,
    extract_multilingual_fields,
    check_duplicate_parcel,
    SUPPORTED_LANGUAGES,
    preprocess_image
)

CLIENT = TestClient(app)

def auth(email="Tngov@cbe.ac.in", password="Tngov@CBE#2026"):
    r = CLIENT.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}

def create_test_image(filename):
    p = UPLOADS / filename
    img = Image.new("RGB", (200, 200), color="white")
    img.save(p)
    return p

def test_script_and_language_detection():
    # Tamil text
    ta_res = detect_script_and_language("தமிழ்நாடு அரசு நில நிர்வாகத்துறை பட்டா எண்: 452 புல எண்: 142/3B")
    assert ta_res["language"] == "ta"
    assert ta_res["script"] == "Tamil"
    assert ta_res["confidence"] > 0.80

    # Devanagari Hindi text
    hi_res = detect_script_and_language("राजस्व विभाग भू-अभिलेख खसरा संख्या: 312/1 खाता संख्या: 88")
    assert hi_res["language"] == "hi"
    assert hi_res["script"] == "Devanagari"

    # Devanagari Marathi text
    mr_res = detect_script_and_language("महाराष्ट्र शासन भूमी अभिलेख गाव नमुना ७/१२ सर्व्हे गट क्रमांक: 215/4 खातेदार")
    assert mr_res["language"] == "mr"
    assert mr_res["script"] == "Devanagari"

    # Telugu text
    te_res = detect_script_and_language("రెవెన్యూ రికార్డు పట్టాదారు పాస్ పుస్తకం సర్వే నెం: 89/2A")
    assert te_res["language"] == "te"
    assert te_res["script"] == "Telugu"

    # English text
    en_res = detect_script_and_language("Government of Tamil Nadu Survey No: 123/4A Village: Sulur")
    assert en_res["language"] == "en"
    assert en_res["script"] == "Latin"

def test_image_preprocessing_pipeline(tmp_path):
    img_p = tmp_path / "raw_deed.png"
    im = Image.new("RGB", (600, 400), color="gray")
    im.save(img_p)

    out_p = tmp_path / "proc_raw_deed.png"
    metrics = preprocess_image(img_p, out_p)
    assert out_p.exists()
    assert "grayscale" in metrics["steps_applied"]
    assert "auto_contrast" in metrics["steps_applied"]
    assert "median_denoise" in metrics["steps_applied"]
    assert metrics["original_width"] == 600

def test_multilingual_field_extraction():
    ta_sample = """
    தமிழ்நாடு அரசு
    பட்டா எண்: 452
    புல எண்: 142/3B
    உரிமையாளர் பெயர்: சுப்பிரமணியன் கே
    நிலப்பரப்பு: 2.75 ஏக்கர்
    வருவாய் கிராமம்: சூலூர்
    வட்டம்: சூலூர்
    மாவட்டம்: கோயம்புத்தூர்
    """
    extracted = extract_multilingual_fields(ta_sample, detected_lang="ta")
    assert extracted["survey_number"]["value"] == "142/3B"
    assert extracted["survey_number"]["confidence"] > 0.70
    assert "சுப்பிரமணியன்" in extracted["owner_name"]["value"]
    assert extracted["village"]["value"] == "சூலூர்"

def test_handwritten_mode_rejection():
    h = auth()
    doc_id = "DOC-HW-" + uuid.uuid4().hex[:8]
    img_path = create_test_image(f"{doc_id}.png")

    c = conn()
    c.execute("INSERT INTO documents (document_id, document_name, path, format, uploaded_by, verification_status, ocr_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (doc_id, f"{doc_id}.png", str(img_path), ".png", "Tngov@cbe.ac.in", "Pending", "Not Started"))
    c.commit()
    c.close()

    r = CLIENT.post(f"/ocr/{doc_id}/process", headers=h, json={"language": "auto", "mode": "handwritten"})
    assert r.status_code == 400
    assert "Selected language/handwriting model is not available in the current deployment." in r.text

def test_multilingual_ocr_processing_lifecycle():
    h = auth()
    doc_id = "DOC-MULTI-" + uuid.uuid4().hex[:8]
    img_path = create_test_image(f"{doc_id}.png")

    c = conn()
    c.execute("INSERT INTO documents (document_id, document_name, path, format, uploaded_by, verification_status, ocr_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (doc_id, f"{doc_id}.png", str(img_path), ".png", "Tngov@cbe.ac.in", "Pending", "Not Started"))
    c.commit()
    c.close()

    # 1. Process OCR
    r = CLIENT.post(f"/ocr/{doc_id}/process", headers=h, json={"language": "ta", "mode": "auto"})
    assert r.status_code == 200
    data = r.json()
    assert data["ocr_status"] == "Verification Required"
    assert data["language"] in ("ta", "en")
    assert "extractions" in data
    assert "detailed_extractions" in data

    # 2. Get OCR details
    r_get = CLIENT.get(f"/ocr/{doc_id}", headers=h)
    assert r_get.status_code == 200
    det = r_get.json()
    assert det["document_id"] == doc_id
    assert len(det["extractions"]) > 0

    # 3. Verify OCR with human correction (active learning)
    corr_fields = {
        "survey_number": "142/3B-CORRECTED",
        "owner_name": "Subramanian K (Verified)",
        "village": "Sulur",
        "taluk": "Sulur",
        "district": "Coimbatore"
    }
    r_ver = CLIENT.post(f"/ocr/{doc_id}/verify", headers=h, json={"fields": corr_fields, "notes": "Field survey confirmed subdivision 3B"})
    assert r_ver.status_code == 200
    assert r_ver.json()["success"] is True

    # 4. Verify learning records stored
    c = conn()
    lr_row = c.execute("SELECT * FROM ocr_learning_records WHERE document_id=?", (doc_id,)).fetchall()
    assert len(lr_row) > 0
    c.close()

    # 5. Verify PDF Report Generation
    r_pdf = CLIENT.get(f"/ocr/{doc_id}/pdf", headers=h)
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert len(r_pdf.content) > 1000

def test_ocr_rejection_workflow():
    h = auth()
    doc_id = "DOC-REJ-" + uuid.uuid4().hex[:8]
    img_path = create_test_image(f"{doc_id}.png")

    c = conn()
    c.execute("INSERT INTO documents (document_id, document_name, path, format, uploaded_by, verification_status, ocr_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (doc_id, f"{doc_id}.png", str(img_path), ".png", "Tngov@cbe.ac.in", "Pending", "Not Started"))
    c.commit()
    c.close()

    r_proc = CLIENT.post(f"/ocr/{doc_id}/process", headers=h, json={"language": "hi", "mode": "auto"})
    assert r_proc.status_code == 200

    r_rej = CLIENT.post(f"/ocr/{doc_id}/reject", headers=h, json={"reason": "Blurred scan unreadable upon human review"})
    assert r_rej.status_code == 200

    c = conn()
    doc_row = c.execute("SELECT ocr_status, rejection_reason FROM documents WHERE document_id=?", (doc_id,)).fetchone()
    assert doc_row["ocr_status"] == "Rejected"
    assert "Blurred" in doc_row["rejection_reason"]
    c.close()

def test_verification_queue_and_analytics():
    h = auth()
    r_q = CLIENT.get("/ocr/verification-queue?district=Coimbatore", headers=h)
    assert r_q.status_code == 200
    assert "queue" in r_q.json()
    assert "count" in r_q.json()

    r_ana = CLIENT.get("/ocr/analytics?district=Coimbatore", headers=h)
    assert r_ana.status_code == 200
    ana = r_ana.json()
    assert "total_documents_processed" in ana
    assert "average_confidence" in ana
    assert "language_breakdown" in ana
    assert "active_learning_corrections" in ana

