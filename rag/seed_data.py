"""
Seed data builder — run once to populate the RAG knowledge base.

Downloads and creates financial analysis documents from free sources:
  1. yfinance earnings/fundamentals summaries for major tickers
  2. Recent financial news articles via RSS
  3. Pre-written financial analysis reference texts (P/E interpretation,
     technical patterns, macro signals, sector rotation — the "historical
     patterns" the Analysis Agent retrieves)

Usage:
    python rag/seed_data.py
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from pathlib import Path
from typing import Any

import yfinance as yf

from mcp_server.tools.news_fetcher import fetch_financial_news
from config.settings import SEED_TICKERS, CHROMA_DB_PATH


# ── Output path ────────────────────────────────────────────────────────────────
SEED_DOCS_DIR = Path(__file__).parent / "seed_docs"
SEED_DOCS_DIR.mkdir(exist_ok=True)


# ── 1. yfinance fundamentals summaries ────────────────────────────────────────

def _build_ticker_summary(symbol: str) -> str:
    """Create a structured text summary for a ticker from yfinance data."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        name = info.get("longName", symbol)
        sector = info.get("sector", "N/A")
        pe = info.get("trailingPE", "N/A")
        eps = info.get("trailingEps", "N/A")
        market_cap = info.get("marketCap")
        cap_str = f"${market_cap / 1e9:.1f}B" if market_cap else "N/A"
        revenue_growth = info.get("revenueGrowth")
        rev_str = f"{revenue_growth*100:.1f}%" if revenue_growth else "N/A"
        profit_margin = info.get("profitMargins")
        margin_str = f"{profit_margin*100:.1f}%" if profit_margin else "N/A"
        rec = info.get("recommendationKey", "N/A")
        target = info.get("targetMeanPrice", "N/A")
        w52_high = info.get("fiftyTwoWeekHigh", "N/A")
        w52_low = info.get("fiftyTwoWeekLow", "N/A")
        description = (info.get("longBusinessSummary") or "")[:400]

        # Quarterly financials
        fin_text = ""
        try:
            fins = ticker.quarterly_financials
            if not fins.empty:
                latest_col = fins.columns[0]
                total_rev = fins.loc["Total Revenue", latest_col] if "Total Revenue" in fins.index else None
                net_inc = fins.loc["Net Income", latest_col] if "Net Income" in fins.index else None
                if total_rev:
                    fin_text += f"  Latest Quarterly Revenue: ${total_rev/1e9:.2f}B\n"
                if net_inc:
                    fin_text += f"  Latest Quarterly Net Income: ${net_inc/1e9:.2f}B\n"
        except Exception:
            pass

        return (
            f"=== COMPANY ANALYSIS: {name} ({symbol}) ===\n\n"
            f"Sector: {sector}\n"
            f"Market Capitalization: {cap_str}\n"
            f"Trailing P/E Ratio: {pe}\n"
            f"Earnings Per Share (EPS): {eps}\n"
            f"Revenue Growth (YoY): {rev_str}\n"
            f"Profit Margin: {margin_str}\n"
            f"52-Week High: {w52_high} | 52-Week Low: {w52_low}\n"
            f"Analyst Recommendation: {rec} | Analyst Price Target: {target}\n"
            f"{fin_text}\n"
            f"Business Description:\n{description}\n\n"
            f"Investment Context:\n"
            f"A P/E ratio of {pe} for {name} should be evaluated relative to its "
            f"sector peers in {sector}. Revenue growth of {rev_str} and profit "
            f"margins of {margin_str} are key indicators of operational efficiency. "
            f"Analyst consensus of '{rec}' with a target price of {target} reflects "
            f"current Wall Street sentiment.\n"
        )
    except Exception as exc:
        return f"=== {symbol} DATA UNAVAILABLE ===\nError: {exc}\n"


def build_ticker_summaries() -> None:
    print("[Seed] Building yfinance fundamentals summaries ...")
    for symbol in SEED_TICKERS:
        print(f"  Fetching {symbol} ...")
        doc_text = _build_ticker_summary(symbol)
        (SEED_DOCS_DIR / f"fundamentals_{symbol}.txt").write_text(doc_text, encoding="utf-8")
    print(f"[Seed] Saved {len(SEED_TICKERS)} ticker summaries.")


# ── 2. RSS news articles ───────────────────────────────────────────────────────

def build_news_articles() -> None:
    print("[Seed] Fetching recent financial news from RSS ...")
    all_articles = fetch_financial_news(query="", limit=50)
    news_text = "=== RECENT FINANCIAL NEWS DIGEST ===\n\n"
    for i, art in enumerate(all_articles, 1):
        news_text += (
            f"--- Article {i} ---\n"
            f"Title: {art['title']}\n"
            f"Published: {art['published']}\n"
            f"Summary: {art['summary']}\n\n"
        )
    (SEED_DOCS_DIR / "recent_news.txt").write_text(news_text, encoding="utf-8")
    print(f"[Seed] Saved {len(all_articles)} news articles.")


# ── 3. Pre-written financial analysis reference texts ─────────────────────────

REFERENCE_TEXTS: list[tuple[str, str]] = [
    (
        "pe_ratio_analysis.txt",
        """=== GUIDE: PRICE-TO-EARNINGS (P/E) RATIO INTERPRETATION ===

The Price-to-Earnings (P/E) ratio is one of the most widely used valuation metrics.
It measures how much investors are willing to pay per dollar of earnings.

FORMULA: P/E = Current Stock Price / Earnings Per Share (EPS)

INTERPRETATION RANGES:
- P/E < 10: Potentially undervalued, or market expects declining earnings. Common in mature or cyclical industries (energy, banking).
- P/E 10–20: Fair value range for stable, mature companies with moderate growth.
- P/E 20–35: Growth premium — market expects above-average earnings growth. Typical for tech sector leaders.
- P/E 35–60: High growth expectations. Common in hypergrowth tech, biotech. Higher risk of multiple compression.
- P/E > 60: Speculative territory. Often seen in early-stage growth or turnaround stories. Requires exceptional growth to justify.

CONTEXT MATTERS:
- Always compare P/E to the sector average. A P/E of 30 may be cheap for software but expensive for utilities.
- Forward P/E (based on projected earnings) is often more useful than trailing P/E.
- A negative P/E means the company is currently unprofitable.
- PEG ratio (P/E divided by earnings growth rate) adjusts for growth: PEG < 1 is generally considered undervalued.

SECTOR AVERAGES (approximate):
- Technology: 25–40
- Healthcare: 20–30
- Financials: 10–15
- Energy: 8–15
- Utilities: 15–20
- Consumer Discretionary: 20–30

HISTORICAL PATTERN: The S&P 500 average P/E has ranged from ~7 (1980 lows) to ~45 (dot-com peak). The long-run average is approximately 15–17.
""",
    ),
    (
        "technical_analysis_patterns.txt",
        """=== GUIDE: KEY TECHNICAL ANALYSIS PATTERNS FOR STOCKS ===

Technical analysis studies price and volume patterns to forecast future price movement.

SUPPORT AND RESISTANCE:
- Support level: A price floor where buying interest is strong enough to prevent further decline. The more times a price bounces off a level, the stronger the support.
- Resistance level: A price ceiling where selling pressure overcomes buying. When resistance is broken, it often becomes new support.
- Breakout: Price decisively moving above resistance (bullish signal) or below support (bearish signal).

MOVING AVERAGES:
- 50-day SMA (Simple Moving Average): Short-to-medium trend indicator. Price above 50-day SMA is generally bullish.
- 200-day SMA: Long-term trend indicator. Golden Cross (50-day crosses above 200-day) is a major bullish signal. Death Cross is bearish.
- EMA (Exponential Moving Average): Weights recent prices more heavily, reacts faster to price changes.

RELATIVE STRENGTH INDEX (RSI):
- RSI measures momentum on a scale of 0–100.
- RSI > 70: Overbought — potential pullback or reversal signal.
- RSI < 30: Oversold — potential bounce or reversal signal.
- RSI divergence (price makes new high but RSI doesn't) warns of weakening momentum.

VOLUME ANALYSIS:
- Rising price + rising volume: Confirms the trend (strong signal).
- Rising price + falling volume: Trend may be weakening (divergence warning).
- High volume on breakout: Increases reliability of the breakout signal.

COMMON CHART PATTERNS:
- Head and Shoulders: Bearish reversal pattern — three peaks with the middle being highest.
- Cup and Handle: Bullish continuation — price forms a 'U' shape then a brief dip.
- Double Top / Double Bottom: Reversal patterns at resistance / support.
- Ascending Triangle: Bullish — higher lows with flat resistance ceiling, often breaks upward.

BOLLINGER BANDS:
- Two standard deviations above/below the 20-day SMA.
- Price touching upper band: Overbought region.
- Price touching lower band: Oversold region.
- Band squeeze (narrow bands): Indicates low volatility, often precedes a large move.
""",
    ),
    (
        "macro_economic_signals.txt",
        """=== GUIDE: MACROECONOMIC SIGNALS AND THEIR MARKET IMPACT ===

Macro signals affect all asset classes. Understanding them is essential for top-down investment analysis.

INTEREST RATES (Federal Reserve Policy):
- Rate hike cycle: Higher rates increase borrowing costs → compress P/E multiples → headwind for growth stocks. Benefit: value stocks, financials (wider net interest margin).
- Rate cut cycle: Lower rates reduce discount rates → expand P/E multiples → tailwind for growth and tech. Bonds rally.
- Fed Funds Rate above 4%: Generally contractionary territory, watch for recession signals.
- Inverted yield curve (2yr > 10yr): Historical predictor of recession within 12–18 months.

INFLATION (CPI / PCE):
- High inflation (>4%): Fed likely to raise rates → negative for bonds and growth stocks → positive for commodities, energy, TIPS.
- Moderate inflation (2–3%): Goldilocks zone — supports earnings without forcing aggressive Fed action.
- Deflation: Dangerous — signals weak demand, leads to corporate earnings compression.
- Core CPI vs Headline CPI: Core (excludes food/energy) is the Fed's preferred measure.

GDP GROWTH:
- GDP growth > 3%: Strong expansion, supportive of corporate earnings and equities.
- GDP growth 1–3%: Moderate growth, selective stock picking important.
- GDP growth < 0% (two consecutive quarters): Technical recession. Defensives outperform.

UNEMPLOYMENT:
- Low unemployment (<4%): Strong consumer spending, supports retail and consumer discretionary.
- Rising unemployment: Leading indicator of consumer stress, watch credit card delinquencies.

SECTOR ROTATION BY ECONOMIC CYCLE:
- Early cycle (recovery): Financials, Consumer Discretionary, Real Estate outperform.
- Mid cycle (expansion): Technology, Industrials, Materials lead.
- Late cycle (slowdown): Energy, Healthcare, Consumer Staples are defensive.
- Recession: Utilities, Healthcare, Consumer Staples — the classic defensives.

DOLLAR INDEX (DXY):
- Strong dollar: Headwind for US multinationals (revenue in foreign currencies converts to fewer dollars). Positive for US consumers (cheaper imports).
- Weak dollar: Tailwind for US exporters and emerging market assets.
""",
    ),
    (
        "sector_rotation_guide.txt",
        """=== GUIDE: SECTOR ROTATION STRATEGIES ===

Sector rotation is the practice of shifting investment capital between industry sectors
based on expected performance at different stages of the economic cycle.

THE 11 GICS SECTORS (S&P 500):
1. Information Technology (IT)
2. Healthcare
3. Financials
4. Consumer Discretionary
5. Communication Services
6. Industrials
7. Consumer Staples
8. Energy
9. Materials
10. Real Estate (REITs)
11. Utilities

ROTATION FRAMEWORK:
- Bull market early phase: Cyclicals (Consumer Discretionary, Technology, Financials) lead.
- Bull market mature phase: Energy, Materials, Industrials catch up as demand peaks.
- Bear market early phase: Defensives rotate in: Healthcare, Consumer Staples, Utilities.
- Bear market deep phase: Cash, Treasuries, Gold outperform equities.

KEY METRICS FOR SECTOR COMPARISON:
- Relative Strength (RS): Sector ETF price vs S&P 500. RS > 1 = outperforming.
- Earnings Revision Breadth: Sectors with more upward analyst revisions tend to outperform.
- Forward P/E vs 10-year average: Cheap sectors relative to history are candidates for rotation.

TECHNOLOGY SECTOR SPECIFICS:
- Highly sensitive to interest rates (long-duration assets).
- Revenue growth and free cash flow margin are more important than P/E for high-growth names.
- Semiconductor cycle (NVDA, AMD, INTC) is distinct from software cycle.
- AI infrastructure spending (hyperscalers: MSFT, GOOGL, AMZN, META) drives chipmaker demand.

FINANCIAL SECTOR SPECIFICS:
- Banks benefit from steeper yield curves (borrow short, lend long).
- Net Interest Margin (NIM) expands with rising rates.
- Credit quality (NPL ratio) deteriorates in recessions.

ENERGY SECTOR SPECIFICS:
- Highly correlated with oil price (WTI Crude, Brent).
- Oil above $80/bbl generally very profitable for major integrated oil companies.
- ESG headwinds but strong free cash flow generation in recent cycles.
""",
    ),
    (
        "earnings_analysis_framework.txt",
        """=== GUIDE: EARNINGS ANALYSIS FRAMEWORK ===

Earnings season (4 times per year) is when public companies report quarterly financial results.
Understanding how to interpret earnings reports is critical for investment decisions.

KEY METRICS IN AN EARNINGS REPORT:
1. Revenue (Top Line): Total sales. Compare to analyst consensus estimates.
   - Revenue Beat: Actual > Estimate (positive surprise)
   - Revenue Miss: Actual < Estimate (negative surprise)

2. EPS (Earnings Per Share): Net income / shares outstanding.
   - GAAP EPS: Includes all items (stock comp, restructuring charges, etc.)
   - Non-GAAP / Adjusted EPS: Excludes one-time items. Often higher. Watch for quality.

3. Gross Margin: (Revenue - COGS) / Revenue. Measures pricing power.
4. Operating Margin: Profitability after operating expenses. More comprehensive than gross margin.
5. Free Cash Flow (FCF): Cash from operations minus capex. "Cash is king" — less manipulable than EPS.
6. Guidance: Forward-looking revenue/EPS outlook from management. Often more impactful than the actual results.

EARNINGS SURPRISE INTERPRETATION:
- Beat EPS + Beat Revenue + Raise Guidance: Strongest signal — stock typically rallies.
- Beat EPS + Miss Revenue: Mixed — operational efficiency but demand concerns.
- Miss EPS + Beat Revenue: Margin compression — watch cost trajectory.
- Miss EPS + Miss Revenue + Lower Guidance: Trifecta miss — significant selloff typical.

"BUY THE RUMOR, SELL THE NEWS" PATTERN:
Stocks that run up significantly into earnings often sell off on "good" results because
the good news was already priced in. The setup matters as much as the result.

HISTORICAL EARNINGS GROWTH VS PRICE:
Long-run equity returns closely track earnings growth. S&P 500 earnings grow ~7% annually on average.
Companies with sustained 15%+ EPS growth (e.g., FAANG names in 2015-2022) command premium multiples.
When EPS growth decelerates from high levels, multiple compression can be severe.

EARNINGS QUALITY CHECKLIST:
✓ Does FCF match reported earnings? (High accruals ratio = lower quality)
✓ Is revenue growth organic or acquisition-driven?
✓ Is EPS growth driven by buybacks (shares declining) or actual earnings growth?
✓ Are accounts receivable growing faster than revenue? (Collection risk)
""",
    ),
    (
        "risk_management_framework.txt",
        """=== GUIDE: INVESTMENT RISK MANAGEMENT FRAMEWORK ===

All investment analysis must include a risk assessment. No analysis is complete without
identifying downside scenarios and quantifying potential loss.

KEY RISK METRICS:
- Beta: Sensitivity to market movements. Beta > 1 = amplifies market moves. Beta < 1 = defensive.
- Sharpe Ratio: (Return - Risk-free rate) / Standard Deviation. Higher = better risk-adjusted return.
- Max Drawdown: Largest peak-to-trough decline. Measures tail risk.
- Volatility (30-day): Standard deviation of daily returns. Higher = more uncertain.

RISK CATEGORIES:
1. Market Risk (Systematic): Overall market decline affects all stocks. Diversification helps but cannot eliminate.
2. Company-Specific Risk (Idiosyncratic): Earnings miss, CEO departure, product failure, litigation.
3. Sector/Industry Risk: Regulatory changes (pharma, fintech), commodity price shifts (energy), rate sensitivity (REITs).
4. Macro Risk: Recession, inflation shock, geopolitical events, central bank policy shifts.
5. Liquidity Risk: Inability to exit a position at desired price. More relevant for small-cap stocks.
6. Concentration Risk: Too much exposure to a single stock, sector, or theme.

POSITION SIZING PRINCIPLES:
- 2% Rule: Never risk more than 2% of portfolio on a single trade.
- Kelly Criterion: Optimal position size based on edge and win probability.
- Diversification: Target 20–30 uncorrelated positions to reduce idiosyncratic risk.

STOP-LOSS AND RISK/REWARD:
- Minimum acceptable risk/reward ratio: 1:2 (risk $1 to make $2).
- Hard stop-loss: Predetermined exit price to limit downside.
- Trailing stop: Moves up with price to lock in gains.

BEAR CASE ANALYSIS:
Always model a bear case scenario:
- What if revenue growth is half of expectations?
- What if multiple compresses to sector average (or below)?
- What is the downside price target if the investment thesis is wrong?

IMPORTANT: This framework is for educational and analytical purposes only.
Past patterns do not guarantee future results. All investments carry risk of loss.
""",
    ),
]


def build_reference_texts() -> None:
    print("[Seed] Writing pre-built financial analysis reference texts ...")
    for filename, content in REFERENCE_TEXTS:
        (SEED_DOCS_DIR / filename).write_text(content, encoding="utf-8")
    print(f"[Seed] Saved {len(REFERENCE_TEXTS)} reference documents.")


# ── Main entry point ───────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Financial News Analyst — RAG Seed Data Builder")
    print("=" * 60)

    build_reference_texts()
    build_ticker_summaries()
    build_news_articles()

    print("\n[Seed] All seed documents saved to:", SEED_DOCS_DIR)
    print("[Seed] Run rag/indexer.py next to embed and store in ChromaDB.")


if __name__ == "__main__":
    main()
