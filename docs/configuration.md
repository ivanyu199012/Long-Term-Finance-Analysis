# Configuration

All configuration lives in `src/config.py`.

## Ticker Groups

```python
TICKERS_INTL  # International (USD) — yfinance source
TICKERS_KR    # Korean (KRW) — pykrx + krx_gold sources
TICKERS       # Combined list (TICKERS_INTL + TICKERS_KR)
```

### Per-Ticker Settings

Each ticker dict has:

| Key | Description |
|-----|-------------|
| `symbol` | Ticker symbol (yfinance format, pykrx code, or "KRX_GOLD") |
| `label` | Display name |
| `source` | Data source: "yfinance", "pykrx", or "krx_gold" |
| `ma_weights` | Dict mapping MA window → max score points |
| `ma_fade_thresholds` | Dict mapping MA window → fade-out % threshold |
| `drawdown_full_pct` | Drawdown % at which full DD score is awarded |
| `base_weight` | Base portfolio allocation weight (sums to 1.0 per group) |
| `min_weight` | Minimum allocation floor |

## Technical Indicator Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `MA_WINDOWS` | [50, 100, 200] | Moving average window sizes |
| `RSI_PERIOD` | 14 | RSI look-back period |
| `RSI_MAX_SCORE` | 1.5 | Max RSI component score |
| `DRAWDOWN_MAX_SCORE` | 1.5 | Max drawdown component score |
| `DRAWDOWN_WINDOW` | 500 | Rolling window for peak detection |
| `TAIL_DAYS` | 100 | Days shown on the chart |
| `DOWNLOAD_PERIOD` | "3y" | yfinance download period (yfinance only) |

## Investment Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `BASE_AMOUNT` | ₩500,000 | Base monthly amount for per-ticker suggestions |
| `MONTHLY_BUDGET` | ₩1,000,000 | Total monthly budget for portfolio allocation |

## API Keys

| Setting | Source | Description |
|---------|--------|-------------|
| `KRX_AUTH_KEY` | `.env` file | KRX Open API key for gold data |

## Output

| Setting | Default | Description |
|---------|---------|-------------|
| `OUTPUT_FILE` | `out/combined_chart.html` | Dashboard output path |
| `BACKTEST_OUTPUT_FILE` | `out/backtest_chart.html` | Backtest output path |

## Chart Appearance

| Setting | Description |
|---------|-------------|
| `MA_STYLES` | Line style and color per MA window |
| `FIGURE_SIZE` | Chart dimensions |
| `HEIGHT_RATIOS` | Row height ratios |
