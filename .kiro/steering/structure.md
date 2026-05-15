# Project Structure & Architecture

## Directory Layout

```
src/                    — Application source code
├── main.py             — Entry point (CLI dispatch: dashboard vs backtest)
├── config.py           — All configuration: ticker definitions, indicator params, output paths
├── models.py           — Pure dataclasses (BuyScore, TickerData, Allocation, BacktestResult)
├── indicators.py       — Pure math functions (RSI, drawdown, score computation)
├── allocation.py       — Score-to-multiplier mapping, portfolio allocation logic
├── chart.py            — Plotly rendering and HTML output generation
├── backtest.py         — Backtest engine (flat DCA vs score-based DCA)
└── fetchers/           — Data source adapters
    ├── __init__.py     — Dispatcher: routes by source, computes indicators, returns TickerData
    ├── yfinance.py     — Yahoo Finance (international tickers)
    ├── pykrx.py        — Korean ETFs via pykrx library
    ├── naver.py        — Naver real-time price scraping (ETF + gold)
    └── krx_gold.py     — KRX Gold API + local CSV caching
tests/                  — Scenario-based tests (no network calls, synthetic inputs)
docs/                   — Detailed documentation (scoring, backtest, data sources, config)
data/                   — Local CSV cache (KRX Gold historical data)
out/                    — Generated HTML output (gitignored)
```

## Architecture Patterns

- **Layered design**: config → models → indicators → fetchers → allocation/backtest → chart → main
- **Pure functions for logic**: `indicators.py` has no side effects; all parameters passed explicitly
- **Dataclass contracts**: `models.py` defines shared types between modules — no business logic
- **Fetcher dispatcher**: `fetchers/__init__.py` is the single entry point (`fetch_ticker()`), routes to source-specific helpers, and returns a fully-populated `TickerData`
- **Config centralization**: All ticker definitions, thresholds, and settings live in `config.py`

## Conventions

- Module-level docstrings describe purpose and design intent
- Function docstrings use NumPy-style (Parameters/Returns sections)
- Type annotations with `from __future__ import annotations`
- Korean column names from pykrx are renamed to English equivalents at the fetcher boundary
- Tests use synthetic data — no network calls, no API keys required
- Each fetcher returns a consistent tuple signature for the dispatcher to unpack
