import requests
from config import ODDS_API_KEY, SPORTS
from db import log_request

BASE_URL = "https://api.the-odds-api.com/v1/sports/{sport}/odds"
PARAMS = {
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "decimal",
}

RATE_LIMIT_FLOOR = 5


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fetch_odds_with_quota(sport):
    """Internal fetch that returns (data, requests_remain) or None on error."""
    if not ODDS_API_KEY:
        print("[fetcher] ODDS_API_KEY is not set")
        return None

    try:
        response = requests.get(
            BASE_URL.format(sport=sport),
            params={**PARAMS, "apiKey": ODDS_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"[fetcher] HTTP error for {sport}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[fetcher] Request failed for {sport}: {e}")
        return None

    requests_used   = _safe_int(response.headers.get("x-requests-used"),     0)
    requests_remain = _safe_int(response.headers.get("x-requests-remaining"), 0)
    log_request(requests_used, requests_remain, sport)

    return response.json(), requests_remain


def fetch_odds(sport):
    """Fetch raw odds for a single sport. Returns list of games or None on error."""
    result = _fetch_odds_with_quota(sport)
    if result is None:
        return None
    data, _ = result
    return data


def fetch_all():
    """Fetch raw odds for all sports in SPORTS. Returns dict keyed by sport.

    Halts early if remaining requests fall to RATE_LIMIT_FLOOR to protect the
    free-tier quota.
    """
    odds = {}
    for sport in SPORTS:
        result = _fetch_odds_with_quota(sport)
        if result is None:
            continue
        data, remaining = result
        odds[sport] = data
        if remaining <= RATE_LIMIT_FLOOR:
            print(f"[fetcher] requests_remain={remaining} — halting cycle to protect quota")
            break
    return odds
