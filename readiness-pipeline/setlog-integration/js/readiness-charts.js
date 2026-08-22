/**
 * Renders the readiness dashboard from decrypted log entries.
 * Direct JS port of svg_charts.py / build_dashboard.py — same gauge and
 * strip-chart visual language, so it looks identical to the local
 * dashboard.html. Pure string-building (testable in Node), DOM attachment
 * happens only in renderInto().
 */

const INK = "#1B2430";
const INK_SOFT = "#5B6472";
const PAPER_LINE = "#D9D4C8";
const NOMINAL = "#2E7D6B";
const CAUTION = "#C97A2E";
const CRITICAL = "#B33F3F";
const REF_LINE = "#3B5BA5";
const GHOST = "#B7B2A6";

function bandColor(score) {
  if (score === null || score === undefined) return GHOST;
  if (score >= 60) return NOMINAL;
  if (score >= 40) return CAUTION;
  return CRITICAL;
}

function bandLabel(score) {
  if (score === null || score === undefined) return "NO DATA";
  if (score >= 80) return "GREEN LIGHT";
  if (score >= 60) return "NOMINAL";
  if (score >= 40) return "CAUTION";
  return "RECOVER";
}

function fmtMinutes(mins) {
  if (mins === null || mins === undefined) return null;
  const total = Math.round(mins);
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${h}h${String(m).padStart(2, "0")}m`;
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function gaugeSvg(value, { detail = null, width = 640, height = 88, big = false } = {}) {
  const padL = 14, padR = 14;
  const trackY = height * (big ? 0.42 : 0.38);
  const trackH = big ? 14 : 10;
  const trackW = width - padL - padR;
  const xAt = (v) => padL + (v / 100) * trackW;

  const zones = [
    [0, 40, CRITICAL],
    [40, 60, CAUTION],
    [60, 100, NOMINAL],
  ];
  const zoneRects = zones
    .map(
      ([a, b, color]) =>
        `<rect x="${xAt(a).toFixed(1)}" y="${trackY.toFixed(1)}" width="${(xAt(b) - xAt(a)).toFixed(1)}" height="${trackH}" fill="${color}" opacity="0.22" />`
    )
    .join("");

  const ticks = [0, 20, 40, 60, 80, 100]
    .map(
      (t) =>
        `<line x1="${xAt(t).toFixed(1)}" y1="${(trackY - 4).toFixed(1)}" x2="${xAt(t).toFixed(1)}" y2="${(trackY + trackH + 4).toFixed(1)}" stroke="${INK_SOFT}" stroke-width="1" opacity="0.5" />` +
        `<text x="${xAt(t).toFixed(1)}" y="${(trackY + trackH + 16).toFixed(1)}" font-size="9" fill="${INK_SOFT}" text-anchor="middle" font-family="ui-monospace,monospace">${t}</text>`
    )
    .join("");

  const frame = `<rect x="${padL}" y="${trackY.toFixed(1)}" width="${trackW.toFixed(1)}" height="${trackH}" fill="none" stroke="${INK}" stroke-width="1.25" />`;

  let marker = "";
  let numberStr = "--";
  if (value !== null && value !== undefined) {
    const v = Math.max(0, Math.min(100, value));
    const mx = xAt(v);
    marker =
      `<polygon points="${(mx - 5).toFixed(1)},${(trackY - 8).toFixed(1)} ${(mx + 5).toFixed(1)},${(trackY - 8).toFixed(1)} ${mx.toFixed(1)},${(trackY - 1).toFixed(1)}" fill="${INK}" />` +
      `<line x1="${mx.toFixed(1)}" y1="${(trackY - 8).toFixed(1)}" x2="${mx.toFixed(1)}" y2="${(trackY - 20).toFixed(1)}" stroke="${INK}" stroke-width="1" stroke-dasharray="2,2" />`;
    numberStr = v.toFixed(0);
  }

  const numSize = big ? 34 : 22;
  const numY = big ? 30 : 20;
  const numberEl = `<text x="${padL}" y="${numY}" font-size="${numSize}" font-weight="600" fill="${INK}" font-family="ui-monospace,monospace">${numberStr}</text>`;

  const detailEl = detail
    ? `<text x="${width - padR}" y="${numY - 2}" font-size="11" fill="${INK_SOFT}" text-anchor="end" font-family="ui-monospace,monospace">${esc(detail)}</text>`
    : "";

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg">${numberEl}${detailEl}${zoneRects}${frame}${ticks}${marker}</svg>`;
}

function niceTicks(lo, hi, n = 3) {
  if (lo === hi) {
    lo -= 1;
    hi += 1;
  }
  const step = (hi - lo) / n;
  return Array.from({ length: n + 1 }, (_, i) => lo + step * i);
}

function trendSvg(dates, values, { baseline = null, width = 720, height = 150, color = INK } = {}) {
  const padL = 40, padR = 14, padT = 14, padB = 24;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const present = values.filter((v) => v !== null && v !== undefined);
  if (present.length === 0) {
    return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg"><text x="${width / 2}" y="${height / 2}" font-size="12" fill="${GHOST}" text-anchor="middle" font-family="ui-monospace,monospace">NO DATA YET</text></svg>`;
  }

  let lo = Math.min(...present), hi = Math.max(...present);
  if (baseline !== null && baseline !== undefined) {
    lo = Math.min(lo, baseline);
    hi = Math.max(hi, baseline);
  }
  const span = hi - lo || 1;
  lo -= span * 0.15;
  hi += span * 0.15;

  const n = values.length;
  const xAt = (i) => padL + (i / Math.max(1, n - 1)) * plotW;
  const yAt = (v) => padT + plotH - ((v - lo) / (hi - lo)) * plotH;

  const grid = niceTicks(lo, hi, 3)
    .map(
      (t) =>
        `<line x1="${padL}" y1="${yAt(t).toFixed(1)}" x2="${width - padR}" y2="${yAt(t).toFixed(1)}" stroke="${PAPER_LINE}" stroke-width="1" />` +
        `<text x="${padL - 6}" y="${(yAt(t) + 3).toFixed(1)}" font-size="9" fill="${INK_SOFT}" text-anchor="end" font-family="ui-monospace,monospace">${t.toFixed(0)}</text>`
    )
    .join("");

  let baselineLine = "";
  if (baseline !== null && baseline !== undefined) {
    const by = yAt(baseline);
    baselineLine =
      `<line x1="${padL}" y1="${by.toFixed(1)}" x2="${width - padR}" y2="${by.toFixed(1)}" stroke="${REF_LINE}" stroke-width="1.25" stroke-dasharray="4,3" />` +
      `<text x="${width - padR}" y="${(by - 4).toFixed(1)}" font-size="9" fill="${REF_LINE}" text-anchor="end" font-family="ui-monospace,monospace">baseline ${baseline.toFixed(0)}</text>`;
  }

  let d = "";
  let started = false;
  const points = [];
  values.forEach((v, i) => {
    if (v === null || v === undefined) {
      started = false;
      return;
    }
    const x = xAt(i), y = yAt(v);
    d += (started ? "L" : "M") + `${x.toFixed(1)},${y.toFixed(1)} `;
    started = true;
    points.push(`<rect x="${(x - 2).toFixed(1)}" y="${(y - 2).toFixed(1)}" width="4" height="4" fill="${color}" />`);
  });
  const lineEl = `<path d="${d.trim()}" fill="none" stroke="${color}" stroke-width="1.75" />`;

  const labelIdxs = [...new Set([0, Math.floor(n / 2), n - 1])].sort((a, b) => a - b);
  const xLabels = labelIdxs
    .map(
      (i) =>
        `<text x="${xAt(i).toFixed(1)}" y="${height - 6}" font-size="9" fill="${INK_SOFT}" text-anchor="middle" font-family="ui-monospace,monospace">${(dates[i] || "").slice(5)}</text>`
    )
    .join("");

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg">${grid}${baselineLine}${lineEl}${points.join("")}${xLabels}</svg>`;
}

function tableRow(e) {
  const raw = e.raw || {};
  const s = e.overall_score;
  const hrvV = raw.hrv_rmssd_ms;
  const rhrV = raw.resting_hr_bpm;
  const sleepV = raw.total_sleep_min;
  let note = e.coach_note || "";
  if (typeof note === "string" && note.startsWith("(")) note = "";
  if (note.length > 60) note = note.slice(0, 57) + "...";

  const scoreCell = s !== null && s !== undefined ? s.toFixed(0) : "--";
  const band = s !== null && s !== undefined ? bandLabel(s) : "--";
  const color = bandColor(s);
  const hrvCell = hrvV !== null && hrvV !== undefined ? hrvV.toFixed(0) : "--";
  const rhrCell = rhrV !== null && rhrV !== undefined ? rhrV.toFixed(0) : "--";
  const sleepCell = fmtMinutes(sleepV) || "--";

  return (
    "<tr>" +
    `<td>${e.date || ""}</td>` +
    `<td>${scoreCell}</td>` +
    `<td style="color:${color}">${band}</td>` +
    `<td>${hrvCell}</td>` +
    `<td>${rhrCell}</td>` +
    `<td>${sleepCell}</td>` +
    `<td class="note">${esc(note)}</td>` +
    "</tr>"
  );
}

/**
 * Builds the full dashboard body (everything inside <div class="wrap">…</div>,
 * minus the outer HTML shell — the shell/CSS lives in readiness.html so it
 * can share styling with the rest of SETLOG).
 */
function renderDashboardHTML(entries, { historyWindow = 30, targetSleepHours = 8.0 } = {}) {
  if (!entries || entries.length === 0) {
    return `<div class="empty">NO-GO &mdash; no logged data yet.</div>`;
  }

  const recent = entries.slice(-historyWindow);
  const latest = entries[entries.length - 1];

  const dates = recent.map((e) => e.date || "");
  const overall = recent.map((e) => (e.overall_score !== undefined ? e.overall_score : null));
  const hrvRaw = recent.map((e) => {
    const v = (e.raw || {}).hrv_rmssd_ms;
    return v !== undefined ? v : null;
  });
  const rhrRaw = recent.map((e) => {
    const v = (e.raw || {}).resting_hr_bpm;
    return v !== undefined ? v : null;
  });
  const sleepHours = recent.map((e) => {
    const m = (e.raw || {}).total_sleep_min;
    return m !== null && m !== undefined ? m / 60 : null;
  });

  const latestScore = latest.overall_score !== undefined ? latest.overall_score : null;
  const baselines = latest.baselines || {};
  const latestRaw = latest.raw || {};
  const hrvBase = baselines.hrv_mean_ms !== undefined ? baselines.hrv_mean_ms : null;
  const rhrBase = baselines.resting_hr_mean_bpm !== undefined ? baselines.resting_hr_mean_bpm : null;

  const heroGauge = gaugeSvg(latestScore, { width: 680, height: 110, big: true });

  const hrvDetail =
    latestRaw.hrv_rmssd_ms != null && hrvBase != null
      ? `${latestRaw.hrv_rmssd_ms.toFixed(0)}ms / baseline ${hrvBase.toFixed(0)}ms`
      : null;
  const rhrDetail =
    latestRaw.resting_hr_bpm != null && rhrBase != null
      ? `${latestRaw.resting_hr_bpm.toFixed(0)}bpm / baseline ${rhrBase.toFixed(0)}bpm`
      : null;
  const sleepMin = latestRaw.total_sleep_min;
  const sleepDetail =
    sleepMin != null ? `${fmtMinutes(sleepMin)} / target ${targetSleepHours.toFixed(0)}h` : null;

  const comp = latest.components || {};
  const hrvGauge = gaugeSvg(comp.hrv !== undefined ? comp.hrv : null, { detail: hrvDetail, width: 280, height: 78 });
  const rhrGauge = gaugeSvg(comp.resting_hr !== undefined ? comp.resting_hr : null, { detail: rhrDetail, width: 280, height: 78 });
  const sleepGauge = gaugeSvg(comp.sleep !== undefined ? comp.sleep : null, { detail: sleepDetail, width: 280, height: 78 });

  const overallTrend = trendSvg(dates, overall, { baseline: 60 });
  const hrvTrend = trendSvg(dates, hrvRaw, { baseline: hrvBase });
  const rhrTrend = trendSvg(dates, rhrRaw, { baseline: rhrBase });
  const sleepTrend = trendSvg(dates, sleepHours, { baseline: targetSleepHours });

  const color = bandColor(latestScore);
  const label = bandLabel(latestScore);
  const daysBaseline = latest.days_in_baseline || 0;

  let coachHtml = "";
  const note = latest.coach_note;
  if (note && typeof note === "string" && !note.startsWith("(")) {
    coachHtml = `<div class="panel"><div class="coach-note">${esc(note)}</div></div>`;
  }

  const tableRowsHtml = [...recent].reverse().map(tableRow).join("");

  return `
<div class="panel hero">
  <div class="hero-gauge">
    <p class="panel-label">Overall readiness &mdash; ${latest.date || ""}</p>
    ${heroGauge}
  </div>
  <div class="hero-status">
    <span class="band-tag" style="color:${color}">${label}</span>
    <div class="hero-date">${daysBaseline} DAYS IN BASELINE</div>
  </div>
</div>
${coachHtml}
<div class="components">
  <div class="component panel"><p class="panel-label">HRV</p>${hrvGauge}</div>
  <div class="component panel"><p class="panel-label">Resting HR</p>${rhrGauge}</div>
  <div class="component panel"><p class="panel-label">Sleep</p>${sleepGauge}</div>
</div>
<div class="panel trends">
  <div><p class="panel-label">Readiness score &mdash; last ${recent.length} days</p>${overallTrend}</div>
  <div><p class="panel-label">HRV (ms) &mdash; last ${recent.length} days</p>${hrvTrend}</div>
  <div><p class="panel-label">Resting HR (bpm) &mdash; last ${recent.length} days</p>${rhrTrend}</div>
  <div><p class="panel-label">Sleep (hours) &mdash; last ${recent.length} days</p>${sleepTrend}</div>
</div>
<div class="panel">
  <p class="panel-label">Log</p>
  <table>
    <thead><tr><th>Date</th><th>Score</th><th>Band</th><th>HRV</th><th>RHR</th><th>Sleep</th><th>Note</th></tr></thead>
    <tbody>${tableRowsHtml}</tbody>
  </table>
</div>`;
}

function renderInto(container, entries, opts) {
  container.innerHTML = renderDashboardHTML(entries, opts);
}

if (typeof module !== "undefined") {
  module.exports = { renderDashboardHTML, renderInto, gaugeSvg, trendSvg, bandColor, bandLabel };
}
