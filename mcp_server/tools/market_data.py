"""
Market data tools — yfinance wrappers exposed via the custom MCP server.

Each function is a pure Python helper; the MCP server registers them as tools.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from typing import Any
import yfinance as yf
from cachetools import TTLCache
import threading

# ── TTL cache — 5-minute freshness window ──────────────────────────────────────
# Prevents redundant yfinance API calls when the same ticker is queried multiple
# times within a short period (e.g. during the same crew run or rapid re-queries).
_cache: TTLCache = TTLCache(maxsize=128, ttl=300)   # 5 minutes
_cache_lock = threading.Lock()

from config.settings import DEFAULT_HISTORY_PERIOD

# Cryptocurrency ticker normalization — yfinance requires the "-USD" suffix for crypto assets.
# Users enter plain symbols (e.g. "BTC"); we map them to the correct yfinance format.
_CRYPTO_MAP: dict[str, str] = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
    "DOGE": "DOGE-USD", "ADA": "ADA-USD", "XRP": "XRP-USD",
    "BNB": "BNB-USD", "DOT": "DOT-USD", "AVAX": "AVAX-USD",
    "MATIC": "MATIC-USD", "LINK": "LINK-USD", "LTC": "LTC-USD",
    "UNI": "UNI-USD", "ATOM": "ATOM-USD", "NEAR": "NEAR-USD",
}


def _normalize_symbol(symbol: str) -> str:
    """Normalise a ticker symbol, mapping crypto abbreviations to yfinance format."""
    s = symbol.upper().strip()
    return _CRYPTO_MAP.get(s, s)


def fetch_stock_data(symbol: str, period: str = DEFAULT_HISTORY_PERIOD) -> dict[str, Any]:
    """
    Fetch OHLCV price history for a ticker.

    Args:
        symbol: Stock ticker symbol (e.g. 'AAPL').
        period: yfinance period string: '1d','5d','1mo','3mo','6mo','1y','2y','5y'.

    Returns:
        Dict with keys: symbol, period, records (list of daily OHLCV dicts),
        latest_close, price_change_pct.
    """
    symbol = _normalize_symbol(symbol)
    cache_key = f"stock_data:{symbol}:{period}"
    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
    except (ValueError, Exception) as exc:
        return {"symbol": symbol, "error": str(exc)}

    if hist.empty:
        return {"symbol": symbol, "error": f"No data found for ticker '{symbol}'"}

    records = []
    for date, row in hist.tail(30).iterrows():  # cap at 30 rows to keep payload small
        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })

    latest_close = records[-1]["close"] if records else None
    first_close = records[0]["open"] if records else None
    price_change_pct = None
    if latest_close and first_close and first_close != 0:
        price_change_pct = round(((latest_close - first_close) / first_close) * 100, 2)

    result = {
        "symbol": symbol,
        "period": period,
        "latest_close": latest_close,
        "price_change_pct": price_change_pct,
        "records": records,
    }
    with _cache_lock:
        _cache[cache_key] = result
    return result


def fetch_company_fundamentals(symbol: str) -> dict[str, Any]:
    """
    Fetch company fundamentals and key financial metrics.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with company name, sector, market cap, P/E ratio, EPS,
        52-week range, dividend yield, analyst target price.
    """
    symbol = _normalize_symbol(symbol)
    cache_key = f"fundamentals:{symbol}"
    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
    except (ValueError, Exception) as exc:
        return {"symbol": symbol, "error": str(exc)}

    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        return {"symbol": symbol, "error": f"No fundamental data found for '{symbol}'"}

    def _safe(key: str, default=None):
        val = info.get(key, default)
        # yfinance sometimes returns 'Infinity' or NaN; sanitise
        if val is not None:
            try:
                f = float(val)
                if f != f or f == float("inf") or f == float("-inf"):
                    return default
                return val
            except (TypeError, ValueError):
                return val
        return default

    fundamentals = {
        "symbol": symbol,
        "company_name": _safe("longName", symbol),
        "sector": _safe("sector", "N/A"),
        "industry": _safe("industry", "N/A"),
        "country": _safe("country", "N/A"),
        "market_cap": _safe("marketCap"),
        "current_price": _safe("currentPrice") or _safe("regularMarketPrice"),
        "pe_ratio": _safe("trailingPE"),
        "forward_pe": _safe("forwardPE"),
        "eps": _safe("trailingEps"),
        "price_to_book": _safe("priceToBook"),
        "revenue_growth": _safe("revenueGrowth"),
        "earnings_growth": _safe("earningsGrowth"),
        "profit_margin": _safe("profitMargins"),
        "week_52_high": _safe("fiftyTwoWeekHigh"),
        "week_52_low": _safe("fiftyTwoWeekLow"),
        "dividend_yield": _safe("dividendYield"),
        "analyst_target_price": _safe("targetMeanPrice"),
        "recommendation": _safe("recommendationKey", "N/A"),
        "beta": _safe("beta"),
        "description": (_safe("longBusinessSummary") or "")[:600],  # cap summary length
    }
    with _cache_lock:
        _cache[cache_key] = fundamentals
    return fundamentals


def fetch_market_overview() -> dict[str, Any]:
    """
    Fetch a macro snapshot: major indices and volatility index.

    Returns:
        Dict with current prices and day-change for SPY, QQQ, DIA, VIX.
    """
    symbols = {
        "SPY": "S&P 500 ETF",
        "QQQ": "NASDAQ-100 ETF",
        "DIA": "Dow Jones ETF",
        "^VIX": "Volatility Index",
    }
    overview: dict[str, Any] = {"indices": {}}

    for sym, label in symbols.items():
        try:
            t = yf.Ticker(sym)
            info = t.info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev = info.get("regularMarketPreviousClose")
            change_pct = None
            if price and prev and prev != 0:
                change_pct = round(((price - prev) / prev) * 100, 2)
            overview["indices"][sym] = {
                "label": label,
                "price": price,
                "previous_close": prev,
                "change_pct": change_pct,
            }
        except Exception as exc:
            overview["indices"][sym] = {"label": label, "error": str(exc)}

    return overview
