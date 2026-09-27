# Sales Anomaly Alert POC

POC to track sales across Nagpur branches in Supabase and send automated email alerts via EmailJS if sales drop below ₹5,000.

## Branches (Nagpur)
- **Friends Colony** (Total: ₹1,500 -> Triggers Alert)
- **Hazari Pahad** (Total: ₹12,000 -> Normal)
- **Gokulpeth** (Total: ₹8,500 -> Normal)
- **Hingna** (Total: ₹2,200 -> Triggers Alert)

---

## 1. Run Database Migration
Copy and execute [schema.sql](file:///d:/codelift-projects/daily-alerts/schema.sql) in your Supabase SQL Editor.

## 2. GitHub Secrets Configuration
Add the following in repository **Settings > Secrets and variables > Actions**:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `EMAILJS_SERVICE_ID` 
- `EMAILJS_TEMPLATE_ID`
- `EMAILJS_PUBLIC_KEY`
- `ALERT_TO_EMAIL` (Recipient email address)

## 3. EmailJS Template Variables
The script sends data matching your template fields:
- `message`
- `studentname`
- `action_url`
- `action_text`
- `emailtype`
- `to_email`

## 4. Run Locally
```bash
pip install -r requirements.txt
python main.py
```
