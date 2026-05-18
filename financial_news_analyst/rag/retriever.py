"""
RAG retriever — similarity search over the ChromaDB financial knowledge base.

Used by the Analysis Agent to retrieve relevant historical patterns,
financial analysis guides, and company fundamentals for a given query.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from langchain_chroma import Chroma

from config.settings import RAG_TOP_K, RAG_SCORE_THRESHOLD
from rag.indexer import get_vectorstore

# Module-level singleton — loaded once, reused across agent calls
_vectorstore: Optional[Chroma] = None


def _get_store() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


def retrieve(query: str, k: int = RAG_TOP_K, score_threshold: float = RAG_SCORE_THRESHOLD) -> str:
    """
    Retrieve relevant financial knowledge documents for a query.

    Args:
        query: Natural language query (e.g. "NVIDIA earnings momentum analysis").
        k: Number of top documents to retrieve.
        score_threshold: Minimum cosine similarity score (0–1). Documents below
                         this threshold are excluded to avoid noise.

    Returns:
        Formatted string of retrieved document excerpts with source attribution.
        Returns an empty-result message if nothing passes the threshold.
    """
    store = _get_store()

    results = store.similarity_search_with_relevance_scores(query, k=k)

    filtered = [
        (doc, score) for doc, score in results
        if score >= score_threshold
    ]

    if not filtered:
        return (
            "No highly relevant historical patterns found for this specific query. "
            "Proceed with the available market data and news context."
        )

    parts: list[str] = [
        f"[HISTORICAL REFERENCE FRAMEWORKS — {len(filtered)} document(s) retrieved. "
        f"These are analytical patterns and historical context ONLY. "
        f"Do NOT treat these as current prices, live news, or recent financial figures. "
        f"For current data, rely exclusively on the context from the Data Agent and News Agent.]\n"
    ]
    for i, (doc, score) in enumerate(filtered, 1):
        source = doc.metadata.get("filename", "unknown")
        category = doc.metadata.get("category", "reference")
        parts.append(
            f"--- Source {i}: {source} (category: {category}, relevance: {score:.2f}) ---\n"
            f"{doc.page_content.strip()}\n"
        )

    return "\n".join(parts)


def retrieve_with_metadata(query: str, k: int = RAG_TOP_K) -> list[dict]:
    """
    Retrieve documents with full metadata (for observability / source attribution UI).

    Returns:
        List of dicts: {content, source, category, score}.
    """
    store = _get_store()
    results = store.similarity_search_with_relevance_scores(query, k=k)
    return [
        {
            "content": doc.page_content.strip(),
            "source": doc.metadata.get("filename", "unknown"),
            "category": doc.metadata.get("category", "reference"),
            "score": round(score, 4),
        }
        for doc, score in results
    ]
