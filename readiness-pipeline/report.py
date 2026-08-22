"""
Turns the raw scoring dict into something you'd actually want to read
over coffee, instead of a JSON dump.
"""


def _format_minutes(mins):
    if mins is None:
        return "n/a"
    h, m = divmod(int(round(mins)), 60)
    return f"{h}h{m:02d}m"


def _overall_band(score):
    if score is None:
        return "Not enough baseline data yet"
    if score >= 80:
        return "Green light, good day to push"
    if score >= 60:
        return "Normal, train as planned"
    if score >= 40:
        return "Caution, consider an easier session"
    return "Recover, prioritize rest today"


def _raw_direction(raw, baseline_mean, baseline_stdev):
    """Describes the raw value vs. baseline, independent of whether that
    direction is good or bad (that's what the score/band already conveys)."""
    if raw is None or baseline_mean is None:
        return "no data"
    stdev = baseline_stdev or 1e-6
    z = (raw - baseline_mean) / stdev
    if z > 0.2:
        return "above baseline"
    if z < -0.2:
        return "below baseline"
    return "near baseline"


def print_report(result, today_row, coach_note=None):
    date = result.get("date", "?")
    score = result.get("overall_score")
    components = result.get("components", {})
    baselines = result.get("baselines", {})
    strain = result.get("prior_day_strain_minutes")
    n_baseline_days = result.get("days_in_baseline", 0)

    score_str = f"{score:.0f}/100" if score is not None else "--/100"

    print()
    print(f"Readiness — {date}")
    print("=" * (13 + len(date)))
    print()
    print(f"  {score_str}   {_overall_band(score)}")
    print()

    hrv = components.get("hrv")
    rhr = components.get("resting_hr")
    sleep = components.get("sleep")

    hrv_raw = today_row.get("hrv_rmssd_ms")
    hrv_base = baselines.get("hrv_mean_ms")
    hrv_detail = f"{hrv_raw:.0f}ms" if hrv_raw is not None else "n/a"
    if hrv_base is not None and hrv_raw is not None:
        hrv_detail += f" (baseline {hrv_base:.0f}ms)"

    rhr_raw = today_row.get("resting_hr_bpm")
    rhr_base = baselines.get("resting_hr_mean_bpm")
    rhr_detail = f"{rhr_raw:.0f}bpm" if rhr_raw is not None else "n/a"
    if rhr_base is not None and rhr_raw is not None:
        rhr_detail += f" (baseline {rhr_base:.0f}bpm)"

    sleep_detail = _format_minutes(today_row.get("total_sleep_min"))

    def line(label, score_val, direction, detail):
        score_disp = f"{score_val:3.0f}" if score_val is not None else " --"
        print(f"  {label:<11} {score_disp}   {direction:<15} {detail}")

    hrv_dir = _raw_direction(hrv_raw, hrv_base, baselines.get("hrv_stdev_ms"))
    rhr_dir = _raw_direction(rhr_raw, rhr_base, baselines.get("resting_hr_stdev_bpm"))
    sleep_dir = "vs 8h target" if sleep is not None else "no data"

    line("HRV", hrv, hrv_dir, hrv_detail)
    line("Resting HR", rhr, rhr_dir, rhr_detail)
    line("Sleep", sleep, sleep_dir, sleep_detail)

    print()
    if strain is not None:
        print(f"  Yesterday's elevated-HR time: {strain:.0f} min")

    if n_baseline_days < 14:
        print(f"  ({n_baseline_days} days of baseline so far, stabilizes around ~30)")

    if coach_note:
        print()
        print(f"  Coach: {coach_note}")
    print()
