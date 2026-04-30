"""Korean ETF data fetcher via pykrx.

Fetches OHLCV data for Korean-listed ETFs (e.g. TIGER S&P500, TIGER 나스닥100)
using the pykrx library.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock


def download_pykrx(symbol: str, period_days: int = 1100) -> pd.DataFrame:
    """Download OHLCV data for a Korean ETF ticker.

    Parameters
    ----------
    symbol:
        KRX ticker code (e.g. "360750" for TIGER S&P500).
    period_days:
        Number of calendar days to look back from today.
        Default 1100 (~3 years of trading days, enough for MA200 warm-up).

    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex and columns: Close, Open, High, Low, Volume.
        Column names match the yfinance output contract.
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=period_days)).strftime("%Y%m%d")

    df = stock.get_market_ohlcv_by_date(start_date, end_date, symbol)

    if df.empty:
        raise ValueError(f"No data returned from pykrx for symbol {symbol}")

    # Rename Korean columns to match yfinance contract
    df = df.rename(columns={
        "종가": "Close",
        "시가": "Open",
        "고가": "High",
        "저가": "Low",
        "거래량": "Volume",
    })

    # Ensure DatetimeIndex
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"

    # Drop rows where Close is 0 (non-trading days that pykrx sometimes returns)
    df = df[df["Close"] > 0]

    return df


def get_live_price_pykrx(symbol: str) -> float:
    """Get the latest close price for a Korean ETF.

    Fetches the most recent trading day's close price.

    Parameters
    ----------
    symbol:
        KRX ticker code.

    Returns
    -------
    float
        Latest close price in KRW.
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=7)).strftime("%Y%m%d")

    df = stock.get_market_ohlcv_by_date(start_date, end_date, symbol)

    if df.empty:
        raise ValueError(f"No recent data from pykrx for symbol {symbol}")

    # Get the last row's close price
    close_col = "종가" if "종가" in df.columns else "Close"
    return float(df[close_col].iloc[-1])
