"""
Persistent database manager using SQLite.
On Streamlit Cloud, writes to /tmp so data survives the session.
On local, writes to ./data/ next to the project root.
"""
import sqlite3
import json
import os
from datetime import datetime
import pandas as pd

# ── DB path: /tmp on cloud, ./data locally ────────────────────────────────────
def _get_db_path() -> str:
    # Streamlit Cloud sets STREAMLIT_SHARING_MODE or runs under /mount/src/
    on_cloud = (
        os.environ.get("STREAMLIT_SHARING_MODE") == "true"
        or "/mount/src/" in os.path.abspath(__file__)
    )
    if on_cloud:
        return "/tmp/trading_bot.db"
    local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(local_dir, exist_ok=True)
    return os.path.join(local_dir, "trading_bot.db")

DB_PATH = _get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS balance (
            id INTEGER PRIMARY KEY,
            amount REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT,
            symbol TEXT DEFAULT 'XAUUSD',
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            sl REAL,
            tp REAL,
            lot_size REAL,
            strategy TEXT,
            confidence REAL,
            status TEXT DEFAULT 'open',
            pnl REAL DEFAULT 0,
            opened_at TEXT,
            closed_at TEXT,
            regime TEXT,
            session TEXT,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE,
            direction TEXT,
            entry REAL,
            sl REAL,
            tp REAL,
            confidence REAL,
            strategy TEXT,
            regime TEXT,
            session TEXT,
            dxy_bias TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            strategy TEXT,
            total_trades INTEGER,
            win_rate REAL,
            profit_factor REAL,
            max_drawdown REAL,
            net_pnl REAL,
            params TEXT
        )
    """)

    # Seed balance if first run
    c.execute("SELECT COUNT(*) FROM balance")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO balance (amount, updated_at) VALUES (?, ?)",
                  (5000.0, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()


def get_balance() -> float:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT amount FROM balance ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row["amount"] if row else 5000.0


def set_balance(amount: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE balance SET amount=?, updated_at=? WHERE id=1",
              (amount, datetime.utcnow().isoformat()))
    if c.rowcount == 0:
        c.execute("INSERT INTO balance (amount, updated_at) VALUES (?,?)",
                  (amount, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def save_signal(signal: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO signals
        (signal_id, direction, entry, sl, tp, confidence, strategy, regime, session, dxy_bias, created_at, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        signal.get("signal_id"), signal.get("direction"), signal.get("entry"),
        signal.get("sl"), signal.get("tp"), signal.get("confidence"),
        signal.get("strategy"), signal.get("regime"), signal.get("session"),
        signal.get("dxy_bias"), signal.get("created_at"), signal.get("status", "pending")
    ))
    conn.commit()
    conn.close()


def get_signals(limit: int = 50) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return df


def open_trade(signal: dict, lot_size: float, balance: float) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO trades
        (signal_id, direction, entry_price, sl, tp, lot_size, strategy, confidence, status, opened_at, regime, session)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        signal.get("signal_id"), signal.get("direction"), signal.get("entry"),
        signal.get("sl"), signal.get("tp"), lot_size, signal.get("strategy"),
        signal.get("confidence"), "open", datetime.utcnow().isoformat(),
        signal.get("regime"), signal.get("session")
    ))
    conn.commit()
    trade_id = c.lastrowid
    conn.close()
    return trade_id


def close_trade(trade_id: int, exit_price: float, pnl: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE trades SET exit_price=?, pnl=?, status='closed', closed_at=?
        WHERE id=?
    """, (exit_price, pnl, datetime.utcnow().isoformat(), trade_id))
    conn.commit()
    conn.close()


def get_trades(status: str = None, limit: int = 100) -> pd.DataFrame:
    conn = get_connection()
    if status:
        df = pd.read_sql(
            "SELECT * FROM trades WHERE status=? ORDER BY opened_at DESC LIMIT ?",
            conn, params=(status, limit)
        )
    else:
        df = pd.read_sql(
            "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?",
            conn, params=(limit,)
        )
    conn.close()
    return df


def get_open_trades() -> pd.DataFrame:
    return get_trades(status="open")


def set_bot_state(key: str, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO bot_state (key, value, updated_at) VALUES (?,?,?)",
        (key, json.dumps(value), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_bot_state(key: str, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except Exception:
            return default
    return default


def save_backtest(result: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO backtest_results
        (run_at, strategy, total_trades, win_rate, profit_factor, max_drawdown, net_pnl, params)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        datetime.utcnow().isoformat(), result.get("strategy"),
        result.get("total_trades"), result.get("win_rate"),
        result.get("profit_factor"), result.get("max_drawdown"),
        result.get("net_pnl"), json.dumps(result.get("params", {}))
    ))
    conn.commit()
    conn.close()


def get_backtest_results(limit: int = 20) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM backtest_results ORDER BY run_at DESC LIMIT ?",
        conn, params=(limit,)
    )
    conn.close()
    return df


# Auto-init on import
init_db()
