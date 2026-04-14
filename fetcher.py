import requests
from config import ODDS_API_KEY, SPORTS
from db import log_request

BASE_URL = "https://api.the-odds-api.com/v1/sports/{sport}/odds"
PARAMS = {
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "decimal",
}


def fetch_odds(sport):
    """Fetch raw odds dict for a single sport. Returns list of games or None on error."""
    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY is not set")

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

    requests_used = int(response.headers.get("x-requests-used", 0))
    requests_remain = int(response.headers.get("x-requests-remaining", 0))
    log_request(requests_used, requests_remain, sport)

    return response.json()


def fetch_all():
    """Fetch raw odds for all sports in SPORTS. Returns dict keyed by sport."""
    odds = {}
    for sport in SPORTS:
        result = fetch_odds(sport)
        if result is not None:
            odds[sport] = result
    return odds
