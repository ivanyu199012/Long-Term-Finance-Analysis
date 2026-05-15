# Korean Data Sources

## Overview

Korean tickers use two data sources:
- **pykrx** — for Korean-listed ETFs (TIGER S&P500, TIGER 나스닥100)
- **KRX Open API** — for KRX Gold Spot (금현물 1Kg)

## Setup

### 1. Install dependencies

```bash
uv sync
```

pykrx and requests are included in `pyproject.toml`.

### 2. Configure KRX API key

Create a `.env` file in the project root (see `.env.example`):

```
KRX_AUTH_KEY=your_key_here
```

Get your key at: https://data.krx.co.kr/

### 3. Run

```bash
uv run python -m src.main
```

The Korean tickers will be fetched automatically.

## pykrx (Korean ETFs)

- **Library:** `pykrx` (pip package)
- **Tickers:** 360750 (TIGER S&P500), 133690 (TIGER 나스닥100)
- **Method:** `stock.get_market_ohlcv_by_date(start, end, ticker)`
- **Rate limits:** None
- **Caching:** Not needed (fast single-call API)

### Naver Chart API Fallback

When pykrx fails (network timeout, KRX site changes), the fetcher automatically falls back to Naver's mobile chart API:

- **URL:** `https://m.stock.naver.com/front-api/external/chart/domestic/info?symbol={code}&requestType=1&startTime={start}&endTime={end}&timeframe=day`
- **Response format:** List-of-lists (may be JSON or JS-literal with single quotes)
- **Parsing:** Tries `json.loads()` first, falls back to `ast.literal_eval()` for single-quoted responses
- **Columns:** `['날짜', '시가', '고가', '저가', '종가', '거래량', '외국인소진율']`

This is an undocumented Naver frontend API — it may change without notice and is only used as a fallback.

## KRX Gold API

- **Endpoint:** `https://data-dbg.krx.co.kr/svc/apis/gen/gold_bydd_trd`
- **Method:** GET with `AUTH_KEY` header and `basDd` (YYYYMMDD) param
- **Product filter:** `ISU_NM` containing "금 99.99_1Kg" (case-insensitive)
- **Rate limits:** 0.2s sleep between requests
- **One day per request** — must loop for historical data

### Caching

Gold data is cached locally at `data/gold_krx.csv`:
- First run: fetches all available history (slow, ~5-10 min for full range)
- Subsequent runs: loads cache, only fetches dates after the last cached date
- Cache is committed to git (shared across clones)
- Early-exit: stops fetching after 30 consecutive empty days

### Limitations

- API may not have data for future dates or very recent dates
- Non-trading days (weekends, holidays) return empty responses
- Product name casing varies between dates (`1Kg` vs `1kg`) — handled with case-insensitive matching
