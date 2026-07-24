/**
 * app.js — Paramount Merchant Navy Sales Dashboard.
 *
 * Responsibilities:
 *   • Fetch published CSV data from Google Sheets (read-only URLs in config.js)
 *   • Parse CSV with a small dependency-free parser (handles quoted fields)
 *   • Render KPIs, priority follow-up list, latest leads, lead-source bars
 *   • Auto-refresh every config.refreshInterval ms (default 5 minutes)
 *
 * No build step, no frameworks — pure vanilla JS for GitHub Pages.
 */

/* ============================ CSV parsing ============================ */

/**
 * Minimal RFC-4180-ish CSV parser supporting quoted fields and commas
 * inside quotes. Returns an array of row-objects keyed by the header row.
 */
function parseCsv(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field); field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some(v => v !== '')) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); if (row.some(v => v !== '')) rows.push(row); }

  if (!rows.length) return [];
  const header = rows[0].map(h => h.trim());
  return rows.slice(1).map(r =>
    Object.fromEntries(header.map((h, idx) => [h, (r[idx] || '').trim()]))
  );
}

/* ============================ Helpers ============================ */

const $ = id => document.getElementById(id);

const CLOSED_STATUSES = ['admitted', 'enrolled', 'closed', 'converted', 'admission closed'];

function isConfigured(url) {
  return url && !url.includes('REPLACE_') && !url.includes('XXXXX');
}

/** Robustly check if a sheet timestamp is today (handles common formats). */
function isToday(value) {
  if (!value) return false;
  const now = new Date();
  // Try native parsing first (ISO, "MM/DD/YYYY HH:MM:SS" etc.)
  const d = new Date(value);
  if (!isNaN(d)) {
    return d.getFullYear() === now.getFullYear() &&
           d.getMonth() === now.getMonth() &&
           d.getDate() === now.getDate();
  }
  // Fallback: DD/MM/YYYY
  const m = String(value).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) {
    return +m[3] === now.getFullYear() && +m[2] === now.getMonth() + 1 && +m[1] === now.getDate();
  }
  return false;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function showBanner(message, isError) {
  const el = $('statusBanner');
  el.textContent = message;
  el.classList.remove('hidden');
  el.classList.toggle('error', !!isError);
}

function hideBanner() { $('statusBanner').classList.add('hidden'); }

async function fetchCsv(url) {
  const resp = await fetch(url, { cache: 'no-store' });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} fetching sheet CSV`);
  return parseCsv(await resp.text());
}

/* ============================ Rendering ============================ */

function renderKpis(leads) {
  const total = leads.length;
  const today = leads.filter(l => isToday(l['Timestamp'])).length;
  const admissions = leads.filter(l =>
    CLOSED_STATUSES.includes((l['Status'] || '').toLowerCase())).length;
  const conversion = total ? ((admissions / total) * 100).toFixed(1) + '%' : '0%';

  $('kpiTodayLeads').textContent = today;
  $('kpiTotalLeads').textContent = total;
  $('kpiAdmissions').textContent = admissions;
  $('kpiConversion').textContent = conversion;
}

function renderSources(leads) {
  const counts = {};
  leads.forEach(l => {
    const src = l['Lead Source'] || 'Unknown';
    counts[src] = (counts[src] || 0) + 1;
  });
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? entries[0][1] : 1;

  $('sourceBreakdown').innerHTML = entries.length
    ? entries.map(([name, n]) => `
        <div class="source-row">
          <span class="source-name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
          <div class="source-bar-wrap"><div class="source-bar" style="width:${(n / max) * 100}%"></div></div>
          <span class="source-count">${n}</span>
        </div>`).join('')
    : '<p class="muted">No leads yet.</p>';
}

function renderFollowups(followups) {
  // Priority list = P1/P2, not yet completed, sorted P1 first then by date.
  const open = followups
    .filter(f => /^p[12]/i.test((f['Priority'] || '').trim()))
    .filter(f => !['done', 'completed', 'closed'].includes((f['Status'] || '').toLowerCase()))
    .sort((a, b) => (a['Priority'] || '').localeCompare(b['Priority'] || '') ||
                    (a['Followup Date'] || '').localeCompare(b['Followup Date'] || ''));

  $('followupCount').textContent = open.length;
  $('followupBody').innerHTML = open.length
    ? open.slice(0, 25).map(f => {
        const p = (f['Priority'] || '').toUpperCase();
        const badge = p.startsWith('P1') ? 'badge-p1' : 'badge-p2';
        return `<tr>
          <td><span class="badge ${badge}">${escapeHtml(p.split(' ')[0] || p)}</span></td>
          <td>${escapeHtml(f['Candidate Name'] || '')}</td>
          <td><a href="tel:${escapeHtml(f['Phone Number'] || '')}">${escapeHtml(f['Phone Number'] || '')}</a></td>
          <td>${escapeHtml(f['Followup Date'] || '')}</td>
          <td>${escapeHtml(f['Assigned Counselor'] || '')}</td>
        </tr>`;
      }).join('')
    : '<tr><td colspan="5" class="muted">No open P1/P2 follow-ups 🎉</td></tr>';
}

function renderLeads(leads) {
  const latest = leads.slice(-10).reverse(); // newest rows are at the bottom
  $('leadsBody').innerHTML = latest.length
    ? latest.map(l => {
        const status = (l['Status'] || 'New').trim();
        const cls = CLOSED_STATUSES.includes(status.toLowerCase()) ? 'badge-closed' : 'badge-open';
        return `<tr>
          <td>${escapeHtml(l['Lead ID'] || '—')}</td>
          <td>${escapeHtml(l['Candidate Name'] || '')}</td>
          <td>${escapeHtml(l['Course Interested'] || '')}</td>
          <td><span class="badge ${cls}">${escapeHtml(status)}</span></td>
        </tr>`;
      }).join('')
    : '<tr><td colspan="4" class="muted">No leads yet.</td></tr>';
}

/* ============================ Refresh loop ============================ */

async function refresh() {
  const leadsOk = isConfigured(config.leadRegisterCsvUrl);
  const followOk = isConfigured(config.followupTrackerCsvUrl);

  if (!leadsOk && !followOk) {
    showBanner('⚙️ Setup pending: publish your Google Sheets to the web as CSV and paste the URLs into dashboard_ui/config.js (see README Step 1 & 4).');
    return;
  }

  try {
    hideBanner();
    if (leadsOk) {
      const leads = await fetchCsv(config.leadRegisterCsvUrl);
      renderKpis(leads);
      renderSources(leads);
      renderLeads(leads);
    }
    if (followOk) {
      const followups = await fetchCsv(config.followupTrackerCsvUrl);
      renderFollowups(followups);
    }
    $('lastUpdated').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
  } catch (err) {
    console.error(err);
    showBanner('⚠️ Could not load sheet data: ' + err.message +
      ' — check the CSV URLs are published and public.', true);
  }
}

/* ============================ Init ============================ */

document.addEventListener('DOMContentLoaded', () => {
  // Branding
  document.title = '⚓ ' + config.branding.title + ' — Sales Dashboard';

  // Quick Add button
  const quickAdd = $('quickAddBtn');
  if (isConfigured(config.quickAddFormUrl)) quickAdd.href = config.quickAddFormUrl;
  else quickAdd.addEventListener('click', e => {
    e.preventDefault();
    alert('Add your Google Form URL to dashboard_ui/config.js (quickAddFormUrl) first.');
  });

  // Manual refresh
  $('refreshBtn').addEventListener('click', refresh);

  // First load + auto refresh every 5 minutes
  refresh();
  setInterval(refresh, config.refreshInterval || 300000);
});
