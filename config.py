"""Application configuration for FinAnalysis.

Centralises ticker definitions, moving-average windows, chart settings,
and output paths so they can be changed in one place.
"""

from dataclasses import dataclass

# ── Ticker definitions ──────────────────────────────────────────────

TICKERS: list[dict] = [
    {
        "symbol": "^GSPC",
        "label": "S&P 500",
        "ma_weights": {50: 0.5, 100: 1.5, 200: 5},
    },
    {
        "symbol": "GC=F",
        "label": "Gold",
        "ma_weights": {50: 1.75, 100: 2.5, 200: 2.75},
    },
]

# ── Technical-indicator settings ────────────────────────────────────

MA_WINDOWS: list[int] = [50, 100, 200]
"""Moving-average window sizes applied to every ticker."""

RSI_PERIOD: int = 14
"""Look-back period for the RSI calculation."""

RSI_MAX_SCORE: float = 1.5
"""Maximum score the RSI component can contribute."""

DRAWDOWN_MAX_SCORE: float = 1.5
"""Maximum score the drawdown component can contribute."""

DRAWDOWN_FULL_PCT: float = 0.30
"""Drawdown percentage at which the full score is awarded (linear 0–30%)."""

TAIL_DAYS: int = 100
"""Number of recent trading days shown on the chart."""

DOWNLOAD_PERIOD: str = "3y"
"""yfinance download period string (e.g. '1y', '6mo', '2y')."""

# ── Chart appearance ────────────────────────────────────────────────


@dataclass(frozen=True)
class MaStyle:
    """Visual style for a single moving-average line."""

    linestyle: str
    color: str


MA_STYLES: dict[int, MaStyle] = {
    50: MaStyle(linestyle="--", color="green"),
    100: MaStyle(linestyle="-.", color="blue"),
    200: MaStyle(linestyle=":", color="red"),
}

FIGURE_SIZE: tuple[int, int] = (16, 10)
HEIGHT_RATIOS: list[int] = [3, 1]

# ── Output ──────────────────────────────────────────────────────────

OUTPUT_FILE: str = "combined_chart.html"
