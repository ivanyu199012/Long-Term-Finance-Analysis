# FinAnalysis

Technical-analysis dashboard and DCA scoring system for S&P 500, NASDAQ 100, Gold (international + Korean markets). Generates buy-in scores, portfolio allocation recommendations, and backtest comparisons — all in a self-contained HTML dashboard.

## Features

- Interactive Plotly charts with MA, RSI, and score panels
- Buy-in score (0–10) from MA positioning + RSI + drawdown
- Portfolio allocation with dynamic score-based weighting
- Tabbed dashboard: Korea 🇰🇷 (investment) + International 🌐 (reference)
- Backtest: flat DCA vs score-based DCA over 5y and 10y
- Multiple data sources: yfinance, pykrx (Korean ETFs), KRX Gold API

## Quick Start

```bash
# Install dependencies
uv sync

# Create .env with your KRX API key (see .env.example)
cp .env.example .env

# Dashboard mode
uv run python -m src.main

# Backtest mode
uv run python -m src.main --backtest

# Run tests
uv run pytest
```

On Windows: double-click `run.bat`.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- KRX API key (for Korean gold data) — get at https://data.krx.co.kr/

## Project Structure

```
src/
├── main.py          — Entry point (dashboard + backtest)
├── config.py        — All configuration and ticker definitions
├── models.py        — Dataclasses (BuyScore, TickerData, etc.)
├── indicators.py    — Pure math (RSI, drawdown, score computation)
├── allocation.py    — Score-to-multiplier mapping, portfolio allocation
├── chart.py         — Plotly rendering and HTML output
├── backtest.py      — Backtest engine
└── fetchers/
    ├── __init__.py  — Dispatcher (routes by source)
    ├── yfinance.py  — Yahoo Finance fetcher
    ├── pykrx.py     — Korean ETF fetcher
    └── krx_gold.py  — KRX Gold API + CSV caching
tests/               — Scenario-based scoring + backtest + fetcher tests
docs/                — Detailed documentation
data/                — Local CSV cache (KRX Gold)
out/                 — Generated HTML output
```

## Documentation

- [Scoring methodology](docs/scoring.md) — how the buy-in score works
- [Backtest](docs/backtest.md) — strategies, metrics, and interpretation
- [Korean data sources](docs/korean-data-sources.md) — pykrx + KRX Gold API setup
- [Configuration](docs/configuration.md) — all settings explained

## Output

- `out/combined_chart.html` — tabbed dashboard (opens automatically on Windows)
- `out/backtest_chart.html` — backtest comparison table

> ⚠ Technical indicator scores only — not financial advice.
