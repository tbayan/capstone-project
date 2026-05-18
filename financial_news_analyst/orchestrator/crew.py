"""
CrewAI orchestrator — assembles the three agents into a sequential crew
and defines the tasks that chain their outputs.

Data Agent → News Agent → Analysis Agent

Usage:
    from orchestrator.crew import run_analysis
    report = run_analysis(ticker="NVDA", question="Is this a good time to invest?")
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from typing import Callable, Optional

from crewai import Crew, Task, Process

from agents.data_agent import create_data_agent
from agents.news_agent import create_news_agent
from agents.analysis_agent import create_analysis_agent
from config.settings import FINANCIAL_DISCLAIMER_TRIGGERS, DISCLAIMER_TEXT


# ── Task definitions ───────────────────────────────────────────────────────────

def _make_data_task(ticker: str, question: str, agent) -> Task:
    """Task for the Data Agent: gather market data and fundamentals."""
    return Task(
        description=(
            f"Fetch comprehensive financial data for the stock ticker: **{ticker}**\n\n"
            f"The user's investment question is: '{question}'\n\n"
            "Your task:\n"
            f"1. Use the 'Get Market Overview' tool to capture the current macro environment.\n"
            f"2. Use 'Get Stock Price Data' for {ticker} with period '3mo' to show recent performance.\n"
            f"3. Use 'Get Company Fundamentals' for {ticker} to retrieve valuation metrics.\n\n"
            "Present the data in a clear, structured format. Highlight any unusual metrics "
            "(e.g., very high/low P/E, extreme price movements, strong or weak analyst ratings). "
            "If a tool call fails, note it and continue with available data — do not fabricate numbers."
        ),
        expected_output=(
            "A structured data summary containing:\n"
            "- Current macro market snapshot (index prices and day changes)\n"
            f"- {ticker} price: latest close, 3-month price change percentage\n"
            f"- {ticker} fundamentals: company name, sector, market cap, P/E, EPS, "
            "52-week range, analyst recommendation, target price\n"
            "- Any notable data anomalies or missing data points flagged clearly"
        ),
        agent=agent,
    )


def _make_news_task(ticker: str, question: str, agent, data_task: Task) -> Task:
    """Task for the News Agent: gather and analyse news sentiment."""
    return Task(
        description=(
            f"Research recent financial news for **{ticker}** to support the investment question: "
            f"'{question}'\n\n"
            "Your task:\n"
            f"1. Use 'Get Ticker News' for {ticker} to fetch ticker-specific news.\n"
            f"2. Use 'Search Financial News' with a broader query like '{ticker} earnings outlook' "
            "to catch additional coverage.\n"
            "3. Synthesise the news into a sentiment assessment and key takeaways.\n\n"
            "Focus on: earnings reports, analyst upgrades/downgrades, product launches, "
            "regulatory news, macroeconomic events that affect this stock, and any pending catalysts. "
            "Be precise about dates — clearly note how recent each piece of news is. "
            "Do NOT invent or fabricate news stories."
        ),
        expected_output=(
            "A news analysis summary containing:\n"
            "- Overall sentiment: Bullish / Bearish / Neutral with brief justification\n"
            "- 3–5 most impactful recent headlines with dates and one-sentence summaries\n"
            "- Key upcoming catalysts (earnings date, product launches, regulatory decisions) if any\n"
            "- Notable risks or concerns raised in recent coverage\n"
            "- Sources cited for each major point"
        ),
        agent=agent,
        context=[data_task],  # receives data agent's output as context
    )


def _make_analysis_task(ticker: str, question: str, agent, data_task: Task, news_task: Task) -> Task:
    """Task for the Analysis Agent: synthesise and produce the final report."""
    return Task(
        description=(
            f"Produce a comprehensive investment analysis report for **{ticker}** "
            f"addressing the user's question: '{question}'\n\n"
            "You have access to:\n"
            "- Market data and fundamentals from the Data Agent (in context)\n"
            "- News sentiment and recent events from the News Agent (in context)\n"
            "- The financial knowledge base via the 'Retrieve Historical Financial Patterns' tool\n\n"
            "Your task:\n"
            "1. Use 'Retrieve Historical Financial Patterns' to find relevant frameworks "
            f"(e.g., search for '{ticker} valuation P/E sector comparison' and 'investment risk assessment').\n"
            "2. Synthesise all three information sources into the structured report below.\n"
            "3. Maintain intellectual honesty — if the data is mixed or uncertain, say so.\n"
            "4. Always end with the required disclaimer.\n\n"
            "IMPORTANT: This is an AI-generated analysis for educational purposes only."
        ),
        expected_output=(
            "A structured investment analysis report with these sections:\n\n"
            f"# Investment Analysis: {ticker}\n\n"
            "## 1. Executive Summary\n"
            "[2-3 sentence high-level conclusion]\n\n"
            "## 2. Market Data Summary\n"
            "[Key metrics table or structured list]\n\n"
            "## 3. News & Sentiment Analysis\n"
            "[Sentiment rating and key news findings]\n\n"
            "## 4. Historical Pattern Comparison\n"
            "[Retrieved knowledge base insights applied to current situation]\n\n"
            "## 5. Investment Thesis\n"
            "### Bull Case\n"
            "[3 positive factors]\n"
            "### Bear Case\n"
            "[3 risk factors]\n\n"
            "## 6. Risk Flags\n"
            "[Specific risks: valuation, execution, macro, sector]\n\n"
            "## 7. Conclusion & Outlook\n"
            "[Balanced conclusion with probability framing]\n\n"
            "⚠️ Disclaimer: This analysis is AI-generated for informational purposes only "
            "and does NOT constitute financial advice."
        ),
        agent=agent,
        context=[data_task, news_task],  # receives both prior agents' outputs
    )


# ── Crew assembly ──────────────────────────────────────────────────────────────

def _apply_guardrails(report: str) -> str:
    """
    Post-process the analysis report — add disclaimer if trigger phrases found.
    Part of the guardrails requirement from non-functional requirements.
    """
    report_lower = report.lower()
    for trigger in FINANCIAL_DISCLAIMER_TRIGGERS:
        if trigger.lower() in report_lower:
            if DISCLAIMER_TEXT not in report:
                report += DISCLAIMER_TEXT
            break
    # Always ensure disclaimer is present in the final output
    if "not financial advice" not in report.lower() and "not constitute financial advice" not in report.lower():
        report += DISCLAIMER_TEXT
    return report


def run_analysis(
    ticker: str,
    question: str,
    step_callback: Optional[Callable[[str, str], None]] = None,
) -> dict:
    """
    Run the full three-agent financial analysis crew.

    Args:
        ticker: Stock ticker symbol (already validated by security layer).
        question: User's investment question.
        step_callback: Optional callable(agent_role, output) called after each agent completes.
                       Used by the Streamlit UI to update progress in real-time.

    Returns:
        Dict with keys:
          - 'report': final analysis string
          - 'data_summary': Data Agent output
          - 'news_summary': News Agent output
          - 'elapsed_seconds': total execution time
          - 'ticker': ticker symbol
          - 'question': original question
    """
    start_time = time.time()

    # Create agents (fresh instances per request to avoid state leakage)
    data_agent = create_data_agent()
    news_agent = create_news_agent()
    analysis_agent = create_analysis_agent()

    # Create tasks
    data_task = _make_data_task(ticker, question, data_agent)
    news_task = _make_news_task(ticker, question, news_agent, data_task)
    analysis_task = _make_analysis_task(ticker, question, analysis_agent, data_task, news_task)

    # Assemble the crew
    crew = Crew(
        agents=[data_agent, news_agent, analysis_agent],
        tasks=[data_task, news_task, analysis_task],
        process=Process.sequential,   # Data → News → Analysis
        verbose=True,
    )

    # Execute
    crew_result = crew.kickoff(inputs={"ticker": ticker, "question": question})

    # Extract individual task outputs
    data_output = data_task.output.raw if data_task.output else "Data collection failed."
    news_output = news_task.output.raw if news_task.output else "News collection failed."
    final_report = crew_result.raw if hasattr(crew_result, "raw") else str(crew_result)

    # Apply security guardrails to final output
    final_report = _apply_guardrails(final_report)

    # Fire step callbacks if provided (for UI progress display)
    if step_callback:
        step_callback("Data Agent", data_output)
        step_callback("News Agent", news_output)
        step_callback("Analysis Agent", final_report)

    elapsed = round(time.time() - start_time, 2)

    return {
        "ticker": ticker.upper(),
        "question": question,
        "report": final_report,
        "data_summary": data_output,
        "news_summary": news_output,
        "elapsed_seconds": elapsed,
    }
