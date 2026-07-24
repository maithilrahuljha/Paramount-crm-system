"""
google_sheets_connector.py
==========================
Paramount Merchant Navy CRM — Google Sheets API v4 connector + hourly KPI
aggregation.

What this script does (run hourly by .github/workflows/hourly_aggregation.yml):
    1. Authenticates with a Google service account (JSON in env var).
    2. Locates the CRM spreadsheets inside the Paramount_CRM_Data Drive folder.
    3. Reads Lead_Register, Followup_Tracker and Daily_Sales_Log.
    4. Computes KPIs (today's leads, priority follow-ups, conversion rate,
       calls made, admissions closed, revenue, per-counselor leaderboard).
    5. Writes/updates a "KPI_Dashboard" tab inside Lead_Register using a single
       batch update (quota friendly).
    6. Saves a JSON snapshot to data/kpi_snapshot.json (committed by the
       workflow, consumable by the GitHub Pages dashboard).

Required environment variables (GitHub Secrets):
    GOOGLE_SERVICE_ACCOUNT_JSON  Full JSON key of the service account.
    DRIVE_FOLDER_ID              ID of the Paramount_CRM_Data Drive folder.

Cost: $0 — stays well inside the free Sheets API quota (300 read requests
per minute per project); this script performs < 10 API calls per run.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

# Third-party (see requirements.txt)
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# IST = UTC + 5:30 — all "today" logic uses Indian Standard Time.
IST = timezone(timedelta(hours=5, minutes=30))

SHEET_LEAD_REGISTER = "Lead_Register"
SHEET_FOLLOWUP = "Followup_Tracker"
SHEET_DAILY_LOG = "Daily_Sales_Log"

CLOSED_STATUSES = {"admitted", "enrolled", "closed", "converted", "admission closed"}
SNAPSHOT_PATH = os.path.join("data", "kpi_snapshot.json")

MAX_RETRIES = 4  # exponential backoff attempts for API calls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def with_backoff(func, *args, **kwargs):
    """Call ``func`` retrying with exponential backoff on API errors."""
    delay = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # gspread raises APIError / requests errors
            if attempt == MAX_RETRIES:
                raise
            print(f"[retry {attempt}/{MAX_RETRIES}] {exc} — sleeping {delay}s")
            time.sleep(delay)
            delay *= 2


def get_client() -> gspread.Client:
    """Build an authorized gspread client from the service-account secret."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON secret is not set.")
        sys.exit(1)
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(client: gspread.Client, title: str):
    """Open a spreadsheet by title (must be shared with the service account)."""
    try:
        return with_backoff(client.open, title)
    except gspread.SpreadsheetNotFound:
        print(
            f"ERROR: Spreadsheet '{title}' not found. Make sure it exists in "
            "the Paramount_CRM_Data folder AND is shared with the service "
            "account email (Editor access)."
        )
        return None


def read_records(spreadsheet, tab_title: str | None = None) -> list[dict]:
    """Read all rows of a worksheet as list-of-dicts (header row = keys)."""
    if spreadsheet is None:
        return []
    try:
        ws = spreadsheet.worksheet(tab_title) if tab_title else spreadsheet.sheet1
        return with_backoff(ws.get_all_records)
    except Exception as exc:
        print(f"WARNING: could not read '{spreadsheet.title}': {exc}")
        return []


def today_ist_str() -> str:
    """Return today's date in IST as YYYY-MM-DD."""
    return datetime.now(IST).strftime("%Y-%m-%d")


def parse_int(value) -> int:
    """Best-effort integer parsing for form-entered numbers."""
    try:
        return int(str(value).replace(",", "").replace("₹", "").strip() or 0)
    except (ValueError, TypeError):
        return 0


def is_today(timestamp: str) -> bool:
    """Check whether a sheet timestamp string falls on today's IST date."""
    ts = str(timestamp).strip()
    if not ts:
        return False
    today = datetime.now(IST)
    candidates = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
    ]
    for fmt in candidates:
        try:
            parsed = datetime.strptime(ts.split(".")[0], fmt)
            return parsed.date() == today.date()
        except ValueError:
            continue
    return False


# ---------------------------------------------------------------------------
# KPI computation
# ---------------------------------------------------------------------------
def compute_kpis(leads: list[dict], followups: list[dict], logs: list[dict]) -> dict:
    """Aggregate raw sheet rows into a KPI dictionary."""
    total_leads = len(leads)
    todays_leads = sum(1 for r in leads if is_today(r.get("Timestamp", "")))
    admissions = sum(
        1 for r in leads
        if str(r.get("Status", "")).strip().lower() in CLOSED_STATUSES
    )
    conversion_rate = round((admissions / total_leads) * 100, 2) if total_leads else 0.0

    # Priority follow-ups: anything tagged P1/P2 and not completed.
    priority_followups = [
        {
            "lead_id": r.get("Lead ID", ""),
            "name": r.get("Candidate Name", ""),
            "phone": str(r.get("Phone Number", "")),
            "priority": str(r.get("Priority", "")).strip(),
            "followup_date": str(r.get("Followup Date", "")),
            "counselor": r.get("Assigned Counselor", ""),
        }
        for r in followups
        if str(r.get("Priority", "")).strip().upper().startswith(("P1", "P2"))
        and str(r.get("Status", "")).strip().lower() not in {"done", "completed", "closed"}
    ]

    # Today's sales activity from Daily_Sales_Log.
    todays_logs = [r for r in logs if is_today(r.get("Log Date", ""))]
    calls_today = sum(parse_int(r.get("Total Calls Made")) for r in todays_logs)
    admissions_today = sum(parse_int(r.get("Admissions Closed")) for r in todays_logs)

    # Per-counselor leaderboard (all-time from the daily log).
    leaderboard: dict[str, dict] = {}
    for r in logs:
        name = str(r.get("Counselor Name", "")).strip() or "Unknown"
        row = leaderboard.setdefault(name, {"calls": 0, "admissions": 0})
        row["calls"] += parse_int(r.get("Total Calls Made"))
        row["admissions"] += parse_int(r.get("Admissions Closed"))

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_at_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "total_leads": total_leads,
        "todays_new_leads": todays_leads,
        "admissions_closed_total": admissions,
        "conversion_rate_pct": conversion_rate,
        "priority_followups_count": len(priority_followups),
        "priority_followups": priority_followups[:50],  # cap payload size
        "calls_made_today": calls_today,
        "admissions_closed_today": admissions_today,
        "counselor_leaderboard": leaderboard,
    }


def write_kpi_tab(spreadsheet, kpis: dict) -> None:
    """Write KPIs to a 'KPI_Dashboard' tab using ONE batch update call."""
    if spreadsheet is None:
        return
    try:
        try:
            ws = spreadsheet.worksheet("KPI_Dashboard")
        except gspread.WorksheetNotFound:
            ws = with_backoff(spreadsheet.add_worksheet, "KPI_Dashboard", rows=50, cols=4)

        rows = [
            ["Paramount CRM — KPI Dashboard", ""],
            ["Last Updated (IST)", kpis["generated_at_ist"]],
            ["", ""],
            ["Total Leads", kpis["total_leads"]],
            ["Today's New Leads", kpis["todays_new_leads"]],
            ["Admissions Closed (Total)", kpis["admissions_closed_total"]],
            ["Conversion Rate (%)", kpis["conversion_rate_pct"]],
            ["Open P1/P2 Follow-ups", kpis["priority_followups_count"]],
            ["Calls Made Today", kpis["calls_made_today"]],
            ["Admissions Closed Today", kpis["admissions_closed_today"]],
        ]
        # Single batch call — quota friendly (one write instead of ten).
        with_backoff(ws.batch_update, [{"range": "A1:B10", "values": rows}])
        print("KPI_Dashboard tab updated.")
    except Exception as exc:
        print(f"WARNING: could not update KPI_Dashboard tab: {exc}")


def save_snapshot(kpis: dict) -> None:
    """Persist the KPI snapshot for the GitHub Pages dashboard.

    Written to both data/ (repo record) and docs/data/ (served by Pages).
    """
    for path in (SNAPSHOT_PATH, os.path.join("docs", SNAPSHOT_PATH)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(kpis, fh, indent=2, ensure_ascii=False)
        print(f"Snapshot written to {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Run the hourly aggregation end-to-end."""
    try:
        client = get_client()
        lead_ss = open_spreadsheet(client, SHEET_LEAD_REGISTER)
        follow_ss = open_spreadsheet(client, SHEET_FOLLOWUP)
        log_ss = open_spreadsheet(client, SHEET_DAILY_LOG)

        leads = read_records(lead_ss)
        followups = read_records(follow_ss)
        logs = read_records(log_ss)

        kpis = compute_kpis(leads, followups, logs)
        print(json.dumps({k: v for k, v in kpis.items()
                          if k not in ("priority_followups", "counselor_leaderboard")},
                         indent=2))

        write_kpi_tab(lead_ss, kpis)
        save_snapshot(kpis)
        return 0
    except Exception as exc:
        print(f"FATAL: hourly aggregation failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
