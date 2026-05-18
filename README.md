# Financial News Analyst

Repository: [github.com/tbayan/capstone-project](https://github.com/tbayan/capstone-project)

> A local, zero-egress multi-agent investment research system.  
> Three specialised AI agents — coordinated by CrewAI, backed by a custom MCP server, a ChromaDB RAG knowledge base, and a local Ollama LLM — collaborate to produce professional, narrative-style investment research notes.  
> **No API keys. No cloud calls. No data leaves the machine.**

---

## Deliverables

| Deliverable | File | Status |
|-------------|------|--------|
| Architecture Blueprint | [ARCHITECTURE_Blueprint.md](ARCHITECTURE_Blueprint.md) | ✅ Complete |
| Executive Summary | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | ✅ Complete |
| Self-Review | [SELF_REVIEW.md](SELF_REVIEW.md) | ✅ Complete |
| System Overview (bonus) | [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | ✅ Complete |
| Code Repository | this repo | ✅ Complete |
| Test Suite (96 tests) | [tests/](tests/) | ✅ Complete |
| README & Setup | [README.md](README.md) | ✅ Complete |
| Video Demo | Done, Link provided| ✅ Complete |

---

## What it does

A user enters a stock or crypto ticker and a research question (e.g. *"What are the key risk factors for NVDA heading into Q3?"*). The platform:

1. Fetches live market prices, valuation metrics, and macro data via a custom MCP server
2. Scrapes and summarises recent financial news from RSS feeds
3. Retrieves relevant analytical frameworks and historical patterns from a local RAG knowledge base
4. Synthesises all inputs into a professional, narrative-style research note using a local LLM
5. Displays a live candlestick chart, a rolling market ticker tape, and the full report in a dark-themed professional UI

---

## Architecture

```
Browser
  │
  ▼
Streamlit UI  (port 8501)
  │  ├─ SimplyWallSt-inspired dark theme
  │  ├─ Live market ticker tape (SPY, QQQ, NVDA, BTC, ETH …)
  │  ├─ Plotly candlestick charts (stocks + crypto)
  │  ├─ Security: input validation · rate limiting · output guardrails
  │  └─ Observability: loguru + SQLite audit trail · feedback rating
  ▼
CrewAI Orchestrator  (sequential process)
  │
  ├─▶ [01] Data Agent ──────────▶ MCP Server  :8000
  │     Financial Data Specialist   ├── market_data.py  →  yfinance prices, fundamentals, macro
  │                                 └── news_fetcher.py →  RSS + yfinance news
  ├─▶ [02] News Agent ──────────▶ MCP Server  :8000
  │     Financial News Analyst
  │
  └─▶ [03] Analysis Agent ──────▶ ChromaDB RAG
        Senior Investment Analyst    ├── nomic-embed-text (Ollama) — embedding
                                     ├── 17 seed documents · 52 indexed chunks
                                     └── retrieves top-5 by cosine similarity (threshold 0.4)
  │
  ▼
Ollama  (localhost:11434)
  ├── qwen3:8b            — all agents; think=False for data/news, think=True for analysis (~60s pipeline)
  └── nomic-embed-text   — document and query embedding (RAG only)
```

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Agent orchestration | **CrewAI 0.130** — sequential process | Agents share context via task outputs |
| LLM | **Ollama + qwen3:8b** | Local inference, ~60s full pipeline; think=True on Analysis Agent |
| Embeddings | **nomic-embed-text** via Ollama | Fixed at index build time — not swapped with LLM |
| MCP server | **FastMCP (mcp 1.9)** — custom-built, 5 tools | Owned entirely by this project |
| Vector store | **ChromaDB** — embedded, persists to disk | 17 docs → 52 chunks @ 800 tokens |
| Market data | **yfinance** — free, no API key | Prices, fundamentals, macro |
| News | **feedparser** + yfinance news — free | RSS: Yahoo Finance, MarketWatch, BBC, Reuters |
| UI | **Streamlit 1.45** | Dark SWS palette, Plotly charts, CSS ticker tape |
| Charts | **Plotly** — candlestick + volume + SMA-20 | Stocks and crypto (`{SYM}-USD`) |
| Observability | **loguru + SQLite** | Full audit trail, metrics summary, feedback ratings |
| Security | Custom `validators.py` | Input sanitisation, rate limiting, PII redaction, output guardrails |
| Testing | **pytest** — 4 modules, 78+ tests | Unit · integration · E2E · adversarial |

---

## Prerequisites

- **Python 3.11+**
- **Ollama** — [ollama.ai](https://ollama.ai)
- **NVIDIA GPU** — 8 GB+ VRAM (RTX 3080 class or higher); `qwen3:8b` fits in 5.2 GB

---

## Setup

### 1. Pull models

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure (optional)

```bash
cp .env.example .env
# Edit .env to override:
#   DEMO_PASSWORD   — access key shown on login screen (default: capstone2026)
#   AGENT_MODEL     — e.g. ollama_chat/qwen3:14b for a more powerful model
#   MCP_SERVER_PORT — default 8000
```

### 4. Build the RAG knowledge base (once)

```bash
python rag/seed_data.py   # fetches fundamentals, writes 17 seed documents to rag/seed_docs/
python rag/indexer.py     # embeds and stores in ChromaDB  (~3 min first run)
```

The index persists to `rag/chroma_db/`. Re-run `indexer.py --force` to rebuild after adding new documents.

---

## Running

Two terminals required:

```bash
# Terminal 1 — MCP server
source .venv/bin/activate
python mcp_server/server.py
# → [MCP] Starting FinancialDataServer on http://localhost:8000

# Terminal 2 — Streamlit UI
source .venv/bin/activate
streamlit run ui/app.py
# → http://localhost:8501
```

Log in with the access key set in `.env` (default: `capstone2026`).

---

## Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

| Module | Scope | Live services needed |
|--------|-------|---------------------|
| `test_security.py` | Input validation, rate limiting, PII redaction, guardrails | No |
| `test_mcp_server.py` | All 5 MCP tools (unit + integration) | No |
| `test_rag.py` | Retrieval quality, relevance scoring, indexer | No (needs index built) |
| `test_agents.py` | Full pipeline, adversarial prompts, hallucination guards | Yes (MCP + Ollama) |

Fast subset (no live services, ~10 s):

```bash
pytest tests/test_security.py tests/test_mcp_server.py -v
```

---

## Non-Functional Requirements

### Observability & Monitoring
- Every pipeline run is logged to SQLite with ticker, question, elapsed time, report text, and user feedback rating
- `get_metrics_summary()` surfaces aggregate stats (total runs, avg latency, feedback ratios) in the UI sidebar
- Loguru writes structured logs to `logs/app.log` with rotation
- CPU, RAM, and process memory displayed live in the sidebar

### Security & Safety
- `security/validators.py` sanitises all inputs: ticker format, query length, SQL injection, prompt injection, PII patterns
- Per-session rate limiter: 10 requests / session
- Output guardrails: reports checked for dangerous financial advice keywords before display
- Authentication gate on the Streamlit UI
- No credentials committed; `.env.example` provided

### RAG Quality
- Cosine similarity threshold (0.4) prevents low-relevance chunks from reaching the LLM
- Source attribution shown in the UI (file name, category, relevance score) for every retrieved chunk
- Analysis Agent prompt explicitly instructs the LLM to treat RAG output as *historical context only* and to use only real numbers from the Data/News agents
- `test_rag.py` verifies retrieval precision and recall against known queries

### Resource Efficiency
- yfinance data cached with TTL (60 s for ticker tape, 300 s for OHLCV charts)
- RAG index loaded once per process (module-level singleton)
- ChromaDB runs embedded — no separate server process
- MCP responses cached where applicable; all inference stays on-device

---

## Project Structure

```
├── agents/
│   ├── data_agent.py             — [01] Financial Data Specialist
│   ├── news_agent.py             — [02] Financial News Analyst
│   ├── analysis_agent.py         — [03] Senior Investment Analyst (RAG synthesis)
│   └── tools/
│       ├── mcp_client_tools.py   — HTTP wrappers calling the MCP server
│       └── rag_tools.py          — ChromaDB retrieval tool (CrewAI @tool)
├── mcp_server/
│   ├── server.py                 — Custom FastMCP server  :8000
│   └── tools/
│       ├── market_data.py        — yfinance wrappers (TTL-cached)
│       └── news_fetcher.py       — RSS + yfinance news scraper
├── orchestrator/
│   └── crew.py                   — CrewAI Crew + sequential task chain
├── rag/
│   ├── seed_data.py              — One-time knowledge base builder (17 docs)
│   ├── indexer.py                — ChromaDB indexing pipeline (nomic-embed-text)
│   ├── retriever.py              — Similarity search with score threshold
│   └── seed_docs/                — 17 financial reference documents
│       ├── fundamentals_*.txt    — Per-ticker fundamentals (10 tickers)
│       ├── earnings_analysis_framework.txt
│       ├── macro_economic_signals.txt
│       ├── pe_ratio_analysis.txt
│       ├── risk_management_framework.txt
│       ├── sector_rotation_guide.txt
│       ├── technical_analysis_patterns.txt
│       └── recent_news.txt
├── observability/
│   └── logger.py                 — loguru + SQLite audit trail + feedback ratings
├── security/
│   └── validators.py             — Validation, rate limiting, PII redaction, guardrails
├── ui/
│   └── app.py                    — Streamlit dashboard
│       ├── SimplyWallSt dark palette (#0d1220, teal #00c9a7)
│       ├── Rolling market ticker tape (live prices, CSS animation)
│       ├── Plotly candlestick charts (6 mo OHLCV + SMA-20 + volume)
│       ├── Narrative report renderer (prose, no bullet lists)
│       └── Auth gate · history panel · metrics sidebar · logout
├── tests/
│   ├── conftest.py
│   ├── test_security.py          — 25+ security & validation tests
│   ├── test_mcp_server.py        — MCP tool unit + integration tests
│   ├── test_rag.py               — Retrieval quality tests
│   └── test_agents.py            — End-to-end + adversarial pipeline tests
├── config/
│   └── settings.py               — Central configuration (all overridable via .env)
├── ARCHITECTURE_Blueprint.md      — Complete system design & technology rationale
├── EXECUTIVE_SUMMARY.md          — 1-2 page business overview
├── SYSTEM_OVERVIEW.md            — Technical system overview
├── SELF_REVIEW.md                — Architecture decisions & trade-offs
├── requirements.txt
└── .env.example
```

---

## Agent Design

### [01] Data Agent — Financial Data Specialist
Uses three MCP tools to fetch: live stock price + key metrics (`get_stock_data`), company fundamentals — P/E, EPS, market cap, debt ratios (`get_company_info`), and macro market overview — index performance, VIX, sector trends (`get_market_overview`). Temperature 0.1 (factual, minimal hallucination).

### [02] News Agent — Financial News Analyst
Uses two MCP tools: `search_news` (RSS feeds: Yahoo Finance, MarketWatch, BBC Business, Reuters) and `get_ticker_news` (yfinance news API). Extracts sentiment signals, identifies earnings events, analyst upgrades/downgrades, regulatory news. Temperature 0.2.

### [03] Analysis Agent — Senior Investment Analyst
Receives context from agents 01 and 02. Calls `retrieve_historical_patterns` (RAG tool) to pull relevant analytical frameworks. Synthesises everything into a prose research note structured as: Executive Summary → Market Snapshot → News & Sentiment → Historical Context → Investment Thesis → Key Risks → Outlook. Explicitly instructed to use only real numbers and never fabricate data. Temperature 0.4.

### MCP Server — Custom-built (5 tools)
| Tool | Function |
|------|----------|
| `get_stock_data` | Live price, 52-week range, volume, % change |
| `get_company_info` | P/E, EPS, market cap, beta, debt/equity, analyst rating |
| `get_market_overview` | SPY/QQQ/DXY performance, VIX, top gainers/losers |
| `search_news` | RSS feed scraper with keyword filtering |
| `get_ticker_news` | yfinance news API — ticker-specific headlines |

### RAG Knowledge Base
17 domain documents → 800-token chunks with 100-token overlap → 52 vectors indexed with `nomic-embed-text` → stored in ChromaDB. Retrieval: cosine similarity, top-5, score ≥ 0.4. Documents cover: per-ticker fundamentals (10 stocks), earnings analysis frameworks, macro signals, P/E methodology, risk management, sector rotation, technical patterns.

---

## UI Highlights

- **Dark theme** — SimplyWallSt-inspired palette: `#0d1220` background, `#00c9a7` teal accent, `#e05561` red, `#7b5ea7` purple
- **Ticker tape** — rolling CSS animation with live prices for SPY, QQQ, NVDA, AAPL, TSLA, BTC, ETH, GLD (pauses on hover)
- **Charts** — Plotly candlestick + volume + SMA-20, dark-themed, works for stocks and crypto
- **Narrative reports** — LLM output rendered as flowing prose paragraphs, not bullet lists
- **History** — sidebar shows last 6 analyses with colour-coded feedback dots, fully clickable
- **Auth + logout** — password gate, session-scoped rate limiter, logout button

---

## Configuration Reference

All settings live in `config/settings.py` and are fully overridable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_PASSWORD` | `capstone2026` | UI access key |
| `AGENT_MODEL` | `ollama_chat/qwen3:8b` | LLM for all agents |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model (RAG) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `MCP_SERVER_PORT` | `8000` | FastMCP server port |
| `RAG_TOP_K` | `5` | Documents retrieved per query |
| `RAG_SCORE_THRESHOLD` | `0.4` | Min cosine similarity |

---

*For educational purposes only. Not financial advice.*
