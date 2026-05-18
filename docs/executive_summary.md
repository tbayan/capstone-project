# Executive Summary: Financial News Analyst

**Project Title**: Financial News Analyst — Multi-Agent Investment Research System  
**Date**: May 2026  
**Classification**: Capstone Project — AI Engineering Programme

---

## Problem Statement

Retail investors face a significant information asymmetry. Professional investment analysis firms employ teams of quantitative analysts, news researchers, and sector specialists working in parallel to produce timely investment reports. An individual investor accessing the same information must manually cross-reference stock screeners, news aggregators, and financial databases — a process that takes hours and requires specialist knowledge to interpret.

The core challenge: **how do we bring structured, multi-perspective investment analysis to any user in seconds, at zero marginal cost, using only freely available data?**

---

## Solution

**Financial News Analyst** is a local multi-agent AI system that orchestrates three specialised AI agents in sequence to produce a structured investment analysis report. The system:

1. **Fetches live market data** via a custom-built MCP server that calls yfinance (stock prices, fundamentals, macro indices)
2. **Scrapes current financial news** via the same MCP server aggregating free RSS feeds and ticker-specific news
3. **Retrieves historical patterns** from a RAG knowledge base of financial analysis guides and company fundamentals
4. **Synthesises all three streams** into a structured 7-section investment report with bull/bear scenarios and risk flags

The entire system runs **locally on the user's machine** — no cloud APIs, no API keys, no data egress. The LLM (Ollama qwen2.5:7b) and embedding model (nomic-embed-text) run on local GPU hardware.

---

## Technical Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent Orchestration | CrewAI | Sequential 3-agent pipeline |
| LLM | Ollama (qwen2.5:7b) | Local inference, ~1-2s per agent step |
| MCP Server | FastMCP (custom-built) | Exposes financial data tools to agents |
| Knowledge Base | ChromaDB + nomic-embed-text | RAG over financial analysis documents |
| Market Data | yfinance | Free stock data (prices, fundamentals) |
| News | RSS + yfinance News | Free financial news aggregation |
| UI | Streamlit | Analyst-grade dashboard interface |
| Security | Custom validators | Input sanitisation, rate limiting, guardrails |
| Observability | loguru + SQLite | Full audit trail and metrics |

**Key architectural decisions**:
- **Sequential agent chaining**: Data → News → Analysis. Each agent's output becomes context for the next, enabling genuine collaboration rather than independent parallel calls.
- **Custom MCP server**: Built from scratch using the MCP Python SDK. The server encapsulates all external data access, making agents fully decoupled from data source implementations.
- **RAG-grounded synthesis**: The Analysis Agent is explicitly prohibited from hallucinating analysis — it must retrieve relevant frameworks from the knowledge base before drawing conclusions. Score thresholds enforce retrieval quality.

---

## Key Findings

Through development and testing, this project established:

1. **7B models are sufficient for structured financial tasks** when given explicit role descriptions, tool access, and structured output requirements. The qwen2.5:7b model consistently produced coherent 7-section reports on valid tickers.

2. **MCP as an abstraction layer significantly improves agent testability**. Because all data access is routed through the MCP server, each tool can be tested independently of the agent layer.

3. **Input validation is the most critical security control**. LLM systems are vulnerable to prompt injection at the query boundary. The security layer (regex validation + injection pattern matching) blocked all tested adversarial inputs before they reached the LLM.

4. **RAG grounding reduces hallucination measurably**. Off-topic queries returned the explicit fallback message rather than confabulated "analysis", demonstrating the score threshold mechanism working correctly.

5. **Free data sources are viable for a functional MVP**. yfinance + RSS feeds provide sufficient data quality for educational-grade analysis with no API costs.

---

## Business Value

| Stakeholder | Value Delivered |
|-------------|----------------|
| Retail investors | Structured analysis in seconds vs. hours of manual research |
| Finance students | Interactive learning tool for financial analysis frameworks |
| Financial advisors | Rapid first-pass screening tool for client portfolios |
| Enterprises | Template for deploying private, on-premise financial AI (GDPR-safe) |

**Cost model**: €0 ongoing operational cost after hardware (dual 4090). No per-query API fees, no SaaS subscriptions, no data licensing fees. Scales to concurrent users limited only by GPU capacity.

---

## Limitations

- **Not financial advice**: The system explicitly disclaims investment advice. All outputs are AI-generated estimates based on publicly available data and must not be used for actual investment decisions without professional review.
- **Data freshness**: yfinance data may lag by 15 minutes (exchange delay). News from RSS feeds is typically within 1 hour.
- **Model limitations**: A 7B parameter model cannot match a certified financial analyst. The system is a research assistance tool, not a replacement for expert judgment.
- **Scale**: In-memory rate limiting resets on restart; the SQLite audit DB is not designed for concurrent multi-user production load.

---

## Conclusion

Financial News Analyst demonstrates that a capable, secure, and fully explainable multi-agent AI system can be built using only open-source tools and free data sources, running entirely on local hardware. The project achieves the core capstone objectives:

- ✅ Multi-agent architecture (3 agents with distinct roles)
- ✅ RAG pipeline over domain-specific knowledge base
- ✅ MCP integration via custom-built server
- ✅ Real-world applicability (investment research)
- ✅ Inter-agent collaboration (sequential context chaining)
- ✅ Testability (positive + adversarial test suites)
- ✅ Demonstrability (Streamlit UI with real-time agent progress)
- ✅ Security (OWASP-aligned input validation + rate limiting + output guardrails)
- ✅ Observability (structured logging + SQLite audit trail + user ratings)

The system is production-extensible: swap `qwen2.5:7b` for a larger model, replace in-memory rate limiting with Redis, and add authenticated multi-tenancy — the core architecture supports all of these without fundamental redesign.
