"""
Custom FastMCP financial data server.

This is the project's own MCP server — built from scratch using the MCP Python SDK.
No third-party MCP servers are used.

Exposes four tools:
  - get_stock_data        : OHLCV price history (yfinance)
  - get_company_info      : Company fundamentals (yfinance)
  - get_market_overview   : Major index snapshot (yfinance)
  - search_financial_news : RSS-aggregated financial news

Run with:
    python mcp_server/server.py

Server starts at http://localhost:8000 (configurable via .env).
"""

import sys
import os

# Make root importable when server.py is run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

from mcp_server.tools.market_data import (
    fetch_stock_data,
    fetch_company_fundamentals,
    fetch_market_overview,
)
from mcp_server.tools.news_fetcher import fetch_financial_news, fetch_ticker_news
from config.settings import MCP_SERVER_PORT

# ── FastMCP server instance ────────────────────────────────────────────────────
mcp = FastMCP(
    name="FinancialDataServer",
    instructions=(
        "A financial data MCP server providing real-time market data, "
        "company fundamentals, and financial news via free public sources. "
        "Built for the Financial News Analyst capstone project."
    ),
    port=MCP_SERVER_PORT,
    host="127.0.0.1",
)


# ── Tool: Stock price history ──────────────────────────────────────────────────

@mcp.tool()
def get_stock_data(symbol: str, period: str = "1y") -> dict[str, Any]:
    """
    Fetch OHLCV (open/high/low/close/volume) price history for a stock ticker.

    Args:
        symbol: Stock ticker symbol, e.g. 'AAPL', 'MSFT', 'NVDA'.
        period: Time period for history. Valid values: '1d', '5d', '1mo', '3mo',
                '6mo', '1y', '2y', '5y'. Default is '1y'.

    Returns:
        Dictionary with symbol, period, latest_close price, price_change_pct
        over the period, and up to 30 daily OHLCV records.
    """
    return fetch_stock_data(symbol, period)


# ── Tool: Company fundamentals ─────────────────────────────────────────────────

@mcp.tool()
def get_company_info(symbol: str) -> dict[str, Any]:
    """
    Fetch company fundamentals and key financial metrics for a stock ticker.

    Args:
        symbol: Stock ticker symbol, e.g. 'AAPL', 'TSLA', 'JPM'.

    Returns:
        Dictionary with company name, sector, market cap, P/E ratio, EPS,
        52-week high/low, dividend yield, analyst recommendation, and beta.
    """
    return fetch_company_fundamentals(symbol)


# ── Tool: Market overview ──────────────────────────────────────────────────────

@mcp.tool()
def get_market_overview() -> dict[str, Any]:
    """
    Fetch a macro market snapshot showing current prices and day-change
    for major indices: S&P 500 (SPY), NASDAQ-100 (QQQ), Dow Jones (DIA),
    and the Volatility Index (VIX).

    Returns:
        Dictionary with an 'indices' key mapping each symbol to its
        current price, previous close, and percentage change.
    """
    return fetch_market_overview()


# ── Tool: Financial news search ────────────────────────────────────────────────

@mcp.tool()
def search_financial_news(query: str = "", limit: int = 8) -> list[dict[str, Any]]:
    """
    Search and aggregate financial news from multiple free RSS feeds.

    Args:
        query: Keyword or ticker to filter news (e.g. 'NVDA', 'interest rates',
               'earnings beat'). Leave empty to get top general headlines.
        limit: Maximum number of articles to return (1–20). Default is 8.

    Returns:
        List of article dictionaries, each with: title, summary, url,
        published timestamp, and source feed URL.
    """
    limit = max(1, min(20, limit))  # clamp to 1-20
    return fetch_financial_news(query=query, limit=limit)


# ── Tool: Ticker-specific news ─────────────────────────────────────────────────

@mcp.tool()
def get_ticker_news(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    """
    Fetch recent news articles specifically about a stock ticker symbol.
    Uses yfinance's news endpoint as primary source with RSS fallback.

    Args:
        symbol: Stock ticker symbol, e.g. 'AAPL', 'GOOGL'.
        limit: Maximum number of articles to return (1–15). Default is 8.

    Returns:
        List of article dicts: {title, summary, url, published, source}.
    """
    limit = max(1, min(15, limit))
    return fetch_ticker_news(symbol=symbol, limit=limit)


# ── Entry point ────────────────────────────────────────────────────────────────

# Dispatch table: maps tool name -> callable
_TOOL_DISPATCH: dict[str, Any] = {
    "get_stock_data": fetch_stock_data,
    "get_company_info": fetch_company_fundamentals,
    "get_market_overview": fetch_market_overview,
    "search_financial_news": fetch_financial_news,
    "get_ticker_news": fetch_ticker_news,
}


async def call_tool_endpoint(request: Request) -> JSONResponse:
    """Simple /call-tool HTTP endpoint for CrewAI agent tools."""
    try:
        body = await request.json()
        name = body.get("name", "")
        arguments = body.get("arguments", {})
        if name not in _TOOL_DISPATCH:
            return JSONResponse({"error": f"Unknown tool: {name}"}, status_code=404)
        result = _TOOL_DISPATCH[name](**arguments)
        return JSONResponse({"content": [{"type": "text", "text": json.dumps(result)}]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


if __name__ == "__main__":
    print(f"[MCP] Starting FinancialDataServer on port {MCP_SERVER_PORT} ...")
    # Build a combined Starlette app: /call-tool for agents + /mcp for MCP protocol
    mcp_app = mcp.streamable_http_app()
    app = Starlette(routes=[
        Route("/call-tool", call_tool_endpoint, methods=["POST"]),
        Mount("/", app=mcp_app),
    ])
    uvicorn.run(app, host="127.0.0.1", port=MCP_SERVER_PORT, log_level="info")
