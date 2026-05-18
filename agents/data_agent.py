"""
Data Agent — fetches market data and company fundamentals via MCP tools.

Responsibilities:
  - Current stock price and price history
  - Company fundamentals (P/E, EPS, market cap, etc.)
  - Macro market overview (indices, VIX)
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crewai import Agent, LLM

from agents.tools.mcp_client_tools import (
    get_stock_data_tool,
    get_company_info_tool,
    get_market_overview_tool,
)
from config.settings import AGENT_MODEL, OLLAMA_BASE_URL


def create_data_agent() -> Agent:
    """
    Create and return the Data Agent.

    The Data Agent is a quantitative analyst specialising in pulling accurate,
    structured numerical data from financial markets. It calls the custom MCP
    server to retrieve live stock prices and company fundamentals.
    """
    llm = LLM(
        model=AGENT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,   # low temperature for factual data retrieval
        timeout=1800,
    )

    return Agent(
        role="Financial Data Specialist",
        goal=(
            "Fetch and present accurate, up-to-date market data and company fundamentals "
            "for the requested stock ticker. Include current price, key valuation metrics "
            "(P/E, EPS, market cap), price performance, analyst recommendations, and the "
            "current macro market environment."
        ),
        backstory=(
            "You are a quantitative analyst with 15 years of experience at a top-tier "
            "investment bank. You are trusted for your numerical precision and ability to "
            "rapidly gather and organise financial data from multiple sources. You always "
            "present data clearly and flag any missing or unreliable data points rather "
            "than guessing. You know that accurate data is the foundation of sound analysis."
        ),
        tools=[get_stock_data_tool, get_company_info_tool, get_market_overview_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,   # limit retries to keep response fast
    )
