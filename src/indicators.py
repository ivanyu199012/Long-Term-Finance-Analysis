"""Technical indicator calculations for FinAnalysis.

Pure math functions — all parameters are passed in explicitly.
No direct config imports; callers provide the necessary values.
"""

from __future__ import annotations

import pandas as pd

from src.models import BuyScore


# ── Public API ──────────────────────────────────────────────────────


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute the Relative Strength Index using Wilder's EWM smoothing.

    Parameters
    ----------
    series:
        A price series (typically the *Close* column).
    period:
        Look-back window (default 14).

    Returns
    -------
    pd.Series
        RSI values in the range 0–100.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def calc_drawdown(
    close: pd.Series,
    window: int = 500,
) -> tuple[float, float]:
    """Compute current and max drawdown from a close-price series.

    Parameters
    ----------
    close:
        Daily close prices.
    window:
        Rolling window (trading days) to find the local peak.

    Returns
    -------
    tuple[float, float]
        (current_drawdown, max_drawdown) as negative fractions
        (e.g. -0.15 means 15% below peak).
    """
    peak = close.rolling(window=window, min_periods=1).max()
    drawdown = (close - peak) / peak
    current_dd = float(drawdown.iloc[-1])
    max_dd = float(drawdown.min())
    return current_dd, max_dd


def compute_buy_score(
    current_price: float,
    moving_averages: dict[int, float],
    rsi: pd.Series,
    current_drawdown: float,
    max_drawdown: float,
    ma_weights: dict[int, float],
    ma_fade_thresholds: dict[int, float],
    drawdown_full_pct: float,
    rsi_max_score: float = 1.5,
    drawdown_max_score: float = 1.5,
    base_amount: float = 500_000.0,
) -> BuyScore:
    """Derive a 0–10 buy-in score from MA positioning, RSI, and drawdown.

    Scoring breakdown
    -----------------
    - MA component (0–7 pts): weighted per MA window — full weight when
      price is below the MA, linear fade-out using per-ticker thresholds,
      zero beyond threshold.
    - RSI component (0–1.5 pts): full score at RSI ≤ 35, half at
      RSI ≤ 45, zero above.
    - Drawdown component (0–1.5 pts): scaled linearly from 0% to
      per-ticker ``drawdown_full_pct``.

    The final score is clamped to [0, 10] and mapped to a suggestion string.
    """
    # ── MA component ──
    ma_breakdown: dict[int, float] = {}
    for window, ma in moving_averages.items():
        diff_pct = (current_price - ma) / ma
        threshold = ma_fade_thresholds[window]
        if diff_pct <= 0:
            score = ma_weights[window]
        elif diff_pct <= threshold:
            score = ma_weights[window] * (1 - diff_pct / threshold)
        else:
            score = 0.0
        ma_breakdown[window] = score
    ma_score = sum(ma_breakdown.values())

    # ── RSI component ──
    latest_rsi = float(rsi.iloc[-1])
    if latest_rsi <= 35:
        rsi_score = rsi_max_score
    elif latest_rsi <= 45:
        rsi_score = rsi_max_score * 0.5
    else:
        rsi_score = 0.0

    # ── Drawdown component ──
    dd_abs = abs(current_drawdown)
    drawdown_score = min(dd_abs / drawdown_full_pct, 1.0) * drawdown_max_score

    total = ma_score + rsi_score + drawdown_score
    total = max(0.0, min(10.0, total))

    suggestion = score_to_suggestion(total, base_amount)
    return BuyScore(
        score=total,
        suggestion=suggestion,
        ma_score=ma_score,
        rsi_score=rsi_score,
        drawdown_score=drawdown_score,
        current_drawdown=current_drawdown,
        max_drawdown=max_drawdown,
        ma_breakdown=ma_breakdown,
    )


def score_to_suggestion(score: float, base_amount: float = 500_000.0) -> str:
    """Map a numeric score to a suggestion string with concrete buy-in amount.

    Parameters
    ----------
    score:
        Buy-in score (0–10).
    base_amount:
        Base investment amount used to compute the suggestion amount.
    """
    from src.allocation import score_to_multiplier

    multiplier = score_to_multiplier(score)

    if multiplier >= 2.25:
        label = "Aggressive buy-in"
    elif multiplier >= 1.5:
        label = "Increase buy-in"
    elif multiplier >= 1.0:
        label = "Regular buy-in"
    elif multiplier >= 0.5:
        label = "Reduce buy-in"
    else:
        label = "Minimum buy-in"

    amount = base_amount * multiplier
    return f"{label}<br> ({multiplier:.2f}x → ₩{amount:.2f})"


def compute_score_series(
    close: pd.Series,
    rsi: pd.Series,
    ma_weights: dict[int, float],
    ma_fade_thresholds: dict[int, float],
    drawdown_full_pct: float,
    ma_windows: list[int] | None = None,
    rsi_max_score: float = 1.5,
    drawdown_max_score: float = 1.5,
    drawdown_window: int = 500,
) -> pd.Series:
    """Compute the buy-in score for every day in the series.

    Replicates the same MA + RSI + drawdown logic used in
    ``compute_buy_score`` but vectorised across all rows.

    Parameters
    ----------
    close:
        Daily close prices.
    rsi:
        Pre-computed RSI series (same index as close).
    ma_weights:
        Per-window MA weights.
    ma_fade_thresholds:
        Per-window fade thresholds.
    drawdown_full_pct:
        Drawdown percentage at which full score is awarded.
    ma_windows:
        MA window sizes. Defaults to keys of ``ma_weights``.
    rsi_max_score:
        Maximum RSI component score.
    drawdown_max_score:
        Maximum drawdown component score.
    drawdown_window:
        Rolling window for peak calculation.
    """
    if ma_windows is None:
        ma_windows = list(ma_weights.keys())

    # MAs
    mas = {w: close.rolling(window=w).mean() for w in ma_windows}

    # MA component: full weight when price < MA, linear fade per window threshold
    ma_score = pd.Series(0.0, index=close.index)
    for w, ma in mas.items():
        diff_pct = (close - ma) / ma
        weight = ma_weights[w]
        threshold = ma_fade_thresholds[w]
        score = pd.Series(0.0, index=close.index)

        # below MA → full score
        score = score.where(diff_pct > 0, weight)

        # between 0 and threshold → linear decay
        mask = (diff_pct > 0) & (diff_pct <= threshold)
        score[mask] = weight * (1 - diff_pct[mask] / threshold)

        # above threshold → already 0
        ma_score = ma_score + score

    # RSI component: step-based (35/45 thresholds)
    rsi_score = pd.Series(0.0, index=close.index)
    rsi_score = rsi_score.where(rsi > 45, rsi_max_score * 0.5)
    rsi_score = rsi_score.where(rsi > 35, rsi_max_score)

    # Drawdown component: linear 0–drawdown_full_pct
    peak = close.rolling(window=drawdown_window, min_periods=1).max()
    dd = ((close - peak) / peak).abs()
    dd_score = (dd / drawdown_full_pct).clip(upper=1.0) * drawdown_max_score

    total = (ma_score + rsi_score + dd_score).clip(0.0, 10.0)
    return total
