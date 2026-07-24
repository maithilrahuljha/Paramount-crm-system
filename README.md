# ⚓ Paramount Merchant Navy — Sales Operations System

A **zero-cost, GitHub-first CRM ecosystem** for the Paramount Merchant Navy sales team:
Google Sheets as the live database, Google Forms for mobile-friendly data entry,
GitHub Actions for automation, GitHub Pages for a real-time admin dashboard, and
Looker Studio for executive reporting.

| Component | Purpose | Platform (Free) |
|---|---|---|
| Google Sheets | Live DB — leads, students, follow-ups, sales logs | Google Drive |
| Google Forms | Data entry for the sales team (mobile) | Google Drive |
| GitHub Repository | Source code, automation logic, version control | GitHub |
| GitHub Actions | Daily briefings, hourly KPIs, monthly archives | GitHub (2000 min/mo) |
| GitHub Pages | Real-time admin dashboard (HTML/CSS/JS) | GitHub Pages |
| Google Apps Script | On-form-submit Lead ID generator | Google Sheets |
| Looker Studio | Executive dashboard (charts & KPIs) | Looker Studio |

**Live dashboard (after enabling Pages):** `https://maithilrahuljha.github.io/Paramount-crm-system/`

---

## 📁 Repository Structure

```
├── github_workflows/               # ⚠️ Copy to .github/workflows/ (see Step 0)
│   ├── morning_briefing.yml        # 8:30 AM IST daily — Slack + Email briefing
│   ├── hourly_aggregation.yml      # Every hour — KPI computation & snapshot
│   └── monthly_archive.yml         # 1st of month — archive completed leads
├── install_workflows.sh            # One-command installer for the workflows
├── scripts/
│   ├── google_sheets_connector.py  # Sheets API v4 integration + KPI engine
│   ├── send_slack_email.py         # Slack webhook + Gmail SMTP briefing
│   └── archive_leads.py            # Moves closed leads to Archive_YYYY_MM tab
├── dashboard_ui/                   # Dashboard source (edit here)
│   ├── index.html                  # Layout (Navy Blue + Gold branding)
│   ├── style.css                   # Mobile-first responsive styles
│   ├── app.js                      # CSV fetch/parse, KPIs, 5-min auto refresh
│   └── config.js                   # ← paste your Sheet CSV URLs + Form URL here
├── docs/                           # GitHub Pages deployment folder (mirror of dashboard_ui)
├── apps_script_backup/
│   └── Code.gs                     # onFormSubmit trigger — PMN-YYYY-XXXX Lead IDs
├── looker_studio_export/
│   └── paramount_dashboard.json    # Looker Studio layout schema (rebuild reference)
├── data/
│   └── kpi_snapshot.json           # Hourly KPI snapshot (committed by Actions)
├── TEAM_FORMS_ACCESS_GUIDE.md      # Template for the team's form links doc
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 🚀 Deployment Guide

### Step 0 — Install the GitHub Actions Workflows (one-time, 30 seconds)

> The automation agent's GitHub App token cannot write to `.github/workflows/`
> (GitHub requires the special `workflows` permission), so the three workflow
> files are staged in [`github_workflows/`](github_workflows/). Install them
> with your own account:

**Option A — locally:**
```bash
git clone https://github.com/maithilrahuljha/Paramount-crm-system.git
cd Paramount-crm-system
git checkout arena/019f9176-paramount-crm-system
bash install_workflows.sh
```

**Option B — GitHub web UI:** for each file in `github_workflows/`, click
*Add file → Create new file*, name it `.github/workflows/<same filename>`,
paste the contents, and commit.

### Step 1 — Google Sheets & Forms Setup

Create a Google Drive folder named **`Paramount_CRM_Data`**, then create **4 sheets**
with these exact headers in row 1:

**Sheet 1: `Lead_Register`**
```
Lead ID | Timestamp | Candidate Name | Email | Phone Number | Course Interested | Lead Source | Status | Remarks
```

**Sheet 2: `Followup_Tracker`**
```
Lead ID | Candidate Name | Phone Number | Priority | Followup Date | Assigned Counselor | Status | Remarks
```

**Sheet 3: `Student_Master_DB`**
```
Cadet ID | Enrollment Date | Full Name | Email | Phone Number | Course Enrolled | Batch Name | Fee Status
```

**Sheet 4: `Daily_Sales_Log`**
```
Log Date | Counselor Name | Total Calls Made | New Leads Contacted | Interviews Conducted | Admissions Closed | Daily Notes
```

Then create **3 Google Forms** (question sets below), link each to its sheet
(*Responses tab → green Sheets icon → Select existing spreadsheet*):

<details>
<summary><b>Form 1 — Paramount Lead Intake Form (10 questions) → Lead_Register</b></summary>

| # | Question | Type | Options / Notes |
|---|---|---|---|
| 1 | Candidate Full Name | Short answer | Required |
| 2 | Email Address | Short answer | Required |
| 3 | Phone Number (with country code) | Short answer | Required, number validation |
| 4 | City / Location | Short answer | Required |
| 5 | Course Interested In | Dropdown | Deck Cadet, Engine Cadet, ETO, GME, B.Sc Nautical Science, Diploma, Other |
| 6 | How did you hear about us? | Dropdown | Google Search, Facebook/Instagram, YouTube, WhatsApp, Referral, Walk-in, Phone Call, Email, Other |
| 7 | Preferred Batch Month | Dropdown | January, April, July, October, Not Sure |
| 8 | Current Education Level | Dropdown | 10th Pass, 12th Appearing, 12th Pass, Graduate, Post Graduate, Other |
| 9 | Counsellor Assigned | Dropdown | Rahul Jha, Priya Sharma, Amit Kumar (edit as needed) |
| 10 | Additional Remarks | Paragraph | Optional |

Settings: Collect email addresses · Link to Lead_Register · Limit to 1 response.
</details>

<details>
<summary><b>Form 2 — Followup & Callback Log Form (11 questions) → Followup_Tracker</b></summary>

| # | Question | Type | Options / Notes |
|---|---|---|---|
| 1 | Lead ID | Short answer | Required, format `PMN-YYYY-XXXX` |
| 2 | Candidate Full Name | Short answer | Required |
| 3 | Phone Number | Short answer | Required, number validation |
| 4 | Call Date & Time | Date + Time | Required |
| 5 | Discussion Summary | Paragraph | Required |
| 6 | Interest Level | Dropdown | 🔥 Highly Interested, 👍 Interested, 🤔 Not Sure, 👎 Not Interested |
| 7 | Priority Level | Dropdown | P1 (Admission within 3 days), P2 (Interested), P3 (Need Counselling), P4 (Future Batch), P5 (Cold Lead) |
| 8 | Next Follow-up Date | Date | Required |
| 9 | Assigned Counselor | Dropdown | Rahul Jha, Priya Sharma, Amit Kumar |
| 10 | Call Result | Dropdown | Contacted - Spoke to Candidate, Contacted - Spoke to Parent, Voicemail, Wrong Number, Callback Requested, No Answer |
| 11 | Remarks | Paragraph | Optional |

Settings: Collect email addresses · Link to Followup_Tracker.
</details>

<details>
<summary><b>Form 3 — Daily Counselor Sales Report Form (11 questions) → Daily_Sales_Log</b></summary>

| # | Question | Type | Options / Notes |
|---|---|---|---|
| 1 | Report Date | Date | Required |
| 2 | Counselor Name | Dropdown | Rahul Jha, Priya Sharma, Amit Kumar |
| 3 | Total Calls Made Today | Short answer | Required, number ≥ 0 |
| 4 | Calls Answered / Connected | Short answer | Required, number ≥ 0 |
| 5 | New Leads Added Today | Short answer | Required, number ≥ 0 |
| 6 | Follow-up Calls Completed | Short answer | Required, number ≥ 0 |
| 7 | Counselling Sessions Conducted | Short answer | Required, number ≥ 0 |
| 8 | Admissions Closed Today | Short answer | Required, number ≥ 0 |
| 9 | Revenue Collected Today (₹) | Short answer | Required, number ≥ 0 |
| 10 | Pending Cases / Issues | Paragraph | Optional |
| 11 | Tomorrow's Priority Plan | Paragraph | Required |

Settings: Collect email addresses · Link to Daily_Sales_Log.
</details>

**Publish sheets to web (for the dashboard):**
1. Open `Lead_Register` → **File → Share → Publish to web**.
2. Select the specific sheet tab → choose **CSV** → **Publish** → copy the URL.
3. Repeat for `Followup_Tracker`.
4. Paste both URLs into `dashboard_ui/config.js` **and** `docs/config.js`.

**Form links:** click **Send** on each form → link icon → copy the URL → record
them in `TEAM_FORMS_ACCESS_GUIDE.md` (or a Google Doc copy for the team).

---

### Step 2 — Google Cloud Console (Service Account)

1. **Create project:** [Google Cloud Console](https://console.cloud.google.com) → project dropdown → **NEW PROJECT** → Name: `Paramount-CRM` → Location: *No organization* → **CREATE**.
2. **Enable APIs:** APIs & Services → Library → enable **Google Sheets API** and **Google Drive API**.
3. **Create service account:** IAM & Admin → Service Accounts → **+ CREATE SERVICE ACCOUNT** → Name: `paramount-crm-sa` → Role: **Editor** → DONE.
4. **Generate JSON key:** ⋮ → Manage keys → **ADD KEY → Create new key → JSON** → the file downloads. Its full content becomes the `GOOGLE_SERVICE_ACCOUNT_JSON` secret.
5. **Share Drive assets:** share the `Paramount_CRM_Data` folder **and each of the 4 sheets** with the `client_email` from the JSON, permission **Editor**.

---

### Step 3 — GitHub Secrets

Repository → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Description | Where to Get |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON content of the service account key | Google Cloud Console → Service Accounts → Create Key (JSON) |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | Slack Apps → Incoming Webhooks → Create |
| `GMAIL_USER` | Gmail address for sending briefings | Your Gmail/Workspace email |
| `GMAIL_APP_PASSWORD` | 16-character app password | Google Account → Security → 2-Step Verification → App Passwords |
| `DRIVE_FOLDER_ID` | ID of the `Paramount_CRM_Data` folder | Drive URL: `drive.google.com/drive/folders/[THIS_IS_THE_ID]` |
| `BRIEFING_RECIPIENTS` *(optional)* | Comma-separated emails for the briefing | Team email list (defaults to `GMAIL_USER`) |

> 🔐 Scripts read every secret via `os.environ.get()` — nothing is hardcoded.

---

### Step 4 — GitHub Pages

1. Repository → **Settings → Pages**.
2. Source: **Deploy from a branch** → Branch: your default branch (merge this work into `main`, or select `arena/019f9176-paramount-crm-system`) → Folder: **/docs** → **Save**.
3. Wait ~2 minutes → dashboard live at
   **https://maithilrahuljha.github.io/Paramount-crm-system/**

> The `/docs` folder is a deployable mirror of `dashboard_ui/`. GitHub Pages only
> serves from `/ (root)` or `/docs`, so `/docs` is used. Keep both `config.js`
> files in sync when you paste your CSV/Form URLs.

---

### Step 5 — Apps Script Deployment (Lead ID generator)

1. Open the `Lead_Register` sheet → **Extensions → Apps Script**.
2. Paste the contents of [`apps_script_backup/Code.gs`](apps_script_backup/Code.gs) → save as **Lead ID Generator**.
3. Triggers (clock icon) → **+ Add Trigger** → Function: `onFormSubmit` → Event source: *From spreadsheet* → Event type: **On form submit** → Save.
4. Run `onFormSubmit` once manually to authorize. Optional: run `backfillLeadIds` to stamp IDs on existing rows.

Every new form submission now gets a sequential ID like `PMN-2026-0042` in column A.

---

### Step 6 — GitHub Actions Verification

1. Open the **Actions** tab — you should see 3 workflows:
   * **Morning Briefing - 8:30 AM IST** (daily, 03:00 UTC)
   * **Hourly KPI Aggregation** (every hour)
   * **Monthly Lead Archive** (1st of month, 00:00 UTC)
2. Each supports **Run workflow** (manual `workflow_dispatch`) — trigger a test run after adding secrets.
3. Check the run logs; connection errors almost always mean the sheets aren't shared with the service-account email.

**Free-tier budget:** ~24 hourly runs/day × ~1 min + 1 daily run ≈ **~780 min/month**, safely inside GitHub's 2000 free minutes.

---

### Step 7 — Looker Studio Dashboard

1. Go to [Looker Studio](https://lookerstudio.google.com) → **Create → Report**.
2. Add data source → **Google Sheets** connector → select `Lead_Register` (repeat for `Followup_Tracker` and `Daily_Sales_Log`).
3. Rebuild the layout from [`looker_studio_export/paramount_dashboard.json`](looker_studio_export/paramount_dashboard.json) — scorecards, time series, pie/bar charts, priority table, plus theme colors `#1a237e` / `#ffd700` / `#0d47a1`.
4. **Share → Anyone with the link (Viewer)** and send the report URL to management.

---

## 🔄 Automation Details

| Workflow | Schedule (UTC) | What it does | Failure policy |
|---|---|---|---|
| `morning_briefing.yml` | `0 3 * * *` (8:30 AM IST) | Pulls live KPIs → Slack briefing + HTML email | Slack fails → email still sends; Sheets fails → degraded briefing sent |
| `hourly_aggregation.yml` | `0 * * * *` | Reads 3 sheets → computes KPIs → updates `KPI_Dashboard` tab (one `batch_update`) → commits `kpi_snapshot.json` | Exponential backoff on all API calls |
| `monthly_archive.yml` | `0 0 1 * *` | Moves leads with Status ∈ {Admitted, Enrolled, Closed, Converted} to `Archive_YYYY_MM` tab | Deletes only after archive append succeeds; `DRY_RUN=true` supported |

---

## 🔒 Constraints & Rules Honored

1. **Cost: $0** — free tiers only (GitHub Actions 2000 min/mo, Google API free quotas).
2. **Authentication** — all secrets via `os.environ.get()`; nothing hardcoded.
3. **Performance** — Sheets API v4 with batch reads/writes (`get_all_records`, `batch_update`, `append_rows`).
4. **Error handling** — Slack failure falls back to SMTP email; every network call retries with exponential backoff; all scripts wrapped in try/except with non-zero exit codes on fatal errors.
5. **Security** — published CSV URLs are read-only; the service account has Editor (never Owner) access.
6. **Documentation** — every script has module docstrings, function docstrings and inline comments.

---

## 🧾 Deliverables Checklist (owner actions)

- [ ] Create `Paramount_CRM_Data` folder + 4 sheets + 3 forms (Step 1)
- [ ] Publish CSVs & update `config.js` in `dashboard_ui/` **and** `docs/` (Steps 1 & 4)
- [ ] Create GCP project + service account + share sheets (Step 2)
- [ ] Add the GitHub Secrets (Step 3)
- [ ] Enable GitHub Pages from `/docs` (Step 4)
- [ ] Install the Apps Script trigger (Step 5)
- [ ] Manually run all 3 workflows once (Step 6)
- [ ] Build & share the Looker Studio report (Step 7)
- [ ] Fill in `TEAM_FORMS_ACCESS_GUIDE.md` and share with the team

---

*⚓ Fair winds and following seas — Paramount Merchant Navy Sales Ops.*
