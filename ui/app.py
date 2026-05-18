"""Streamlit UI — Financial News Analyst"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
import threading
import uuid
import time
from datetime import datetime

import streamlit as st
import psutil
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from security.validators import validate_request, ValidationError, rate_limiter
from observability.logger import (
    log_request_start, log_request_end, save_rating,
    get_recent_requests, get_request_by_id, get_metrics_summary,
)
from config.settings import DEMO_PASSWORD

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial News Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SimplyWallSt-inspired dark palette ────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg:       #0d1220;
    --surface:  #131929;
    --card:     #192133;
    --card2:    #1e2a40;
    --border:   #253350;
    --border2:  #2e3f60;
    --teal:     #00c9a7;
    --teal-dim: rgba(0,201,167,0.13);
    --purple:   #7b5ea7;
    --blue:     #3d7cf5;
    --text:     #dde6f0;
    --dim:      #7a8caa;
    --muted:    #3a4a6a;
    --err:      #e05561;
    --warn:     #f5a623;
    --up:       #00c9a7;
    --down:     #e05561;
    --mono:     'Fira Code','Cascadia Code','SF Mono',monospace;
    --sans:     'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    font-family: var(--sans) !important;
    color: var(--text) !important;
}
.main .block-container {
    padding-top: 0 !important;
    padding-left: 1.75rem !important;
    padding-right: 1.75rem !important;
    max-width: 1500px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #090e18 !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small { color: var(--dim) !important; }
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: var(--card) !important;
    border: 1px solid var(--border2) !important;
    color: var(--text) !important;
    caret-color: var(--teal) !important;
    border-radius: 5px !important;
}
[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder,
[data-testid="stSidebar"] .stTextArea > div > div > textarea::placeholder { color: var(--muted) !important; }
[data-testid="stSidebar"] .stTextInput > div > div > input:focus,
[data-testid="stSidebar"] .stTextArea > div > div > textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 2px var(--teal-dim) !important;
}
[data-testid="stSidebar"] .stTextInput > label,
[data-testid="stSidebar"] .stTextArea > label {
    font-size:.66rem !important; font-family:var(--mono) !important;
    text-transform:uppercase !important; letter-spacing:.1em !important;
    color:var(--dim) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--teal) !important; color: #0d1220 !important;
    border: none !important; font-weight: 700 !important;
    letter-spacing:.09em !important; text-transform:uppercase !important;
    font-size:.67rem !important; border-radius:5px !important; height:38px !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover { background:#00e0b9 !important; }
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
    background: transparent !important; border: 1px solid var(--border2) !important;
    color: var(--dim) !important; border-radius:5px !important;
    font-size:.73rem !important; text-align:left !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
    border-color:var(--teal) !important; color:var(--teal) !important;
    background:var(--teal-dim) !important;
}
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background:var(--card) !important; border:1px solid var(--border) !important;
    border-radius:6px !important; box-shadow:none !important; padding:8px 12px !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    font-size:.58rem !important; font-family:var(--mono) !important;
    text-transform:uppercase !important; letter-spacing:.1em !important; color:var(--dim) !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color:var(--text) !important; font-family:var(--mono) !important; font-size:.92rem !important; }
[data-testid="stSidebar"] hr { border-color:var(--border) !important; opacity:1 !important; }

/* ── Main typography ── */
h1 { font-size:1.2rem !important; font-weight:700 !important; color:var(--text) !important; }
h2 { font-size:1rem !important; font-weight:600 !important; color:var(--text) !important; }
h3 { font-size:.92rem !important; font-weight:600 !important; color:var(--text) !important; }
h4 { font-size:.75rem !important; font-weight:600 !important; color:var(--dim) !important; text-transform:uppercase !important; letter-spacing:.1em !important; }
p, li { color:var(--text) !important; line-height:1.8 !important; font-size:.88rem !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background:var(--card) !important; border:1px solid var(--border2) !important;
    color:var(--text) !important; border-radius:5px !important;
    font-family:var(--sans) !important; font-size:.875rem !important;
    caret-color:var(--teal) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color:var(--teal) !important; box-shadow:0 0 0 2px var(--teal-dim) !important;
}
.stTextInput > label, .stTextArea > label {
    color:var(--dim) !important; font-size:.66rem !important;
    font-family:var(--mono) !important; text-transform:uppercase !important; letter-spacing:.1em !important;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background:var(--teal) !important; color:#0d1220 !important;
    border:none !important; font-weight:700 !important;
    letter-spacing:.09em !important; text-transform:uppercase !important;
    font-size:.68rem !important; border-radius:5px !important; height:38px !important;
}
.stButton > button[kind="primary"]:hover { background:#00e0b9 !important; }
.stButton > button:not([kind="primary"]) {
    background:transparent !important; border:1px solid var(--border2) !important;
    color:var(--dim) !important; border-radius:5px !important; font-size:.78rem !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color:var(--teal) !important; color:var(--teal) !important; background:var(--teal-dim) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background:var(--card) !important; border:1px solid var(--border) !important;
    border-radius:8px !important; padding:12px 16px !important;
    box-shadow:0 2px 8px rgba(0,0,0,0.25) !important;
}
[data-testid="stMetricLabel"] {
    color:var(--dim) !important; font-size:.58rem !important; text-transform:uppercase !important;
    letter-spacing:.1em !important; font-family:var(--mono) !important;
}
[data-testid="stMetricValue"] { color:var(--text) !important; font-family:var(--mono) !important; font-size:1.05rem !important; }

/* ── Alerts ── */
.stAlert { background:var(--card2) !important; border-radius:6px !important; border-left-width:3px !important; }
.stAlert p { font-size:.82rem !important; }

/* ── Expander ── */
details { background:var(--card) !important; border:1px solid var(--border) !important; border-radius:8px !important; }
details summary { color:var(--dim) !important; font-size:.78rem !important; padding:10px 16px !important; }
details > div { padding:0 16px 14px !important; }

/* ── Divider / caption / code / scroll ── */
hr { border-color:var(--border) !important; opacity:1 !important; margin:12px 0 !important; }
.stCaption { color:var(--dim) !important; font-size:.7rem !important; font-family:var(--mono) !important; }
code { background:rgba(0,201,167,.1) !important; color:var(--teal) !important; border-radius:3px !important; padding:1px 5px !important; font-family:var(--mono) !important; font-size:.8em !important; }
[data-testid="stProgressBar"] { background:var(--card2) !important; border-radius:2px !important; }
[data-testid="stProgressBar"] > div > div { background:var(--teal) !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }

/* ── Download ── */
[data-testid="stDownloadButton"] > button {
    background:transparent !important; border:1px solid var(--border2) !important;
    color:var(--dim) !important; font-size:.7rem !important; border-radius:5px !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color:var(--teal) !important; color:var(--teal) !important; background:var(--teal-dim) !important;
}

/* ── Narrative report ── */
.report-body { font-family:var(--sans) !important; }
.report-body h2 {
    font-size:.68rem !important; font-weight:600 !important; color:var(--teal) !important;
    text-transform:uppercase !important; letter-spacing:.14em !important;
    margin:22px 0 8px !important; padding-bottom:5px !important;
    border-bottom:1px solid var(--border) !important;
}
.report-body p {
    font-size:.875rem !important; line-height:1.84 !important;
    color:var(--text) !important; margin-bottom:12px !important;
    font-family:var(--sans) !important;
}
.report-body strong { color:#c8e0f8 !important; font-weight:600 !important; }

/* ── Ticker tape ── */
.ticker-tape-wrap {
    overflow:hidden; background:#070c15;
    border-bottom:1px solid var(--border);
    padding:7px 0; width:100%; margin-bottom:14px;
}
.ticker-tape {
    display:inline-block; white-space:nowrap;
    animation:marquee 45s linear infinite;
    font-family:var(--mono); font-size:.7rem;
}
.ticker-tape:hover { animation-play-state:paused; }
@keyframes marquee { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.t-sym  { color:#c8d8ec; font-weight:600; margin-right:2px; }
.t-px   { color:#8fa5c0; }
.t-up   { color:#00c9a7; font-weight:600; }
.t-dn   { color:#e05561; font-weight:600; }
.t-sep  { color:#1e2a40; margin:0 16px; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────

for _k, _v in [
    ("session_id", str(uuid.uuid4())[:8]),
    ("authenticated", False),
    ("last_result", None),
    ("last_db_id", None),
    ("analysis_running", False),
    ("viewed_history", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Helpers ────────────────────────────────────────────────────────────────────

_CRYPTO_SYMBOLS = {
    "BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","DOT",
    "MATIC","LINK","UNI","LTC","BCH","ATOM","NEAR","APT","SUI",
}
_TAPE_TICKERS = ["SPY","QQQ","NVDA","AAPL","TSLA","AMZN","MSFT","BTC-USD","ETH-USD","GLD"]


def _is_crypto(ticker: str) -> bool:
    return ticker.upper() in _CRYPTO_SYMBOLS or ticker.upper().endswith("-USD")


def _yf_ticker(ticker: str) -> str:
    t = ticker.upper()
    return f"{t}-USD" if t in _CRYPTO_SYMBOLS else t


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_tape_html() -> str:
    items = []
    for sym in _TAPE_TICKERS:
        try:
            info = yf.Ticker(sym).fast_info
            price = getattr(info, "last_price", None)
            prev  = getattr(info, "previous_close", None)
            if not price or not prev or prev == 0:
                continue
            pct = (price - prev) / prev * 100
            cls = "t-up" if pct >= 0 else "t-dn"
            sign = "+" if pct >= 0 else ""
            label = sym.replace("-USD", "")
            items.append(
                f'<span class="t-sym">{label}</span>'
                f'<span class="t-px"> ${price:,.2f}</span>'
                f'<span class="{cls}"> {sign}{pct:.2f}%</span>'
                f'<span class="t-sep">|</span>'
            )
        except Exception:
            continue
    if not items:
        return ""
    inner = "  ".join(items)
    return inner + "&nbsp;" * 10 + inner   # doubled for seamless loop


def _render_tape() -> None:
    html = _fetch_tape_html()
    if not html:
        return
    st.markdown(
        f'<div class="ticker-tape-wrap"><div class="ticker-tape">{html}</div></div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_ohlcv(ticker: str):
    return yf.download(_yf_ticker(ticker), period="6mo", interval="1d",
                       progress=False, auto_adjust=True)


def _render_chart(ticker: str) -> None:
    with st.spinner(f"Loading {ticker} chart …"):
        try:
            df = _fetch_ohlcv(ticker)
        except Exception:
            st.caption("Chart unavailable.")
            return

    if df is None or df.empty:
        st.caption("No price data for chart.")
        return

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    if not {"Open","High","Low","Close","Volume"}.issubset(df.columns):
        st.caption("Incomplete OHLCV data.")
        return

    colors = ["#00c9a7" if c >= o else "#e05561"
              for c, o in zip(df["Close"], df["Open"])]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.02,
    )
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color="#00c9a7", decreasing_line_color="#e05561",
        increasing_fillcolor="#00c9a7", decreasing_fillcolor="#e05561",
        line_width=1, name=ticker,
    ), row=1, col=1)

    sma20 = df["Close"].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=df.index, y=sma20,
        line=dict(color="#7b5ea7", width=1.2, dash="dot"),
        name="SMA 20",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        marker_color=colors, marker_opacity=0.5,
        name="Volume", showlegend=False,
    ), row=2, col=1)

    axis_cfg = dict(gridcolor="#1e2a40", zerolinecolor="#1e2a40",
                    showline=False, tickfont=dict(color="#7a8caa", size=9))
    fig.update_layout(
        height=320, margin=dict(l=0, r=0, t=6, b=0),
        paper_bgcolor="#0d1220", plot_bgcolor="#0d1220",
        font=dict(family="Inter,sans-serif", color="#7a8caa", size=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", x=0, y=1.02,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=9, color="#7a8caa")),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#192133", font_color="#dde6f0", font_size=11),
        xaxis=axis_cfg, xaxis2=axis_cfg, yaxis=axis_cfg, yaxis2=axis_cfg,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_report(report: str) -> None:
    """Render LLM output as styled narrative prose."""
    if not report:
        st.caption("No report generated.")
        return
    lines = report.strip().split("\n")
    parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^#{1,3} ", line):
            heading = re.sub(r"^#{1,3} ", "", line)
            parts.append(f"<h2>{heading}</h2>")
        elif re.match(r"^[-*•]\s+", line):
            text = re.sub(r"^[-*•]\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            parts.append(f"<p>{text}</p>")
        elif re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            parts.append(f"<p>{text}</p>")
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            parts.append(f"<p>{text}</p>")
    st.markdown(f'<div class="report-body">{"".join(parts)}</div>', unsafe_allow_html=True)


# ── Auth page ──────────────────────────────────────────────────────────────────

def _auth_page() -> None:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display:none !important; }
    [data-testid="stHeader"]  { background:transparent !important; }

    /* ── Galaxy pixel-art background ────────────────────────────────────────── */
    /* 5 star layers on prime-number grids (no visible repeating grid lines)    */
    /* + 3 nebula glow blobs in purple / deep-blue / teal                       */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #040812 !important;
        background-image:
            radial-gradient(circle, rgba(255,255,255,.92) 1px, transparent 1px),
            radial-gradient(circle, rgba(255,255,255,.55) 1px, transparent 1px),
            radial-gradient(circle, rgba(255,230,150,.78) 1px, transparent 1px),
            radial-gradient(circle, rgba(185,145,255,.68) 1px, transparent 1px),
            radial-gradient(circle, rgba(0,201,167,.58)   1px, transparent 1px),
            radial-gradient(ellipse 300px 220px at 14% 56%, rgba(88,28,160,.28) 0%, transparent 65%),
            radial-gradient(ellipse 220px 340px at 83% 21%, rgba(22,52,165,.22) 0%, transparent 65%),
            radial-gradient(ellipse 340px 150px at 57% 87%, rgba(0,88,72,.15)   0%, transparent 65%) !important;
        background-size:
            53px 53px, 79px 67px, 97px 83px, 131px 71px, 61px 109px,
            100% 100%, 100% 100%, 100% 100% !important;
        background-position:
            7px 11px, 38px 52px, 67px 24px, 14px 81px, 44px 37px,
            0 0, 0 0, 0 0 !important;
        background-attachment: fixed !important;
    }

    /* Reset block container so column layout controls width */
    .main .block-container {
        max-width: 100% !important;
        padding-top: 10vh !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* ── Login card inputs ───────────────────────────────────────────────────── */
    .stTextInput > label { display:none !important; }
    .stTextInput > div > div > input {
        background: #0b1422 !important;
        border: 1px solid #243048 !important;
        color: #dde6f0 !important;
        border-radius: 8px !important;
        text-align: center !important;
        font-size: .85rem !important;
        letter-spacing: .04em !important;
        padding: 9px 12px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #f97316 !important;
        box-shadow: 0 0 0 2px rgba(249,115,22,.18) !important;
        outline: none !important;
    }
    .stTextInput > div > div > input::placeholder { color: #2a3a58 !important; }

    /* ── Sign In button ──────────────────────────────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg,#f97316,#ea6c0a) !important;
        color: #fff !important; font-weight: 700 !important;
        font-size: .72rem !important; letter-spacing: .14em !important;
        text-transform: uppercase !important; border: none !important;
        border-radius: 8px !important; height: 40px !important;
        width: 100% !important; margin-top: 2px !important;
        transition: all .18s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg,#fb923c,#f97316) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(249,115,22,.42) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Columns center the card reliably across all screen widths
    _, col, _ = st.columns([1.5, 1, 1.5])
    with col:
        # Card header — logo + title (pure HTML, no widget interaction needed)
        st.markdown("""
        <div style="
            background: rgba(10,15,28,0.88);
            border: 1px solid #1c2840;
            border-radius: 18px;
            padding: 30px 24px 22px;
            text-align: center;
            backdrop-filter: blur(14px);
            box-shadow: 0 8px 40px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.03);
            margin-bottom: 10px;
        ">
            <div style="
                display:inline-flex; align-items:center; justify-content:center;
                width:56px; height:56px;
                background: linear-gradient(135deg,#f97316,#c2410c);
                border-radius:14px; margin-bottom:16px;
                box-shadow: 0 6px 24px rgba(249,115,22,.42);
            ">
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="2"  y="18" width="6" height="10" rx="1.5" fill="white" opacity=".9"/>
                    <rect x="12" y="10" width="6" height="18" rx="1.5" fill="white"/>
                    <rect x="22" y="3"  width="6" height="25" rx="1.5" fill="white" opacity=".85"/>
                    <polyline points="5,18 15,10 25,3" stroke="white" stroke-width="1.5"
                        stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".5"/>
                </svg>
            </div>
            <div style="font-size:.98rem; font-weight:700; color:#dde6f0; letter-spacing:-.01em; line-height:1.2;">
                Financial News Analyst
            </div>
            <div style="font-size:.58rem; color:#2e3f60; margin-top:5px; letter-spacing:.13em; text-transform:uppercase;">
                Capstone Project
            </div>
        </div>
        """, unsafe_allow_html=True)

        pwd = st.text_input("key", placeholder="Enter access key",
                            type="password", key="pwd_input", label_visibility="hidden")

        if st.button("Sign In", type="primary", use_container_width=True):
            if pwd == DEMO_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid access key.")

        st.markdown("""
        <div style="text-align:center; margin-top:14px; font-size:.54rem; color:#151e30; letter-spacing:.1em;">
            LOCAL &nbsp;·&nbsp; PRIVATE &nbsp;·&nbsp; ZERO EGRESS
        </div>
        """, unsafe_allow_html=True)


if not st.session_state["authenticated"]:
    _auth_page()
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:10px 0 18px;">
        <div style="display:inline-flex; align-items:center; gap:9px;">
            <div style="
                width:30px; height:30px;
                background:linear-gradient(135deg,#f97316,#c2410c);
                border-radius:7px; display:flex; align-items:center;
                justify-content:center; flex-shrink:0;
                box-shadow:0 3px 10px rgba(249,115,22,.35);
            ">
                <svg width="16" height="16" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="2"  y="18" width="6" height="10" rx="1.5" fill="white" opacity=".9"/>
                    <rect x="12" y="10" width="6" height="18" rx="1.5" fill="white"/>
                    <rect x="22" y="3"  width="6" height="25" rx="1.5" fill="white" opacity=".85"/>
                    <polyline points="5,18 15,10 25,3" stroke="white" stroke-width="1.5"
                        stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".5"/>
                </svg>
            </div>
            <div>
                <div style="font-size:.88rem; font-weight:700; color:#dde6f0; line-height:1.2;">FNA</div>
                <div style="font-size:.55rem; color:#3a4a6a; letter-spacing:.12em; text-transform:uppercase;">
                    Research Platform
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">New Analysis</p>', unsafe_allow_html=True)

    ticker_input = st.text_input(
        "Ticker", placeholder="AAPL · NVDA · BTC",
        max_chars=8, help="US stock or crypto ticker",
    ).strip().upper()

    question_input = st.text_area(
        "Research question",
        placeholder="e.g. What are the key risks heading into Q3?",
        max_chars=500, height=88,
    )

    session_id = st.session_state["session_id"]
    remaining = rate_limiter.remaining(session_id)
    st.caption(f"session `{session_id}` · {remaining}/10 left")

    run_button = st.button(
        "Run Analysis",
        type="primary",
        disabled=st.session_state["analysis_running"],
        use_container_width=True,
    )

    st.divider()

    st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">Metrics</p>', unsafe_allow_html=True)
    metrics = get_metrics_summary()
    mc1, mc2 = st.columns(2)
    mc1.metric("Total", metrics.get("total_requests", 0))
    mc2.metric("Avg", f"{(metrics.get('avg_elapsed_sec') or 0):.0f}s")
    mc1.metric("▲ Good", metrics.get("thumbs_up", 0))
    mc2.metric("▼ Poor", metrics.get("thumbs_down", 0))

    st.divider()

    st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">System</p>', unsafe_allow_html=True)
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    sc1, sc2 = st.columns(2)
    sc1.metric("CPU", f"{cpu:.0f}%")
    sc2.metric("RAM", f"{mem.percent:.0f}%")
    proc_mb = round(psutil.Process().memory_info().rss / 1_048_576, 1)
    st.caption(f"proc `{proc_mb} MB` · free `{round(mem.available/1_073_741_824,1)} GB`")

    st.divider()

    st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">Recent Analyses</p>', unsafe_allow_html=True)
    history = get_recent_requests(limit=6)
    if history:
        for h in history:
            dot_color = "#00c9a7" if h["rating"] == 1 else ("#e05561" if h["rating"] == -1 else "#3a4a6a")
            btn_label = f"{h['ticker']}  {h['question'][:26]}…"
            if st.button(btn_label, key=f"hist_{h['id']}", use_container_width=True):
                full = get_request_by_id(h["id"])
                st.session_state["viewed_history"] = {
                    "ticker": full["ticker"] if full else h["ticker"],
                    "question": full["question"] if full else h["question"],
                    "report": (full.get("report") or None) if full else None,
                    "elapsed_seconds": (full.get("elapsed_sec") or 0) if full else 0,
                    "db_id": h["id"],
                }
                st.rerun()
            st.markdown(
                f'<div style="margin-top:-5px;margin-bottom:5px;font-size:.61rem;color:#3a4a6a;">'
                f'<span style="color:{dot_color}">●</span>'
                f' {h["timestamp"][:16]} · {h["elapsed_sec"]:.0f}s</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<p style="font-size:.72rem;color:#2e3f60;font-style:italic;">No analyses yet.</p>', unsafe_allow_html=True)

    st.divider()
    if st.button("Log Out", key="logout_btn", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# ── Main content ───────────────────────────────────────────────────────────────

_render_tape()

st.markdown("""
<div style="display:flex;align-items:center;gap:12px;padding-bottom:14px;border-bottom:1px solid #253350;margin-bottom:18px;">
    <div style="
        display:inline-flex; align-items:center; justify-content:center;
        width:34px; height:34px; flex-shrink:0;
        background:linear-gradient(135deg,#f97316,#c2410c);
        border-radius:9px;
        box-shadow:0 3px 12px rgba(249,115,22,.35);
    ">
        <svg width="18" height="18" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2"  y="18" width="6" height="10" rx="1.5" fill="white" opacity=".9"/>
            <rect x="12" y="10" width="6" height="18" rx="1.5" fill="white"/>
            <rect x="22" y="3"  width="6" height="25" rx="1.5" fill="white" opacity=".85"/>
            <polyline points="5,18 15,10 25,3" stroke="white" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".5"/>
        </svg>
    </div>
    <span style="font-size:1.08rem;font-weight:700;color:#dde6f0;letter-spacing:-.01em;">Financial News Analyst</span>
    <span style="font-size:.58rem;color:#3a4a6a;font-family:'Fira Code',monospace;letter-spacing:.06em;">qwen3:8b</span>
</div>
""", unsafe_allow_html=True)

# ── Run analysis ───────────────────────────────────────────────────────────────

# Pop any pending run saved by the button handler (triggers after a clean rerun)
_pending = st.session_state.pop("_pending_run", None)

if _pending:
    clean_ticker   = _pending["ticker"]
    clean_question = _pending["question"]
    log_request_start(clean_ticker, clean_question)

    # Chart is always first
    _render_chart(clean_ticker)

    st.markdown(
        f'<div style="margin:10px 0 4px;">'
        f'<span style="font-size:1.1rem;font-weight:700;color:#dde6f0;">{clean_ticker}</span>'
        f'<span style="font-size:.78rem;color:#7a8caa;margin-left:10px;">{clean_question}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.1em;text-transform:uppercase;margin-bottom:3px;">01 · Data Agent</p>', unsafe_allow_html=True)
        data_ph = st.empty(); data_ph.info("Fetching market data …")
    with pc2:
        st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.1em;text-transform:uppercase;margin-bottom:3px;">02 · News Agent</p>', unsafe_allow_html=True)
        news_ph = st.empty(); news_ph.info("Awaiting data …")
    with pc3:
        st.markdown('<p style="font-size:.62rem;color:#7a8caa;letter-spacing:.1em;text-transform:uppercase;margin-bottom:3px;">03 · Analysis Agent</p>', unsafe_allow_html=True)
        anls_ph = st.empty(); anls_ph.info("Awaiting news …")

    progress_bar = st.progress(0, text="Initialising pipeline …")

    result_container: dict = {}
    error_container:  dict = {}

    def _run_crew() -> None:
        try:
            from orchestrator.crew import run_analysis
            result_container.update(run_analysis(ticker=clean_ticker, question=clean_question))
        except Exception as exc:
            from observability.logger import log_error
            log_error("crew_runner", str(exc), type(exc).__name__)
            error_container["error"] = str(exc)

    thread = threading.Thread(target=_run_crew, daemon=True)
    thread.start()

    _steps = [
        "Fetching market data …",
        "Loading company fundamentals …",
        "Scanning news feeds …",
        "Assessing sentiment …",
        "Retrieving knowledge base …",
        "Synthesising research note …",
        "Finalising …",
    ]
    _step = 0
    _loop_start = time.time()
    while thread.is_alive():
        if _step < len(_steps):
            progress_bar.progress(min(8 + _step * 13, 90), text=_steps[_step])
            if _step == 1: data_ph.success("Market data collected")
            if _step == 3: news_ph.success("News analysed")
            if _step == 5: anls_ph.info("Synthesising report …")
            _step += 1
        else:
            elapsed_s = int(time.time() - _loop_start)
            progress_bar.progress(90, text=f"Agents still working … ({elapsed_s}s elapsed)")
        time.sleep(10)

    thread.join()
    progress_bar.progress(100, text="Complete.")

    if "error" in error_container:
        st.error(f"Pipeline error: {error_container['error']}")
        st.session_state["analysis_running"] = False
        st.stop()

    result = result_container
    db_id  = log_request_end(result)
    st.session_state.update({"last_result": result, "last_db_id": db_id, "analysis_running": False})

    data_ph.success("Data collected")
    news_ph.success("News analysed")
    anls_ph.success("Report generated")

    with st.expander("Raw agent outputs", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Data Agent", "News Agent", "Knowledge Base"])
        with tab1: st.text(result.get("data_summary", "—"))
        with tab2: st.text(result.get("news_summary", "—"))
        with tab3:
            rag = result.get("rag_sources", [])
            if rag:
                for i, src in enumerate(rag, 1):
                    st.markdown(f"**{i}.** `{src.get('source','?')}` — relevance `{src.get('score',0):.2f}`")
                    content = src.get("content", "")
                    st.caption((content[:300] + "…") if len(content) > 300 else content)
                    if i < len(rag): st.divider()
            else:
                st.caption("No sources above threshold.")

    st.divider()
    _render_report(result.get("report", ""))
    st.divider()

    elapsed = result.get("elapsed_seconds", 0)
    st.markdown(
        f'<p style="font-size:.65rem;color:#2e3f60;font-family:monospace;">'
        f'{clean_ticker} · {datetime.now().strftime("%Y-%m-%d %H:%M")} · {elapsed:.0f}s · {session_id}'
        f'</p>',
        unsafe_allow_html=True,
    )

    cr1, cr2, cr3, _ = st.columns([1.2, 1.2, 2, 5.6])
    if cr1.button("▲ Useful", key="thumbs_up"):
        save_rating(db_id, 1); st.success("Saved.")
    if cr2.button("▼ Poor", key="thumbs_down"):
        save_rating(db_id, -1); st.info("Saved.")
    with cr3:
        report_txt = (
            f"Financial Analysis Report\nTicker: {clean_ticker}\n"
            f"Question: {clean_question}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'─'*60}\n\n{result.get('report','')}"
        )
        st.download_button(
            "↓ Download report",
            data=report_txt,
            file_name=f"fna_{clean_ticker}_{time.strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
        )

elif run_button and ticker_input and question_input:
    # Validate input, clear old state, then rerun so the page is blank before analysis starts
    try:
        clean_ticker, clean_question = validate_request(ticker_input, question_input, session_id)
    except ValidationError as e:
        st.error(str(e))
        st.stop()
    st.session_state.update({
        "analysis_running": True,
        "last_result": None,
        "last_db_id": None,
        "viewed_history": None,
        "_pending_run": {"ticker": clean_ticker, "question": clean_question},
    })
    st.rerun()

elif run_button and (not ticker_input or not question_input):
    st.warning("Ticker and question are both required.")

# ── History viewer ─────────────────────────────────────────────────────────────
elif st.session_state.get("viewed_history"):
    vh = st.session_state["viewed_history"]
    if st.button("← Back", key="back_from_history"):
        st.session_state["viewed_history"] = None
        st.rerun()

    _render_chart(vh["ticker"])
    st.markdown(
        f'<div style="margin:10px 0 4px;">'
        f'<span style="font-size:1.1rem;font-weight:700;color:#dde6f0;">{vh["ticker"]}</span>'
        f'<span style="font-size:.78rem;color:#7a8caa;margin-left:10px;">{vh["question"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"{vh['elapsed_seconds']:.0f}s")
    st.divider()

    if vh.get("report"):
        _render_report(vh["report"])
        db_id = vh.get("db_id")
        if db_id:
            hc1, hc2, _ = st.columns([1.2, 1.2, 7.6])
            if hc1.button("▲ Useful", key="hist_up"):
                save_rating(db_id, 1); st.success("Saved.")
            if hc2.button("▼ Poor", key="hist_down"):
                save_rating(db_id, -1); st.info("Saved.")
    else:
        st.info("Full report not stored for this entry.")

# ── Persist last result on re-render ──────────────────────────────────────────
elif st.session_state.get("last_result") and not run_button:
    result = st.session_state["last_result"]
    ticker = result.get("ticker", "")

    _render_chart(ticker)
    st.markdown(
        f'<div style="margin:10px 0 4px;">'
        f'<span style="font-size:1.1rem;font-weight:700;color:#dde6f0;">{ticker}</span>'
        f'<span style="font-size:.78rem;color:#7a8caa;margin-left:10px;">{result.get("question","")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    _render_report(result.get("report", ""))

    rag = result.get("rag_sources", [])
    if rag:
        with st.expander(f"Knowledge base sources ({len(rag)})"):
            for i, src in enumerate(rag, 1):
                st.markdown(f"**{i}.** `{src.get('source','?')}` — relevance `{src.get('score',0):.2f}`")
                content = src.get("content", "")
                st.caption((content[:300] + "…") if len(content) > 300 else content)

    db_id = st.session_state.get("last_db_id")
    if db_id:
        rc1, rc2, _ = st.columns([1.2, 1.2, 7.6])
        if rc1.button("▲ Useful", key="re_up"):
            save_rating(db_id, 1); st.success("Saved.")
        if rc2.button("▼ Poor", key="re_down"):
            save_rating(db_id, -1); st.info("Saved.")

else:
    # ── Welcome state ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background:#131929; border:1px solid #253350;
        border-top:2px solid #00c9a7; border-radius:8px;
        padding:24px 28px; margin-top:4px; max-width:620px;
    ">
        <div style="font-size:.92rem;font-weight:600;color:#dde6f0;margin-bottom:10px;">
            Ready for research
        </div>
        <div style="font-size:.83rem;color:#7a8caa;line-height:1.78;">
            Enter a <span style="color:#00c9a7;font-weight:500;">ticker symbol</span>
            (equity or crypto) and your research question in the sidebar,
            then click <span style="color:#dde6f0;font-weight:600;">Run Analysis</span>.
            The platform fetches live market data and news, retrieves relevant context
            from the knowledge base, and synthesises a professional research note.
        </div>
    </div>
    <p style="font-size:.62rem;color:#1e2a40;margin-top:14px;font-family:monospace;">
        For educational purposes only · Not financial advice
    </p>
    """, unsafe_allow_html=True)
