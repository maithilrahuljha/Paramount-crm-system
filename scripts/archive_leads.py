"""
archive_leads.py
================
Paramount Merchant Navy CRM — Monthly lead archiver.

What this script does (run monthly by .github/workflows/monthly_archive.yml):
    1. Opens the Lead_Register spreadsheet via the service account.
    2. Finds all leads whose Status is completed/closed (see CLOSED_STATUSES).
    3. Appends them to an "Archive_YYYY_MM" tab (created if missing) inside
       the same spreadsheet — one batch append, quota friendly.
    4. Deletes the archived rows from the live tab (bottom-up so row indexes
       stay valid).

Safety features:
    * Dry-run mode: set DRY_RUN=true to preview without changing anything.
    * Nothing is deleted unless the archive append succeeded first.
    * Exponential backoff on every API call.

Required environment variables (GitHub Secrets):
    GOOGLE_SERVICE_ACCOUNT_JSON  Service-account JSON key.
    DRIVE_FOLDER_ID              Paramount_CRM_Data folder ID.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import gspread

from google_sheets_connector import (
    CLOSED_STATUSES,
    IST,
    SHEET_LEAD_REGISTER,
    get_client,
    open_spreadsheet,
    with_backoff,
)


def get_archive_tab(spreadsheet, header: list[str]):
    """Return (creating if needed) this month's archive worksheet."""
    # Archive is named for the month that just ENDED (runs on the 1st).
    last_month = (datetime.now(IST).replace(day=1) - timedelta(days=1))
    tab_name = f"Archive_{last_month.strftime('%Y_%m')}"
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = with_backoff(
            spreadsheet.add_worksheet, tab_name, rows=1000, cols=len(header) + 2
        )
        with_backoff(ws.append_row, header, value_input_option="RAW")
        print(f"Created archive tab: {tab_name}")
    return ws


def main() -> int:
    """Archive completed leads out of the live Lead_Register tab."""
    dry_run = os.environ.get("DRY_RUN", "").strip().lower() in {"1", "true", "yes"}

    try:
        client = get_client()
        spreadsheet = open_spreadsheet(client, SHEET_LEAD_REGISTER)
        if spreadsheet is None:
            return 1

        live = spreadsheet.sheet1
        all_values = with_backoff(live.get_all_values)
        if len(all_values) < 2:
            print("Lead_Register is empty — nothing to archive.")
            return 0

        header, rows = all_values[0], all_values[1:]

        # Locate the Status column (case-insensitive).
        try:
            status_idx = [h.strip().lower() for h in header].index("status")
        except ValueError:
            print("ERROR: 'Status' column not found in Lead_Register header.")
            return 1

        # Collect (sheet_row_number, row_values) for completed leads.
        to_archive = [
            (i + 2, row)  # +2 => 1-based rows + header row
            for i, row in enumerate(rows)
            if len(row) > status_idx
            and row[status_idx].strip().lower() in CLOSED_STATUSES
        ]

        if not to_archive:
            print("No completed leads to archive this month.")
            return 0

        print(f"Found {len(to_archive)} completed lead(s) to archive.")
        if dry_run:
            for rownum, row in to_archive:
                print(f"  [dry-run] would archive row {rownum}: {row[:3]}")
            return 0

        # 1) Append to archive tab in ONE batch call.
        archive_ws = get_archive_tab(spreadsheet, header)
        with_backoff(
            archive_ws.append_rows,
            [row for _, row in to_archive],
            value_input_option="RAW",
        )
        print(f"Appended {len(to_archive)} row(s) to '{archive_ws.title}'.")

        # 2) Delete from live tab bottom-up so indexes remain valid.
        for rownum, _ in sorted(to_archive, key=lambda t: t[0], reverse=True):
            with_backoff(live.delete_rows, rownum)
        print(f"Removed {len(to_archive)} row(s) from the live Lead_Register.")
        return 0

    except Exception as exc:
        print(f"FATAL: monthly archive failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
