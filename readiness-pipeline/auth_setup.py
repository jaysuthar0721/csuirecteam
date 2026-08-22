"""
One-time setup script. Run this once to authorize the app against your
Google Health account and save a refresh token to token.json.

Before running:
1. Go to console.cloud.google.com, create (or select) a project.
2. Enable the "Google Health API" on the API Enablement page.
3. Create an OAuth 2.0 Client ID (type: Web application).
   - Authorized redirect URI: https://www.google.com
4. On the Audience page, add your own Google account email as a test user
   (the app starts in "Testing" mode, capped at 100 users).
5. On the Data Access page, add these two scopes for your OAuth client:
   - https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
   - https://www.googleapis.com/auth/googlehealth.sleep.readonly
6. Copy config.example.json to config.json and fill in client_id / client_secret.

Then run: python auth_setup.py
"""

import json
import urllib.parse
import webbrowser

import requests

SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
]

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def build_auth_url(config):
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "access_type": "offline",
        "scope": " ".join(SCOPES),
        "prompt": "consent",
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def extract_code_from_pasted_url(pasted):
    """Accepts either the full redirected URL or just the bare code."""
    pasted = pasted.strip()
    if pasted.startswith("http"):
        query = urllib.parse.urlparse(pasted).query
        parsed = urllib.parse.parse_qs(query)
        if "code" not in parsed:
            raise ValueError("No 'code' parameter found in that URL.")
        return parsed["code"][0]
    return pasted


def exchange_code_for_tokens(config, code):
    resp = requests.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config["redirect_uri"],
        },
    )
    resp.raise_for_status()
    return resp.json()


def main():
    config = load_config()
    auth_url = build_auth_url(config)

    print("Opening the Google authorization page in your browser.")
    print("If it doesn't open automatically, visit this URL:\n")
    print(auth_url)
    print()
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print("After you approve access, you'll land on a google.com page")
    print("whose URL bar contains '?code=...'. Paste that full URL")
    print("(or just the code value) below.\n")
    pasted = input("Paste the redirect URL or code here: ")
    code = extract_code_from_pasted_url(pasted)

    tokens = exchange_code_for_tokens(config, code)
    if "refresh_token" not in tokens:
        raise RuntimeError(
            "No refresh_token in response. Make sure prompt=consent was used "
            "and this is the first authorization (revoke prior access in your "
            "Google Account permissions and try again if needed)."
        )

    with open("token.json", "w") as f:
        json.dump(tokens, f, indent=2)

    print("\nSaved refresh token to token.json.")
    print("You can now run sync_daily.py.")
    print(
        "\nNote: while your Google Cloud OAuth app is in 'Testing' status, "
        "the refresh token expires after 7 days and you'll need to rerun "
        "this script. Publishing the app to production (Audience page) "
        "removes that limit."
    )


if __name__ == "__main__":
    main()
