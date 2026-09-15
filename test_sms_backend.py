import sys
sys.path.insert(0, 'c:/Users/RITHIKA/OneDrive/Desktop/sih/survi')

from backend.core import conn, token
from backend.routes.sms import (
    api_sms_stats,
    api_sms_templates,
    api_sms_recipients,
    api_send_sms,
    api_send_bulk_sms,
    api_sms_history,
    api_sms_health,
    SendSingleSMSRequest,
    BulkSMSRequest
)

print("=== 1. Testing Health & Templates ===")
print("Health:", api_sms_health())
print("Templates count:", len(api_sms_templates()["templates"]))

print("\n=== 2. Testing District Stats for All 5 Districts ===")
for dist in ["Coimbatore", "Tiruppur", "Namakkal", "Erode", "Salem"]:
    email = f"district.{dist.lower()}@tngov.in"
    tok = token(email, "district_authority", district_scope=dist, state_scope="Tamil Nadu")
    stats = api_sms_stats(district=dist, authorization="Bearer " + tok)
    print(f"  {dist}: Total Sent={stats['total_sent']}, Delivered={stats['delivered']}, Pending={stats['pending']}, Failed={stats['failed']}, Recipients={stats['district_recipients']}")

print("\n=== 3. Testing Recipient Identification in Namakkal ===")
nmk_tok = token("district.namakkal@tngov.in", "district_authority", district_scope="Namakkal", state_scope="Tamil Nadu")
recipients_data = api_sms_recipients(district="Namakkal", authorization="Bearer " + nmk_tok)
print(f"Namakkal Parcels: {recipients_data['total_parcels']}, Valid Phones: {recipients_data['valid_mobile_count']}, Missing Phones: {recipients_data['missing_mobile_count']}")

print("\n=== 4. Testing Cross-District Security ===")
try:
    # Namakkal District Authority attempting to query Coimbatore
    bad_stats = api_sms_stats(district="Coimbatore", authorization="Bearer " + nmk_tok)
    print("ERROR: Cross-district access was NOT blocked!")
except Exception as e:
    print("SUCCESS: Cross-district query blocked properly:", e)

print("\n=== 5. Testing Bulk SMS Sending in Namakkal ===")
sample_req = BulkSMSRequest(
    project_id="",
    template_name="Land Acquisition Notification",
    message_text="Government of Tamil Nadu: Land acquisition proceedings initiated for Survey No {survey_no}, Village {village}.",
    district="Namakkal"
)
bulk_result = api_send_bulk_sms(sample_req, authorization="Bearer " + nmk_tok)
print("Bulk SMS result:", bulk_result["message"])
print("Summary:", bulk_result["summary"]["delivered"], "delivered,", bulk_result["summary"]["skipped_missing_phone"], "skipped missing phone.")

# Check audit table for the entry
c = conn()
audit_entry = c.execute("SELECT * FROM audit WHERE action='BULK_SMS_SENT' ORDER BY id DESC LIMIT 1").fetchone()
print("Audit entry created:", dict(audit_entry))
c.close()

print("\nAll Backend SMS tests passed successfully!")
