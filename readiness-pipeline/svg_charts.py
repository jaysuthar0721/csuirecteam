"""
Hand-rolled SVG generators for the readiness dashboard. No chart library,
no CDN dependency, everything renders offline from a plain file:// open.

Visual language: linear instrument gauges with tick marks and dimension-line
callouts, and strip-chart trend traces on graph-paper backgrounds. Think
flight data recorder / strain-gauge readout rather than a fitness app.
"""

INK = "#1B2430"
INK_SOFT = "#5B6472"
PAPER = "#EDEAE3"
PAPER_LINE = "#D9D4C8"
NOMINAL = "#2E7D6B"
CAUTION = "#C97A2E"
CRITICAL = "#B33F3F"
REF_LINE = "#3B5BA5"
GHOST = "#B7B2A6"


def band_color(score):
    if score is None:
        return GHOST
    if score >= 60:
        return NOMINAL
    if score >= 40:
        return CAUTION
    return CRITICAL


def band_label(score):
    if score is None:
        return "NO DATA"
    if score >= 80:
        return "GREEN LIGHT"
    if score >= 60:
        return "NOMINAL"
    if score >= 40:
        return "CAUTION"
    return "RECOVER"


def gauge_svg(value, detail=None, width=640, height=88, big=False):
    """
    Horizontal 0-100 instrument gauge with red/amber/teal background zones,
    tick marks every 20, and a marker + leader line at the current value.
    `detail` is an optional string shown under the marker (raw units).
    """
    pad_l, pad_r = 14, 14
    track_y = height * 0.42 if big else height * 0.38
    track_h = 14 if big else 10
    track_w = width - pad_l - pad_r

    def x_at(v):
        return pad_l + (v / 100.0) * track_w

    zones = [
        (0, 40, CRITICAL),
        (40, 60, CAUTION),
        (60, 100, NOMINAL),
    ]
    zone_rects = "".join(
        f'<rect x="{x_at(a):.1f}" y="{track_y:.1f}" width="{(x_at(b) - x_at(a)):.1f}" '
        f'height="{track_h}" fill="{color}" opacity="0.22" />'
        for a, b, color in zones
    )

    ticks = "".join(
        f'<line x1="{x_at(t):.1f}" y1="{track_y - 4:.1f}" x2="{x_at(t):.1f}" '
        f'y2="{track_y + track_h + 4:.1f}" stroke="{INK_SOFT}" stroke-width="1" opacity="0.5" />'
        f'<text x="{x_at(t):.1f}" y="{track_y + track_h + 16:.1f}" font-size="9" '
        f'fill="{INK_SOFT}" text-anchor="middle" font-family="ui-monospace,monospace">{t}</text>'
        for t in (0, 20, 40, 60, 80, 100)
    )

    frame = (
        f'<rect x="{pad_l}" y="{track_y:.1f}" width="{track_w:.1f}" height="{track_h}" '
        f'fill="none" stroke="{INK}" stroke-width="1.25" />'
    )

    marker = ""
    number_str = "--"
    if value is not None:
        v = max(0, min(100, value))
        mx = x_at(v)
        marker_h = track_h + 14
        marker = (
            f'<polygon points="{mx-5:.1f},{track_y - 8:.1f} {mx+5:.1f},{track_y - 8:.1f} {mx:.1f},{track_y - 1:.1f}" '
            f'fill="{INK}" />'
            f'<line x1="{mx:.1f}" y1="{track_y - 8:.1f}" x2="{mx:.1f}" y2="{track_y - 20:.1f}" '
            f'stroke="{INK}" stroke-width="1" stroke-dasharray="2,2" />'
        )
        number_str = f"{v:.0f}"

    num_size = 34 if big else 22
    num_y = 30 if big else 20
    number_el = (
        f'<text x="{pad_l}" y="{num_y}" font-size="{num_size}" font-weight="600" '
        f'fill="{INK}" font-family="ui-monospace,monospace">{number_str}</text>'
    )

    detail_el = ""
    if detail:
        detail_el = (
            f'<text x="{width - pad_r}" y="{num_y - 2}" font-size="11" fill="{INK_SOFT}" '
            f'text-anchor="end" font-family="ui-monospace,monospace">{detail}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f"{number_el}{detail_el}{zone_rects}{frame}{ticks}{marker}"
        f"</svg>"
    )


def _nice_ticks(lo, hi, n=4):
    if lo == hi:
        lo -= 1
        hi += 1
    span = hi - lo
    step = span / n
    return [lo + step * i for i in range(n + 1)]


def trend_svg(dates, values, baseline=None, unit="", width=720, height=150, color=INK):
    """
    Strip-chart trend line for a series of (date_str, value|None) pairs.
    `baseline` draws a dashed reference line (e.g. rolling baseline mean).
    """
    pad_l, pad_r, pad_t, pad_b = 40, 14, 14, 24
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    present = [v for v in values if v is not None]
    if not present:
        return (
            f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{width/2}" y="{height/2}" font-size="12" fill="{GHOST}" '
            f'text-anchor="middle" font-family="ui-monospace,monospace">NO DATA YET</text>'
            f"</svg>"
        )

    lo, hi = min(present), max(present)
    if baseline is not None:
        lo, hi = min(lo, baseline), max(hi, baseline)
    span = (hi - lo) or 1
    lo -= span * 0.15
    hi += span * 0.15

    n = len(values)

    def x_at(i):
        return pad_l + (i / max(1, n - 1)) * plot_w

    def y_at(v):
        return pad_t + plot_h - ((v - lo) / (hi - lo)) * plot_h

    grid_ticks = _nice_ticks(lo, hi, 3)
    grid = "".join(
        f'<line x1="{pad_l}" y1="{y_at(t):.1f}" x2="{width - pad_r}" y2="{y_at(t):.1f}" '
        f'stroke="{PAPER_LINE}" stroke-width="1" />'
        f'<text x="{pad_l - 6}" y="{y_at(t)+3:.1f}" font-size="9" fill="{INK_SOFT}" '
        f'text-anchor="end" font-family="ui-monospace,monospace">{t:.0f}</text>'
        for t in grid_ticks
    )

    baseline_line = ""
    if baseline is not None:
        by = y_at(baseline)
        baseline_line = (
            f'<line x1="{pad_l}" y1="{by:.1f}" x2="{width - pad_r}" y2="{by:.1f}" '
            f'stroke="{REF_LINE}" stroke-width="1.25" stroke-dasharray="4,3" />'
            f'<text x="{width - pad_r}" y="{by - 4:.1f}" font-size="9" fill="{REF_LINE}" '
            f'text-anchor="end" font-family="ui-monospace,monospace">baseline {baseline:.0f}{unit}</text>'
        )

    segments = []
    points = []
    path_started = False
    d = ""
    for i, v in enumerate(values):
        if v is None:
            path_started = False
            continue
        x, y = x_at(i), y_at(v)
        d += ("M" if not path_started else "L") + f"{x:.1f},{y:.1f} "
        path_started = True
        points.append(
            f'<rect x="{x-2:.1f}" y="{y-2:.1f}" width="4" height="4" fill="{color}" />'
        )
    line_el = f'<path d="{d.strip()}" fill="none" stroke="{color}" stroke-width="1.75" />'

    # x-axis labels: first, middle, last only, to avoid clutter
    label_idxs = sorted(set([0, n // 2, n - 1]))
    x_labels = "".join(
        f'<text x="{x_at(i):.1f}" y="{height - 6}" font-size="9" fill="{INK_SOFT}" '
        f'text-anchor="middle" font-family="ui-monospace,monospace">{dates[i][5:]}</text>'
        for i in label_idxs
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f"{grid}{baseline_line}{line_el}{''.join(points)}{x_labels}"
        f"</svg>"
    )
