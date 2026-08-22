"""
Run this daily (cron/Task Scheduler) after you wake up, once your Fitbit
Air has synced overnight data to the Google Health app.

    python sync_daily.py

What it does:
1. Pulls the last (baseline_window_days + 3) days of HRV, resting HR,
   sleep, and heart rate zone data from the Google Health API.
2. Upserts it into readiness.db (SQLite).
3. Computes yesterday's readiness score against your rolling baseline.
4. Optionally asks Claude for a short coaching note (if ANTHROPIC_API_KEY
   is set).
5. Prints the result and appends it to readiness_log.jsonl.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import db
from google_health_client import GoogleHealthClient
from parsers import (
    parse_daily_hrv,
    parse_daily_resting_hr,
    parse_sleep_sessions,
    parse_daily_heart_rate_zones,
)
from scoring import compute_readiness
from report import print_report


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def sync_range(client, conn, start_date, end_date, debug=False):
    """start_date/end_date are date objects; end_date is exclusive-ish (we
    add a day of padding on the API call to be safe with UTC boundaries)."""
    start_iso = f"{start_date.isoformat()}T00:00:00Z"
    end_iso = f"{(end_date + timedelta(days=1)).isoformat()}T00:00:00Z"

    hrv_points = client.list_data_points("daily-heart-rate-variability", start_iso, end_iso)
    rhr_points = client.list_data_points("daily-resting-heart-rate", start_iso, end_iso)
    sleep_points = client.list_data_points("sleep", start_iso, end_iso)
    zone_points = client.list_data_points("daily-heart-rate-zones", start_iso, end_iso)

    if debug:
        for label, pts in [
            ("hrv", hrv_points), ("rhr", rhr_points),
            ("sleep", sleep_points), ("zones", zone_points),
        ]:
            print(f"--- raw {label} sample ---")
            print(json.dumps(pts[0] if pts else {}, indent=2))

    hrv_by_date = parse_daily_hrv(hrv_points)
    rhr_by_date = parse_daily_resting_hr(rhr_points)
    sleep_by_date = parse_sleep_sessions(sleep_points)
    strain_by_date = parse_daily_heart_rate_zones(zone_points)

    all_dates = set(hrv_by_date) | set(rhr_by_date) | set(sleep_by_date) | set(strain_by_date)
    for date in all_dates:
        fields = {}
        if date in hrv_by_date:
            fields["hrv_rmssd_ms"] = hrv_by_date[date]
        if date in rhr_by_date:
            fields["resting_hr_bpm"] = rhr_by_date[date]
        if date in sleep_by_date:
            fields.update(sleep_by_date[date])
        if date in strain_by_date:
            fields["strain_minutes"] = strain_by_date[date]
        db.upsert_day(conn, date, **fields)

    return len(all_dates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="print a sample raw API response per data type")
    parser.add_argument("--score-date", default=None, help="YYYY-MM-DD to score instead of yesterday")
    args = parser.parse_args()

    config = load_config()
    baseline_window = config.get("baseline_window_days", 30)
    target_sleep_hours = config.get("target_sleep_hours", 8.0)

    client = GoogleHealthClient()
    conn = db.connect()

    today = datetime.now(timezone.utc).date()
    score_date = (
        datetime.strptime(args.score_date, "%Y-%m-%d").date()
        if args.score_date
        else today - timedelta(days=1)
    )
    pull_start = score_date - timedelta(days=baseline_window + 3)

    n_days_synced = sync_range(client, conn, pull_start, today, debug=args.debug)
    print(f"Synced {n_days_synced} days of data ({pull_start} to {today}).")

    today_row = db.get_day(conn, score_date.isoformat())
    if not today_row:
        print(f"No data found for {score_date}. Has your device synced yet?")
        return

    history = db.get_recent_days(conn, baseline_window, before_date=score_date.isoformat())
    result = compute_readiness(today_row, history, target_sleep_hours)

    note = None
    try:
        from coach import generate_note
        note = generate_note(result)
    except Exception as e:
        note = f"(coaching note skipped: {e})"

    print_report(result, today_row, coach_note=note)

    with open("readiness_log.jsonl", "a") as f:
        log_entry = dict(result)
        log_entry["coach_note"] = note
        log_entry["raw"] = {
            "hrv_rmssd_ms": today_row.get("hrv_rmssd_ms"),
            "resting_hr_bpm": today_row.get("resting_hr_bpm"),
            "total_sleep_min": today_row.get("total_sleep_min"),
            "deep_sleep_min": today_row.get("deep_sleep_min"),
            "rem_sleep_min": today_row.get("rem_sleep_min"),
        }
        f.write(json.dumps(log_entry) + "\n")

    from build_dashboard import build
    build()

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "setlog-integration"))
    from publish_to_setlog import publish as publish_to_setlog
    publish_to_setlog(log_path="readiness_log.jsonl")


if __name__ == "__main__":
    main()
