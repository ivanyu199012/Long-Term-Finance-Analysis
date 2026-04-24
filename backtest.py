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

# ── Portfolio-level backtest ────────────────────────────────────────


@dataclass
class PortfolioBacktestResult:
    """Results for a portfolio-level backtest."""

    total_invested: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    n_months: int
    per_asset: dict[str, BacktestResult]


@dataclass
class PortfolioComparison:
    """Side-by-side comparison of flat allocation vs score-based allocation."""

    period: str
    flat: PortfolioBacktestResult
    score_alloc: PortfolioBacktestResult


def run_portfolio_backtest(
    asset_data: list[dict],
    period: str,
) -> PortfolioComparison:
    """Run portfolio-level backtest: flat allocation vs score-based allocation.

    Parameters
    ----------
    asset_data:
        List of dicts, each with keys: label, close (pd.Series),
        ma_weights, ma_fade_thresholds, drawdown_full_pct,
        base_weight, min_weight.
    period:
        Period label (e.g. "5y", "10y") for trimming.
    """
    from config import MONTHLY_BUDGET

    # Compute monthly scores for each asset
    asset_monthly: list[dict] = []
    for ad in asset_data:
        close = ad["close"]
        rsi = _calc_rsi(close)
        scores = _compute_score_series(
            close, rsi, ad["ma_weights"],
            ad["ma_fade_thresholds"], ad["drawdown_full_pct"],
        )
        monthly_close = close.resample("ME").last().dropna()
        monthly_scores = scores.reindex(monthly_close.index, method="ffill").dropna()

        common_idx = monthly_close.index.intersection(monthly_scores.index)
        monthly_close = monthly_close.loc[common_idx]
        monthly_scores = monthly_scores.loc[common_idx]

        # Shift scores by 1 month to avoid lookahead bias
        monthly_scores = monthly_scores.shift(1).dropna()
        monthly_close = monthly_close.loc[monthly_scores.index]

        asset_monthly.append({
            "label": ad["label"],
            "monthly_close": monthly_close,
            "monthly_scores": monthly_scores,
            "base_weight": ad["base_weight"],
            "min_weight": ad["min_weight"],
        })

    # Find common date range across all assets
    common_dates = asset_monthly[0]["monthly_close"].index
    for am in asset_monthly[1:]:
        common_dates = common_dates.intersection(am["monthly_close"].index)

    # Trim to target period
    target_months = {"5y": 60, "10y": 120}.get(period)
    if target_months and len(common_dates) > target_months:
        common_dates = common_dates[-target_months:]

    # Align all assets to common dates
    for am in asset_monthly:
        am["monthly_close"] = am["monthly_close"].loc[common_dates]
        am["monthly_scores"] = am["monthly_scores"].loc[common_dates]

    n_months = len(common_dates)

    # ── Flat allocation: fixed base_weight split ──
    flat_units: dict[str, float] = {am["label"]: 0.0 for am in asset_monthly}
    flat_invested = 0.0
    flat_pv_list: list[float] = []

    for i, date in enumerate(common_dates):
        for am in asset_monthly:
            price = float(am["monthly_close"].iloc[i])
            amount = MONTHLY_BUDGET * am["base_weight"]
            flat_units[am["label"]] += amount / price
            flat_invested += amount

        # Portfolio value = sum of all asset values
        pv = sum(
            flat_units[am["label"]] * float(am["monthly_close"].iloc[i])
            for am in asset_monthly
        )
        flat_pv_list.append(pv)

    # ── Score-based allocation: dynamic weights ──
    score_units: dict[str, float] = {am["label"]: 0.0 for am in asset_monthly}
    score_invested = 0.0
    score_pv_list: list[float] = []

    for i, date in enumerate(common_dates):
        # Compute raw weights = base_weight × multiplier
        raw_weights: dict[str, float] = {}
        for am in asset_monthly:
            s = float(am["monthly_scores"].iloc[i])
            mult = score_to_multiplier(s)
            raw_weights[am["label"]] = am["base_weight"] * mult

        # Normalize to 100%
        total_raw = sum(raw_weights.values())
        weights = {k: v / total_raw for k, v in raw_weights.items()}

        # Enforce minimum floors
        floored: dict[str, float] = {}
        free_labels: list[str] = []
        locked_total = 0.0
        for am in asset_monthly:
            lbl = am["label"]
            if weights[lbl] < am["min_weight"]:
                floored[lbl] = am["min_weight"]
                locked_total += am["min_weight"]
            else:
                free_labels.append(lbl)

        if floored:
            remaining = 1.0 - locked_total
            free_total = sum(weights[l] for l in free_labels)
            for lbl in free_labels:
                floored[lbl] = weights[lbl] / free_total * remaining if free_total > 0 else remaining / len(free_labels)
            weights = floored

        for am in asset_monthly:
            price = float(am["monthly_close"].iloc[i])
            amount = MONTHLY_BUDGET * weights[am["label"]]
            score_units[am["label"]] += amount / price
            score_invested += amount

        pv = sum(
            score_units[am["label"]] * float(am["monthly_close"].iloc[i])
            for am in asset_monthly
        )
        score_pv_list.append(pv)

    # ── Compute results ──
    def _make_result(pv_list: list[float], total_inv: float) -> PortfolioBacktestResult:
        final = pv_list[-1] if pv_list else 0.0
        ret = ((final - total_inv) / total_inv * 100) if total_inv > 0 else 0.0
        pv_s = pd.Series(pv_list, index=common_dates)
        peak = pv_s.cummax()
        dd = (pv_s - peak) / peak
        max_dd = float(dd.min()) * 100
        return PortfolioBacktestResult(
            total_invested=total_inv,
            final_value=final,
            total_return_pct=ret,
            max_drawdown_pct=max_dd,
            n_months=n_months,
            per_asset={},
        )

    flat_result = _make_result(flat_pv_list, flat_invested)
    score_result = _make_result(score_pv_list, score_invested)

    return PortfolioComparison(
        period=period,
        flat=flat_result,
        score_alloc=score_result,
    )


def print_portfolio_backtest(result: PortfolioComparison) -> None:
    """Print a formatted portfolio backtest comparison."""
    print(f"\n{'=' * 70}")
    print(f"  Portfolio Backtest — {result.period}")
    print(f"  ({result.flat.n_months} months, all assets combined)")
    print(f"{'=' * 70}")
    print()

    header = f"  {'Metric':<25} {'Flat Alloc':>18} {'Score Alloc':>18}"
    print(header)
    print(f"  {'-' * 58}")

    rows = [
        ("Total invested", f"₩{result.flat.total_invested:,.0f}", f"₩{result.score_alloc.total_invested:,.0f}"),
        ("Portfolio value", f"₩{result.flat.final_value:,.0f}", f"₩{result.score_alloc.final_value:,.0f}"),
        ("Total return", f"{result.flat.total_return_pct:+.2f}%", f"{result.score_alloc.total_return_pct:+.2f}%"),
        ("Max drawdown", f"{result.flat.max_drawdown_pct:.2f}%", f"{result.score_alloc.max_drawdown_pct:.2f}%"),
    ]

    for label, flat, score in rows:
        print(f"  {label:<25} {flat:>18} {score:>18}")

    print()
