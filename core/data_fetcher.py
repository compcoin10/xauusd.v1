"""
Live data fetcher for XAUUSD (GC=F), DXY (DX-Y.NYB) and macro indicators.
Uses yfinance as primary source with fallback simulation for demo mode.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time

XAUUSD_TICKER = "GC=F"
DXY_TICKER = "DX-Y.NYB"

TIMEFRAME_MAP = {
    "M15": ("15m", 7),      # interval, days back
    "H1":  ("1h",  30),
    "H4":  ("4h",  60),
    "D1":  ("1d",  365),
}

def fetch_ohlcv(ticker: str, interval: str = "1h", days: int = 30) -> pd.DataFrame:
    """Fetch OHLCV data from yfinance."""
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        df = yf.download(ticker, start=start, end=end, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return _generate_synthetic(ticker, interval, days)

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        })
        # Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df
    except Exception as e:
        print(f"[DataFetcher] yfinance error for {ticker}: {e}")
        return _generate_synthetic(ticker, interval, days)


def _generate_synthetic(ticker: str, interval: str, days: int) -> pd.DataFrame:
    """Generate realistic synthetic OHLCV for demo/fallback."""
    base_price = 2350.0 if "GC" in ticker or "XAU" in ticker else 104.0
    vol_factor = 15.0 if "GC" in ticker else 0.4

    freq_map = {"15m": "15T", "1h": "1H", "4h": "4H", "1d": "1D"}
    freq = freq_map.get(interval, "1H")

    end = pd.Timestamp.now(tz="UTC").floor(freq)
    periods = days * 24 if interval == "1h" else days * 4 if interval == "4h" else days * 96 if interval == "15m" else days
    idx = pd.date_range(end=end, periods=min(periods, 500), freq=freq, tz="UTC")

    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.003, len(idx))
    prices = base_price * np.cumprod(1 + returns)

    rows = []
    for i, (ts, p) in enumerate(zip(idx, prices)):
        spread = vol_factor * abs(np.random.normal(0, 1))
        o = p * (1 + np.random.uniform(-0.001, 0.001))
        h = max(o, p) + spread * 0.5
        l = min(o, p) - spread * 0.5
        c = p
        v = abs(np.random.normal(10000, 3000))
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": v})

    df = pd.DataFrame(rows, index=idx)
    return df


def get_xauusd(timeframe: str = "H1") -> pd.DataFrame:
    interval, days = TIMEFRAME_MAP.get(timeframe, ("1h", 30))
    return fetch_ohlcv(XAUUSD_TICKER, interval, days)


def get_dxy(timeframe: str = "H1") -> pd.DataFrame:
    interval, days = TIMEFRAME_MAP.get(timeframe, ("1h", 30))
    return fetch_ohlcv(DXY_TICKER, interval, days)


def get_latest_price(ticker: str = XAUUSD_TICKER) -> float:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
        if price:
            return float(price)
    except Exception:
        pass
    # fallback: last close from 1-day fetch
    try:
        df = fetch_ohlcv(ticker, "1h", 2)
        if not df.empty:
            return float(df["close"].iloc[-1])
    except Exception:
        pass
    return 2350.0


def get_current_session() -> str:
    """Return current Forex session based on UTC time."""
    utc_now = datetime.now(pytz.utc)
    hour = utc_now.hour
    if 22 <= hour or hour < 8:
        return "Asian"
    elif 8 <= hour < 13:
        return "London"
    elif 13 <= hour < 22:
        return "New York"
    return "Overlap"


def get_macro_events() -> list:
    """Return upcoming/recent macro events (static for demo; extend with API)."""
    return [
        {"event": "US CPI", "impact": "High", "date": "2025-06-11"},
        {"event": "FOMC Meeting", "impact": "High", "date": "2025-06-17"},
        {"event": "US PPI", "impact": "Medium", "date": "2025-06-13"},
        {"event": "NFP", "impact": "High", "date": "2025-06-06"},
        {"event": "GDP Q1", "impact": "Medium", "date": "2025-06-26"},
    ]


def get_dxy_bias(dxy_df: pd.DataFrame) -> str:
    """Simple DXY trend bias: if DXY rising → bearish gold bias."""
    if dxy_df is None or len(dxy_df) < 20:
        return "Neutral"
    closes = dxy_df["close"].values
    sma20 = closes[-20:].mean()
    last = closes[-1]
    if last > sma20 * 1.002:
        return "Bearish (DXY ↑)"
    elif last < sma20 * 0.998:
        return "Bullish (DXY ↓)"
    return "Neutral"
