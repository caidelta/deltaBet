import os

ODDS_API_KEY       = os.getenv("ODDS_API_KEY")
DISCORD_WEBHOOK    = os.getenv("DISCORD_WEBHOOK_URL")
MIN_ARB_PCT        = float(os.getenv("MIN_ARB_PCT", "0.005"))
POLL_INTERVAL_MIN  = int(os.getenv("POLL_INTERVAL_MIN", "30"))
BANKROLL           = float(os.getenv("BANKROLL", "100"))
SPORTS             = ["americanfootball_nfl", "basketball_nba", "icehockey_nhl"]
DB_PATH            = os.getenv("DB_PATH", "arb.db")
