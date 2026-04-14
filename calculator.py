from datetime import datetime, timezone, timedelta
from config import MIN_ARB_PCT, POLL_INTERVAL_MIN


def implied_prob(odds):
    """Return implied probability for a decimal odds value.

    >>> implied_prob(2.0)
    0.5
    >>> round(implied_prob(1.5), 4)
    0.6667
    """
    return 1 / odds


def arb_pct(probs):
    """Return sum of implied probabilities minus 1.

    Negative result means a true arb exists; the magnitude is the margin.

    >>> round(arb_pct([0.4762, 0.4878]), 4)  # odds 2.10 / 2.05 → margin ~+1.3%
    -0.036
    >>> round(arb_pct([0.5, 0.5]), 4)        # break-even book
    0.0
    >>> round(arb_pct([0.55, 0.50]), 4)      # overround book (no arb)
    0.05
    """
    return sum(probs) - 1


def is_arb(pct, threshold=MIN_ARB_PCT):
    """Return True when arb_pct is sufficiently negative to exceed threshold.

    pct < 0 signals a true arb; threshold filters noise from stale odds.

    >>> is_arb(-0.013)          # 1.3% margin, above default 0.5% threshold
    True
    >>> is_arb(-0.002)          # 0.2% margin, below default threshold → filtered
    False
    >>> is_arb(0.0)             # break-even, not an arb
    False
    """
    return pct < -threshold


def kelly_stakes(bankroll, odds_1, odds_2):
    """Return (stake_1, stake_2) sized to lock in the arb margin.

    Uses the Kelly-adjacent formula from Layer 4:
        margin  = 1 - (1/odds_1 + 1/odds_2)
        stake_1 = (bankroll * margin) / (1 - 1/odds_1)
        stake_2 = bankroll - stake_1

    Raises ValueError if either odds value is <= 1.0 (guards division by zero).

    >>> s1, s2 = kelly_stakes(100, 2.10, 2.05)
    >>> round(s1, 2), round(s2, 2)
    (52.17, 47.83)
    >>> round(s1 + s2, 10)      # stakes sum to exactly bankroll
    100.0
    """
    if odds_1 <= 1.0 or odds_2 <= 1.0:
        raise ValueError(f"Odds must be > 1.0, got {odds_1}, {odds_2}")
    margin = 1 - (implied_prob(odds_1) + implied_prob(odds_2))
    stake_1 = (bankroll * margin) / (1 - implied_prob(odds_1))
    stake_2 = bankroll - stake_1
    return stake_1, stake_2


def best_odds_per_outcome(bookmakers):
    """Return {outcome_name: (price, book_title)} with the highest price per outcome.

    Bookmakers whose last_update is older than POLL_INTERVAL_MIN minutes are
    excluded to prevent stale-vs-fresh comparisons producing phantom arbs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=POLL_INTERVAL_MIN)
    best = {}
    for bookmaker in bookmakers:
        last_update = bookmaker.get("last_update")
        if last_update:
            try:
                updated_at = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
                if updated_at < cutoff:
                    continue
            except ValueError:
                pass  # unparseable timestamp — include the bookmaker
        for market in bookmaker.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name  = outcome["name"]
                price = outcome["price"]
                if name not in best or price > best[name][0]:
                    best[name] = (price, bookmaker["title"])
    return best


def find_arbs(games):
    """Scan a list of games (output of fetch_odds) and return all arb opportunities.

    Each opportunity is a dict with keys: game, home_team, away_team,
    commence_time, book1, book2, name1, name2, odds1, odds2, arb_pct, margin.
    Books and names are sorted so the result is stable across calls.

    >>> find_arbs([])
    []
    """
    if not games:
        return []

    opportunities = []
    for game in games:
        best = best_odds_per_outcome(game.get("bookmakers", []))
        if len(best) != 2:
            continue

        (name1, (odds1, book1)), (name2, (odds2, book2)) = best.items()

        pct = arb_pct([implied_prob(odds1), implied_prob(odds2)])
        if not is_arb(pct):
            continue

        # Sort book pair for stable output
        if book1 > book2:
            book1, book2 = book2, book1
            name1, name2 = name2, name1
            odds1, odds2 = odds2, odds1

        opportunities.append({
            "game":         f"{game.get('home_team', 'Unknown')} vs {game.get('away_team', 'Unknown')}",
            "home_team":    game.get("home_team", "Unknown"),
            "away_team":    game.get("away_team", "Unknown"),
            "commence_time": game.get("commence_time", ""),
            "book1":        book1,
            "book2":        book2,
            "name1":        name1,
            "name2":        name2,
            "odds1":        odds1,
            "odds2":        odds2,
            "arb_pct":      pct,
            "margin":       -pct,
        })

    return opportunities
