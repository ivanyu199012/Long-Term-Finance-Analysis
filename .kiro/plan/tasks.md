# Implementation Tasks

Reference: `.kiro/plan/korean_data_addition.md`

---

## Process

1. Complete one task at a time, then stop and wait for user review
2. If a gap or ambiguity is found during implementation, ask the user before proceeding
3. Update this file as implementation progresses — mark tasks as ✅ done, note any deviations or discoveries
4. Each task has a **Verify** step that must pass before marking complete

**Status legend:** ⬜ Not started | 🔄 In progress | ✅ Done | ⏭️ Skipped

---

## Phase 1: Project Restructure ✅

The restructure must happen first — it's easier to add new features into a clean structure.

### Task 1.1: Create `src/` package skeleton ✅

- Create `src/__init__.py` (empty or minimal)
- Create `src/fetchers/__init__.py` (empty placeholder)
- **Verify:** directories exist, Python can import `src` ✅

### Task 1.2: Extract `src/models.py` ✅

Move all dataclasses from `data.py` and `backtest.py` into `src/models.py`:
- `BuyScore`
- `TickerData`
- `Allocation`
- `BacktestResult` (with `equity_curve`, `monthly_investments` fields)
- `BacktestComparison`
- `PortfolioBacktestResult` (with `equity_curve` field)
- `PortfolioComparison`

No logic — just dataclass definitions and their imports (`pandas`, `__future__.annotations`).

- **Verify:** `src/models.py` imports cleanly, no circular deps ✅

### Task 1.3: Extract `src/indicators.py` ✅

Move pure math functions from `data.py`:
- `_calc_rsi(series, period)` → make public as `calc_rsi`
- `_calc_drawdown(close)` → make public as `calc_drawdown`
- `_compute_buy_score(...)` → make public as `compute_buy_score`
- `_compute_score_series(...)` → make public as `compute_score_series`
- `_score_to_suggestion(score, base_amount)` → make public as `score_to_suggestion` (formats suggestion string; depends on `score_to_multiplier` from allocation, so import it)

All parameters passed in (no imports from config inside the functions). Import `BuyScore` from `src.models`.

- **Verify:** functions work standalone with explicit params ✅

> Note: Also created a minimal `src/allocation.py` with `score_to_multiplier` since `score_to_suggestion` imports it. Task 1.4 will flesh it out with `compute_allocation`.

### Task 1.4: Extract `src/allocation.py` ✅

Move from `data.py`:
- `score_to_multiplier(score)` 
- `compute_allocation(tickers)`

Import `Allocation` from `src.models`, config values from `src.config`.

- **Verify:** `backtest.py` and `main.py` can both import from here without circular deps ✅

> Note: `compute_allocation` accepts optional `ticker_configs` and `monthly_budget` params for explicit injection, falling back to config imports when not provided. Config imports currently reference root-level `config.py` — will be updated to `src.config` in Task 1.5.

### Task 1.5: Move `config.py` → `src/config.py` ✅

- Move file contents as-is
- Add `import os` and `from dotenv import load_dotenv` + `load_dotenv()` call
- Add `KRX_AUTH_KEY = os.environ.get("KRX_AUTH_KEY", "")`
- Add `BACKTEST_OUTPUT_FILE` (already exists in current config)
- Add comment noting `DOWNLOAD_PERIOD` applies to yfinance only
- Add `"source": "yfinance"` to each existing ticker dict
- Split `TICKERS` into `TICKERS_INTL` and `TICKERS_KR` (KR is empty for now)
- Keep `TICKERS = TICKERS_INTL + TICKERS_KR` for backward compat

- **Verify:** existing code still works with the combined `TICKERS` list ✅

> Note: Added `python-dotenv>=1.0` to `pyproject.toml` and ran `uv sync` (pulled forward from Task 1.12 since it's required for the import). Root-level `config.py` is still in place for existing code — will be removed in Task 1.12.

### Task 1.6: Move `fetchers/yfinance.py` ✅

Extract from `data.py`:
- `_download(symbol)` → `download(symbol)`
- `_get_live_price(symbol, df)` → `get_live_price(symbol, df)`
- The estimated-data fill logic (NaN handling with mean of prev close + live price)

These become public functions in `src/fetchers/yfinance.py`.

- **Verify:** yfinance fetcher works in isolation ✅

### Task 1.7: Create `src/fetchers/__init__.py` dispatcher ✅

Implement `fetch_ticker(symbol, label, source="yfinance", **kwargs) -> TickerData`:
- Routes to `fetchers.yfinance` / `fetchers.pykrx` / `fetchers.krx_gold` based on `source`
- After fetching the DataFrame, calls indicator functions from `src.indicators`
- Assembles and returns `TickerData`

This replaces the old `fetch_ticker()` from `data.py`.

- **Verify:** dashboard mode works end-to-end with yfinance tickers ✅

> Note: pykrx and krx_gold branches raise `NotImplementedError` — placeholders for Phase 2 & 3.

### Task 1.8: Move `backtest.py` → `src/backtest.py` ✅

- Update imports: `_calc_rsi` → `src.indicators.calc_rsi`, `_compute_score_series` → `src.indicators.compute_score_series`, `score_to_multiplier` → `src.allocation.score_to_multiplier`
- Dataclasses already in `src.models` — import from there
- Keep `print_backtest` and `print_portfolio_backtest` here (terminal output)
- Keep `run_backtest`, `run_portfolio_backtest`, `_run_strategy` here

- **Verify:** backtest tests pass ✅

### Task 1.9: Move `chart.py` → `src/chart.py` ✅

- Update imports: `TickerData`, `Allocation` → from `src.models`
- `BacktestComparison`, `PortfolioComparison` → from `src.models`
- Config imports → from `src.config`

- **Verify:** no import errors ✅

### Task 1.10: Move `main.py` → `src/main.py` ✅

- Update all imports to use `src.*` paths
- Dashboard calls `fetch_ticker` from `src.fetchers`
- Allocation calls from `src.allocation`
- Chart calls from `src.chart`
- Backtest calls from `src.backtest`

- **Verify:** `uv run python -m src.main` works ✅ (import check passed; full run requires network)

### Task 1.11: Update `tests/` imports ✅

- All test files: change `from data import ...` → `from src.indicators import ...` etc.
- `from backtest import ...` → `from src.backtest import ...`
- `from data import score_to_multiplier` → `from src.allocation import score_to_multiplier`
- `from data import _compute_buy_score` → `from src.indicators import compute_buy_score` (now public)
- `from backtest import _run_strategy` → `from src.backtest import _run_strategy` (stays private but importable for tests)
- `from backtest import BacktestResult` → `from src.models import BacktestResult`

- **Verify:** `uv run pytest` — all 26 tests pass ✅

### Task 1.12: Update project files ✅

- `pyproject.toml`: update `[project.scripts]` to `finanalysis = "src.main:main"`
- `requirements.txt`: add `python-dotenv>=1.0`
- `run.bat`: change to `uv run python -m src.main`
- `.gitignore`: add `.env` and `data/`
- Delete old root-level `data.py`, `config.py`, `chart.py`, `backtest.py`, `main.py` (now in `src/`)
- Fix: `src/allocation.py` had stale `from config import` → updated to `from src.config import`
- Fix: backtest dashboard card layout — grouped by period (row 1: 5y tickers, row 2: 10y tickers, row 3: portfolio cards)

- **Verify:** `uv run python -m src.main` works, `uv run pytest` passes ✅

---

## Phase 2: Add Korean ETF Data Source (pykrx) ✅

### Task 2.1: Add `pykrx` and `requests` dependencies ✅

- Add `pykrx>=1.0` to `pyproject.toml` `[project.dependencies]`
- Add `requests>=2.28` to `pyproject.toml` `[project.dependencies]` (explicit dep for KRX Gold fetcher — may already be transitive via yfinance but should be declared)
- Add `setuptools<81` (required by pykrx for `pkg_resources`)
- Add all to `requirements.txt`
- Run `uv sync` to install

- **Verify:** `from pykrx import stock` works, `import requests` works ✅

> Note: pykrx depends on `pkg_resources` which was removed in setuptools 82+. Pinned `setuptools<81` to keep it working. pykrx emits a deprecation warning — harmless.

### Task 2.2: Implement `src/fetchers/pykrx.py` ✅

Create the module with:
- `download_pykrx(symbol: str, period_days: int) -> pd.DataFrame`
  - Compute start/end dates from `period_days`
  - Call `stock.get_market_ohlcv_by_date(start, end, symbol)`
  - Rename columns: 종가→Close, 시가→Open, 고가→High, 저가→Low
  - Ensure DatetimeIndex
  - Return DataFrame with same shape as yfinance output
- `get_live_price_pykrx(symbol: str) -> float`
  - Fetch today's data, return latest close

- **Verify:** manual test with ticker "133690" ✅ (23 rows, correct columns, live price ₩177,990)

### Task 2.3: Register pykrx in dispatcher ✅

Update `src/fetchers/__init__.py`:
- Add `elif source == "pykrx":` branch
- Call `download_pykrx(symbol, ...)`
- Skip estimated-data logic (not needed for pykrx)

- **Verify:** `fetch_ticker("133690", "TIGER 나스닥100", source="pykrx", ...)` returns valid `TickerData` ✅ (Price: ₩177,990, Score: 2.4)

### Task 2.4: Add Korean ETF tickers to config ✅

Add to `TICKERS_KR` in `src/config.py`:
```python
{"symbol": "360750", "label": "TIGER S&P500", "source": "pykrx", 
 "ma_weights": {50:0.5, 100:1.5, 200:5.0}, "ma_fade_thresholds": {50:0.07, 100:0.10, 200:0.15},
 "drawdown_full_pct": 0.25, "base_weight": 0.45, "min_weight": 0.30},
{"symbol": "133690", "label": "TIGER 나스닥100", "source": "pykrx",
 "ma_weights": {50:1.0, 100:2.0, 200:4.0}, "ma_fade_thresholds": {50:0.10, 100:0.14, 200:0.20},
 "drawdown_full_pct": 0.35, "base_weight": 0.25, "min_weight": 0.10},
```

- **Verify:** dashboard fetches and scores both ETFs correctly ✅ (TIGER S&P500: 2.9, TIGER 나스닥100: 2.4)

> Note: Allocation currently spans all 5 tickers (intl + KR). Will be split to KR-only in Task 4.3.

### Task 2.5: Write tests for pykrx fetcher ✅

Create `tests/test_fetchers_pykrx.py`:
- Mock `stock.get_market_ohlcv_by_date` to return synthetic DataFrame
- Verify column renaming
- Verify DatetimeIndex
- Verify output shape matches expected contract

- **Verify:** `uv run pytest tests/test_fetchers_pykrx.py` passes ✅ (7 tests)

---

## Phase 3: Add KRX Gold Data Source ⬜

### Task 3.1: Implement `src/fetchers/krx_gold.py` ✅

Create the module with:
- `download_krx_gold(auth_key: str) -> pd.DataFrame`
  - Check for existing cache at `data/gold_krx.csv`
  - If cache exists: load it, determine last date, fetch only new dates
  - If no cache: fetch from 2014-03-24 (or configurable start) to today
  - Loop day-by-day with `time.sleep(0.2)` between requests
  - Filter response for `ISU_NM == "금 1Kg"`
  - Extract `BAS_DD` → date, `TDD_CLSPRC` → Close
  - Skip non-trading days (empty response)
  - Save updated cache to `data/gold_krx.csv`
  - Return DataFrame with DatetimeIndex and `Close` column
- `get_live_price_krx_gold(auth_key: str) -> float`
  - Fetch today's date, return close price

- **Verify:** manual test with real API key (or mock) ✅ (imports clean, tests pass)

### Task 3.2: Register krx_gold in dispatcher ✅

Update `src/fetchers/__init__.py`:
- Add `elif source == "krx_gold":` branch
- Pass `KRX_AUTH_KEY` from config
- Skip estimated-data logic

- **Verify:** `fetch_ticker("KRX_GOLD", "금현물 (KRX)", source="krx_gold", ...)` returns valid `TickerData` ✅ (Price: ₩217,060, Score: 10.0, 267 rows, MA200 computed)

> Note: Fixed case-sensitivity bug in product name filter (`1Kg` vs `1kg`). Added early-exit after 30 consecutive empty days to avoid long waits when system date is ahead of API data.

### Task 3.3: Add KRX Gold ticker to config ✅

Add to `TICKERS_KR` in `src/config.py`:
```python
{"symbol": "KRX_GOLD", "label": "금현물 (KRX)", "source": "krx_gold",
 "ma_weights": {50: 1.75, 100: 2.5, 200: 2.75},
 "ma_fade_thresholds": {50: 0.05, 100: 0.08, 200: 0.12},
 "drawdown_full_pct": 0.20,
 "base_weight": 0.30, "min_weight": 0.20},
```

- **Verify:** dashboard fetches and scores KRX Gold correctly ✅ (Total: 6 tickers, KR: 3)

### Task 3.4: Create `.env` template ✅

- Create `.env.example` (committed) with `KRX_AUTH_KEY=your_key_here`
- Create `.env` (git-ignored) with actual key for local use

- **Verify:** `load_dotenv()` picks up the key ✅

### Task 3.5: Write tests for KRX Gold fetcher

Create `tests/test_fetchers_krx_gold.py`:
- Mock HTTP requests to KRX API
- Verify filtering for "금 1Kg"
- Verify date parsing and DataFrame output
- Verify caching logic (reads existing CSV, appends new data)
- Verify rate-limiting (sleep called between requests)

- **Verify:** `uv run pytest tests/test_fetchers_krx_gold.py` passes

---

## Phase 4: Dashboard Layout Update ⬜

### Task 4.1: Update `src/chart.py` — two-group layout

Modify `generate_chart()` to accept two ticker groups:
- Render "International (USD) — Reference" section header + cards + charts
- Render "Korean (KRW) — Investment Portfolio" section header + cards + charts
- Portfolio allocation cards only appear in the Korean section
- Each section has its own Plotly subplot grid (3 rows × N cols)

- **Verify:** HTML output shows two visually distinct sections

### Task 4.2: Update `src/main.py` — dashboard orchestration

- Fetch `TICKERS_INTL` and `TICKERS_KR` separately
- Compute allocation only for `TICKERS_KR`
- Pass both groups to `generate_chart()`
- Terminal output shows both groups with a separator

- **Verify:** full dashboard runs with all 6 tickers

### Task 4.3: Update allocation scope

- `compute_allocation()` receives only KR tickers
- International tickers still show per-ticker score/suggestion text (using `BASE_AMOUNT × multiplier`) but no portfolio allocation percentage
- `MONTHLY_BUDGET` split applies to KR group only

- **Verify:** allocation percentages for KR tickers sum to 100%

---

## Phase 5: Backtest Update ⬜

### Task 5.1: Separate backtest by group

Update `src/main.py` `_run_backtest()`:
- Run per-ticker backtests for all tickers (both groups)
- Run portfolio backtest separately for each group:
  - International portfolio backtest (USD)
  - Korean portfolio backtest (KRW)
- Generate backtest chart with both groups

- **Verify:** backtest runs, skips tickers with insufficient data

### Task 5.2: Update backtest chart for two groups

Update `generate_backtest_chart()`:
- Accept comparisons grouped by intl/KR
- Render separate sections in the HTML
- Portfolio equity curves per group

- **Verify:** backtest HTML shows both groups clearly

---

## Phase 6: Finalization ⬜

### Task 6.1: Tune `base_weight` / `min_weight` for KR tickers

Set weights for the Korean group so they sum to 1.0:
- 금현물 (KRX): TBD (e.g. 0.30 base, 0.20 min)
- TIGER S&P500: TBD (e.g. 0.45 base, 0.30 min)
- TIGER 나스닥100: TBD (e.g. 0.25 base, 0.10 min)

Confirm `min_weight` values don't sum to more than 1.0.

- **Verify:** allocation math works, no negative remainders

### Task 6.2: Restructure documentation

Replace the monolithic README with a focused entry point + detailed docs:

**Create `docs/` directory:**
- `docs/scoring.md` — score methodology, per-ticker MA weights/thresholds, suggestion tiers, multiplier table
- `docs/backtest.md` — backtest modes (per-ticker + portfolio), strategies (flat/raw/normalized), how to interpret results
- `docs/korean-data-sources.md` — KRX Gold API setup (auth key, rate limits, caching), pykrx usage, `.env` configuration
- `docs/configuration.md` — all `config.py` options explained (tickers, weights, periods, budgets, chart styles)

**Trim `README.md` to:**
- Project one-liner + what it does
- Quick start (install, run dashboard, run backtest)
- Brief feature list
- Project structure overview (just the `src/` tree)
- Links to `docs/*.md` for detailed topics
- Prerequisites + output section

Move the scoring tables, backtest explanation, estimated data handling, and detailed config docs out of README into the appropriate `docs/` file.

- **Verify:** README is under ~80 lines, all detailed info is findable in `docs/`

### Task 6.3: Final integration test

- Run `uv run python -m src.main` — dashboard with all 6 tickers
- Run `uv run python -m src.main --backtest` — backtest for all tickers
- Run `uv run pytest` — all tests pass
- Verify HTML outputs render correctly in browser

### Task 6.4: Final verification of old file cleanup

- Confirm Task 1.12's deletion of root-level files is complete (no stale `data.py`, `config.py`, `chart.py`, `backtest.py`, `main.py` at root)
- Grep for any remaining imports referencing old paths (e.g. `from data import`, `from config import` without `src.` prefix)
- Verify `uv run python -m src.main` and `uv run pytest` still pass

- **Verify:** no orphan files, no broken imports

---

## Task Dependency Graph

```
Phase 1 (restructure) ─── all tasks sequential (1.1 → 1.2 → ... → 1.12)
    │
    ├── Phase 2 (pykrx) ─── 2.1 → 2.2 → 2.3 → 2.4 → 2.5
    │
    ├── Phase 3 (KRX Gold) ─── 3.1 → 3.2 → 3.3 → 3.4 → 3.5
    │       (can run in parallel with Phase 2)
    │
    └── Phase 4 (dashboard layout) ─── 4.1 → 4.2 → 4.3
            (depends on Phase 2 + 3 being done)
            │
            └── Phase 5 (backtest update) ─── 5.1 → 5.2
                    │
                    └── Phase 6 (finalization) ─── 6.1 → 6.2 → 6.3 → 6.4
```

---

## Summary

| Phase | Tasks | Estimated effort |
|-------|-------|-----------------|
| 1. Restructure | 12 tasks | Medium-high (most refactoring risk) |
| 2. pykrx | 5 tasks | Low (simple API) |
| 3. KRX Gold | 5 tasks | Medium (caching, rate limits) |
| 4. Dashboard layout | 3 tasks | Medium (chart refactoring) |
| 5. Backtest update | 2 tasks | Low-medium |
| 6. Finalization | 4 tasks | Low |
| **Total** | **31 tasks** | |
