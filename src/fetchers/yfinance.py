"""Yahoo Finance data fetcher for FinAnalysis.

Handles downloading historical data and getting live prices via yfinance.
Also contains the estimated-data fill logic for incomplete trading days.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def download(symbol: str, period: str = "3y") -> pd.DataFrame:
    """Download and normalise column names from yfinance.

    The multi-level column index returned by ``yf.download`` is
    flattened to simple strings so downstream code can use
    ``df["Close"]`` directly.

    Parameters
    ----------
    symbol:
        Yahoo Finance ticker symbol (e.g. ``"^GSPC"``).
    period:
        yfinance period string (e.g. '1y', '3y', '6mo').
    """
    df = yf.download(symbol, period=period, auto_adjust=True)
    df.columns = df.columns.get_level_values(0)
    return df


def get_live_price(symbol: str, df: pd.DataFrame) -> float:
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


def fill_estimated_data(
    df: pd.DataFrame,
    current_price: float,
) -> list[str]:
    """Fill incomplete rows with estimated prices.

    When yfinance returns rows with NaN Close (e.g. today before market
    close), fills them with the mean of the previous day's close and the
    current live price.  This keeps MA and drawdown calculations valid
    without dropping the row entirely.

    Parameters
    ----------
    df:
        DataFrame with at least a 'Close' column (modified in place).
    current_price:
        The live/current price to use for estimation.

    Returns
    -------
    list[str]
        List of date strings that were estimated.
    """
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
    return estimated_dates
