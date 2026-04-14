import sqlite3
from config import DB_PATH

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sport     TEXT,
            game      TEXT,
            commence  TEXT,
            book1     TEXT,
            book2     TEXT,
            outcome1  TEXT,
            outcome2  TEXT,
            odds1     REAL,
            odds2     REAL,
            arb_pct   REAL,
            found_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS request_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            polled_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            requests_used   INTEGER,
            requests_remain INTEGER,
            sport           TEXT
        );
    """)
    con.commit()
    con.close()

def log_opportunity(sport, game, commence, book1, book2, outcome1, outcome2, odds1, odds2, arb_pct):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO opportunities
           (sport, game, commence, book1, book2, outcome1, outcome2, odds1, odds2, arb_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sport, game, commence, book1, book2, outcome1, outcome2, odds1, odds2, arb_pct),
    )
    con.commit()
    con.close()

def log_request(requests_used, requests_remain, sport):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO request_log (requests_used, requests_remain, sport)
           VALUES (?, ?, ?)""",
        (requests_used, requests_remain, sport),
    )
    con.commit()
    con.close()

def get_recent(n=20):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM opportunities ORDER BY found_at DESC LIMIT ?", (n,)
    ).fetchall()
    con.close()
    return rows
