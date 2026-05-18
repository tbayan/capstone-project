"""
Streamlit UI — Financial News Analyst

Multi-agent financial analysis interface with real-time agent progress,
structured report display, rating system, and session history.

Run with:
    streamlit run ui/app.py
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import threading
import uuid
from queue import Queue, Empty
from typing import Optional

import streamlit as st

from security.validators import validate_request, ValidationError, rate_limiter
from observability.logger import log_request_start, log_request_end, save_rating, get_recent_requests, get_metrics_summary
from config.settings import DEMO_PASSWORD

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial News Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialisation ───────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if "last_db_id" not in st.session_state:
    st.session_state["last_db_id"] = None

if "analysis_running" not in st.session_state:
    st.session_state["analysis_running"] = False

# ── Auth gate ──────────────────────────────────────────────────────────────────

def _auth_page() -> None:
    st.title("📈 Financial News Analyst")
    st.markdown("**Multi-agent AI system** — Powered by local LLM + RAG + custom MCP server")
    st.divider()
    st.subheader("Access Required")
    pwd = st.text_input("Demo password:", type="password", key="pwd_input")
    if st.button("Enter"):
        if pwd == DEMO_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")


if not st.session_state["authenticated"]:
    _auth_page()
    st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Financial News Analyst")
    st.caption("Multi-agent AI · Local LLM · Custom MCP · RAG")
    st.divider()

    # Input form
    st.subheader("New Analysis")
    ticker_input = st.text_input(
        "Stock Ticker",
        placeholder="e.g. AAPL, NVDA, TSLA",
        max_chars=6,
        help="Enter a valid US stock ticker symbol (1–5 letters)",
    ).strip().upper()

    question_input = st.text_area(
        "Investment Question",
        placeholder="e.g. Is this a good time to invest in NVDA given current AI spending trends?",
        max_chars=500,
        height=100,
    )

    session_id = st.session_state["session_id"]
    remaining = rate_limiter.remaining(session_id)
    st.caption(f"Session: `{session_id}` · Requests remaining: **{remaining}/{10}**")

    run_button = st.button(
        "Run Analysis 🔍",
        type="primary",
        disabled=st.session_state["analysis_running"],
        use_container_width=True,
    )

    st.divider()

    # Metrics summary
    st.subheader("Session Metrics")
    metrics = get_metrics_summary()
    col1, col2 = st.columns(2)
    col1.metric("Total Runs", metrics.get("total_requests", 0))
    col2.metric("Avg Time", f"{(metrics.get('avg_elapsed_sec') or 0):.1f}s")
    col1.metric("👍 Ratings", metrics.get("thumbs_up", 0))
    col2.metric("👎 Ratings", metrics.get("thumbs_down", 0))

    st.divider()

    # Recent history
    st.subheader("Recent History")
    history = get_recent_requests(limit=5)
    if history:
        for h in history:
            rating_icon = "👍" if h["rating"] == 1 else ("👎" if h["rating"] == -1 else "•")
            st.markdown(
                f"{rating_icon} **{h['ticker']}** — _{h['question'][:40]}..._  \n"
                f"<small>{h['timestamp']} · {h['elapsed_sec']:.1f}s</small>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No analyses run yet.")


# ── Main content ───────────────────────────────────────────────────────────────

st.title("📊 Financial Analysis Dashboard")
st.markdown(
    "Powered by **3 AI agents** (Data · News · Analysis) + "
    "**Custom MCP server** + **RAG knowledge base** · All running locally on your machine."
)

# ── Run analysis ───────────────────────────────────────────────────────────────

if run_button and ticker_input and question_input:
    # Validate inputs through security layer
    try:
        clean_ticker, clean_question = validate_request(
            ticker_input, question_input, session_id
        )
    except ValidationError as e:
        st.error(f"Input validation failed: {e}")
        st.stop()

    st.session_state["analysis_running"] = True
    st.session_state["last_result"] = None
    st.session_state["last_db_id"] = None

    log_request_start(clean_ticker, clean_question)

    # ── Progress display ───────────────────────────────────────────────────────
    st.subheader(f"Analysing **{clean_ticker}** ...")
    st.markdown(f"> _{clean_question}_")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 1️⃣ Data Agent")
        data_placeholder = st.empty()
        data_placeholder.info("⏳ Fetching market data via MCP server ...")

    with col2:
        st.markdown("#### 2️⃣ News Agent")
        news_placeholder = st.empty()
        news_placeholder.info("⏳ Waiting for data agent ...")

    with col3:
        st.markdown("#### 3️⃣ Analysis Agent")
        analysis_placeholder = st.empty()
        analysis_placeholder.info("⏳ Waiting for news agent ...")

    report_placeholder = st.empty()
    progress_bar = st.progress(0, text="Starting analysis ...")

    # Run crew in a thread and collect results
    result_container: dict = {}
    error_container: dict = {}

    def _run_crew():
        try:
            from orchestrator.crew import run_analysis
            result = run_analysis(
                ticker=clean_ticker,
                question=clean_question,
            )
            result_container.update(result)
        except Exception as exc:
            from observability.logger import log_error
            log_error("crew_runner", str(exc), type(exc).__name__)
            error_container["error"] = str(exc)

    thread = threading.Thread(target=_run_crew, daemon=True)
    thread.start()

    # Poll for completion with progress updates
    import time
    step = 0
    step_messages = [
        "Data agent fetching market data ...",
        "Data agent retrieving company fundamentals ...",
        "News agent scanning financial feeds ...",
        "News agent analysing sentiment ...",
        "Analysis agent retrieving historical patterns ...",
        "Analysis agent synthesising report ...",
        "Finalising report ...",
    ]

    while thread.is_alive():
        if step < len(step_messages):
            progress_bar.progress(
                min(10 + step * 12, 90),
                text=step_messages[step],
            )
            step += 1
        time.sleep(3)

    thread.join()
    progress_bar.progress(100, text="Analysis complete!")

    if "error" in error_container:
        st.error(f"Analysis failed: {error_container['error']}")
        st.session_state["analysis_running"] = False
        st.stop()

    result = result_container
    db_id = log_request_end(result)
    st.session_state["last_result"] = result
    st.session_state["last_db_id"] = db_id
    st.session_state["analysis_running"] = False

    # Update agent output placeholders
    data_placeholder.success("✅ Data collected")
    news_placeholder.success("✅ News analysed")
    analysis_placeholder.success("✅ Report generated")

    with col1:
        with st.expander("View Data Agent Output"):
            st.text(result.get("data_summary", "No output."))

    with col2:
        with st.expander("View News Agent Output"):
            st.text(result.get("news_summary", "No output."))

    st.divider()

    # Final report
    st.subheader("📋 Investment Analysis Report")
    st.markdown(result.get("report", "No report generated."))

    st.divider()
    elapsed = result.get("elapsed_seconds", 0)
    st.caption(f"⏱ Analysis completed in **{elapsed}s** · Ticker: `{clean_ticker}` · Session: `{session_id}`")

    # Rating widget
    st.subheader("Was this analysis helpful?")
    r_col1, r_col2, r_col3 = st.columns([1, 1, 6])
    if r_col1.button("👍 Yes", key="thumbs_up"):
        save_rating(db_id, 1)
        st.success("Thanks for the feedback!")
    if r_col2.button("👎 No", key="thumbs_down"):
        save_rating(db_id, -1)
        st.info("Thanks — we'll use this to improve.")

    # Download report
    report_text = (
        f"Financial Analysis Report\n"
        f"Ticker: {clean_ticker}\n"
        f"Question: {clean_question}\n"
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'='*60}\n\n"
        f"{result.get('report', '')}"
    )
    st.download_button(
        "⬇️ Download Report (.txt)",
        data=report_text,
        file_name=f"analysis_{clean_ticker}_{time.strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )

elif run_button and (not ticker_input or not question_input):
    st.warning("Please enter both a ticker symbol and an investment question.")

# ── Show previous result if no new run ────────────────────────────────────────
elif st.session_state.get("last_result") and not run_button:
    result = st.session_state["last_result"]
    st.subheader(f"📋 Last Analysis: {result.get('ticker')}")
    st.markdown(f"> _{result.get('question')}_")
    st.divider()
    st.markdown(result.get("report", ""))

    db_id = st.session_state.get("last_db_id")
    if db_id:
        r_col1, r_col2, _ = st.columns([1, 1, 6])
        if r_col1.button("👍", key="re_up"):
            save_rating(db_id, 1)
            st.success("Saved!")
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
