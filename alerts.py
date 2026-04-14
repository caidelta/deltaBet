import sqlite3
import requests
from config import DISCORD_WEBHOOK, DB_PATH, BANKROLL

SPORT_LABELS = {
    "americanfootball_nfl": "NFL",
    "basketball_nba":       "NBA",
    "icehockey_nhl":        "NHL",
}

DEDUP_MINUTES = 30


def _already_alerted(game, book1, book2):
    """Return True if this game+books combo was logged in the last 30 minutes.

    D1: books are sorted before querying so order differences across cycles
    don't bypass dedup.
    E4: OperationalError (table not yet created) is caught and treated as no
    prior alert rather than crashing the pipeline.
    """
    book1, book2 = sorted([book1, book2])
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute(
            """
            SELECT 1 FROM opportunities
            WHERE game  = ?
              AND book1 = ?
              AND book2 = ?
              AND found_at >= datetime('now', ? || ' minutes')
            LIMIT 1
            """,
            (game, book1, book2, f"-{DEDUP_MINUTES}"),
        ).fetchone()
    except sqlite3.OperationalError:
        row = None  # table not yet initialised — treat as no prior alert
    finally:
        con.close()
    return row is not None


def _build_embed(sport, game, book1, book2, margin, odds1, odds2, stake1, stake2):
    sport_label = SPORT_LABELS.get(sport, sport)
    description = (
        f"**Sport:**   {sport_label}\n"
        f"**Game:**    {game}\n"
        f"**Books:**   {book1} / {book2}\n"
        f"**Margin:**  +{margin * 100:.1f}%\n"
        f"**Odds:**    {odds1:.2f} / {odds2:.2f}\n"
        f"**Stake:**   ${stake1:.0f} / ${stake2:.0f} "
        f"(on ${BANKROLL:.0f} bankroll)"
    )
    return {
        "embeds": [
            {
                "title": "\U0001f6a8 ARB OPPORTUNITY",
                "description": description,
                "color": 0xFF0000,
            }
        ]
    }


def send_alert(sport, game, book1, book2, margin, odds1, odds2, stake1, stake2):
    """Post a Discord embed for an arb opportunity. Skips if dedup window active.

    Returns True if the alert was sent, False if skipped or failed.
    """
    if not DISCORD_WEBHOOK:
        print("[alerts] DISCORD_WEBHOOK not set — skipping alert")
        return False

    if _already_alerted(game, book1, book2):
        print(f"[alerts] Dedup hit — skipping {game} ({book1}/{book2})")
        return False

    payload = _build_embed(sport, game, book1, book2, margin, odds1, odds2, stake1, stake2)

    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[alerts] Webhook POST failed: {e}")
        return False

    return True
