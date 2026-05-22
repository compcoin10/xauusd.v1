# ⚜️ XAUUSD AI Trading Intelligence Bot

> **Live Streamlit App** · SMC · Liquidity Sweeps · EMA Momentum · Breakout · Trend Continuation · DXY Correlation

---

## 🚀 Deploy to Streamlit Cloud (Step-by-Step)

### Step 1 — Push to GitHub

```bash
# In the extracted xauusd_bot/ folder:
git init
git add .
git commit -m "feat: XAUUSD Trading Bot v1.0"

# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/xauusd-bot.git
git branch -M main
git push -u origin main
```

### Step 2 — Connect to Streamlit Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub
2. Click **"New app"**
3. Select your repository: `YOUR_USERNAME/xauusd-bot`
4. Branch: `main`
5. **Main file path**: `app.py`
6. Click **"Deploy!"**

> Streamlit Cloud will auto-install everything in `requirements.txt`.  
> First deploy takes ~2 minutes.

### Step 3 — Done ✅

Your bot is live at:
`https://YOUR_USERNAME-xauusd-bot-app-XXXX.streamlit.app`

---

## 📁 Project Structure

```
xauusd_bot/
├── app.py                        # ← Main Streamlit entry point
├── requirements.txt              # Python dependencies
├── packages.txt                  # System-level apt packages
├── .streamlit/
│   ├── config.toml               # Dark theme + server config
│   └── secrets.toml.template     # API keys template (gitignored)
├── .github/
│   └── workflows/
│       └── deploy.yml            # CI checks on push
├── core/
│   ├── __init__.py
│   ├── database.py               # SQLite persistence (balance, trades, signals)
│   ├── data_fetcher.py           # yfinance XAUUSD + DXY data, session detection
│   ├── indicators.py             # EMA, ATR, ADX, RSI, BB + full SMC suite
│   ├── signal_engine.py          # 5 strategies → confidence-scored signals
│   ├── risk_manager.py           # Position sizing, monthly 5% target, daily limits
│   ├── backtester.py             # Walk-forward backtest engine
│   └── bot_runner.py             # Background thread, 5-min tick, SL/TP management
└── utils/
    ├── __init__.py
    └── chart_builder.py          # Plotly dark-gold chart factory
```

---

## 🧠 Strategies

| # | Strategy | Logic |
|---|---|---|
| A | **Liquidity Sweeps** | Detects equal H/L pools → sweep → reversal entry |
| B | **Trend Continuation** | EMA20 pullback in ADX-confirmed trend |
| C | **Breakout** | Volume-confirmed break of S/R level |
| D | **EMA Momentum** | EMA20 × EMA50 crossover |
| E | **SMC** | CHoCH + BOS + OB + FVG combination entries |

## 📐 Market Regimes (H1)

| Regime | Condition |
|---|---|
| **Bull** | ADX > 25 AND EMA20 > EMA50 > EMA200 |
| **Bear** | ADX > 25 AND EMA20 < EMA50 < EMA200 |
| **Ranging** | ADX < 25 |
| **High Volatile** | ATR > 1.5× 50-bar mean ATR |
| **Low Liquidity** | Volume < 0.5× 50-bar mean volume |

## 💰 Risk Management

| Parameter | Value |
|---|---|
| Risk per trade | 1% of balance |
| Max open trades | 3 |
| Max daily loss | 3% of balance |
| Monthly target | 5% of balance |
| Balance persistence | ✅ Survives restarts |

---

## 🏃 Local Development

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate     # Linux / Mac
venv\Scripts\activate        # Windows

# Install
pip install -r requirements.txt

# Run
streamlit run app.py
# → http://localhost:8501
```

---

## ⚠️ Notes on Streamlit Cloud

- **Storage**: Streamlit Cloud uses `/tmp` for the SQLite DB. Data persists for the session lifetime but resets on redeploy. For true persistence, migrate `DB_PATH` to **Supabase** (free PostgreSQL) or a mounted volume.
- **Secrets**: Never commit `secrets.toml`. Add API keys via the **Secrets** panel in your app settings on Streamlit Cloud.
- **Auto-refresh**: Toggle "Auto-refresh (60 s)" in the sidebar. The bot thread runs in background every 5 minutes.
- **Data source**: Live data via `yfinance` (Yahoo Finance). If market is closed or rate-limited, realistic synthetic data is used automatically — the UI never breaks.

---

## 📊 Data Sources

| Source | Ticker | Used for |
|---|---|---|
| Yahoo Finance | `GC=F` | XAUUSD (Gold Futures) |
| Yahoo Finance | `DX-Y.NYB` | US Dollar Index |
| Static | — | Macro event calendar |

---

*⚜️ Not financial advice. Trade responsibly.*
