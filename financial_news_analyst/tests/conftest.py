"""
pytest conftest — shared fixtures for all test modules.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is importable from test files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(scope="session")
def valid_ticker():
    """A well-known ticker guaranteed to have data."""
    return "AAPL"


@pytest.fixture(scope="session")
def valid_question():
    return "What is the current investment outlook for this company?"


@pytest.fixture(scope="session")
def session_id():
    return "test_session_001"
