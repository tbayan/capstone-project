"""Streamlit UI — Financial News Analyst"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import threading
import uuid
import time

import streamlit as st
import psutil

from security.validators import validate_request, ValidationError, rate_limiter
from observability.logger import (
    log_request_start, log_request_end, save_rating,
    get_recent_requests, get_request_by_id, get_metrics_summary,
)
from config.settings import DEMO_PASSWORD

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FNA · Financial News Analyst",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS theme ───────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Palette ── */
:root {
    --bg:       #07091a;
    --surface:  #0c1424;
    --card:     #0f1a2e;
    --border:   #1a304f;
    --accent:   #0ea5e9;
    --purple:   #818cf8;
    --text:     #cbd5e1;
    --dim:      #475569;
    --muted:    #1e3a5f;
    --ok:       #22c55e;
    --err:      #f87171;
    --warn:     #fbbf24;
    --mono:     'Fira Code', 'Cascadia Code', 'SF Mono', monospace;
}

/* ── App background + subtle star field ── */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    background-image:
        radial-gradient(ellipse at 18% 28%, rgba(14,165,233,0.055) 0%, transparent 44%),
        radial-gradient(ellipse at 80% 70%, rgba(129,140,248,0.045) 0%, transparent 44%),
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Ccircle cx='14' cy='22' r='0.8' fill='%23fff' fill-opacity='.2'/%3E%3Ccircle cx='94' cy='12' r='0.5' fill='%237dd3fc' fill-opacity='.36'/%3E%3Ccircle cx='50' cy='102' r='0.9' fill='%23fff' fill-opacity='.15'/%3E%3Ccircle cx='138' cy='58' r='0.6' fill='%23fff' fill-opacity='.26'/%3E%3Ccircle cx='72' cy='44' r='0.5' fill='%237dd3fc' fill-opacity='.28'/%3E%3Ccircle cx='26' cy='80' r='0.4' fill='%23fff' fill-opacity='.13'/%3E%3Ccircle cx='116' cy='130' r='0.7' fill='%237dd3fc' fill-opacity='.2'/%3E%3Ccircle cx='7' cy='142' r='0.5' fill='%23fff' fill-opacity='.17'/%3E%3Ccircle cx='158' cy='30' r='0.6' fill='%23fff' fill-opacity='.22'/%3E%3Ccircle cx='62' cy='160' r='0.4' fill='%237dd3fc' fill-opacity='.18'/%3E%3Ccircle cx='170' cy='92' r='0.5' fill='%23fff' fill-opacity='.19'/%3E%3Ccircle cx='40' cy='168' r='0.6' fill='%23fff' fill-opacity='.14'/%3E%3Ccircle cx='148' cy='148' r='0.4' fill='%237dd3fc' fill-opacity='.15'/%3E%3C/svg%3E") !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span:not([data-testid]),
[data-testid="stSidebar"] small { color: var(--text) !important; }

/* ── Main block ── */
.main .block-container {
    padding-top: 1.75rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1480px !important;
}

/* ── Typography ── */
h1 { font-size: 1.3rem !important; font-weight: 700 !important; color: var(--text) !important; letter-spacing: -.015em !important; margin-bottom: .25rem !important; }
h2 { font-size: 1.05rem !important; font-weight: 600 !important; color: var(--text) !important; }
h3 { font-size: .92rem !important; font-weight: 600 !important; color: var(--text) !important; }
h4 { font-size: .85rem !important; font-weight: 600 !important; color: var(--dim) !important; text-transform: uppercase; letter-spacing: .07em !important; }
p, li { color: var(--text) !important; line-height: 1.72 !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 3px !important;
    font-size: .875rem !important;
    caret-color: var(--accent) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(14,165,233,.12) !important;
    outline: none !important;
}
.stTextInput > label, .stTextArea > label {
    color: var(--dim) !important;
    font-size: .7rem !important;
    font-family: var(--mono) !important;
    text-transform: uppercase !important;
    letter-spacing: .09em !important;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background-color: var(--accent) !important;
    color: #040810 !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
    font-size: .7rem !important;
    border-radius: 3px !important;
    height: 38px !important;
}
.stButton > button[kind="primary"]:hover { background-color: #38bdf8 !important; }
.stButton > button:not([kind="primary"]) {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--dim) !important;
    border-radius: 3px !important;
    font-size: .78rem !important;
    transition: border-color .15s, color .15s !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 10px 14px !important;
}
[data-testid="stMetricLabel"] {
    color: var(--dim) !important;
    font-size: .62rem !important;
    text-transform: uppercase !important;
    letter-spacing: .1em !important;
    font-family: var(--mono) !important;
}
[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 1.05rem !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; opacity: .55 !important; margin: 14px 0 !important; }

/* ── Alert boxes ── */
.stAlert { background-color: var(--card) !important; border-radius: 4px !important; border-left-width: 3px !important; }
div[data-baseweb="notification"] { background-color: var(--card) !important; }

/* ── Expander ── */
details {
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    background: var(--card) !important;
}
details summary {
    color: var(--dim) !important;
    font-size: .78rem !important;
    font-family: var(--mono) !important;
    padding: 8px 12px !important;
}

/* ── Captions ── */
.stCaption { color: var(--dim) !important; font-size: .7rem !important; font-family: var(--mono) !important; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div { background-color: var(--accent) !important; }
[data-testid="stProgressBar"] { background-color: var(--card) !important; border-radius: 2px !important; }

/* ── Code ── */
code {
    background: rgba(14,165,233,.1) !important;
    color: var(--accent) !important;
    border-radius: 2px !important;
    padding: 1px 5px !important;
    font-family: var(--mono) !important;
    font-size: .82em !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: transparent !important;
    border: 1px solid var(--muted) !important;
    color: var(--dim) !important;
    font-size: .7rem !important;
    letter-spacing: .07em !important;
    border-radius: 3px !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Auth page overrides ── */
.auth-hide-sidebar [data-testid="stSidebar"] { display: none !important; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── Session state initialisation ───────────────────────────────────────────────

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

# ── Auth gate ──────────────────────────────────────────────────────────────────

def _auth_page() -> None:
    # Hide sidebar + center block for the login screen
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    .main .block-container {
        max-width: 400px !important;
        padding-top: 18vh !important;
        margin: 0 auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding-bottom:28px;">
        <div style="
            font-family:'Fira Code','SF Mono',monospace;
            font-size:.6rem;
            color:#0ea5e9;
            letter-spacing:.28em;
            text-transform:uppercase;
            opacity:.75;
            margin-bottom:10px;
        ">Multi-Agent · RAG · MCP</div>
        <div style="
            font-size:2.8rem;
            font-weight:800;
            color:#e2e8f0;
            letter-spacing:-.03em;
            line-height:1;
            font-family:'Inter',-apple-system,sans-serif;
        ">FNA</div>
        <div style="
            font-size:.78rem;
            color:#475569;
            margin-top:6px;
            letter-spacing:.06em;
        ">Financial News Analyst</div>
    </div>
    <div style="border-top:1px solid #1a304f; margin-bottom:22px;"></div>
    """, unsafe_allow_html=True)

    pwd = st.text_input("Access key", placeholder="Enter access key", type="password",
                        key="pwd_input", label_visibility="hidden")

    if st.button("ENTER", type="primary", use_container_width=True):
        if pwd == DEMO_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid access key.")

    st.markdown("""
    <div style="
        text-align:center;
        margin-top:24px;
        font-family:'Fira Code',monospace;
        font-size:.58rem;
        color:#1a304f;
        letter-spacing:.1em;
    ">local inference · zero data egress</div>
    """, unsafe_allow_html=True)


if not st.session_state["authenticated"]:
    _auth_page()
    st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 18px 0;">
        <div style="
            font-family:'Fira Code',monospace;
            font-size:.58rem;
            color:#0ea5e9;
            letter-spacing:.22em;
            text-transform:uppercase;
            opacity:.7;
            margin-bottom:4px;
        ">Financial Intelligence</div>
        <div style="
            font-size:1.35rem;
            font-weight:800;
            color:#e2e8f0;
            letter-spacing:-.02em;
            line-height:1;
        ">FNA</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Input form ──
    st.markdown("#### Analysis")

    ticker_input = st.text_input(
        "Ticker",
        placeholder="AAPL · NVDA · TSLA",
        max_chars=6,
        help="US stock ticker (1–6 characters)",
    ).strip().upper()

    question_input = st.text_area(
        "Question",
        placeholder="e.g. What are the key risk factors for NVDA heading into Q3?",
        max_chars=500,
        height=90,
    )

    session_id = st.session_state["session_id"]
    remaining = rate_limiter.remaining(session_id)
    st.caption(f"`{session_id}` · {remaining}/10 remaining")

    run_button = st.button(
        "RUN ANALYSIS",
        type="primary",
        disabled=st.session_state["analysis_running"],
        use_container_width=True,
    )

    st.divider()

    # ── Metrics ──
    st.markdown("#### Metrics")
    metrics = get_metrics_summary()
    mc1, mc2 = st.columns(2)
    mc1.metric("Runs", metrics.get("total_requests", 0))
    mc2.metric("Avg", f"{(metrics.get('avg_elapsed_sec') or 0):.0f}s")
    mc1.metric("▲", metrics.get("thumbs_up", 0))
    mc2.metric("▼", metrics.get("thumbs_down", 0))

    st.divider()

    # ── System resources ──
    st.markdown("#### Resources")
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    proc_mb = round(psutil.Process().memory_info().rss / 1_048_576, 1)
    rc1, rc2 = st.columns(2)
    rc1.metric("CPU", f"{cpu:.0f}%")
    rc2.metric("RAM", f"{mem.percent:.0f}%")
    st.caption(f"proc `{proc_mb} MB` · free `{round(mem.available/1_073_741_824,1)} GB`")

    st.divider()

    # ── History ──
    st.markdown("#### History")
    history = get_recent_requests(limit=5)
    if history:
        for h in history:
            mark = "▲" if h["rating"] == 1 else ("▼" if h["rating"] == -1 else "·")
            label = f"{mark} **{h['ticker']}** {h['question'][:32]}…"
            if st.button(label, key=f"hist_{h['id']}", use_container_width=True):
                full = get_request_by_id(h["id"])
                st.session_state["viewed_history"] = {
                    "ticker": full["ticker"] if full else h["ticker"],
                    "question": full["question"] if full else h["question"],
                    "report": (full.get("report") or None) if full else None,
                    "elapsed_seconds": (full.get("elapsed_sec") or 0) if full else 0,
                    "db_id": h["id"],
                }
                st.rerun()
            st.caption(f"{h['timestamp'][:16]} · {h['elapsed_sec']:.1f}s")
    else:
        st.caption("No analyses yet.")


# ── Main content ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="
    display:flex;
    align-items:baseline;
    gap:14px;
    padding-bottom:18px;
    border-bottom:1px solid #1a304f;
    margin-bottom:20px;
">
    <span style="font-size:1.15rem; font-weight:700; color:#e2e8f0; letter-spacing:-.01em;">
        Financial News Analyst
    </span>
    <span style="
        font-family:'Fira Code',monospace;
        font-size:.6rem;
        color:#475569;
        letter-spacing:.08em;
    ">v1.0 · local inference · zero egress</span>
</div>
""", unsafe_allow_html=True)

# ── Run analysis ───────────────────────────────────────────────────────────────

if run_button and ticker_input and question_input:
    try:
        clean_ticker, clean_question = validate_request(
            ticker_input, question_input, session_id
        )
    except ValidationError as e:
        st.error(f"{e}")
        st.stop()

    st.session_state["analysis_running"] = True
    st.session_state["last_result"] = None
    st.session_state["last_db_id"] = None
    st.session_state["viewed_history"] = None

    log_request_start(clean_ticker, clean_question)

    # ── Progress display ──
    st.markdown(f"### {clean_ticker}")
    st.caption(clean_question)
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### [01] Data Agent")
        data_ph = st.empty()
        data_ph.info("Fetching market data …")
    with col2:
        st.markdown("#### [02] News Agent")
        news_ph = st.empty()
        news_ph.info("Awaiting data agent …")
    with col3:
        st.markdown("#### [03] Analysis Agent")
        anls_ph = st.empty()
        anls_ph.info("Awaiting news agent …")

    progress_bar = st.progress(0, text="Initialising pipeline …")

    result_container: dict = {}
    error_container: dict = {}

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
        "Retrieving company fundamentals …",
        "Scanning financial news feeds …",
        "Assessing sentiment …",
        "Retrieving historical patterns (RAG) …",
        "Synthesising report …",
        "Finalising …",
    ]
    _step = 0
    while thread.is_alive():
        if _step < len(_steps):
            progress_bar.progress(min(10 + _step * 12, 90), text=_steps[_step])
            _step += 1
        time.sleep(3)

    thread.join()
    progress_bar.progress(100, text="Complete.")

    if "error" in error_container:
        st.error(f"Pipeline error: {error_container['error']}")
        st.session_state["analysis_running"] = False
        st.stop()

    result = result_container
    db_id = log_request_end(result)
    st.session_state["last_result"] = result
    st.session_state["last_db_id"] = db_id
    st.session_state["analysis_running"] = False

    data_ph.success("Data collected")
    news_ph.success("News analysed")
    anls_ph.success("Report generated")

    with col1:
        with st.expander("Data agent output"):
            st.text(result.get("data_summary", "—"))
    with col2:
        with st.expander("News agent output"):
            st.text(result.get("news_summary", "—"))
    with col3:
        rag_sources = result.get("rag_sources", [])
        label = f"Knowledge base sources ({len(rag_sources)} retrieved)"
        with st.expander(label):
            if rag_sources:
                for i, src in enumerate(rag_sources, 1):
                    score = src.get("score", 0)
                    st.markdown(
                        f"**{i}.** `{src.get('source','?')}` "
                        f"— *{src.get('category','reference')}* "
                        f"— relevance `{score:.2f}`"
                    )
                    st.caption((src.get("content","")[:280] + "…") if len(src.get("content","")) > 280 else src.get("content",""))
                    st.divider()
            else:
                st.caption("No sources met the relevance threshold.")

    st.divider()
    st.markdown("### Analysis Report")
    st.markdown(result.get("report", "No report generated."))

    st.divider()
    elapsed = result.get("elapsed_seconds", 0)
    st.caption(f"`{clean_ticker}` · {elapsed}s · session `{session_id}`")

    # ── Rating ──
    st.markdown("#### Rate this analysis")
    rc1, rc2, _ = st.columns([1, 1, 8])
    if rc1.button("▲", key="thumbs_up"):
        save_rating(db_id, 1)
        st.success("Saved.")
    if rc2.button("▼", key="thumbs_down"):
        save_rating(db_id, -1)
        st.info("Saved.")

    # ── Download ──
    report_txt = (
        f"Financial Analysis Report\nTicker: {clean_ticker}\n"
        f"Question: {clean_question}\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'─'*60}\n\n{result.get('report','')}"
    )
    st.download_button(
        "Download report (.txt)",
        data=report_txt,
        file_name=f"fna_{clean_ticker}_{time.strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )

elif run_button and (not ticker_input or not question_input):
    st.warning("Ticker and question are both required.")

# ── History viewer ─────────────────────────────────────────────────────────────
elif st.session_state.get("viewed_history"):
    vh = st.session_state["viewed_history"]
    back = "← Current analysis" if st.session_state.get("last_result") else "← Back"
    if st.button(back, key="back_from_history"):
        st.session_state["viewed_history"] = None
        st.rerun()

    st.markdown(f"### {vh['ticker']}")
    st.caption(vh["question"])
    st.caption(f"{vh['elapsed_seconds']:.1f}s")
    st.divider()

    if vh.get("report"):
        st.markdown(vh["report"])
        db_id = vh.get("db_id")
        if db_id:
            hc1, hc2, _ = st.columns([1, 1, 8])
            if hc1.button("▲", key="hist_up"):
                save_rating(db_id, 1); st.success("Saved.")
            if hc2.button("▼", key="hist_down"):
                save_rating(db_id, -1); st.info("Saved.")
    else:
        st.info("Report not stored for this entry. Run a new analysis to capture full output.")

# ── Persist last result ────────────────────────────────────────────────────────
elif st.session_state.get("last_result") and not run_button:
    result = st.session_state["last_result"]
    st.markdown(f"### {result.get('ticker')}")
    st.caption(result.get("question", ""))
    st.divider()
    st.markdown(result.get("report", ""))

    rag_sources = result.get("rag_sources", [])
    if rag_sources:
        with st.expander(f"Knowledge base sources ({len(rag_sources)} retrieved)"):
            for i, src in enumerate(rag_sources, 1):
                score = src.get("score", 0)
                st.markdown(
                    f"**{i}.** `{src.get('source','?')}` "
                    f"— *{src.get('category','reference')}* "
                    f"— relevance `{score:.2f}`"
                )
                st.caption((src.get("content","")[:280] + "…") if len(src.get("content","")) > 280 else src.get("content",""))
                st.divider()

    db_id = st.session_state.get("last_db_id")
    if db_id:
        rc1, rc2, _ = st.columns([1, 1, 8])
        if rc1.button("▲", key="re_up"):
            save_rating(db_id, 1)
            st.success("Saved.")
        if r_col2.button("👎", key="re_down"):
            save_rating(db_id, -1)
            st.info("Saved!")

else:
    # Welcome state
    st.info(
        "👈 Enter a ticker and question in the sidebar, then click **Run Analysis** to start."
    )
    st.markdown("""
    ### How it works

    | Step | Agent | What it does |
    |------|-------|-------------|
    | 1 | **Data Agent** | Calls your custom MCP server to fetch live stock prices and company fundamentals via yfinance |
    | 2 | **News Agent** | Calls your custom MCP server to scrape financial news from free RSS feeds |
    | 3 | **Analysis Agent** | Retrieves relevant patterns from the RAG knowledge base, then synthesises all inputs into a structured investment report |

    All three agents run locally on your machine using **Ollama (qwen2.5:7b)**.
    No API keys required. No data leaves your computer.
    """)

    st.divider()
    st.caption("⚠️ This system is for educational purposes only. Not financial advice.")
