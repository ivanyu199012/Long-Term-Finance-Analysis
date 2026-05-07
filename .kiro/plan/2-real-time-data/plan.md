# Real-Time Price for Korean Tickers

## Problem

Korean data sources (pykrx, KRX Gold API) only provide closing prices from completed trading days. During market hours, the dashboard shows yesterday's close — not the current price. This makes it hard to decide whether to buy *right now* based on the score.

## Goal

Show real-time (or near-real-time) prices for Korean tickers during market hours, so the score reflects the current market state when you're making a buy decision.

## Decisions

| Question | Decision |
|----------|----------|
| International tickers real-time? | No — yfinance `fast_info.last_price` is already sufficient |
| Show both close and live price? | Yes — display both for transparency |
| `--live` flag? | No — always attempt real-time for Korean tickers. If it fails, fall back silently with a warning. No extra flag needed. |
| Error handling | If scraping fails: print warning in terminal, show warning in dashboard, fall back to daily close price. Never crash. |

## Approach: Naver Finance Scraping

Scrape current prices from Naver Finance — no auth needed, covers both ETFs and gold.

### Data Sources

| Ticker | URL | What to parse |
|--------|-----|---------------|
| TIGER S&P500 (360750) | `https://finance.naver.com/item/main.naver?code=360750` | Current price from the page |
| TIGER 나스닥100 (133690) | `https://finance.naver.com/item/main.naver?code=133690` | Current price from the page |
| KRX Gold | `https://finance.naver.com/marketindex/goldDetail.naver` | KRX gold spot price |

### How It Works

1. Always attempt to scrape Naver for real-time price (regardless of market hours)
2. If scraping succeeds: use real-time price as `current_price`, show "live" indicator
3. If scraping fails: fall back to last close, show warning in terminal + dashboard
4. The score recalculates using whichever price is available
5. Dashboard shows both "Last Close" and "Live Price" for transparency

### What Changes in the Dashboard

**Score card (Korean tickers only):**
- Shows "Live: ₩XXX,XXX" alongside "Close: ₩XXX,XXX"
- MA distance percentages use the live price
- Score uses live price for MA component
- RSI and drawdown still use daily closes (they need full-day data)
- If live price unavailable: shows "⚠ Live price unavailable — using last close"

**Terminal output:**
- Normal: `Price: 26,160 (live) | Close: 25,980`
- Fallback: `⚠ Live price unavailable for TIGER S&P500 — using last close`

## Error Handling

```
Scraping attempt
    ├── Success → use live price, show "live" badge
    └── Failure (any exception)
            ├── Print yellow warning in terminal
            ├── Show red warning line in dashboard HTML
            └── Fall back to last close price (existing behavior)
```

Failure cases handled:
- Network timeout (requests timeout)
- HTTP error (4xx, 5xx)
- HTML structure changed (parse error)
- Price value not found or not numeric
- Any unexpected exception

## Architecture

```
src/fetchers/
├── naver.py          # NEW: scrape real-time prices from Naver Finance
├── __init__.py       # Updated: use naver price as current_price when available
├── pykrx.py          # Unchanged (still provides historical closes)
└── krx_gold.py       # Unchanged (still provides historical closes)
```

### `src/fetchers/naver.py`

```python
def get_realtime_price_etf(ticker_code: str) -> float | None:
    """Scrape current ETF price from Naver Finance.
    Returns None if scraping fails (any reason).
    Logs warning on failure.
    """

def get_realtime_price_gold() -> float | None:
    """Scrape current KRX gold spot price from Naver Finance.
    Returns None if scraping fails (any reason).
    Logs warning on failure.
    """
```

### Integration in `fetchers/__init__.py`

```python
def _fetch_pykrx(symbol):
    df = download_pykrx(symbol)
    close_price = get_live_price_pykrx(symbol)  # last close
    
    # Try real-time price
    live_price = get_realtime_price_etf(symbol)
    current_price = live_price if live_price else close_price
    is_live = live_price is not None
    
    return df, current_price, [], close_price, is_live

def _fetch_krx_gold(symbol):
    df = download_krx_gold(auth_key)
    close_price = get_live_price_krx_gold(auth_key)
    
    live_price = get_realtime_price_gold()
    current_price = live_price if live_price else close_price
    is_live = live_price is not None
    
    return df, current_price, [], close_price, is_live
```

### TickerData Extension

Add optional fields to `TickerData`:
- `close_price: float | None` — the last daily close (for display alongside live)
- `is_live_price: bool` — whether `current_price` is real-time or fallback
- `live_price_warning: str | None` — warning message if scraping failed

## Dependencies

- `beautifulsoup4` — for HTML parsing
- `requests` — already installed

## Risks

| Risk | Mitigation |
|------|-----------|
| Naver changes HTML structure | Graceful fallback to last close; warning shown |
| Rate limiting | Only 2-3 requests per run (one per ticker) |
| Price parsing fails | Return None → fallback, never crash |
| Stale live price (market closed) | Still useful — shows the last traded price which may differ from official close |

## Implementation Tasks

1. Add `beautifulsoup4` to dependencies
2. Implement `src/fetchers/naver.py` with ETF and gold scraping + error handling
3. Update `TickerData` model with `close_price`, `is_live_price`, `live_price_warning` fields
4. Update `_fetch_pykrx` and `_fetch_krx_gold` to try real-time price first
5. Update `src/main.py` terminal output to show live/close distinction + warnings
6. Update `src/chart.py` score cards to show both prices + warning when fallback
7. Write tests (mock HTML responses, test fallback behavior)
