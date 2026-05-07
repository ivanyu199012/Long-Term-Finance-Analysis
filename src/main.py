"""FinAnalysis — entry point.

Downloads market data, generates a combined technical-analysis chart,
and opens the resulting HTML file.  Also supports a ``--backtest`` mode
that compares flat DCA vs score-based DCA over 5-year and 10-year periods.

Usage::

    python -m src.main              # dashboard mode (default)
    python -m src.main --backtest   # run backtest comparison
"""

from __future__ import annotations

import subprocess
import sys

from src.allocation import compute_allocation
from src.chart import generate_chart
from src.config import (
    BACKTEST_OUTPUT_FILE,
    DRAWDOWN_MAX_SCORE,
    MONTHLY_BUDGET,
    OUTPUT_FILE,
    RSI_MAX_SCORE,
    TICKERS,
    TICKERS_INTL,
    TICKERS_KR,
)
from src.fetchers import fetch_ticker


def main() -> None:
    """Dispatch to dashboard or backtest mode based on CLI args."""
    if "--backtest" in sys.argv:
        _run_backtest()
    else:
        _run_dashboard()


def _run_dashboard() -> None:
    """Fetch data for every configured ticker, render the chart, and open it."""
    print("=" * 60)
    print("  FinAnalysis — Technical Analysis Dashboard")
    print("=" * 60)
    print()

    def _fetch_and_print(ticker_configs: list[dict], group_label: str) -> list:
        """Fetch tickers and print summary for a group."""
        results = []
        if not ticker_configs:
            return results
        print(f"── {group_label} ──")
        print()
        for t in ticker_configs:
            print(f"[{t['label']}] Downloading data for {t['symbol']}...")
            td = fetch_ticker(**t)
            results.append(td)

            bs = td.buy_score
            rsi_val = float(td.rsi.iloc[-1])
            ma_max = sum(td.ma_weights.values())
            print(f"  Weights — MA: {ma_max:.1f}  RSI: {RSI_MAX_SCORE:.1f}  DD: {DRAWDOWN_MAX_SCORE:.1f}  (DD full at {td.drawdown_full_pct:.0%})")

            # Price display: show live/close for Korean tickers
            if td.is_live_price and td.close_price is not None:
                live_label = f"({td.live_price_time})" if td.live_price_time else "(live)"
                close_label = f"({td.close_price_date})" if td.close_price_date else ""
                print(f"  Price:  {td.current_price:>12,.2f} {live_label} | Close {close_label}: {td.close_price:,.2f}")
            elif td.live_price_warning:
                print(f"  Price:  {td.current_price:>12,.2f}")
                print(f"  \033[33m⚠ {td.live_price_warning}\033[0m")
            else:
                print(f"  Price:  {td.current_price:>12,.2f}")

            for w, ma in td.moving_averages.items():
                pct = td.ma_pct_diffs[w]
                above_below = "above" if pct > 0 else "below"
                print(f"  MA{w}:  {ma:>12,.2f}  ({abs(pct):.2f}% {above_below})")
            print(f"  RSI:    {rsi_val:>12.1f}")
            print(f"  DD:     {min(bs.current_drawdown, 0):>11.1%}  (max: {bs.max_drawdown:.1%})")
            print(f"  Score:  {bs.score:.1f}/10  (MA: {bs.ma_score:.1f}/{ma_max:.1f}, RSI: {bs.rsi_score:.1f}/{RSI_MAX_SCORE:.1f}, DD: {bs.drawdown_score:.1f}/{DRAWDOWN_MAX_SCORE:.1f})")
            print(f"  → {bs.suggestion}")
            if td.estimated_dates:
                print(f"  \033[33m⚠ Estimated data for: {', '.join(td.estimated_dates)} (mean of prev close & live price)\033[0m")
            print()
        return results

    # Fetch both groups
    tickers_intl = _fetch_and_print(TICKERS_INTL, "International (USD)")
    tickers_kr = _fetch_and_print(TICKERS_KR, "Korean (KRW)")

    # Compute allocation for KR group only
    allocations = compute_allocation(tickers_kr, ticker_configs=TICKERS_KR) if tickers_kr else None

    # Generate chart with two-group tabbed layout
    print("Generating interactive chart...")
    path = generate_chart(
        tickers=tickers_intl + tickers_kr,  # legacy fallback
        allocations=allocations,
        output_path=OUTPUT_FILE,
        tickers_intl=tickers_intl,
        tickers_kr=tickers_kr,
    )
    print(f"Chart saved: {path}")
    print()

    # Print allocation recommendation (KR only)
    if allocations:
        print("=" * 60)
        print(f"  Monthly Allocation — Korean Portfolio (₩{MONTHLY_BUDGET:,.0f} budget)")
        print("=" * 60)
        for a in allocations:
            print(f"  {a.label:<20} {a.weight_pct:>5.1f}%  →  ₩{a.amount:>12,.0f}")
        print()

    _open_file(path)
    print("Done.")


def _run_backtest() -> None:
    """Download data and run backtest for each ticker at 5y and 10y."""
    import yfinance as yf

    from src.backtest import print_backtest, print_portfolio_backtest, run_backtest, run_portfolio_backtest
    from src.chart import generate_backtest_chart
    from src.fetchers.krx_gold import download_krx_gold
    from src.fetchers.pykrx import download_pykrx

    print("=" * 60)
    print("  FinAnalysis — Backtest: Flat DCA vs Score-based DCA")
    print("=" * 60)
    print()

    all_comparisons_intl = []
    all_comparisons_kr = []

    def _get_close_series(t: dict, period: str) -> "pd.Series | None":
        """Get close price series for a ticker, using the appropriate source."""
        import pandas as pd

        source = t.get("source", "yfinance")
        symbol = t["symbol"]
        label = t["label"]

        if source == "yfinance":
            download_period = {"5y": "7y", "10y": "12y"}[period]
            print(f"[{label}] Downloading {download_period} data for {symbol} ({period} backtest)...")
            df = yf.download(symbol, period=download_period, auto_adjust=True)
            df.columns = df.columns.get_level_values(0)
            close = df["Close"].dropna()
        elif source == "pykrx":
            period_days = {"5y": 2600, "10y": 4000}[period]
            print(f"[{label}] Downloading {period_days}d data for {symbol} ({period} backtest)...")
            df = download_pykrx(symbol, period_days=period_days)
            close = df["Close"].dropna()
        elif source == "krx_gold":
            from src.config import KRX_AUTH_KEY
            period_days = {"5y": 2600, "10y": 4000}[period]
            print(f"[{label}] Loading KRX Gold data ({period} backtest)...")
            df = download_krx_gold(KRX_AUTH_KEY, period_days=period_days)
            close = df["Close"].dropna()
        else:
            print(f"  ⚠ Unknown source '{source}' for {label}, skipping.")
            return None

        if len(close) < 252:
            print(f"  ⚠ Not enough data for {period} ({len(close)} days), skipping.")
            return None
        return close

    # ── Per-ticker backtests ──
    for group_label, ticker_list, results_list in [
        ("International (USD)", TICKERS_INTL, all_comparisons_intl),
        ("Korean (KRW)", TICKERS_KR, all_comparisons_kr),
    ]:
        if not ticker_list:
            continue
        print(f"── {group_label} ──")
        print()
        for t in ticker_list:
            for period in ("5y", "10y"):
                close = _get_close_series(t, period)
                if close is None:
                    continue
                result = run_backtest(
                    close, t["ma_weights"], t["ma_fade_thresholds"],
                    t["drawdown_full_pct"], t["label"], period,
                )
                results_list.append(result)
                print_backtest(result)

    # ── Portfolio-level backtests (separate per group) ──
    all_portfolio_intl = []
    all_portfolio_kr = []

    for group_label, ticker_list, portfolio_list in [
        ("International", TICKERS_INTL, all_portfolio_intl),
        ("Korean", TICKERS_KR, all_portfolio_kr),
    ]:
        if not ticker_list:
            continue
        for period in ("5y", "10y"):
            asset_data = []
            for t in ticker_list:
                close = _get_close_series(t, period)
                if close is None:
                    continue
                asset_data.append({
                    "label": t["label"],
                    "close": close,
                    "ma_weights": t["ma_weights"],
                    "ma_fade_thresholds": t["ma_fade_thresholds"],
                    "drawdown_full_pct": t["drawdown_full_pct"],
                    "base_weight": t["base_weight"],
                    "min_weight": t["min_weight"],
                })

            if len(asset_data) == len(ticker_list):
                portfolio_result = run_portfolio_backtest(asset_data, period)
                portfolio_list.append(portfolio_result)
                print_portfolio_backtest(portfolio_result)

    # ── Generate HTML dashboard ──
    all_comparisons = all_comparisons_intl + all_comparisons_kr
    all_portfolio = all_portfolio_intl + all_portfolio_kr
    if all_comparisons:
        print("Generating backtest dashboard...")
        path = generate_backtest_chart(
            all_comparisons,
            portfolio_comparisons=all_portfolio or None,
            output_path=BACKTEST_OUTPUT_FILE,
        )
        print(f"Backtest chart saved: {path}")
        _open_file(path)

    print("Done.")


def _open_file(path: str) -> None:
    """Open *path* with the OS default viewer (Windows-only for now)."""
    if sys.platform == "win32":
        subprocess.Popen(["start", "", path], shell=True)  # noqa: S603
    else:
        print(f"Open the file manually: {path}")


if __name__ == "__main__":
    main()
