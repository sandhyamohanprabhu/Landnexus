"""
Seed District SMS Data & Database Migrations — SURVI / LANDNEXUS
================================================================
1. Creates `sms_logs` table with indices.
2. Adds `mobile_number` and `owner_name` columns to `parcels` table if missing.
3. Seeds synthetic Indian phone numbers for parcels across all 5 districts:
   Coimbatore, Tiruppur, Erode, Salem, Namakkal (leaving ~8% missing to test detection).
4. Seeds baseline government SMS logs per district so summary cards show real database metrics.
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "survi.db"

DISTRICTS = ["Coimbatore", "Tiruppur", "Namakkal", "Erode", "Salem"]

TAMIL_NAMES = [
    "Murugan K", "Senthil Nathan S", "Lakshmi Ammal", "Ramasamy Gounder",
    "Palanisamy V", "Kavitha Rajan", "Anand Chettiar", "Selvi M",
    "Dhandapani P", "Meenakshi Sundaram", "Thirunavukkarasu R", "Revathi S",
    "Karthikeyan N", "Subramaniam T", "Banumathi K", "Chinnasamy A",
    "Ganesan M", "Saravanan P", "Vasanthi R", "Mohan Kumar S"
]

TEMPLATES = [
    ("TPL-01", "Land Acquisition Notification", "Statutory Notice", "Government of Tamil Nadu, {dist} District Administration: Land acquisition proceedings initiated for Project {prj}. Survey No: {srv}, Village: {vil}."),
    ("TPL-02", "Field Verification Scheduled", "Field Operation", "TN Land Acquisition Notice: Joint field verification scheduled for Survey No {srv}, Village {vil} on {dt}. Landowner {owner} is requested to be present."),
    ("TPL-04", "Compensation Approved", "Compensation", "TN Revenue Dept: Compensation award of Rs. {amt} has been approved by District Collector, {dist} for Survey No {srv}, Project {prj}."),
    ("TPL-05", "Compensation Payment Processed", "Disbursement", "Direct Benefit Transfer Alert: Compensation amount of Rs. {amt} for Survey No {srv} has been credited to your verified bank account. UTR Ref: TN-{dist[:3].upper()}-9841."),
    ("TPL-08", "Parcel Verification Completed", "Verification", "Land Records Update: Ground survey and boundary verification for Survey No {srv}, Village {vil} has been successfully completed and tagged in LANDNEXUS GIS.")
]

def generate_indian_mobile():
    prefix = random.choice(["9842", "9443", "8903", "9789", "7373", "9944", "9629"])
    suffix = f"{random.randint(100000, 999999)}"
    return f"{prefix[:4]}{suffix[:6]}"

def run_migration_and_seed():
    print(f"[MIGRATION] Connecting to {DB_PATH.name} ...")
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row

    # 1. Create sms_logs table
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sms_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT NOT NULL,
            project_id TEXT,
            parcel_id INTEGER,
            recipient_name TEXT,
            recipient_phone TEXT,
            message TEXT,
            template TEXT,
            message_type TEXT,
            provider TEXT,
            status TEXT,
            provider_message_id TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            delivered_at TEXT,
            failure_reason TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sms_logs_district ON sms_logs(district);
        CREATE INDEX IF NOT EXISTS idx_sms_logs_project ON sms_logs(project_id);
        CREATE INDEX IF NOT EXISTS idx_sms_logs_status ON sms_logs(status);
        CREATE INDEX IF NOT EXISTS idx_sms_logs_created ON sms_logs(created_at);
    """)

    # 2. Add columns to parcels if missing
    p_cols = [r['name'] for r in c.execute("PRAGMA table_info(parcels)").fetchall()]
    if 'mobile_number' not in p_cols:
        print("[MIGRATION] Adding mobile_number column to parcels table...")
        c.execute("ALTER TABLE parcels ADD COLUMN mobile_number TEXT")
    if 'owner_name' not in p_cols:
        print("[MIGRATION] Adding owner_name column to parcels table...")
        c.execute("ALTER TABLE parcels ADD COLUMN owner_name TEXT")

    # 3. Add phone_number column to users if missing
    u_cols = [r['name'] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    if 'phone_number' not in u_cols:
        print("[MIGRATION] Adding phone_number column to users table...")
        c.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")

    # 4. Seed Indian phone numbers for parcels across all districts
    print("\n[SEED] Checking and seeding phone numbers across all 5 districts...")
    for dist in DISTRICTS:
        parcels = c.execute("SELECT id, survey_no, owner_reference, mobile_number, owner_name FROM parcels WHERE lower(district) = ?", (dist.lower(),)).fetchall()
        print(f"  {dist}: {len(parcels)} parcels found")
        updated = 0
        for p in parcels:
            # Check if mobile_number is already set
            cur_phone = p['mobile_number']
            cur_name = p['owner_name']
            
            # 92% of parcels get a valid Indian phone number, 8% remain missing
            give_phone = random.random() < 0.92
            new_phone = cur_phone or (generate_indian_mobile() if give_phone else None)
            
            # Name resolution
            new_name = cur_name or p['owner_reference'] or random.choice(TAMIL_NAMES)
            if "@" in str(new_name):
                new_name = random.choice(TAMIL_NAMES)

            c.execute("UPDATE parcels SET mobile_number = ?, owner_name = ? WHERE id = ?", (new_phone, new_name, p['id']))
            updated += 1

        print(f"  {dist}: updated {updated} parcels with verified phone and owner details.")

    # 5. Seed initial baseline SMS logs for each district
    print("\n[SEED] Seeding baseline SMS history logs per district...")
    base_counts = {
        "Coimbatore": {"total": 45, "delivered": 42, "pending": 1, "failed": 2},
        "Tiruppur":   {"total": 35, "delivered": 32, "pending": 1, "failed": 2},
        "Namakkal":   {"total": 28, "delivered": 26, "pending": 1, "failed": 1},
        "Erode":      {"total": 30, "delivered": 28, "pending": 1, "failed": 1},
        "Salem":      {"total": 32, "delivered": 30, "pending": 1, "failed": 1},
    }

    now = datetime.now()
    for dist, counts in base_counts.items():
        existing = c.execute("SELECT count(*) FROM sms_logs WHERE lower(district) = ?", (dist.lower(),)).fetchone()[0]
        if existing >= counts["total"]:
            print(f"  {dist}: already has {existing} logs, skipping baseline seed.")
            continue

        # Get sample parcels from this district
        p_samples = c.execute("SELECT id, survey_no, village, project_id, owner_name, mobile_number FROM parcels WHERE lower(district) = ? AND mobile_number IS NOT NULL LIMIT 50", (dist.lower(),)).fetchall()
        if not p_samples:
            continue

        needed = counts["total"] - existing
        print(f"  {dist}: generating {needed} baseline SMS logs...")
        
        for i in range(needed):
            p = random.choice(p_samples)
            tpl_id, tpl_title, tpl_cat, tpl_raw = random.choice(TEMPLATES)
            days_ago = random.randint(0, 14)
            log_time = now - timedelta(days=days_ago, hours=random.randint(1, 10), minutes=random.randint(1, 50))
            log_time_str = log_time.strftime("%Y-%m-%d %H:%M:%S")

            # Determine status according to target ratio
            if i < counts["failed"]:
                st = "Failed"
                err = random.choice(["Recipient Handset Switched Off", "Subscriber Out of Coverage", "Telecom DND Filtered"])
                del_time = None
            elif i < (counts["failed"] + counts["pending"]):
                st = "Pending"
                err = None
                del_time = None
            else:
                st = "Delivered"
                err = None
                del_time = (log_time + timedelta(seconds=random.randint(3, 12))).strftime("%Y-%m-%d %H:%M:%S")

            amt = f"{random.randint(5, 45)},{random.randint(10, 99)},000"
            msg = tpl_raw.replace("{dist}", dist)\
                         .replace("{prj}", str(p['project_id']))\
                         .replace("{srv}", str(p['survey_no']))\
                         .replace("{vil}", str(p['village']))\
                         .replace("{owner}", str(p['owner_name']))\
                         .replace("{amt}", amt)\
                         .replace("{dt}", log_time.strftime("%d-%m-%Y"))

            msg_type = "Bulk" if (i % 3 == 0) else "Individual"
            msg_id = f"SIM-{dist[:3].upper()}-{random.randint(100000, 999999)}"

            c.execute("""
                INSERT INTO sms_logs (
                    district, project_id, parcel_id, recipient_name, recipient_phone,
                    message, template, message_type, provider, status,
                    provider_message_id, created_by, created_at, delivered_at, failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dist,
                p['project_id'],
                p['id'],
                p['owner_name'],
                p['mobile_number'],
                msg,
                tpl_title,
                msg_type,
                "DEMO (Safe Simulation)",
                st,
                msg_id,
                f"district.{dist.lower()}@tngov.in",
                log_time_str,
                del_time,
                err
            ))

    c.commit()
    c.close()
    print("\n[DONE] SMS database migration and baseline seeding complete!")

if __name__ == "__main__":
    run_migration_and_seed()
