"""
Live data fetcher for XAUUSD (GC=F) and DXY (DX-Y.NYB).
Falls back to synthetic data if yfinance is unavailable (demo mode).
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

XAUUSD_TICKER = "GC=F"
DXY_TICKER    = "DX-Y.NYB"

TIMEFRAME_MAP = {
    "M15": ("15m", 7),
    "H1":  ("1h",  30),
    "H4":  ("4h",  60),
    "D1":  ("1d",  365),
}


def fetch_ohlcv(ticker: str, interval: str = "1h", days: int = 30) -> pd.DataFrame:
    try:
        end   = datetime.now()
        start = end - timedelta(days=days)
        df = yf.download(
            ticker, start=start, end=end,
            interval=interval, progress=False, auto_adjust=True
        )
        if df is None or df.empty:
            return _synthetic(ticker, interval, days)

        # Flatten MultiIndex columns (yfinance ≥0.2.38)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]

        rename_map = {"open":"open","high":"high","low":"low","close":"close","volume":"volume"}
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        df = df[["open","high","low","close","volume"]].dropna()
        df.index = pd.to_datetime(df.index)
        return df

    except Exception as e:
        print(f"[DataFetcher] yfinance error ({ticker}): {e}")
        return _synthetic(ticker, interval, days)


def _synthetic(ticker: str, interval: str, days: int) -> pd.DataFrame:
    """Realistic synthetic OHLCV — used as demo fallback."""
    is_gold = "GC" in ticker or "XAU" in ticker
    base    = 2350.0 if is_gold else 104.5
    spread  = 12.0   if is_gold else 0.35

    freq_map = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}
    freq = freq_map.get(interval, "1h")

    end     = pd.Timestamp.now(tz="UTC").floor(freq)
    periods = {"15m": days * 96, "1h": days * 24, "4h": days * 6, "1d": days}.get(interval, days * 24)
    periods = min(periods, 600)
    idx     = pd.date_range(end=end, periods=periods, freq=freq, tz="UTC")

    np.random.seed(12 if is_gold else 7)
    rets   = np.random.normal(0.00005, 0.0028, len(idx))
    prices = base * np.cumprod(1 + rets)

    rows = []
    for p in prices:
        o  = p * (1 + np.random.uniform(-0.0008, 0.0008))
        h  = max(o, p) + abs(np.random.normal(0, spread * 0.4))
        l  = min(o, p) - abs(np.random.normal(0, spread * 0.4))
        v  = abs(np.random.normal(12000, 3500))
        rows.append({"open": o, "high": h, "low": l, "close": p, "volume": v})

    return pd.DataFrame(rows, index=idx)


def get_xauusd(timeframe: str = "H1") -> pd.DataFrame:
    interval, days = TIMEFRAME_MAP.get(timeframe, ("1h", 30))
    return fetch_ohlcv(XAUUSD_TICKER, interval, days)


def get_dxy(timeframe: str = "H1") -> pd.DataFrame:
    interval, days = TIMEFRAME_MAP.get(timeframe, ("1h", 30))
    return fetch_ohlcv(DXY_TICKER, interval, days)


def get_latest_price() -> float:
    try:
        t     = yf.Ticker(XAUUSD_TICKER)
        info  = t.fast_info
        price = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
        if price and float(price) > 100:
            return float(price)
    except Exception:
        pass
    try:
        df = fetch_ohlcv(XAUUSD_TICKER, "1h", 2)
        if not df.empty:
            return float(df["close"].iloc[-1])
    except Exception:
        pass
    return 2350.0


def get_current_session() -> str:
    hour = datetime.now(pytz.utc).hour
    if 22 <= hour or hour < 8:
        return "Asian"
    elif 8 <= hour < 13:
        return "London"
    else:
        return "New York"


def get_dxy_bias(dxy_df: pd.DataFrame) -> str:
    if dxy_df is None or len(dxy_df) < 20:
        return "Neutral"
    sma20 = dxy_df["close"].iloc[-20:].mean()
    last  = dxy_df["close"].iloc[-1]
    if last > sma20 * 1.002:
        return "Bearish (DXY ↑)"
    elif last < sma20 * 0.998:
        return "Bullish (DXY ↓)"
    return "Neutral"


def get_macro_events() -> list:
    return [
        {"event": "US CPI",       "impact": "High",   "date": "2025-06-11"},
        {"event": "FOMC Meeting",  "impact": "High",   "date": "2025-06-17"},
        {"event": "US PPI",        "impact": "Medium", "date": "2025-06-13"},
        {"event": "NFP",           "impact": "High",   "date": "2025-06-06"},
        {"event": "GDP Q1 Final",  "impact": "Medium", "date": "2025-06-26"},
        {"event": "PCE Deflator",  "impact": "High",   "date": "2025-06-27"},
    ]
