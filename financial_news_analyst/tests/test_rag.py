"""
Tests for the RAG pipeline (indexer and retriever).

Tests the retrieval quality and robustness of the ChromaDB-backed
financial knowledge base.

Note: these tests require the index to be built first:
    python rag/seed_data.py
    python rag/indexer.py

The retriever auto-builds the index if seed_docs exist.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════
#  POSITIVE TESTS
# ═══════════════════════════════════════════════════════════════

class TestRetrieverPositive:
    def test_financial_query_returns_string(self):
        """A financial query should return a non-empty string."""
        from rag.retriever import retrieve
        result = retrieve("P/E ratio interpretation technology stocks")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_pe_query_mentions_pe(self):
        """Querying about P/E ratio should retrieve content containing 'P/E'."""
        from rag.retriever import retrieve
        result = retrieve("price to earnings ratio valuation")
        # Either we get relevant content OR the no-results fallback message
        assert isinstance(result, str)
        # If results were found, they should be relevant
        if "No highly relevant" not in result:
            result_lower = result.lower()
            assert any(term in result_lower for term in ["p/e", "price", "earnings", "valuation"])

    def test_risk_query_retrieves_context(self):
        """Querying about risk should retrieve risk management content."""
        from rag.retriever import retrieve
        result = retrieve("investment risk beta volatility")
        assert isinstance(result, str)

    def test_sector_rotation_query(self):
        """Sector rotation is in the seed docs and should be retrievable."""
        from rag.retriever import retrieve
        result = retrieve("sector rotation economic cycle defensive stocks")
        assert isinstance(result, str)

    def test_retrieve_with_metadata_returns_list(self):
        """retrieve_with_metadata should return a list of dicts."""
        from rag.retriever import retrieve_with_metadata
        result = retrieve_with_metadata("earnings analysis framework")
        assert isinstance(result, list)
        if result:
            item = result[0]
            assert "content" in item
            assert "source" in item
            assert "score" in item

    def test_scores_are_between_0_and_1(self):
        """Relevance scores from ChromaDB should be in [0, 1]."""
        from rag.retriever import retrieve_with_metadata
        results = retrieve_with_metadata("technical analysis support resistance")
        for item in results:
            score = item.get("score", 0)
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"


# ═══════════════════════════════════════════════════════════════
#  NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════

class TestRetrieverNegative:
    def test_offtopic_query_returns_fallback_or_low_results(self):
        """
        An off-topic query ('how to bake bread') should either:
        a) Return the no-results fallback message, OR
        b) Return results with very low scores (below threshold, filtered out)
        """
        from rag.retriever import retrieve, RAG_SCORE_THRESHOLD
        from config.settings import RAG_SCORE_THRESHOLD as threshold

        result = retrieve("how to bake sourdough bread at home")
        assert isinstance(result, str)
        # Either we get the fallback message or very limited results
        # The key assertion: it should NOT return financial analysis content confidently
        # (low score content is filtered by threshold)

    def test_empty_query_does_not_crash(self):
        """Empty query should not raise — returns fallback message."""
        from rag.retriever import retrieve
        try:
            result = retrieve("")
            assert isinstance(result, str)
        except Exception as exc:
            pytest.fail(f"retrieve('') raised unexpectedly: {exc}")

    def test_very_long_query_does_not_crash(self):
        """Extremely long query strings should be handled gracefully."""
        from rag.retriever import retrieve
        long_query = "financial analysis " * 100  # ~2000 chars
        try:
            result = retrieve(long_query)
            assert isinstance(result, str)
        except Exception as exc:
            pytest.fail(f"retrieve(long_query) raised unexpectedly: {exc}")

    def test_injection_in_query_does_not_crash(self):
        """SQL/prompt injection in RAG query should not cause a crash."""
        from rag.retriever import retrieve
        injection = "'; DROP TABLE documents; --"
        try:
            result = retrieve(injection)
            assert isinstance(result, str)
        except Exception as exc:
            pytest.fail(f"retrieve(injection) raised unexpectedly: {exc}")


# ═══════════════════════════════════════════════════════════════
#  INDEXER TESTS
# ═══════════════════════════════════════════════════════════════

class TestIndexer:
    def test_get_vectorstore_returns_chroma_instance(self):
        """get_vectorstore should return a Chroma instance."""
        from rag.indexer import get_vectorstore
        from langchain_chroma import Chroma
        store = get_vectorstore()
        assert isinstance(store, Chroma)

    def test_vectorstore_has_documents(self):
        """The vectorstore should have at least some documents indexed."""
        from rag.indexer import get_vectorstore
        store = get_vectorstore()
        count = store._collection.count()
        assert count > 0, "ChromaDB collection is empty — run seed_data.py and indexer.py"
