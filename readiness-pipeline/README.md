# Fitbit Air readiness/recovery pipeline

Pulls your HRV, resting heart rate, sleep stages, and heart rate zone data
from the Google Health API, builds your personal rolling baseline, and
computes a readiness score, no Google Health Premium required.

## How the score works

`overall_score` = 50% HRV vs. your 30-day baseline + 25% resting heart rate
vs. baseline (inverted) + 25% sleep (duration vs. target + deep/REM
proportion). Each component is a z-score mapped to 0-100. Previous day's
elevated-heart-rate minutes are reported alongside the score as context,
not folded into the number.

This is a reasonable starting formula, not a clinical instrument. After
2-4 weeks of real data, look at `readiness_log.jsonl` and adjust the
weights in `scoring.py` to match how your body actually behaves. If you'd
like, drop the log file into a Claude chat and ask it to help you tune the
weights or spot patterns (e.g. "how does my readiness two days after leg
day compare to the rest of the week?").

## One-time setup

1. **Google Cloud project**
   - Go to [console.cloud.google.com](https://console.cloud.google.com),
     create a project (or use an existing one).
   - Enable the **Google Health API**: [API Enablement page](https://console.developers.google.com/apis/library/health.googleapis.com)
   - Create an OAuth 2.0 Client ID on the [Credentials page](https://console.developers.google.com/apis/credentials):
     type **Web application**, Authorized redirect URI = `https://www.google.com`
   - Copy the Client ID and Client Secret.

2. **Add yourself as a test user**
   - Your app starts in "Testing" mode. On the [Audience page](https://console.developers.google.com/auth/audience),
     add your own Google account email under "Test users".
   - Note: while in Testing mode, refresh tokens expire after 7 days, so
     you'll rerun `auth_setup.py` weekly. Publishing the app to production
     (still fine for personal use, just an extra checkbox flow) removes
     that limit.

3. **Add scopes**
   - On the [Data Access page](https://console.developers.google.com/auth/scopes),
     add these two scopes to your OAuth client:
     - `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
     - `https://www.googleapis.com/auth/googlehealth.sleep.readonly`

4. **Local setup**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp config.example.json config.json
   # edit config.json: paste in your client_id and client_secret
   ```

5. **Authorize once**
   ```bash
   python auth_setup.py
   ```
   This opens a browser, you approve access, then paste the resulting
   `google.com/?code=...` URL back into the terminal. Saves `token.json`.

6. **Run it**
   ```bash
   python sync_daily.py
   ```
   First run will have little/no baseline (needs 5+ days minimum, ~30 for
   a stable score). Keep running it daily and the score will sharpen up.

## Automating it

Add a daily cron job (adjust the path):
```
0 8 * * * cd /path/to/readiness-pipeline && .venv/bin/python sync_daily.py >> cron.log 2>&1
```
Run it after your typical wake time so the previous night's sleep has
synced from the Fitbit Air to the Google Health app.

## Optional: Claude coaching notes

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."   # from console.anthropic.com
```
With the key set, `sync_daily.py` will print a short coaching note after
the score. Uses `claude-haiku-4-5-20251001` by default since this is a
cheap, high-frequency call, swap the model in `coach.py` if you want
richer notes.

## Dashboard

`sync_daily.py` regenerates `dashboard.html` after every sync, no server
needed, just double-click it to open in your browser. It's a static file
built fresh each morning: an overall readiness gauge, HRV/resting HR/sleep
gauges with baseline callouts, four trend strip-charts over your last 30
days, and a log table.

To rebuild it manually without waiting for a sync (e.g. after tuning
`scoring.py` weights):
```bash
python build_dashboard.py
```

The look is a linear instrument-gauge style (tick marks, band zones,
dimension-line callouts) rather than a fitness-app dial, deliberately, so
it reads more like a data instrument than a wellness app. It has zero
external dependencies (no CDN, no JS charting library) so it keeps working
even fully offline.

## SETLOG integration (optional)

Want the dashboard as a page inside SETLOG, viewable from your phone? See
`setlog-integration/README.md`. It encrypts the data locally before
publishing it, since GitHub Pages URLs are always public, so your HRV and
sleep numbers stay unreadable to anyone without your passphrase, even
though the file technically sits in a public repo.

## Files

- `auth_setup.py` - one-time OAuth flow, run when token.json is missing or expired
- `google_health_client.py` - handles token refresh + API calls
- `parsers.py` - raw API JSON -> flat per-day values
- `db.py` - SQLite storage (`readiness.db`)
- `scoring.py` - baseline + readiness score math
- `coach.py` - optional Claude-generated daily note
- `sync_daily.py` - the script you actually run (daily)
- `svg_charts.py` - gauge and trend-chart SVG generators (no dependencies)
- `build_dashboard.py` - renders `dashboard.html` from the log

## If field names don't match

The API is fairly new. `parsers.py` is built directly from Google's
published schema for HRV, resting heart rate, and sleep, those should be
solid. The heart rate zones proxy (`daily-heart-rate-zones`) is written
defensively since the exact zone-naming wasn't confirmed against a live
response. Run `python sync_daily.py --debug` to print one raw data point
per type; if strain_minutes comes back empty, paste that raw JSON into a
Claude chat and it can fix the parser in `parsers.py` in one pass.
