import os
from datetime import datetime
import requests
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "service_2s3qdly")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "template_pkgrc46")
EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "codelift.official@gmail.com")

THRESHOLD = 5000.0

def send_email(sales, today_iso, today_formatted):
    """Sends date-specific sales audit email via EmailJS"""
    
    report_lines = [
        f"Daily Sales Report: {today_formatted}",
        f"Date: {today_iso} | Benchmark Target: Rs. {THRESHOLD:,.0f}",
        "-" * 42
    ]
    
    total_sales = 0.0
    critical_branches = []
    
    for branch, total in sales.items():
        total_sales += total
        diff = total - THRESHOLD
        margin = f"+Rs. {diff:,.0f}" if diff >= 0 else f"-Rs. {abs(diff):,.0f}"
        
        if total >= THRESHOLD:
            status = "GOOD [GREEN]"
        elif total >= 3000:
            status = "WARNING [ORANGE]"
        else:
            status = "CRITICAL [RED]"
            critical_branches.append(branch)
            
        report_lines.append(f"{branch}: Rs. {total:,.0f} — {status} ({margin})")

    report_lines.append("-" * 42)
    report_lines.append(f"Today's Total Revenue: Rs. {total_sales:,.0f}")
    if critical_branches:
        report_lines.append(f"Alert: {len(critical_branches)} branch(es) below threshold today ({', '.join(critical_branches)}).")
    else:
        report_lines.append("Status: All branches met today's sales target.")

    payload = {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_PUBLIC_KEY,
        "template_params": {
            "studentname": "Operations Team",
            "message": "\n".join(report_lines),
            "emailtype": f"Daily Sales Audit ({today_formatted})",
            "action_url": "https://supabase.com",
            "action_text": "View Today's Analytics",
            "to_email": ALERT_TO_EMAIL
        }
    }

    headers = {"Content-Type": "application/json", "origin": "http://localhost"}
    res = requests.post("https://api.emailjs.com/api/v1.0/email/send", json=payload, headers=headers)
    if res.status_code == 200:
        print(f"[SUCCESS] Email sent for date {today_iso}!")
    else:
        print(f"[FAILED] Email failed: {res.status_code} - {res.text}")

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_KEY are required.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")          # e.g., '2026-09-27'
    today_formatted = now.strftime("%d %b %Y")    # e.g., '27 Sep 2026'

    # 1. Fetch all outlets
    outlets = supabase.table("outlets").select("name").execute().data or []
    sales = {o["name"]: 0.0 for o in outlets}

    # 2. Fetch ONLY today's completed orders
    orders = (
        supabase.table("orders")
        .select("amount, outlets(name)")
        .eq("status", "COMPLETED")
        .eq("created_at", today_iso)
        .execute()
        .data or []
    )

    # 3. Aggregate sales for today
    for o in orders:
        branch = o["outlets"]["name"]
        sales[branch] = sales.get(branch, 0.0) + float(o["amount"])

    # 4. Print today's summary to console
    print(f"\n==========================================")
    print(f" Daily Sales Audit — {today_formatted} ({today_iso})")
    print(f"==========================================")
    for branch, total in sales.items():
        status = "GREEN" if total >= THRESHOLD else ("ORANGE" if total >= 3000 else "RED")
        print(f"[{status}] {branch}: Rs. {total:,.0f}")
    print(f"==========================================\n")

    # 5. Send Date-Wise Email Report
    send_email(sales, today_iso, today_formatted)

if __name__ == "__main__":
    main()
