"""
Backtesting engine: walk-forward simulation of all strategies on historical data.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from core.indicators import enrich_df, market_regime, find_sr_levels, find_liquidity_sweeps, find_fvg, find_order_blocks, find_choch_bos
from core.database import save_backtest


def backtest_strategy(df: pd.DataFrame, strategy: str = "All", initial_balance: float = 5000.0,
                      risk_pct: float = 1.0, atr_sl_mult: float = 1.5, atr_tp_mult: float = 3.0) -> dict:
    """
    Walk-forward backtest on a single DataFrame (H1 recommended).
    Returns trade log and performance metrics.
    """
    df_e = enrich_df(df)
    trades = []
    balance = initial_balance
    equity_curve = [balance]
    min_bars = 200

    for i in range(min_bars, len(df_e) - 1):
        window = df_e.iloc[:i+1]
        close  = window["close"].iloc[-1]
        atr_v  = window["atr"].iloc[-1]
        adx_v  = window["adx"].iloc[-1]
        e20    = window["ema20"].iloc[-1]
        e20p   = window["ema20"].iloc[-2]
        e50    = window["ema50"].iloc[-1]
        e50p   = window["ema50"].iloc[-2]
        e200   = window["ema200"].iloc[-1]
        rsi_v  = window["rsi"].iloc[-1]
        vol    = window["volume"].iloc[-1]
        vol_ma = window["vol_sma"].iloc[-1]

        signals_to_test = []

        # ─ Strategy D: EMA Cross
        if strategy in ("All", "EMA Momentum"):
            if e20p <= e50p and e20 > e50 and rsi_v < 70:
                signals_to_test.append(("BUY", "EMA Momentum"))
            elif e20p >= e50p and e20 < e50 and rsi_v > 30:
                signals_to_test.append(("SELL", "EMA Momentum"))

        # ─ Strategy B: Trend Continuation
        if strategy in ("All", "Trend Continuation"):
            if e20 > e50 > e200 and adx_v > 25 and abs(close - e20) / atr_v < 1.0:
                signals_to_test.append(("BUY", "Trend Continuation"))
            elif e20 < e50 < e200 and adx_v > 25 and abs(close - e20) / atr_v < 1.0:
                signals_to_test.append(("SELL", "Trend Continuation"))

        # ─ Strategy C: Breakout
        if strategy in ("All", "Breakout"):
            sr = find_sr_levels(window, window=15, n_levels=5)
            prev_close = window["close"].iloc[-2]
            for res in sr.get("resistance", []):
                if prev_close < res < close and vol > vol_ma * 1.3:
                    signals_to_test.append(("BUY", "Breakout"))
            for sup in sr.get("support", []):
                if prev_close > sup > close and vol > vol_ma * 1.3:
                    signals_to_test.append(("SELL", "Breakout"))

        # Process first valid signal only
        for direction, strat_name in signals_to_test[:1]:
            entry = close
            if direction == "BUY":
                sl = entry - atr_v * atr_sl_mult
                tp = entry + atr_v * atr_tp_mult
            else:
                sl = entry + atr_v * atr_sl_mult
                tp = entry - atr_v * atr_tp_mult

            risk_amt = balance * risk_pct / 100
            sl_dist  = abs(entry - sl)
            lot_size = max(0.01, min(risk_amt / (sl_dist * 100 + 1e-9), 1.0))

            # Simulate trade outcome on next candles
            outcome = _simulate_trade(df_e.iloc[i+1:i+50], direction, entry, sl, tp)

            if direction == "BUY":
                pnl = (outcome["exit"] - entry) * lot_size * 100
            else:
                pnl = (entry - outcome["exit"]) * lot_size * 100

            balance += pnl
            trades.append({
                "index": i,
                "time":  df_e.index[i].isoformat(),
                "strategy": strat_name,
                "direction": direction,
                "entry":  entry,
                "sl":     sl,
                "tp":     tp,
                "exit":   outcome["exit"],
                "outcome": outcome["result"],
                "pnl":    round(pnl, 2),
                "balance": round(balance, 2),
            })
            equity_curve.append(balance)
            break  # 1 signal per bar

    trades_df = pd.DataFrame(trades)
    return _compute_metrics(trades_df, equity_curve, initial_balance, strategy, {
        "risk_pct": risk_pct, "atr_sl_mult": atr_sl_mult, "atr_tp_mult": atr_tp_mult
    })


def _simulate_trade(future: pd.DataFrame, direction: str, entry: float, sl: float, tp: float) -> dict:
    """Check future candles to see if TP or SL is hit first."""
    for _, row in future.iterrows():
        if direction == "BUY":
            if row["low"] <= sl:
                return {"result": "loss", "exit": sl}
            if row["high"] >= tp:
                return {"result": "win", "exit": tp}
        else:
            if row["high"] >= sl:
                return {"result": "loss", "exit": sl}
            if row["low"] <= tp:
                return {"result": "win", "exit": tp}
    # Timed out
    last = future["close"].iloc[-1] if not future.empty else entry
    return {"result": "timeout", "exit": last}


def _compute_metrics(trades_df: pd.DataFrame, equity_curve: list, initial_balance: float, strategy: str, params: dict) -> dict:
    if trades_df.empty:
        result = {
            "strategy": strategy, "total_trades": 0, "win_rate": 0,
            "profit_factor": 0, "max_drawdown": 0, "net_pnl": 0,
            "final_balance": initial_balance, "params": params,
            "trades": [], "equity_curve": equity_curve,
        }
        save_backtest(result)
        return result

    wins   = trades_df[trades_df["outcome"] == "win"]["pnl"]
    losses = trades_df[trades_df["outcome"] == "loss"]["pnl"]

    win_rate      = len(wins) / len(trades_df) * 100
    profit_factor = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else 0
    net_pnl       = trades_df["pnl"].sum()

    eq = np.array(equity_curve)
    peak = np.maximum.accumulate(eq)
    dd   = (eq - peak) / (peak + 1e-9)
    max_dd = abs(dd.min()) * 100

    result = {
        "strategy":       strategy,
        "total_trades":   len(trades_df),
        "win_rate":       round(win_rate, 1),
        "profit_factor":  round(profit_factor, 2),
        "max_drawdown":   round(max_dd, 2),
        "net_pnl":        round(net_pnl, 2),
        "final_balance":  round(initial_balance + net_pnl, 2),
        "params":         params,
        "trades":         trades_df.to_dict("records"),
        "equity_curve":   equity_curve,
    }
    save_backtest(result)
    return result
