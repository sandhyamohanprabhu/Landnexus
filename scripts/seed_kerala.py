"""
Seed Kerala Synthetic Data for Multi-State LANDNEXUS Prototype
==============================================================
Creates realistic projects, parcels, milestones, compensation, and R&R records
for Kerala State Authority (Districts: Palakkad, Ernakulam, Thrissur, Thiruvananthapuram).
Does NOT touch Tamil Nadu or Coimbatore records.
"""

import sqlite3
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "survi.db"

random.seed(101)

KERALA_DISTRICTS = {
    "Palakkad": {
        "taluks": [("Palakkad", ["Marutharode", "Pirayiri", "Kodumba", "Kannadi"]),
                   ("Ottapalam", ["Ottapalam", "Ambalapara", "Vaniyamkulam"]),
                   ("Alathur", ["Alathur", "Kavassery", "Tarur"])],
        "center": (10.7867, 76.6548),
        "projects": [
            ("PRJ-KER-PLK-01", "Palakkad Mega Food & Industrial Corridor", "Industrial", "Palakkad", "Marutharode", 45.2, 12, 18, "Compensation"),
            ("PRJ-KER-PLK-02", "Bharathapuzha River Basin Irrigation & Check Dam", "Irrigation", "Alathur", "Kavassery", 28.5, 8, 10, "Award"),
        ]
    },
    "Ernakulam": {
        "taluks": [("Kanayannur", ["Edappally", "Kakkanad", "Poonithura", "Ernakulam"]),
                   ("Aluva", ["Aluva", "Angamaly", "Chengamanad"]),
                   ("Kunnathunad", ["Perumbavoor", "Vengola", "Aikaranad"])],
        "center": (9.9816, 76.2999),
        "projects": [
            ("PRJ-KER-EKM-01", "Kochi Metro Phase-II Kakkanad Extension Corridor", "Metro / Transit", "Kanayannur", "Kakkanad", 62.0, 16, 24, "Rehabilitation"),
            ("PRJ-KER-EKM-02", "Smart Coastal Port Link Express Road", "Road", "Kanayannur", "Edappally", 35.8, 10, 15, "Compensation"),
        ]
    },
    "Thrissur": {
        "taluks": [("Thrissur", ["Ayyanthole", "Ollur", "Vilvattom", "Nadathara"]),
                   ("Mukundapuram", ["Irinjalakuda", "Nenmanikkara", "Porathissery"])],
        "center": (10.5276, 76.2144),
        "projects": [
            ("PRJ-KER-TSR-01", "Thrissur Smart Agro-Logistics Park & Rail Siding", "Rail", "Thrissur", "Nadathara", 50.4, 14, 20, "Survey"),
            ("PRJ-KER-TSR-02", "Kole Wetland Eco-Restoration & Drainage Canal", "Environmental", "Mukundapuram", "Irinjalakuda", 22.0, 6, 8, "Proposal"),
        ]
    },
    "Thiruvananthapuram": {
        "taluks": [("Thiruvananthapuram", ["Pattom", "Sasthamangalam", "Kowdiar", "Ulloor"]),
                   ("Neyyattinkara", ["Neyyattinkara", "Parassala", "Balaramapuram"])],
        "center": (8.5241, 76.9366),
        "projects": [
            ("PRJ-KER-TVM-01", "Vizhinjam Port Connectivity Outer Ring Road", "Highway", "Neyyattinkara", "Balaramapuram", 88.0, 25, 35, "Award"),
            ("PRJ-KER-TVM-02", "Technopark Phase-IV Aerospace Corridor", "Tech Park", "Thiruvananthapuram", "Ulloor", 40.0, 11, 14, "Compensation"),
        ]
    }
}

def seed_kerala():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT count(*) FROM projects WHERE district IN ('Palakkad','Ernakulam','Thrissur','Thiruvananthapuram')")
    if cur.fetchone()[0] > 0:
        print("Kerala projects already seeded. Skipping.")
        conn.close()
        return

    print("Seeding Kerala synthetic data...")

    # Insert projects
    for dist, dinfo in KERALA_DISTRICTS.items():
        for pid, pname, ptype, taluk, village, land_req, aff_par, aff_fam, stage in dinfo["projects"]:
            cur.execute("""
                INSERT OR IGNORE INTO projects (
                    project_id, project_name, project_type, district, taluk, village,
                    total_land_required, affected_parcels, affected_families,
                    project_start_date, planned_completion_date, current_stage,
                    project_status, progress, priority, department
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '2024-01-15', '2027-12-31', ?, 'Active', ?, 'High', 'Kerala KRFB / KSIDC')
            """, (pid, pname, ptype, dist, taluk, village, land_req, aff_par, aff_fam, stage, random.randint(35, 75)))

            # Seed project milestones
            milestones = ["Proposal", "SIA / Survey", "Notification", "Legal Dispute / Resolution", "Approval", "Award", "Compensation", "Possession", "Rehabilitation", "Closure / Completion"]
            for m in milestones:
                cur.execute("""
                    INSERT OR IGNORE INTO project_milestones (project_id, stage, status, planned_date, delay_days)
                    VALUES (?, ?, ?, '2024-06-01', ?)
                """, (pid, m, "Completed" if m in ("Proposal", "SIA / Survey") else "In Progress", random.choice([0, 5, 12, 25])))

    # Insert parcels for Kerala projects (approx 40 parcels per district)
    p_counter = 0

    for dist, dinfo in KERALA_DISTRICTS.items():
        clat, clon = dinfo["center"]
        for pidx, (pid, pname, ptype, taluk, village, land_req, aff_par, aff_fam, stage) in enumerate(dinfo["projects"]):
            for i in range(aff_par):
                p_counter += 1
                rec_id = f"KL-{dist[:3].upper()}-{p_counter:04d}"
                surv_no = f"{random.randint(10, 450)}/{random.randint(1, 9)}{chr(65 + random.randint(0, 3))}"
                area = round(random.uniform(0.2, 2.5), 2)
                lat = round(clat + random.uniform(-0.08, 0.08), 6)
                lon = round(clon + random.uniform(-0.08, 0.08), 6)
                owner_ref = f"citizen.ker_{dist[:3].lower()}_{p_counter}@demo.in"

                cur.execute("""
                    INSERT INTO parcels (
                        record_id, survey_no, subdivision, village, taluk, district,
                        area, classification, project_id, latitude, longitude,
                        validation_status, risk_category, risk_probability, risk_score,
                        delay_probability, training_label, owner_reference, acquisition_status
                    ) VALUES (?, ?, '1', ?, ?, ?, ?, 'Dry', ?, ?, ?, 'VALID', ?, ?, ?, ?, 'LOW', ?, ?)
                """, (rec_id, surv_no, village, taluk, dist, area, pid, lat, lon,
                      random.choice(["LOW", "MEDIUM", "HIGH"]), random.uniform(0.1, 0.7),
                      random.randint(20, 75), random.uniform(0.1, 0.5), owner_ref, stage))
                
                parcel_db_id = cur.lastrowid

                # Seed compensation
                assessed = round(area * random.uniform(1500000, 3500000), 2)
                paid = assessed if stage in ("Possession", "Rehabilitation", "Closure / Completion") else round(assessed * 0.5, 2) if stage == "Compensation" else 0
                cur.execute("""
                    INSERT INTO compensation (
                        project_id, parcel_id, assessed_amount, approved_amount, paid_amount, pending_amount, status, payment_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (pid, parcel_db_id, assessed, assessed, paid, assessed - paid,
                      "Paid" if paid == assessed else "In Progress" if paid > 0 else "Pending",
                      "2025-08-15" if paid > 0 else None))

                # Seed RR family for about half the parcels
                if i < aff_fam:
                    fam_id = f"FAM-KER-{dist[:3].upper()}-{p_counter:04d}"
                    fam_head = f"Shri {random.choice(['Radhakrishnan', 'Suresh Kumar', 'Mohandas', 'Thomas Philip', 'Abdul Rahman', 'Narayanan Nair'])}"
                    cur.execute("""
                        INSERT INTO rr_families (
                            family_id, parcel_id, project_id, district, taluk, village, survey_no,
                            family_head, members, impact_type, displacement_status,
                            rr_stage, exceptional_state, compensation_status, housing_status,
                            livelihood_status, verification_status, grievance_status,
                            readiness_percentage, readiness_band, risk_level, compensation_entitled,
                            compensation_paid, pending_action
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Titleholder Land Lost', 'Physically Displaced',
                                  ?, 'In Progress', 'Approved', 'Site Identified', 'Eligible', 'Verified',
                                  'No Grievance', ?, 'On Track', 'Low', ?, ?, 'Complete allotment formalities')
                    """, (fam_id, parcel_db_id, pid, dist, taluk, village, surv_no,
                          fam_head, random.randint(3, 6),
                          "Compensation" if stage == "Compensation" else "Housing" if stage == "Award" else "Completed",
                          random.randint(60, 95), assessed, paid))

    conn.commit()
    conn.close()
    print("Kerala synthetic data seeded successfully.")

if __name__ == "__main__":
    seed_kerala()
