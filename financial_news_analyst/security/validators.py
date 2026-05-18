"""
Security layer — input validation, rate limiting, content guardrails.

All user inputs pass through this module before reaching the agent crew.
Implements OWASP-aligned protections:
  - Input sanitisation (injection prevention)
  - Rate limiting (abuse prevention)
  - Content filtering (harmful output prevention)
  - Ticker symbol validation (type/format checking)
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
import time
from collections import defaultdict
from typing import Optional

from config.settings import (
    MAX_TICKER_LENGTH,
    MAX_QUERY_LENGTH,
    RATE_LIMIT_REQUESTS,
    INJECTION_PATTERNS,
    FINANCIAL_DISCLAIMER_TRIGGERS,
    DISCLAIMER_TEXT,
)

# ── Ticker validation ──────────────────────────────────────────────────────────

_TICKER_RE = re.compile(r"^[A-Z\^]{1,6}$")   # allows ^ for index tickers like ^VIX


class ValidationError(ValueError):
    """Raised when input validation fails — caught by the UI layer."""
    pass


def validate_ticker(symbol: str) -> str:
    """
    Validate and normalise a stock ticker symbol.

    Rules:
      - Must be 1–6 uppercase letters (or ^ for index symbols)
      - Strip surrounding whitespace
      - Reject SQL/script injection attempts

    Returns:
        Uppercased, stripped valid ticker.

    Raises:
        ValidationError: If the symbol fails validation.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Ticker symbol must be a non-empty string.")

    symbol = symbol.strip().upper()

    if len(symbol) > MAX_TICKER_LENGTH + 1:   # +1 for ^ prefix
        raise ValidationError(
            f"Ticker symbol too long (max {MAX_TICKER_LENGTH} characters): '{symbol}'"
        )

    if not _TICKER_RE.match(symbol):
        raise ValidationError(
            f"Invalid ticker symbol '{symbol}'. "
            "Only uppercase letters A-Z (and ^ for indices) are allowed."
        )

    return symbol


# ── Query validation ───────────────────────────────────────────────────────────

_HTML_SCRIPT_RE = re.compile(r"<[^>]*>", re.IGNORECASE)


def validate_query(query: str) -> str:
    """
    Validate and sanitise a user query string.

    Protections:
      - Strip HTML and script tags (XSS prevention)
      - Check length limit
      - Detect and block prompt injection patterns

    Returns:
        Sanitised query string.

    Raises:
        ValidationError: If the query contains injection patterns or is too long.
    """
    if not query or not isinstance(query, str):
        raise ValidationError("Query must be a non-empty string.")

    # Strip HTML tags
    query = _HTML_SCRIPT_RE.sub("", query).strip()

    # Collapse excessive whitespace
    query = re.sub(r"\s+", " ", query)

    if len(query) > MAX_QUERY_LENGTH:
        raise ValidationError(
            f"Query too long ({len(query)} chars). Maximum is {MAX_QUERY_LENGTH} characters."
        )

    # Check for prompt injection patterns
    query_lower = query.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern.lower() in query_lower:
            raise ValidationError(
                f"Query contains a disallowed phrase: '{pattern}'. "
                "Please ask a genuine investment question."
            )

    return query


# ── Rate limiting ──────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Simple in-memory rate limiter (per session ID).

    Allows up to RATE_LIMIT_REQUESTS requests per rolling 1-hour window.
    Sufficient for demo purposes; replace with Redis for production.
    """

    def __init__(self) -> None:
        # {session_id: [timestamp, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._window_seconds = 3600   # 1 hour

    def check(self, session_id: str) -> None:
        """
        Check rate limit for a session.

        Raises:
            ValidationError: If the session has exceeded the rate limit.
        """
        now = time.time()
        cutoff = now - self._window_seconds
        timestamps = self._requests[session_id]

        # Prune old timestamps outside the window
        self._requests[session_id] = [t for t in timestamps if t > cutoff]

        if len(self._requests[session_id]) >= RATE_LIMIT_REQUESTS:
            raise ValidationError(
                f"Rate limit exceeded: maximum {RATE_LIMIT_REQUESTS} requests per hour. "
                "Please wait before making another request."
            )

    def record(self, session_id: str) -> None:
        """Record a new request for a session."""
        self._requests[session_id].append(time.time())

    def remaining(self, session_id: str) -> int:
        """Return how many requests the session has remaining in the current window."""
        now = time.time()
        cutoff = now - self._window_seconds
        active = [t for t in self._requests.get(session_id, []) if t > cutoff]
        return max(0, RATE_LIMIT_REQUESTS - len(active))


# Module-level singleton rate limiter
rate_limiter = RateLimiter()


# ── Guardrails ─────────────────────────────────────────────────────────────────

def apply_output_guardrails(text: str) -> str:
    """
    Post-process agent output to enforce content guardrails.

    - Detects phrases that imply guaranteed returns or risk-free investments
    - Appends mandatory disclaimer if triggered or if no disclaimer is present
    - Does NOT alter the core analysis content

    Returns:
        The original text with disclaimer appended if needed.
    """
    text_lower = text.lower()
    needs_disclaimer = False

    for trigger in FINANCIAL_DISCLAIMER_TRIGGERS:
        if trigger.lower() in text_lower:
            needs_disclaimer = True
            break

    # Always ensure disclaimer is present
    if "not financial advice" not in text_lower and "not constitute financial advice" not in text_lower:
        needs_disclaimer = True

    if needs_disclaimer and DISCLAIMER_TEXT not in text:
        text += DISCLAIMER_TEXT

    return text


# ── Combined validation entry point ───────────────────────────────────────────

def validate_request(ticker: str, question: str, session_id: str) -> tuple[str, str]:
    """
    Validate a full analysis request (ticker + question + rate limit check).

    Returns:
        Tuple of (validated_ticker, validated_question).

    Raises:
        ValidationError: On any validation failure.
    """
    rate_limiter.check(session_id)
    clean_ticker = validate_ticker(ticker)
    clean_question = validate_query(question)
    rate_limiter.record(session_id)
    return clean_ticker, clean_question
