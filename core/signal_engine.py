"""
Signal engine: implements 5 strategies and produces buy/sell signals with confidence scores.
Strategies:
  a. Liquidity Sweeps
  b. Trend Continuation
  c. Breakout
  d. EMA Momentum
  e. SMC (CHoCH, BOS, OB, FVG, Liq Pulls)
"""
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from core.indicators import (
    enrich_df, market_regime, find_sr_levels, volume_profile,
    find_fvg, find_order_blocks, find_choch_bos, find_liquidity_sweeps
)
from core.data_fetcher import get_current_session, get_dxy_bias


def _make_signal(direction, entry, sl, tp, strategy, confidence, regime, session, dxy_bias, notes=""):
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    return {
        "signal_id":  str(uuid.uuid4())[:8].upper(),
        "direction":  direction,
        "entry":      round(entry, 2),
        "sl":         round(sl, 2),
        "tp":         round(tp, 2),
        "rr":         round(rr, 2),
        "strategy":   strategy,
        "confidence": round(min(confidence, 99.0), 1),
        "regime":     regime,
        "session":    session,
        "dxy_bias":   dxy_bias,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status":     "pending",
        "notes":      notes,
    }


# ─── STRATEGY A: LIQUIDITY SWEEP ──────────────────────────────────────────────
def strategy_liq_sweep(df: pd.DataFrame, df_e: pd.DataFrame, sr: dict, regime: str, session: str, dxy_bias: str) -> list:
    signals = []
    sweeps = find_liquidity_sweeps(df, window=20)
    if not sweeps:
        return signals

    last_sweep = sweeps[-1]
    last_close = df_e["close"].iloc[-1]
    atr_v = df_e["atr"].iloc[-1]

    # After buy-side sweep: expect reversal down
    if last_sweep["type"] == "buy_side_sweep":
        entry = last_close
        sl    = entry + atr_v * 1.5
        tp    = entry - atr_v * 3.0
        conf  = 65 + (10 if regime in ["Bear", "Ranging"] else 0) + (5 if "Bearish" in dxy_bias else 0)
        if regime not in ["Bull"]:
            signals.append(_make_signal("SELL", entry, sl, tp, "Liq Sweep", conf, regime, session, dxy_bias,
                                        f"Buy-side liq swept at {last_sweep['level']:.2f}"))

    # After sell-side sweep: expect reversal up
    elif last_sweep["type"] == "sell_side_sweep":
        entry = last_close
        sl    = entry - atr_v * 1.5
        tp    = entry + atr_v * 3.0
        conf  = 65 + (10 if regime in ["Bull", "Ranging"] else 0) + (5 if "Bullish" in dxy_bias else 0)
        if regime not in ["Bear"]:
            signals.append(_make_signal("BUY", entry, sl, tp, "Liq Sweep", conf, regime, session, dxy_bias,
                                        f"Sell-side liq swept at {last_sweep['level']:.2f}"))
    return signals


# ─── STRATEGY B: TREND CONTINUATION ──────────────────────────────────────────
def strategy_trend_continuation(df_e: pd.DataFrame, sr: dict, regime: str, session: str, dxy_bias: str) -> list:
    signals = []
    close  = df_e["close"].iloc[-1]
    e20    = df_e["ema20"].iloc[-1]
    e50    = df_e["ema50"].iloc[-1]
    e200   = df_e["ema200"].iloc[-1]
    rsi_v  = df_e["rsi"].iloc[-1]
    atr_v  = df_e["atr"].iloc[-1]
    adx_v  = df_e["adx"].iloc[-1]

    if adx_v < 20:
        return signals  # No trend to continue

    # Bullish continuation: price pulls back to EMA20 in uptrend
    if e20 > e50 > e200 and regime == "Bull":
        if abs(close - e20) / atr_v < 1.0 and rsi_v < 60:
            entry = close
            sl    = e50 - atr_v * 0.5
            tp    = entry + (entry - sl) * 2.5
            conf  = 70 + (5 if adx_v > 30 else 0) + (5 if "Bullish" in dxy_bias else 0)
            signals.append(_make_signal("BUY", entry, sl, tp, "Trend Continuation", conf,
                                        regime, session, dxy_bias, "EMA20 pullback in uptrend"))

    # Bearish continuation
    elif e20 < e50 < e200 and regime == "Bear":
        if abs(close - e20) / atr_v < 1.0 and rsi_v > 40:
            entry = close
            sl    = e50 + atr_v * 0.5
            tp    = entry - (sl - entry) * 2.5
            conf  = 70 + (5 if adx_v > 30 else 0) + (5 if "Bearish" in dxy_bias else 0)
            signals.append(_make_signal("SELL", entry, sl, tp, "Trend Continuation", conf,
                                        regime, session, dxy_bias, "EMA20 pullback in downtrend"))
    return signals


# ─── STRATEGY C: BREAKOUT ─────────────────────────────────────────────────────
def strategy_breakout(df: pd.DataFrame, df_e: pd.DataFrame, sr: dict, regime: str, session: str, dxy_bias: str) -> list:
    signals = []
    close   = df_e["close"].iloc[-1]
    prev_close = df_e["close"].iloc[-2]
    atr_v   = df_e["atr"].iloc[-1]
    vol     = df_e["volume"].iloc[-1]
    vol_avg = df_e["vol_sma"].iloc[-1]

    for res in sr.get("resistance", []):
        # Bullish breakout above resistance
        if prev_close < res < close and vol > vol_avg * 1.3:
            sl   = res - atr_v * 0.8
            tp   = close + atr_v * 3.0
            conf = 68 + (8 if vol > vol_avg * 1.5 else 0) + (5 if session in ["London", "New York"] else 0)
            signals.append(_make_signal("BUY", close, sl, tp, "Breakout", conf,
                                        regime, session, dxy_bias, f"Bullish breakout above {res:.2f}"))

    for sup in sr.get("support", []):
        # Bearish breakdown below support
        if prev_close > sup > close and vol > vol_avg * 1.3:
            sl   = sup + atr_v * 0.8
            tp   = close - atr_v * 3.0
            conf = 68 + (8 if vol > vol_avg * 1.5 else 0) + (5 if session in ["London", "New York"] else 0)
            signals.append(_make_signal("SELL", close, sl, tp, "Breakout", conf,
                                        regime, session, dxy_bias, f"Bearish breakdown below {sup:.2f}"))

    return signals[:1]  # max 1 breakout signal


# ─── STRATEGY D: EMA MOMENTUM ─────────────────────────────────────────────────
def strategy_ema_momentum(df_e: pd.DataFrame, regime: str, session: str, dxy_bias: str) -> list:
    signals = []
    close   = df_e["close"].iloc[-1]
    e20_cur = df_e["ema20"].iloc[-1]
    e20_prev = df_e["ema20"].iloc[-2]
    e50_cur = df_e["ema50"].iloc[-1]
    e50_prev = df_e["ema50"].iloc[-2]
    atr_v   = df_e["atr"].iloc[-1]
    rsi_v   = df_e["rsi"].iloc[-1]

    # EMA20 crosses above EMA50 → BUY
    if e20_prev <= e50_prev and e20_cur > e50_cur:
        if rsi_v < 70:
            entry = close
            sl    = entry - atr_v * 1.5
            tp    = entry + atr_v * 3.5
            conf  = 72 + (5 if regime == "Bull" else 0) + (5 if "Bullish" in dxy_bias else 0)
            signals.append(_make_signal("BUY", entry, sl, tp, "EMA Momentum", conf,
                                        regime, session, dxy_bias, "EMA20 crossed above EMA50"))

    # EMA20 crosses below EMA50 → SELL
    elif e20_prev >= e50_prev and e20_cur < e50_cur:
        if rsi_v > 30:
            entry = close
            sl    = entry + atr_v * 1.5
            tp    = entry - atr_v * 3.5
            conf  = 72 + (5 if regime == "Bear" else 0) + (5 if "Bearish" in dxy_bias else 0)
            signals.append(_make_signal("SELL", entry, sl, tp, "EMA Momentum", conf,
                                        regime, session, dxy_bias, "EMA20 crossed below EMA50"))
    return signals


# ─── STRATEGY E: SMC ──────────────────────────────────────────────────────────
def strategy_smc(df: pd.DataFrame, df_e: pd.DataFrame, regime: str, session: str, dxy_bias: str) -> list:
    signals = []
    close   = df_e["close"].iloc[-1]
    atr_v   = df_e["atr"].iloc[-1]

    fvgs    = find_fvg(df)
    obs     = find_order_blocks(df)
    events  = find_choch_bos(df)

    # Latest CHoCH/BOS
    if events:
        last_ev = events[-1]
        if last_ev["type"] in ("CHoCH_Bull", "BOS_Bull"):
            # Look for OB below price or FVG
            for ob in reversed(obs):
                if ob["type"] == "bullish_ob" and ob["bottom"] < close < ob["top"] + atr_v:
                    sl   = ob["bottom"] - atr_v * 0.5
                    tp   = close + (close - sl) * 2.5
                    conf = 75 + (5 if last_ev["type"] == "CHoCH_Bull" else 0) + (5 if "Bullish" in dxy_bias else 0)
                    signals.append(_make_signal("BUY", close, sl, tp, "SMC", conf,
                                                regime, session, dxy_bias,
                                                f"{last_ev['type']} + Bullish OB @ {ob['bottom']:.2f}-{ob['top']:.2f}"))
                    break

        elif last_ev["type"] in ("BOS_Bear",):
            for ob in reversed(obs):
                if ob["type"] == "bearish_ob" and ob["bottom"] < close < ob["top"] + atr_v:
                    sl   = ob["top"] + atr_v * 0.5
                    tp   = close - (sl - close) * 2.5
                    conf = 75 + (5 if "Bearish" in dxy_bias else 0)
                    signals.append(_make_signal("SELL", close, sl, tp, "SMC", conf,
                                                regime, session, dxy_bias,
                                                f"BOS Bear + Bearish OB @ {ob['bottom']:.2f}-{ob['top']:.2f}"))
                    break

    # FVG fill signals
    for fvg in reversed(fvgs):
        if fvg["type"] == "bullish" and fvg["bottom"] < close < fvg["top"]:
            sl   = fvg["bottom"] - atr_v * 0.5
            tp   = close + (close - sl) * 2.0
            conf = 65
            signals.append(_make_signal("BUY", close, sl, tp, "SMC-FVG", conf,
                                        regime, session, dxy_bias, f"Price in bullish FVG"))
            break
        elif fvg["type"] == "bearish" and fvg["bottom"] < close < fvg["top"]:
            sl   = fvg["top"] + atr_v * 0.5
            tp   = close - (sl - close) * 2.0
            conf = 65
            signals.append(_make_signal("SELL", close, sl, tp, "SMC-FVG", conf,
                                        regime, session, dxy_bias, f"Price in bearish FVG"))
            break

    return signals[:1]


# ─── MASTER SIGNAL GENERATOR ──────────────────────────────────────────────────
def generate_signals(df_m15: pd.DataFrame, df_h1: pd.DataFrame, dxy_df: pd.DataFrame = None) -> list:
    """Run all strategies and return top-ranked signals."""
    if df_h1 is None or len(df_h1) < 50:
        return []

    df_e   = enrich_df(df_h1)
    regime = market_regime(df_e)
    session = get_current_session()
    dxy_bias = get_dxy_bias(dxy_df) if dxy_df is not None else "Neutral"
    sr     = find_sr_levels(df_h1)

    all_signals = []

    # Run all strategies
    try:
        all_signals += strategy_liq_sweep(df_h1, df_e, sr, regime, session, dxy_bias)
    except Exception as e:
        print(f"[SignalEngine] Liq sweep error: {e}")

    try:
        all_signals += strategy_trend_continuation(df_e, sr, regime, session, dxy_bias)
    except Exception as e:
        print(f"[SignalEngine] Trend cont error: {e}")

    try:
        all_signals += strategy_breakout(df_h1, df_e, sr, regime, session, dxy_bias)
    except Exception as e:
        print(f"[SignalEngine] Breakout error: {e}")

    try:
        all_signals += strategy_ema_momentum(df_e, regime, session, dxy_bias)
    except Exception as e:
        print(f"[SignalEngine] EMA momentum error: {e}")

    try:
        all_signals += strategy_smc(df_h1, df_e, regime, session, dxy_bias)
    except Exception as e:
        print(f"[SignalEngine] SMC error: {e}")

    # Filter: RR >= 1.5, confidence >= 60
    valid = [s for s in all_signals if s.get("rr", 0) >= 1.5 and s.get("confidence", 0) >= 60]

    # Sort by confidence descending
    valid.sort(key=lambda x: x["confidence"], reverse=True)

    # De-duplicate: only 1 BUY and 1 SELL max
    seen_dir = set()
    unique = []
    for s in valid:
        if s["direction"] not in seen_dir:
            unique.append(s)
            seen_dir.add(s["direction"])

    return unique
