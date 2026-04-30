# Tech Stack

## Language & Runtime

- Python 3.10+
- Package/project manager: [uv](https://docs.astral.sh/uv/)

## Dependencies

| Library | Purpose |
|---------|---------|
| yfinance | Market data download and live price quotes |
| pandas | Data manipulation, time series, rolling calculations |
| plotly | Interactive HTML chart generation |

## Dev Dependencies

| Library | Purpose |
|---------|---------|
| pytest | Test runner |

## Project Configuration

- `pyproject.toml` — project metadata, dependencies, and pytest config.
- `requirements.txt` — pip-compatible dependency list (mirrors pyproject.toml).
- No linter or formatter is configured in the project.

## Common Commands

```bash
# Run dashboard (default mode)
uv run main.py

# Run backtest comparison
uv run main.py --backtest

# Run tests
uv run pytest

# Install dependencies (pip alternative)
pip install -r requirements.txt
```

## Build Notes

- No build step — the project runs directly as Python scripts.
- `run.bat` is a Windows convenience wrapper for `uv run main.py`.
- Output goes to `out/combined_chart.html` and opens automatically on Windows.
- uv manages the virtual environment in `.venv/` automatically.
