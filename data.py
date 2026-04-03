"""Data fetching and technical-indicator calculations.

All interaction with *yfinance* is isolated here so the rest of the
application stays decoupled from the data source.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from config import (
    DOWNLOAD_PERIOD,
    DRAWDOWN_FULL_PCT,
    DRAWDOWN_MAX_SCORE,
    MA_WEIGHTS,
    MA_WINDOWS,
    RSI_MAX_SCORE,
    RSI_PERIOD,
    TAIL_DAYS,
)


# ── Public data container ───────────────────────────────────────────


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
    history: pd.DataFrame
    current_price: float
    moving_averages: dict[int, float]
    ma_pct_diffs: dict[int, float]
    rsi: pd.Series
    tail: pd.DataFrame
    rsi_tail: pd.Series
    score_tail: pd.Series = None  # type: ignore[assignment]
    buy_score: BuyScore = None  # type: ignore[assignment]


# ── Public helpers ──────────────────────────────────────────────────


def fetch_ticker(symbol: str, label: str) -> TickerData:
    """Download one year of daily data and compute indicators.

    Parameters
    ----------
    symbol:
        Yahoo Finance ticker symbol (e.g. ``"^GSPC"``).
    label:
        Human-readable name used in chart titles.

    Returns
    -------
    TickerData
        A container with price history, moving averages, RSI, and
        the most recent *TAIL_DAYS* slice for charting.
    """
    df = _download(symbol)
    current_price = float(df["Close"].iloc[-1])

    moving_averages: dict[int, float] = {}
    ma_pct_diffs: dict[int, float] = {}
    for window in MA_WINDOWS:
        ma_value = float(df["Close"].rolling(window=window).mean().iloc[-1])
        moving_averages[window] = ma_value
        ma_pct_diffs[window] = (current_price - ma_value) / ma_value * 100

    rsi = _calc_rsi(df["Close"])
    current_dd, max_dd = _calc_drawdown(df["Close"])
    buy_score = _compute_buy_score(current_price, moving_averages, rsi, current_dd, max_dd)
    score_series = _compute_score_series(df["Close"], rsi)

    return TickerData(
        symbol=symbol,
        label=label,
        history=df,
        current_price=current_price,
        moving_averages=moving_averages,
        ma_pct_diffs=ma_pct_diffs,
        rsi=rsi,
        tail=df.tail(TAIL_DAYS),
        rsi_tail=rsi.tail(TAIL_DAYS),
        score_tail=score_series.tail(TAIL_DAYS),
        buy_score=buy_score,
    )


# ── Private helpers ─────────────────────────────────────────────────


def _compute_buy_score(
    current_price: float,
    moving_averages: dict[int, float],
    rsi: pd.Series,
    current_drawdown: float,
    max_drawdown: float,
) -> BuyScore:
    """Derive a 0–10 buy-in score from MA positioning, RSI, and drawdown.

    Scoring breakdown
    -----------------
    - MA component (0–7 pts): weighted per MA window — longer-term
      averages carry more weight (configurable via ``MA_WEIGHTS``).
    - RSI component (0–2 pts): scaled linearly so RSI 30 or lower
      = max, RSI 70 or higher = 0 (configurable via ``RSI_MAX_SCORE``).
    - Drawdown component (0–2 pts): scaled linearly from 0% to
      ``DRAWDOWN_FULL_PCT`` (configurable via ``DRAWDOWN_MAX_SCORE``).

    The final score is clamped to [0, 10] and mapped to a suggestion
    string.
    """
    # ── MA component (0–7) ──
    ma_breakdown: dict[int, float] = {}
    for window, ma in moving_averages.items():
        ma_breakdown[window] = MA_WEIGHTS[window] if current_price < ma else 0.0
    ma_score = sum(ma_breakdown.values())

    # ── RSI component (0–2) ──
    latest_rsi = float(rsi.iloc[-1])
    if latest_rsi <= 30:
        rsi_score = RSI_MAX_SCORE
    elif latest_rsi <= 40:
        rsi_score = RSI_MAX_SCORE * 0.5
    else:
        rsi_score = 0.0

    # ── Drawdown component (0–2) ──
    dd_abs = abs(current_drawdown)
    drawdown_score = min(dd_abs / DRAWDOWN_FULL_PCT, 1.0) * DRAWDOWN_MAX_SCORE

    total = ma_score + rsi_score + drawdown_score
    total = max(0.0, min(10.0, total))

    suggestion = _score_to_suggestion(total)
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


def _score_to_suggestion(score: float, base_amount: float = 500_000.0) -> str:
    """Map a numeric score to a suggestion with concrete buy-in amount."""
    if score >= 8.5:
        multiplier = 2.25  # midpoint of 2.0–2.5
        label = "Aggressive buy-in"
    elif score >= 6.5:
        multiplier = 1.5
        label = "Increase buy-in"
    elif score >= 4.5:
        multiplier = 1.0
        label = "Regular buy-in"
    elif score >= 2.5:
        multiplier = 0.5
        label = "Reduce buy-in"
    else:
        multiplier = 0.25
        label = "Minimum buy-in"

    amount = base_amount * multiplier
    return f"{label}<br> ({multiplier:.2f}x → ₩{amount:.2f})"


def _download(symbol: str) -> pd.DataFrame:
    """Download and normalise column names from *yfinance*.

    The multi-level column index returned by ``yf.download`` is
    flattened to simple strings so downstream code can use
    ``df["Close"]`` directly.
    """
    df = yf.download(symbol, period=DOWNLOAD_PERIOD, auto_adjust=True)
    df.columns = df.columns.get_level_values(0)
    return df


def _calc_drawdown(close: pd.Series) -> tuple[float, float]:
    """Compute current and max drawdown from a close-price series.

    Returns
    -------
    tuple[float, float]
        (current_drawdown, max_drawdown) as negative fractions
        (e.g. -0.15 means 15% below peak).
    """
    peak = close.cummax()
    drawdown = (close - peak) / peak
    current_dd = float(drawdown.iloc[-1])
    max_dd = float(drawdown.min())
    return current_dd, max_dd


def _compute_score_series(close: pd.Series, rsi: pd.Series) -> pd.Series:
    """Compute the buy-in score for every day in the series.

    Replicates the same MA + RSI + drawdown logic used in
    ``_compute_buy_score`` but vectorised across all rows.
    """
    # MAs
    mas = {w: close.rolling(window=w).mean() for w in MA_WINDOWS}

    # MA component: full weight when price < MA
    ma_score = pd.Series(0.0, index=close.index)
    for w, ma in mas.items():
        ma_score = ma_score + (close < ma).astype(float) * MA_WEIGHTS[w]

    # RSI component: step-based
    rsi_score = pd.Series(0.0, index=close.index)
    rsi_score = rsi_score.where(rsi > 40, RSI_MAX_SCORE * 0.5)
    rsi_score = rsi_score.where(rsi > 30, RSI_MAX_SCORE)

    # Drawdown component: linear 0–DRAWDOWN_FULL_PCT
    peak = close.cummax()
    dd = ((close - peak) / peak).abs()
    dd_score = (dd / DRAWDOWN_FULL_PCT).clip(upper=1.0) * DRAWDOWN_MAX_SCORE

    total = (ma_score + rsi_score + dd_score).clip(0.0, 10.0)
    return total


def _calc_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Compute the Relative Strength Index for *series*.

    Uses the simple rolling-average method (Cutler's RSI).

    Parameters
    ----------
    series:
        A price series (typically the *Close* column).
    period:
        Look-back window.  Defaults to :pydata:`RSI_PERIOD`.

    Returns
    -------
    pd.Series
        RSI values in the range 0–100.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
