"""
Analysis Agent — synthesises market data, news, and RAG-retrieved patterns
to produce a structured investment insight report.

Responsibilities:
  - Retrieve relevant historical patterns and analysis frameworks from the RAG knowledge base
  - Combine quantitative data (from Data Agent) with qualitative news (from News Agent)
  - Produce a structured investment analysis with clear sections and a risk-adjusted conclusion
  - Apply appropriate disclaimers and flag potential biases
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crewai import Agent, LLM

from agents.tools.rag_tools import retrieve_historical_patterns
from config.settings import AGENT_MODEL, OLLAMA_BASE_URL


def create_analysis_agent() -> Agent:
    """
    Create and return the Analysis Agent.

    The Analysis Agent is a senior investment analyst who synthesises all available
    information — structured market data, news sentiment, and historical patterns
    retrieved from the RAG knowledge base — into a coherent, actionable report.
    """
    llm = LLM(
        model=AGENT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.4,   # balanced creativity for synthesis and structured output
        timeout=1800,
    )

    return Agent(
        role="Senior Investment Analyst",
        goal=(
            "Synthesise the market data and news analysis provided by your colleagues "
            "with relevant historical patterns from the financial knowledge base. Produce "
            "a structured investment analysis report with the following sections:\n"
            "1. Executive Summary (2-3 sentences)\n"
            "2. Market Data Summary (key metrics)\n"
            "3. News & Sentiment Analysis\n"
            "4. Historical Pattern Comparison (from RAG knowledge base)\n"
            "5. Investment Thesis (bull case and bear case)\n"
            "6. Risk Flags\n"
            "7. Conclusion & Outlook\n"
            "Always include a disclaimer that this is not financial advice."
        ),
        backstory=(
            "You are a veteran investment analyst with 20 years of experience at a "
            "leading hedge fund and later at a prominent equity research firm. You have "
            "covered both domestic and international markets across technology, financials, "
            "energy, and healthcare sectors. You are known for producing balanced, "
            "evidence-based reports that acknowledge both upside and downside scenarios. "
            "You always back your analysis with data and clearly separate facts from opinion. "
            "You are rigorous about citing the sources of your information and you never "
            "make absolute predictions — you deal in probabilities and scenarios. "
            "You understand that every investment carries risk and you always communicate "
            "that clearly to your readers."
        ),
        tools=[retrieve_historical_patterns],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=4,   # allow one extra iteration for thorough synthesis
    )
