# Project Structure

```
.
├── main.py           # Entry point — dispatches to dashboard or backtest mode
├── config.py         # All configuration: tickers, indicator params, chart styles, output paths
├── data.py           # Data fetching (yfinance), indicator calculations, scoring logic, allocation
├── chart.py          # Plotly chart rendering and HTML output generation
├── backtest.py       # Backtest engine: flat DCA vs score-based DCA simulation
├── tests/
│   ├── test_scoring.py   # Scenario-based tests for buy-in scoring (_compute_buy_score)
│   └── test_backtest.py  # Tests for DCA strategy simulation and multiplier mapping
├── out/
│   └── combined_chart.html  # Generated output (git-ignored)
├── pyproject.toml    # Project metadata, dependencies, pytest config
├── requirements.txt  # Pip-compatible dependency list
└── run.bat           # Windows convenience launcher
```

## Architecture

The project follows a flat module layout with clear separation of concerns:

- **config.py** is the single source of truth for all tunable parameters. Other modules import from it — never hardcode values elsewhere.
- **data.py** owns all yfinance interaction and all scoring/indicator math. It exposes `TickerData` and `BuyScore` dataclasses as the primary data contracts.
- **chart.py** is purely presentational — it receives computed `TickerData` objects and renders HTML. No data fetching or calculation here.
- **backtest.py** is a pure calculation module — no I/O or network calls. It reuses scoring functions from `data.py`.
- **main.py** is thin orchestration only — it wires the other modules together and handles CLI dispatch.

## Conventions

- Dataclasses are used for structured data containers (`BuyScore`, `TickerData`, `BacktestResult`, `Allocation`, etc.).
- Private helpers are prefixed with `_` (e.g. `_compute_buy_score`, `_calc_rsi`). Public API functions have no prefix.
- Tests use synthetic data only — no network calls. Test classes are grouped by market scenario (e.g. `TestNormalBullMarket`, `TestMajorCrash`).
- Type hints are used throughout. `from __future__ import annotations` is standard.
- Docstrings follow NumPy/Google hybrid style with `Parameters` / `Returns` sections.
