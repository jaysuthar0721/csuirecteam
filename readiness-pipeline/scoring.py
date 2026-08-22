"""
Composite readiness score, built from personal rolling baselines rather
than population norms. This is a reasonable starting formula, not a
clinical instrument, tune the weights once you have a month of your own
data to look back on.

Weights:
  50% HRV vs. your own baseline (most sensitive recovery signal)
  25% resting HR vs. your own baseline (inverted: lower is better)
  25% sleep (duration vs. target + deep/REM proportion)

Prior-day strain (dailyHeartRateZones) is reported alongside the score as
context rather than folded into the number, since a hard training day
lowering "readiness" the same day it happened is misleading. It's most
useful for you to eyeball next to tomorrow's HRV dip.
"""

import statistics


def _mean_stdev(values):
    values = [v for v in values if v is not None]
    if len(values) < 5:
        return None, None  # not enough history to trust a baseline yet
    mean = statistics.mean(values)
    stdev = statistics.pstdev(values) or 1e-6  # avoid div by zero
    return mean, stdev


def _z_to_score(z, invert=False):
    if z is None:
        return None
    if invert:
        z = -z
    score = 50 + 25 * z
    return max(0, min(100, score))


def compute_baseline(history_rows, field):
    values = [row.get(field) for row in history_rows]
    return _mean_stdev(values)


def sleep_component_score(total_sleep_min, deep_min, rem_min, target_sleep_hours):
    if not total_sleep_min:
        return None
    target_min = target_sleep_hours * 60
    duration_score = min(100, (total_sleep_min / target_min) * 100)

    quality_ratio = (deep_min + rem_min) / total_sleep_min if total_sleep_min else 0
    # ~40-50% deep+REM is typical for a good night; scale so ~40% -> ~100.
    quality_score = min(100, quality_ratio * 250)

    return 0.6 * duration_score + 0.4 * quality_score


def compute_readiness(today_row, history_rows, target_sleep_hours=8.0):
    """
    today_row: dict for the day being scored (from db.get_day)
    history_rows: prior days used to build the rolling baseline
                  (should NOT include today_row)
    Returns a dict with the overall score and its components, or None
    fields where there isn't enough data yet.
    """
    hrv_mean, hrv_sd = compute_baseline(history_rows, "hrv_rmssd_ms")
    rhr_mean, rhr_sd = compute_baseline(history_rows, "resting_hr_bpm")

    hrv_z = (
        (today_row["hrv_rmssd_ms"] - hrv_mean) / hrv_sd
        if today_row.get("hrv_rmssd_ms") is not None and hrv_mean is not None
        else None
    )
    rhr_z = (
        (today_row["resting_hr_bpm"] - rhr_mean) / rhr_sd
        if today_row.get("resting_hr_bpm") is not None and rhr_mean is not None
        else None
    )

    hrv_score = _z_to_score(hrv_z, invert=False)
    rhr_score = _z_to_score(rhr_z, invert=True)
    sleep_score = sleep_component_score(
        today_row.get("total_sleep_min"),
        today_row.get("deep_sleep_min") or 0,
        today_row.get("rem_sleep_min") or 0,
        target_sleep_hours,
    )

    components = {"hrv": hrv_score, "resting_hr": rhr_score, "sleep": sleep_score}
    weights = {"hrv": 0.5, "resting_hr": 0.25, "sleep": 0.25}

    available = {k: v for k, v in components.items() if v is not None}
    if not available:
        overall = None
    else:
        weight_sum = sum(weights[k] for k in available)
        overall = sum(available[k] * weights[k] for k in available) / weight_sum

    return {
        "date": today_row.get("date"),
        "overall_score": round(overall, 1) if overall is not None else None,
        "components": {k: (round(v, 1) if v is not None else None) for k, v in components.items()},
        "baselines": {
            "hrv_mean_ms": round(hrv_mean, 1) if hrv_mean else None,
            "hrv_stdev_ms": round(hrv_sd, 2) if hrv_sd else None,
            "resting_hr_mean_bpm": round(rhr_mean, 1) if rhr_mean else None,
            "resting_hr_stdev_bpm": round(rhr_sd, 2) if rhr_sd else None,
        },
        "prior_day_strain_minutes": today_row.get("strain_minutes"),
        "days_in_baseline": len(history_rows),
    }
