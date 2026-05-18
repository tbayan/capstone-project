"""
News fetcher tools — RSS-based financial news scraper exposed via the custom MCP server.

Aggregates multiple free RSS feeds; no API keys required.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import time
from typing import Any
from html import unescape

import feedparser
import requests

from config.settings import RSS_FEEDS


# ── HTML stripping ─────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    if not text:
        return ""
    return unescape(_HTML_TAG_RE.sub(" ", text)).strip()


def _clean_text(text: str, max_len: int = 500) -> str:
    cleaned = _strip_html(text)
    # collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_len]


# ── Core fetch ─────────────────────────────────────────────────────────────────

def _parse_feed(url: str, timeout: int = 8) -> list[dict[str, Any]]:
    """Parse a single RSS feed, return list of entry dicts."""
    try:
        # feedparser handles network issues gracefully, but set a timeout via requests
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "FinancialNewsAnalyst/1.0"})
        feed = feedparser.parse(response.text)
        articles = []
        for entry in feed.entries:
            title = _clean_text(entry.get("title", ""), 200)
            summary = _clean_text(entry.get("summary", "") or entry.get("description", ""), 500)
            link = entry.get("link", "")
            published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
            published = (
                time.strftime("%Y-%m-%d %H:%M", published_struct)
                if published_struct else "unknown"
            )
            if title:
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "published": published,
                    "source": url,
                })
        return articles
    except Exception as exc:
        return [{"error": f"Failed to fetch {url}: {str(exc)}"}]


def fetch_financial_news(query: str = "", limit: int = 10) -> list[dict[str, Any]]:
    """
    Aggregate financial news from multiple free RSS feeds.

    Args:
        query: Optional keyword filter applied to title + summary (case-insensitive).
        limit: Maximum number of articles to return.

    Returns:
        List of article dicts: {title, summary, url, published, source}.
    """
    query_lower = query.lower().strip()
    all_articles: list[dict[str, Any]] = []

    for feed_url in RSS_FEEDS:
        articles = _parse_feed(feed_url)
        for art in articles:
            if "error" in art:
                continue
            # filter by query if provided
            if query_lower:
                combined = (art["title"] + " " + art["summary"]).lower()
                if query_lower not in combined:
                    continue
            all_articles.append(art)

    # Deduplicate by title
    seen_titles: set[str] = set()
    unique: list[dict[str, Any]] = []
    for art in all_articles:
        title_key = art["title"].lower()[:60]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(art)

    # Sort by published date (newest first)
    def _sort_key(a: dict) -> str:
        return a.get("published", "unknown")

    unique.sort(key=_sort_key, reverse=True)
    return unique[:limit]


def fetch_ticker_news(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    """
    Fetch news specifically mentioning a stock ticker symbol.

    Uses yfinance's built-in news endpoint as primary source, falls back
    to RSS query on failure.

    Args:
        symbol: Stock ticker symbol (e.g. 'AAPL').
        limit: Maximum number of articles to return.

    Returns:
        List of article dicts: {title, summary, url, published, source}.
    """
    symbol_upper = symbol.upper().strip()
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol_upper)
        raw_news = ticker.news or []
        articles = []
        for item in raw_news[:limit]:
            content = item.get("content", {})
            title = _clean_text(content.get("title", item.get("title", "")), 200)
            summary = _clean_text(
                content.get("summary", item.get("summary", ""))
                or content.get("description", ""),
                500,
            )
            url = (
                content.get("canonicalUrl", {}).get("url", "")
                or item.get("link", "")
            )
            pub_time = item.get("providerPublishTime") or content.get("pubDate", "")
            if isinstance(pub_time, int):
                pub_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(pub_time))
            if title:
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "published": str(pub_time),
                    "source": "yfinance_news",
                })
        if articles:
            return articles
    except Exception:
        pass  # fall through to RSS fallback

    # Fallback: RSS query on ticker symbol
    return fetch_financial_news(query=symbol_upper, limit=limit)
