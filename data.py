"""Data fetching and technical-indicator calculations.

All interaction with *yfinance* is isolated here so the rest of the
application stays decoupled from the data source.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from config import DOWNLOAD_PERIOD, MA_WINDOWS, RSI_PERIOD, TAIL_DAYS


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
    ma_score: int
    rsi_score: float
    ma_breakdown: dict[int, int]


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
    buy_score = _compute_buy_score(current_price, moving_averages, rsi)

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
        buy_score=buy_score,
    )


# ── Private helpers ─────────────────────────────────────────────────


def _compute_buy_score(
    current_price: float,
    moving_averages: dict[int, float],
    rsi: pd.Series,
) -> BuyScore:
    """Derive a 0–10 buy-in score from MA positioning and RSI.

    Scoring breakdown
    -----------------
    - MA component (0–6 pts): +2 for each MA the price is *below*
      (below MA → potential value).
    - RSI component (0–4 pts): scaled linearly so RSI 30 or lower = 4,
      RSI 70 or higher = 0 (oversold → buying opportunity).

    The final score is clamped to [0, 10] and mapped to a suggestion
    string.
    """
    # ── MA component (0–6) ──
    ma_breakdown: dict[int, int] = {}
    for window, ma in moving_averages.items():
        ma_breakdown[window] = 2 if current_price < ma else 0
    ma_score = sum(ma_breakdown.values())

    # ── RSI component (0–4) ──
    latest_rsi = float(rsi.iloc[-1])
    if latest_rsi <= 30:
        rsi_score = 4.0
    elif latest_rsi >= 70:
        rsi_score = 0.0
    else:
        # Linear interpolation: RSI 30→4, RSI 70→0
        rsi_score = (70 - latest_rsi) / (70 - 30) * 4

    total = ma_score + rsi_score
    total = max(0.0, min(10.0, total))

    suggestion = _score_to_suggestion(total)
    return BuyScore(
        score=total,
        suggestion=suggestion,
        ma_score=ma_score,
        rsi_score=rsi_score,
        ma_breakdown=ma_breakdown,
    )


def _score_to_suggestion(score: float) -> str:
    """Map a numeric score to a human-readable suggestion."""
    if score >= 9:
        return "Big buy-in"
    if score >= 7:
        return "A little more buy-in"
    if score >= 5:
        return "Regular buy-in"
    if score >= 3:
        return "Less buy-in"
    return "Do not buy"


def _download(symbol: str) -> pd.DataFrame:
    """Download and normalise column names from *yfinance*.

    The multi-level column index returned by ``yf.download`` is
    flattened to simple strings so downstream code can use
    ``df["Close"]`` directly.
    """
    df = yf.download(symbol, period=DOWNLOAD_PERIOD, auto_adjust=True)
    df.columns = df.columns.get_level_values(0)
    return df


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
