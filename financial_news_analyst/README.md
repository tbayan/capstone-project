# Financial News Analyst

A local, multi-agent AI system for investment research. Three specialised CrewAI agents — backed by a custom MCP server, a RAG knowledge base, and a local Ollama LLM — collaborate to produce structured investment analysis reports.

**All processing is local. No API keys. No data egress.**

---

## Architecture at a Glance

```
User → Streamlit UI → Security Layer → CrewAI Orchestrator
                                              │
                    ┌─────────────────────────┼───────────────────────────┐
                    ▼                         ▼                           ▼
             Data Agent                  News Agent              Analysis Agent
          (Market data via MCP)     (News via MCP)          (RAG + Synthesis)
                    │                         │                           │
                    └─────────────────────────┴───────────────────────────┘
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                       ▼
                 Custom MCP Server                        ChromaDB RAG
                 (FastMCP, port 8000)                    (nomic-embed-text)
                 yfinance + RSS feeds
                          │
                          ▼
                 Ollama (qwen2.5:7b)
                 localhost:11434
```

---

## Prerequisites

1. **Python 3.11+**
2. **Ollama** — [install from ollama.ai](https://ollama.ai)
3. **GPU** — dual 4090 recommended; any NVIDIA GPU with 8GB+ VRAM works

---

## Setup

### 1. Pull Ollama models

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 2. Create virtual environment and install dependencies

```bash
cd financial_news_analyst
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env to change demo password, model names, or MCP port
```

### 4. Build the RAG knowledge base (run once)

```bash
python rag/seed_data.py     # downloads financial data and creates seed documents
python rag/indexer.py       # embeds documents and stores in ChromaDB
```

This takes ~5 minutes on first run (embedding 10 company summaries + reference guides + news).

---

## Running the System

You need **two terminals**:

### Terminal 1 — Start the MCP server

```bash
source .venv/bin/activate
python mcp_server/server.py
```

Expected output:
```
[MCP] Starting FinancialDataServer on port 8000 ...
```

### Terminal 2 — Start the Streamlit UI

```bash
source .venv/bin/activate
streamlit run ui/app.py
```

Open your browser at `http://localhost:8501`. Default demo password: `capstone2026`

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

**Test categories**:

| File | What it tests | Requires live services? |
|------|--------------|------------------------|
| `test_security.py` | Input validation, rate limiting, guardrails | No |
| `test_mcp_server.py` | MCP tool functions (direct call) | No (uses yfinance directly) |
| `test_rag.py` | Retrieval quality, indexer | No (needs RAG index built) |
| `test_agents.py` | LLM behaviour, adversarial prompts | Partial (security tests: No; full agent tests: Yes) |

Run only the fast tests (no live services needed):
```bash
pytest tests/test_security.py tests/test_mcp_server.py -v
```

Run all tests including live agent tests (requires MCP server + Ollama running):
```bash
pytest tests/ -v
```

---

## Project Structure

```
financial_news_analyst/
├── mcp_server/
│   ├── server.py                 ← Custom FastMCP server (YOUR MCP server)
│   └── tools/
│       ├── market_data.py        ← yfinance wrappers
│       └── news_fetcher.py       ← RSS financial news scraper
├── rag/
│   ├── seed_data.py              ← One-time knowledge base builder
│   ├── indexer.py                ← ChromaDB indexing pipeline
│   ├── retriever.py              ← Similarity search
│   └── chroma_db/                ← Persisted vector store (auto-created)
├── agents/
│   ├── data_agent.py             ← Agent 1: Financial Data Specialist
│   ├── news_agent.py             ← Agent 2: Financial News Analyst
│   ├── analysis_agent.py         ← Agent 3: Senior Investment Analyst
│   └── tools/
│       ├── mcp_client_tools.py   ← CrewAI tools calling MCP server via HTTP
│       └── rag_tools.py          ← CrewAI tool for RAG retrieval
├── orchestrator/
│   └── crew.py                   ← CrewAI Crew + Task chaining
├── observability/
│   └── logger.py                 ← Structured logging + SQLite audit trail
├── security/
│   └── validators.py             ← Input validation, rate limiting, guardrails
├── ui/
│   └── app.py                    ← Streamlit dashboard
├── tests/
│   ├── conftest.py
│   ├── test_mcp_server.py        ← MCP tool tests
│   ├── test_rag.py               ← RAG pipeline tests
│   ├── test_agents.py            ← LLM behaviour tests (positive + adversarial)
│   └── test_security.py          ← Security layer tests
├── docs/
│   ├── architecture_blueprint.md ← Full system design document
│   └── executive_summary.md      ← 1-page project overview
├── config/settings.py            ← Central configuration
├── requirements.txt
└── .env.example
```

---

## Deliverables

| Deliverable | Location |
|-------------|----------|
| Architecture Blueprint | `docs/architecture_blueprint.md` |
| Executive Summary | `docs/executive_summary.md` |
| Code Repository | This directory |
| Test Suite | `tests/` |
| Video Demo | Record separately (see below) |

---

## Recording the Video Demo

Suggested flow for your 2–5 minute demo:

1. Show both terminals running (MCP server + Streamlit)
2. Log in and enter a ticker (`NVDA`) and question (`Is this a good time to invest given AI spending trends?`)
3. Narrate each agent step as it progresses
4. Show the final report — highlight the 7 sections
5. In a separate terminal, run `pytest tests/test_security.py -v` and show all tests passing
6. Show one adversarial test failing correctly (`test_prompt_injection_blocked`)
7. Briefly explain the architecture: MCP server → agents → RAG → report

---

## Configuration Reference

All settings are in `config/settings.py` and overridable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MODEL` | `ollama/qwen2.5:7b` | LLM for agents (switch to `qwen2.5:14b` for better quality) |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model for RAG |
| `MCP_SERVER_PORT` | `8000` | Port for the custom MCP server |
| `DEMO_PASSWORD` | `capstone2026` | Streamlit demo access password |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per session per hour |

---

## Disclaimer

This system is for **educational and demonstration purposes only**. It does not constitute financial advice. All investment decisions should be made with the guidance of a qualified financial advisor. Past patterns do not guarantee future results.
