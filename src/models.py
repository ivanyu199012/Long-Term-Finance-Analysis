"""Data models for FinAnalysis.

Pure dataclass definitions — no business logic.  These are the shared
contracts between modules (fetchers, indicators, allocation, backtest, chart).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# ── Scoring & ticker data ───────────────────────────────────────────


@dataclass
class BuyScore:
    """Technical-indicator-based buy-in score and suggestion text.

    The score ranges from 0 (do not buy) to 10 (strong buy signal).
    It is derived purely from moving-average positioning and RSI —
    it is *not* financial advice.
    """

    score: float
    suggestion: str
    ma_score: float
    rsi_score: float
    drawdown_score: float
    current_drawdown: float
    max_drawdown: float
    ma_breakdown: dict[int, float]


@dataclass
class TickerData:
    """Holds downloaded price data and pre-computed indicators for one ticker."""

    symbol: str
    label: str
    ma_weights: dict[int, float]
    ma_fade_thresholds: dict[int, float]
    drawdown_full_pct: float
    history: pd.DataFrame
    current_price: float
    moving_averages: dict[int, float]
    ma_pct_diffs: dict[int, float]
    rsi: pd.Series
    tail: pd.DataFrame
    rsi_tail: pd.Series
    estimated_dates: list[str] = None  # type: ignore[assignment]
    score_tail: pd.Series = None  # type: ignore[assignment]
    buy_score: BuyScore = None  # type: ignore[assignment]


# ── Allocation ──────────────────────────────────────────────────────


@dataclass
class Allocation:
    """Portfolio allocation recommendation for one ticker."""

    label: str
    weight_pct: float
    amount: float


# ── Backtest results ────────────────────────────────────────────────


@dataclass
class BacktestResult:
    """Results for a single strategy run."""

    total_invested: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    n_months: int
    equity_curve: pd.Series | None = None
    monthly_investments: pd.Series | None = None


@dataclass
class BacktestComparison:
    """Side-by-side comparison of flat DCA vs score-based DCA."""

    label: str
    period: str
    flat: BacktestResult
    score_raw: BacktestResult
    score_normalized: BacktestResult


@dataclass
class PortfolioBacktestResult:
    """Results for a portfolio-level backtest."""

    total_invested: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    n_months: int
    per_asset: dict[str, BacktestResult]
    equity_curve: pd.Series | None = None


@dataclass
class PortfolioComparison:
    """Side-by-side comparison of flat allocation vs score-based allocation."""

    period: str
    flat: PortfolioBacktestResult
    score_alloc: PortfolioBacktestResult
