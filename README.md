# FinAnalysis

Interactive technical-analysis dashboard for S&P 500 and Gold. Downloads daily data, computes moving averages, RSI, and drawdown, generates a buy-in score, and outputs a self-contained HTML chart you can open in any browser.

## Features

- **Interactive Plotly charts** — zoom, pan, hover for exact values
- **Moving averages** — MA50 / MA100 / MA200 with % distance from current price
- **RSI oscillator** — with overbought/oversold shading
- **Drawdown tracking** — current and max drawdown from peak
- **Buy-in score (0–10)** — rules-based heuristic from MA positioning + RSI + drawdown
- **Historical score chart** — score plotted over the last 100 days with suggestion threshold lines
- **Per-product MA weights** — each ticker can have its own MA weight configuration
- **Score breakdown** — see exactly how many points each indicator contributes
- **Single HTML output** — no server needed, just open the file

## Score methodology

MA weights are configured per ticker:

**S&P 500** (MA total: 7.0)

| Component | Max pts | Logic |
|-----------|---------|-------|
| MA200     | 5.0     | Full weight if price is below MA200 |
| MA100     | 1.5     | Full weight if price is below MA100 |
| MA50      | 0.5     | Full weight if price is below MA50  |

**Gold** (MA total: 7.0)

| Component | Max pts | Logic |
|-----------|---------|-------|
| MA200     | 2.75    | Full weight if price is below MA200 |
| MA100     | 2.5     | Full weight if price is below MA100 |
| MA50      | 1.75    | Full weight if price is below MA50  |

**Shared components**

| Component | Max pts | Logic |
|-----------|---------|-------|
| RSI       | 1.5     | Step: full at RSI ≤ 30, half at RSI ≤ 40, 0 above 40 |
| Drawdown  | 1.5     | Linear: 0 pts at 0% DD, full at 30% DD |

**Total possible: 10 pts** (clamped to 0–10)

### Suggestion thresholds

| Score   | Suggestion        |
|---------|-------------------|
| ≥ 8.5   | Aggressive buy-in |
| ≥ 6.5   | Increase buy-in   |
| ≥ 4.5   | Regular buy-in    |
| ≥ 2.5   | Reduce buy-in     |
| < 2.5   | Minimum buy-in    |

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
config.py   — Ticker list, per-product MA weights, RSI/DD settings, chart styles
data.py     — Data fetching (yfinance) and indicator/score calculations
chart.py    — Plotly chart rendering and HTML output (price, RSI, score panels)
main.py     — Entry point
```

## Configuration

Edit `config.py` to:

- Add/remove tickers in the `TICKERS` list (each with its own `ma_weights`)
- Change moving-average windows (`MA_WINDOWS`)
- Adjust RSI period and max score (`RSI_PERIOD`, `RSI_MAX_SCORE`)
- Adjust drawdown max score and full-credit threshold (`DRAWDOWN_MAX_SCORE`, `DRAWDOWN_FULL_PCT`)
- Change the download period (`DOWNLOAD_PERIOD`)
- Change the number of days shown (`TAIL_DAYS`)
- Modify chart colours and styles (`MA_STYLES`)

## Output

`combined_chart.html` — opens automatically on Windows after generation.
