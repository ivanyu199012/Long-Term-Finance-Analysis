# Product Overview

FinAnalysis is a technical-analysis dashboard for S&P 500, NASDAQ 100, and Gold. It downloads daily market data, computes indicators (moving averages, RSI, drawdown), generates a rules-based buy-in score (0–10), and outputs a self-contained interactive HTML chart.

## Core Capabilities

- **Dashboard mode** — fetches live data via yfinance, renders a Plotly chart with price/MA, RSI, and score panels per ticker, and opens the HTML output.
- **Backtest mode** (`--backtest`) — compares flat DCA vs score-based DCA over 5y and 10y periods for each ticker and a combined portfolio.
- **Portfolio allocation** — dynamically allocates a monthly budget across tickers using score-weighted base weights with minimum floors.

## Scoring System

The buy-in score combines three components (total 10 pts):
- **MA component (0–7)** — per-ticker weighted moving average positioning with linear fade thresholds.
- **RSI component (0–1.5)** — step function at RSI 35/45 boundaries.
- **Drawdown component (0–1.5)** — linear scale from 0% to a per-ticker drawdown threshold.

Score maps to a suggestion tier and investment multiplier (0.25x–2.25x of a base amount).

## Key Domain Concepts

- All monetary values are in Korean Won (₩).
- Each ticker has its own MA weights, fade thresholds, and drawdown full percentage — these are tuned to the asset's volatility profile.
- Estimated data handling: when yfinance returns incomplete rows (e.g. before market close), missing prices are filled with the mean of previous close and live price.
- The tool is explicitly **not financial advice** — it's a DCA timing heuristic.
