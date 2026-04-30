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

    tickers = []
    for t in TICKERS:
        print(f"[{t['label']}] Downloading data for {t['symbol']}...")
        td = fetch_ticker(**t)
        tickers.append(td)

        bs = td.buy_score
        rsi_val = float(td.rsi.iloc[-1])
        ma_max = sum(td.ma_weights.values())
        print(f"  Weights — MA: {ma_max:.1f}  RSI: {RSI_MAX_SCORE:.1f}  DD: {DRAWDOWN_MAX_SCORE:.1f}  (DD full at {td.drawdown_full_pct:.0%})")
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

    print("Generating interactive chart...")
    allocations = compute_allocation(tickers)
    path = generate_chart(tickers, allocations=allocations, output_path=OUTPUT_FILE)
    print(f"Chart saved: {path}")
    print()

    # Print allocation recommendation
    print("=" * 60)
    print(f"  Monthly Allocation (₩{MONTHLY_BUDGET:,.0f} budget)")
    print("=" * 60)
    for a in allocations:
        print(f"  {a.label:<15} {a.weight_pct:>5.1f}%  →  ₩{a.amount:>12,.0f}")
    print()

    _open_file(path)
    print("Done.")


def _run_backtest() -> None:
    """Download data and run backtest for each ticker at 5y and 10y."""
    import yfinance as yf

    from src.backtest import print_backtest, print_portfolio_backtest, run_backtest, run_portfolio_backtest
    from src.chart import generate_backtest_chart

    print("=" * 60)
    print("  FinAnalysis — Backtest: Flat DCA vs Score-based DCA")
    print("=" * 60)
    print()

    all_comparisons = []

    for t in TICKERS:
        symbol = t["symbol"]
        label = t["label"]
        ma_weights = t["ma_weights"]
        ma_fade = t["ma_fade_thresholds"]
        dd_full = t["drawdown_full_pct"]

        for period in ("5y", "10y"):
            download_period = {"5y": "7y", "10y": "12y"}[period]
            print(f"[{label}] Downloading {download_period} data for {symbol} ({period} backtest)...")
            df = yf.download(symbol, period=download_period, auto_adjust=True)
            df.columns = df.columns.get_level_values(0)
            close = df["Close"].dropna()

            if len(close) < 252:
                print(f"  ⚠ Not enough data for {period}, skipping.")
                continue

            result = run_backtest(close, ma_weights, ma_fade, dd_full, label, period)
            all_comparisons.append(result)
            print_backtest(result)

    # ── Portfolio-level backtest ──
    all_portfolio = []
    for period in ("5y", "10y"):
        download_period = {"5y": "7y", "10y": "12y"}[period]
        asset_data = []
        for t in TICKERS:
            print(f"[{t['label']}] Downloading {download_period} data for {t['symbol']} (portfolio {period})...")
            df = yf.download(t["symbol"], period=download_period, auto_adjust=True)
            df.columns = df.columns.get_level_values(0)
            close = df["Close"].dropna()
            if len(close) < 252:
                print(f"  ⚠ Not enough data for {period}, skipping.")
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

        if len(asset_data) == len(TICKERS):
            portfolio_result = run_portfolio_backtest(asset_data, period)
            all_portfolio.append(portfolio_result)
            print_portfolio_backtest(portfolio_result)

    # ── Generate HTML dashboard ──
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
