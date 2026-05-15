# Project Structure & Architecture

## Directory Layout

```
src/                    — Application source code
├── main.py             — Entry point (CLI dispatch: dashboard vs backtest, parallel fetching)
├── config.py           — All configuration: ticker definitions, indicator params, network settings, output paths
├── models.py           — TypedDict (TickerConfig), dataclasses (FetchResult, BuyScore, TickerData, etc.), FetchError exception
├── indicators.py       — Pure math functions (RSI, drawdown, score computation, score_to_multiplier)
├── allocation.py       — enforce_weight_floors, compute_allocation, re-exports score_to_multiplier
├── chart.py            — Plotly figure construction + Jinja2 template rendering
├── backtest.py         — Backtest engine (flat DCA vs score-based DCA)
├── templates/          — Jinja2 HTML templates (separated from Python logic)
│   ├── dashboard.html  — Base page wrapper for the dashboard
│   ├── backtest.html   — Full backtest results page with comparison tables
│   └── partials/
│       ├── score_cards.html — Ticker score cards with MA/RSI/DD breakdown
│       └── tab_layout.html  — Tabbed interface (Korea 🇰🇷 / International 🌐)
└── fetchers/           — Data source adapters
    ├── __init__.py     — Dispatcher: routes by source, computes indicators, returns TickerData
    ├── yfinance.py     — Yahoo Finance (international tickers)
    ├── pykrx.py        — Korean ETFs via pykrx library + Naver chart API fallback
    ├── naver.py        — Naver real-time price APIs (ETF, domestic gold, international gold)
    └── krx_gold.py     — KRX Gold API + local CSV caching
tests/                  — Scenario-based tests (no network calls, synthetic inputs)
docs/                   — Detailed documentation (scoring, backtest, data sources, config)
data/                   — Local CSV cache (KRX Gold historical data)
out/                    — Generated HTML output (gitignored)
```

## Architecture Patterns

- **Layered design**: config → models → indicators → fetchers → allocation/backtest → chart → main
- **Pure functions for logic**: `indicators.py` has no side effects; all parameters passed explicitly
- **Type-safe contracts**: `TickerConfig` (TypedDict), `FetchResult` (dataclass), `FetchError` (exception) in `models.py`
- **Fetcher dispatcher**: `fetchers/__init__.py` is the single entry point (`fetch_ticker()`), routes to source-specific helpers, returns `FetchResult` then builds `TickerData`
- **Fallback chains**: pykrx → Naver chart API; live price sources configurable per ticker via `live_price_source`
- **Config centralization**: All ticker definitions, thresholds, timeouts, and paths live in `config.py`
- **Template separation**: HTML/CSS/JS in Jinja2 templates (`src/templates/`), Plotly figure construction stays in Python
- **Parallel fetching**: yfinance tickers run sequentially (not thread-safe), non-yfinance tickers run in parallel via ThreadPoolExecutor

## Conventions

- Module-level docstrings describe purpose and design intent
- Function docstrings use NumPy-style (Parameters/Returns sections)
- Type annotations with `from __future__ import annotations`
- Korean column names from pykrx are renamed to English equivalents at the fetcher boundary
- Tests use synthetic data — no network calls, no API keys required
- Fetchers return `FetchResult` dataclass (not raw tuples)
- Custom `FetchError` exception for unrecoverable fetch failures
- `enforce_weight_floors()` is the shared helper for allocation floor logic (used by both dashboard and backtest)
