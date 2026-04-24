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
    DRAWDOWN_WINDOW,
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
    ma_weights: dict[int, float]
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


# ── Public helpers ──────────────────────────────────────────────────


def fetch_ticker(symbol: str, label: str, ma_weights: dict[int, float]) -> TickerData:
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
    current_price = _get_live_price(symbol, df)

    # Fill incomplete rows (e.g. today before market close) with
    # mean(previous close, live price) for a more realistic estimate.
    estimated_dates: list[str] = []
    nan_mask = df["Close"].isna()
    if nan_mask.any():
        for idx in df.index[nan_mask]:
            pos = df.index.get_loc(idx)
            prev_close = float(df["Close"].iloc[pos - 1]) if pos > 0 else current_price
            est_price = (prev_close + current_price) / 2
            df.at[idx, "Close"] = est_price
            for col in ("Open", "High", "Low"):
                if col in df.columns:
                    df.at[idx, col] = est_price
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            estimated_dates.append(date_str)

    moving_averages: dict[int, float] = {}
    ma_pct_diffs: dict[int, float] = {}
    for window in MA_WINDOWS:
        ma_value = float(df["Close"].rolling(window=window).mean().iloc[-1])
        moving_averages[window] = ma_value
        ma_pct_diffs[window] = (current_price - ma_value) / ma_value * 100

    rsi = _calc_rsi(df["Close"])
    current_dd, max_dd = _calc_drawdown(df["Close"])
    buy_score = _compute_buy_score(current_price, moving_averages, rsi, current_dd, max_dd, ma_weights)
    score_series = _compute_score_series(df["Close"], rsi, ma_weights)

    return TickerData(
        symbol=symbol,
        label=label,
        ma_weights=ma_weights,
        history=df,
        current_price=current_price,
        moving_averages=moving_averages,
        ma_pct_diffs=ma_pct_diffs,
        rsi=rsi,
        tail=df.tail(TAIL_DAYS),
        rsi_tail=rsi.tail(TAIL_DAYS),
        score_tail=score_series.tail(TAIL_DAYS),
        estimated_dates=estimated_dates,
        buy_score=buy_score,
    )


# ── Private helpers ─────────────────────────────────────────────────


def _compute_buy_score(
    current_price: float,
    moving_averages: dict[int, float],
    rsi: pd.Series,
    current_drawdown: float,
    max_drawdown: float,
    ma_weights: dict[int, float],
) -> BuyScore:
    """Derive a 0–10 buy-in score from MA positioning, RSI, and drawdown.

    Scoring breakdown
    -----------------
    - MA component (0–7 pts): weighted per MA window — full weight when
      price is below the MA, linear fade-out from 0% to 10% above,
      zero beyond 10% (configurable via ``MA_WEIGHTS``).
    - RSI component (0–1.5 pts): full score at RSI ≤ 35, half at
      RSI ≤ 45, zero above (configurable via ``RSI_MAX_SCORE``).
    - Drawdown component (0–1.5 pts): scaled linearly from 0% to
      ``DRAWDOWN_FULL_PCT`` (configurable via ``DRAWDOWN_MAX_SCORE``).

    The final score is clamped to [0, 10] and mapped to a suggestion
    string.
    """
    # ── MA component (0–7) ──
    ma_breakdown: dict[int, float] = {}
    for window, ma in moving_averages.items():
        diff_pct = (current_price - ma) / ma
        if diff_pct <= 0:
            score = ma_weights[window]
        elif diff_pct <= 0.10:
            score = ma_weights[window] * (1 - diff_pct / 0.10)
        else:
            score = 0.0
        ma_breakdown[window] = score
    ma_score = sum(ma_breakdown.values())

    # ── RSI component (0–1.5) ──
    latest_rsi = float(rsi.iloc[-1])
    if latest_rsi <= 35:
        rsi_score = RSI_MAX_SCORE
    elif latest_rsi <= 45:
        rsi_score = RSI_MAX_SCORE * 0.5
    else:
        rsi_score = 0.0

    # ── Drawdown component (0–1.5) ──
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


def _get_live_price(symbol: str, df: pd.DataFrame) -> float:
    """Return the real-time market price, falling back to last close.

    Uses ``yf.Ticker.fast_info.last_price`` for the live quote.
    If that fails, falls back to the last close from the downloaded
    history.
    """
    try:
        price = yf.Ticker(symbol).fast_info.last_price
        if price:
            return float(price)
    except Exception:
        pass
    return float(df["Close"].dropna().iloc[-1])


def _calc_drawdown(close: pd.Series) -> tuple[float, float]:
    """Compute current and max drawdown from a close-price series.

    Returns
    -------
    tuple[float, float]
        (current_drawdown, max_drawdown) as negative fractions
        (e.g. -0.15 means 15% below peak).
    """
    peak = close.rolling(window=DRAWDOWN_WINDOW).max()
    drawdown = (close - peak) / peak
    current_dd = float(drawdown.iloc[-1])
    max_dd = float(drawdown.min())
    return current_dd, max_dd


def _compute_score_series(close: pd.Series, rsi: pd.Series, ma_weights: dict[int, float]) -> pd.Series:
    """Compute the buy-in score for every day in the series.

    Replicates the same MA + RSI + drawdown logic used in
    ``_compute_buy_score`` but vectorised across all rows.
    """
    # MAs
    mas = {w: close.rolling(window=w).mean() for w in MA_WINDOWS}

    # MA component: full weight when price < MA, linear fade 0–10% above
    ma_score = pd.Series(0.0, index=close.index)
    for w, ma in mas.items():
        diff_pct = (close - ma) / ma
        weight = ma_weights[w]
        score = pd.Series(0.0, index=close.index)

        # below MA → full score
        score = score.where(diff_pct > 0, weight)

        # between 0 and 10% → linear decay
        mask = (diff_pct > 0) & (diff_pct <= 0.10)
        score[mask] = weight * (1 - diff_pct[mask] / 0.10)
        
        # above 10% → already 0
        ma_score = ma_score + score

    # RSI component: step-based (35/45 thresholds)
    rsi_score = pd.Series(0.0, index=close.index)
    rsi_score = rsi_score.where(rsi > 45, RSI_MAX_SCORE * 0.5)
    rsi_score = rsi_score.where(rsi > 35, RSI_MAX_SCORE)

    # Drawdown component: linear 0–DRAWDOWN_FULL_PCT
    peak = close.rolling(window=DRAWDOWN_WINDOW).max()
    dd = ((close - peak) / peak).abs()
    dd_score = (dd / DRAWDOWN_FULL_PCT).clip(upper=1.0) * DRAWDOWN_MAX_SCORE

    total = (ma_score + rsi_score + dd_score).clip(0.0, 10.0)
    return total


def _calc_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Compute the Relative Strength Index using Wilder's EWM smoothing.

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
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))
