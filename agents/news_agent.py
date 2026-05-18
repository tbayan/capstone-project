"""
News Agent — scrapes and summarises financial news via MCP tools.

Responsibilities:
  - Recent news headlines and summaries for a ticker
  - Sentiment signals from news (positive/negative/neutral)
  - Notable events: earnings announcements, regulatory news, analyst upgrades/downgrades
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crewai import Agent, LLM

from agents.tools.mcp_client_tools import (
    search_news_tool,
    get_ticker_news_tool,
)
from config.settings import AGENT_MODEL, OLLAMA_BASE_URL


def create_news_agent() -> Agent:
    """
    Create and return the News Agent.

    The News Agent is a financial journalist who monitors news feeds for signals
    that affect investment decisions. It identifies sentiment trends, breaking news,
    and key events that the market may have already reacted to or is about to react to.
    """
    llm = LLM(
        model=AGENT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,
        max_tokens=1100,       # sentiment + 3-5 headlines + catalysts fits in ~1k tokens
        timeout=1800,
        extra_body={"options": {"num_ctx": 6144}},  # news content + data context fits in 6k
    )

    return Agent(
        role="Financial News Analyst",
        goal=(
            "Find, read, and summarise the most relevant and recent financial news "
            "for the requested stock ticker. Identify the overall news sentiment "
            "(bullish / bearish / neutral), highlight the 3–5 most impactful headlines, "
            "and note any significant upcoming catalysts or risks mentioned in the news."
        ),
        backstory=(
            "You are a senior financial journalist with 12 years of experience covering "
            "Wall Street for a major financial publication. You have an exceptional ability "
            "to quickly scan dozens of headlines and separate signal from noise. You know "
            "which stories move markets and which are just background noise. You always "
            "cite your sources and note the publication date of the news you report on. "
            "You are careful to distinguish between confirmed facts and analyst speculation."
        ),
        tools=[get_ticker_news_tool, search_news_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,   # exactly 2 tool calls (ticker news + search) → 2 iterations sufficient
    )
