"""
Central configuration for the Financial News Analyst system.
All tunable constants live here — change once, applies everywhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Telemetry opt-out ──────────────────────────────────────────────────────────
# Disable OpenTelemetry OTLP span export (CrewAI ships with this enabled by
# default; without a local collector it floods logs with connection errors).
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "1")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DB_PATH = str(BASE_DIR / "rag" / "chroma_db")
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
AUDIT_DB_PATH = str(LOGS_DIR / "audit.db")
LOG_FILE_PATH = str(LOGS_DIR / "app.log")

# ── LLM (Ollama) ───────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# Main LLM for agents — qwen3:32b on dual 4090
AGENT_MODEL = os.getenv("AGENT_MODEL", "ollama_chat/qwen3:32b")
# Embedding model for RAG
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# ── MCP Server ─────────────────────────────────────────────────────────────────
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8000"))
MCP_SERVER_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"

# ── RAG ────────────────────────────────────────────────────────────────────────
RAG_CHUNK_SIZE = 800
RAG_CHUNK_OVERLAP = 100
RAG_TOP_K = 5
RAG_SCORE_THRESHOLD = 0.4   # minimum similarity score to include a result
RAG_COLLECTION_NAME = "financial_knowledge"

# ── Financial Data ─────────────────────────────────────────────────────────────
# Tickers used to seed the RAG knowledge base
SEED_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "GS", "BAC", "META"]
DEFAULT_HISTORY_PERIOD = "1y"   # yfinance period string

# Free financial RSS feeds (no API key required)
RSS_FEEDS = [
    "https://finance.yahoo.com/rss/",
    "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
]

# ── Security & Rate Limiting ───────────────────────────────────────────────────
MAX_TICKER_LENGTH = 5
MAX_QUERY_LENGTH = 500
RATE_LIMIT_REQUESTS = 10    # max requests per hour per session
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "capstone2026")

# ── Guardrails ─────────────────────────────────────────────────────────────────
# Phrases that trigger a forced disclaimer on agent output
FINANCIAL_DISCLAIMER_TRIGGERS = [
    "guaranteed return",
    "100% profit",
    "risk-free investment",
    "certain to rise",
    "definite profit",
]

DISCLAIMER_TEXT = (
    "\n\n⚠️ **Disclaimer**: This analysis is AI-generated and for informational "
    "purposes only. It does NOT constitute financial advice. Always consult a "
    "qualified financial advisor before making investment decisions."
)

# Prompt-injection patterns to block at input validation stage
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard previous",
    "act as",
    "you are now",
    "system prompt",
    "jailbreak",
    "dan mode",
]
