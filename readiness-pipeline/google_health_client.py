"""
Thin wrapper around the Google Health API (health.googleapis.com/v4).

Reference: https://developers.google.com/health/data-types/vitals
           https://developers.google.com/health/data-types/sleep
           https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints
"""

import json
import time

import requests

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
API_BASE = "https://health.googleapis.com/v4/users/me/dataTypes"

# Data types whose dataPoints are keyed by a daily `date` field rather than
# a start/end interval. Their AIP-160 filter member is
# "{data_type_with_underscores}.date", e.g. "daily_heart_rate_variability.date".
DAILY_SUMMARY_TYPES = {
    "daily-heart-rate-variability",
    "daily-resting-heart-rate",
    "daily-heart-rate-zones",
    "daily-oxygen-saturation",
    "daily-respiratory-rate",
    "daily-sleep-temperature-derivations",
}


class GoogleHealthClient:
    def __init__(self, config_path="config.json", token_path="token.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        self.token_path = token_path
        with open(token_path) as f:
            self.tokens = json.load(f)
        self._access_token = None
        self._access_token_expiry = 0

    def _refresh_access_token(self):
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "refresh_token": self.tokens["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        # Refresh a little early to be safe.
        self._access_token_expiry = time.time() + data.get("expires_in", 3600) - 60
        # The token endpoint sometimes rotates the refresh token; persist if so.
        if "refresh_token" in data:
            self.tokens["refresh_token"] = data["refresh_token"]
            with open(self.token_path, "w") as f:
                json.dump(self.tokens, f, indent=2)
        return self._access_token

    def _get_access_token(self):
        if self._access_token is None or time.time() >= self._access_token_expiry:
            self._refresh_access_token()
        return self._access_token

    def list_data_points(self, data_type, start_time_iso, end_time_iso):
        """
        Fetch all data points for a given data type over a time range.

        data_type examples: 'daily-heart-rate-variability', 'daily-resting-heart-rate',
        'sleep', 'daily-oxygen-saturation', 'daily-respiratory-rate',
        'daily-sleep-temperature-derivations', 'daily-heart-rate-zones'

        Returns the list of raw dataPoint dicts from the API response.
        """
        url = f"{API_BASE}/{data_type}/dataPoints"
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json",
        }
        params = {}
        if data_type in DAILY_SUMMARY_TYPES:
            # This endpoint doesn't accept startTime/endTime query params;
            # it wants an AIP-160 filter over the daily `date` field, keyed
            # by the data type name with hyphens swapped for underscores.
            field = data_type.replace("-", "_")
            start_date = start_time_iso[:10]
            end_date = end_time_iso[:10]
            params["filter"] = (
                f'{field}.date >= "{start_date}" AND {field}.date < "{end_date}"'
            )
        # Other types (e.g. 'sleep') don't support server-side time filtering
        # on this API version; fetch unfiltered and let the caller filter by
        # date after parsing.

        all_points = []
        page_token = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 401:
                # Access token expired mid-run; refresh once and retry.
                self._access_token = None
                headers["Authorization"] = f"Bearer {self._get_access_token()}"
                resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            body = resp.json()
            all_points.extend(body.get("dataPoints", []))
            page_token = body.get("nextPageToken")
            if not page_token:
                break
        return all_points
