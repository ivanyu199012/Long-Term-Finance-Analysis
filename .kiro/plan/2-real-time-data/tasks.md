# Implementation Tasks: Real-Time Price

Reference: `.kiro/plan/2-real-time-data/plan.md`

---

## Process

1. Complete one task at a time, then stop and wait for user review
2. If a gap or ambiguity is found during implementation, ask the user before proceeding
3. Update this file as implementation progresses — mark tasks as ✅ done, note any deviations
4. Each task has a **Verify** step that must pass before marking complete

**Status legend:** ⬜ Not started | 🔄 In progress | ✅ Done | ⏭️ Skipped

---

### Task 1: Implement Naver scraping ✅

- Add `beautifulsoup4>=4.12` to `pyproject.toml` and `requirements.txt`, run `uv sync`
- Create `src/fetchers/naver.py` with `get_realtime_price_etf(ticker_code)` and `get_realtime_price_gold()`
- Both return `float | None` — None on any failure, with warning printed to stderr
- Error handling: timeout=5s, catch all exceptions, never crash
- Write `tests/test_fetchers_naver.py` with mocked HTML responses

- **Verify:** manual test returns valid prices ✅ (ETF: ₩26,340 / ₩180,055, Gold: ₩216,412.93); 7 tests pass

> Note: Gold price from Naver is the international reference in KRW/g (Shinhan Bank rate), not the exact KRX spot price. They track closely but may differ by 1-2%.

### Task 2: Integrate into fetcher + model ✅

- Add `close_price`, `is_live_price`, `live_price_warning` fields to `TickerData`
- Update `_fetch_pykrx` and `_fetch_krx_gold` in dispatcher to try Naver first, fall back to close
- Populate new TickerData fields accordingly
- International tickers unaffected (`is_live_price=False`)

- **Verify:** `uv run python -m src.main` runs; Korean tickers use live price when available; all tests pass ✅

### Task 3: Update terminal + dashboard display ✅

- Terminal: show `Price: XX,XXX (live) | Close: XX,XXX` for Korean tickers; show warning on fallback
- Dashboard cards: show both "Live" and "Close" prices; show red warning when fallback
- International tickers: no change

- **Verify:** terminal and HTML output show live/close distinction; fallback warning appears when scraping fails ✅

### Task 4: Final verification ✅

- Run full dashboard with all 6 tickers ✅
- Run `uv run pytest` — all 52 tests pass ✅
- Korean tickers show live price with timestamp (MM/DD HH:MM) and close price with date (MM/DD)
- International tickers unaffected

- **Verify:** all scenarios work correctly ✅

---

## Summary

| Task | Estimated effort |
|------|-----------------|
| 1. Naver scraping | Medium |
| 2. Integration | Low |
| 3. Display | Low-medium |
| 4. Verification | Low |
| **Total** | **4 tasks** |
