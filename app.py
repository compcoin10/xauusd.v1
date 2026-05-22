"""
⚜️  XAUUSD AI Trading Intelligence — Streamlit Dashboard
Deploy: push repo to GitHub → connect at share.streamlit.io → main file = app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timezone

# ── Page config — MUST be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="XAUUSD Trading Bot",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Core imports ──────────────────────────────────────────────────────────────
from core.database import (
    get_balance, set_balance, get_signals, get_trades,
    get_bot_state, set_bot_state, get_open_trades, save_signal
)
from core.data_fetcher import (
    get_xauusd, get_dxy, get_latest_price,
    get_current_session, get_macro_events, get_dxy_bias
)
from core.signal_engine import generate_signals
from core.indicators import (
    enrich_df, market_regime, find_sr_levels,
    find_choch_bos, find_fvg, find_liquidity_sweeps
)
from core.risk_manager import (
    get_performance_summary, get_monthly_stats, calculate_lot_size, calculate_pnl
)
from core.bot_runner import start_bot, stop_bot, is_bot_running
from core.database import open_trade, close_trade
from utils.chart_builder import (
    build_main_chart, build_equity_curve, build_dxy_chart, build_correlation_chart
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #0d0f14 !important;
    color: #e0e0e0 !important;
}

/* ── Header ── */
.xau-header {
    background: linear-gradient(135deg,#0d0f14 0%,#13151c 60%,#0d0f14 100%);
    border-bottom: 1px solid #f5c842;
    padding: 1rem 1.5rem 0.8rem;
    margin-bottom: 1.2rem;
}
.xau-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.7rem;
    font-weight: 800;
    color: #f5c842;
    letter-spacing: 0.04em;
    text-shadow: 0 0 24px rgba(245,200,66,.4);
    line-height: 1.2;
}
.xau-sub {
    font-size: 0.68rem;
    color: #666;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 2px;
}

/* ── KPI cards ── */
.kpi-card {
    background: #13151c;
    border: 1px solid #1e2235;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg,#f5c842,transparent);
}
.kpi-label { font-size:.62rem; color:#666; text-transform:uppercase; letter-spacing:.14em; margin-bottom:.25rem; }
.kpi-value { font-family:'Syne',sans-serif; font-size:1.45rem; font-weight:700; color:#f5c842; }
.kpi-value.g { color:#00d4aa; }
.kpi-value.r { color:#ff4d6d; }
.kpi-sub   { font-size:.65rem; color:#555; margin-top:.15rem; }

/* ── Signal cards ── */
.sig-card { border-radius:8px; padding:.9rem 1.1rem; margin-bottom:.7rem; border:1px solid; }
.sig-card.buy  { background:rgba(0,212,170,.07); border-color:rgba(0,212,170,.35); }
.sig-card.sell { background:rgba(255,77,109,.07); border-color:rgba(255,77,109,.35); }
.sig-dir { font-size:1rem; font-weight:700; }
.sig-dir.buy  { color:#00d4aa; }
.sig-dir.sell { color:#ff4d6d; }
.sig-meta { font-size:.68rem; color:#888; margin-top:.3rem; line-height:1.7; }
.conf-bar { height:3px; border-radius:2px; background:#1e2235; margin-top:.5rem; overflow:hidden; }
.conf-fill { height:100%; border-radius:2px; background:linear-gradient(90deg,#f5c842,#00d4aa); }

/* ── Section headers ── */
.sec-title {
    font-family:'Syne',sans-serif;
    font-size:.75rem; font-weight:600;
    letter-spacing:.2em; text-transform:uppercase;
    color:#f5c842;
    border-bottom:1px solid #1e2235;
    padding-bottom:.35rem; margin-bottom:.9rem;
}

/* ── Regime badges ── */
.badge { display:inline-block; padding:.18rem .6rem; border-radius:20px;
         font-size:.66rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; }
.badge-bull  { background:rgba(0,212,170,.15);  color:#00d4aa; border:1px solid #00d4aa; }
.badge-bear  { background:rgba(255,77,109,.15); color:#ff4d6d; border:1px solid #ff4d6d; }
.badge-range { background:rgba(77,138,240,.15); color:#4d8af0; border:1px solid #4d8af0; }
.badge-vol   { background:rgba(245,200,66,.15); color:#f5c842; border:1px solid #f5c842; }
.badge-liq   { background:rgba(155,93,229,.15); color:#9b5de5; border:1px solid #9b5de5; }
.badge-def   { background:rgba(100,100,100,.15);color:#aaa;    border:1px solid #555; }

/* ── Live dot ── */
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }
.live-dot { display:inline-block; width:7px; height:7px; border-radius:50%;
            background:#00d4aa; animation:pulse 1.6s infinite; margin-right:5px; }
.offline-dot { display:inline-block; width:7px; height:7px; border-radius:50%;
               background:#ff4d6d; margin-right:5px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background:#13151c !important; border-right:1px solid #1e2235; }

/* ── Buttons ── */
.stButton > button {
    background:#1e2235 !important; color:#f5c842 !important;
    border:1px solid #f5c842 !important; border-radius:6px !important;
    font-family:'JetBrains Mono',monospace !important;
    font-size:.72rem !important; font-weight:600 !important;
    letter-spacing:.08em !important; transition:all .2s !important;
}
.stButton > button:hover { background:#f5c842 !important; color:#0d0f14 !important; }

/* ── Tab style ── */
[data-testid="stTab"] { font-size:.78rem !important; letter-spacing:.05em; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:#0d0f14; }
::-webkit-scrollbar-thumb { background:#2a2d3e; border-radius:2px; }

/* ── metric-card override for open trades ── */
.trade-card {
    background:#13151c; border:1px solid #1e2235; border-radius:6px;
    padding:.7rem .9rem; margin-bottom:.5rem; font-size:.73rem;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def regime_badge(r: str) -> str:
    cls = {"Bull":"bull","Bear":"bear","Ranging":"range",
           "High Volatile":"vol","Low Liquidity":"liq"}.get(r, "def")
    return f'<span class="badge badge-{cls}">{r}</span>'


def kpi(col, label: str, value: str, sub: str = "", color: str = ""):
    cls = f"kpi-value {color[0]}" if color else "kpi-value"
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="{cls}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


def sig_card(sig: dict):
    d   = sig["direction"]
    cls = "buy" if d == "BUY" else "sell"
    pct = min(sig["confidence"], 100)
    st.markdown(f"""
    <div class="sig-card {cls}">
        <div class="sig-dir {cls}">{d} &nbsp;·&nbsp; {sig['strategy']}</div>
        <div class="sig-meta">
            Entry <b>${sig['entry']:,.2f}</b> &nbsp;|&nbsp;
            SL <b>${sig['sl']:,.2f}</b> &nbsp;|&nbsp;
            TP <b>${sig['tp']:,.2f}</b><br>
            R:R <b>{sig['rr']:.1f}×</b> &nbsp;·&nbsp; Confidence <b>{sig['confidence']:.0f}%</b><br>
            Regime: {sig['regime']} &nbsp;|&nbsp; {sig['session']}<br>
            <small style="color:#666">{sig.get('notes','')}</small>
        </div>
        <div class="conf-bar"><div class="conf-fill" style="width:{pct}%"></div></div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="xau-header">
    <div class="xau-title">⚜️ XAUUSD Trading Intelligence</div>
    <div class="xau-sub">SMC · Liquidity Sweeps · EMA Momentum · Breakout · Trend Continuation · DXY Correlation</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Bot Control")

    bot_running  = is_bot_running()
    auto_trade   = get_bot_state("auto_trade", False)

    c1, c2 = st.columns(2)
    with c1:
        lbl = "● LIVE" if bot_running else "▶ START"
        if st.button(lbl, use_container_width=True):
            if not bot_running:
                start_bot()
                st.success("Bot started!")
                st.rerun()
    with c2:
        if st.button("■ STOP", use_container_width=True):
            stop_bot()
            st.warning("Bot stopped.")
            st.rerun()

    auto_on = st.toggle("Auto-Execute Trades", value=auto_trade)
    if auto_on != auto_trade:
        set_bot_state("auto_trade", auto_on)

    st.markdown("---")
    st.markdown("### 💰 Account Balance")
    cur_bal = get_balance()
    new_bal = st.number_input("Balance ($)", value=float(cur_bal),
                               min_value=100.0, max_value=10_000_000.0, step=100.0,
                               format="%.2f")
    if st.button("Update Balance", use_container_width=True):
        set_balance(new_bal)
        st.success(f"✓ Balance set to ${new_bal:,.2f}")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Chart Settings")
    tf_sel   = st.selectbox("Timeframe", ["M15", "H1", "H4", "D1"], index=1)
    show_smc = st.toggle("SMC Overlays",    value=True)
    show_sr  = st.toggle("S/R Levels",      value=True)
    show_vp  = st.toggle("Volume Profile",  value=True)

    st.markdown("---")
    session_now = get_current_session()
    st.markdown(f"**Session** &nbsp; {regime_badge(session_now)}", unsafe_allow_html=True)
    st.markdown(f"`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`")

    # Auto-refresh every 60 s via meta tag (no extra dependency)
    refresh_on = st.toggle("Auto-refresh (60 s)", value=False)
    if refresh_on:
        st.markdown(
            '<meta http-equiv="refresh" content="60">',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING  (cached 5 min)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(tf: str):
    return (
        get_xauusd(tf),
        get_xauusd("H1"),
        get_xauusd("M15"),
        get_dxy("H1"),
    )


with st.spinner("Fetching live market data…"):
    df_xau, df_h1, df_m15, df_dxy = load_market_data(tf_sel)

price_now  = get_latest_price()
price_prev = get_bot_state("last_price", price_now) or price_now
price_chg  = price_now - float(price_prev)
price_pct  = price_chg / price_now * 100

# Regime
regime = "Unknown"
df_e   = None
if df_h1 is not None and len(df_h1) >= 200:
    df_e   = enrich_df(df_h1)
    regime = market_regime(df_e)

dxy_bias = get_dxy_bias(df_dxy)
balance  = get_balance()
perf     = get_performance_summary()
monthly  = get_monthly_stats(balance)
open_cnt = len(get_open_trades())


# ══════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">Market Snapshot</div>', unsafe_allow_html=True)

cols = st.columns(7)
arrow = "▲" if price_chg >= 0 else "▼"
pc    = "green" if price_chg >= 0 else "red"

kpi(cols[0], "XAUUSD",        f"${price_now:,.2f}", f"{arrow} {abs(price_pct):.2f}%", pc)
kpi(cols[1], "Account Balance",f"${balance:,.2f}",  f"P&L {perf['total_pnl']:+.2f}")
kpi(cols[2], "Win Rate",       f"{perf['win_rate']:.1f}%",
    f"{perf['total_trades']} trades", "green" if perf["win_rate"] >= 50 else "red")
kpi(cols[3], "Monthly P&L",    f"${monthly['pnl']:+,.2f}",
    f"Target ${monthly['target']:,.0f}", "green" if monthly["pnl"] >= 0 else "red")
kpi(cols[4], "Profit Factor",  f"{perf['profit_factor']:.2f}",
    "Good" if perf["profit_factor"] > 1.5 else "Needs work",
    "green" if perf["profit_factor"] > 1.5 else "red")
kpi(cols[5], "Max Drawdown",   f"{perf['max_drawdown']:.1f}%", "Peak-to-trough",
    "green" if perf["max_drawdown"] < 10 else "red")
kpi(cols[6], "Market Regime",  regime, dxy_bias,
    "green" if regime == "Bull" else ("red" if regime == "Bear" else ""))

st.markdown("<br>", unsafe_allow_html=True)

# Status bar
dot = '<span class="live-dot"></span>' if bot_running else '<span class="offline-dot"></span>'
st.markdown(
    f"{dot} Bot: <b>{'ONLINE' if bot_running else 'OFFLINE'}</b> &nbsp;|&nbsp; "
    f"Auto-Trade: <b>{'ON ✓' if auto_on else 'OFF'}</b> &nbsp;|&nbsp; "
    f"Open Positions: <b>{open_cnt}</b> &nbsp;|&nbsp; "
    f"Session: <b>{session_now}</b> &nbsp;|&nbsp; "
    f"DXY Bias: <b>{dxy_bias}</b>",
    unsafe_allow_html=True
)
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Live Chart", "🎯 Signals", "📊 Backtest", "💼 Trade History", "🌐 DXY & Macro"
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — LIVE CHART
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    ch_col, sig_col = st.columns([3, 1])

    with ch_col:
        st.markdown('<div class="sec-title">Price Action · SMC · Volume Profile</div>', unsafe_allow_html=True)

        @st.cache_data(ttl=120, show_spinner=False)
        def get_live_signals(h1_len, m15_len):
            return generate_signals(df_m15, df_h1, df_dxy)

        live_sigs = get_live_signals(len(df_h1) if df_h1 is not None else 0,
                                      len(df_m15) if df_m15 is not None else 0)

        fig = build_main_chart(df_xau, signals=live_sigs,
                                show_smc=show_smc, show_sr=show_sr,
                                show_volume_profile=show_vp)
        st.plotly_chart(fig, use_container_width=True)

    with sig_col:
        st.markdown('<div class="sec-title">Live Signals</div>', unsafe_allow_html=True)

        if not live_sigs:
            st.info("No signals at this moment. Market may be in low-probability setup.")
        else:
            for sig in live_sigs:
                sig_card(sig)
                lot = calculate_lot_size(sig["entry"], sig["sl"], balance)
                st.caption(f"Lot: {lot:.2f}  |  Risk: ${balance * 0.01:,.0f}")
                if st.button(f"Execute {sig['direction']}", key=f"exec_{sig['signal_id']}"):
                    save_signal(sig)
                    open_trade(sig, lot, balance)
                    st.success(f"Opened {sig['direction']} @ {sig['entry']:.2f}")
                    st.rerun()

        st.markdown('<div class="sec-title" style="margin-top:1rem">SMC Events (H1)</div>', unsafe_allow_html=True)
        if df_h1 is not None and len(df_h1) > 50:
            for ev in find_choch_bos(df_h1)[-6:]:
                ico = "🟢" if "Bull" in ev["type"] else "🔴"
                st.caption(f"{ico} {ev['type']} @ ${ev['price']:.2f}")

            st.markdown('<div class="sec-title" style="margin-top:.8rem">FVGs (H1)</div>', unsafe_allow_html=True)
            for fvg in find_fvg(df_h1)[-5:]:
                ico = "🟢" if fvg["type"] == "bullish" else "🔴"
                st.caption(f"{ico} {fvg['type'].title()} FVG  {fvg['bottom']:.1f} – {fvg['top']:.1f}")

            sweeps = find_liquidity_sweeps(df_h1)
            if sweeps:
                st.markdown('<div class="sec-title" style="margin-top:.8rem">Liq Sweeps</div>', unsafe_allow_html=True)
                for sw in sweeps[-4:]:
                    ico = "🔵" if "buy" in sw["type"] else "🟣"
                    st.caption(f"{ico} {sw['type'].replace('_',' ').title()} @ {sw['level']:.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SIGNALS
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="sec-title">Signal History</div>', unsafe_allow_html=True)

    r1, r2, r3 = st.columns([1, 1, 4])
    with r1:
        if st.button("🔄 Generate Now", use_container_width=True):
            with st.spinner("Running signal engine…"):
                new_sigs = generate_signals(df_m15, df_h1, df_dxy)
                for s in new_sigs:
                    save_signal(s)
            st.success(f"✓ {len(new_sigs)} signal(s) generated")
            st.rerun()
    with r2:
        dir_filter = st.selectbox("Filter", ["All","BUY","SELL"], label_visibility="collapsed")

    sig_hist = get_signals(limit=200)
    if not sig_hist.empty and dir_filter != "All":
        sig_hist = sig_hist[sig_hist["direction"] == dir_filter]

    if sig_hist.empty:
        st.info("No signals recorded yet. Click Generate Now or start the bot.")
    else:
        cols_show = [c for c in ["signal_id","created_at","direction","strategy",
                                   "entry","sl","tp","confidence","rr","regime","session","dxy_bias","status"]
                     if c in sig_hist.columns]
        st.dataframe(sig_hist[cols_show].head(80), use_container_width=True, height=420)

    # Confidence histogram
    if not sig_hist.empty and "confidence" in sig_hist.columns:
        st.markdown('<div class="sec-title" style="margin-top:1rem">Confidence Distribution</div>', unsafe_allow_html=True)
        fig_c = go.Figure(go.Histogram(
            x=sig_hist["confidence"], nbinsx=20,
            marker_color="#f5c842", opacity=.85
        ))
        fig_c.update_layout(
            paper_bgcolor="#0d0f14", plot_bgcolor="#13151c",
            font=dict(color="#e0e0e0"), height=220,
            margin=dict(l=10,r=10,t=10,b=10),
            xaxis_title="Confidence (%)", yaxis_title="Count"
        )
        st.plotly_chart(fig_c, use_container_width=True)

    # Strategy breakdown
    if not sig_hist.empty and "strategy" in sig_hist.columns:
        st.markdown('<div class="sec-title">Strategy Breakdown</div>', unsafe_allow_html=True)
        strat_cnt = sig_hist.groupby("strategy").size().reset_index(name="count")
        fig_s = go.Figure(go.Bar(
            x=strat_cnt["strategy"], y=strat_cnt["count"],
            marker_color="#4d8af0", opacity=.9
        ))
        fig_s.update_layout(
            paper_bgcolor="#0d0f14", plot_bgcolor="#13151c",
            font=dict(color="#e0e0e0"), height=220,
            margin=dict(l=10,r=10,t=10,b=10)
        )
        st.plotly_chart(fig_s, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — BACKTEST
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="sec-title">Walk-Forward Strategy Backtester</div>', unsafe_allow_html=True)

    bt_l, bt_r = st.columns([1, 2])
    with bt_l:
        bt_strat  = st.selectbox("Strategy", ["All","EMA Momentum","Trend Continuation","Breakout"])
        bt_bal    = st.number_input("Initial Balance ($)", value=5000.0, step=500.0, format="%.0f")
        bt_risk   = st.slider("Risk / Trade (%)", 0.5, 3.0, 1.0, 0.1)
        bt_sl_m   = st.slider("ATR SL Multiplier", 0.5, 3.0, 1.5, 0.1)
        bt_tp_m   = st.slider("ATR TP Multiplier", 1.0, 6.0, 3.0, 0.25)
        bt_tf     = st.selectbox("Data Timeframe", ["H1","H4","D1"])
        run_bt    = st.button("▶ Run Backtest", use_container_width=True)

    with bt_r:
        if run_bt:
            from core.backtester import backtest_strategy
            bt_data = get_xauusd(bt_tf)
            if bt_data is not None and len(bt_data) > 250:
                with st.spinner("Simulating trades…"):
                    result = backtest_strategy(
                        bt_data, strategy=bt_strat,
                        initial_balance=bt_bal,
                        risk_pct=bt_risk,
                        atr_sl_mult=bt_sl_m,
                        atr_tp_mult=bt_tp_m,
                    )
                st.session_state["bt_result"] = result
            else:
                st.error("Not enough historical data. Try H1 timeframe.")

        if "bt_result" in st.session_state:
            r = st.session_state["bt_result"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Trades",  r["total_trades"])
            m2.metric("Win Rate",      f"{r['win_rate']:.1f}%")
            m3.metric("Profit Factor", f"{r['profit_factor']:.2f}")
            m4.metric("Max Drawdown",  f"{r['max_drawdown']:.1f}%")

            n1, n2 = st.columns(2)
            n1.metric("Net P&L",       f"${r['net_pnl']:+,.2f}")
            n2.metric("Final Balance", f"${r['final_balance']:,.2f}")

            if r.get("equity_curve"):
                fig_eq = build_equity_curve(r["equity_curve"])
                st.plotly_chart(fig_eq, use_container_width=True)

            if r.get("trades"):
                trade_log = pd.DataFrame(r["trades"])
                if not trade_log.empty:
                    st.markdown("**Recent Trade Log**")
                    cols_bt = [c for c in ["time","strategy","direction","entry",
                                            "exit","outcome","pnl","balance"] if c in trade_log.columns]
                    st.dataframe(trade_log[cols_bt].tail(40), use_container_width=True, height=300)

    # History
    st.markdown("---")
    st.markdown('<div class="sec-title">Previous Runs</div>', unsafe_allow_html=True)
    from core.database import get_backtest_results
    bt_hist = get_backtest_results(10)
    if not bt_hist.empty:
        h_cols = [c for c in ["run_at","strategy","total_trades","win_rate",
                               "profit_factor","max_drawdown","net_pnl"] if c in bt_hist.columns]
        st.dataframe(bt_hist[h_cols], use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — TRADE HISTORY
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="sec-title">Open Positions</div>', unsafe_allow_html=True)

    open_trades = get_open_trades()
    if open_trades.empty:
        st.info("No open positions.")
    else:
        for _, t in open_trades.iterrows():
            if t["direction"] == "BUY":
                upnl = (price_now - float(t["entry_price"])) * float(t["lot_size"]) * 100
            else:
                upnl = (float(t["entry_price"]) - price_now) * float(t["lot_size"]) * 100
            pnl_color = "#00d4aa" if upnl >= 0 else "#ff4d6d"
            arrow = "▲" if t["direction"] == "BUY" else "▼"
            st.markdown(f"""
            <div class="trade-card">
                <b style="color:{'#00d4aa' if t['direction']=='BUY' else '#ff4d6d'}">{arrow} {t['direction']}</b>
                &nbsp; Entry <b>${float(t['entry_price']):,.2f}</b>
                &nbsp;|&nbsp; Lot <b>{float(t['lot_size']):.2f}</b>
                &nbsp;|&nbsp; {t['strategy']}<br>
                SL <b>${float(t['sl']):,.2f}</b>
                &nbsp;|&nbsp; TP <b>${float(t['tp']):,.2f}</b>
                &nbsp;|&nbsp; Unrealised: <b style="color:{pnl_color}">${upnl:+,.2f}</b>
            </div>""", unsafe_allow_html=True)

            if st.button(f"Close Trade #{t['id']}", key=f"close_{t['id']}"):
                pnl = calculate_pnl(t["direction"], float(t["entry_price"]), price_now, float(t["lot_size"]))
                close_trade(int(t["id"]), price_now, pnl)
                set_balance(balance + pnl)
                st.success(f"Closed at ${price_now:,.2f} | PnL: ${pnl:+,.2f}")
                st.rerun()

    st.markdown("---")
    st.markdown('<div class="sec-title">Closed Trades</div>', unsafe_allow_html=True)
    closed = get_trades(status="closed", limit=100)
    if not closed.empty:
        c_cols = [c for c in ["id","opened_at","closed_at","direction","strategy",
                               "entry_price","exit_price","lot_size","pnl"] if c in closed.columns]
        st.dataframe(closed[c_cols].head(50), use_container_width=True, height=360)

        # Cumulative PnL chart
        st.markdown('<div class="sec-title" style="margin-top:1rem">Cumulative P&L</div>', unsafe_allow_html=True)
        closed_sorted = closed.sort_values("closed_at")
        cum = closed_sorted["pnl"].cumsum()
        bar_colors = ["#00d4aa" if p >= 0 else "#ff4d6d" for p in closed_sorted["pnl"]]

        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(
            y=cum.values, mode="lines+markers",
            line=dict(color="#f5c842", width=2),
            marker=dict(color=bar_colors, size=5),
            fill="tozeroy", fillcolor="rgba(245,200,66,.08)",
            name="Cumul. PnL"
        ))
        fig_pnl.update_layout(
            paper_bgcolor="#0d0f14", plot_bgcolor="#13151c",
            font=dict(color="#e0e0e0"), height=280,
            margin=dict(l=10,r=10,t=30,b=10),
            yaxis_title="USD", showlegend=False,
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

        # Monthly progress
        prog = int(min(monthly["progress_pct"], 100))
        st.markdown('<div class="sec-title">Monthly Target (5%)</div>', unsafe_allow_html=True)
        st.progress(prog / 100,
                    text=f"P&L: ${monthly['pnl']:+,.2f} / Target: ${monthly['target']:,.0f}  ({monthly['progress_pct']:.1f}%)")
    else:
        st.info("No closed trades yet.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — DXY & MACRO
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    d_left, d_right = st.columns([2, 1])

    with d_left:
        st.markdown('<div class="sec-title">US Dollar Index (DXY)</div>', unsafe_allow_html=True)
        st.plotly_chart(build_dxy_chart(df_dxy), use_container_width=True)

        st.markdown('<div class="sec-title">XAUUSD vs DXY — 20-bar Rolling Correlation</div>', unsafe_allow_html=True)
        st.plotly_chart(build_correlation_chart(df_h1, df_dxy), use_container_width=True)

    with d_right:
        st.markdown('<div class="sec-title">DXY Bias</div>', unsafe_allow_html=True)
        bias_color = "#00d4aa" if "Bullish" in dxy_bias else ("#ff4d6d" if "Bearish" in dxy_bias else "#f5c842")
        st.markdown(f"""
        <div class="kpi-card" style="margin-bottom:1rem;">
            <div class="kpi-label">Gold Bias from DXY</div>
            <div class="kpi-value" style="color:{bias_color};font-size:1.1rem">{dxy_bias}</div>
            <div class="kpi-sub">DXY ↑ → Gold bearish (inverse correlation)</div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec-title">Macro Events</div>', unsafe_allow_html=True)
        for ev in get_macro_events():
            ic = "#ff4d6d" if ev["impact"] == "High" else ("#f5c842" if ev["impact"] == "Medium" else "#888")
            st.markdown(f"""
            <div class="kpi-card" style="margin-bottom:.5rem;padding:.6rem .9rem;">
                <div style="color:{ic};font-weight:700;font-size:.75rem">{ev['event']}</div>
                <div class="kpi-sub">{ev['date']} · {ev['impact']} impact</div>
            </div>""", unsafe_allow_html=True)

        if df_e is not None:
            st.markdown('<div class="sec-title" style="margin-top:1rem">Regime Indicators</div>', unsafe_allow_html=True)
            row = df_e.iloc[-1]
            metrics = [
                ("ADX",    f"{row['adx']:.1f}",   "> 25 = Trend"),
                ("EMA20",  f"{row['ema20']:.2f}",  ""),
                ("EMA50",  f"{row['ema50']:.2f}",  ""),
                ("EMA200", f"{row['ema200']:.2f}", ""),
                ("ATR",    f"{row['atr']:.2f}",    "Volatility"),
                ("RSI",    f"{row['rsi']:.1f}",    "< 30 OS | > 70 OB"),
            ]
            for label, val, hint in metrics:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                            border-bottom:1px solid #1e2235;padding:.35rem 0;font-size:.72rem;">
                    <span style="color:#888">{label}</span>
                    <span style="color:#f5c842;font-weight:600">{val}
                        <span style="color:#444;font-size:.62rem">&nbsp;{hint}</span>
                    </span>
                </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#333;font-size:.66rem;"
    "font-family:JetBrains Mono,monospace;padding:.5rem 0'>"
    "⚜️ XAUUSD Trading Intelligence &nbsp;·&nbsp; "
    "SMC · Liq Sweeps · EMA Momentum · Breakout · Trend Continuation &nbsp;·&nbsp; "
    "Data via yfinance &nbsp;·&nbsp; Not financial advice"
    "</div>",
    unsafe_allow_html=True
)

# Auto-start bot on every cold load
if not is_bot_running():
    start_bot()
