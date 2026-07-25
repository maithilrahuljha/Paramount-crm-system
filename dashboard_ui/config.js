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
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vS7Jqtg0yQMYBIoZ2LTV9jJLFGtnaxfjA0hGcqjVOSK-l3ZjOUv6eOUTIVeazQX_Ao_JmuzVz7-eVCX/pub?gid=1210441358&single=true&output=csv',

  // Published CSV of the Followup_Tracker sheet
  followupTrackerCsvUrl:
    'https://docs.google.com/spreadsheets/d/e/2PACX-1vQBrIIkNmVzdoXgpK3xHiFPMFHSEDENI-rfwaPHQu01vEozHDpfYwT24YL25kwaIaiy_bi9hifrlm1e/pubhtml',

  // "Quick Add Lead" button target (Lead Intake Google Form)
  quickAddFormUrl:
    'https://docs.google.com/forms/d/1wrN-HyT5qxTBdgi9Y6x3GbttBzLQHtQaE5sLuYu0zC4/viewform',

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
