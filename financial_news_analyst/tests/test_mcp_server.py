"""
Tests for the custom MCP server tools (market_data and news_fetcher).

These tests call the tool functions directly (not via HTTP) to test the
underlying logic without requiring the MCP server to be running.

Positive tests: valid inputs return expected structure.
Negative tests: invalid inputs return error dicts, not exceptions.
"""

from __future__ import annotations

import pytest
from mcp_server.tools.market_data import (
    fetch_stock_data,
    fetch_company_fundamentals,
    fetch_market_overview,
)
from mcp_server.tools.news_fetcher import fetch_financial_news, fetch_ticker_news


# ═══════════════════════════════════════════════════════════════
#  POSITIVE TESTS — valid inputs
# ═══════════════════════════════════════════════════════════════

class TestFetchStockDataPositive:
    def test_returns_dict(self):
        result = fetch_stock_data("AAPL", "5d")
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = fetch_stock_data("AAPL", "5d")
        assert "symbol" in result
        assert "latest_close" in result
        assert "records" in result

    def test_symbol_is_uppercase(self):
        result = fetch_stock_data("aapl", "5d")   # lowercase input
        assert result.get("symbol") == "AAPL"

    def test_latest_close_is_positive(self):
        result = fetch_stock_data("MSFT", "1mo")
        close = result.get("latest_close")
        assert close is not None and close > 0

    def test_records_is_list(self):
        result = fetch_stock_data("NVDA", "1mo")
        records = result.get("records", [])
        assert isinstance(records, list)

    def test_record_has_ohlcv_keys(self):
        result = fetch_stock_data("GOOGL", "1mo")
        records = result.get("records", [])
        if records:
            r = records[0]
            for key in ("date", "open", "high", "low", "close", "volume"):
                assert key in r, f"Missing key '{key}' in record"

    def test_price_change_pct_is_numeric(self):
        result = fetch_stock_data("JPM", "3mo")
        chg = result.get("price_change_pct")
        assert chg is None or isinstance(chg, (int, float))


class TestFetchCompanyFundamentalsPositive:
    def test_returns_dict(self):
        result = fetch_company_fundamentals("AAPL")
        assert isinstance(result, dict)

    def test_has_company_name(self):
        result = fetch_company_fundamentals("AAPL")
        assert result.get("company_name") and "Apple" in result.get("company_name", "")

    def test_has_sector(self):
        result = fetch_company_fundamentals("MSFT")
        assert result.get("sector") is not None

    def test_market_cap_positive(self):
        result = fetch_company_fundamentals("NVDA")
        cap = result.get("market_cap")
        if cap is not None:
            assert cap > 0

    def test_description_is_string(self):
        result = fetch_company_fundamentals("GOOGL")
        desc = result.get("description", "")
        assert isinstance(desc, str)


class TestFetchMarketOverviewPositive:
    def test_returns_dict(self):
        result = fetch_market_overview()
        assert isinstance(result, dict)

    def test_has_indices_key(self):
        result = fetch_market_overview()
        assert "indices" in result

    def test_spy_present(self):
        result = fetch_market_overview()
        assert "SPY" in result.get("indices", {})

    def test_vix_present(self):
        result = fetch_market_overview()
        assert "^VIX" in result.get("indices", {})


class TestFetchNewsPositive:
    def test_returns_list(self):
        result = fetch_financial_news("", limit=5)
        assert isinstance(result, list)

    def test_respects_limit(self):
        result = fetch_financial_news("", limit=3)
        assert len(result) <= 3

    def test_article_has_title(self):
        result = fetch_financial_news("", limit=5)
        for art in result:
            assert "title" in art

    def test_no_html_in_title(self):
        """Titles should be stripped of HTML tags."""
        result = fetch_financial_news("", limit=5)
        for art in result:
            title = art.get("title", "")
            assert "<" not in title and ">" not in title


# ═══════════════════════════════════════════════════════════════
#  NEGATIVE TESTS — invalid/edge inputs
# ═══════════════════════════════════════════════════════════════

class TestFetchStockDataNegative:
    def test_invalid_ticker_returns_error_key(self):
        """A clearly invalid ticker should return an error dict, not raise."""
        result = fetch_stock_data("XXXXXXXXXX99", "5d")
        # Should either have 'error' key or empty records — never raise exception
        assert isinstance(result, dict)
        # If data comes back it's an error or empty
        assert "error" in result or result.get("records") == [] or result.get("latest_close") is None

    def test_empty_ticker_returns_error(self):
        result = fetch_stock_data("", "5d")
        assert isinstance(result, dict)
        assert "error" in result

    def test_does_not_raise_on_bad_period(self):
        """Bad period string should not crash — yfinance returns empty."""
        try:
            result = fetch_stock_data("AAPL", "99yrs")
            assert isinstance(result, dict)
        except Exception:
            pytest.fail("fetch_stock_data raised on bad period instead of returning error dict")


class TestFetchCompanyFundamentalsNegative:
    def test_invalid_ticker_returns_dict(self):
        result = fetch_company_fundamentals("XXXXXXXXXX99")
        assert isinstance(result, dict)

    def test_does_not_raise_on_empty_symbol(self):
        try:
            result = fetch_company_fundamentals("")
            assert isinstance(result, dict)
        except Exception:
            pytest.fail("fetch_company_fundamentals raised on empty symbol")


class TestFetchNewsNegative:
    def test_empty_query_returns_list(self):
        """Empty query should return general news, not error."""
        result = fetch_financial_news(query="", limit=3)
        assert isinstance(result, list)

    def test_limit_zero_returns_empty(self):
        result = fetch_financial_news(query="earnings", limit=0)
        # limit is clamped in the server layer; direct call returns []
        assert isinstance(result, list)
        assert len(result) == 0

    def test_very_specific_query_returns_list(self):
        """Extremely specific query may return empty but must not crash."""
        result = fetch_financial_news(query="xyzzy_impossible_query_string_12345", limit=5)
        assert isinstance(result, list)
