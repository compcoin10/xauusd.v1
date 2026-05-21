# ⚜️ XAUUSD AI Trading Intelligence Bot

A professional, full-featured XAUUSD (Gold) trading signal system with Streamlit dashboard, SMC analysis, multi-strategy signal engine, backtesting, and 24/7 bot operation.

---

## 🚀 Features

### Signal Strategies
| Strategy | Description |
|---|---|
| **Liquidity Sweeps** | Detects equal highs/lows (buy/sell-side liq) and reversal after sweep |
| **Trend Continuation** | EMA20 pullback entries in trending markets |
| **Breakout** | Volume-confirmed breakouts above resistance / below support |
| **EMA Momentum** | EMA20 × EMA50 crossover signals |
| **SMC (Smart Money)** | CHoCH, BOS, Order Blocks, Fair Value Gaps, Liq Pulls |

### SMC Concepts
- **CHoCH** (Change of Character): Trend reversal detection
- **BOS** (Break of Structure): Continuation confirmation
- **OB** (Order Blocks): Institutional entry zones
- **FVG** (Fair Value Gaps): Price imbalance zones
- **Liquidity Pools**: Equal highs/lows sweeps

### Market Regime Classifier (1H)
| Regime | Condition |
|---|---|
| **Bull** | ADX > 25 AND EMA20 > EMA50 > EMA200 |
| **Bear** | ADX > 25 AND EMA20 < EMA50 < EMA200 |
| **Ranging** | ADX < 25 |
| **High Volatile** | ATR > 1.5× mean ATR |
| **Low Liquidity** | Volume < 0.5× mean volume |

### Risk Management
- 1% risk per trade (configurable)
- Max 3 open trades simultaneously
- 3% max daily loss limit
- 5% monthly target tracking
- Persistent balance across restarts
- Full trade history with PnL

### Dashboard Tabs
1. **Live Chart** — Candlesticks + EMA20/50/200 + S/R + SMC overlays + Volume Profile (POC/VAH/VAL)
2. **Signals** — Real-time buy/sell signals with confidence scores, manual execution
3. **Backtest** — Walk-forward backtest with equity curve, trade log, performance metrics
4. **Trade History** — Open/closed positions, cumulative PnL, monthly progress
5. **DXY & Macro** — DXY chart, rolling correlation with Gold, macro event calendar

---

## 🛠️ Local Setup

```bash
# 1. Clone or extract the project
cd xauusd_bot

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dashboard
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## ☁️ Deploy to Streamlit Cloud

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: XAUUSD Trading Bot"
   git remote add origin https://github.com/YOUR_USERNAME/xauusd-bot.git
   git push -u origin main
   ```

2. **Connect to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click **New App**
   - Select your repository and branch
   - Set **Main file**: `app.py`
   - Click **Deploy**

3. **Persistent Data Note**
   - Streamlit Cloud has ephemeral storage; the SQLite DB (`data/trading_bot.db`) resets on redeploy.
   - For production persistence, switch `DB_PATH` in `core/database.py` to a mounted volume or use a cloud DB (Supabase, PlanetScale).

---

## 📁 Project Structure

```
xauusd_bot/
├── app.py                    # Main Streamlit dashboard
├── requirements.txt
├── .streamlit/
│   └── config.toml           # Dark theme config
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD
├── core/
│   ├── database.py           # SQLite persistence (balance, trades, signals)
│   ├── data_fetcher.py       # yfinance XAUUSD/DXY data + session detection
│   ├── indicators.py         # EMA, ATR, ADX, RSI, BB, S/R, SMC indicators
│   ├── signal_engine.py      # 5-strategy signal generator
│   ├── risk_manager.py       # Position sizing, monthly tracking, PnL
│   ├── backtester.py         # Walk-forward backtesting engine
│   └── bot_runner.py         # 24/7 background scheduler
├── utils/
│   └── chart_builder.py      # Plotly chart factory (dark theme)
└── data/
    └── trading_bot.db        # Auto-created SQLite database
```

---

## ⚙️ Configuration

Key parameters in `core/risk_manager.py`:
```python
RISK_PER_TRADE_PCT  = 1.0    # % of balance risked per trade
MAX_OPEN_TRADES     = 3      # Concurrent trades limit
MAX_DAILY_LOSS_PCT  = 3.0    # Daily drawdown stop
TARGET_MONTHLY_PCT  = 5.0    # Monthly profit target
```

---

## ⚠️ Disclaimer

This system is for **educational and research purposes only**. Trading involves significant financial risk. Past performance does not guarantee future results. Always paper-trade first and never risk more than you can afford to lose.

---

## 📊 Data Sources

- **Price data**: [yfinance](https://pypi.org/project/yfinance/) — Yahoo Finance (GC=F for Gold, DX-Y.NYB for DXY)
- **Macro events**: Static calendar (extend with ForexFactory API or Investing.com scraper)
- **Session detection**: UTC-based Asian/London/New York logic

---

*Built with ❤️ for serious XAUUSD traders | SMC + EMA + Breakout + Liq Sweep + Trend Continuation*
