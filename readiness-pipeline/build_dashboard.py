"""
Reads readiness_log.jsonl and (re)writes dashboard.html, a fully static,
dependency-free page you open with a plain double-click, no server needed.

Run standalone any time:  python build_dashboard.py
sync_daily.py also calls build() automatically after every sync.
"""

import json
import os
from datetime import datetime, timezone

from svg_charts import gauge_svg, trend_svg, band_color, band_label, INK

CSS = """
:root {
  --paper: #EDEAE3;
  --paper-line: #D9D4C8;
  --ink: #1B2430;
  --ink-soft: #5B6472;
  --nominal: #2E7D6B;
  --caution: #C97A2E;
  --critical: #B33F3F;
  --ref: #3B5BA5;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 32px 20px 60px;
  background: var(--paper);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
.wrap { max-width: 900px; margin: 0 auto; }
header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 10px;
  margin-bottom: 4px;
}
.wrap > .rule2 {
  border-top: 1px solid var(--ink);
  opacity: 0.4;
  margin-bottom: 28px;
}
h1 {
  font-size: 15px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin: 0;
  font-weight: 700;
}
.meta {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--ink-soft);
  text-align: right;
}
.panel {
  border: 1px solid var(--ink);
  background: rgba(255,255,255,0.35);
  padding: 16px 18px;
  margin-bottom: 20px;
}
.panel-label {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 0 0 8px 0;
  font-weight: 600;
}
.hero { display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }
.hero-gauge { flex: 1 1 420px; min-width: 280px; }
.hero-status { flex: 0 0 auto; text-align: right; }
.band-tag {
  display: inline-block;
  font-family: ui-monospace, monospace;
  font-size: 13px;
  letter-spacing: 0.08em;
  font-weight: 700;
  padding: 4px 10px;
  border: 1px solid currentColor;
}
.hero-date { font-family: ui-monospace, monospace; font-size: 11px; color: var(--ink-soft); margin-top: 6px; }
.coach-note {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.5;
  border-left: 2px solid var(--ink);
  padding-left: 10px;
  color: var(--ink);
}
.components {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
.trends { display: grid; grid-template-columns: 1fr; gap: 20px; }
table {
  width: 100%;
  border-collapse: collapse;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 11.5px;
}
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--paper-line); white-space: nowrap; }
th { color: var(--ink-soft); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; font-size: 10px; }
td.note { white-space: normal; color: var(--ink-soft); font-family: -apple-system, sans-serif; font-size: 12px; }
tr:hover td { background: rgba(59,91,165,0.06); }
footer {
  margin-top: 28px;
  font-family: ui-monospace, monospace;
  font-size: 10.5px;
  color: var(--ink-soft);
  border-top: 1px solid var(--paper-line);
  padding-top: 10px;
}
.empty {
  border: 1px dashed var(--ink-soft);
  padding: 40px 20px;
  text-align: center;
  font-family: ui-monospace, monospace;
  color: var(--ink-soft);
}
"""


def _fmt_minutes(mins):
    if mins is None:
        return None
    h, m = divmod(int(round(mins)), 60)
    return f"{h}h{m:02d}m"


def load_entries(log_path="readiness_log.jsonl"):
    entries = []
    if not os.path.exists(log_path):
        return entries
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    by_date = {e["date"]: e for e in entries if e.get("date")}
    return [by_date[d] for d in sorted(by_date)]


def _load_target_sleep_hours():
    try:
        with open("config.json") as f:
            return json.load(f).get("target_sleep_hours", 8.0)
    except Exception:
        return 8.0


def _empty_state_html():
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Readiness - awaiting first sync</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>Readiness Log</h1><div class="meta">STANDBY</div></header>
<div class="rule2"></div>
<div class="empty">
  NO-GO -- no logged data yet.<br><br>
  Run <strong>python sync_daily.py</strong> after your Fitbit Air has synced
  at least one night to the Google Health app, then reload this page.
</div>
</div></body></html>"""


def build(log_path="readiness_log.jsonl", out_path="dashboard.html", history_window=30):
    entries = load_entries(log_path)
    html = _empty_state_html() if not entries else _render(entries, history_window)
    with open(out_path, "w") as f:
        f.write(html)
    return out_path


def _render(entries, history_window):
    recent = entries[-history_window:]
    latest = entries[-1]
    target_sleep_hours = _load_target_sleep_hours()

    dates = [e.get("date", "") for e in recent]
    overall = [e.get("overall_score") for e in recent]
    hrv_raw = [e.get("raw", {}).get("hrv_rmssd_ms") for e in recent]
    rhr_raw = [e.get("raw", {}).get("resting_hr_bpm") for e in recent]
    sleep_hours = [
        (e.get("raw", {}).get("total_sleep_min") / 60.0)
        if e.get("raw", {}).get("total_sleep_min") is not None
        else None
        for e in recent
    ]

    latest_score = latest.get("overall_score")
    latest_baselines = latest.get("baselines", {})
    latest_raw = latest.get("raw", {})
    hrv_base = latest_baselines.get("hrv_mean_ms")
    rhr_base = latest_baselines.get("resting_hr_mean_bpm")

    hero_gauge = gauge_svg(latest_score, width=680, height=110, big=True)

    hrv_detail = (
        f"{latest_raw.get('hrv_rmssd_ms'):.0f}ms / baseline {hrv_base:.0f}ms"
        if latest_raw.get("hrv_rmssd_ms") is not None and hrv_base is not None
        else None
    )
    rhr_detail = (
        f"{latest_raw.get('resting_hr_bpm'):.0f}bpm / baseline {rhr_base:.0f}bpm"
        if latest_raw.get("resting_hr_bpm") is not None and rhr_base is not None
        else None
    )
    sleep_min = latest_raw.get("total_sleep_min")
    sleep_detail = (
        f"{_fmt_minutes(sleep_min)} / target {target_sleep_hours:.0f}h"
        if sleep_min is not None
        else None
    )

    hrv_gauge = gauge_svg(latest.get("components", {}).get("hrv"), detail=hrv_detail, width=280, height=78)
    rhr_gauge = gauge_svg(latest.get("components", {}).get("resting_hr"), detail=rhr_detail, width=280, height=78)
    sleep_gauge = gauge_svg(latest.get("components", {}).get("sleep"), detail=sleep_detail, width=280, height=78)

    overall_trend = trend_svg(dates, overall, baseline=60, unit="", color=INK)
    hrv_trend = trend_svg(dates, hrv_raw, baseline=hrv_base, unit="ms", color=INK)
    rhr_trend = trend_svg(dates, rhr_raw, baseline=rhr_base, unit="bpm", color=INK)
    sleep_trend = trend_svg(dates, sleep_hours, baseline=target_sleep_hours, unit="h", color=INK)

    color = band_color(latest_score)
    label = band_label(latest_score)
    days_baseline = latest.get("days_in_baseline", 0)

    coach_html = ""
    note = latest.get("coach_note")
    if note and isinstance(note, str) and not note.startswith("("):
        coach_html = f'<div class="panel"><div class="coach-note">{_esc(note)}</div></div>'

    table_rows_html = "".join(_table_row(e) for e in reversed(recent))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Readiness - {latest.get('date','')}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head>
<body><div class="wrap">

<header>
  <h1>Readiness Log</h1>
  <div class="meta">{len(entries)} DAYS LOGGED &middot; GENERATED {_now_str()}</div>
</header>
<div class="rule2"></div>

<div class="panel hero">
  <div class="hero-gauge">
    <p class="panel-label">Overall readiness &mdash; {latest.get('date','')}</p>
    {hero_gauge}
  </div>
  <div class="hero-status">
    <span class="band-tag" style="color:{color}">{label}</span>
    <div class="hero-date">{days_baseline} DAYS IN BASELINE</div>
  </div>
</div>
{coach_html}

<div class="components">
  <div class="component panel">
    <p class="panel-label">HRV</p>
    {hrv_gauge}
  </div>
  <div class="component panel">
    <p class="panel-label">Resting HR</p>
    {rhr_gauge}
  </div>
  <div class="component panel">
    <p class="panel-label">Sleep</p>
    {sleep_gauge}
  </div>
</div>

<div class="panel trends">
  <div>
    <p class="panel-label">Readiness score &mdash; last {len(recent)} days</p>
    {overall_trend}
  </div>
  <div>
    <p class="panel-label">HRV (ms) &mdash; last {len(recent)} days</p>
    {hrv_trend}
  </div>
  <div>
    <p class="panel-label">Resting HR (bpm) &mdash; last {len(recent)} days</p>
    {rhr_trend}
  </div>
  <div>
    <p class="panel-label">Sleep (hours) &mdash; last {len(recent)} days</p>
    {sleep_trend}
  </div>
</div>

<div class="panel">
  <p class="panel-label">Log</p>
  <table>
    <thead><tr>
      <th>Date</th><th>Score</th><th>Band</th><th>HRV</th><th>RHR</th><th>Sleep</th><th>Note</th>
    </tr></thead>
    <tbody>
      {table_rows_html}
    </tbody>
  </table>
</div>

<footer>Personal telemetry, not a medical device. Readiness weights: 50% HRV / 25% resting HR / 25% sleep, vs. your own rolling baseline.</footer>

</div></body></html>"""


def _table_row(e):
    raw = e.get("raw", {})
    s = e.get("overall_score")
    hrv_v = raw.get("hrv_rmssd_ms")
    rhr_v = raw.get("resting_hr_bpm")
    sleep_v = raw.get("total_sleep_min")
    note_text = e.get("coach_note") or ""
    if isinstance(note_text, str) and note_text.startswith("("):
        note_text = ""
    if len(note_text) > 60:
        note_text = note_text[:57] + "..."

    score_cell = f"{s:.0f}" if s is not None else "--"
    band = band_label(s) if s is not None else "--"
    color = band_color(s)
    hrv_cell = f"{hrv_v:.0f}" if hrv_v is not None else "--"
    rhr_cell = f"{rhr_v:.0f}" if rhr_v is not None else "--"
    sleep_cell = _fmt_minutes(sleep_v) if sleep_v is not None else "--"

    return (
        "<tr>"
        f"<td>{e.get('date','')}</td>"
        f"<td>{score_cell}</td>"
        f'<td style="color:{color}">{band}</td>'
        f"<td>{hrv_cell}</td>"
        f"<td>{rhr_cell}</td>"
        f"<td>{sleep_cell}</td>"
        f'<td class="note">{_esc(note_text)}</td>'
        "</tr>"
    )


def _esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
