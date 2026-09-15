"""
LANDNEXUS - 5-District Synthetic Data Seeder
============================================
Creates a reusable pool of 500 land parcels for EACH of:
  - Tiruppur (500)
  - Erode (500)
  - Salem (500)
  - Namakkal (500)
Existing Coimbatore parcels are preserved completely UNTOUCHED.

Creates multiple realistic projects per district, assigning a realistic subset
(e.g., 18, 27, 12, 35) to projects while leaving ~400 parcels per district
in the unassigned pool (project_id = NULL).

Populates linked operational data:
  - project_milestones (for SLA and Bottleneck Detection)
  - compensation (varied statuses: Not Started to Fully Paid)
  - field_assignments & field_verifications
  - grievances (varied statuses: Open to Escalated)
  - alerts (operational alerts per district)
  - documents (cadastral survey, title deeds, notifications)
  - risk_predictions
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, date, timedelta

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "survi.db"

random.seed(42)

DISTRICTS_DATA = {
    "Tiruppur": {
        "code": "TIR",
        "taluks": [
            ("Tiruppur North", ["15 Velampalayam", "Mannarai", "Perumanallur", "Chettipalayam", "Kaniyur"]),
            ("Tiruppur South", ["Veerapandi", "Nallur", "Mudalipalayam", "Andipalayam", "Ugayanur"]),
            ("Avinashi", ["Avinashi", "Sevur", "Karamadai", "Velayuthampalayam", "Alathur"]),
            ("Palladam", ["Palladam", "Samalapuram", "Karadivavi", "Karanampettai", "Vadamambalam"]),
            ("Dharapuram", ["Dharapuram", "Kundadam", "Mulanur", "Alangiam", "Kallimanthayam"]),
            ("Kangeyam", ["Kangeyam", "Uthukuli", "Nathakadaiyur", "Sivanmalai", "Chennimalai"]),
            ("Udumalaipettai", ["Udumalaipettai", "Kaniyur", "Madathukulam", "Dhali", "Poolavadi"]),
        ],
        "center_lat": 11.1085,
        "center_lon": 77.3411,
        "lat_range": (11.00, 11.22),
        "lon_range": (77.25, 77.45),
        "projects": [
            {
                "id": "PRJ-TIR-001",
                "name": "Tiruppur Smart Textile Corridor & Ring Road",
                "type": "Road",
                "taluk": "Tiruppur North",
                "village": "Perumanallur",
                "stage": "Compensation",
                "status": "Active",
                "progress": 68.5,
                "parcels_to_assign": 18,
                "dept": "State Highways Department",
            },
            {
                "id": "PRJ-TIR-002",
                "name": "Palladam Industrial Logistics Park & Rail Spur",
                "type": "Rail",
                "taluk": "Palladam",
                "village": "Samalapuram",
                "stage": "Award",
                "status": "Delayed",
                "progress": 52.0,
                "parcels_to_assign": 27,
                "dept": "Southern Railway / TIDCO",
            },
            {
                "id": "PRJ-TIR-003",
                "name": "Amaravathi River Basin Irrigation Channel Modernization",
                "type": "Irrigation",
                "taluk": "Dharapuram",
                "village": "Kundadam",
                "stage": "Notification",
                "status": "Active",
                "progress": 30.0,
                "parcels_to_assign": 12,
                "dept": "Water Resources Department",
            },
            {
                "id": "PRJ-TIR-004",
                "name": "Avinashi Multi-Modal Freight Terminal",
                "type": "Industrial",
                "taluk": "Avinashi",
                "village": "Sevur",
                "stage": "Rehabilitation",
                "status": "At Risk",
                "progress": 82.0,
                "parcels_to_assign": 35,
                "dept": "SIPCOT",
            },
            {
                "id": "PRJ-TIR-005",
                "name": "Udumalaipettai Solar Renewable Energy Zone",
                "type": "Industrial",
                "taluk": "Udumalaipettai",
                "village": "Dhali",
                "stage": "Proposal",
                "status": "Pending",
                "progress": 10.0,
                "parcels_to_assign": 15,
                "dept": "TANGEDCO",
            },
        ],
    },
    "Erode": {
        "code": "ERO",
        "taluks": [
            ("Erode", ["Brough Road", "Surampatti", "Kasipalayam", "Periasemur", "Veerappanchatram"]),
            ("Perundurai", ["Perundurai", "Ingur", "Seenapuram", "Vijayapuri", "Kullampalayam"]),
            ("Bhavani", ["Bhavani", "Komarayanur", "Oricheri", "Mylambadi", "Kurichi"]),
            ("Gobichettipalayam", ["Gobichettipalayam", "Lakkampatti", "Kallipatti", "Nambiyur", "Kugalur"]),
            ("Sathyamangalam", ["Sathyamangalam", "Bhavanisagar", "Pungar", "Bannari", "Rajan Nagar"]),
            ("Anthiyur", ["Anthiyur", "Brammadesam", "Burgur", "Ennamangalam", "Moongilpatti"]),
            ("Kodumudi", ["Kodumudi", "Sivagiri", "Kombanai", "Unjalur", "Chennimalai"]),
        ],
        "center_lat": 11.3410,
        "center_lon": 77.7172,
        "lat_range": (11.22, 11.45),
        "lon_range": (77.60, 77.85),
        "projects": [
            {
                "id": "PRJ-ERO-001",
                "name": "Erode-Bhavani Riverfront Expressway",
                "type": "Road",
                "taluk": "Bhavani",
                "village": "Komarayanur",
                "stage": "Possession",
                "status": "Active",
                "progress": 78.0,
                "parcels_to_assign": 20,
                "dept": "Highways Department",
            },
            {
                "id": "PRJ-ERO-002",
                "name": "Perundurai SIPCOT Green Pharma Cluster Expansion",
                "type": "Industrial",
                "taluk": "Perundurai",
                "village": "Ingur",
                "stage": "Compensation",
                "status": "Delayed",
                "progress": 62.0,
                "parcels_to_assign": 30,
                "dept": "SIPCOT",
            },
            {
                "id": "PRJ-ERO-003",
                "name": "Bhavanisagar Reservoir Agricultural Canal Extension",
                "type": "Irrigation",
                "taluk": "Sathyamangalam",
                "village": "Bhavanisagar",
                "stage": "Notification",
                "status": "Active",
                "progress": 25.0,
                "parcels_to_assign": 15,
                "dept": "Public Works Department",
            },
            {
                "id": "PRJ-ERO-004",
                "name": "Gobichettipalayam High-Tech Agro Food Park",
                "type": "Industrial",
                "taluk": "Gobichettipalayam",
                "village": "Lakkampatti",
                "stage": "Approval",
                "status": "Pending",
                "progress": 40.0,
                "parcels_to_assign": 25,
                "dept": "Agricultural Marketing Board",
            },
            {
                "id": "PRJ-ERO-005",
                "name": "Anthiyur Tribal Access Road & Bridge Project",
                "type": "Road",
                "taluk": "Anthiyur",
                "village": "Burgur",
                "stage": "Legal Dispute / Resolution",
                "status": "At Risk",
                "progress": 35.0,
                "parcels_to_assign": 14,
                "dept": "Rural Development Department",
            },
        ],
    },
    "Salem": {
        "code": "SAL",
        "taluks": [
            ("Salem", ["Hasthampatti", "Ammapet", "Suramangalam", "Fairlands", "Shevapet"]),
            ("Salem West", ["Kandhampatty", "Jagir Ammapalayam", "Meyyanur", "Sivathapuram", "Alagapuram"]),
            ("Salem South", ["Veerapandi", "Attayampatti", "Panamarathupatti", "Mallur", "Dasanaickenpatti"]),
            ("Omalur", ["Omalur", "Tharamangalam", "Karuppur", "Kollapatti", "Pagalpatti"]),
            ("Mettur", ["Mettur Dam", "Kolathur", "Mecheri", "Palamalai", "Koonandiyur"]),
            ("Attur", ["Attur", "Narasingapuram", "Thalaivasal", "Malliyakarai", "Manivilundan"]),
            ("Sankari", ["Sankari", "Magudanchavadi", "Thevoor", "Idappadi", "Pullipalayam"]),
        ],
        "center_lat": 11.6643,
        "center_lon": 78.1460,
        "lat_range": (11.55, 11.75),
        "lon_range": (78.05, 78.25),
        "projects": [
            {
                "id": "PRJ-SAL-001",
                "name": "Salem Steel Plant Metro Transit Corridor",
                "type": "Rail",
                "taluk": "Salem West",
                "village": "Jagir Ammapalayam",
                "stage": "Award",
                "status": "Active",
                "progress": 55.0,
                "parcels_to_assign": 22,
                "dept": "Chennai Metro Rail / Southern Railway",
            },
            {
                "id": "PRJ-SAL-002",
                "name": "Omalur Aerospace & Defense Industrial Park",
                "type": "Industrial",
                "taluk": "Omalur",
                "village": "Karuppur",
                "stage": "Compensation",
                "status": "Delayed",
                "progress": 65.0,
                "parcels_to_assign": 28,
                "dept": "TIDCO Defense Corridor",
            },
            {
                "id": "PRJ-SAL-003",
                "name": "Mettur Dam Industrial Water Supply Grid Phase II",
                "type": "Irrigation",
                "taluk": "Mettur",
                "village": "Mecheri",
                "stage": "Possession",
                "status": "Active",
                "progress": 75.0,
                "parcels_to_assign": 14,
                "dept": "TWAD Board",
            },
            {
                "id": "PRJ-SAL-004",
                "name": "Salem-Attur-Cuddalore Economic Corridor 4-Laning",
                "type": "Road",
                "taluk": "Attur",
                "village": "Narasingapuram",
                "stage": "Rehabilitation",
                "status": "At Risk",
                "progress": 85.0,
                "parcels_to_assign": 36,
                "dept": "National Highways Authority (NHAI)",
            },
            {
                "id": "PRJ-SAL-005",
                "name": "Sankari Logistics & Bulk Cement Transshipment Yard",
                "type": "Industrial",
                "taluk": "Sankari",
                "village": "Magudanchavadi",
                "stage": "Proposal",
                "status": "Pending",
                "progress": 15.0,
                "parcels_to_assign": 16,
                "dept": "State Transport Department",
            },
        ],
    },
    "Namakkal": {
        "code": "NMK",
        "taluks": [
            ("Namakkal", ["Thillaipuram", "Erumapatti", "Siluvampatti", "Vagurampatti", "Nallipalayam"]),
            ("Rasipuram", ["Rasipuram", "Vennandur", "Pillanallur", "Gurusamipalayam", "Singalandapuram"]),
            ("Tiruchengode", ["Tiruchengode", "Mallasamudram", "Elachipalayam", "Molasi", "Devanankurichi"]),
            ("Paramathi Velur", ["Paramathi", "Velur", "Pothanur", "Pandamangalam", "Kabilarmalai"]),
            ("Sendamangalam", ["Sendamangalam", "Kalappanaickenpatti", "Kollimalai Foothills", "Belukurichi"]),
            ("Mohanur", ["Mohanur", "Arasur", "Kumarapalayam", "Oruvandur", "Madakasampatti"]),
            ("Komarapalayam", ["Komarapalayam", "Padaiveedu", "Sanniyasipatti", "Kallakkurichi"]),
        ],
        "center_lat": 11.2189,
        "center_lon": 78.1674,
        "lat_range": (11.10, 11.35),
        "lon_range": (78.05, 78.30),
        "projects": [
            {
                "id": "PRJ-NMK-001",
                "name": "Namakkal Poultry & Agro Logistic Express Hub",
                "type": "Industrial",
                "taluk": "Namakkal",
                "village": "Siluvampatti",
                "stage": "Compensation",
                "status": "Active",
                "progress": 60.0,
                "parcels_to_assign": 16,
                "dept": "Agricultural Marketing & Agri-Business",
            },
            {
                "id": "PRJ-NMK-002",
                "name": "Tiruchengode-Erode Cauvery High-Level Bridge & Bypass",
                "type": "Road",
                "taluk": "Tiruchengode",
                "village": "Molasi",
                "stage": "Award",
                "status": "Delayed",
                "progress": 48.0,
                "parcels_to_assign": 24,
                "dept": "Highways Department",
            },
            {
                "id": "PRJ-NMK-003",
                "name": "Cauvery Lift Irrigation Scheme for Sendamangalam",
                "type": "Irrigation",
                "taluk": "Sendamangalam",
                "village": "Belukurichi",
                "stage": "Notification",
                "status": "Active",
                "progress": 32.0,
                "parcels_to_assign": 10,
                "dept": "Water Resources Department",
            },
            {
                "id": "PRJ-NMK-004",
                "name": "Rasipuram Heavy Engineering & Truck Body Building SEZ",
                "type": "Industrial",
                "taluk": "Rasipuram",
                "village": "Vennandur",
                "stage": "Possession",
                "status": "At Risk",
                "progress": 72.0,
                "parcels_to_assign": 30,
                "dept": "SIPCOT",
            },
            {
                "id": "PRJ-NMK-005",
                "name": "Mohanur Bio-Ethanol Refinery Rail Feeder Line",
                "type": "Rail",
                "taluk": "Mohanur",
                "village": "Arasur",
                "stage": "Proposal",
                "status": "Pending",
                "progress": 12.0,
                "parcels_to_assign": 12,
                "dept": "Sugar Mills Corporation / Railways",
            },
        ],
    },
}

TAMIL_FIRST_NAMES = [
    "Murugan", "Kandasamy", "Subramanian", "Palanisamy", "Selvan", "Shanmugam",
    "Arumugam", "Ramasamy", "Periasamy", "Muthusamy", "Dhanapal", "Kumar",
    "Senthil", "Saravanan", "Velusamy", "Karthik", "Manickam", "Thangaraj",
    "Balasubramaniam", "Natarajan", "Ganesan", "Sivalingam", "Ranganathan",
    "Lakshmi", "Kavitha", "Parvathi", "Revathi", "Dhanalakshmi", "Saraswathi",
    "Mallika", "Kalavathi", "Radha", "Meenakshi", "Gowri", "Balamani"
]

TAMIL_INITIALS = ["A", "B", "C", "D", "G", "K", "M", "N", "P", "R", "S", "T", "V"]

LAND_CLASSIFICATIONS = [
    ("Wet Land (Nanja)", 0.35),
    ("Dry Land (Punja)", 0.40),
    ("Commercial", 0.08),
    ("Industrial", 0.07),
    ("Residential", 0.06),
    ("Poramboke (Government)", 0.04),
]

STAGES_ORDER = [
    "Proposal", "SIA / Survey", "Notification", "Legal Dispute / Resolution",
    "Approval", "Award", "Compensation", "Possession", "Rehabilitation", "Closure / Completion"
]


def _random_classification():
    r = random.random()
    cum = 0
    for cls, weight in LAND_CLASSIFICATIONS:
        cum += weight
        if r <= cum:
            return cls
    return "Dry Land (Punja)"


def seed_districts():
    print(f"Connecting to database: {DB}")
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    # 1. Check existing Coimbatore parcels count to ensure untouched
    cbe_count = c.execute("SELECT COUNT(*) FROM parcels WHERE district='Coimbatore'").fetchone()[0]
    print(f"  Existing Coimbatore parcels: {cbe_count} (PRESERVED UNTOUCHED)")

    # 2. Check if new districts already have parcels
    for district_name, dinfo in DISTRICTS_DATA.items():
        existing = c.execute("SELECT COUNT(*) FROM parcels WHERE district=?", (district_name,)).fetchone()[0]
        if existing >= 500:
            print(f"  {district_name} already has {existing} parcels. Skipping parcel insertion.")
            continue

        print(f"\n--- Seeding {district_name} (500 Parcels & Projects) ---")
        code = dinfo["code"]
        taluk_list = dinfo["taluks"]
        projects = dinfo["projects"]

        # 2a. Insert Projects for this district
        print(f"  Inserting {len(projects)} projects for {district_name}...")
        for p in projects:
            c.execute("""
                INSERT OR REPLACE INTO projects (
                    project_id, project_name, project_type, district, taluk, village,
                    department, priority, current_stage, project_status, progress,
                    total_land_required, affected_parcels, affected_families,
                    project_start_date, planned_completion_date, responsible_officer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["name"], p["type"], district_name, p["taluk"], p["village"],
                p["dept"], "High" if p["status"] in ("Delayed", "At Risk") else "Medium",
                p["stage"], p["status"], p["progress"],
                round(p["parcels_to_assign"] * random.uniform(1.2, 2.8), 2),
                p["parcels_to_assign"],
                int(p["parcels_to_assign"] * random.uniform(1.0, 1.8)),
                "2024-01-15", "2026-12-31", f"officer.{code.lower()}@tngov.in"
            ))

            # Milestones for SLA & Bottlenecks
            for st_idx, st in enumerate(STAGES_ORDER):
                is_completed = STAGES_ORDER.index(p["stage"]) > st_idx if p["stage"] in STAGES_ORDER else False
                is_current = (st == p["stage"])
                delay_days = random.randint(16, 45) if (is_current and p["status"] in ("Delayed", "At Risk")) else (0 if is_completed else random.choice([0, 0, 5, 12]))
                m_status = "Completed" if is_completed else ("In Progress" if is_current else "Pending")
                c.execute("""
                    INSERT OR REPLACE INTO project_milestones (
                        project_id, stage, status, delay_days, planned_date, expected_date, responsible_officer
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["id"], st, m_status, delay_days,
                    "2024-03-01",
                    "2024-06-30" if is_completed else "2025-05-31",
                    f"officer.{code.lower()}@tngov.in"
                ))

        # 2b. Generate 500 parcels
        # We assign subsets to projects, and leave the rest with project_id = NULL
        print(f"  Generating 500 parcels for {district_name}...")
        assigned_quota = {}
        for p in projects:
            assigned_quota[p["id"]] = p["parcels_to_assign"]

        total_to_assign = sum(assigned_quota.values())
        print(f"    Parcels to assign to projects: {total_to_assign}")
        print(f"    Parcels to keep unassigned: {500 - total_to_assign}")

        current_proj_idx = 0
        proj_assigned_count = {p["id"]: 0 for p in projects}

        for i in range(1, 501):
            record_id = f"REC-{code}-{i:04d}"
            t_info = taluk_list[(i - 1) % len(taluk_list)]
            taluk_name = t_info[0]
            village_name = t_info[1][(i - 1) % len(t_info[1])]

            survey_base = 100 + (i // 5)
            sub_num = ((i - 1) % 5) + 1
            sub_suffix = random.choice(["", "A", "B", "C", "/1", "/2"])
            survey_no = f"{survey_base}/{sub_num}{sub_suffix}"
            subdivision = f"{sub_num}{sub_suffix}" if sub_suffix else f"{sub_num}"

            area = round(random.uniform(0.35, 8.50), 2)
            classification = _random_classification()
            owner_name = f"{random.choice(TAMIL_FIRST_NAMES)} {random.choice(TAMIL_INITIALS)}"
            owner_email = f"citizen.{code.lower()}{i:03d}@demo.in"

            # Coordinates
            lat = round(random.uniform(dinfo["lat_range"][0], dinfo["lat_range"][1]), 6)
            lon = round(random.uniform(dinfo["lon_range"][0], dinfo["lon_range"][1]), 6)

            # Assign to project or leave unassigned
            proj_id = None
            acq_status = "Proposal"
            if current_proj_idx < len(projects):
                target_p = projects[current_proj_idx]
                if proj_assigned_count[target_p["id"]] < target_p["parcels_to_assign"]:
                    proj_id = target_p["id"]
                    acq_status = target_p["stage"]
                    proj_assigned_count[target_p["id"]] += 1
                else:
                    current_proj_idx += 1
                    if current_proj_idx < len(projects):
                        target_p = projects[current_proj_idx]
                        proj_id = target_p["id"]
                        acq_status = target_p["stage"]
                        proj_assigned_count[target_p["id"]] += 1

            # Varied Risk
            risk_roll = random.random()
            if risk_roll < 0.35:
                risk_category = "LOW"
                risk_score = round(random.uniform(0.08, 0.28), 2)
                delay_prob = round(random.uniform(0.05, 0.20), 2)
            elif risk_roll < 0.65:
                risk_category = "MEDIUM"
                risk_score = round(random.uniform(0.32, 0.58), 2)
                delay_prob = round(random.uniform(0.25, 0.48), 2)
            elif risk_roll < 0.88:
                risk_category = "HIGH"
                risk_score = round(random.uniform(0.62, 0.79), 2)
                delay_prob = round(random.uniform(0.52, 0.72), 2)
            else:
                risk_category = "CRITICAL"
                risk_score = round(random.uniform(0.81, 0.98), 2)
                delay_prob = round(random.uniform(0.75, 0.95), 2)

            comp_pending = 1 if (proj_id and acq_status in ("Award", "Compensation", "Legal Dispute / Resolution")) else 0
            legal_disputes = 1 if (risk_category in ("HIGH", "CRITICAL") and random.random() < 0.30) else 0
            aff_families = random.randint(1, 4) if proj_id else random.randint(1, 2)
            rehab_pending = 1 if (proj_id and acq_status in ("Rehabilitation", "Compensation") and random.random() < 0.5) else 0
            approval_pending = 1 if acq_status == "Approval" else 0
            possession_pending = 1 if acq_status == "Possession" else 0

            c.execute("""
                INSERT OR REPLACE INTO parcels (
                    record_id, survey_no, subdivision, village, taluk, district,
                    area, classification, project_id, latitude, longitude,
                    validation_status, risk_category, risk_probability, risk_score,
                    delay_probability, training_label, created_by, owner_reference,
                    case_reference, area_unit, land_use, acquisition_status,
                    project_type, affected_families, legal_disputes,
                    compensation_pending, approval_pending, documentation_pending,
                    rehabilitation_pending, notification_pending, award_pending,
                    possession_pending, stakeholder_responsiveness, environmental_risk,
                    weather_risk, historical_delay, delay_days, remarks
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?
                )
            """, (
                record_id, survey_no, subdivision, village_name, taluk_name, district_name,
                area, classification, proj_id, lat, lon,
                "VALID", risk_category, risk_score, risk_score,
                delay_prob, "DELAYED" if risk_category in ("HIGH", "CRITICAL") else "ON_TIME",
                "system.seeder@tngov.in", owner_email,
                f"CASE-{code}-{i:04d}", "acres", "Agriculture" if "Land" in classification else classification,
                acq_status, "Infrastructure", aff_families, legal_disputes,
                comp_pending, approval_pending, 0,
                rehab_pending, 1 if acq_status == "Notification" else 0, 1 if acq_status == "Award" else 0,
                possession_pending, round(random.uniform(40, 95), 1), round(random.uniform(10, 60), 1),
                round(random.uniform(10, 50), 1), round(random.uniform(0, 30), 1),
                random.randint(15, 60) if risk_category in ("HIGH", "CRITICAL") else 0,
                f"Synthetic parcel {record_id} in {village_name}, {taluk_name}, {district_name}"
            ))

            parcel_id = c.execute("SELECT id FROM parcels WHERE record_id=?", (record_id,)).fetchone()[0]

            # 2c. Risk prediction entry
            c.execute("""
                INSERT OR REPLACE INTO risk_predictions (
                    parcel_id, project_id, risk_score, risk_category, delay_probability, model_version
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (parcel_id, proj_id, risk_score, risk_category, delay_prob, "v2.0-rf-production"))

            # 2d. Operational compensation record if assigned to project
            if proj_id:
                rate_per_acre = random.choice([1500000, 2200000, 3500000, 4800000, 6000000])
                assessed = round(area * rate_per_acre, 2)
                approved = assessed

                # Varied Compensation Statuses
                if acq_status in ("Proposal", "Notification", "SIA / Survey"):
                    comp_status = "Not Started"
                    paid = 0.0
                elif acq_status in ("Approval", "Award"):
                    comp_status = random.choice(["Processing", "Approved"])
                    paid = 0.0
                elif acq_status == "Compensation":
                    c_choice = random.choice(["Processing", "Approved", "Partially Paid", "Payment Failed", "Disputed"])
                    comp_status = c_choice
                    paid = round(approved * 0.4, 2) if c_choice == "Partially Paid" else 0.0
                elif acq_status in ("Possession", "Rehabilitation", "Closure / Completion"):
                    comp_status = random.choice(["Partially Paid", "Fully Paid", "Fully Paid"])
                    paid = approved if comp_status == "Fully Paid" else round(approved * 0.6, 2)
                else:
                    comp_status = "Processing"
                    paid = 0.0

                pending = max(0.0, round(approved - paid, 2))
                c.execute("""
                    INSERT OR REPLACE INTO compensation (
                        parcel_id, project_id, assessed_amount, approved_amount,
                        paid_amount, pending_amount, status, payment_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    parcel_id, proj_id, assessed, approved, paid, pending, comp_status,
                    "2024-11-20" if paid > 0 else None
                ))

                # 2e. Field assignment / verification for subset
                if i % 3 == 0:
                    verif_status = random.choice(["Pending", "Verified", "Scheduled", "Failed", "Re-verification Required"])
                    c.execute("""
                        INSERT OR REPLACE INTO field_assignments (
                            parcel_id, officer_email, assigned_by, status
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        parcel_id, f"field.{dist_name.lower()}@tngov.in", f"district.{dist_name.lower()}@tngov.in",
                        "Verified" if verif_status == "Verified" else "Pending Verification"
                    ))
                    if verif_status in ("Verified", "Failed"):
                        c.execute("""
                            INSERT OR REPLACE INTO field_verifications (
                                parcel_id, officer_email, gps_lat, gps_lon, status, remarks
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            parcel_id, f"field.{dist_name.lower()}@tngov.in", lat, lon,
                            verif_status, f"On-ground survey verification for {survey_no} in {village_name}"
                        ))

                # 2f. Grievance for subset
                if legal_disputes or (i % 7 == 0):
                    g_type = random.choice([
                        "Compensation Discrepancy", "Survey Boundary Dispute",
                        "Ownership Title Contest", "Tree / Structure Valuation", "R&R Allotment Delay"
                    ])
                    g_status = random.choice(["Open", "Under Review", "Assigned", "Field Investigation", "Resolved", "Escalated"])
                    c.execute("""
                        INSERT OR REPLACE INTO grievances (
                            parcel_id, project_id, submitted_by, type, status, description, resolution
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        parcel_id, proj_id, owner_name, g_type, g_status,
                        f"Grievance filed regarding {g_type.lower()} for Survey No. {survey_no}, {village_name}",
                        "Settlement agreement executed in Lok Adalat" if g_status == "Resolved" else None
                    ))

                # 2g. Alerts for critical / delayed cases
                if risk_category in ("HIGH", "CRITICAL") or acq_status in ("Delayed", "At Risk"):
                    alert_id = f"ALT-{code}-{i:04d}"
                    alert_type = "High Risk Parcel" if risk_category == "CRITICAL" else "Compensation Overdue"
                    severity = "CRITICAL" if risk_category == "CRITICAL" else "HIGH"
                    c.execute("""
                        INSERT OR REPLACE INTO alerts (
                            alert_id, project_id, parcel_id, type, severity, trigger,
                            message, recommended_action, assigned_to, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        alert_id, proj_id, parcel_id, alert_type, severity, "Intelligence Engine",
                        f"Action required on Survey {survey_no} ({village_name}): {alert_type}",
                        "Review title and expedite compensation tranche",
                        f"district.{code.lower()}@tngov.in", "Open"
                    ))

                # 2h. Document records
                if i % 4 == 0:
                    doc_id = f"DOC-{code}-{i:04d}"
                    c.execute("""
                        INSERT OR REPLACE INTO documents (
                            document_id, project_id, parcel_id, document_name, path, format,
                            uploaded_by, verification_status, ocr_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doc_id, proj_id, parcel_id, f"Cadastral_Survey_Sketch_{survey_no.replace('/', '_')}.pdf",
                        f"/uploads/{doc_id}.pdf", ".pdf", f"officer.{code.lower()}@tngov.in",
                        random.choice(["Verified", "Pending"]),
                        random.choice(["Completed", "Verification Required"])
                    ))

        c.commit()
        print(f"  ✓ 500 parcels seeded for {district_name}")

    # Summary
    print("\n=== FINAL PARCEL COUNTS BY DISTRICT ===")
    counts = c.execute("SELECT district, COUNT(*) cnt, SUM(CASE WHEN project_id IS NULL OR project_id='' THEN 1 ELSE 0 END) unassigned FROM parcels GROUP BY district").fetchall()
    for row in counts:
        print(f"  {row['district']}: {row['cnt']} total parcels ({row['unassigned']} unassigned)")

    print("\n=== FINAL PROJECT COUNTS BY DISTRICT ===")
    pcounts = c.execute("SELECT district, COUNT(*) cnt FROM projects GROUP BY district").fetchall()
    for row in pcounts:
        print(f"  {row['district']}: {row['cnt']} projects")

    c.close()
    print("\n✅ Multi-district synthetic seeding complete!")


if __name__ == "__main__":
    seed_districts()
