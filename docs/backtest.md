# Backtest

Compares DCA strategies over historical data to validate the scoring system.

## Running

```bash
uv run python -m src.main --backtest
```

## Strategies Compared

### Per-Ticker Backtest

- **Flat DCA** — invest a fixed `BASE_AMOUNT` every month
- **Score-based DCA (raw)** — invest `BASE_AMOUNT × multiplier` based on the monthly score. Total invested differs from flat.
- **Score-based DCA (normalized)** — same as raw but scaled so total invested matches flat DCA. Apples-to-apples return comparison.

### Portfolio Backtest

- **Flat Allocation** — fixed weight split (55/15/30) every month
- **Score Allocation** — dynamic weights based on per-asset scores, with minimum floors enforced

## Output

- Terminal: formatted comparison tables
- HTML: `out/backtest_chart.html` — static table showing returns, max drawdown, and edge per ticker

## Metrics

| Metric | Description |
|--------|-------------|
| Total Return % | (final value - total invested) / total invested |
| Max Drawdown % | Largest peak-to-trough decline in portfolio value |
| Edge (pp) | Score return minus Flat return (percentage points) |

## Periods

- **5y** — 60 months of monthly DCA
- **10y** — 120 months of monthly DCA

Extra data is downloaded for warm-up (MA200 + drawdown window need ~500 trading days).

## Lookahead Bias Prevention

Monthly scores are shifted by 1 month — last month's signal decides this month's investment amount. This prevents using information that wouldn't be available at decision time.

## Data Sources for Backtest

| Source | Method |
|--------|--------|
| International (yfinance) | `yf.download(period="7y"/"12y")` |
| Korean ETFs (pykrx) | `stock.get_market_ohlcv_by_date()` with extended range |
| KRX Gold | Cached CSV data via KRX API |
