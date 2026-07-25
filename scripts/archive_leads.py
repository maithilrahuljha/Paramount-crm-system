#!/usr/bin/env python3
"""
Paramount Merchant Navy - Monthly Lead Archive
Moves completed/enrolled leads to an archive tab
Runs on the 1st of every month
"""

import os
import json
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CLOSED_STATUSES = {'enrolled', 'completed', 'admitted', 'closed', 'joined'}
SHEET_LEAD_REGISTER = 'Lead_Register'
FORM_RESPONSES_TAB = 'Form Responses 1'  # The tab where form data is stored

def get_client():
    """Authenticate and return Google Sheets client"""
    try:
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")
        
        creds_dict = json.loads(service_account_json)
        scope = ['https://spreadsheets.google.com/feeds', 
                 'https://www.googleapis.com/auth/drive']
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        logger.info("✅ Successfully authenticated with Google Sheets API")
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to authenticate: {str(e)}")
        raise

def with_backoff(func, *args, **kwargs):
    """Execute function with exponential backoff on rate limits"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if 'Quota exceeded' in str(e) or 'Rate limit' in str(e):
                wait_time = 2 ** attempt
                logger.warning(f"Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")

def find_spreadsheet_by_name(client, folder_id, sheet_name):
    """Find a spreadsheet by name in a specific folder"""
    try:
        folder = client.open_by_key(folder_id)
        files = folder.list_spreadsheet_files()
        
        for file in files:
            if file['name'] == sheet_name:
                logger.info(f"✅ Found spreadsheet: {sheet_name} (ID: {file['id']})")
                return file['id']
        
        raise ValueError(f"Spreadsheet '{sheet_name}' not found in folder")
        
    except Exception as e:
        logger.error(f"❌ Error finding spreadsheet '{sheet_name}': {str(e)}")
        raise

def get_archive_tab(spreadsheet, header):
    """Get or create this month's archive tab"""
    # Archive is named for the month that just ended (runs on the 1st)
    last_month = (datetime.now() - timedelta(days=1)).replace(day=1)
    tab_name = f"Archive_{last_month.strftime('%Y_%m')}"
    
    try:
        ws = spreadsheet.worksheet(tab_name)
        logger.info(f"Using existing archive tab: {tab_name}")
    except gspread.WorksheetNotFound:
        ws = with_backoff(
            spreadsheet.add_worksheet, tab_name, rows=1000, cols=len(header) + 2
        )
        with_backoff(ws.append_row, header, value_input_option="RAW")
        logger.info(f"Created new archive tab: {tab_name}")
    
    return ws

def main():
    """Archive completed leads out of the live Lead_Register tab"""
    dry_run = os.environ.get("DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
    
    try:
        folder_id = os.environ.get('DRIVE_FOLDER_ID')
        if not folder_id:
            raise ValueError("DRIVE_FOLDER_ID environment variable not set")
        
        # Authenticate
        client = get_client()
        
        # Find the Lead_Register spreadsheet
        spreadsheet_id = find_spreadsheet_by_name(client, folder_id, SHEET_LEAD_REGISTER)
        spreadsheet = client.open_by_key(spreadsheet_id)
        logger.info(f"✅ Opened spreadsheet: {spreadsheet.title}")
        
        # Get the "Form Responses 1" tab where form data is stored
        try:
            live = spreadsheet.worksheet(FORM_RESPONSES_TAB)
            logger.info(f"✅ Using tab: {FORM_RESPONSES_TAB}")
        except gspread.WorksheetNotFound:
            # Fallback to first sheet if tab not found
            live = spreadsheet.get_worksheet(0)
            logger.info(f"⚠️ Using first sheet instead: {live.title}")
        
        all_values = with_backoff(live.get_all_values)
        
        if len(all_values) < 2:
            logger.info(f"No data found in {live.title} — nothing to archive.")
            return 0
        
        header = all_values[0]
        rows = all_values[1:]
        
        # Find the Status column
        try:
            status_idx = [h.strip().lower() for h in header].index("status")
            logger.info(f"Found 'Status' column at index {status_idx}")
        except ValueError:
            logger.error("❌ 'Status' column not found in header.")
            logger.info(f"Headers found: {header}")
            return 1
        
        # Collect rows with closed statuses
        to_archive = []
        for i, row in enumerate(rows):
            if len(row) > status_idx:
                status = row[status_idx].strip().lower()
                if status in CLOSED_STATUSES:
                    to_archive.append((i + 2, row))  # +2 for header row
        
        if not to_archive:
            logger.info("No completed leads to archive this month.")
            return 0
        
        logger.info(f"Found {len(to_archive)} completed lead(s) to archive.")
        
        if dry_run:
            for rownum, row in to_archive:
                logger.info(f"  [DRY-RUN] would archive row {rownum}: {row[:3]}")
            return 0
        
        # 1) Append to archive tab in ONE batch
        archive_ws = get_archive_tab(spreadsheet, header)
        with_backoff(
            archive_ws.append_rows,
            [row for _, row in to_archive],
            value_input_option="RAW"
        )
        logger.info(f"✅ Appended {len(to_archive)} row(s) to '{archive_ws.title}'.")
        
        # 2) Delete from live tab bottom-up
        for rownum, _ in sorted(to_archive, key=lambda t: t[0], reverse=True):
            with_backoff(live.delete_rows, rownum)
        
        logger.info(f"✅ Removed {len(to_archive)} row(s) from the live {live.title}.")
        return 0
        
    except Exception as exc:
        logger.error(f"❌ FATAL: monthly archive failed: {exc}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
