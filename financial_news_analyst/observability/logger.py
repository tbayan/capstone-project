"""
Observability — structured logging, metrics tracking, and SQLite audit trail.

Tracks:
  - Every analysis request (ticker, question, timing, outputs)
  - Per-agent step timing and output length (proxy for token usage)
  - User ratings (thumbs up/down)
  - Error events

All data is written to:
  - logs/app.log  (human-readable structured log via loguru)
  - logs/audit.db (SQLite for querying and UI history)
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlite3
import time
import json
from contextlib import contextmanager
from typing import Optional

from loguru import logger

from config.settings import LOG_FILE_PATH, AUDIT_DB_PATH

# ── Loguru setup ───────────────────────────────────────────────────────────────
logger.remove()  # remove default stderr sink
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)
logger.add(
    LOG_FILE_PATH,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)


# ── SQLite setup ───────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUDIT_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create audit tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_requests (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                ticker       TEXT NOT NULL,
                question     TEXT NOT NULL,
                elapsed_sec  REAL,
                data_len     INTEGER,
                news_len     INTEGER,
                report_len   INTEGER,
                token_est    INTEGER,
                error        TEXT,
                rating       INTEGER   -- NULL until rated; 1=thumbs up, -1=thumbs down
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_steps (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id   INTEGER,
                agent_role   TEXT NOT NULL,
                step_time_ms INTEGER,
                output_len   INTEGER,
                FOREIGN KEY (request_id) REFERENCES analysis_requests(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                component    TEXT,
                message      TEXT,
                details      TEXT
            )
        """)
        conn.commit()
        # Schema migration: add 'report' column if it doesn't exist yet
        try:
            conn.execute("ALTER TABLE analysis_requests ADD COLUMN report TEXT")
            conn.commit()
        except Exception:
            pass  # Column already exists


# Initialise on import
init_db()


# ── Logging helpers ────────────────────────────────────────────────────────────

def log_request_start(ticker: str, question: str) -> str:
    """Log the start of an analysis request. Returns a request_id string."""
    request_id = f"{ticker}_{int(time.time())}"
    logger.info(f"[REQUEST START] ticker={ticker} question='{question[:60]}...' id={request_id}")
    return request_id


def log_request_end(result: dict) -> int:
    """
    Persist a completed analysis request to the audit DB.

    Args:
        result: The dict returned by orchestrator.crew.run_analysis().

    Returns:
        The SQLite row id of the inserted record.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    ticker = result.get("ticker", "")
    question = result.get("question", "")
    elapsed = result.get("elapsed_seconds", 0)
    data_len = len(result.get("data_summary", ""))
    news_len = len(result.get("news_summary", ""))
    report_len = len(result.get("report", ""))
    # Estimate token usage: chars / 4 (rough approximation)
    token_est = (data_len + news_len + report_len) // 4

    logger.success(
        f"[REQUEST END] ticker={ticker} elapsed={elapsed}s "
        f"report_len={report_len} token_est={token_est}"
    )

    report_text = result.get("report", "")

    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO analysis_requests
               (timestamp, ticker, question, elapsed_sec, data_len, news_len, report_len, token_est, report)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, ticker, question, elapsed, data_len, news_len, report_len, token_est, report_text),
        )
        conn.commit()
        return cur.lastrowid


def log_agent_step(request_db_id: int, agent_role: str, output: str, step_time_ms: int) -> None:
    """Log an individual agent step to the audit DB."""
    logger.debug(
        f"[AGENT STEP] role='{agent_role}' time={step_time_ms}ms output_len={len(output)}"
    )
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO agent_steps (request_id, agent_role, step_time_ms, output_len)
               VALUES (?, ?, ?, ?)""",
            (request_db_id, agent_role, step_time_ms, len(output)),
        )
        conn.commit()


def save_rating(request_db_id: int, rating: int) -> None:
    """
    Save a user rating for an analysis (1 = thumbs up, -1 = thumbs down).

    Args:
        request_db_id: The SQLite row id from log_request_end().
        rating: 1 (positive) or -1 (negative).
    """
    rating = 1 if rating > 0 else -1
    logger.info(f"[RATING] request_id={request_db_id} rating={rating}")
    with _get_conn() as conn:
        conn.execute(
            "UPDATE analysis_requests SET rating = ? WHERE id = ?",
            (rating, request_db_id),
        )
        conn.commit()


def log_error(component: str, message: str, details: str = "") -> None:
    """Log an error event to both loguru and the audit DB."""
    logger.error(f"[ERROR] component={component} msg='{message}' details='{details[:200]}'")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO error_events (timestamp, component, message, details) VALUES (?, ?, ?, ?)",
            (timestamp, component, message, details[:1000]),
        )
        conn.commit()


# ── Query helpers for the UI ───────────────────────────────────────────────────

def get_recent_requests(limit: int = 10) -> list[dict]:
    """Return the most recent analysis requests from the audit DB."""
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT id, timestamp, ticker, question, elapsed_sec, report_len, token_est, rating
               FROM analysis_requests ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_request_by_id(request_id: int) -> dict | None:
    """Return a single analysis request including the full report text."""
    with _get_conn() as conn:
        row = conn.execute(
            """SELECT id, timestamp, ticker, question, elapsed_sec, report, rating
               FROM analysis_requests WHERE id = ?""",
            (request_id,),
        ).fetchone()
    return dict(row) if row else None


def get_metrics_summary() -> dict:
    """Return aggregate metrics for the observability dashboard."""
    with _get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)            AS total_requests,
                AVG(elapsed_sec)    AS avg_elapsed_sec,
                SUM(token_est)      AS total_tokens_est,
                SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS thumbs_up,
                SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS thumbs_down,
                COUNT(error)        AS error_count
            FROM analysis_requests
        """).fetchone()
    return dict(row) if row else {}
