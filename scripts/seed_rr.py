"""
LANDNEXUS R&R Synthetic Data Seed Script
=========================================
Generates comprehensive, realistic Rehabilitation & Resettlement (R&R) demo data
across 5 Tamil Nadu districts for the SIH hackathon prototype.

Run: python scripts/seed_rr.py

Fully deterministic - uses INSERT OR IGNORE / fixed family IDs.
Safe to re-run: will not create duplicate records.
Does NOT modify any existing compensation, parcel, or project records.
"""

import sqlite3
import random
import json
import sys
import os
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "survi.db"

random.seed(42)  # deterministic

# ── Helper names ─────────────────────────────────────────────────────────────
TAMIL_NAMES = [
    "Murugan K", "Selvi R", "Kannan M", "Lakshmi D", "Rajan S",
    "Sumathi P", "Arumugam V", "Meenakshi T", "Senthil A", "Kavitha N",
    "Palani G", "Anandhi B", "Krishnan L", "Vijayalakshmi C", "Subramanian P",
    "Geetha M", "Muthusamy R", "Saraswathi A", "Perumal K", "Thenmozhi S",
    "Balamurugan T", "Kamakshi D", "Sundaram N", "Ponni V", "Ramesh B",
    "Chithra J", "Velmurugan E", "Mangai S", "Annamalai T", "Saroja K",
    "Govindasamy P", "Rajeswari M", "Shanmugam A", "Malathi R", "Ezhilan S",
    "Parvathi N", "Chellaswamy D", "Devi L", "Natarajan B", "Usha M",
    "Jayakumar V", "Revathi C", "Arjunan P", "Kokilam T", "Sivasubramanian N",
    "Alamelu R", "Bhaskar K", "Nalini A", "Duraisamy G", "Vasanthi P",
    "Manikandan S", "Radhika L", "Velu T", "Pushpavalli N", "Saminathan K",
    "Hemalatha R", "Chinnasamy B", "Sasikala M", "Periasamy V", "Jamuna D",
    "Gunasekaran A", "Meena S", "Suresh P", "Anjalai K", "Rajamani T",
    "Karpagam B", "Muthaiah N", "Gowri S", "Palanisamy L", "Yamuna R",
    "Ramasamy G", "Kamalam P", "Elango M", "Malar V", "Thiyagarajan K",
    "Poomani S", "Lakshmanan D", "Ambika R", "Somasundaram T", "Nirmala A",
    "Venkatesan P", "Kumari B", "Murugesan C", "Saranya L", "Arunkumar S",
    "Azhagammai K", "Sundaresan N", "Vidhya T", "Raghunathan M", "Ponmalar R",
    "Thandapani V", "Suganya A", "Kanagaraj P", "Meenakshi S", "Ponnusamy T",
    "Ambujam L", "Velusamy B", "Dhanalakshmi R", "Chellaiah K", "Prabha N",
    "Marimuthu G", "Vasantha S", "Sivalingam T", "Kaveri P", "Balakrishnan M",
    "Thilagam R", "Nagarajan K", "Indira S", "Rasu V", "Chandra M",
    "Kanagavel P", "Girija T", "Thangavel N", "Kamakodi A", "Periyannan B",
    "Andal S", "Mohan K", "Savithri R", "Gurusamy D", "Parameshwari M",
    "Senthilkumar V", "Rani P", "Karuppaiah L", "Vanitha T", "Ilangovan N",
    "Selvarani B", "Krishnamurthy G", "Bhavani A", "Ganapathi K", "Tulasi S",
    "Narayanan M", "Amirtham P", "Sivagnanam T", "Renuka D", "Kadiravan V",
    "Komalam N", "Subramani R", "Kousalya B", "Kupusamy K", "Palaniammal S",
]

# ── District / Taluk / Village Data ─────────────────────────────────────────
DISTRICT_DATA = {
    "Coimbatore": {
        "taluks": {
            "Sulur": ["Sulur", "Irugur", "Thondamuthur", "Kuniyamuthur"],
            "Annur": ["Annur", "Anamalai", "Palladam", "Tiruppur North"],
            "Perur": ["Perur", "Thondamuthur", "Mettupalayam"],
            "Madukkarai": ["Madukkarai", "Coimbatore South", "Pollachi"],
            "Kinathukadavu": ["Kinathukadavu", "Pollachi", "Anamalai"],
            "Karamadai": ["Karamadai", "Mettupalayam", "Annur"],
        },
        "target_families": 128,
        "avg_readiness": 84,
        "readiness_std": 15,
        "profile": "mostly_on_track",
    },
    "Tiruppur": {
        "taluks": {
            "Tiruppur": ["Tiruppur", "Kangeyam", "Avinashi"],
            "Palladam": ["Palladam", "Uthukuli", "Tiruppur"],
            "Dharapuram": ["Dharapuram", "Udumalpet", "Kangeyam"],
            "Udumalpet": ["Udumalpet", "Mulanur", "Dharapuram"],
            "Kangeyam": ["Kangeyam", "Tiruppur", "Avinashi"],
            "Avinashi": ["Avinashi", "Tiruppur", "Palladam"],
        },
        "target_families": 96,
        "avg_readiness": 79,
        "readiness_std": 18,
        "profile": "on_track_attention",
    },
    "Erode": {
        "taluks": {
            "Erode": ["Erode", "Bhavani", "Perundurai"],
            "Bhavani": ["Bhavani", "Gobichettipalayam", "Sathyamangalam"],
            "Gobichettipalayam": ["Gobichettipalayam", "Sathyamangalam", "Bhavani"],
            "Perundurai": ["Perundurai", "Erode", "Nambiyur"],
            "Sathyamangalam": ["Sathyamangalam", "Gobichettipalayam", "Anthiyur"],
            "Anthiyur": ["Anthiyur", "Sathyamangalam", "Gobichettipalayam"],
        },
        "target_families": 114,
        "avg_readiness": 68,
        "readiness_std": 20,
        "profile": "attention_delayed",
    },
    "Salem": {
        "taluks": {
            "Salem": ["Salem", "Yercaud", "Attur"],
            "Attur": ["Attur", "Gangavalli", "Thalaivasal"],
            "Omalur": ["Omalur", "Edapadi", "Mettur"],
            "Mettur": ["Mettur", "Omalur", "Salem"],
            "Edapadi": ["Edapadi", "Omalur", "Attur"],
            "Vazhapadi": ["Vazhapadi", "Sankari", "Attur"],
        },
        "target_families": 143,
        "avg_readiness": 61,
        "readiness_std": 22,
        "profile": "delayed_at_risk",
    },
    "Namakkal": {
        "taluks": {
            "Namakkal": ["Namakkal", "Rasipuram", "Tiruchengode"],
            "Rasipuram": ["Rasipuram", "Namakkal", "Kolli Hills"],
            "Tiruchengode": ["Tiruchengode", "Namakkal", "Erode"],
            "Kolli Hills": ["Kolli Hills", "Rasipuram", "Namakkal"],
            "Paramathi Velur": ["Paramathi", "Velur", "Namakkal"],
            "Senthamangalam": ["Senthamangalam", "Kolli Hills", "Namakkal"],
        },
        "target_families": 87,
        "avg_readiness": 48,
        "readiness_std": 22,
        "profile": "critical_blocked",
    },
}

# ── Component Status Options ─────────────────────────────────────────────────
COMP_STATUSES = [
    "Not Started", "Processing", "Approved",
    "Partially Paid", "Fully Paid", "Payment Failed", "Disputed"
]
HOUSING_STATUSES = [
    "Not Required", "Pending", "Approved", "Site Identified",
    "Construction in Progress", "Ready", "Handed Over", "Verification Failed"
]
LIVELIHOOD_STATUSES = [
    "Not Assessed", "Assessment Pending", "Eligible", "Plan Prepared",
    "Sanctioned", "Training Pending", "Support Delivered", "Monitoring", "Completed"
]
VERIF_STATUSES = [
    "Not Started", "Scheduled", "Pending", "Verified", "Failed", "Re-verification Required"
]
GRIEVANCE_STATUSES = [
    "No Grievance", "Open", "Under Review", "Assigned",
    "Field Investigation", "Resolved", "Reopened", "Escalated"
]
RR_STAGES = [
    "Affected Family Identified",
    "Impact Assessment",
    "R&R Eligibility Assessment",
    "Entitlement Determined",
    "R&R Plan Prepared",
    "Approval Pending",
    "Approved",
    "Benefit Sanctioned",
    "Housing / Livelihood / Other Benefits Arranged",
    "Field Verification",
    "Benefit Delivered",
    "Rehabilitation Completed",
]
EXCEPTIONAL_STATES = [
    "Pending", "Partially Completed", "Blocked", "On Hold",
    "Disputed", "Grievance Raised", "Verification Failed",
    "Re-verification Required", "At Risk", "Completed"
]
IMPACT_TYPES = [
    "Full Displacement", "Partial Displacement", "Livelihood Loss",
    "Homestead Loss", "Agricultural Land Loss", "Commercial Loss",
    "Combined Impact"
]
RISK_LEVELS = ["Low", "Medium", "High", "Critical"]

# ── Readiness Score Calculation ──────────────────────────────────────────────
COMP_SCORES = {
    "Not Started": 0, "Processing": 15, "Approved": 25,
    "Partially Paid": 60, "Fully Paid": 100, "Payment Failed": 5, "Disputed": 15
}
HOUSING_SCORES = {
    "Not Required": 100, "Pending": 5, "Approved": 20, "Site Identified": 35,
    "Construction in Progress": 60, "Ready": 85, "Handed Over": 100, "Verification Failed": 20
}
LIVELIHOOD_SCORES = {
    "Not Assessed": 0, "Assessment Pending": 10, "Eligible": 25, "Plan Prepared": 40,
    "Sanctioned": 55, "Training Pending": 65, "Support Delivered": 85,
    "Monitoring": 90, "Completed": 100
}
VERIF_SCORES = {
    "Not Started": 0, "Scheduled": 20, "Pending": 35,
    "Verified": 100, "Failed": 0, "Re-verification Required": 15
}
GRIEVANCE_SCORES = {
    "No Grievance": 100, "Open": 20, "Under Review": 35, "Assigned": 45,
    "Field Investigation": 55, "Resolved": 100, "Reopened": 10, "Escalated": 0
}

WEIGHTS = {"comp": 0.30, "housing": 0.25, "livelihood": 0.20, "verif": 0.15, "grievance": 0.10}


def calc_readiness(comp, housing, livelihood, verif, grievance):
    score = (
        COMP_SCORES.get(comp, 0) * WEIGHTS["comp"] +
        HOUSING_SCORES.get(housing, 0) * WEIGHTS["housing"] +
        LIVELIHOOD_SCORES.get(livelihood, 0) * WEIGHTS["livelihood"] +
        VERIF_SCORES.get(verif, 0) * WEIGHTS["verif"] +
        GRIEVANCE_SCORES.get(grievance, 0) * WEIGHTS["grievance"]
    )
    return round(score, 1)


def readiness_band(pct):
    if pct >= 90:
        return "Completed"
    elif pct >= 75:
        return "On Track"
    elif pct >= 50:
        return "Attention Required"
    elif pct >= 25:
        return "Delayed"
    else:
        return "Critical"


def infer_rr_stage(comp, housing, livelihood, verif, grievance, readiness):
    """Infer the R&R workflow stage from component statuses."""
    if comp == "Fully Paid" and housing in ("Handed Over", "Not Required") and livelihood in ("Completed", "Monitoring", "Support Delivered") and verif == "Verified":
        return "Rehabilitation Completed"
    if comp in ("Fully Paid", "Partially Paid") and verif == "Verified":
        return "Benefit Delivered"
    if housing in ("Construction in Progress", "Ready") or livelihood in ("Training Pending", "Support Delivered"):
        return "Housing / Livelihood / Other Benefits Arranged"
    if comp in ("Approved", "Partially Paid") and livelihood in ("Sanctioned", "Plan Prepared"):
        return "Benefit Sanctioned"
    if comp == "Approved" and livelihood in ("Eligible", "Plan Prepared"):
        return "Approved"
    if comp in ("Processing", "Not Started") and livelihood in ("Assessment Pending", "Eligible"):
        return "Approval Pending"
    if livelihood in ("Not Assessed", "Assessment Pending") and comp == "Not Started":
        return "R&R Eligibility Assessment"
    if readiness < 20:
        return "Affected Family Identified"
    if readiness < 40:
        return "Impact Assessment"
    return "Entitlement Determined"


def infer_exceptional_state(comp, housing, livelihood, verif, grievance, readiness):
    if comp == "Fully Paid" and housing in ("Handed Over", "Not Required") and verif == "Verified" and grievance in ("No Grievance", "Resolved"):
        return "Completed"
    if grievance == "Escalated":
        return "Blocked"
    if grievance in ("Open", "Reopened") and readiness < 60:
        return "Grievance Raised"
    if verif == "Failed":
        return "Verification Failed"
    if verif == "Re-verification Required":
        return "Re-verification Required"
    if comp == "Disputed" or housing == "Verification Failed":
        return "Disputed"
    if readiness < 25:
        return "At Risk"
    if readiness < 50:
        return "Delayed"
    if readiness >= 90 and grievance not in ("Open", "Escalated", "Reopened"):
        return "Completed"
    if housing == "Construction in Progress" or livelihood == "Training Pending":
        return "Partially Completed"
    return "Pending"


def infer_pending_action(comp, housing, livelihood, verif, grievance, rr_stage, exceptional):
    """Generate a meaningful, specific pending action."""
    if exceptional == "Completed":
        return "No action required — rehabilitation completed"
    if exceptional == "Escalated" or grievance == "Escalated":
        return "Escalate grievance to State R&R Commissioner"
    if grievance in ("Open", "Reopened"):
        return "Resolve open grievance before proceeding with benefit delivery"
    if verif == "Failed":
        return "Conduct re-verification after addressing discrepancies"
    if verif == "Re-verification Required":
        return "Schedule and complete field re-verification"
    if verif == "Not Started":
        return "Complete family verification before entitlement determination"
    if comp == "Not Started":
        return "Initiate compensation assessment and documentation"
    if comp == "Processing":
        return "Approve R&R compensation entitlement"
    if comp == "Disputed":
        return "Resolve disputed compensation entitlement through mediation"
    if comp == "Payment Failed":
        return "Retry compensation payment — check bank details"
    if comp == "Partially Paid":
        return "Release pending balance of compensation payment"
    if housing == "Pending":
        return "Identify and approve alternative housing site"
    if housing == "Approved":
        return "Commence housing construction / initiate allocation"
    if housing == "Site Identified":
        return "Issue housing construction work order"
    if housing == "Construction in Progress":
        return "Monitor construction progress and target completion"
    if housing == "Ready":
        return "Complete housing handover with field verification"
    if housing == "Verification Failed":
        return "Resolve housing quality issues flagged in verification"
    if livelihood == "Not Assessed":
        return "Complete livelihood impact assessment"
    if livelihood == "Assessment Pending":
        return "Finalise livelihood assessment and determine eligibility"
    if livelihood == "Eligible":
        return "Prepare and approve livelihood support plan"
    if livelihood == "Plan Prepared":
        return "Sanction livelihood support plan and release funds"
    if livelihood == "Sanctioned":
        return "Arrange livelihood training / skill development programme"
    if livelihood == "Training Pending":
        return "Confirm training schedule and enroll family members"
    if livelihood == "Support Delivered":
        return "Begin monitoring livelihood support outcomes"
    if livelihood == "Monitoring":
        return "Complete monitoring cycle and close livelihood support"
    if rr_stage == "Approval Pending":
        return "Obtain District Collector approval for R&R plan"
    if rr_stage == "R&R Plan Prepared":
        return "Submit R&R plan for district authority review"
    if comp == "Approved":
        return "Disburse approved compensation amount"
    if comp == "Fully Paid" and housing == "Handed Over":
        return "Complete field verification and close rehabilitation case"
    return "Review R&R status and initiate next workflow step"


def infer_risk_level(readiness, grievance, verif, comp, exceptional):
    if grievance == "Escalated" or exceptional in ("Blocked", "At Risk"):
        return "Critical"
    if readiness < 30 or grievance in ("Open", "Reopened") or verif == "Failed":
        return "High"
    if readiness < 60 or comp in ("Payment Failed", "Disputed"):
        return "Medium"
    return "Low"


# ── Profile-based status generators ─────────────────────────────────────────
def gen_components_for_profile(profile, target_readiness):
    """Generate internally consistent component statuses matching a target readiness."""
    
    # Define component combinations for different readiness bands
    r = target_readiness
    
    if r >= 90:  # Completed / On Track high
        comp = random.choice(["Fully Paid", "Fully Paid", "Fully Paid", "Approved"])
        housing = random.choice(["Handed Over", "Handed Over", "Not Required", "Ready"])
        livelihood = random.choice(["Completed", "Monitoring", "Support Delivered", "Monitoring"])
        verif = "Verified"
        grievance = random.choice(["No Grievance", "No Grievance", "Resolved"])
        
    elif r >= 75:  # On Track
        comp = random.choice(["Fully Paid", "Approved", "Partially Paid", "Fully Paid"])
        housing = random.choice(["Handed Over", "Ready", "Construction in Progress", "Not Required"])
        livelihood = random.choice(["Support Delivered", "Training Pending", "Monitoring", "Plan Prepared"])
        verif = random.choice(["Verified", "Verified", "Pending"])
        grievance = random.choice(["No Grievance", "No Grievance", "Resolved", "Under Review"])
        
    elif r >= 50:  # Attention Required
        comp = random.choice(["Approved", "Processing", "Partially Paid", "Not Started"])
        housing = random.choice(["Site Identified", "Approved", "Construction in Progress", "Pending"])
        livelihood = random.choice(["Eligible", "Plan Prepared", "Sanctioned", "Assessment Pending"])
        verif = random.choice(["Pending", "Verified", "Scheduled", "Not Started"])
        grievance = random.choice(["No Grievance", "Open", "Under Review", "Assigned"])
        
    elif r >= 25:  # Delayed
        comp = random.choice(["Not Started", "Processing", "Disputed", "Payment Failed"])
        housing = random.choice(["Pending", "Approved", "Verification Failed", "Pending"])
        livelihood = random.choice(["Not Assessed", "Assessment Pending", "Eligible"])
        verif = random.choice(["Not Started", "Scheduled", "Failed", "Re-verification Required"])
        grievance = random.choice(["Open", "Reopened", "Under Review", "Assigned"])
        
    else:  # Critical
        comp = random.choice(["Not Started", "Disputed", "Payment Failed", "Not Started"])
        housing = random.choice(["Pending", "Pending", "Verification Failed"])
        livelihood = random.choice(["Not Assessed", "Assessment Pending"])
        verif = random.choice(["Not Started", "Failed", "Re-verification Required"])
        grievance = random.choice(["Open", "Escalated", "Reopened", "Open"])

    return comp, housing, livelihood, verif, grievance


# ── Mandatory Edge Case Templates ────────────────────────────────────────────
EDGE_CASES = [
    # 1. Fully completed R&R family
    {"tag": "CASE_01_COMPLETED", "comp": "Fully Paid", "housing": "Handed Over",
     "livelihood": "Completed", "verif": "Verified", "grievance": "No Grievance"},
    # 2. Compensation paid but R&R incomplete
    {"tag": "CASE_02_COMP_PAID_RR_INCOMPLETE", "comp": "Fully Paid", "housing": "Construction in Progress",
     "livelihood": "Training Pending", "verif": "Verified", "grievance": "No Grievance"},
    # 3. Housing ready but livelihood pending
    {"tag": "CASE_03_HOUSING_READY_LIVELIHOOD_PENDING", "comp": "Approved", "housing": "Ready",
     "livelihood": "Plan Prepared", "verif": "Verified", "grievance": "No Grievance"},
    # 4. Livelihood delivered but monitoring pending
    {"tag": "CASE_04_LIVELIHOOD_DELIVERED_MONITORING_PENDING", "comp": "Fully Paid", "housing": "Handed Over",
     "livelihood": "Support Delivered", "verif": "Verified", "grievance": "No Grievance"},
    # 5. Family verification failed
    {"tag": "CASE_05_VERIF_FAILED", "comp": "Processing", "housing": "Pending",
     "livelihood": "Assessment Pending", "verif": "Failed", "grievance": "No Grievance"},
    # 6. Re-verification required
    {"tag": "CASE_06_RE_VERIF_REQUIRED", "comp": "Processing", "housing": "Pending",
     "livelihood": "Assessment Pending", "verif": "Re-verification Required", "grievance": "No Grievance"},
    # 7. Open grievance blocking completion
    {"tag": "CASE_07_GRIEVANCE_BLOCKING", "comp": "Fully Paid", "housing": "Ready",
     "livelihood": "Monitoring", "verif": "Verified", "grievance": "Open"},
    # 8. Escalated grievance
    {"tag": "CASE_08_ESCALATED_GRIEVANCE", "comp": "Disputed", "housing": "Pending",
     "livelihood": "Not Assessed", "verif": "Not Started", "grievance": "Escalated"},
    # 9. Partial compensation
    {"tag": "CASE_09_PARTIAL_COMP", "comp": "Partially Paid", "housing": "Site Identified",
     "livelihood": "Plan Prepared", "verif": "Verified", "grievance": "No Grievance"},
    # 10. Payment failure
    {"tag": "CASE_10_PAYMENT_FAILED", "comp": "Payment Failed", "housing": "Approved",
     "livelihood": "Eligible", "verif": "Verified", "grievance": "Open"},
    # 11. R&R approval pending
    {"tag": "CASE_11_APPROVAL_PENDING", "comp": "Not Started", "housing": "Pending",
     "livelihood": "Eligible", "verif": "Pending", "grievance": "No Grievance"},
    # 12. Benefit sanctioned but not delivered
    {"tag": "CASE_12_SANCTIONED_NOT_DELIVERED", "comp": "Approved", "housing": "Approved",
     "livelihood": "Sanctioned", "verif": "Verified", "grievance": "No Grievance"},
    # 13. Housing construction in progress
    {"tag": "CASE_13_CONSTRUCTION_IN_PROGRESS", "comp": "Approved", "housing": "Construction in Progress",
     "livelihood": "Training Pending", "verif": "Verified", "grievance": "No Grievance"},
    # 14. Vulnerable/at-risk family
    {"tag": "CASE_14_VULNERABLE_AT_RISK", "comp": "Not Started", "housing": "Pending",
     "livelihood": "Not Assessed", "verif": "Not Started", "grievance": "Escalated"},
    # 15. Multiple pending benefits
    {"tag": "CASE_15_MULTIPLE_PENDING", "comp": "Processing", "housing": "Pending",
     "livelihood": "Assessment Pending", "verif": "Scheduled", "grievance": "Under Review"},
    # 16. Disputed entitlement
    {"tag": "CASE_16_DISPUTED_ENTITLEMENT", "comp": "Disputed", "housing": "Pending",
     "livelihood": "Assessment Pending", "verif": "Pending", "grievance": "Field Investigation"},
    # 17. Rehabilitation on hold
    {"tag": "CASE_17_ON_HOLD", "comp": "Approved", "housing": "Site Identified",
     "livelihood": "Plan Prepared", "verif": "Verified", "grievance": "Under Review"},
    # 18. Field verification pending
    {"tag": "CASE_18_FIELD_VERIF_PENDING", "comp": "Approved", "housing": "Ready",
     "livelihood": "Support Delivered", "verif": "Pending", "grievance": "No Grievance"},
    # 19. Field verification completed but District approval pending
    {"tag": "CASE_19_DISTRICT_APPROVAL_PENDING", "comp": "Approved", "housing": "Ready",
     "livelihood": "Support Delivered", "verif": "Verified", "grievance": "No Grievance"},
    # 20. Rehabilitation completed
    {"tag": "CASE_20_REHAB_COMPLETED", "comp": "Fully Paid", "housing": "Not Required",
     "livelihood": "Completed", "verif": "Verified", "grievance": "Resolved"},
]


def make_family_id(district, seq):
    dist_code = district[:3].upper()
    return f"RNR-{dist_code}-{seq:04d}"


def pick_name(used_names, seq):
    return TAMIL_NAMES[seq % len(TAMIL_NAMES)]


# ── Database Schema Migration ────────────────────────────────────────────────
MIGRATE_SQL = """
-- Add new columns to r_and_r if they don't exist
-- We will create a new table rr_families and leave r_and_r intact

CREATE TABLE IF NOT EXISTS rr_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id TEXT UNIQUE NOT NULL,
    parcel_id INTEGER REFERENCES parcels(id),
    project_id TEXT REFERENCES projects(project_id),
    district TEXT NOT NULL,
    taluk TEXT NOT NULL,
    village TEXT NOT NULL,
    survey_no TEXT,
    family_head TEXT NOT NULL,
    members INTEGER DEFAULT 4,
    impact_type TEXT,
    displacement_status TEXT DEFAULT 'Displaced',
    is_vulnerable INTEGER DEFAULT 0,
    
    -- R&R Workflow Stage
    rr_stage TEXT NOT NULL DEFAULT 'Affected Family Identified',
    exceptional_state TEXT,
    
    -- Component Statuses
    compensation_status TEXT DEFAULT 'Not Started',
    housing_status TEXT DEFAULT 'Pending',
    livelihood_status TEXT DEFAULT 'Not Assessed',
    verification_status TEXT DEFAULT 'Not Started',
    grievance_status TEXT DEFAULT 'No Grievance',
    
    -- Computed Metrics
    readiness_percentage REAL DEFAULT 0,
    readiness_band TEXT DEFAULT 'Critical',
    risk_level TEXT DEFAULT 'High',
    
    -- Compensation Details
    compensation_entitled REAL DEFAULT 0,
    compensation_paid REAL DEFAULT 0,
    
    -- Narrative
    pending_action TEXT,
    remarks TEXT,
    
    -- Timestamps
    identified_date TEXT,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Edge case tag (for demo traceability)
    edge_case_tag TEXT
);

CREATE INDEX IF NOT EXISTS idx_rrf_district ON rr_families(district);
CREATE INDEX IF NOT EXISTS idx_rrf_project ON rr_families(project_id);
CREATE INDEX IF NOT EXISTS idx_rrf_rr_stage ON rr_families(rr_stage);
CREATE INDEX IF NOT EXISTS idx_rrf_readiness ON rr_families(readiness_percentage);
CREATE INDEX IF NOT EXISTS idx_rrf_risk ON rr_families(risk_level);

CREATE TABLE IF NOT EXISTS rr_grievances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id TEXT NOT NULL REFERENCES rr_families(family_id),
    project_id TEXT,
    district TEXT,
    grievance_type TEXT,
    description TEXT,
    status TEXT DEFAULT 'Open',
    assigned_to TEXT,
    resolution TEXT,
    raised_date TEXT,
    resolved_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rrg_family ON rr_grievances(family_id);
CREATE INDEX IF NOT EXISTS idx_rrg_district ON rr_grievances(district);
CREATE INDEX IF NOT EXISTS idx_rrg_status ON rr_grievances(status);

CREATE TABLE IF NOT EXISTS rr_field_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id TEXT NOT NULL REFERENCES rr_families(family_id),
    district TEXT,
    officer_email TEXT,
    verification_type TEXT DEFAULT 'Family Verification',
    status TEXT DEFAULT 'Pending',
    remarks TEXT,
    evidence_notes TEXT,
    assigned_date TEXT,
    completed_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rrf_verify_family ON rr_field_verifications(family_id);
"""

# ── Synthetic Project/Parcel Data for Missing Districts ──────────────────────
DISTRICT_PROJECTS = {
    "Tiruppur": [
        ("PRJ-RNR-TPR-001", "Tiruppur Ring Road Expansion Project", "Road", "Tiruppur", 180),
        ("PRJ-RNR-TPR-002", "Tiruppur Industrial Water Supply Project", "Irrigation", "Palladam", 120),
        ("PRJ-RNR-TPR-003", "Tiruppur Smart City Urban Renewal", "Urban Development", "Tiruppur", 95),
        ("PRJ-RNR-TPR-004", "Dharapuram Bypass Road Project", "Road", "Dharapuram", 140),
        ("PRJ-RNR-TPR-005", "Kangeyam Rural Housing Scheme", "Housing", "Kangeyam", 85),
    ],
    "Erode": [
        ("PRJ-RNR-ERD-001", "Erode Cauvery Canal Rehabilitation Project", "Irrigation", "Erode", 210),
        ("PRJ-RNR-ERD-002", "Gobichettipalayam Road Widening Project", "Road", "Gobichettipalayam", 165),
        ("PRJ-RNR-ERD-003", "Bhavani River Bridge & Approach Road", "Road", "Bhavani", 130),
        ("PRJ-RNR-ERD-004", "Erode Solar Power Transmission Corridor", "Renewable Energy", "Perundurai", 175),
        ("PRJ-RNR-ERD-005", "Sathyamangalam Forest Buffer Zone Project", "Conservation", "Sathyamangalam", 90),
    ],
    "Salem": [
        ("PRJ-RNR-SLM-001", "Salem Steel Plant Expansion Corridor", "Industrial", "Salem", 280),
        ("PRJ-RNR-SLM-002", "Salem Bypass Road Phase-2 Project", "Road", "Attur", 220),
        ("PRJ-RNR-SLM-003", "Mettur Dam Reservoir Widening Project", "Irrigation", "Mettur", 195),
        ("PRJ-RNR-SLM-004", "Edapadi Rural Drinking Water Supply", "Water Supply", "Edapadi", 145),
        ("PRJ-RNR-SLM-005", "Salem Urban Transport Corridor Project", "Urban Development", "Salem", 250),
        ("PRJ-RNR-SLM-006", "Omalur Industrial Estate Expansion", "Industrial", "Omalur", 170),
    ],
    "Namakkal": [
        ("PRJ-RNR-NMK-001", "Namakkal Poultry Corridor Road Project", "Road", "Namakkal", 155),
        ("PRJ-RNR-NMK-002", "Rasipuram Town Expansion Project", "Urban Development", "Rasipuram", 110),
        ("PRJ-RNR-NMK-003", "Tiruchengode Industrial Hub Connectivity", "Road", "Tiruchengode", 125),
        ("PRJ-RNR-NMK-004", "Kolli Hills Eco Tourism Access Road", "Road", "Kolli Hills", 85),
        ("PRJ-RNR-NMK-005", "Namakkal Solar Energy Transmission Line", "Renewable Energy", "Paramathi Velur", 95),
    ],
}

GRIEVANCE_TYPES = [
    "Compensation Inadequate",
    "Survey Measurement Error",
    "Housing Allocation Issue",
    "Livelihood Support Delayed",
    "Identity/Ownership Dispute",
    "Entitlement Classification Wrong",
    "Documentation Incomplete",
    "Repeated Inspection Harassment",
    "Officer Misconduct",
    "Payment Not Received",
]

GRIEVANCE_DESCRIPTIONS = {
    "Compensation Inadequate": "Family disputes that the assessed market value is significantly lower than the prevailing rate in the locality.",
    "Survey Measurement Error": "The survey measurement recorded is incorrect; actual land area is larger than what has been assessed.",
    "Housing Allocation Issue": "The alternative housing site offered is in a flood-prone area and lacks basic amenities.",
    "Livelihood Support Delayed": "Livelihood support amount sanctioned three months ago but has not been transferred to the bank account.",
    "Identity/Ownership Dispute": "There is a dispute with a neighbouring family over the ownership boundary affecting compensation calculation.",
    "Entitlement Classification Wrong": "Family is classified as non-BPL but qualifies under BPL norms and should receive enhanced R&R benefits.",
    "Documentation Incomplete": "Original patta documents were not accepted; family has submitted all required records but case is on hold.",
    "Repeated Inspection Harassment": "Revenue officials have conducted multiple inspections without informing the family in advance.",
    "Officer Misconduct": "Field officer made incorrect remarks in the verification report which do not reflect ground reality.",
    "Payment Not Received": "Compensation amount was approved and marked as paid but the bank confirms no credit has been received.",
}


def seed_synthetic_projects(c):
    """Seed projects and basic parcels for non-Coimbatore districts."""
    print("Seeding synthetic projects for Tiruppur, Erode, Salem, Namakkal...")
    
    seq = 1000
    for district, projects in DISTRICT_PROJECTS.items():
        taluks = list(DISTRICT_DATA[district]["taluks"].keys())
        for proj_id, proj_name, proj_type, taluk, land_req in projects:
            existing = c.execute("SELECT 1 FROM projects WHERE project_id=?", (proj_id,)).fetchone()
            if not existing:
                c.execute("""
                    INSERT INTO projects(
                        project_id, project_name, project_type, district, taluk,
                        total_land_required, affected_parcels, affected_families,
                        project_start_date, expected_completion_date,
                        current_stage, project_status, progress
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    proj_id, proj_name, proj_type, district, taluk,
                    land_req, random.randint(15, 45), random.randint(8, 30),
                    "2023-04-01", "2026-12-31",
                    random.choice(["Compensation", "Possession", "Rehabilitation", "Award"]),
                    "Active", random.randint(40, 85)
                ))
                # Create minimal project milestones
                for stage in ["Proposal", "SIA / Survey", "Notification", "Approval", "Award",
                               "Compensation", "Possession", "Rehabilitation"]:
                    c.execute("""
                        INSERT OR IGNORE INTO project_milestones(project_id, stage, status)
                        VALUES (?, ?, ?)
                    """, (proj_id, stage, "Completed" if stage in ["Proposal", "SIA / Survey", "Notification"] else "In Progress"))
            
            seq += 1
    c.commit()
    print("  ✓ Projects seeded")


def seed_rr_families(c):
    """Seed all R&R family records across 5 districts."""
    print("Seeding R&R family records...")
    
    # Track global sequence for deterministic IDs
    global_seq = 1
    edge_case_idx = 0
    
    for district, ddata in DISTRICT_DATA.items():
        target = ddata["target_families"]
        avg_r = ddata["avg_readiness"]
        std_r = ddata["readiness_std"]
        profile = ddata["profile"]
        taluks = ddata["taluks"]
        
        projects_in_district = [r[0] for r in c.execute(
            "SELECT project_id FROM projects WHERE district=? ORDER BY project_id",
            (district,)
        ).fetchall()]
        
        if not projects_in_district:
            print(f"  WARNING: No projects found for {district}")
            continue
        
        # Get existing parcels for Coimbatore, create synthetic ones for others
        if district == "Coimbatore":
            # Pick from existing r_and_r records that haven't been upgraded
            existing_parcels = c.execute("""
                SELECT p.id, p.survey_no, p.village, p.taluk, p.district, 
                       p.project_id, p.owner_reference, rr.id as rr_id
                FROM parcels p
                JOIN r_and_r rr ON rr.parcel_id = p.id
                WHERE p.district = 'Coimbatore'
                AND NOT EXISTS (
                    SELECT 1 FROM rr_families rf WHERE rf.parcel_id = p.id
                )
                LIMIT ?
            """, (target * 2,)).fetchall()
        else:
            existing_parcels = []
        
        district_family_count = 0
        parcel_pool = list(existing_parcels) if existing_parcels else []
        
        for i in range(target):
            # Generate target readiness with some noise
            target_r = max(0, min(100, avg_r + random.gauss(0, std_r)))
            
            # Decide if this is an edge case
            use_edge_case = (edge_case_idx < len(EDGE_CASES) and 
                             district_family_count < min(5, target // 5))
            
            if use_edge_case and edge_case_idx < len(EDGE_CASES):
                ec = EDGE_CASES[edge_case_idx]
                comp = ec["comp"]
                housing = ec["housing"]
                livelihood = ec["livelihood"]
                verif = ec["verif"]
                grievance = ec["grievance"]
                edge_tag = ec["tag"]
                edge_case_idx += 1
            else:
                comp, housing, livelihood, verif, grievance = gen_components_for_profile(profile, target_r)
                edge_tag = None
            
            readiness = calc_readiness(comp, housing, livelihood, verif, grievance)
            band = readiness_band(readiness)
            rr_stage = infer_rr_stage(comp, housing, livelihood, verif, grievance, readiness)
            exceptional = infer_exceptional_state(comp, housing, livelihood, verif, grievance, readiness)
            pending_action = infer_pending_action(comp, housing, livelihood, verif, grievance, rr_stage, exceptional)
            risk = infer_risk_level(readiness, grievance, verif, comp, exceptional)
            
            # Pick a taluk and village
            taluk = random.choice(list(taluks.keys()))
            village = random.choice(taluks[taluk])
            
            # Pick a project
            proj_id = random.choice(projects_in_district)
            
            # Survey number
            survey_no = f"{random.randint(10000, 99999):05d}/{random.randint(1,5)}{random.choice(['', 'A', 'B', 'C'])}"
            
            # Family details
            family_id = make_family_id(district, global_seq)
            family_head = pick_name([], global_seq)
            members = random.randint(2, 8)
            impact_type = random.choice(IMPACT_TYPES)
            is_vulnerable = 1 if (risk in ("Critical", "High") and random.random() < 0.4) else 0
            displacement_status = random.choice(["Displaced", "Partially Displaced", "Temporarily Relocated"])
            
            # Compensation amounts
            base_amount = random.randint(200000, 2500000)
            comp_entitled = round(base_amount, -3)
            if comp == "Fully Paid":
                comp_paid = comp_entitled
            elif comp == "Partially Paid":
                comp_paid = round(comp_entitled * random.uniform(0.3, 0.7), -3)
            elif comp in ("Approved", "Processing"):
                comp_paid = 0
            else:
                comp_paid = 0
            
            # Dates
            ident_date = f"202{random.randint(3,5)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            
            # Parcel linkage for Coimbatore
            parcel_id = None
            if district == "Coimbatore" and parcel_pool:
                p_row = parcel_pool.pop(0)
                parcel_id = p_row["id"]
                survey_no = p_row["survey_no"]
                village = p_row["village"]
                taluk = p_row["taluk"]
                proj_id = p_row["project_id"]
            
            try:
                c.execute("""
                    INSERT OR IGNORE INTO rr_families (
                        family_id, parcel_id, project_id, district, taluk, village,
                        survey_no, family_head, members, impact_type, displacement_status,
                        is_vulnerable, rr_stage, exceptional_state,
                        compensation_status, housing_status, livelihood_status,
                        verification_status, grievance_status,
                        readiness_percentage, readiness_band, risk_level,
                        compensation_entitled, compensation_paid,
                        pending_action, identified_date, edge_case_tag
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    family_id, parcel_id, proj_id, district, taluk, village,
                    survey_no, family_head, members, impact_type, displacement_status,
                    is_vulnerable, rr_stage, exceptional,
                    comp, housing, livelihood,
                    verif, grievance,
                    readiness, band, risk,
                    comp_entitled, comp_paid,
                    pending_action, ident_date, edge_tag
                ))
            except Exception as e:
                print(f"    Error inserting family {family_id}: {e}")
                continue
            
            # Add grievance record if applicable
            if grievance not in ("No Grievance", "Resolved"):
                g_type = random.choice(GRIEVANCE_TYPES)
                g_desc = GRIEVANCE_DESCRIPTIONS.get(g_type, "Grievance raised by affected family.")
                g_date = ident_date
                c.execute("""
                    INSERT OR IGNORE INTO rr_grievances (
                        family_id, project_id, district, grievance_type,
                        description, status, raised_date
                    ) VALUES (?,?,?,?,?,?,?)
                """, (family_id, proj_id, district, g_type, g_desc, grievance, g_date))
            
            # Add field verification record if applicable
            if verif in ("Verified", "Failed", "Re-verification Required", "Pending", "Scheduled"):
                v_status = verif if verif != "Re-verification Required" else "Failed"
                v_date = ident_date if verif == "Verified" else None
                c.execute("""
                    INSERT OR IGNORE INTO rr_field_verifications (
                        family_id, district,
                        verification_type, status, assigned_date, completed_date
                    ) VALUES (?,?,?,?,?,?)
                """, (family_id, district, "Family R&R Verification", 
                      v_status, ident_date, v_date if verif == "Verified" else None))
            
            global_seq += 1
            district_family_count += 1
        
        c.commit()
        count = c.execute("SELECT COUNT(*) FROM rr_families WHERE district=?", (district,)).fetchone()[0]
        print(f"  ✓ {district}: {count} families seeded")
    
    total = c.execute("SELECT COUNT(*) FROM rr_families").fetchone()[0]
    print(f"\n  Total R&R families: {total}")


def verify_edge_cases(c):
    """Verify all 20 edge cases are present in the data."""
    print("\nVerifying edge cases...")
    for ec in EDGE_CASES:
        count = c.execute(
            "SELECT COUNT(*) FROM rr_families WHERE edge_case_tag=?", (ec["tag"],)
        ).fetchone()[0]
        status = "✓" if count > 0 else "✗ MISSING"
        print(f"  {status} {ec['tag']}: {count} records")


def print_summary(c):
    """Print a summary of the seeded data."""
    print("\n=== SEED SUMMARY ===")
    for r in c.execute("""
        SELECT district, COUNT(*) families, 
               ROUND(AVG(readiness_percentage), 1) avg_readiness,
               SUM(CASE WHEN readiness_band='Completed' THEN 1 ELSE 0 END) completed,
               SUM(CASE WHEN readiness_band='On Track' THEN 1 ELSE 0 END) on_track,
               SUM(CASE WHEN readiness_band='Attention Required' THEN 1 ELSE 0 END) attention,
               SUM(CASE WHEN readiness_band='Delayed' THEN 1 ELSE 0 END) delayed,
               SUM(CASE WHEN readiness_band='Critical' THEN 1 ELSE 0 END) critical
        FROM rr_families
        GROUP BY district ORDER BY district
    """).fetchall():
        print(f"  {dict(r)}")
    
    print("\n  Grievances by status:")
    for r in c.execute("SELECT status, COUNT(*) cnt FROM rr_grievances GROUP BY status").fetchall():
        print(f"    {r[0]}: {r[1]}")
    
    print("\n  Field verifications by status:")
    for r in c.execute("SELECT status, COUNT(*) cnt FROM rr_field_verifications GROUP BY status").fetchall():
        print(f"    {r[0]}: {r[1]}")


def main():
    print(f"Connecting to: {DB}")
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    
    print("Running schema migration...")
    c.executescript(MIGRATE_SQL)
    c.commit()
    print("  ✓ Schema migration complete")
    
    # Seed synthetic projects for missing districts
    seed_synthetic_projects(c)
    
    # Seed R&R family data
    seed_rr_families(c)
    
    # Verify edge cases
    verify_edge_cases(c)
    
    # Sync legacy r_and_r table for matched Coimbatore parcels
    try:
        c.execute("""
            UPDATE r_and_r
            SET family_head = (SELECT rf.family_head FROM rr_families rf WHERE rf.parcel_id = r_and_r.parcel_id),
                members = (SELECT rf.members FROM rr_families rf WHERE rf.parcel_id = r_and_r.parcel_id),
                status = (SELECT rf.exceptional_state FROM rr_families rf WHERE rf.parcel_id = r_and_r.parcel_id),
                milestone = (SELECT rf.rr_stage FROM rr_families rf WHERE rf.parcel_id = r_and_r.parcel_id),
                pending_action = (SELECT rf.pending_action FROM rr_families rf WHERE rf.parcel_id = r_and_r.parcel_id)
            WHERE parcel_id IN (SELECT parcel_id FROM rr_families WHERE parcel_id IS NOT NULL)
        """)
        c.commit()
    except Exception as e:
        print(f"  Note: legacy r_and_r sync skipped: {e}")
    
    # Print summary
    print_summary(c)
    
    c.close()
    print("\n✅ R&R seed complete!")


if __name__ == "__main__":
    main()
