"""
Technical indicators: EMA, ATR, ADX, Volume Profile, SMC concepts
(CHoCH, BOS, OB, FVG, Liquidity).
"""
import pandas as pd
import numpy as np


# ─── EMA ──────────────────────────────────────────────────────────────────────
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


# ─── ATR ──────────────────────────────────────────────────────────────────────
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ─── ADX ──────────────────────────────────────────────────────────────────────
def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up   = h.diff()
    down = -l.diff()
    plus_dm  = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)

    tr_s = atr(df, period)
    plus_di  = 100 * pd.Series(plus_dm,  index=df.index).ewm(span=period, adjust=False).mean() / tr_s
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(span=period, adjust=False).mean() / tr_s
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
    return dx.ewm(span=period, adjust=False).mean(), plus_di, minus_di


# ─── RSI ──────────────────────────────────────────────────────────────────────
def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs   = gain / (loss + 1e-9)
    return 100 - 100 / (1 + rs)


# ─── BOLLINGER BANDS ──────────────────────────────────────────────────────────
def bollinger(series: pd.Series, period: int = 20, std: float = 2.0):
    mid = series.rolling(period).mean()
    sd  = series.rolling(period).std()
    return mid - std * sd, mid, mid + std * sd


# ─── MARKET REGIME ────────────────────────────────────────────────────────────
def market_regime(df: pd.DataFrame) -> str:
    """
    Bull:   ADX>25 AND EMA20>EMA50>EMA200
    Bear:   ADX>25 AND EMA20<EMA50<EMA200
    Ranging: ADX<25
    High Volatile: ATR > 1.5× mean ATR
    Low Liquidity: volume < 0.5× mean volume
    """
    if len(df) < 200:
        return "Unknown"

    adx_val, _, _ = adx(df)
    adx_cur = adx_val.iloc[-1]

    e20  = ema(df["close"], 20).iloc[-1]
    e50  = ema(df["close"], 50).iloc[-1]
    e200 = ema(df["close"], 200).iloc[-1]

    atr_cur  = atr(df).iloc[-1]
    atr_mean = atr(df).rolling(50).mean().iloc[-1]

    vol_cur  = df["volume"].iloc[-1]
    vol_mean = df["volume"].rolling(50).mean().iloc[-1]

    if vol_cur < 0.5 * vol_mean:
        return "Low Liquidity"
    if atr_cur > 1.5 * atr_mean:
        return "High Volatile"
    if adx_cur > 25:
        if e20 > e50 > e200:
            return "Bull"
        elif e20 < e50 < e200:
            return "Bear"
    return "Ranging"


# ─── SUPPORT / RESISTANCE ─────────────────────────────────────────────────────
def find_sr_levels(df: pd.DataFrame, window: int = 20, n_levels: int = 8) -> dict:
    """Pivot-based S/R detection."""
    highs = df["high"].values
    lows  = df["low"].values
    resistance, support = [], []

    for i in range(window, len(df) - window):
        if highs[i] == max(highs[i-window:i+window]):
            resistance.append(highs[i])
        if lows[i] == min(lows[i-window:i+window]):
            support.append(lows[i])

    def cluster(levels, n):
        if not levels:
            return []
        levels = sorted(set(levels))
        clustered, group = [], [levels[0]]
        for lv in levels[1:]:
            if lv - group[-1] < group[-1] * 0.003:
                group.append(lv)
            else:
                clustered.append(np.mean(group))
                group = [lv]
        clustered.append(np.mean(group))
        return sorted(clustered)[-n:]

    return {
        "resistance": cluster(resistance, n_levels),
        "support":    cluster(support, n_levels),
    }


# ─── VOLUME PROFILE (POC, VAH, VAL) ──────────────────────────────────────────
def volume_profile(df: pd.DataFrame, bins: int = 50) -> dict:
    price_min = df["low"].min()
    price_max = df["high"].max()
    price_bins = np.linspace(price_min, price_max, bins + 1)
    vol_by_price = np.zeros(bins)

    for _, row in df.iterrows():
        lo, hi, vol = row["low"], row["high"], row["volume"]
        for j in range(bins):
            bin_lo, bin_hi = price_bins[j], price_bins[j+1]
            overlap = max(0, min(hi, bin_hi) - max(lo, bin_lo))
            if overlap > 0:
                vol_by_price[j] += vol * overlap / (hi - lo + 1e-9)

    poc_idx = np.argmax(vol_by_price)
    poc = (price_bins[poc_idx] + price_bins[poc_idx+1]) / 2

    total_vol = vol_by_price.sum()
    cum = 0
    vah_idx, val_idx = poc_idx, poc_idx
    for step in range(bins):
        up   = poc_idx + step if poc_idx + step < bins else None
        down = poc_idx - step if poc_idx - step >= 0 else None
        if up is not None:   cum += vol_by_price[up]
        if down is not None: cum += vol_by_price[down]
        if up is not None:   vah_idx = up
        if down is not None: val_idx = down
        if cum >= 0.70 * total_vol:
            break

    return {
        "poc": poc,
        "vah": (price_bins[vah_idx] + price_bins[vah_idx+1]) / 2,
        "val": (price_bins[val_idx] + price_bins[val_idx+1]) / 2,
        "profile": vol_by_price.tolist(),
        "price_bins": price_bins.tolist(),
    }


# ─── SMC: FAIR VALUE GAPS ─────────────────────────────────────────────────────
def find_fvg(df: pd.DataFrame) -> list:
    """Identify bullish and bearish Fair Value Gaps."""
    gaps = []
    for i in range(2, len(df)):
        # Bullish FVG: candle[i-2].high < candle[i].low
        if df["high"].iloc[i-2] < df["low"].iloc[i]:
            gaps.append({
                "type": "bullish",
                "top":  df["low"].iloc[i],
                "bottom": df["high"].iloc[i-2],
                "index": i,
                "time": df.index[i],
            })
        # Bearish FVG: candle[i-2].low > candle[i].high
        elif df["low"].iloc[i-2] > df["high"].iloc[i]:
            gaps.append({
                "type": "bearish",
                "top":  df["low"].iloc[i-2],
                "bottom": df["high"].iloc[i],
                "index": i,
                "time": df.index[i],
            })
    return gaps[-20:]  # last 20


# ─── SMC: ORDER BLOCKS ────────────────────────────────────────────────────────
def find_order_blocks(df: pd.DataFrame) -> list:
    """Detect bullish/bearish order blocks."""
    obs = []
    closes = df["close"].values
    for i in range(3, len(df) - 1):
        # Bearish OB: last down candle before impulsive up move
        if closes[i-1] < closes[i-2] and closes[i] > closes[i-1] * 1.005:
            obs.append({
                "type": "bullish_ob",
                "top":    df["high"].iloc[i-1],
                "bottom": df["low"].iloc[i-1],
                "time":   df.index[i-1],
            })
        # Bullish OB: last up candle before impulsive down move
        if closes[i-1] > closes[i-2] and closes[i] < closes[i-1] * 0.995:
            obs.append({
                "type": "bearish_ob",
                "top":    df["high"].iloc[i-1],
                "bottom": df["low"].iloc[i-1],
                "time":   df.index[i-1],
            })
    return obs[-20:]


# ─── SMC: CHoCH / BOS ─────────────────────────────────────────────────────────
def find_choch_bos(df: pd.DataFrame) -> list:
    """Detect Change of Character and Break of Structure."""
    events = []
    highs = df["high"].values
    lows  = df["low"].values
    closes = df["close"].values
    swing_len = 5

    for i in range(swing_len * 2, len(df)):
        # BOS Bullish: price breaks above recent swing high
        prev_high = max(highs[i-swing_len*2:i-swing_len])
        if closes[i] > prev_high and closes[i-1] <= prev_high:
            events.append({"type": "BOS_Bull", "price": prev_high, "time": df.index[i]})
        # BOS Bearish
        prev_low = min(lows[i-swing_len*2:i-swing_len])
        if closes[i] < prev_low and closes[i-1] >= prev_low:
            events.append({"type": "BOS_Bear", "price": prev_low, "time": df.index[i]})
        # CHoCH: after downtrend, higher high formed
        if i > swing_len * 3:
            recent_highs = [highs[j] for j in range(i-swing_len*3, i-swing_len, swing_len)]
            if len(recent_highs) >= 2 and highs[i] > recent_highs[-1] > recent_highs[-2]:
                events.append({"type": "CHoCH_Bull", "price": highs[i], "time": df.index[i]})
    return events[-30:]


# ─── SMC: LIQUIDITY SWEEPS ────────────────────────────────────────────────────
def find_liquidity_sweeps(df: pd.DataFrame, window: int = 20) -> list:
    """Identify equal highs/lows (liquidity pools) and sweeps."""
    sweeps = []
    highs  = df["high"].values
    lows   = df["low"].values
    closes = df["close"].values
    tol    = 0.001  # 0.1% tolerance for "equal" levels

    for i in range(window, len(df)):
        # Equal highs (buy-side liquidity)
        eq_highs = [h for h in highs[i-window:i] if abs(h - highs[i-window]) / highs[i-window] < tol]
        if len(eq_highs) >= 2:
            liq_level = np.mean(eq_highs)
            if highs[i] > liq_level * 1.001 and closes[i] < liq_level:
                sweeps.append({
                    "type": "buy_side_sweep", "level": liq_level, "time": df.index[i]
                })
        # Equal lows (sell-side liquidity)
        eq_lows = [l for l in lows[i-window:i] if abs(l - lows[i-window]) / lows[i-window] < tol]
        if len(eq_lows) >= 2:
            liq_level = np.mean(eq_lows)
            if lows[i] < liq_level * 0.999 and closes[i] > liq_level:
                sweeps.append({
                    "type": "sell_side_sweep", "level": liq_level, "time": df.index[i]
                })
    return sweeps[-20:]


# ─── ADD ALL INDICATORS TO DATAFRAME ─────────────────────────────────────────
def enrich_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema20"]  = ema(df["close"], 20)
    df["ema50"]  = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)
    df["atr"]    = atr(df)
    adx_v, pdi, mdi = adx(df)
    df["adx"]    = adx_v
    df["plus_di"] = pdi
    df["minus_di"] = mdi
    df["rsi"]    = rsi(df["close"])
    bb_lo, bb_mid, bb_hi = bollinger(df["close"])
    df["bb_lo"]  = bb_lo
    df["bb_mid"] = bb_mid
    df["bb_hi"]  = bb_hi
    df["vol_sma"] = df["volume"].rolling(20).mean()
    return df
