"""
Bot runner: background thread that ticks every 5 minutes.
Safe for Streamlit Cloud — uses daemon threads, no subprocess.
"""
import time
import threading
from datetime import datetime, timezone

from core.data_fetcher import get_xauusd, get_dxy, get_latest_price, get_current_session
from core.signal_engine import generate_signals
from core.indicators import enrich_df, market_regime
from core.risk_manager import calculate_lot_size, calculate_pnl, should_trade
from core.database import (
    get_bot_state, set_bot_state, save_signal,
    open_trade, close_trade, get_open_trades, get_balance, set_balance
)

_lock        = threading.Lock()
_bot_thread  = None
_stop_event  = threading.Event()


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    print(f"[BOT {ts}] {msg}")


def _update_open_trades(current_price: float, balance: float) -> float:
    open_trades = get_open_trades()
    for _, trade in open_trades.iterrows():
        direction  = trade["direction"]
        exit_price = None

        if direction == "BUY":
            if current_price <= float(trade["sl"]):
                exit_price = float(trade["sl"])
            elif current_price >= float(trade["tp"]):
                exit_price = float(trade["tp"])
        else:
            if current_price >= float(trade["sl"]):
                exit_price = float(trade["sl"])
            elif current_price <= float(trade["tp"]):
                exit_price = float(trade["tp"])

        if exit_price is not None:
            pnl = calculate_pnl(direction, float(trade["entry_price"]), exit_price, float(trade["lot_size"]))
            close_trade(int(trade["id"]), exit_price, pnl)
            balance += pnl
            set_balance(balance)
            _log(f"Trade #{trade['id']} closed | PnL=${pnl:+.2f} | Balance=${balance:.2f}")

    return balance


def _bot_loop():
    _log("Bot thread started.")
    while not _stop_event.is_set():
        try:
            if not get_bot_state("bot_enabled", True):
                _stop_event.wait(timeout=30)
                continue

            balance       = get_balance()
            current_price = get_latest_price()
            set_bot_state("last_price", current_price)
            set_bot_state("last_tick",  datetime.now(timezone.utc).isoformat())

            # SL/TP management
            balance = _update_open_trades(current_price, balance)

            # Fetch data
            df_h1  = get_xauusd("H1")
            df_m15 = get_xauusd("M15")
            dxy_df = get_dxy("H1")

            # Regime detection
            if df_h1 is not None and len(df_h1) >= 200:
                df_e   = enrich_df(df_h1)
                regime = market_regime(df_e)
                set_bot_state("regime",  regime)
                set_bot_state("session", get_current_session())

            # Signal generation
            signals = generate_signals(df_m15, df_h1, dxy_df)
            for sig in signals:
                save_signal(sig)
                _log(f"Signal: {sig['direction']} | {sig['strategy']} | conf={sig['confidence']}%")

                if get_bot_state("auto_trade", False):
                    can_trade, reason = should_trade(balance)
                    if can_trade:
                        lot = calculate_lot_size(sig["entry"], sig["sl"], balance)
                        open_trade(sig, lot, balance)
                        _log(f"Auto-trade opened: {sig['direction']} @ {sig['entry']} lot={lot}")
                    else:
                        _log(f"Auto-trade skipped: {reason}")

        except Exception as e:
            _log(f"Loop error: {e}")

        _stop_event.wait(timeout=300)   # 5-minute tick

    _log("Bot thread stopped.")


def start_bot() -> bool:
    global _bot_thread
    with _lock:
        if _bot_thread and _bot_thread.is_alive():
            return False
        _stop_event.clear()
        set_bot_state("bot_running", True)
        _bot_thread = threading.Thread(target=_bot_loop, daemon=True, name="XAUBotThread")
        _bot_thread.start()
    return True


def stop_bot() -> bool:
    _stop_event.set()
    set_bot_state("bot_running", False)
    return True


def is_bot_running() -> bool:
    return _bot_thread is not None and _bot_thread.is_alive()
