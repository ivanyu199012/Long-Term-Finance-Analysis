# Integration Plan: Korean ETFs + KRX Gold

## Overview

Add three Korean-market tickers alongside the existing international ones:
- **KRX Gold Spot** (금 1Kg) — via KRX Open API
- **TIGER 미국 S&P500 ETF** (360750) — via pykrx
- **TIGER 미국 나스닥100 ETF** (133690) — via pykrx

These use the same scoring, backtest, and chart logic — only the data fetching layer differs.

---

## Decisions

| Question | Decision |
|----------|----------|
| Separate ticker group or mixed? | Two groups on the same dashboard, visually separated: "International (USD)" on top, "Korean (KRW)" below. Portfolio allocation applies only to Korean tickers (actual investment vehicles). International tickers serve as reference signals. |
| KRX API auth key | Use `python-dotenv` to load from `.env` file. Read via `os.environ.get("KRX_AUTH_KEY", "")` in config. `.env` is git-ignored. |
| Currency | Keep separate — each group shows prices in its native currency (USD / KRW). No conversion. |
| Keep GC=F (yfinance Gold)? | Yes — keep as a reference benchmark alongside KRX Gold. |
| Refactor data.py? | Yes — split into `models.py`, `indicators.py`, `allocation.py`, `fetchers/` package. |
| score_to_multiplier / compute_allocation | Move to dedicated `allocation.py` — used by both dashboard and backtest. |
| Folder structure | Move to `src/` package with `fetchers/` subfolder for data sources. |

---

## 1. New dependencies

Add to `pyproject.toml` and `requirements.txt`:
```
pykrx>=1.0
python-dotenv>=1.0
requests>=2.28
```

---

## 2. Project restructure

Current flat layout → `src/` package:

```
src/
├── __init__.py
├── main.py              # Entry point (dashboard + backtest dispatch)
├── config.py            # All configuration + dotenv loading
├── models.py            # Dataclasses: BuyScore, TickerData, Allocation, BacktestResult, etc.
├── indicators.py        # Pure math: _calc_rsi, _calc_drawdown, _compute_buy_score, _compute_score_series
├── allocation.py        # score_to_multiplier, compute_allocation
├── chart.py             # Plotly rendering (dashboard + backtest charts)
├── backtest.py          # Backtest engine
└── fetchers/
    ├── __init__.py      # Re-exports: fetch_ticker() dispatcher (routes by "source" field)
    ├── yfinance.py      # _download, _get_live_price (existing logic)
    ├── pykrx.py         # _download_pykrx (Korean ETFs)
    └── krx_gold.py      # _download_krx_gold (KRX API + local CSV caching)
tests/
├── test_scoring.py
├── test_backtest.py
└── ...
data/                    # Local CSV cache (git-ignored)
out/                     # Generated HTML output (git-ignored)
.env                     # KRX_AUTH_KEY (git-ignored)
```

**Entry point adjustments:**
- `pyproject.toml` script: `finanalysis = "src.main:main"`
- `run.bat`: `uv run python -m src.main`

---

## 3. Module responsibilities

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `models.py` | Pure dataclasses — no logic | None |
| `indicators.py` | RSI, drawdown, score computation (pure math, params passed in) | `pandas`, `models` |
| `allocation.py` | `score_to_multiplier()`, `compute_allocation()` | `models`, `config` |
| `fetchers/__init__.py` | `fetch_ticker()` dispatcher — routes to correct source | `fetchers.*`, `indicators`, `models`, `config` |
| `fetchers/yfinance.py` | Download + live price via yfinance | `yfinance`, `pandas` |
| `fetchers/pykrx.py` | Download via pykrx | `pykrx`, `pandas` |
| `fetchers/krx_gold.py` | Download via KRX API + CSV caching | `requests`, `pandas`, `config` |
| `backtest.py` | Backtest engine (pure calculation) | `indicators`, `allocation`, `models`, `config` |
| `chart.py` | Plotly rendering (dashboard + backtest) | `plotly`, `models`, `config` |
| `main.py` | CLI dispatch, orchestration, terminal output | Everything above |
| `config.py` | All tunable parameters, ticker definitions, dotenv loading | `python-dotenv` |

---

## 4. Configuration (`config.py`)

```python
import os
from dotenv import load_dotenv

load_dotenv()

KRX_AUTH_KEY: str = os.environ.get("KRX_AUTH_KEY", "")
```

New ticker entries use a `"source"` field:

```python
# Existing tickers get source: "yfinance" (explicit)
{"symbol": "^GSPC", "label": "S&P 500", "source": "yfinance", ...},
{"symbol": "^NDX",  "label": "NASDAQ 100", "source": "yfinance", ...},
{"symbol": "GC=F",  "label": "Gold (USD)", "source": "yfinance", ...},

# New Korean tickers
{"symbol": "KRX_GOLD", "label": "금현물 (KRX)", "source": "krx_gold", ...},
{"symbol": "360750",   "label": "TIGER S&P500", "source": "pykrx", ...},
{"symbol": "133690",   "label": "TIGER 나스닥100", "source": "pykrx", ...},
```

Tickers are split into two groups:

```python
TICKERS_INTL: list[dict] = [...]   # yfinance — USD reference
TICKERS_KR: list[dict] = [...]     # pykrx + krx_gold — KRW investment
TICKERS: list[dict] = TICKERS_INTL + TICKERS_KR  # combined for iteration
```

Portfolio allocation (`base_weight`/`min_weight`) applies only to `TICKERS_KR`.

---

## 5. Fetcher details

### 5.1 pykrx (Korean ETFs)

```python
from pykrx import stock

def _download_pykrx(symbol: str, period: str = "3y") -> pd.DataFrame:
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=...)).strftime("%Y%m%d")
    df = stock.get_market_ohlcv_by_date(start_date, end_date, symbol)
    df = df.rename(columns={"종가": "Close", "시가": "Open", "고가": "High", "저가": "Low"})
    df.index = pd.to_datetime(df.index)
    return df
```

- Single call, no rate limits
- Column mapping: 종가→Close, 시가→Open, 고가→High, 저가→Low

### 5.2 KRX Gold API

```
Endpoint: https://data-dbg.krx.co.kr/svc/apis/gen/gold_bydd_trd
Method: GET
Header: AUTH_KEY: <key>
Params: {"basDd": "YYYYMMDD"}
Response: filter ISU_NM == "금 1Kg", use TDD_CLSPRC as close
```

- **One day per request** — must loop
- Rate limit: `time.sleep(0.2)` between calls
- Caching strategy:
  - First run: fetch from 2014-03-24 (or 300+ days back) → save to `data/gold_krx.csv`
  - Subsequent runs: load CSV, fetch only dates after last cached date, append
- Handle non-trading days (API returns empty) gracefully

### 5.3 yfinance (existing)

No changes to logic — just relocated to `src/fetchers/yfinance.py`.

---

## 6. Dashboard layout

Single HTML output (`out/combined_chart.html`):

```
┌─────────────────────────────────────────────────────┐
│  International (USD) — Reference                     │
│  [S&P 500 card] [NASDAQ 100 card] [Gold USD card]   │
├─────────────────────────────────────────────────────┤
│  Price/MA charts  |  RSI charts  |  Score charts     │
│  (3 columns — one per intl ticker)                   │
├─────────────────────────────────────────────────────┤
│  Korean (KRW) — Investment Portfolio                 │
│  [금현물 card] [TIGER S&P card] [TIGER 나스닥 card]    │
│  + Portfolio allocation summary                      │
├─────────────────────────────────────────────────────┤
│  Price/MA charts  |  RSI charts  |  Score charts     │
│  (3 columns — one per KR ticker)                     │
└─────────────────────────────────────────────────────┘
```

---

## 7. Backtest considerations

| Source | Max history | 5y backtest | 10y backtest |
|--------|-------------|-------------|--------------|
| yfinance (^GSPC, ^NDX, GC=F) | 20+ years | ✅ | ✅ |
| pykrx 360750 (TIGER S&P) | ~2020 listing | ✅ (barely) | ❌ skip |
| pykrx 133690 (TIGER 나스닥) | ~2010 listing | ✅ | ✅ |
| KRX Gold | 2014-03-24 | ✅ | ✅ (barely) |

Backtest gracefully skips periods with insufficient data (existing behavior).

Portfolio backtest runs separately for each group (intl vs KR) since they have different currencies and allocation pools.

---

## 8. Implementation order

1. **Restructure to `src/` package** — move existing files, update imports, verify tests pass
2. **Split `data.py`** into `models.py`, `indicators.py`, `allocation.py`, `fetchers/` — verify tests pass
3. **Add dependencies** — `pykrx`, `python-dotenv`, `requests`
4. **Add `source` field** to existing tickers, implement dispatcher in `fetchers/__init__.py`
5. **Implement `fetchers/pykrx.py`** — simplest new source, no rate limits
6. **Add Korean ETF tickers** to config, verify dashboard works
7. **Implement `fetchers/krx_gold.py`** with CSV caching
8. **Add KRX Gold ticker** to config, verify dashboard works
9. **Update dashboard layout** — two-group visual separation
10. **Update backtest** — separate portfolio backtests per group
11. **Adjust `base_weight`/`min_weight`** for KR tickers to sum to 1.0
12. **Restructure documentation** — create `docs/`, trim README

---

## 9. Files to update/create

### New files
- `src/__init__.py`
- `src/models.py`
- `src/indicators.py`
- `src/allocation.py`
- `src/fetchers/__init__.py`
- `src/fetchers/yfinance.py`
- `src/fetchers/pykrx.py`
- `src/fetchers/krx_gold.py`
- `.env` (git-ignored, contains `KRX_AUTH_KEY`)

### Moved files (content refactored)
- `main.py` → `src/main.py`
- `config.py` → `src/config.py`
- `chart.py` → `src/chart.py`
- `backtest.py` → `src/backtest.py`
- `data.py` → split into models/indicators/allocation/fetchers

### Updated files
- `pyproject.toml` — new deps, updated script entry
- `requirements.txt` — new deps
- `run.bat` — updated command
- `.gitignore` — add `.env`, `data/`
- `tests/` — update imports to `src.*`

---

## 10. Risk / watch-outs

- **KRX API reliability** — the gold API may be slow or have downtime. The caching layer mitigates this for repeat runs, but first-run will be slow (~5-10 min for full history).
- **pykrx breaking changes** — it's a community library. Pin version and test periodically.
- **Import restructure** — biggest risk of breakage. Do this first, run tests after each step.
- **Timezone differences** — KRX data is KST, yfinance is market-local. Shouldn't matter since we only use dates (not intraday), but worth noting.
- **Non-trading day alignment** — Korean and US markets have different holidays. Portfolio backtest for the KR group uses only KR trading days.

---

## 11. Gap check (reviewed against current codebase)

### Already handled by .gitignore
- `out/` is already ignored ✅
- `__pycache__/` already ignored ✅

### Needs to be added to .gitignore
- `.env`
- `data/`

### Backtest dataclass alignment
- `BacktestResult` and `PortfolioBacktestResult` now carry `equity_curve` and `monthly_investments` fields (added in the backtest dashboard work). These need to be moved to `models.py` during the restructure.
- `BacktestComparison` and `PortfolioComparison` also move to `models.py`.

### Chart module alignment
- `chart.py` currently imports from `data.py` (`TickerData`, `Allocation`). After restructure, it imports from `src.models` instead.
- `generate_backtest_chart()` (recently added) imports `BacktestComparison` and `PortfolioComparison` — these also move to `models.py`.

### Backtest imports from data.py
- `backtest.py` currently imports `_calc_rsi` and `_compute_score_series` from `data.py`. After restructure, these come from `src.indicators`.
- `backtest.py` imports `score_to_multiplier` from `data.py`. After restructure, this comes from `src.allocation`.

### DOWNLOAD_PERIOD per source
- yfinance uses `DOWNLOAD_PERIOD = "3y"` as a string. pykrx needs explicit start/end dates. KRX Gold fetches all available history. The `DOWNLOAD_PERIOD` config value only applies to yfinance — the other fetchers compute their own date ranges. This is fine but should be documented in `config.py`.

### Estimated data handling
- The "fill incomplete rows with mean of prev close + live price" logic currently lives in `fetch_ticker()`. This is yfinance-specific (partial trading day data). pykrx and KRX Gold won't have this issue since they only return completed trading days. The logic stays in `fetchers/yfinance.py`.

### International tickers — allocation
- The plan says "Portfolio allocation applies only to Korean tickers." The existing code currently computes allocation for the international tickers. After the change, `compute_allocation()` should only receive `TICKERS_KR`. The international group shows scores and suggestions but no allocation cards.
- The existing `BASE_AMOUNT` per-ticker suggestion (₩500,000 × multiplier) can still display for international tickers as a reference, but the portfolio-level allocation (₩1,000,000 budget split) is KR-only.

### Test coverage for new fetchers
- Need new test files: `tests/test_fetchers_pykrx.py`, `tests/test_fetchers_krx_gold.py`
- These should mock the network calls and verify DataFrame output format
- Existing scoring/backtest tests remain unchanged (they test pure math)
