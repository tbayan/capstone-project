# Architecture Blueprint: Financial News Analyst

## System Overview

**Financial News Analyst** is a local, multi-agent AI system that provides investment analysis by combining live market data, real-time financial news, and a RAG-augmented knowledge base. The system is fully self-hosted — no data leaves the user's machine.

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **LLM** | Ollama + qwen3:8b | Local inference, fast on dual 4090 (~1-2s/step), no API costs, GDPR-safe |
| **Agent Framework** | CrewAI | Role-based agents with task chaining; clean abstraction over LangChain |
| **MCP Server** | FastMCP (custom-built) | Project-owned MCP server using the official MCP Python SDK; no third-party servers |
| **Vector Store** | ChromaDB | Lightweight, embedded, no infrastructure needed, persists to disk |
| **Embeddings** | nomic-embed-text (Ollama) | High-quality local embeddings, free, fast |
| **RAG Pipeline** | LangChain + ChromaDB | Industry-standard retrieval pipeline; supports metadata filtering |
| **Market Data** | yfinance | Free, reliable Yahoo Finance data; no API key required |
| **News** | RSS + yfinance News | Multiple free RSS feeds; no API key required |
| **UI** | Streamlit | Rapid development, clean UI, built-in session state |
| **Logging** | loguru + SQLite | Structured logs to file; queryable audit trail |
| **Testing** | pytest | Standard Python testing; positive + adversarial test suites |

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER (Browser)                                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTPS / localhost
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI (ui/app.py)                          │
│  - Input validation (security/validators.py)                             │
│  - Rate limiting (RateLimiter)                                           │
│  - Real-time agent progress display                                      │
│  - Rating widget → SQLite                                                │
│  - Report download (.txt)                                                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ validate_request()
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (orchestrator/crew.py)                    │
│                     CrewAI Sequential Process                            │
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│   │  DATA AGENT  │───▶│  NEWS AGENT  │───▶│    ANALYSIS AGENT        │  │
│   │              │    │              │    │                          │  │
│   │ Role: Quant  │    │ Role: News   │    │ Role: Senior Analyst     │  │
│   │ Analyst      │    │ Journalist   │    │                          │  │
│   │              │    │              │    │ Uses RAG to retrieve     │  │
│   │ Tools:       │    │ Tools:       │    │ historical patterns      │  │
│   │ - Stock data │    │ - News feed  │    │ then synthesises all     │  │
│   │ - Fundaments │    │ - Ticker news│    │ inputs into report       │  │
│   │ - Market OVW │    │              │    │                          │  │
│   └──────┬───────┘    └──────┬───────┘    └──────────┬───────────────┘  │
└──────────┼────────────────────┼────────────────────────┼────────────────┘
           │ HTTP               │ HTTP                   │
           ▼                    ▼                        ▼
┌──────────────────────┐                    ┌────────────────────────────┐
│  CUSTOM MCP SERVER   │                    │    RAG KNOWLEDGE BASE       │
│  (mcp_server/)       │                    │    (rag/)                   │
│                      │                    │                             │
│  FastMCP server      │                    │  ChromaDB vector store      │
│  Port 8000           │                    │  ~500+ document chunks      │
│                      │                    │                             │
│  Tools:              │                    │  Seeded with:               │
│  - get_stock_data    │                    │  - Fundamentals guides      │
│  - get_company_info  │                    │  - P/E interpretation       │
│  - get_market_ovw    │                    │  - Technical patterns       │
│  - search_news       │                    │  - Macro economic signals   │
│  - get_ticker_news   │                    │  - Sector rotation guide    │
│                      │                    │  - Earnings frameworks      │
│  Data Sources:       │                    │  - Risk management          │
│  - yfinance (free)   │                    │  - Company summaries        │
│  - RSS feeds (free)  │                    │  - Recent news (seeded)     │
└──────────────────────┘                    └────────────────────────────┘
           │                                           │
           ▼                                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      OLLAMA (Local LLM Server)                        │
│                      http://localhost:11434                           │
│                                                                       │
│   qwen2.5:7b      — Agent reasoning and synthesis (~1-2s/step)       │
│   nomic-embed-text — Document and query embedding for RAG             │
└──────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY (observability/logger.py)            │
│                                                                       │
│   logs/app.log   — Structured JSON logs (loguru)                     │
│   logs/audit.db  — SQLite: requests, agent steps, ratings, errors    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: End-to-End Request

1. User enters **ticker** (e.g., `NVDA`) and **question** in Streamlit UI
2. **Security layer** validates ticker format (regex), sanitises question (injection detection), checks rate limit
3. **Orchestrator** (`crew.py`) creates fresh agent instances and tasks, kicks off CrewAI sequential process
4. **Data Agent** calls MCP server tools → MCP server calls yfinance → returns structured market data
5. **News Agent** calls MCP server tools → MCP server scrapes RSS feeds + yfinance news → returns articles
6. **Analysis Agent** queries ChromaDB via RAG tool → retrieves relevant knowledge → synthesises report with guardrails
7. **Guardrails** check output for financial disclaimer compliance
8. **Observability** logs elapsed time, output sizes, token estimates to SQLite
9. Result returned to Streamlit UI → displayed with agent-by-agent breakdown
10. User rates the analysis → rating saved to audit DB

---

## Agent Roles and Responsibilities

### Agent 1: Financial Data Specialist (Data Agent)
- **Mandate**: Fetch accurate, structured numerical data only. Never fabricate numbers.
- **Tools**: `get_stock_data_tool`, `get_company_info_tool`, `get_market_overview_tool`
- **Output**: Structured data block: price history, fundamentals, macro snapshot
- **Temperature**: 0.1 (minimise hallucination for factual data tasks)

### Agent 2: Financial News Analyst (News Agent)
- **Mandate**: Find and interpret relevant news. Separate fact from speculation. Cite sources.
- **Tools**: `get_ticker_news_tool`, `search_news_tool`
- **Output**: Sentiment rating (Bullish/Bearish/Neutral) + top 3–5 headlines + upcoming catalysts
- **Temperature**: 0.3 (slight creativity for nuanced interpretation)

### Agent 3: Senior Investment Analyst (Analysis Agent)
- **Mandate**: Synthesise all inputs. Apply financial frameworks. Produce balanced, evidence-based report.
- **Tools**: `retrieve_historical_patterns` (RAG)
- **Output**: Full structured investment report (7 sections) with mandatory disclaimer
- **Temperature**: 0.4 (balanced synthesis and structured output)

---

## Custom MCP Server Design

The MCP server is built **from scratch** using the `mcp` Python SDK (FastMCP). It is:

- Owned and operated by this project — no third-party MCP servers
- Running on `http://localhost:8000` using streamable-http transport
- Exposes 5 tools: `get_stock_data`, `get_company_info`, `get_market_overview`, `search_financial_news`, `get_ticker_news`
- All data sources are **free** (yfinance, public RSS feeds) — no API keys
- Agents call the server via HTTP through `httpx` wrappers in `agents/tools/mcp_client_tools.py`

---

## RAG Pipeline Design

### Knowledge Base Composition
| Document Type | Count | Source |
|--------------|-------|--------|
| Financial analysis guides | 6 | Pre-written reference texts |
| Company fundamentals | 10 | yfinance (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, JPM, GS, BAC, META) |
| Recent news digest | 1 | Aggregated RSS feeds (50 articles) |

### Retrieval Configuration
- **Embedding model**: `nomic-embed-text` (768-dim, local via Ollama)
- **Chunk size**: 800 chars, 100 char overlap
- **Top-K**: 5 documents per query
- **Score threshold**: 0.4 (cosine similarity) — below-threshold results excluded
- **Collection name**: `financial_knowledge`

### Retrieval Quality Measures
- Source attribution in every retrieved chunk (filename + category + score)
- Score threshold prevents low-relevance noise from reaching the LLM
- Off-topic queries receive explicit "no relevant patterns found" message

---

## Security Architecture

| Control | Implementation | Addresses |
|---------|---------------|-----------|
| Input validation | Regex ticker validation (`^[A-Z^]{1,6}$`) | Injection, type confusion |
| Query sanitisation | HTML stripping + injection pattern matching | XSS, prompt injection |
| Rate limiting | In-memory per-session counter (10 req/hr) | Abuse, DoS |
| Output guardrails | Trigger phrase detection + mandatory disclaimer | Misleading output |
| Access control | Session password (env var) | Unauthorised access |
| Audit trail | SQLite with all requests logged | Accountability, debugging |

---

## Non-Functional Requirements Coverage

| Requirement | Implementation |
|-------------|---------------|
| LLM Tracing | loguru structured logs per agent step |
| Performance Metrics | elapsed_sec, output_len, token_est in SQLite |
| Error Tracking | error_events table in audit.db |
| User Feedback | Thumbs up/down → SQLite |
| Input Validation | security/validators.py |
| Content Filtering | apply_output_guardrails() |
| Rate Limiting | RateLimiter class per session |
| RAG Quality | Score threshold + source attribution |
| Hallucination Detection | RAG grounding + low-temperature LLM config |
| Source Attribution | Chunk metadata (filename, category, score) |
| Local-First | 100% local (Ollama + ChromaDB + SQLite) |
| Graceful Degradation | All MCP tools return error dicts, not exceptions |
| Audit Trail | Every request logged with full metadata |

---

## Limitations and Trade-offs

1. **No real-time streaming**: Agent outputs are collected thread-based, not streamed token-by-token. Chosen for simplicity; Streamlit doesn't natively support token streaming without SSE.

2. **In-memory rate limiting**: Resets on server restart. For production, replace with Redis.

3. **7B model limitations**: `qwen2.5:7b` is capable but may produce less nuanced analysis than larger models. Switchable to `qwen2.5:14b` in settings.py with no code changes.

4. **RSS feed reliability**: Public RSS feeds may go down or change structure. yfinance news endpoint is the primary fallback.

5. **Not financial advice**: This system is for educational/demonstration purposes. Investment decisions require licensed financial advisors and certified data sources.
