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
    )


# ── Private helpers ─────────────────────────────────────────────────


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
