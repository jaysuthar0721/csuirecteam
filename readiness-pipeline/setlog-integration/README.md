# SETLOG integration

Adds a private "Readiness" page to SETLOG, viewable from your phone,
without exposing your HRV/sleep data on the public internet.

## Why encryption

GitHub Pages sites are always publicly reachable by URL, even from a
private source repo (true private hosting needs GitHub Enterprise Cloud,
not realistic for a personal project). So whatever lands in the repo,
assume the URL is public.

The fix: the readiness data is encrypted on your computer before it's ever
written to the repo, with a passphrase that never leaves your control. The
published file (`readiness_data.enc.json`) is unreadable noise without it.
Decryption happens entirely in the browser (Web Crypto API, built into
every modern browser, no library needed) when you type your passphrase on
the Readiness page.

This was tested cross-language: Python encrypts, and the actual Web Crypto
API (same one Chrome/Safari use) decrypts it correctly, including
correctly *rejecting* a wrong passphrase rather than silently returning
garbage.

## What's in this folder

- `crypto_utils.py` - Python-side encryption (AES-256-GCM, PBKDF2 key derivation)
- `js/readiness-crypto.js` - browser-side decryption, same algorithm
- `js/readiness-charts.js` - JS port of the gauge/trend chart renderer (byte-for-byte identical output to the Python version for the same input, verified)
- `publish_to_setlog.py` - encrypts your log and writes/commits/pushes it into your SETLOG repo
- `readiness.html` - the page itself: passphrase prompt, decrypt, render

## Setup

1. **Copy files into your SETLOG repo.**
   ```bash
   cp readiness.html /path/to/setlog/
   cp -r js/readiness-crypto.js js/readiness-charts.js /path/to/setlog/js/
   ```
   (Adjust the `<script src="js/...">` paths in `readiness.html` if
   SETLOG's folder structure differs.)

2. **Add a nav link** to `readiness.html` from wherever SETLOG's other
   pages/tabs are linked.

3. **Pick a passphrase.** Something you can type on your phone without
   pain but isn't guessable, a short phrase works well ("correct horse
   battery staple" style). This is never stored anywhere by the pipeline,
   you'll type it into your terminal once (as an environment variable) and
   into the Readiness page in your browser.

4. **Configure `config.json`** in the main pipeline folder (not this one):
   ```json
   "setlog": {
     "enabled": true,
     "repo_path": "/full/path/to/your/local/setlog/checkout",
     "data_filename": "readiness_data.enc.json",
     "max_days": 400,
     "git_auto_push": true
   }
   ```
   `repo_path` is your local clone of SETLOG, the one with a working
   `git remote` already pointed at GitHub, since `sync_daily.py` will
   `git commit` + `git push` there directly.

5. **Set the passphrase as an environment variable**, not in any config
   file. Add this to the same shell profile or cron environment that runs
   `sync_daily.py`:
   ```bash
   export READINESS_PASSPHRASE="your passphrase here"
   ```
   If you're using cron, cron doesn't load your shell profile by default,
   put the export directly in the crontab line, e.g.:
   ```
   0 8 * * * READINESS_PASSPHRASE="..." cd /path/to/readiness-pipeline && .venv/bin/python sync_daily.py >> cron.log 2>&1
   ```

6. **Run `sync_daily.py` once.** It will encrypt your log, write
   `readiness_data.enc.json` into your SETLOG repo, commit, and push. Give
   GitHub Pages a minute to rebuild, then visit `/readiness.html` on your
   live SETLOG URL, from your phone or laptop, and enter your passphrase.

## What ends up public

Only `readiness_data.enc.json`, which looks like this to anyone without
your passphrase:
```json
{"salt": "N1uu...", "iv": "oW9S...", "ciphertext": "NdRz...", "iterations": 250000}
```
No dates, no numbers, no metadata about what kind of data it even is,
beyond "this person tracks something." The chart-rendering code
(`readiness-charts.js`) is also public, same as any client-side JS on
GitHub Pages, but code isn't your data.

## Honest limits

- Anyone who gets your passphrase can decrypt the file, same as any
  password-based scheme. Don't reuse a password you care about elsewhere.
- The passphrase, once entered, is decrypting in your browser's memory.
  Standard browser security applies (a compromised browser/device is a
  bigger threat model than this encryption is designed to defend against).
- Old commits stay in git history forever unless you rewrite it. Each
  day's ciphertext is fully random (new salt and IV every time) even if
  the underlying data barely changed, so this isn't a way to hide *that*
  you're publishing something, only *what* it says.
