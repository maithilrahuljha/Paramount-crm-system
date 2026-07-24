/**
 * config.js — Paramount CRM Dashboard configuration.
 *
 * ⚠️ ACTION REQUIRED after Google setup:
 *   1. Publish Lead_Register + Followup_Tracker to the web as CSV
 *      (File → Share → Publish to web → select tab → CSV).
 *   2. Replace the placeholder URLs below with your published CSV URLs.
 *   3. Replace quickAddFormUrl with your Lead Intake form link.
 *
 * The CSV URLs are READ-ONLY — publishing to web never grants write access.
 */
const config = {
  // Published CSV of the Lead_Register sheet
  leadRegisterCsvUrl:
    'https://docs.google.com/spreadsheets/d/REPLACE_LEAD_REGISTER_ID/export?format=csv&gid=0',

  // Published CSV of the Followup_Tracker sheet
  followupTrackerCsvUrl:
    'https://docs.google.com/spreadsheets/d/REPLACE_FOLLOWUP_TRACKER_ID/export?format=csv&gid=0',

  // "Quick Add Lead" button target (Lead Intake Google Form)
  quickAddFormUrl:
    'https://docs.google.com/forms/d/REPLACE_FORM_ID/viewform',

  // Optional: KPI snapshot committed hourly by GitHub Actions (fallback data)
  kpiSnapshotUrl: '../data/kpi_snapshot.json',

  // Auto-refresh interval in milliseconds (5 minutes)
  refreshInterval: 300000,

  branding: {
    title: 'Paramount Merchant Navy',
    subtitle: 'Sales Operations Command Center',
    colors: ['#1a237e', '#ffd700', '#0d47a1']
  }
};
