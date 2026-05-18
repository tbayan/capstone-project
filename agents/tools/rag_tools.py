"""
RAG tool — CrewAI @tool wrapper for the financial knowledge base retriever.

The Analysis Agent uses this to retrieve relevant historical patterns,
financial analysis guides, and company context from the ChromaDB vector store.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from crewai.tools import tool
from rag.retriever import retrieve


@tool("Retrieve Historical Financial Patterns")
def retrieve_historical_patterns(query: str) -> str:
    """
    Search the financial knowledge base for relevant historical patterns,
    analysis guides, sector context, and company fundamentals that match
    the current investment question.

    Use this tool to ground your analysis in proven financial frameworks
    and historical context before forming investment conclusions.

    Args:
        query: A specific financial question or topic to retrieve context for.
               Examples:
               - "NVIDIA P/E valuation context and semiconductor sector"
               - "interest rate impact on technology stocks"
               - "earnings beat interpretation and price reaction patterns"
               - "risk metrics for high-beta growth stocks"

    Returns:
        Relevant excerpts from the financial knowledge base with source attribution.
    """
    return retrieve(query)
