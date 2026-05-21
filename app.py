"""
XAUUSD AI Trading Bot — Main Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
import time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="XAUUSD Trading Bot",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ───────────────────────────────────────────────────────────────────
from core.database import (
    get_balance, set_balance, get_signals, get_trades,
    get_bot_state, set_bot_state, get_open_trades
)
from core.data_fetcher import get_xauusd, get_dxy, get_latest_price, get_current_session, get_macro_events
from core.signal_engine import generate_signals
from core.indicators import enrich_df, market_regime, find_sr_levels
from core.risk_manager import get_performance_summary, get_monthly_stats, calculate_lot_size
from core.bot_runner import start_bot, stop_bot, is_bot_running
from utils.chart_builder import build_main_chart, build_equity_curve, build_dxy_chart, build_correlation_chart

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background: #0d0f14;
    color: #e0e0e0;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #0d0f14 0%, #13151c 50%, #0d0f14 100%);
    border-bottom: 1px solid #f5c842;
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.header-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #f5c842;
    letter-spacing: 0.05em;
    text-shadow: 0 0 20px rgba(245,200,66,0.4);
}
.header-sub {
    font-size: 0.75rem;
    color: #888;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

/* Metric cards */
.metric-card {
    background: #13151c;
    border: 1px solid #1e2235;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #f5c842, transparent);
}
.metric-label {
    font-size: 0.65rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 0.3rem;
}
.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f5c842;
    font-family: 'Syne', sans-serif;
}
.metric-value.green { color: #00d4aa; }
.metric-value.red   { color: #ff4d6d; }
.metric-sub {
    font-size: 0.7rem;
    color: #666;
    margin-top: 0.2rem;
}

/* Signal cards */
.signal-card {
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    border: 1px solid;
    position: relative;
}
.signal-card.buy  { background: rgba(0,212,170,0.08); border-color: rgba(0,212,170,0.4); }
.signal-card.sell { background: rgba(255,77,109,0.08); border-color: rgba(255,77,109,0.4); }
.signal-direction { font-size: 1.1rem; font-weight: 700; }
.signal-direction.buy  { color: #00d4aa; }
.signal-direction.sell { color: #ff4d6d; }
.signal-meta { font-size: 0.7rem; color: #888; margin-top: 0.3rem; }
.confidence-bar {
    height: 4px;
    border-radius: 2px;
    margin-top: 0.5rem;
    background: #1e2235;
    overflow: hidden;
}
.confidence-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, #f5c842, #00d4aa);
}

/* Regime badge */
.regime-badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.regime-Bull      { background: rgba(0,212,170,0.2);  color: #00d4aa; border: 1px solid #00d4aa; }
.regime-Bear      { background: rgba(255,77,109,0.2); color: #ff4d6d; border: 1px solid #ff4d6d; }
.regime-Ranging   { background: rgba(77,138,240,0.2); color: #4d8af0; border: 1px solid #4d8af0; }
.regime-High { background: rgba(245,200,66,0.2); color: #f5c842; border: 1px solid #f5c842; }
.regime-Low  { background: rgba(155,93,229,0.2); color: #9b5de5; border: 1px solid #9b5de5; }

/* Bot status */
.bot-online  { color: #00d4aa; font-weight: 700; }
.bot-offline { color: #ff4d6d; font-weight: 700; }

/* Section headers */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f5c842;
    border-bottom: 1px solid #1e2235;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

/* Tables */
.stDataFrame { font-size: 0.75rem !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #13151c !important;
    border-right: 1px solid #1e2235;
}

/* Buttons */
.stButton > button {
    background: #1e2235;
    color: #f5c842;
    border: 1px solid #f5c842;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #f5c842;
    color: #0d0f14;
}

/* Live pulse */
@keyframes pulse {
    0%   { opacity: 1; }
    50%  { opacity: 0.3; }
    100% { opacity: 1; }
}
.live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00d4aa;
    animation: pulse 1.5s infinite;
    margin-right: 6px;
}

/* Metric row */
.metric-row {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}

/* Trade row colors */
.win  { color: #00d4aa !important; }
.loss { color: #ff4d6d !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div>
        <div class="header-title">⚜️ XAUUSD Trading Intelligence</div>
        <div class="header-sub">AI-Powered Signal Engine · SMC · Multi-Strategy · 24/7</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="main_refresh")
except ImportError:
    pass

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Bot Control")

    # Bot toggle
    bot_enabled = get_bot_state("bot_enabled", True)
    auto_trade  = get_bot_state("auto_trade", False)
    bot_running = is_bot_running()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ START" if not bot_running else "● RUNNING", use_container_width=True):
            if not bot_running:
                start_bot()
                st.success("Bot started!")
    with col2:
        if st.button("■ STOP", use_container_width=True):
            stop_bot()
            st.warning("Bot stopped.")

    st.markdown("---")
    auto_trade_toggle = st.toggle("Auto-Execute Trades", value=auto_trade)
    if auto_trade_toggle != auto_trade:
        set_bot_state("auto_trade", auto_trade_toggle)

    st.markdown("---")
    st.markdown("### 💰 Balance")
    current_bal = get_balance()
    new_bal = st.number_input("Set Balance ($)", value=float(current_bal),
                               min_value=100.0, max_value=1_000_000.0, step=100.0)
    if st.button("Update Balance", use_container_width=True):
        set_balance(new_bal)
        st.success(f"Balance updated: ${new_bal:,.2f}")

    st.markdown("---")
    st.markdown("### 📊 Chart Settings")
    timeframe_sel = st.selectbox("Timeframe", ["M15", "H1", "H4", "D1"], index=1)
    show_smc      = st.toggle("SMC Overlays",     value=True)
    show_sr       = st.toggle("S/R Levels",        value=True)
    show_vp       = st.toggle("Volume Profile",    value=True)

    st.markdown("---")
    st.markdown("### ⏰ Current Session")
    session = get_current_session()
    st.markdown(f"<span class='regime-badge regime-Ranging'>{session}</span>", unsafe_allow_html=True)

    st.markdown("### 🕐 Server Time")
    st.markdown(f"`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data(tf):
    df_xau = get_xauusd(tf)
    df_dxy = get_dxy("H1")
    df_h1  = get_xauusd("H1")
    df_m15 = get_xauusd("M15")
    return df_xau, df_dxy, df_h1, df_m15

with st.spinner("Loading live market data..."):
    df_xau, df_dxy, df_h1, df_m15 = load_data(timeframe_sel)

# Current price
current_price = get_latest_price()
prev_price    = get_bot_state("last_price", current_price)
price_change  = current_price - (prev_price if prev_price else current_price)
price_pct     = (price_change / current_price * 100) if current_price else 0

# Market regime
regime = "Unknown"
if df_h1 is not None and len(df_h1) >= 200:
    df_e = enrich_df(df_h1)
    regime = market_regime(df_e)

# DXY bias
from core.data_fetcher import get_dxy_bias
dxy_bias = get_dxy_bias(df_dxy)

# Performance
balance = get_balance()
perf    = get_performance_summary()
monthly = get_monthly_stats(balance)

# ── KPI Row ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Market Overview</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)

def kpi(col, label, value, sub="", color=""):
    with col:
        color_cls = f'class="metric-value {color}"' if color else 'class="metric-value"'
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div {color_cls}>{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

price_color = "green" if price_change >= 0 else "red"
change_sym  = "▲" if price_change >= 0 else "▼"

kpi(k1, "XAUUSD", f"${current_price:,.2f}", f"{change_sym} {abs(price_pct):.2f}%", price_color)
kpi(k2, "Balance", f"${balance:,.2f}", f"P&L {perf['total_pnl']:+.2f}")
kpi(k3, "Win Rate", f"{perf['win_rate']:.1f}%", f"{perf['total_trades']} trades",
    "green" if perf["win_rate"] > 50 else "red")
kpi(k4, "Monthly P&L", f"${monthly['pnl']:+,.2f}",
    f"Target: ${monthly['target']:,.0f}", "green" if monthly["pnl"] >= 0 else "red")
kpi(k5, "Profit Factor", f"{perf['profit_factor']:.2f}",
    "Good" if perf["profit_factor"] > 1.5 else "Needs work",
    "green" if perf["profit_factor"] > 1.5 else "red")
kpi(k6, "Max DD", f"{perf['max_drawdown']:.1f}%", "Drawdown",
    "green" if perf["max_drawdown"] < 10 else "red")

# Regime kpi
regime_map = {"Bull": "green", "Bear": "red", "Ranging": "", "High Volatile": "", "Low Liquidity": ""}
regime_color = regime_map.get(regime, "")
kpi(k7, "Regime", regime, dxy_bias, regime_color)

st.markdown("<br>", unsafe_allow_html=True)

# ── Bot status bar ────────────────────────────────────────────────────────────
bot_status_html = (
    '<span class="live-dot"></span><span class="bot-online">ONLINE</span>' if is_bot_running()
    else '<span class="bot-offline">■ OFFLINE</span>'
)
open_cnt = len(get_open_trades())
st.markdown(
    f"Bot: {bot_status_html} &nbsp;|&nbsp; "
    f"Auto-Trade: <b>{'ON' if auto_trade_toggle else 'OFF'}</b> &nbsp;|&nbsp; "
    f"Open Positions: <b>{open_cnt}</b> &nbsp;|&nbsp; "
    f"Session: <b>{session}</b> &nbsp;|&nbsp; "
    f"DXY: <b>{dxy_bias}</b>",
    unsafe_allow_html=True
)

st.markdown("---")

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Live Chart", "🎯 Signals", "📊 Backtest", "💼 Trade History", "🌐 DXY & Macro"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: LIVE CHART
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_chart, col_signals = st.columns([3, 1])

    with col_chart:
        st.markdown('<div class="section-title">Price Action · SMC · S/R</div>', unsafe_allow_html=True)

        # Generate fresh signals for chart overlay
        with st.spinner("Generating signals..."):
            live_signals = generate_signals(df_m15, df_h1, df_dxy)

        chart = build_main_chart(df_xau, signals=live_signals,
                                  show_smc=show_smc, show_sr=show_sr,
                                  show_volume_profile=show_vp)
        st.plotly_chart(chart, use_container_width=True)

    with col_signals:
        st.markdown('<div class="section-title">Live Signals</div>', unsafe_allow_html=True)

        if not live_signals:
            st.info("No signals generated yet. Market may be ranging or data loading.")
        else:
            for sig in live_signals:
                direction = sig["direction"]
                dir_cls   = "buy" if direction == "BUY" else "sell"
                conf_pct  = min(sig["confidence"], 100)
                st.markdown(f"""
                <div class="signal-card {dir_cls}">
                    <div class="signal-direction {dir_cls}">{direction} · {sig['strategy']}</div>
                    <div class="signal-meta">
                        Entry: <b>${sig['entry']:,.2f}</b><br>
                        SL: ${sig['sl']:,.2f} | TP: ${sig['tp']:,.2f}<br>
                        R:R <b>{sig['rr']:.1f}x</b> · Conf: <b>{sig['confidence']:.0f}%</b><br>
                        Regime: {sig['regime']} | {sig['session']}<br>
                        <small>{sig.get('notes','')}</small>
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width:{conf_pct}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                lot = calculate_lot_size(sig["entry"], sig["sl"], balance)
                st.caption(f"Suggested lot: {lot:.2f} | Risk: ${balance * 0.01:,.0f}")

                if st.button(f"Manual {direction}", key=f"manual_{sig['signal_id']}"):
                    from core.database import save_signal, open_trade
                    save_signal(sig)
                    open_trade(sig, lot, balance)
                    st.success(f"Trade opened: {direction} @ {sig['entry']:.2f}")

        st.markdown("---")
        st.markdown('<div class="section-title">SMC Events</div>', unsafe_allow_html=True)
        if df_h1 is not None and len(df_h1) > 50:
            from core.indicators import find_choch_bos, find_liquidity_sweeps, find_fvg
            events = find_choch_bos(df_h1)
            for ev in events[-5:]:
                col = "🟢" if "Bull" in ev["type"] else "🔴"
                st.caption(f"{col} {ev['type']} @ ${ev['price']:.2f}")

            st.markdown('<div class="section-title">Recent FVGs</div>', unsafe_allow_html=True)
            fvgs = find_fvg(df_h1)
            for fvg in fvgs[-5:]:
                col = "🟢" if fvg["type"] == "bullish" else "🔴"
                st.caption(f"{col} {fvg['type'].title()} FVG: ${fvg['bottom']:.1f}–${fvg['top']:.1f}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">Signal History</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Signals"):
        with st.spinner("Generating..."):
            new_sigs = generate_signals(df_m15, df_h1, df_dxy)
            for s in new_sigs:
                from core.database import save_signal
                save_signal(s)
        st.success(f"Generated {len(new_sigs)} signal(s)")

    signals_df = get_signals(limit=100)
    if signals_df.empty:
        st.info("No signals yet. Start the bot or click Refresh.")
    else:
        # Color-code direction
        def style_signals(df):
            styles = []
            for _, row in df.iterrows():
                if row.get("direction") == "BUY":
                    styles.append("background-color: rgba(0,212,170,0.08)")
                else:
                    styles.append("background-color: rgba(255,77,109,0.08)")
            return styles

        display_cols = ["signal_id", "created_at", "direction", "strategy", "entry",
                        "sl", "tp", "confidence", "regime", "session", "dxy_bias", "status"]
        available = [c for c in display_cols if c in signals_df.columns]
        st.dataframe(signals_df[available].head(50), use_container_width=True, height=450)

    # Confidence distribution
    if not signals_df.empty and "confidence" in signals_df.columns:
        st.markdown('<div class="section-title">Confidence Distribution</div>', unsafe_allow_html=True)
        fig_conf = go.Figure()
        fig_conf.add_trace(go.Histogram(
            x=signals_df["confidence"], nbinsx=20,
            marker_color="#f5c842", opacity=0.8, name="Confidence"
        ))
        fig_conf.update_layout(
            paper_bgcolor="#0d0f14", plot_bgcolor="#13151c",
            font=dict(color="#e0e0e0"), height=250,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_conf, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: BACKTEST
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">Strategy Backtester</div>', unsafe_allow_html=True)

    col_bt1, col_bt2 = st.columns([1, 2])
    with col_bt1:
        bt_strategy  = st.selectbox("Strategy", ["All", "EMA Momentum", "Trend Continuation", "Breakout"])
        bt_balance   = st.number_input("Initial Balance ($)", value=5000.0, step=500.0)
        bt_risk      = st.slider("Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1)
        bt_atr_sl    = st.slider("ATR SL Multiplier", 0.5, 3.0, 1.5, 0.1)
        bt_atr_tp    = st.slider("ATR TP Multiplier", 1.0, 5.0, 3.0, 0.25)
        bt_tf        = st.selectbox("Timeframe", ["H1", "H4", "D1"], index=0)

        run_bt = st.button("▶ Run Backtest", use_container_width=True)

    with col_bt2:
        if run_bt:
            with st.spinner("Running backtest... This may take a moment."):
                from core.backtester import backtest_strategy
                bt_df = get_xauusd(bt_tf)
                if bt_df is not None and len(bt_df) > 250:
                    result = backtest_strategy(
                        bt_df, strategy=bt_strategy,
                        initial_balance=bt_balance,
                        risk_pct=bt_risk,
                        atr_sl_mult=bt_atr_sl,
                        atr_tp_mult=bt_atr_tp
                    )
                    st.session_state["bt_result"] = result
                else:
                    st.error("Not enough data for backtest. Try H1 or higher.")

        if "bt_result" in st.session_state:
            r = st.session_state["bt_result"]

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Trades", r["total_trades"])
            with m2:
                wc = "normal" if r["win_rate"] < 50 else "off"
                st.metric("Win Rate", f"{r['win_rate']:.1f}%")
            with m3:
                st.metric("Profit Factor", f"{r['profit_factor']:.2f}")
            with m4:
                st.metric("Max Drawdown", f"{r['max_drawdown']:.1f}%")

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Net P&L", f"${r['net_pnl']:+,.2f}")
            with col_b:
                st.metric("Final Balance", f"${r['final_balance']:,.2f}")

            if r.get("equity_curve"):
                fig_eq = build_equity_curve(r["equity_curve"])
                st.plotly_chart(fig_eq, use_container_width=True)

            if r.get("trades"):
                trades_bt = pd.DataFrame(r["trades"])
                if not trades_bt.empty:
                    st.markdown("**Trade Log (last 30)**")
                    show_cols = [c for c in ["time","strategy","direction","entry","exit","outcome","pnl","balance"]
                                 if c in trades_bt.columns]
                    st.dataframe(trades_bt[show_cols].tail(30), use_container_width=True, height=300)

    # Previous backtest results
    st.markdown("---")
    st.markdown('<div class="section-title">Previous Backtest Runs</div>', unsafe_allow_html=True)
    from core.database import get_backtest_results
    bt_history = get_backtest_results(limit=10)
    if not bt_history.empty:
        show_bt_cols = [c for c in ["run_at","strategy","total_trades","win_rate","profit_factor","max_drawdown","net_pnl"]
                        if c in bt_history.columns]
        st.dataframe(bt_history[show_bt_cols], use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: TRADE HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">Trade History</div>', unsafe_allow_html=True)

    col_oh, col_cl = st.columns(2)

    with col_oh:
        st.markdown("**Open Positions**")
        open_trades = get_open_trades()
        if open_trades.empty:
            st.info("No open positions.")
        else:
            for _, t in open_trades.iterrows():
                unrealised_pnl = 0.0
                dir_sym = "▲" if t["direction"] == "BUY" else "▼"
                if t["direction"] == "BUY":
                    unrealised_pnl = (current_price - t["entry_price"]) * t["lot_size"] * 100
                else:
                    unrealised_pnl = (t["entry_price"] - current_price) * t["lot_size"] * 100
                pnl_color = "green" if unrealised_pnl >= 0 else "red"
                st.markdown(f"""
                <div class="metric-card">
                    <b>{dir_sym} {t['direction']}</b> @ ${t['entry_price']:,.2f} |
                    Lot: {t['lot_size']:.2f} | {t['strategy']}<br>
                    SL: ${t['sl']:,.2f} | TP: ${t['tp']:,.2f}<br>
                    Unrealised: <span class="{pnl_color}">${unrealised_pnl:+,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"Close #{t['id']}", key=f"close_{t['id']}"):
                    from core.database import close_trade
                    from core.risk_manager import calculate_pnl
                    pnl = calculate_pnl(t["direction"], t["entry_price"], current_price, t["lot_size"])
                    close_trade(int(t["id"]), current_price, pnl)
                    new_balance = balance + pnl
                    set_balance(new_balance)
                    st.success(f"Trade closed. PnL: ${pnl:+,.2f} | New balance: ${new_balance:,.2f}")
                    st.rerun()

    with col_cl:
        st.markdown("**Closed Trades**")
        closed = get_trades(status="closed", limit=50)
        if closed.empty:
            st.info("No closed trades yet.")
        else:
            show_cols = [c for c in ["id","opened_at","closed_at","direction","strategy",
                                      "entry_price","exit_price","pnl","lot_size"]
                         if c in closed.columns]
            st.dataframe(closed[show_cols].head(30), use_container_width=True, height=400)

    # PnL chart
    st.markdown("---")
    st.markdown('<div class="section-title">Cumulative P&L</div>', unsafe_allow_html=True)
    all_closed = get_trades(status="closed")
    if not all_closed.empty and "pnl" in all_closed.columns:
        all_closed = all_closed.sort_values("closed_at")
        cum_pnl = all_closed["pnl"].cumsum()
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(
            y=cum_pnl.values, mode="lines+markers",
            line=dict(color="#f5c842", width=2),
            marker=dict(color=["#00d4aa" if p >= 0 else "#ff4d6d" for p in all_closed["pnl"].values],
                        size=6),
            fill="tozeroy", fillcolor="rgba(245,200,66,0.1)",
            name="Cumulative PnL"
        ))
        fig_pnl.update_layout(
            paper_bgcolor="#0d0f14", plot_bgcolor="#13151c",
            font=dict(color="#e0e0e0"), height=300,
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(text="Cumulative PnL ($)", font=dict(color="#f5c842"))
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

        # Monthly target progress
        st.markdown('<div class="section-title">Monthly Target Progress</div>', unsafe_allow_html=True)
        prog = monthly["progress_pct"]
        st.progress(int(min(prog, 100)) / 100,
                    text=f"Monthly P&L: ${monthly['pnl']:+,.2f} | Target: ${monthly['target']:,.0f} ({prog:.1f}%)")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: DXY & MACRO
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-title">DXY Correlation Analysis</div>', unsafe_allow_html=True)

    col_d1, col_d2 = st.columns([2, 1])
    with col_d1:
        dxy_chart = build_dxy_chart(df_dxy)
        st.plotly_chart(dxy_chart, use_container_width=True)

        corr_chart = build_correlation_chart(df_h1, df_dxy)
        st.plotly_chart(corr_chart, use_container_width=True)

    with col_d2:
        st.markdown('<div class="section-title">DXY Bias</div>', unsafe_allow_html=True)
        bias_color = "green" if "Bullish" in dxy_bias else ("red" if "Bearish" in dxy_bias else "")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">DXY Signal</div>
            <div class="metric-value {bias_color}">{dxy_bias}</div>
            <div class="metric-sub">Inverse correlation with Gold</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Macro Calendar</div>', unsafe_allow_html=True)
        events = get_macro_events()
        for ev in events:
            impact_color = "#ff4d6d" if ev["impact"] == "High" else "#f5c842" if ev["impact"] == "Medium" else "#888"
            st.markdown(f"""
            <div class="metric-card" style="margin-bottom:0.5rem;">
                <div style="color:{impact_color};font-weight:700;">{ev['event']}</div>
                <div class="metric-sub">{ev['date']} · Impact: {ev['impact']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Regime Details</div>', unsafe_allow_html=True)

        if df_h1 is not None and len(df_h1) >= 200:
            df_e_tab5 = enrich_df(df_h1)
            last_row = df_e_tab5.iloc[-1]
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Regime</div>
                <div class="metric-value">{regime}</div>
                <div class="metric-sub">
                    ADX: {last_row['adx']:.1f}<br>
                    EMA20: {last_row['ema20']:.2f}<br>
                    EMA50: {last_row['ema50']:.2f}<br>
                    EMA200: {last_row['ema200']:.2f}<br>
                    ATR: {last_row['atr']:.2f}<br>
                    RSI: {last_row['rsi']:.1f}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#444;font-size:0.7rem;font-family:JetBrains Mono,monospace;'>"
    "⚜️ XAUUSD Trading Intelligence · Built with SMC + EMA + Breakout + Liq Sweep strategies · "
    "Data via yfinance · Not financial advice"
    "</div>",
    unsafe_allow_html=True
)

# Auto-start bot on load
if not is_bot_running():
    start_bot()
