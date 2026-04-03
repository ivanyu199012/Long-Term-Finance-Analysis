"""FinAnalysis — entry point.

Downloads market data, generates a combined technical-analysis chart,
and opens the resulting image.

Usage::

    python main.py
"""

from __future__ import annotations

import subprocess
import sys

from chart import generate_chart
from config import DRAWDOWN_FULL_PCT, DRAWDOWN_MAX_SCORE, OUTPUT_FILE, RSI_MAX_SCORE, TICKERS
from data import fetch_ticker


def main() -> None:
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
        print(f"  Weights — MA: {ma_max:.1f}  RSI: {RSI_MAX_SCORE:.1f}  DD: {DRAWDOWN_MAX_SCORE:.1f}  (DD full at {DRAWDOWN_FULL_PCT:.0%})")
        print(f"  Price:  {td.current_price:>12,.2f}")
        for w, ma in td.moving_averages.items():
            pct = td.ma_pct_diffs[w]
            above_below = "above" if pct > 0 else "below"
            print(f"  MA{w}:  {ma:>12,.2f}  ({abs(pct):.2f}% {above_below})")
        print(f"  RSI:    {rsi_val:>12.1f}")
        print(f"  DD:     {min(bs.current_drawdown, 0):>11.1%}  (max: {bs.max_drawdown:.1%})")
        print(f"  Score:  {bs.score:.1f}/10  (MA: {bs.ma_score:.1f}/{ma_max:.1f}, RSI: {bs.rsi_score:.1f}/{RSI_MAX_SCORE:.1f}, DD: {bs.drawdown_score:.1f}/{DRAWDOWN_MAX_SCORE:.1f})")
        print(f"  → {bs.suggestion}")
        print()

    print("Generating interactive chart...")
    path = generate_chart(tickers, output_path=OUTPUT_FILE)
    print(f"Chart saved: {path}")
    print()

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
