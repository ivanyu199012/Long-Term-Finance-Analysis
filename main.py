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
from config import OUTPUT_FILE, TICKERS
from data import fetch_ticker


def main() -> None:
    """Fetch data for every configured ticker, render the chart, and open it."""
    tickers = [fetch_ticker(**t) for t in TICKERS]
    path = generate_chart(tickers, output_path=OUTPUT_FILE)

    print(f"Combined chart saved: {path}")
    _open_file(path)


def _open_file(path: str) -> None:
    """Open *path* with the OS default viewer (Windows-only for now)."""
    if sys.platform == "win32":
        subprocess.Popen(["start", "", path], shell=True)  # noqa: S603
    else:
        print(f"Open the file manually: {path}")


if __name__ == "__main__":
    main()
