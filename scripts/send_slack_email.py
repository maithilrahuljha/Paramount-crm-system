"""
send_slack_email.py
===================
Paramount Merchant Navy CRM — Morning Briefing sender (8:30 AM IST).

What this script does (run daily by .github/workflows/morning_briefing.yml):
    1. Pulls live CRM data from Google Sheets (via the service account).
    2. Builds a morning briefing: yesterday's performance + today's P1/P2
       follow-up list + overall pipeline health.
    3. Posts the briefing to Slack via an Incoming Webhook.
    4. Emails the same briefing via Gmail SMTP (app password).

Failure policy (per system rules):
    * If Slack fails      -> the email is STILL sent.
    * If Sheets fails     -> a degraded briefing is sent noting the outage.
    * All network calls   -> retried with exponential backoff.

Required environment variables (GitHub Secrets):
    SLACK_WEBHOOK_URL            Slack incoming webhook URL (optional but recommended).
    GMAIL_USER                   Gmail address used as SMTP sender.
    GMAIL_APP_PASSWORD           16-char Google app password.
    BRIEFING_RECIPIENTS          Comma-separated recipient emails (optional;
                                 defaults to GMAIL_USER).
    GOOGLE_SERVICE_ACCOUNT_JSON  Service-account JSON key.
    DRIVE_FOLDER_ID              Paramount_CRM_Data folder ID.
"""

from __future__ import annotations

import os
import smtplib
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# Reuse the connector's Sheets helpers so logic lives in one place.
from google_sheets_connector import (
    IST,
    SHEET_DAILY_LOG,
    SHEET_FOLLOWUP,
    SHEET_LEAD_REGISTER,
    compute_kpis,
    get_client,
    open_spreadsheet,
    parse_int,
    read_records,
)

MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Briefing construction
# ---------------------------------------------------------------------------
def fetch_data() -> dict | None:
    """Pull CRM data and compute KPIs. Returns None if Sheets is unreachable."""
    try:
        client = get_client()
        leads = read_records(open_spreadsheet(client, SHEET_LEAD_REGISTER))
        followups = read_records(open_spreadsheet(client, SHEET_FOLLOWUP))
        logs = read_records(open_spreadsheet(client, SHEET_DAILY_LOG))
        return compute_kpis(leads, followups, logs)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"WARNING: could not fetch CRM data: {exc}")
        return None


def build_briefing_text(kpis: dict | None) -> tuple[str, str]:
    """Return (plain_text, html) versions of the briefing."""
    today = datetime.now(IST).strftime("%A, %d %B %Y")
    title = f"⚓ Paramount Merchant Navy — Morning Briefing ({today})"

    if kpis is None:
        body = (
            "Good morning team!\n\n"
            "⚠️ Live CRM data could not be fetched this morning "
            "(Google Sheets unreachable). Please check the sheets manually.\n\n"
            "— Paramount CRM Bot"
        )
        html = f"<h2>{title}</h2><p>{body.replace(chr(10), '<br>')}</p>"
        return f"{title}\n\n{body}", html

    followup_lines = [
        f"  • [{f['priority']}] {f['name']} — {f['phone']} "
        f"(due {f['followup_date']}, {f['counselor']})"
        for f in kpis["priority_followups"][:15]
    ] or ["  • No open P1/P2 follow-ups. 🎉"]

    text = (
        f"{title}\n\n"
        f"Good morning team! Here is today's snapshot:\n\n"
        f"📊 PIPELINE\n"
        f"  • Total leads: {kpis['total_leads']}\n"
        f"  • New leads yesterday/today: {kpis['todays_new_leads']}\n"
        f"  • Admissions closed (total): {kpis['admissions_closed_total']}\n"
        f"  • Conversion rate: {kpis['conversion_rate_pct']}%\n\n"
        f"🔥 PRIORITY FOLLOW-UPS ({kpis['priority_followups_count']} open P1/P2)\n"
        + "\n".join(followup_lines)
        + "\n\n🎯 Make every call count. Fair winds and following seas!\n"
        f"— Paramount CRM Bot ({kpis['generated_at_ist']})"
    )

    rows = "".join(
        f"<tr><td>{f['priority']}</td><td>{f['name']}</td><td>{f['phone']}</td>"
        f"<td>{f['followup_date']}</td><td>{f['counselor']}</td></tr>"
        for f in kpis["priority_followups"][:15]
    ) or "<tr><td colspan='5'>No open P1/P2 follow-ups 🎉</td></tr>"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px">
      <h2 style="color:#1a237e">⚓ Paramount Merchant Navy — Morning Briefing</h2>
      <p style="color:#555">{today}</p>
      <table cellpadding="8" style="border-collapse:collapse;width:100%">
        <tr style="background:#1a237e;color:#ffd700"><th colspan="2">Pipeline KPIs</th></tr>
        <tr><td>Total Leads</td><td><b>{kpis['total_leads']}</b></td></tr>
        <tr><td>Today's New Leads</td><td><b>{kpis['todays_new_leads']}</b></td></tr>
        <tr><td>Admissions Closed</td><td><b>{kpis['admissions_closed_total']}</b></td></tr>
        <tr><td>Conversion Rate</td><td><b>{kpis['conversion_rate_pct']}%</b></td></tr>
      </table>
      <h3 style="color:#1a237e">🔥 Priority Follow-ups ({kpis['priority_followups_count']} open)</h3>
      <table cellpadding="6" border="1" style="border-collapse:collapse;width:100%;font-size:13px">
        <tr style="background:#0d47a1;color:#fff">
          <th>Priority</th><th>Name</th><th>Phone</th><th>Due</th><th>Counselor</th>
        </tr>
        {rows}
      </table>
      <p style="color:#888;font-size:12px">Generated {kpis['generated_at_ist']} · Paramount CRM Bot</p>
    </div>
    """
    return text, html


# ---------------------------------------------------------------------------
# Delivery channels
# ---------------------------------------------------------------------------
def send_slack(text: str) -> bool:
    """Post the briefing to Slack. Returns True on success."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        print("Slack webhook not configured — skipping Slack.")
        return False

    delay = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(webhook, json={"text": text}, timeout=15)
            if resp.status_code == 200:
                print("Slack briefing sent. ✅")
                return True
            print(f"Slack returned HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.RequestException as exc:
            print(f"Slack attempt {attempt} failed: {exc}")
        time.sleep(delay)
        delay *= 2
    print("Slack delivery failed after retries — falling back to email only.")
    return False


def send_email(subject: str, text: str, html: str) -> bool:
    """Send the briefing via Gmail SMTP. Returns True on success."""
    user = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not user or not password:
        print("Gmail credentials not configured — skipping email.")
        return False

    recipients = [
        r.strip()
        for r in os.environ.get("BRIEFING_RECIPIENTS", user).split(",")
        if r.strip()
    ]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Paramount CRM Bot <{user}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    delay = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=30) as smtp:
                smtp.login(user, password)
                smtp.sendmail(user, recipients, msg.as_string())
            print(f"Email briefing sent to {len(recipients)} recipient(s). ✅")
            return True
        except Exception as exc:
            print(f"Email attempt {attempt} failed: {exc}")
            time.sleep(delay)
            delay *= 2
    print("Email delivery failed after retries.")
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Build and deliver the morning briefing over both channels."""
    try:
        kpis = fetch_data()
        text, html = build_briefing_text(kpis)
        subject = f"⚓ Paramount Morning Briefing — {datetime.now(IST).strftime('%d %b %Y')}"

        slack_ok = send_slack(text)
        email_ok = send_email(subject, text, html)

        if not slack_ok and not email_ok:
            print("FATAL: briefing could not be delivered on any channel.")
            return 1
        return 0
    except Exception as exc:
        print(f"FATAL: morning briefing crashed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
