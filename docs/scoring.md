# Score Methodology

The buy-in score (0–10) is a rules-based heuristic combining three components:

## Components

| Component | Max pts | Description |
|-----------|---------|-------------|
| MA (moving averages) | 7.0 | Weighted per MA window — full weight below MA, linear fade above |
| RSI | 1.5 | Step function: full at RSI ≤ 35, half at RSI ≤ 45, 0 above |
| Drawdown | 1.5 | Linear: 0 pts at 0% DD, full at per-ticker threshold |

**Total possible: 10 pts** (clamped to 0–10)

## Per-Ticker MA Weights

### S&P 500 / TIGER S&P500 (MA total: 7.0, DD full at 25%)

| Component | Max pts | Fade threshold |
|-----------|---------|----------------|
| MA200 | 5.0 | 0–15% above |
| MA100 | 1.5 | 0–10% above |
| MA50 | 0.5 | 0–7% above |

### NASDAQ 100 / TIGER 나스닥100 (MA total: 7.0, DD full at 35%)

| Component | Max pts | Fade threshold |
|-----------|---------|----------------|
| MA200 | 4.0 | 0–20% above |
| MA100 | 2.0 | 0–14% above |
| MA50 | 1.0 | 0–10% above |

### Gold / 금현물 KRX (MA total: 7.0, DD full at 20%)

| Component | Max pts | Fade threshold |
|-----------|---------|----------------|
| MA200 | 2.75 | 0–12% above |
| MA100 | 2.5 | 0–8% above |
| MA50 | 1.75 | 0–5% above |

## Suggestion Thresholds

| Score | Suggestion | Multiplier | Amount (₩) |
|-------|-----------|------------|------------|
| ≥ 8.5 | Aggressive buy-in | 2.25x | 1,125,000 |
| ≥ 6.5 | Increase buy-in | 1.50x | 750,000 |
| ≥ 4.5 | Regular buy-in | 1.00x | 500,000 |
| ≥ 2.5 | Reduce buy-in | 0.50x | 250,000 |
| < 2.5 | Minimum buy-in | 0.25x | 125,000 |

## Design Notes

> ⚠ This is a technical indicator score only — not financial advice.

> ⚠ **Downside double-counting:** The MA and drawdown components are highly correlated — when price drops below MAs, drawdown also increases. This is by design for a DCA timing tool — it intentionally becomes more aggressive during downturns.

## Estimated Data Handling

When yfinance returns incomplete rows (e.g. today before market close), missing prices are filled with the mean of the previous day's close and the current live price. This keeps MA and drawdown calculations valid without dropping the row.
