"""Application configuration for FinAnalysis.

Centralises ticker definitions, moving-average windows, chart settings,
and output paths so they can be changed in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# ── API keys ────────────────────────────────────────────────────────

KRX_AUTH_KEY: str = os.environ.get("KRX_AUTH_KEY", "")

# ── Ticker definitions ──────────────────────────────────────────────

TICKERS_INTL: list[dict] = [
    {
        "symbol": "^GSPC",
        "label": "S&P 500",
        "source": "yfinance",
        # S&P is broad and stable — the long-term MA200 is the dominant
        # signal, so it gets the lion's share of weight (5.0).  Shorter MAs
        # add minor sensitivity but aren't as meaningful for a diversified index.
        "ma_weights": {50: 0.5, 100: 1.5, 200: 5},
        # S&P is a broad, moderate-volatility index.  Price stays relatively
        # close to its MAs, so standard fade bands are appropriate.
        "ma_fade_thresholds": {50: 0.07, 100: 0.10, 200: 0.15},
        # A 25% drawdown is a significant bear market for the S&P; full
        # drawdown score should be awarded well before a 2008-level crash.
        "drawdown_full_pct": 0.25,
        # Base portfolio allocation weight.  S&P is the core holding.
        "base_weight": 0.55,
        # Minimum allocation floor to prevent abandoning the position.
        "min_weight": 0.40,
    },
    {
        "symbol": "^NDX",
        "label": "NASDAQ 100",
        "source": "yfinance",
        # NASDAQ swings harder on shorter timeframes due to tech concentration.
        # Weight is shifted toward MA50/MA100 (1.0/2.0) to capture these moves,
        # while MA200 is reduced (4.0) since NASDAQ can stay well below it
        # during prolonged sector rotations without it being a strong buy signal.
        "ma_weights": {50: 1.0, 100: 2.0, 200: 4.0},
        # NASDAQ is more volatile and tech-concentrated.  Price routinely
        # deviates further from MAs, so wider fade bands prevent the score
        # from dropping to zero too quickly during normal rallies.
        "ma_fade_thresholds": {50: 0.10, 100: 0.14, 200: 0.20},
        # NASDAQ drawdowns of 30–40% are not unusual (e.g. 2022 tech sell-off).
        # A higher threshold avoids maxing out the drawdown score too early.
        "drawdown_full_pct": 0.35,
        # Smallest base weight — growth satellite, not core.
        "base_weight": 0.15,
        # Low floor since it's a satellite position.
        "min_weight": 0.05,
    },
    {
        "symbol": "GC=F",
        "label": "Gold",
        "source": "yfinance",
        # Gold trends slowly and all three MAs carry roughly equal importance.
        # Weight is spread more evenly (1.75/2.5/2.75) so no single MA
        # dominates — short-term dips below MA50 are just as relevant as
        # crossing below MA200 for a mean-reverting commodity.
        "ma_weights": {50: 1.75, 100: 2.5, 200: 2.75},
        # Gold is a low-volatility safe-haven asset.  It trades in tighter
        # ranges around its MAs, so narrower fade bands make small deviations
        # more meaningful for scoring.
        "ma_fade_thresholds": {50: 0.05, 100: 0.08, 200: 0.12},
        # Gold rarely draws down more than 15–20%.  A lower threshold ensures
        # the drawdown component contributes meaningfully even in mild dips.
        "drawdown_full_pct": 0.20,
        # Hedge allocation — meaningful but not dominant.
        "base_weight": 0.30,
        # Maintain a meaningful hedge position at all times.
        "min_weight": 0.20,
    },
]

TICKERS_KR: list[dict] = [
    {
        "symbol": "360750",
        "label": "TIGER S&P500",
        "source": "pykrx",
        # Tracks S&P 500 — same scoring logic as the international version.
        "ma_weights": {50: 0.5, 100: 1.5, 200: 5.0},
        "ma_fade_thresholds": {50: 0.07, 100: 0.10, 200: 0.15},
        "drawdown_full_pct": 0.25,
        "base_weight": 0.45,
        "min_weight": 0.30,
    },
    {
        "symbol": "133690",
        "label": "TIGER 나스닥100",
        "source": "pykrx",
        # Tracks NASDAQ 100 — same scoring logic as the international version.
        "ma_weights": {50: 1.0, 100: 2.0, 200: 4.0},
        "ma_fade_thresholds": {50: 0.10, 100: 0.14, 200: 0.20},
        "drawdown_full_pct": 0.35,
        "base_weight": 0.25,
        "min_weight": 0.10,
    },
]

TICKERS: list[dict] = TICKERS_INTL + TICKERS_KR
"""Combined ticker list for backward compatibility."""

# ── Technical-indicator settings ────────────────────────────────────

MA_WINDOWS: list[int] = [50, 100, 200]
"""Moving-average window sizes applied to every ticker."""

RSI_PERIOD: int = 14
"""Look-back period for the RSI calculation."""

RSI_MAX_SCORE: float = 1.5
"""Maximum score the RSI component can contribute."""

DRAWDOWN_MAX_SCORE: float = 1.5
"""Maximum score the drawdown component can contribute."""

DRAWDOWN_WINDOW: int = 500
"""Rolling window (trading days) used to find the local peak for drawdown calculation."""

BASE_AMOUNT: float = 500_000.0
"""Base monthly investment amount (₩) used to compute per-asset suggestion buy-in amounts."""

MONTHLY_BUDGET: float = 1_000_000.0
"""Total monthly investment budget (₩) used for portfolio allocation."""

TAIL_DAYS: int = 100
"""Number of recent trading days shown on the chart."""

DOWNLOAD_PERIOD: str = "3y"
"""yfinance download period string (e.g. '1y', '6mo', '2y').  Applies to yfinance source only."""

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

OUTPUT_FILE: str = "out/combined_chart.html"
BACKTEST_OUTPUT_FILE: str = "out/backtest_chart.html"
