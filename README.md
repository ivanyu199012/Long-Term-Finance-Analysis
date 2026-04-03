# FinAnalysis

Interactive technical-analysis dashboard for S&P 500 and Gold. Downloads one year of daily data, computes moving averages and RSI, generates a buy-in score, and outputs a self-contained HTML chart you can open in any browser.

## Features

- **Interactive Plotly charts** — zoom, pan, hover for exact values
- **Moving averages** — MA50 / MA100 / MA200 with % distance from current price
- **RSI oscillator** — with overbought/oversold shading
- **Buy-in score (0–10)** — rules-based heuristic from MA positioning + RSI
- **Score breakdown** — see exactly how many points each indicator contributes
- **Single HTML output** — no server needed, just open the file

## Score methodology

| Component | Max points | Logic |
|-----------|-----------|-------|
| MA50      | 2         | +2 if price is below MA50 |
| MA100     | 2         | +2 if price is below MA100 |
| MA200     | 2         | +2 if price is below MA200 |
| RSI       | 4         | Linear scale: RSI ≤ 30 → 4 pts, RSI ≥ 70 → 0 pts |

> ⚠ This is a technical indicator score only — not financial advice.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

## Quick start

```bash
# Using uv (handles dependencies automatically)
uv run main.py

# Or using pip
pip install -r requirements.txt
python main.py
```

On Windows you can also double-click `run.bat`.

## Project structure

```
config.py   — Ticker list, MA windows, RSI period, chart settings
data.py     — Data fetching (yfinance) and indicator calculations
chart.py    — Plotly chart rendering and HTML output
main.py     — Entry point
```

## Configuration

Edit `config.py` to:

- Add/remove tickers in the `TICKERS` list
- Change moving-average windows (`MA_WINDOWS`)
- Adjust RSI period (`RSI_PERIOD`)
- Change the number of days shown (`TAIL_DAYS`)
- Modify chart colours and styles (`MA_STYLES`)

## Output

`combined_chart.html` — opens automatically on Windows after generation.
