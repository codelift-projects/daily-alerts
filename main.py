import os
import sys
from datetime import datetime
import requests
from dotenv import load_dotenv
from supabase import create_client

# Force UTF-8 stdout if needed
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "service_2s3qdly")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "template_pkgrc46")
EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "codelift.official@gmail.com")

THRESHOLD = 5000.0

def validate_environment():
    """Failpoint 1: Check required environment variables."""
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    if not EMAILJS_PUBLIC_KEY:
        missing.append("EMAILJS_PUBLIC_KEY")
    if not EMAILJS_SERVICE_ID:
        missing.append("EMAILJS_SERVICE_ID")
    if not EMAILJS_TEMPLATE_ID:
        missing.append("EMAILJS_TEMPLATE_ID")
    if not ALERT_TO_EMAIL:
        missing.append("ALERT_TO_EMAIL")

    if missing:
        print("\n" + "=" * 60)
        print("[FAILPOINT 1: CONFIGURATION ERROR]")
        print("Missing required environment variables / GitHub Secrets:")
        for var in missing:
            print(f"  - {var}")
        print("\nAction required:")
        print("  Add these under repository Settings > Secrets and variables > Actions")
        print("=" * 60 + "\n")
        sys.exit(1)

    print("[OK] [1/4] Configuration loaded successfully.")
    print(f"  * Supabase URL: {SUPABASE_URL[:25]}...")
    print(f"  * EmailJS Service: {EMAILJS_SERVICE_ID}")
    print(f"  * EmailJS Template: {EMAILJS_TEMPLATE_ID}")
    print(f"  * Recipient: {ALERT_TO_EMAIL}")

def send_email(sales, today_iso, today_formatted):
    """Sends date-specific sales audit email via EmailJS with Failpoint diagnostics"""
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
    
    print("\n[4/4] Sending email via EmailJS...")
    try:
        res = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json=payload,
            headers=headers,
            timeout=15
        )
    except requests.exceptions.RequestException as e:
        print("\n" + "=" * 60)
        print("[FAILPOINT 4: NETWORK / CONNECTION ERROR]")
        print(f"Could not reach EmailJS API: {e}")
        print("=" * 60 + "\n")
        sys.exit(1)

    if res.status_code == 200:
        print(f"[SUCCESS] Email delivered successfully to {ALERT_TO_EMAIL} for date {today_iso}!")
    else:
        print("\n" + "=" * 60)
        print("[FAILPOINT 4: EMAILJS API REJECTION]")
        print(f"HTTP Status: {res.status_code}")
        print(f"Response: {res.text}")
        print("\nPossible Causes:")
        print("  - Invalid EMAILJS_PUBLIC_KEY, EMAILJS_SERVICE_ID, or EMAILJS_TEMPLATE_ID")
        print("  - EmailJS monthly quota exceeded (Free tier: 200/mo)")
        print("  - Disconnected email account in EmailJS service settings")
        print("=" * 60 + "\n")
        sys.exit(1)

def main():
    # 1. Validate Environment
    validate_environment()

    # 2. Connect to Supabase
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILPOINT 2: SUPABASE CLIENT INITIALIZATION ERROR]")
        print(f"Error creating Supabase client: {e}")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")          # e.g., '2026-09-27'
    today_formatted = now.strftime("%d %b %Y")    # e.g., '27 Sep 2026'

    # 3. Fetch all outlets
    print(f"\n[2/4] Fetching outlets from Supabase...")
    try:
        outlets_res = supabase.table("outlets").select("name").execute()
        outlets = outlets_res.data or []
        if not outlets:
            print("[WARN] No outlets found in 'outlets' table.")
        else:
            print(f"[OK] Found {len(outlets)} outlet(s): {', '.join([o['name'] for o in outlets])}")
    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILPOINT 2: SUPABASE OUTLETS QUERY FAILED]")
        print(f"Error querying 'outlets' table: {e}")
        print("Check if SUPABASE_URL/SUPABASE_KEY are valid and table exists.")
        print("=" * 60 + "\n")
        sys.exit(1)

    sales = {o["name"]: 0.0 for o in outlets}

    # 4. Fetch ONLY today's completed orders
    print(f"\n[3/4] Fetching today's orders ({today_iso})...")
    try:
        orders_res = (
            supabase.table("orders")
            .select("amount, outlets(name)")
            .eq("status", "COMPLETED")
            .eq("created_at", today_iso)
            .execute()
        )
        orders = orders_res.data or []
        print(f"[OK] Found {len(orders)} completed order(s) for today.")
    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILPOINT 3: SUPABASE ORDERS QUERY FAILED]")
        print(f"Error querying 'orders' table: {e}")
        print("=" * 60 + "\n")
        sys.exit(1)

    # 5. Aggregate sales for today
    for o in orders:
        branch = o["outlets"]["name"]
        sales[branch] = sales.get(branch, 0.0) + float(o["amount"])

    # 6. Print today's summary to console
    print(f" Daily Sales Audit — {today_formatted} ({today_iso})")
    for branch, total in sales.items():
        status = "GREEN" if total >= THRESHOLD else ("ORANGE" if total >= 3000 else "RED")
        print(f"[{status}] {branch}: Rs. {total:,.0f}")

    # 7. Send Date-Wise Email Report
    send_email(sales, today_iso, today_formatted)

if __name__ == "__main__":
    main()
