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
    page_title="Financial News Analyst",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS theme ───────────────────────────────────────────────────────────
# Professional financial portal palette — white main area, deep navy sidebar

_CSS = """
<style>
/* ── Palette ── */
:root {
    --bg:        #f0f4f8;
    --surface:   #ffffff;
    --card:      #ffffff;
    --border:    #dde5ef;
    --border2:   #c8d5e3;
    --nav:       #0b2340;
    --nav2:      #0f2d52;
    --accent:    #1561c0;
    --accent-lt: #1a72d9;
    --text:      #1a2738;
    --dim:       #5a6a7e;
    --muted:     #8fa0b3;
    --ok:        #1a7a44;
    --err:       #b91c1c;
    --warn:      #92400e;
    --mono:      'Fira Code', 'Cascadia Code', 'SF Mono', monospace;
}

/* ── App background ── */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
}

/* ── Sidebar — deep navy ── */
[data-testid="stSidebar"] {
    background-color: var(--nav) !important;
    border-right: none !important;
    box-shadow: 2px 0 8px rgba(0,0,0,0.12) !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span:not([data-testid]),
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption { color: rgba(196,218,238,0.85) !important; }

/* Sidebar inputs */
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background-color: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: #ddeef8 !important;
    caret-color: #5ab4f0 !important;
}
[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder,
[data-testid="stSidebar"] .stTextArea > div > div > textarea::placeholder {
    color: rgba(150,185,215,0.5) !important;
}
[data-testid="stSidebar"] .stTextInput > div > div > input:focus,
[data-testid="stSidebar"] .stTextArea > div > div > textarea:focus {
    border-color: #4a9ede !important;
    box-shadow: 0 0 0 2px rgba(74,158,222,0.2) !important;
}
[data-testid="stSidebar"] .stTextInput > label,
[data-testid="stSidebar"] .stTextArea > label {
    color: rgba(160,190,220,0.7) !important;
    font-size: .68rem !important;
    font-family: var(--mono) !important;
    text-transform: uppercase !important;
    letter-spacing: .09em !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background-color: #1e72d4 !important;
    color: #ffffff !important;
    border: none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background-color: #2a86e8 !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: rgba(190,215,238,0.8) !important;
    background: transparent !important;
    font-size: .75rem !important;
    text-align: left !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
    border-color: #4a9ede !important;
    color: #7ec8f0 !important;
    background: rgba(74,158,222,0.1) !important;
}

/* Sidebar metrics */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: rgba(155,190,220,0.75) !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #ddeef8 !important; }

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
    opacity: 1 !important;
}

/* ── Main block ── */
.main .block-container {
    padding-top: 1.75rem !important;
    padding-left: 2.25rem !important;
    padding-right: 2.25rem !important;
    max-width: 1440px !important;
}

/* ── Typography ── */
h1 { font-size: 1.25rem !important; font-weight: 700 !important; color: var(--text) !important; letter-spacing: -.01em !important; }
h2 { font-size: 1.05rem !important; font-weight: 600 !important; color: var(--text) !important; }
h3 { font-size: .95rem !important; font-weight: 600 !important; color: var(--text) !important; }
h4 { font-size: .78rem !important; font-weight: 600 !important; color: var(--dim) !important; text-transform: uppercase !important; letter-spacing: .08em !important; }
p, li { color: var(--text) !important; line-height: 1.72 !important; }

/* ── Main area inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 4px !important;
    font-size: .875rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(21,97,192,0.1) !important;
    outline: none !important;
}
.stTextInput > label, .stTextArea > label {
    color: var(--dim) !important;
    font-size: .68rem !important;
    font-family: var(--mono) !important;
    text-transform: uppercase !important;
    letter-spacing: .09em !important;
}

/* ── Main area primary button ── */
.stButton > button[kind="primary"] {
    background-color: var(--accent) !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 600 !important;
    letter-spacing: .08em !important;
    text-transform: uppercase !important;
    font-size: .7rem !important;
    border-radius: 4px !important;
    height: 38px !important;
}
.stButton > button[kind="primary"]:hover { background-color: var(--accent-lt) !important; }

/* ── Main area secondary button ── */
.stButton > button:not([kind="primary"]) {
    background: transparent !important;
    border: 1.5px solid var(--border2) !important;
    color: var(--dim) !important;
    border-radius: 4px !important;
    font-size: .78rem !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: rgba(21,97,192,0.04) !important;
}

/* ── Main area metrics ── */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
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
hr { border-color: var(--border) !important; opacity: 1 !important; margin: 14px 0 !important; }

/* ── Alerts ── */
.stAlert { border-radius: 4px !important; }

/* ── Expander ── */
details {
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    background: var(--surface) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
details summary {
    color: var(--dim) !important;
    font-size: .8rem !important;
    padding: 8px 14px !important;
}

/* ── Captions ── */
.stCaption { color: var(--dim) !important; font-size: .72rem !important; font-family: var(--mono) !important; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div { background-color: var(--accent) !important; }
[data-testid="stProgressBar"] { background-color: var(--border) !important; border-radius: 2px !important; }

/* ── Code ── */
code {
    background: rgba(21,97,192,0.08) !important;
    color: var(--accent) !important;
    border-radius: 3px !important;
    padding: 1px 5px !important;
    font-family: var(--mono) !important;
    font-size: .82em !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: transparent !important;
    border: 1px solid var(--border2) !important;
    color: var(--dim) !important;
    font-size: .72rem !important;
    border-radius: 4px !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: rgba(21,97,192,0.04) !important;
}
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
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    .stApp, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    .main .block-container {
        max-width: 320px !important;
        padding-top: 22vh !important;
        margin: 0 auto !important;
    }
    /* Login card */
    .login-card {
        background: #ffffff;
        border: 1px solid #dde5ef;
        border-top: 3px solid #1561c0;
        border-radius: 6px;
        padding: 32px 28px 28px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    }
    </style>
    <div class="login-card">
        <div style="margin-bottom:22px;">
            <div style="
                font-size:1.5rem;
                font-weight:800;
                color:#0b2340;
                letter-spacing:-.01em;
                line-height:1.1;
            ">Financial News<br>Analyst</div>
            <div style="
                font-size:.72rem;
                color:#8fa0b3;
                margin-top:5px;
                letter-spacing:.03em;
            ">Investment Research Platform</div>
        </div>
        <div style="border-top:1px solid #dde5ef; margin-bottom:20px;"></div>
    </div>
    """, unsafe_allow_html=True)

    pwd = st.text_input("Access key", placeholder="Enter access key",
                        type="password", key="pwd_input", label_visibility="hidden")

    if st.button("Sign In", type="primary", use_container_width=True):
        if pwd == DEMO_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid access key.")

    st.markdown("""
    <div style="text-align:center; margin-top:16px; font-size:.65rem; color:#c8d5e3;">
        Secure · Local Inference
    </div>
    """, unsafe_allow_html=True)


if not st.session_state["authenticated"]:
    _auth_page()
    st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:6px 0 16px 0;">
        <div style="
            font-size:.58rem;
            color:rgba(100,160,210,0.55);
            letter-spacing:.2em;
            text-transform:uppercase;
            font-family:'Fira Code',monospace;
            margin-bottom:5px;
        ">◈ RESEARCH PLATFORM</div>
        <div style="
            font-size:1.05rem;
            font-weight:700;
            color:#ddeef8;
            letter-spacing:-.01em;
            line-height:1.25;
        ">Financial News<br>Analyst</div>
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

    st.divider()
    # ── Logout ──
    if st.button("Log Out", key="logout_btn", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()


# ── Main content ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="
    display:flex;
    align-items:center;
    gap:10px;
    padding-bottom:16px;
    border-bottom:2px solid #dde5ef;
    margin-bottom:22px;
">
    <div style="
        width:4px;
        height:22px;
        background:#1561c0;
        border-radius:2px;
    "></div>
    <span style="
        font-size:1.15rem;
        font-weight:700;
        color:#1a2738;
        letter-spacing:-.01em;
    ">Financial News Analyst</span>
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
        if rc2.button("▼", key="re_down"):
            save_rating(db_id, -1)
            st.info("Saved.")

else:
    # Welcome state
    st.markdown("""
    <div style="
        background:#ffffff;
        border:1px solid #dde5ef;
        border-left:3px solid #1561c0;
        border-radius:6px;
        padding:20px 24px;
        margin-top:8px;
    ">
        <div style="font-size:.95rem; font-weight:600; color:#1a2738; margin-bottom:8px;">
            Ready for analysis
        </div>
        <div style="font-size:.82rem; color:#5a6a7e; line-height:1.7;">
            Enter a <strong>ticker symbol</strong> and your <strong>research question</strong>
            in the sidebar panel, then click <strong>Run Analysis</strong>.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    st.caption("For educational purposes only. Not financial advice.")
