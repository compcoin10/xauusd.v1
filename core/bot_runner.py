"""
Bot runner: orchestrates data fetch → signal generation → trade management → balance update.
Runs as a background process; state persists in SQLite.
"""
import time
import threading
from datetime import datetime, timezone

from core.data_fetcher import get_xauusd, get_dxy, get_latest_price, get_current_session
from core.signal_engine import generate_signals
from core.indicators import enrich_df, market_regime
from core.risk_manager import calculate_lot_size, calculate_pnl, should_trade
from core.database import (
    get_bot_state, set_bot_state, save_signal, open_trade,
    close_trade, get_open_trades, get_balance, set_balance
)

_bot_thread: threading.Thread = None
_stop_event = threading.Event()


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[BOT {ts}] {msg}")


def _update_open_trades(current_price: float, balance: float) -> float:
    """Check open trades; close if SL/TP is hit."""
    open_trades = get_open_trades()
    for _, trade in open_trades.iterrows():
        hit = False
        exit_price = current_price
        direction  = trade["direction"]

        if direction == "BUY":
            if current_price <= trade["sl"]:
                exit_price, hit = trade["sl"], True
                _log(f"Trade {trade['id']} BUY SL hit @ {exit_price}")
            elif current_price >= trade["tp"]:
                exit_price, hit = trade["tp"], True
                _log(f"Trade {trade['id']} BUY TP hit @ {exit_price}")
        else:
            if current_price >= trade["sl"]:
                exit_price, hit = trade["sl"], True
                _log(f"Trade {trade['id']} SELL SL hit @ {exit_price}")
            elif current_price <= trade["tp"]:
                exit_price, hit = trade["tp"], True
                _log(f"Trade {trade['id']} SELL TP hit @ {exit_price}")

        if hit:
            pnl = calculate_pnl(direction, trade["entry_price"], exit_price, trade["lot_size"])
            close_trade(int(trade["id"]), exit_price, pnl)
            balance += pnl
            set_balance(balance)
            _log(f"Trade closed PnL={pnl:.2f} | New balance={balance:.2f}")

    return balance


def _bot_loop():
    """Main bot loop: runs every 5 minutes."""
    _log("Bot started.")
    while not _stop_event.is_set():
        try:
            if not get_bot_state("bot_enabled", True):
                time.sleep(30)
                continue

            balance = get_balance()
            current_price = get_latest_price()
            set_bot_state("last_price", current_price)
            set_bot_state("last_tick", datetime.now(timezone.utc).isoformat())

            # Update open trades (SL/TP check)
            balance = _update_open_trades(current_price, balance)

            # Generate signals every cycle
            df_h1  = get_xauusd("H1")
            df_m15 = get_xauusd("M15")
            dxy_df = get_dxy("H1")

            signals = generate_signals(df_m15, df_h1, dxy_df)

            for sig in signals:
                save_signal(sig)
                _log(f"Signal: {sig['direction']} {sig['strategy']} conf={sig['confidence']}%")

                # Auto-trade if enabled and risk check passes
                if get_bot_state("auto_trade", False):
                    can_trade, reason = should_trade(balance)
                    if can_trade:
                        lot = calculate_lot_size(sig["entry"], sig["sl"], balance)
                        open_trade(sig, lot, balance)
                        _log(f"Trade opened: {sig['direction']} @ {sig['entry']} lot={lot}")
                    else:
                        _log(f"Trade skipped: {reason}")

            # Update regime in state
            if df_h1 is not None and len(df_h1) >= 200:
                df_e = enrich_df(df_h1)
                regime = market_regime(df_e)
                set_bot_state("regime", regime)
                session = get_current_session()
                set_bot_state("session", session)

        except Exception as e:
            _log(f"Error in bot loop: {e}")

        _stop_event.wait(timeout=300)  # 5 minutes

    _log("Bot stopped.")


def start_bot():
    global _bot_thread, _stop_event
    if _bot_thread and _bot_thread.is_alive():
        return False
    _stop_event.clear()
    set_bot_state("bot_running", True)
    _bot_thread = threading.Thread(target=_bot_loop, daemon=True, name="BotThread")
    _bot_thread.start()
    return True


def stop_bot():
    global _stop_event
    _stop_event.set()
    set_bot_state("bot_running", False)
    return True


def is_bot_running() -> bool:
    return (_bot_thread is not None and _bot_thread.is_alive())
