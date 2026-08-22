"""
Encrypts readiness_log.jsonl and writes it into your SETLOG repo as
readiness_data.enc.json, then optionally commits and pushes it.

The passphrase NEVER goes in config.json or anywhere that could get
committed. Set it as an environment variable instead:

    export READINESS_PASSPHRASE="something only you know"

Called automatically from sync_daily.py if setlog.enabled is true in
config.json. Can also be run standalone:

    python publish_to_setlog.py
"""

import json
import os
import subprocess
import sys

# Make sure crypto_utils.py (same directory as this file) is importable
# no matter what directory this module is imported from.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
from crypto_utils import encrypt_json  # noqa: E402


def load_setlog_config(config_path=None):
    # config.json lives one directory up, in the main pipeline folder.
    config_path = config_path or os.path.join(
        os.path.dirname(_THIS_DIR), "config.json"
    )
    with open(config_path) as f:
        full = json.load(f)
    return full.get("setlog", {})


def load_entries(log_path, max_days=400):
    entries = []
    if not os.path.exists(log_path):
        return entries
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    by_date = {e["date"]: e for e in entries if e.get("date")}
    dates = sorted(by_date)[-max_days:]
    return [by_date[d] for d in dates]


def publish(
    log_path="readiness_log.jsonl",
    setlog_config=None,
):
    cfg = setlog_config if setlog_config is not None else load_setlog_config()
    if not cfg.get("enabled"):
        return None  # integration not configured, silently skip

    passphrase = os.environ.get("READINESS_PASSPHRASE")
    if not passphrase:
        print(
            "READINESS_PASSPHRASE is not set, skipping SETLOG publish. "
            "Set it with: export READINESS_PASSPHRASE='...'",
            file=sys.stderr,
        )
        return None

    repo_path = cfg["repo_path"]
    data_filename = cfg.get("data_filename", "readiness_data.enc.json")
    max_days = cfg.get("max_days", 400)

    entries = load_entries(log_path, max_days=max_days)
    if not entries:
        print("No readiness data to publish yet.", file=sys.stderr)
        return None

    payload = encrypt_json(entries, passphrase)
    out_path = os.path.join(repo_path, data_filename)
    with open(out_path, "w") as f:
        json.dump(payload, f)
    print(f"Wrote {out_path} ({len(entries)} days, encrypted)")

    if cfg.get("git_auto_push", False):
        _git_commit_and_push(repo_path, data_filename)

    return out_path


def _git_commit_and_push(repo_path, data_filename):
    def run(*args):
        return subprocess.run(
            ["git", "-C", repo_path] + list(args),
            capture_output=True,
            text=True,
        )

    add = run("add", data_filename)
    if add.returncode != 0:
        print(f"git add failed: {add.stderr}", file=sys.stderr)
        return

    commit = run("commit", "-m", "Update readiness data")
    if commit.returncode != 0:
        # Most common case: nothing changed since yesterday. Not an error.
        if "nothing to commit" in (commit.stdout + commit.stderr):
            print("No changes to publish (data unchanged since last sync).")
            return
        print(f"git commit failed: {commit.stderr}", file=sys.stderr)
        return

    push = run("push")
    if push.returncode != 0:
        print(f"git push failed: {push.stderr}", file=sys.stderr)
        print("Data was committed locally but not pushed, push it manually.", file=sys.stderr)
    else:
        print("Pushed to SETLOG repo.")


if __name__ == "__main__":
    result = publish()
    if result is None:
        print("Nothing published. Check config.json's 'setlog' section and READINESS_PASSPHRASE.")
