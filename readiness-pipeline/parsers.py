"""
Convert raw Google Health API dataPoint dicts into flat per-day values.

Field names here are taken directly from the API reference
(users.dataTypes.dataPoints). If Google adds/renames fields, print a raw
dataPoint (see sync_daily.py --debug) and adjust the getters below.
"""

from datetime import datetime, timezone


def _google_date_to_iso(date_obj):
    """{'year': 2026, 'month': 4, 'day': 20} -> '2026-04-20'"""
    if not date_obj:
        return None
    return f"{date_obj['year']:04d}-{date_obj['month']:02d}-{date_obj['day']:02d}"


def _civil_or_fallback_date(interval, key):
    """
    key is 'civilStartTime' or 'civilEndTime'. Falls back to parsing the
    matching startTime/endTime timestamp (UTC) if civil time isn't present.
    """
    civil = interval.get(key)
    if civil and civil.get("date"):
        return _google_date_to_iso(civil["date"])
    raw_key = "startTime" if "Start" in key else "endTime"
    raw = interval.get(raw_key)
    if raw:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    return None


def parse_daily_hrv(points):
    """dailyHeartRateVariability -> {date: rmssd_ms}"""
    out = {}
    for p in points:
        d = p.get("dailyHeartRateVariability", {})
        date = _google_date_to_iso(d.get("date"))
        rmssd = d.get("averageHeartRateVariabilityMilliseconds")
        if date and rmssd is not None:
            out[date] = float(rmssd)
    return out


def parse_daily_resting_hr(points):
    """dailyRestingHeartRate -> {date: bpm}"""
    out = {}
    for p in points:
        d = p.get("dailyRestingHeartRate", {})
        date = _google_date_to_iso(d.get("date"))
        bpm = d.get("beatsPerMinute")
        if date and bpm is not None:
            out[date] = float(bpm)
    return out


def parse_sleep_sessions(points):
    """
    sleep -> {date: {total_sleep_min, deep_min, rem_min, light_min, awake_min}}
    Keyed by the wake-up (civilEndTime) date. Naps are skipped.
    Skips sessions rejected by stage processing (i.e. no deep/rem breakdown)
    but still records total sleep time for them.
    """
    out = {}
    for p in points:
        s = p.get("sleep", {})
        meta = s.get("metadata", {})
        if meta.get("nap"):
            continue

        interval = s.get("interval", {})
        date = _civil_or_fallback_date(interval, "civilEndTime")
        if not date:
            continue

        summary = s.get("summary", {})
        total_asleep = float(summary.get("minutesAsleep", 0) or 0)
        awake = float(summary.get("minutesAwake", 0) or 0)

        stage_minutes = {"DEEP": 0.0, "REM": 0.0, "LIGHT": 0.0}
        for stage in summary.get("stagesSummary", []):
            stype = stage.get("type")
            if stype in stage_minutes:
                stage_minutes[stype] += float(stage.get("minutes", 0) or 0)

        # If the same night appears twice (e.g. reconciled + raw), keep the
        # longer session.
        existing = out.get(date)
        if existing and existing["total_sleep_min"] >= total_asleep:
            continue

        out[date] = {
            "total_sleep_min": total_asleep,
            "deep_sleep_min": stage_minutes["DEEP"],
            "rem_sleep_min": stage_minutes["REM"],
            "light_sleep_min": stage_minutes["LIGHT"],
            "awake_min": awake,
        }
    return out


def parse_daily_heart_rate_zones(points):
    """
    dailyHeartRateZones -> {date: minutes_in_cardio_or_peak}

    NOTE: as of the live API, 'daily-heart-rate-zones' dataPoints only carry
    each zone's BPM boundaries (heartRateZones[].heartRateZoneType,
    minBeatsPerMinute, maxBeatsPerMinute) for the day, not time spent in
    each zone, so strain_minutes can't be derived from this endpoint.
    Getting actual per-zone minutes requires the 'active-zone-minutes' data
    type, which needs the 'activity_and_fitness_readonly' OAuth scope (not
    currently requested by this app). Returns {} until that's wired up;
    strain_minutes will just be omitted from the report rather than shown
    as a misleading 0.
    """
    return {}
