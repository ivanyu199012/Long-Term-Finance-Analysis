# Tech Stack & Build System

## Language & Runtime

- Python 3.10+
- Package manager: [uv](https://docs.astral.sh/uv/)

## Key Dependencies

| Library | Purpose |
|---------|---------|
| pandas | Data manipulation, time series |
| plotly | Interactive HTML chart generation |
| jinja2 | HTML templating for dashboard/backtest output |
| yfinance | Yahoo Finance data fetching |
| pykrx | Korean stock/ETF market data |
| requests | HTTP calls (KRX Gold API, Naver) |
| python-dotenv | Environment variable loading |

## Dev Dependencies

| Library | Purpose |
|---------|---------|
| pytest | Test runner |

## Common Commands

```bash
# Install/sync dependencies
uv sync

# Run dashboard (default mode)
uv run python -m src.main

# Run backtest mode
uv run python -m src.main --backtest

# Run tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_scoring.py -v
```

## Environment Setup

- Copy `.env.example` to `.env`
- Set `KRX_AUTH_KEY` for Korean gold data access (from https://data.krx.co.kr/)

## Build Configuration

- `pyproject.toml` defines the project metadata, dependencies, and pytest config
- Entry point: `finanalysis = "src.main:main"`
- Test paths configured to `tests/` with verbose output (`-v`)
- Dependencies pinned to compatible ranges (e.g., `pandas>=2.0,<3.0`)
