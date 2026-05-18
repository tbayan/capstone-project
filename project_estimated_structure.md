financial_news_analyst/
├── mcp_server/
│   ├── server.py                  ← FastMCP server (runs on port 8000)
│   └── tools/
│       ├── market_data.py         ← yfinance wrappers
│       └── news_fetcher.py        ← RSS feed scrapers
├── rag/
│   ├── indexer.py                 ← Embed + store docs in ChromaDB
│   ├── retriever.py               ← Similarity search helper
│   ├── seed_data.py               ← Downloads/creates seed financial docs
│   └── chroma_db/                 ← Persisted vector store (gitignored)
├── agents/
│   ├── data_agent.py
│   ├── news_agent.py
│   ├── analysis_agent.py
│   └── tools/
│       ├── mcp_client_tools.py    ← CrewAI @tool wrappers calling MCP server
│       └── rag_tools.py           ← CrewAI @tool wrapper for RAG retrieval
├── orchestrator/
│   └── crew.py                    ← CrewAI Crew + Task definitions
├── observability/
│   └── logger.py                  ← Structured logging, metrics, audit trail
├── security/
│   └── validators.py              ← Input sanitization, rate limiting, guardrails
├── ui/
│   └── app.py                     ← Streamlit app
├── tests/
│   ├── conftest.py
│   ├── test_mcp_server.py
│   ├── test_rag.py
│   ├── test_agents.py
│   └── test_security.py
├── docs/
│   ├── architecture_blueprint.md  ← Deliverable
│   └── executive_summary.md       ← Deliverable
├── config/settings.py
├── README.md
└── requirements.txt