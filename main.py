from apscheduler.schedulers.blocking import BlockingScheduler

from config import POLL_INTERVAL_MIN, BANKROLL, ODDS_API_KEY
from db import init_db, log_opportunity
from fetcher import fetch_all
from calculator import implied_prob, arb_pct, is_arb, kelly_stakes, best_odds_per_outcome
from alerts import send_alert


def _process_game(sport, game):
    best = best_odds_per_outcome(game.get("bookmakers", []))

    if len(best) != 2:
        return

    (name1, (odds1, book1)), (name2, (odds2, book2)) = best.items()

    probs = [implied_prob(odds1), implied_prob(odds2)]
    pct   = arb_pct(probs)

    if not is_arb(pct):
        return

    # D1: sort book pair so dedup is order-independent across cycles
    if book1 > book2:
        book1, book2 = book2, book1
        name1, name2 = name2, name1
        odds1, odds2 = odds2, odds1

    margin          = -pct
    stake1, stake2  = kelly_stakes(BANKROLL, odds1, odds2)  # E2: raises on odds <= 1.0

    # E1: use .get() — bare key access raises KeyError on malformed API responses
    home     = game.get("home_team", "Unknown")
    away     = game.get("away_team", "Unknown")
    game_str = f"{home} vs {away}"
    commence = game.get("commence_time", "")

    print(f"[main] Arb found: {game_str} | {book1}/{book2} | +{margin*100:.2f}%")

    # D2: log to DB before alerting — dedup depends on the record existing
    # regardless of whether the Discord webhook succeeds
    log_opportunity(
        sport, game_str, commence,
        book1, book2, name1, name2,
        odds1, odds2, pct,
    )

    send_alert(
        sport, game_str, book1, book2,
        margin, odds1, odds2, stake1, stake2,
    )


def poll():
    print("[main] Poll cycle started")
    try:  # E3: top-level handler so a crash here doesn't exit the Render worker
        all_odds = fetch_all()

        if not all_odds:  # L1: distinguish broken API from quiet market
            print("[main] WARNING: no odds data returned for any sport this cycle")
            return

        for sport, games in all_odds.items():
            for game in games:
                try:  # L2: per-game isolation — one bad game doesn't drop the rest
                    _process_game(sport, game)
                except Exception as e:
                    print(f"[main] Skipping game due to error: {e}")

    except Exception as e:
        print(f"[main] Poll cycle failed: {e}")

    print("[main] Poll cycle complete")


if __name__ == "__main__":
    # R3: validate key at startup — fail loudly before init_db or first poll
    if not ODDS_API_KEY:
        raise SystemExit("[main] ODDS_API_KEY is not set — aborting")

    init_db()
    poll()  # run immediately on startup, don't wait for first interval

    scheduler = BlockingScheduler()
    scheduler.add_job(poll, "interval", minutes=POLL_INTERVAL_MIN)
    print(f"[main] Scheduler started — polling every {POLL_INTERVAL_MIN} min")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[main] Shutting down")
