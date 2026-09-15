"""
Seed Controlled Synthetic Demonstration Parcels (SYN-PARCEL-001 through SYN-PARCEL-005)
Strictly compliant with SURVI / LANDNEXUS schema and testing instructions.
ALL DATA ARE DETERMINISTIC, SYNTHETIC, AND DEMONSTRATION-ONLY.
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "survi.db"

SYNTHETIC_PARCELS = [
    {
        "record_id": "SYN-PARCEL-001",
        "survey_no": "SYN-101",
        "subdivision": "1A",
        "village": "Sulur Town",
        "taluk": "Sulur",
        "district": "Coimbatore",
        "area": 2.50,
        "area_unit": "acres",
        "classification": "Ryotwari Dry",
        "land_use": "Agricultural - Synthetic Test",
        "project_id": "PRJ-03428",
        "latitude": 11.0250,
        "longitude": 77.1250,
        "validation_status": "VALID",
        "risk_category": "LOW",
        "risk_probability": 0.15,
        "risk_score": 15.0,
        "delay_probability": 0.15,
        "training_label": "LOW",
        "owner_reference": "citizen.demo.syn001@example.com",
        "owner_name": "Thiru. Synthetic Landowner A",
        "mobile_number": "9876543210",
        "acquisition_status": "Joint Survey Completed",
        "remarks": "SYNTHETIC DATA — NOT REAL. Controlled test parcel 001 with closed polygon boundary.",
        # Closed polygon [lat, lon] for Leaflet Polygon
        "boundary_coordinates": [
            [11.0245, 77.1245],
            [11.0255, 77.1245],
            [11.0255, 77.1255],
            [11.0245, 77.1255],
            [11.0245, 77.1245]
        ]
    },
    {
        "record_id": "SYN-PARCEL-002",
        "survey_no": "SYN-102",
        "subdivision": "2B",
        "village": "Sulur Town",
        "taluk": "Sulur",
        "district": "Coimbatore",
        "area": 4.10,
        "area_unit": "acres",
        "classification": "Ryotwari Wet",
        "land_use": "Agricultural - Synthetic Test",
        "project_id": "PRJ-03428",
        "latitude": 11.0280,
        "longitude": 77.1280,
        "validation_status": "VALID",
        "risk_category": "MEDIUM",
        "risk_probability": 0.48,
        "risk_score": 48.0,
        "delay_probability": 0.48,
        "training_label": "MEDIUM",
        "owner_reference": "citizen.demo.syn002@example.com",
        "owner_name": "Tmt. Synthetic Landowner B",
        "mobile_number": "9876543211",
        "acquisition_status": "Section 11(1) Notification",
        "remarks": "SYNTHETIC DATA — NOT REAL. Controlled test parcel 002 with closed polygon boundary.",
        "boundary_coordinates": [
            [11.0275, 77.1275],
            [11.0285, 77.1275],
            [11.0285, 77.1285],
            [11.0275, 77.1285],
            [11.0275, 77.1275]
        ]
    },
    {
        "record_id": "SYN-PARCEL-003",
        "survey_no": "SYN-103",
        "subdivision": "1",
        "village": "Sulur Town",
        "taluk": "Sulur",
        "district": "Coimbatore",
        "area": 1.80,
        "area_unit": "acres",
        "classification": "Ryotwari Dry",
        "land_use": "Commercial - Synthetic Test",
        "project_id": "PRJ-03428",
        "latitude": 11.0220,
        "longitude": 77.1220,
        "validation_status": "VALID",
        "risk_category": "HIGH",
        "risk_probability": 0.76,
        "risk_score": 76.0,
        "delay_probability": 0.76,
        "training_label": "HIGH",
        "owner_reference": "citizen.demo.syn003@example.com",
        "owner_name": "Thiru. Synthetic Landowner C",
        "mobile_number": "9876543212",
        "acquisition_status": "Compensation In Progress",
        "remarks": "SYNTHETIC DATA — NOT REAL. Controlled test parcel 003 with closed polygon boundary.",
        "boundary_coordinates": [
            [11.0215, 77.1215],
            [11.0225, 77.1215],
            [11.0225, 77.1225],
            [11.0215, 77.1225],
            [11.0215, 77.1215]
        ]
    },
    {
        "record_id": "SYN-PARCEL-004",
        "survey_no": "SYN-104",
        "subdivision": "3C",
        "village": "Sulur Town",
        "taluk": "Sulur",
        "district": "Coimbatore",
        "area": 5.60,
        "area_unit": "acres",
        "classification": "Poramboke Ground",
        "land_use": "Industrial - Synthetic Test",
        "project_id": "PRJ-03428",
        "latitude": 11.0310,
        "longitude": 77.1310,
        "validation_status": "VALID",
        "risk_category": "CRITICAL",
        "risk_probability": 0.92,
        "risk_score": 92.0,
        "delay_probability": 0.92,
        "training_label": "CRITICAL",
        "owner_reference": "citizen.demo.syn004@example.com",
        "owner_name": "Thiru. Synthetic Landowner D",
        "mobile_number": "9876543213",
        "acquisition_status": "Section 19 Declaration",
        "remarks": "SYNTHETIC DATA — NOT REAL. Controlled test parcel 004 with closed polygon boundary.",
        "boundary_coordinates": [
            [11.0305, 77.1305],
            [11.0315, 77.1305],
            [11.0315, 77.1315],
            [11.0305, 77.1315],
            [11.0305, 77.1305]
        ]
    },
    {
        "record_id": "SYN-PARCEL-005",
        "survey_no": "SYN-105",
        "subdivision": "4",
        "village": "Sulur Town",
        "taluk": "Sulur",
        "district": "Coimbatore",
        "area": 3.00,
        "area_unit": "acres",
        "classification": "Ryotwari Dry",
        "land_use": "Agricultural - Synthetic Test",
        "project_id": "PRJ-03428",
        "latitude": 11.0200,
        "longitude": 77.1200,
        "validation_status": "VALID",
        "risk_category": "LOW",
        "risk_probability": 0.10,
        "risk_score": 10.0,
        "delay_probability": 0.10,
        "training_label": "LOW",
        "owner_reference": "citizen.demo.syn005@example.com",
        "owner_name": "Tmt. Synthetic Landowner E",
        "mobile_number": "9876543214",
        "acquisition_status": "Proposal",
        "remarks": "SYNTHETIC DATA — NOT REAL. Controlled test parcel 005 WITHOUT polygon boundary to verify coordinate-only behavior.",
        "boundary_coordinates": None
    }
]

def seed_synthetic_parcels():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row

    # Ensure boundary_geojson column exists
    cols = [r["name"] for r in c.execute("PRAGMA table_info(parcels)").fetchall()]
    if "boundary_geojson" not in cols:
        c.execute("ALTER TABLE parcels ADD COLUMN boundary_geojson TEXT")

    # Insert or update synthetic parcels
    seeded_ids = []
    for p in SYNTHETIC_PARCELS:
        boundary_json = json.dumps(p["boundary_coordinates"]) if p["boundary_coordinates"] else None
        existing = c.execute("SELECT id FROM parcels WHERE record_id=?", (p["record_id"],)).fetchone()
        
        if existing:
            c.execute("""
                UPDATE parcels SET
                    survey_no=?, subdivision=?, village=?, taluk=?, district=?,
                    area=?, area_unit=?, classification=?, land_use=?, project_id=?,
                    latitude=?, longitude=?, validation_status=?, risk_category=?,
                    risk_probability=?, risk_score=?, delay_probability=?, training_label=?,
                    owner_reference=?, owner_name=?, mobile_number=?, acquisition_status=?,
                    remarks=?, boundary_geojson=?
                WHERE record_id=?
            """, (
                p["survey_no"], p["subdivision"], p["village"], p["taluk"], p["district"],
                p["area"], p["area_unit"], p["classification"], p["land_use"], p["project_id"],
                p["latitude"], p["longitude"], p["validation_status"], p["risk_category"],
                p["risk_probability"], p["risk_score"], p["delay_probability"], p["training_label"],
                p["owner_reference"], p["owner_name"], p["mobile_number"], p["acquisition_status"],
                p["remarks"], boundary_json, p["record_id"]
            ))
            pid = existing["id"]
        else:
            cur = c.execute("""
                INSERT INTO parcels (
                    record_id, survey_no, subdivision, village, taluk, district,
                    area, area_unit, classification, land_use, project_id,
                    latitude, longitude, validation_status, risk_category,
                    risk_probability, risk_score, delay_probability, training_label,
                    owner_reference, owner_name, mobile_number, acquisition_status,
                    remarks, boundary_geojson, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'system_synthetic_seed')
            """, (
                p["record_id"], p["survey_no"], p["subdivision"], p["village"], p["taluk"], p["district"],
                p["area"], p["area_unit"], p["classification"], p["land_use"], p["project_id"],
                p["latitude"], p["longitude"], p["validation_status"], p["risk_category"],
                p["risk_probability"], p["risk_score"], p["delay_probability"], p["training_label"],
                p["owner_reference"], p["owner_name"], p["mobile_number"], p["acquisition_status"],
                p["remarks"], boundary_json
            ))
            pid = cur.lastrowid
        
        seeded_ids.append((p["record_id"], pid))

    # Ensure field assignment exists for SYN-PARCEL-001 assigned to field.coimbatore@tngov.in
    syn1_pid = next(pid for rec_id, pid in seeded_ids if rec_id == "SYN-PARCEL-001")
    fa = c.execute("SELECT id FROM field_assignments WHERE parcel_id=? AND lower(officer_email)='field.coimbatore@tngov.in'", (syn1_pid,)).fetchone()
    if not fa:
        c.execute("""
            INSERT INTO field_assignments (parcel_id, officer_email, assigned_by, status, project_id, district, state)
            VALUES (?, 'field.coimbatore@tngov.in', 'district.coimbatore@tngov.in', 'Pending Verification', 'PRJ-03428', 'Coimbatore', 'Tamil Nadu')
        """, (syn1_pid,))

    # Ensure demo document exists for SYN-PARCEL-001
    doc = c.execute("SELECT id FROM documents WHERE parcel_id=?", (syn1_pid,)).fetchone()
    if not doc:
        doc_id = "DOC-SYN-001"
        c.execute("""
            INSERT INTO documents (document_id, project_id, parcel_id, document_name, path, format, uploaded_by, verification_status, ocr_status, ocr_confidence, remarks)
            VALUES (?, 'PRJ-03428', ?, 'Synthetic_Patta_Document_SYN101.pdf', 'uploads/Synthetic_Patta_Document_SYN101.pdf', 'pdf', 'district.coimbatore@tngov.in', 'Verified', 'Completed', 0.96, 'SYNTHETIC DEMO DOCUMENT — NOT REAL')
        """, (doc_id, syn1_pid))
        
        # Add OCR Extractions
        c.execute("""
            INSERT INTO ocr_extractions (document_id, field_name, value, confidence, validation_status, human_verified)
            VALUES (?, 'survey_number', 'SYN-101', 0.98, 'Valid', 1)
        """, (doc_id,))
        c.execute("""
            INSERT INTO ocr_extractions (document_id, field_name, value, confidence, validation_status, human_verified)
            VALUES (?, 'owner_name', 'Thiru. Synthetic Landowner A', 0.95, 'Valid', 1)
        """, (doc_id,))
        c.execute("""
            INSERT INTO ocr_extractions (document_id, field_name, value, confidence, validation_status, human_verified)
            VALUES (?, 'land_extent_acres', '2.50', 0.97, 'Valid', 1)
        """, (doc_id,))

    c.commit()
    c.close()
    print(f"Successfully seeded {len(seeded_ids)} controlled synthetic parcels:")
    for rec_id, pid in seeded_ids:
        print(f"  • {rec_id} (Internal DB ID: {pid})")

if __name__ == "__main__":
    seed_synthetic_parcels()
