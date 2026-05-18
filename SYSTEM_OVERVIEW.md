# Financial News Analyst — System Overview
> Updated: May 18, 2026 · Branch `main`

---

## The 10,000-foot view

```
User (Browser)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Streamlit UI  (port 8501)  ← auth, input, report view  │
└─────────────────────────────────────────────────────────┘
    │  run_analysis(ticker, question)
    ▼
┌─────────────────────────────────────────────────────────┐
│  CrewAI Orchestrator  (orchestrator/crew.py)            │
│                                                         │
│  Task 1         Task 2         Task 3                   │
│  Data Agent  →  News Agent  →  Analysis Agent           │
└─────────────────────────────────────────────────────────┘
    │                │                │
    ▼                ▼                ▼
┌──────────┐   ┌──────────┐   ┌──────────────────────┐
│  MCP     │   │  MCP     │   │  ChromaDB (RAG)       │
│  Server  │   │  Server  │   │  52 chunks            │
│ port 8000│   │ port 8000│   │  nomic-embed-text     │
└──────────┘   └──────────┘   └──────────────────────┘
    │                │
    ▼                ▼
┌──────────┐   ┌──────────────────────────────────────┐
│ yfinance │   │  RSS feeds (Yahoo, Reuters, BBC,     │
│  (live)  │   │  MarketWatch) via feedparser (live)  │
└──────────┘   └──────────────────────────────────────┘

         ↕ ALL LLM CALLS ↕
┌─────────────────────────────────────────────────────────┐
│  Ollama  (localhost:11434)                              │
│  • qwen3:8b         ← all 3 agents (think=False for data/news,          │
│                      think=True for analysis)                          │
│  • nomic-embed-text  ← RAG embeddings only                             │
└─────────────────────────────────────────────────────────┘
```

---

## What is Ollama and what's inside it?

**Ollama** is a local model server — think of it like Docker, but for LLMs. It downloads
models, manages GPU/CPU resources, and exposes a REST API at `http://localhost:11434`.

Three models are installed:

| Model | Size | Used for |
|---|---|---|
| `qwen3:8b` | 5.2 GB | All 3 agents (reasoning, text generation, CoT synthesis) |
| `nomic-embed-text` | 274 MB | RAG — converts text into 768-dim vectors |

**How `qwen3:8b` works:**
It is an 8-billion-parameter transformer model by Alibaba Cloud (Qwen3 architecture).
Quantized to ~4-bit precision so it fits in ~5.2 GB VRAM. It supports an optional
*thinking* mode (`think=True`) that emits chain-of-thought reasoning tokens before the
final answer — used on the Analysis Agent for deeper synthesis. Data and News agents
run with `think=False` for maximum speed (~109 tok/s). It runs entirely on your GPU —
no internet required.

**How `nomic-embed-text` works:**
A smaller model that converts any text string into a 768-dimensional float vector (an
"embedding"). Semantically similar texts get similar vectors. Used only during RAG
indexing and retrieval — never for text generation.

---

## The 3-Agent Pipeline — Step by Step

When you click **Run Analysis** for e.g. `NVDA`:

### Agent 1 — Data Agent (`agents/data_agent.py`)

```
Receives:  "Today is May 18, 2026. Fetch data for NVDA..."
Does:      calls MCP server 3 times:
              → POST /call-tool  {"tool": "get_market_overview"}
                   → SPY / QQQ / DIA / VIX live prices
              → POST /call-tool  {"tool": "get_stock_data", "symbol": "NVDA"}
                   → 30 days OHLCV from Yahoo Finance
              → POST /call-tool  {"tool": "get_company_fundamentals", "symbol": "NVDA"}
                   → market_cap: $5.4T, PE: 46, EPS: $4.89 ...
Outputs:   Structured data summary text (passed to Agent 2 & 3 as context)
```

### Agent 2 — News Agent (`agents/news_agent.py`)

```
Receives:  Data Agent output (as context) + "Fetch news for NVDA..."
Does:      calls MCP server 2 times:
              → POST /call-tool  {"tool": "get_ticker_news", "symbol": "NVDA"}
                   → yfinance .news → ~10 recent articles from Yahoo Finance
              → POST /call-tool  {"tool": "search_financial_news", "query": "NVDA earnings"}
                   → feedparser parses 5 RSS feeds → filters for keyword "NVDA"
Outputs:   Sentiment assessment + key headlines with real publication dates
```

### Agent 3 — Analysis Agent (`agents/analysis_agent.py`)

```
Receives:  Data Agent output + News Agent output (both in context)
Does:      calls RAG tool once:
              → query: "NVDA valuation semiconductor..."
              → nomic-embed-text embeds the query → 768-dim vector
              → ChromaDB cosine-similarity search → top 5 chunks above threshold 0.4
              → returns pe_ratio_analysis.txt, sector_rotation_guide.txt, etc.
Then:      qwen3:8b synthesises ALL of:
              - live market data    (from Agent 1)
              - live news           (from Agent 2)
              - historical frameworks (from RAG)
              - today's date        (injected into every task prompt)
Outputs:   7-section structured investment report
```

### CrewAI ReAct Loop (how each agent "thinks")

Each agent runs a ReAct (Reason + Act) loop internally:

```
1. LLM reads the task description
2. LLM decides which tool to call  → "Thought: I need stock data. Action: Get Stock Price Data"
3. Tool executes, result appended to conversation
4. LLM reads the tool result       → "Observation: latest_close = 221.33"
5. LLM decides next action or finishes
6. Final output passed as context to the next agent
```

Max iterations: Data Agent 3 · News Agent 2 · Analysis Agent 3 (configurable in agent definitions).

---

## The MCP Server — What is it really?

**MCP = Model Context Protocol** — a standard for LLMs to call external tools.
The server (`mcp_server/server.py`) is a FastMCP/Starlette REST API on port 8000.

```
Agent calls tool →  POST http://127.0.0.1:8000/call-tool
                    {"tool": "get_stock_data", "symbol": "AAPL", "period": "3mo"}
                         ↓
                    _TOOL_DISPATCH["get_stock_data"]("AAPL", "3mo")
                         ↓
                    _normalize_symbol("AAPL") → "AAPL"   (BTC → BTC-USD for crypto)
                         ↓
                    yf.Ticker("AAPL").history(period="3mo")
                         ↓
                    returns {"latest_close": 297.02, "price_change_pct": ..., "records": [...]}
```

The 5 tools and their data sources:

| Tool | Source | Data freshness |
|---|---|---|
| `get_stock_data` | `yfinance` → Yahoo Finance API | Real-time (15-min delay) |
| `get_company_fundamentals` | `yfinance` → Yahoo Finance API | Daily |
| `get_market_overview` | `yfinance` → SPY/QQQ/DIA/VIX | Real-time |
| `search_financial_news` | `feedparser` → RSS feeds; word-level + ticker-alias matching | Live (minutes old) |
| `get_ticker_news` | `yfinance` → Yahoo Finance news | Hours old |

**Crypto tickers** are normalised automatically:
`BTC → BTC-USD`, `ETH → ETH-USD`, `SOL → SOL-USD`, etc.

**Sample live prices (May 18, 2026):**
- NVDA: $221.33 · market cap $5.36T · P/E 45.3×
- AAPL: $297.02 · market cap $4.36T · P/E 36.0×
- MSFT: $419.73 · market cap $3.12T · P/E 25.0×
- BTC:  ~$76,939 (via BTC-USD)

---

## The RAG Knowledge Base — What's in it?

**RAG = Retrieval-Augmented Generation.** Instead of trusting the LLM's (possibly stale)
training data for analytical frameworks, a knowledge base is pre-loaded and relevant
chunks are retrieved at query time.

**ChromaDB index:** 52 chunks · 17 source documents · stored at `rag/chroma_db/`

| Category | Files | Purpose |
|---|---|---|
| `reference_guide` (×6) | `pe_ratio_analysis.txt`, `earnings_analysis_framework.txt`, `risk_management_framework.txt`, `sector_rotation_guide.txt`, `macro_economic_signals.txt`, `technical_analysis_patterns.txt` | Analytical frameworks the LLM uses to interpret numbers |
| `company_fundamental` (×10) | `fundamentals_AAPL/NVDA/MSFT/GOOGL/AMZN/META/TSLA/JPM/GS/BAC.txt` | Company snapshots auto-generated from live yfinance data |
| `news` (×1) | `recent_news.txt` | 50 live news headlines seeded at index-build time |

**How a retrieval works:**

```
query: "NVDA semiconductor valuation"
   ↓
nomic-embed-text  →  [0.12, -0.44, 0.87, ... 768 dimensions]
   ↓
ChromaDB cosine similarity vs all 52 stored chunk vectors
   ↓
top 5 matches above threshold 0.40:
   pe_ratio_analysis.txt     (score: 0.51)  ← how to interpret P/E ratios
   fundamentals_NVDA.txt     (score: 0.47)  ← NVDA company snapshot
   sector_rotation_guide.txt (score: 0.43)  ← tech sector context
```

Retrieved documents are **labelled as historical reference frameworks** so the Analysis
Agent does not treat them as current prices or live news.

---

## Security Layer (`security/validators.py`)

| Control | Detail |
|---|---|
| Auth gate | Password required (`DEMO_PASSWORD` in settings) |
| Ticker validation | Regex `^[A-Z\^]{1,6}$` — blocks injection, scripts |
| Question sanitisation | Strip HTML, length cap 500 chars |
| Prompt injection detection | Blocks "ignore previous instructions", "system:", etc. |
| Rate limiting | 10 requests per session |

---

## Observability (`observability/logger.py` → `logs/audit.db`)

Every request is persisted to SQLite with:
- `timestamp`, `ticker`, `question`
- `elapsed_sec`, `report_len`, `token_est`
- `report` (full text, stored since commit `a5be7c9`)
- `rating` (thumbs up/down, set by user after reading)

Additional tables: `agent_steps` (per-agent timing) and `error_events`.

The Streamlit sidebar shows live metrics: total runs, average elapsed time, rating counts,
and a clickable 5-item history list that loads the full stored report without leaving the
current analysis.

---

## Codebase at a Glance

```
financial_news_analyst/
├── agents/
│   ├── data_agent.py          # Data Agent definition + LLM config
│   ├── news_agent.py          # News Agent definition + LLM config
│   ├── analysis_agent.py      # Analysis Agent definition + LLM config
│   └── tools/
│       ├── mcp_client_tools.py  # CrewAI @tool wrappers calling MCP server
│       └── rag_tools.py         # CrewAI @tool wrapper calling ChromaDB
├── config/
│   └── settings.py            # All constants — model names, paths, thresholds
├── mcp_server/
│   ├── server.py              # FastMCP + Starlette server (port 8000)
│   └── tools/
│       ├── market_data.py     # yfinance wrappers (incl. crypto normalisation)
│       └── news_fetcher.py    # feedparser RSS aggregator
├── observability/
│   └── logger.py              # loguru + SQLite audit log
├── orchestrator/
│   └── crew.py                # Task definitions + Crew assembly + run_analysis()
├── rag/
│   ├── indexer.py             # Build / load ChromaDB index
│   ├── retriever.py           # Similarity search + metadata retrieval
│   ├── seed_data.py           # Script to generate seed documents
│   └── seed_docs/             # 17 source .txt files
├── security/
│   └── validators.py          # Input validation, rate limiting, injection detection
├── tests/
│   ├── test_agents.py         # Agent integration tests (95/96 pass)
│   ├── test_mcp_server.py     # MCP server tests (28/28 pass)
│   ├── test_rag.py            # RAG tests (12/12 pass)
│   └── test_security.py       # Security tests (38/38 pass)
├── ui/
│   └── app.py                 # Streamlit UI (port 8501)
└── docs/
    ├── architecture_blueprint.md
    ├── executive_summary.md
    └── SYSTEM_OVERVIEW.md     ← this file
```

**Total: ~3,700 lines of Python across 32 source files**

---

## Deliverable Status (May 18, 2026)

| Requirement | Status | Notes |
|---|---|---|
| 3+ agents in pipeline | ✅ | Data → News → Analysis |
| Custom MCP server | ✅ | 5 tools, port 8000, FastMCP |
| RAG pipeline | ✅ | ChromaDB, 52 chunks, nomic-embed-text |
| Security / guardrails | ✅ | Rate limit, injection detection, auth |
| Observability | ✅ | SQLite audit log, metrics, ratings |
| Test suite (positive + negative + edge) | ✅ | 95/96 pass |
| Streamlit UI | ✅ | Auth, history, RAG sources panel |
| Local LLM only — no cloud API | ✅ | Ollama qwen3:8b throughout |
| Crypto ticker support | ✅ | BTC/ETH/SOL auto-normalised |
| Current date injected into prompts | ✅ | All three task descriptions |
| Report stored + history clickable | ✅ | Since commit `a5be7c9` |
