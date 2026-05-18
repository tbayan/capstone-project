"""
MCP client tools — CrewAI @tool wrappers that call the custom FastMCP server.

Each tool function:
  1. Calls the local MCP server via HTTP (streamable-http transport).
  2. Returns the result as a formatted string for agent consumption.
  3. Handles connection failures gracefully with a descriptive fallback message.

The MCP server must be running before these tools are called:
    python mcp_server/server.py
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import json
from typing import Any

import httpx
from crewai.tools import tool

from config.settings import MCP_SERVER_URL

# HTTP client with reasonable timeout — financial APIs can be slow
_client = httpx.Client(timeout=30.0)


def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Call a tool on the custom MCP server via HTTP POST.

    The MCP streamable-http transport exposes a /call-tool endpoint.
    """
    try:
        response = _client.post(
            f"{MCP_SERVER_URL}/call-tool",
            json={"name": tool_name, "arguments": arguments},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        # MCP response: {content: [{type: "text", text: "..."}]}
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            if isinstance(content, list) and content:
                raw = content[0].get("text", "")
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return {"result": raw}
        return data
    except httpx.ConnectError:
        return {
            "error": (
                f"MCP server is not reachable at {MCP_SERVER_URL}. "
                "Ensure 'python mcp_server/server.py' is running."
            )
        }
    except httpx.TimeoutException:
        return {"error": f"MCP server timed out calling tool '{tool_name}'."}
    except Exception as exc:
        return {"error": f"MCP call failed for '{tool_name}': {str(exc)}"}


def _format_dict(data: dict[str, Any], indent: int = 0) -> str:
    """Convert a dict to a readable key: value string for LLM consumption."""
    prefix = "  " * indent
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            lines.append(_format_dict(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{prefix}{k}: [{len(v)} items]")
        else:
            lines.append(f"{prefix}{k}: {v}")
    return "\n".join(lines)


# ── Tool 1: Stock price data ───────────────────────────────────────────────────

@tool("Get Stock Price Data")
def get_stock_data_tool(symbol: str, period: str = "3mo") -> str:
    """
    Fetch OHLCV price history for a stock ticker via the MCP financial data server.
    Use this to get current price, historical performance, and price change over time.

    Args:
        symbol: Stock ticker symbol (e.g. 'AAPL', 'NVDA', 'TSLA').
        period: Time period: '1d', '5d', '1mo', '3mo', '6mo', '1y'. Default '3mo'.

    Returns:
        Formatted string with latest price, price change %, and recent daily data.
    """
    result = _call_mcp_tool("get_stock_data", {"symbol": symbol, "period": period})

    if "error" in result:
        return f"Stock data unavailable for {symbol}: {result['error']}"

    records = result.get("records", [])
    latest = result.get("latest_close", "N/A")
    change = result.get("price_change_pct", "N/A")
    # Show last 5 records as context
    recent_str = "\n".join(
        f"  {r['date']}: Close=${r['close']}, Volume={r['volume']:,}"
        for r in records[-5:]
    ) if records else "  No recent records available."

    return (
        f"Stock Data for {result.get('symbol', symbol)} (period: {result.get('period', period)})\n"
        f"Latest Close: ${latest}\n"
        f"Price Change over period: {change}%\n"
        f"Recent price history (last 5 trading days):\n{recent_str}"
    )


# ── Tool 2: Company fundamentals ──────────────────────────────────────────────

@tool("Get Company Fundamentals")
def get_company_info_tool(symbol: str) -> str:
    """
    Fetch detailed company fundamentals and financial metrics via the MCP server.
    Use this to get P/E ratio, EPS, market cap, sector, analyst recommendations.

    Args:
        symbol: Stock ticker symbol (e.g. 'AAPL', 'JPM', 'GOOGL').

    Returns:
        Formatted string with company name, sector, valuation metrics, and analyst outlook.
    """
    result = _call_mcp_tool("get_company_info", {"symbol": symbol})

    if "error" in result:
        return f"Company info unavailable for {symbol}: {result['error']}"

    mktcap = result.get("market_cap")
    mktcap_str = f"${mktcap / 1e9:.1f}B" if mktcap else "N/A"

    return (
        f"Company Fundamentals: {result.get('company_name', symbol)} ({symbol})\n"
        f"Sector: {result.get('sector', 'N/A')} | Industry: {result.get('industry', 'N/A')}\n"
        f"Current Price: ${result.get('current_price', 'N/A')}\n"
        f"Market Cap: {mktcap_str}\n"
        f"Trailing P/E: {result.get('pe_ratio', 'N/A')} | Forward P/E: {result.get('forward_pe', 'N/A')}\n"
        f"EPS: ${result.get('eps', 'N/A')} | Beta: {result.get('beta', 'N/A')}\n"
        f"Price-to-Book: {result.get('price_to_book', 'N/A')}\n"
        f"Revenue Growth: {result.get('revenue_growth', 'N/A')} | Profit Margin: {result.get('profit_margin', 'N/A')}\n"
        f"52-Week High: ${result.get('week_52_high', 'N/A')} | Low: ${result.get('week_52_low', 'N/A')}\n"
        f"Dividend Yield: {result.get('dividend_yield', 'N/A')}\n"
        f"Analyst Recommendation: {result.get('recommendation', 'N/A')} | Target Price: ${result.get('analyst_target_price', 'N/A')}\n"
        f"Business: {result.get('description', 'N/A')[:300]}"
    )


# ── Tool 3: Market overview ────────────────────────────────────────────────────

@tool("Get Market Overview")
def get_market_overview_tool() -> str:
    """
    Fetch current macro market snapshot including S&P 500, NASDAQ-100,
    Dow Jones, and the VIX volatility index via the MCP server.
    Use this to understand the current macro environment before analysis.

    Returns:
        Formatted string with current prices and day-change for major indices.
    """
    result = _call_mcp_tool("get_market_overview", {})

    if "error" in result:
        return f"Market overview unavailable: {result['error']}"

    indices = result.get("indices", {})
    lines = ["Market Overview (Major Indices):"]
    for sym, data in indices.items():
        if "error" in data:
            lines.append(f"  {sym}: unavailable")
        else:
            price = data.get("price", "N/A")
            chg = data.get("change_pct", "N/A")
            label = data.get("label", sym)
            direction = "▲" if isinstance(chg, (int, float)) and chg > 0 else "▼"
            lines.append(f"  {label} ({sym}): ${price}  {direction} {chg}% today")
    return "\n".join(lines)


# ── Tool 4: Financial news search ─────────────────────────────────────────────

@tool("Search Financial News")
def search_news_tool(query: str) -> str:
    """
    Search and retrieve recent financial news articles related to a keyword or ticker.
    Use this to find current news, sentiment, and recent events affecting a stock.

    Args:
        query: A keyword, ticker symbol, or topic to search (e.g. 'NVDA earnings',
               'Federal Reserve rate decision', 'banking sector outlook').

    Returns:
        Formatted string listing recent news articles with titles and summaries.
    """
    result = _call_mcp_tool("search_financial_news", {"query": query, "limit": 8})

    if isinstance(result, dict) and "error" in result:
        return f"News search failed for '{query}': {result['error']}"

    articles = result if isinstance(result, list) else result.get("result", [])

    if not articles:
        return f"No recent news found for '{query}'. Market may be closed or query too specific."

    lines = [f"Financial News for '{query}' ({len(articles)} articles found):"]
    for i, art in enumerate(articles[:8], 1):
        lines.append(
            f"\n[{i}] {art.get('title', 'No title')}\n"
            f"    Published: {art.get('published', 'N/A')}\n"
            f"    Summary: {art.get('summary', 'N/A')[:200]}\n"
            f"    URL: {art.get('url', 'N/A')}"
        )
    return "\n".join(lines)


# ── Tool 5: Ticker-specific news ──────────────────────────────────────────────

@tool("Get Ticker News")
def get_ticker_news_tool(symbol: str) -> str:
    """
    Get recent news articles specifically about a stock ticker symbol.
    Prefers the ticker's own news feed over generic RSS.

    Args:
        symbol: Stock ticker symbol (e.g. 'AAPL', 'GOOGL', 'TSLA').

    Returns:
        Formatted list of recent news headlines and summaries for the ticker.
    """
    result = _call_mcp_tool("get_ticker_news", {"symbol": symbol, "limit": 8})

    if isinstance(result, dict) and "error" in result:
        return f"Ticker news unavailable for {symbol}: {result['error']}"

    articles = result if isinstance(result, list) else result.get("result", [])

    if not articles:
        return f"No recent news found for {symbol}."

    lines = [f"Recent News for {symbol.upper()} ({len(articles)} articles):"]
    for i, art in enumerate(articles[:8], 1):
        lines.append(
            f"\n[{i}] {art.get('title', 'No title')}\n"
            f"    Published: {art.get('published', 'N/A')}\n"
            f"    Summary: {art.get('summary', 'N/A')[:200]}"
        )
    return "\n".join(lines)
