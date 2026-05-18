"""Application configuration for FinAnalysis.

Centralises ticker definitions, moving-average windows, chart settings,
and output paths so they can be changed in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.models import TickerConfig

load_dotenv()

# ── API keys ────────────────────────────────────────────────────────

KRX_AUTH_KEY: str = os.environ.get("KRX_AUTH_KEY", "")

# ── Ticker definitions ──────────────────────────────────────────────

TICKERS_INTL: list[TickerConfig] = [
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
        # Use Naver's international gold API for more reliable live price
        "live_price_source": "naver_intl_gold",
    },
]

TICKERS_KR: list[TickerConfig] = [
    {
        "symbol": "360750",
        "label": "TIGER S&P500",
        "source": "pykrx",
        # Tracks S&P 500 — same scoring logic as the international version.
        "ma_weights": {50: 0.5, 100: 1.5, 200: 5.0},
        "ma_fade_thresholds": {50: 0.07, 100: 0.10, 200: 0.15},
        "drawdown_full_pct": 0.25,
        # Core holding — mirrors international S&P allocation.
        "base_weight": 0.55,
        "min_weight": 0.40,
    },
    {
        "symbol": "133690",
        "label": "TIGER 나스닥100",
        "source": "pykrx",
        # Tracks NASDAQ 100 — same scoring logic as the international version.
        "ma_weights": {50: 1.0, 100: 2.0, 200: 4.0},
        "ma_fade_thresholds": {50: 0.10, 100: 0.14, 200: 0.20},
        "drawdown_full_pct": 0.35,
        # Growth satellite — mirrors international NASDAQ allocation.
        "base_weight": 0.15,
        "min_weight": 0.05,
    },
    {
        "symbol": "KRX_GOLD",
        "label": "금현물 (KRX)",
        "source": "krx_gold",
        # KRX Gold reflects both gold price + USD/KRW FX, making it more
        # volatile than international gold.  Wider fade thresholds account
        # for the FX-driven deviations (calculated from 3yr historical data).
        "ma_weights": {50: 1.75, 100: 2.5, 200: 2.75},
        "ma_fade_thresholds": {50: 0.09, 100: 0.16, 200: 0.27},
        "drawdown_full_pct": 0.20,
        # Hedge allocation — mirrors international Gold allocation.
        "base_weight": 0.30,
        "min_weight": 0.20,
    },
]

TICKERS: list[TickerConfig] = TICKERS_INTL + TICKERS_KR
"""Combined ticker list for backward compatibility."""

# ── Comparison pairs ────────────────────────────────────────────────

COMPARISON_PAIRS: list[dict[str, str]] = [
    {"kr_symbol": "360750", "intl_symbol": "^GSPC", "label": "S&P 500"},
    {"kr_symbol": "133690", "intl_symbol": "^NDX", "label": "NASDAQ 100"},
    {"kr_symbol": "KRX_GOLD", "intl_symbol": "GC=F", "label": "Gold"},
]
"""Pairs of KR ↔ International tickers for the comparison tab."""

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

# ── Network & caching ──────────────────────────────────────────────

import pathlib

PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
"""Absolute path to the project root directory."""

HTTP_TIMEOUT: int = 10
"""Default timeout (seconds) for HTTP requests to external APIs."""

NAVER_TIMEOUT: int = 5
"""Timeout (seconds) for Naver real-time price API calls."""

KRX_RATE_LIMIT_SLEEP: float = 0.2
"""Seconds to sleep between consecutive KRX API calls."""

KRX_CACHE_PATH: pathlib.Path = PROJECT_ROOT / "data" / "gold_krx.csv"
"""Path to the KRX Gold CSV cache file."""

# ── Alert settings ─────────────────────────────────────────────────

ALERT_THRESHOLD: float = 6.5
"""Score threshold that triggers an email alert (Increase buy-in level)."""

ALERT_SCORE_DELTA: float = 0.3
"""Minimum score increase from last emailed score to trigger a repeat email same day."""

ALERT_AGGRESSIVE_THRESHOLD: float = 8.0
"""Score threshold for aggressive alert tier (tighter delta)."""

ALERT_AGGRESSIVE_DELTA: float = 0.1
"""Minimum score increase for repeat alert when score is in aggressive zone (≥8.0)."""

ALERT_EMAIL_TO: str = os.environ.get("ALERT_EMAIL_TO", "")
"""Recipient email address for score alerts."""

ALERT_EMAIL_FROM: str = os.environ.get("ALERT_EMAIL_FROM", "")
"""Sender email address (Gmail) for score alerts."""

ALERT_SMTP_PASSWORD: str = os.environ.get("ALERT_SMTP_PASSWORD", "")
"""Gmail App Password for SMTP authentication."""

ALERT_STATE_PATH: pathlib.Path = PROJECT_ROOT / "log" / "alert_state.json"
"""Path to the alert state file (tracks last email time and scores)."""
