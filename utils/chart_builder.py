"""
Chart builder: professional XAUUSD charts with SMC overlays, S/R, volume profile.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from core.indicators import (
    enrich_df, find_sr_levels, volume_profile,
    find_fvg, find_order_blocks, find_choch_bos, find_liquidity_sweeps, market_regime
)


COLORS = {
    "bg":        "#0d0f14",
    "panel":     "#13151c",
    "gold":      "#f5c842",
    "gold_dim":  "#b8962e",
    "green":     "#00d4aa",
    "red":       "#ff4d6d",
    "blue":      "#4d8af0",
    "purple":    "#9b5de5",
    "text":      "#e0e0e0",
    "grid":      "#1e2235",
    "ema20":     "#f5c842",
    "ema50":     "#4d8af0",
    "ema200":    "#ff4d6d",
    "fvg_bull":  "rgba(0,212,170,0.15)",
    "fvg_bear":  "rgba(255,77,109,0.15)",
    "ob_bull":   "rgba(77,138,240,0.2)",
    "ob_bear":   "rgba(155,93,229,0.2)",
    "support":   "rgba(0,212,170,0.6)",
    "resistance":"rgba(255,77,109,0.6)",
}


def _layout(title: str, height: int = 700) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=COLORS["gold"], size=16, family="'JetBrains Mono', monospace")),
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["panel"],
        font=dict(color=COLORS["text"], family="'JetBrains Mono', monospace", size=11),
        xaxis=dict(showgrid=True, gridcolor=COLORS["grid"], showline=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=COLORS["grid"], showline=False, zeroline=False),
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor=COLORS["grid"], borderwidth=1,
                    font=dict(size=10), x=0.01, y=0.99),
        hovermode="x unified",
    )


def build_main_chart(df: pd.DataFrame, signals: list = None, show_smc: bool = True,
                     show_sr: bool = True, show_volume_profile: bool = True) -> go.Figure:
    """Full XAUUSD chart with all overlays."""
    if df is None or len(df) < 50:
        fig = go.Figure()
        fig.update_layout(**_layout("XAUUSD – Insufficient data"))
        return fig

    df_e  = enrich_df(df)
    last  = df_e.tail(200)  # Show last 200 candles

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        vertical_spacing=0.02,
        subplot_titles=("XAUUSD", "Volume", "RSI", "ADX"),
    )

    # ─── CANDLESTICKS ──────────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=last.index, open=last["open"], high=last["high"],
        low=last["low"], close=last["close"],
        name="XAUUSD",
        increasing=dict(line=dict(color=COLORS["green"], width=1), fillcolor=COLORS["green"]),
        decreasing=dict(line=dict(color=COLORS["red"],   width=1), fillcolor=COLORS["red"]),
    ), row=1, col=1)

    # ─── EMAs ─────────────────────────────────────────────────────────────────
    for col, color, name in [("ema20", COLORS["ema20"], "EMA20"),
                              ("ema50", COLORS["ema50"], "EMA50"),
                              ("ema200", COLORS["ema200"], "EMA200")]:
        fig.add_trace(go.Scatter(
            x=last.index, y=last[col], name=name, mode="lines",
            line=dict(color=color, width=1.2, dash="solid"),
        ), row=1, col=1)

    # ─── S/R LEVELS ───────────────────────────────────────────────────────────
    if show_sr:
        sr = find_sr_levels(df)
        for lv in sr.get("resistance", []):
            fig.add_hline(y=lv, row=1, col=1,
                          line=dict(color=COLORS["red"], dash="dash", width=0.8),
                          annotation_text=f"R {lv:.1f}",
                          annotation_font=dict(color=COLORS["red"], size=9),
                          annotation_position="right")
        for lv in sr.get("support", []):
            fig.add_hline(y=lv, row=1, col=1,
                          line=dict(color=COLORS["green"], dash="dash", width=0.8),
                          annotation_text=f"S {lv:.1f}",
                          annotation_font=dict(color=COLORS["green"], size=9),
                          annotation_position="right")

    # ─── VOLUME PROFILE ───────────────────────────────────────────────────────
    if show_volume_profile:
        try:
            vp = volume_profile(last)
            for label, price, color in [("POC", vp["poc"], COLORS["gold"]),
                                         ("VAH", vp["vah"], COLORS["blue"]),
                                         ("VAL", vp["val"], COLORS["purple"])]:
                fig.add_hline(y=price, row=1, col=1,
                              line=dict(color=color, dash="dot", width=1.2),
                              annotation_text=label,
                              annotation_font=dict(color=color, size=9),
                              annotation_position="left")
        except Exception:
            pass

    # ─── SMC OVERLAYS ─────────────────────────────────────────────────────────
    if show_smc:
        # FVGs
        try:
            fvgs = find_fvg(last)
            for fvg in fvgs[-10:]:
                color = COLORS["fvg_bull"] if fvg["type"] == "bullish" else COLORS["fvg_bear"]
                fig.add_hrect(y0=fvg["bottom"], y1=fvg["top"], row=1, col=1,
                              fillcolor=color, line_width=0,
                              annotation_text="FVG",
                              annotation_font=dict(size=8, color=COLORS["text"]))
        except Exception:
            pass

        # Order Blocks
        try:
            obs = find_order_blocks(last)
            for ob in obs[-6:]:
                color = COLORS["ob_bull"] if ob["type"] == "bullish_ob" else COLORS["ob_bear"]
                fig.add_hrect(y0=ob["bottom"], y1=ob["top"], row=1, col=1,
                              fillcolor=color, line_width=0.5,
                              line_color=COLORS["blue"] if "bullish" in ob["type"] else COLORS["purple"],
                              annotation_text="OB",
                              annotation_font=dict(size=8, color=COLORS["text"]))
        except Exception:
            pass

        # CHoCH / BOS
        try:
            events = find_choch_bos(last)
            for ev in events[-5:]:
                color = COLORS["green"] if "Bull" in ev["type"] else COLORS["red"]
                fig.add_vline(x=ev["time"], row=1, col=1,
                              line=dict(color=color, dash="dot", width=0.8),
                              annotation_text=ev["type"].replace("_", " "),
                              annotation_font=dict(size=8, color=color))
        except Exception:
            pass

    # ─── SIGNALS ON CHART ─────────────────────────────────────────────────────
    if signals:
        for sig in signals:
            color = COLORS["green"] if sig["direction"] == "BUY" else COLORS["red"]
            symbol = "triangle-up" if sig["direction"] == "BUY" else "triangle-down"
            fig.add_trace(go.Scatter(
                x=[sig.get("created_at", last.index[-1])],
                y=[sig["entry"]],
                mode="markers+text",
                marker=dict(symbol=symbol, size=14, color=color),
                text=[f"{sig['direction']} {sig['confidence']:.0f}%"],
                textposition="top right" if sig["direction"] == "BUY" else "bottom right",
                textfont=dict(size=9, color=color),
                name=f"{sig['direction']} ({sig['strategy']})",
                showlegend=True,
            ), row=1, col=1)

    # ─── VOLUME ───────────────────────────────────────────────────────────────
    colors_vol = [COLORS["green"] if c >= o else COLORS["red"]
                  for c, o in zip(last["close"], last["open"])]
    fig.add_trace(go.Bar(
        x=last.index, y=last["volume"],
        marker_color=colors_vol, name="Volume", showlegend=False,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=last.index, y=last["vol_sma"], name="Vol MA",
        line=dict(color=COLORS["gold"], width=1), showlegend=False,
    ), row=2, col=1)

    # ─── RSI ──────────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=last.index, y=last["rsi"], name="RSI",
        line=dict(color=COLORS["purple"], width=1.2), showlegend=False,
    ), row=3, col=1)
    fig.add_hline(y=70, row=3, col=1, line=dict(color=COLORS["red"], dash="dash", width=0.8))
    fig.add_hline(y=30, row=3, col=1, line=dict(color=COLORS["green"], dash="dash", width=0.8))
    fig.add_hline(y=50, row=3, col=1, line=dict(color=COLORS["text"], dash="dot", width=0.5))

    # ─── ADX ──────────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=last.index, y=last["adx"], name="ADX",
        line=dict(color=COLORS["gold"], width=1.2), showlegend=False,
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=last.index, y=last["plus_di"], name="+DI",
        line=dict(color=COLORS["green"], width=0.8, dash="dot"), showlegend=False,
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=last.index, y=last["minus_di"], name="-DI",
        line=dict(color=COLORS["red"], width=0.8, dash="dot"), showlegend=False,
    ), row=4, col=1)
    fig.add_hline(y=25, row=4, col=1, line=dict(color=COLORS["text"], dash="dash", width=0.8))

    # ─── LAYOUT ───────────────────────────────────────────────────────────────
    fig.update_layout(**_layout("XAUUSD Live Chart", height=800))
    fig.update_layout(
        xaxis4=dict(showgrid=True, gridcolor=COLORS["grid"]),
        xaxis_rangeslider_visible=False,
    )
    return fig


def build_equity_curve(equity_curve: list, trades: list = None) -> go.Figure:
    """Equity curve chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=equity_curve, mode="lines",
        line=dict(color=COLORS["gold"], width=2),
        fill="tozeroy",
        fillcolor="rgba(245,200,66,0.1)",
        name="Equity",
    ))
    fig.update_layout(**_layout("Equity Curve", height=350))
    return fig


def build_dxy_chart(dxy_df: pd.DataFrame) -> go.Figure:
    """DXY correlation chart."""
    if dxy_df is None or len(dxy_df) < 10:
        fig = go.Figure()
        fig.update_layout(**_layout("DXY – No data"))
        return fig

    last = dxy_df.tail(100)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=last.index, y=last["close"], mode="lines",
        line=dict(color=COLORS["blue"], width=1.5),
        name="DXY",
    ))
    fig.update_layout(**_layout("US Dollar Index (DXY)", height=300))
    return fig


def build_correlation_chart(xau_df: pd.DataFrame, dxy_df: pd.DataFrame) -> go.Figure:
    """Rolling correlation between XAUUSD and DXY."""
    if xau_df is None or dxy_df is None or len(xau_df) < 30 or len(dxy_df) < 30:
        fig = go.Figure()
        fig.update_layout(**_layout("Correlation – Insufficient data"))
        return fig

    # Align on common index
    xau_r = xau_df["close"].pct_change().dropna()
    dxy_r = dxy_df["close"].pct_change().dropna()
    common = xau_r.index.intersection(dxy_r.index)
    if len(common) < 20:
        fig = go.Figure()
        fig.update_layout(**_layout("Correlation – Insufficient overlap"))
        return fig

    corr = xau_r.loc[common].rolling(20).corr(dxy_r.loc[common])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=corr.index, y=corr, mode="lines",
        line=dict(color=COLORS["gold"], width=1.5),
        name="20-bar Rolling Correlation",
    ))
    fig.add_hline(y=0, line=dict(color=COLORS["text"], dash="dash", width=0.8))
    fig.update_layout(**_layout("XAUUSD vs DXY – 20-bar Rolling Correlation", height=280))
    return fig
