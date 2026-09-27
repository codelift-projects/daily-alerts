import os
import requests
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "service_2s3qdly")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "template_pkgrc46")
EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "codelift.official@gmail.com")

THRESHOLD = 5000.0

def send_email(sales):
    report_lines = [ f"Daily Sales Audit (Target: Rs. {THRESHOLD})" ]
    for branch, total in sales.items():
        diff = total - THRESHOLD
        margin = f"+Rs. {diff}" if diff >= 0 else f"-Rs. {diff}"
        status = "GOOD [GREEN]" if total >= THRESHOLD else ("WARNING [ORANGE]" if total >= 3000 else "CRITICAL [RED]")
        report_lines.append(f"{branch}: Rs. {total} — {status} ({margin})")

    payload = {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_PUBLIC_KEY,
        "template_params": {
            "studentname": "Operations Team",
            "message": "\n".join(report_lines),
            "emailtype":"Sales Report",
            "action_url": "https://supabase.com",
            "action_text": "View Dashboard",
            "to_email": ALERT_TO_EMAIL
        }
    }

    headers = {"Content-Type": "application/json", "origin": "http://localhost"}
    res = requests.post("https://api.emailjs.com/api/v1.0/email/send", json=payload, headers=headers)
    if res.status_code == 200:
        print("[SUCCESS] Email sent successfully!")
    else:
        print(f"[FAILED] Email failed: {res.status_code} - {res.text}")

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_KEY are required.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch completed orders with branch names
    orders = supabase.table("orders").select("amount, outlets(name)").eq("status", "COMPLETED").execute().data or []

    # Calculate total sales per branch
    sales = {}
    for o in orders:
        branch = o["outlets"]["name"]
        sales[branch] = sales.get(branch, 0.0) + float(o["amount"])

    # Print summary to console
    for branch, total in sales.items():
        print(f"{branch}: Rs. {total}")

    send_email(sales)

if __name__ == "__main__":
    main()
