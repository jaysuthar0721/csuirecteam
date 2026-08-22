import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT PRIMARY KEY,
    hrv_rmssd_ms REAL,
    resting_hr_bpm REAL,
    total_sleep_min REAL,
    deep_sleep_min REAL,
    rem_sleep_min REAL,
    light_sleep_min REAL,
    awake_min REAL,
    strain_minutes REAL,
    updated_at TEXT
);
"""

FIELDS = [
    "hrv_rmssd_ms",
    "resting_hr_bpm",
    "total_sleep_min",
    "deep_sleep_min",
    "rem_sleep_min",
    "light_sleep_min",
    "awake_min",
    "strain_minutes",
]


def connect(db_path="readiness.db"):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def upsert_day(conn, date, **fields):
    """
    Merge new values into the row for `date`, leaving existing columns
    untouched if not provided in this call (so you can call it once per
    data type without clobbering the others).
    """
    row = conn.execute(
        "SELECT * FROM daily_metrics WHERE date = ?", (date,)
    ).fetchone()
    col_names = [d[0] for d in conn.execute("SELECT * FROM daily_metrics LIMIT 0").description]
    current = dict(zip(col_names, row)) if row else {f: None for f in ["date"] + FIELDS + ["updated_at"]}
    current.update({k: v for k, v in fields.items() if k in FIELDS})
    current["date"] = date
    current["updated_at"] = datetime.now(timezone.utc).isoformat()

    columns = ["date"] + FIELDS + ["updated_at"]
    placeholders = ", ".join("?" for _ in columns)
    values = [current.get(c) for c in columns]
    conn.execute(
        f"INSERT OR REPLACE INTO daily_metrics ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    conn.commit()


def get_recent_days(conn, n_days, before_date=None):
    """Returns rows as list of dicts, most recent first."""
    if before_date:
        rows = conn.execute(
            "SELECT * FROM daily_metrics WHERE date < ? ORDER BY date DESC LIMIT ?",
            (before_date, n_days),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM daily_metrics ORDER BY date DESC LIMIT ?", (n_days,)
        ).fetchall()
    col_names = [d[0] for d in conn.execute("SELECT * FROM daily_metrics LIMIT 0").description]
    return [dict(zip(col_names, row)) for row in rows]


def get_day(conn, date):
    row = conn.execute("SELECT * FROM daily_metrics WHERE date = ?", (date,)).fetchone()
    if not row:
        return None
    col_names = [d[0] for d in conn.execute("SELECT * FROM daily_metrics LIMIT 0").description]
    return dict(zip(col_names, row))
