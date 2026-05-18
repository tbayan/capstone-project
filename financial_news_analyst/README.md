# Financial News Analyst

> Local multi-agent investment research system.  
> Three specialised AI agents — backed by a custom MCP server, a ChromaDB RAG knowledge base, and a local Ollama LLM — collaborate to produce structured, 7-section investment analysis reports.  
> **No API keys. No cloud calls. No data egress.**

---

## Architecture

```
Browser
  │
  ▼
Streamlit UI  (port 8501)
  │  security layer: input validation · rate limiting · output guardrails
  ▼
CrewAI Orchestrator  (sequential)
  │
  ├─▶ [01] Data Agent ─────▶ MCP Server (port 8000)
  │                               ├── yfinance  →  prices, fundamentals, macro
  │                               └── RSS feeds →  financial news
  ├─▶ [02] News Agent ─────▶ MCP Server
  │
  └─▶ [03] Analysis Agent ─▶ ChromaDB RAG (nomic-embed-text · 52 chunks)
                                  └── synthesises all inputs → 7-section report
  │
  ▼
Ollama (localhost:11434)
  ├── qwen2.5:7b        — agent reasoning and synthesis
  └── nomic-embed-text  — document and query embedding
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Agent orchestration | CrewAI (sequential process) |
| LLM | Ollama + qwen2.5:7b (local inference) |
| MCP server | FastMCP — custom-built, project-owned |
| Vector store | ChromaDB (embedded, persists to disk) |
| Embeddings | nomic-embed-text via Ollama |
| Market data | yfinance (free, no API key) |
| News | RSS feeds + yfinance News (free) |
| UI | Streamlit |
| Observability | loguru + SQLite audit trail |
| Security | Custom validators — input sanitisation, rate limiting, PII redaction |
| Testing | pytest — unit, integration, E2E, adversarial |

---

## Prerequisites

- **Python 3.11+**
- **Ollama** — [ollama.ai](https://ollama.ai)
- **GPU** — any NVIDIA with 8 GB+ VRAM (dual 4090 used in development)

---

## Setup

### 1. Pull models

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 2. Install dependencies

```bash
cd financial_news_analyst
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure (optional)

```bash
cp .env.example .env
# Override DEMO_PASSWORD, AGENT_MODEL, MCP_SERVER_PORT as needed
```

### 4. Build the RAG knowledge base (once)

```bash
python rag/seed_data.py    # fetches fundamentals and writes seed documents
python rag/indexer.py      # embeds and stores in ChromaDB (~5 min first run)
```

---

## Running

Two terminals required:

```bash
# Terminal 1 — MCP server
source .venv/bin/activate
python mcp_server/server.py
# → [MCP] Starting FinancialDataServer on port 8000 ...

# Terminal 2 — UI
source .venv/bin/activate
streamlit run ui/app.py
# → http://localhost:8501
```

Default access key: set `DEMO_PASSWORD` in `.env` (falls back to `capstone2026` if unset — change before sharing).

---

## Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

| Module | Scope | Live services needed |
|--------|-------|---------------------|
| `test_security.py` | Input validation, rate limiting, guardrails | No |
| `test_mcp_server.py` | All 5 MCP tools | No |
| `test_rag.py` | Retrieval quality, indexer | No (needs index built) |
| `test_agents.py` | Full pipeline, adversarial prompts | Yes (MCP + Ollama) |

Fast subset (no live services):

```bash
pytest tests/test_security.py tests/test_mcp_server.py -v
```

---

## Project Structure

```
financial_news_analyst/
├── agents/
│   ├── data_agent.py             — Agent 01: Financial Data Specialist
│   ├── news_agent.py             — Agent 02: Financial News Analyst
│   ├── analysis_agent.py         — Agent 03: Senior Investment Analyst
│   └── tools/
│       ├── mcp_client_tools.py   — HTTP wrappers calling the MCP server
│       └── rag_tools.py          — ChromaDB retrieval tool
├── mcp_server/
│   ├── server.py                 — Custom FastMCP server
│   └── tools/
│       ├── market_data.py        — yfinance wrappers (TTL-cached)
│       └── news_fetcher.py       — RSS + yfinance news scraper
├── orchestrator/
│   └── crew.py                   — CrewAI Crew + task chaining
├── rag/
│   ├── seed_data.py              — One-time knowledge base builder
│   ├── indexer.py                — ChromaDB indexing pipeline
│   ├── retriever.py              — Similarity search with score threshold
│   └── seed_docs/                — 17 financial reference documents
├── observability/
│   └── logger.py                 — loguru logs + SQLite audit trail
├── security/
│   └── validators.py             — Validation, rate limiting, PII redaction, guardrails
├── ui/
│   └── app.py                    — Streamlit dashboard
├── tests/
│   ├── conftest.py
│   ├── test_security.py
│   ├── test_mcp_server.py
│   ├── test_rag.py
│   └── test_agents.py
├── docs/
│   ├── architecture_blueprint.md
│   ├── executive_summary.md
│   ├── SELF_REVIEW.md
│   └── SYSTEM_OVERVIEW.md
├── config/settings.py
├── requirements.txt
└── .env.example
```

---

## Deliverables

| Deliverable | Location |
|-------------|----------|
| Architecture Blueprint | [docs/architecture_blueprint.md](docs/architecture_blueprint.md) |
| Executive Summary | [docs/executive_summary.md](docs/executive_summary.md) |
| Self-Review | [docs/SELF_REVIEW.md](docs/SELF_REVIEW.md) |
| Code | `agents/` · `mcp_server/` · `rag/` · `orchestrator/` · `ui/` |
| Test Suite | `tests/` |
| Video Demo | See submission file |

---

## Configuration

All settings live in `config/settings.py` and are overridable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MODEL` | `ollama/qwen2.5:7b` | LLM for agent reasoning |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model for RAG |
| `MCP_SERVER_PORT` | `8000` | Custom MCP server port |
| `DEMO_PASSWORD` | `capstone2026` | UI access key |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per session/hour |

---

## Disclaimer

For educational and research purposes only. This system does not constitute financial advice. All outputs are AI-generated estimates based on publicly available data. Investment decisions require qualified professional guidance.

