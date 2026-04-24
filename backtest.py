"""Backtesting module for FinAnalysis.

Compares flat DCA vs score-based DCA over historical data.
Pure calculation — no I/O or network calls.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import BASE_AMOUNT
from data import _calc_rsi, _compute_score_series, score_to_multiplier


# ── Result containers ───────────────────────────────────────────────


@dataclass
class BacktestResult:
    """Results for a single strategy run."""

    total_invested: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    n_months: int


@dataclass
class BacktestComparison:
    """Side-by-side comparison of flat DCA vs score-based DCA."""

    label: str
    period: str
    flat: BacktestResult
    score_raw: BacktestResult
    score_normalized: BacktestResult


# ── Core backtest logic ─────────────────────────────────────────────


def run_backtest(
    close: pd.Series,
    ma_weights: dict[int, float],
    ma_fade_thresholds: dict[int, float],
    drawdown_full_pct: float,
    label: str,
    period: str,
) -> BacktestComparison:
    """Run flat DCA vs score-based DCA backtest on a close-price series.

    Parameters
    ----------
    close:
        Full daily close-price series.
    ma_weights, ma_fade_thresholds, drawdown_full_pct:
        Per-ticker scoring parameters.
    label:
        Ticker label for display.
    period:
        Period label (e.g. "5y", "10y") for display.

    Returns
    -------
    BacktestComparison
        Contains flat, raw score-based, and normalized score-based results.
    """
    rsi = _calc_rsi(close)
    scores = _compute_score_series(close, rsi, ma_weights, ma_fade_thresholds, drawdown_full_pct)

    # Resample to monthly — last trading day of each month
    monthly_close = close.resample("ME").last().dropna()
    monthly_scores = scores.reindex(monthly_close.index, method="ffill").dropna()

    # Align both series
    common_idx = monthly_close.index.intersection(monthly_scores.index)
    monthly_close = monthly_close.loc[common_idx]
    monthly_scores = monthly_scores.loc[common_idx]

    # Shift scores by 1 month to avoid lookahead bias:
    # use last month's signal to decide this month's investment.
    monthly_scores = monthly_scores.shift(1).dropna()
    monthly_close = monthly_close.loc[monthly_scores.index]

    # Trim to target period (extra data was only needed for warm-up)
    target_months = {"5y": 60, "10y": 120}.get(period)
    if target_months and len(monthly_close) > target_months:
        monthly_close = monthly_close.iloc[-target_months:]
        monthly_scores = monthly_scores.iloc[-target_months:]

    # ── Flat DCA ──
    flat = _run_strategy(monthly_close, multipliers=None)

    # ── Score-based DCA (raw) ──
    multipliers = monthly_scores.map(score_to_multiplier)
    score_raw = _run_strategy(monthly_close, multipliers=multipliers)

    # ── Score-based DCA (normalized to same total as flat) ──
    scale_factor = flat.total_invested / score_raw.total_invested if score_raw.total_invested > 0 else 1.0
    normalized_multipliers = multipliers * scale_factor
    score_normalized = _run_strategy(monthly_close, multipliers=normalized_multipliers)

    return BacktestComparison(
        label=label,
        period=period,
        flat=flat,
        score_raw=score_raw,
        score_normalized=score_normalized,
    )


def _run_strategy(
    monthly_close: pd.Series,
    multipliers: pd.Series | None = None,
) -> BacktestResult:
    """Simulate a DCA strategy over monthly price data.

    Parameters
    ----------
    monthly_close:
        Monthly close prices (last trading day).
    multipliers:
        Per-month investment multiplier.  ``None`` means flat DCA (1.0x).

    Returns
    -------
    BacktestResult
    """
    if multipliers is None:
        multipliers = pd.Series(1.0, index=monthly_close.index)

    total_units = 0.0
    total_invested = 0.0
    portfolio_values: list[float] = []

    for date in monthly_close.index:
        price = float(monthly_close.loc[date])
        mult = float(multipliers.loc[date])
        amount = BASE_AMOUNT * mult

        units = amount / price
        total_units += units
        total_invested += amount

        portfolio_values.append(total_units * price)

    final_value = portfolio_values[-1] if portfolio_values else 0.0
    total_return_pct = ((final_value - total_invested) / total_invested * 100) if total_invested > 0 else 0.0

    # Max drawdown of portfolio value curve
    pv = pd.Series(portfolio_values, index=monthly_close.index)
    peak = pv.cummax()
    dd = (pv - peak) / peak
    max_drawdown_pct = float(dd.min()) * 100

    return BacktestResult(
        total_invested=total_invested,
        final_value=final_value,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        n_months=len(monthly_close),
    )


# ── Display ─────────────────────────────────────────────────────────


def print_backtest(result: BacktestComparison) -> None:
    """Print a formatted backtest comparison to the terminal."""
    print(f"\n{'=' * 70}")
    print(f"  Backtest: {result.label} — {result.period}")
    print(f"  ({result.flat.n_months} months)")
    print(f"{'=' * 70}")
    print()

    header = f"  {'Metric':<25} {'Flat DCA':>15} {'Score (raw)':>15} {'Score (norm)':>15}"
    print(header)
    print(f"  {'-' * 67}")

    rows = [
        ("Total invested", f"₩{result.flat.total_invested:,.0f}", f"₩{result.score_raw.total_invested:,.0f}", f"₩{result.score_normalized.total_invested:,.0f}"),
        ("Portfolio value", f"₩{result.flat.final_value:,.0f}", f"₩{result.score_raw.final_value:,.0f}", f"₩{result.score_normalized.final_value:,.0f}"),
        ("Total return", f"{result.flat.total_return_pct:+.2f}%", f"{result.score_raw.total_return_pct:+.2f}%", f"{result.score_normalized.total_return_pct:+.2f}%"),
        ("Max drawdown", f"{result.flat.max_drawdown_pct:.2f}%", f"{result.score_raw.max_drawdown_pct:.2f}%", f"{result.score_normalized.max_drawdown_pct:.2f}%"),
    ]

    for label, flat, raw, norm in rows:
        print(f"  {label:<25} {flat:>15} {raw:>15} {norm:>15}")

    print()
