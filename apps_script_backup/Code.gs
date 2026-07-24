/**
 * Code.gs — Paramount Merchant Navy CRM
 * Lead ID Generator (Google Apps Script, bound to the Lead_Register sheet).
 *
 * WHAT IT DOES
 *   When the "Paramount Lead Intake Form" is submitted, Google Forms appends
 *   a new row to the linked sheet. This trigger stamps a sequential Lead ID
 *   into Column A in the format:  PMN-YYYY-XXXX  (e.g. PMN-2026-0042)
 *
 * INSTALLATION (one time)
 *   1. Open the Lead_Register spreadsheet → Extensions → Apps Script.
 *   2. Paste this file, save the project as "Lead ID Generator".
 *   3. Left sidebar → Triggers (clock icon) → "+ Add Trigger":
 *        Function:      onFormSubmit
 *        Event source:  From spreadsheet
 *        Event type:    On form submit
 *   4. Save → authorize when prompted (run once manually if asked).
 *
 * NOTE: The form should be linked so responses land in a tab whose first
 * column is "Lead ID" (insert a Lead ID column at position A of the response
 * tab, or rename the response tab to "Lead_Register").
 */

/**
 * Fired automatically on every form submission.
 * @param {Object} e - Form submit event (contains e.range of the new row).
 */
function onFormSubmit(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Lead_Register");

    // Fall back to the sheet that actually received the submission.
    if (!sheet && e && e.range) {
      sheet = e.range.getSheet();
    }
    if (!sheet) {
      Logger.log("ERROR: Could not resolve target sheet.");
      return;
    }

    // Prefer the exact row from the event; fall back to last row.
    var row = (e && e.range) ? e.range.getRow() : sheet.getLastRow();

    // Skip if this row already has a Lead ID (idempotent re-runs).
    var cell = sheet.getRange(row, 1);
    if (String(cell.getValue()).indexOf("PMN-") === 0) return;

    // Sequential counter = number of data rows so far (header excluded).
    var year = new Date().getFullYear();
    var count = sheet.getLastRow() - 1; // subtract header row
    var leadId = "PMN-" + year + "-" + padStart_(String(count), 4);

    cell.setValue(leadId);
    Logger.log("Assigned Lead ID: " + leadId + " (row " + row + ")");
  } catch (err) {
    Logger.log("onFormSubmit failed: " + err);
  }
}

/**
 * String.padStart polyfill for older Apps Script runtimes.
 * @param {string} s   Input string.
 * @param {number} len Target length.
 * @return {string} Zero-padded string.
 */
function padStart_(s, len) {
  while (s.length < len) s = "0" + s;
  return s;
}

/**
 * Utility: run once manually to backfill Lead IDs for existing rows
 * that don't have one yet.
 */
function backfillLeadIds() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Lead_Register");
  if (!sheet) return;
  var year = new Date().getFullYear();
  var last = sheet.getLastRow();
  for (var row = 2; row <= last; row++) {
    var cell = sheet.getRange(row, 1);
    if (String(cell.getValue()).indexOf("PMN-") !== 0) {
      cell.setValue("PMN-" + year + "-" + padStart_(String(row - 1), 4));
    }
  }
}
