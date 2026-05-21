"""
Risk management: position sizing, monthly target tracking, drawdown limits.
"""
import math
from core.database import get_balance, get_trades

RISK_PER_TRADE_PCT  = 1.0   # 1% risk per trade
MAX_OPEN_TRADES     = 3
MAX_DAILY_LOSS_PCT  = 3.0   # Stop trading if daily loss > 3%
TARGET_MONTHLY_PCT  = 5.0   # 5% per month target
XAUUSD_PIP_VALUE    = 0.1   # Per mini-lot (0.01) per pip
LOT_STEP            = 0.01  # Min lot size


def calculate_lot_size(entry: float, sl: float, balance: float = None, risk_pct: float = RISK_PER_TRADE_PCT) -> float:
    """Calculate lot size based on risk % of balance."""
    if balance is None:
        balance = get_balance()

    risk_amount = balance * (risk_pct / 100)
    sl_pips     = abs(entry - sl) * 10  # 1 pip = $0.10 for XAUUSD in USD

    if sl_pips == 0:
        return LOT_STEP

    # For XAUUSD: 1 standard lot = 100 oz; pip value ≈ $1/pip per mini-lot
    # $1 per pip per 0.01 lot (mini), so:
    lot_size = risk_amount / (sl_pips * 1.0 / LOT_STEP)
    lot_size = max(LOT_STEP, round(lot_size / LOT_STEP) * LOT_STEP)
    lot_size = min(lot_size, 1.0)  # Max 1 lot per trade
    return lot_size


def calculate_pnl(direction: str, entry: float, exit_price: float, lot_size: float) -> float:
    """Calculate PnL in USD for XAUUSD."""
    pips = (exit_price - entry) * 10
    if direction == "SELL":
        pips = -pips
    # $1 per pip per 0.01 lot
    return round(pips * (lot_size / LOT_STEP), 2)


def get_monthly_stats(balance: float) -> dict:
    """Calculate current month performance."""
    from datetime import datetime, timezone
    import pandas as pd

    trades = get_trades()
    if trades.empty:
        return {"pnl": 0, "target": balance * TARGET_MONTHLY_PCT / 100, "progress_pct": 0}

    trades["closed_at"] = pd.to_datetime(trades["closed_at"], errors="coerce")
    now = datetime.now(timezone.utc)
    month_trades = trades[
        (trades["status"] == "closed") &
        (trades["closed_at"].dt.month == now.month) &
        (trades["closed_at"].dt.year == now.year)
    ]
    monthly_pnl = month_trades["pnl"].sum() if not month_trades.empty else 0
    target      = balance * TARGET_MONTHLY_PCT / 100
    progress    = (monthly_pnl / target * 100) if target > 0 else 0
    return {"pnl": monthly_pnl, "target": target, "progress_pct": min(progress, 100)}


def get_daily_pnl() -> float:
    """Get today's realized PnL."""
    from datetime import datetime, timezone
    import pandas as pd

    trades = get_trades()
    if trades.empty:
        return 0.0
    trades["closed_at"] = pd.to_datetime(trades["closed_at"], errors="coerce")
    now = datetime.now(timezone.utc)
    today = trades[
        (trades["status"] == "closed") &
        (trades["closed_at"].dt.date == now.date())
    ]
    return today["pnl"].sum() if not today.empty else 0.0


def should_trade(balance: float) -> tuple[bool, str]:
    """Check if bot should place new trades based on risk rules."""
    open_trades = get_trades(status="open")
    if len(open_trades) >= MAX_OPEN_TRADES:
        return False, f"Max open trades ({MAX_OPEN_TRADES}) reached"

    daily_pnl = get_daily_pnl()
    max_daily_loss = -balance * MAX_DAILY_LOSS_PCT / 100
    if daily_pnl < max_daily_loss:
        return False, f"Daily loss limit hit (${daily_pnl:.2f})"

    return True, "OK"


def get_performance_summary(initial_balance: float = 5000.0) -> dict:
    """Compute full performance statistics."""
    import pandas as pd
    import numpy as np

    trades = get_trades(status="closed")
    balance = get_balance()

    if trades.empty:
        return {
            "balance": balance,
            "total_pnl": 0,
            "total_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "avg_rr": 0,
        }

    pnls    = trades["pnl"].values
    wins    = pnls[pnls > 0]
    losses  = pnls[pnls < 0]

    win_rate      = len(wins) / len(pnls) * 100 if len(pnls) > 0 else 0
    profit_factor = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else 0
    total_pnl     = pnls.sum()

    # Max drawdown
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / (peak + initial_balance + 1e-9)
    max_dd   = abs(drawdown.min()) * 100

    return {
        "balance":      balance,
        "total_pnl":    round(total_pnl, 2),
        "total_trades": len(pnls),
        "win_rate":     round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_rr":       0,
    }
