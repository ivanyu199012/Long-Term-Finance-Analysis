"""Korean ETF data fetcher via pykrx with Naver chart API fallback.

Fetches OHLCV data for Korean-listed ETFs (e.g. TIGER S&P500, TIGER 나스닥100)
using the pykrx library.  If pykrx fails (network issues, KRX site changes),
falls back to Naver's mobile chart API as an alternative data source.
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime, timedelta

import pandas as pd
import requests

# Suppress pkg_resources deprecation warning from pykrx
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
    from pykrx import stock

_NAVER_CHART_URL = (
    "https://m.stock.naver.com/front-api/external/chart/domestic/info"
    "?symbol={symbol}&requestType=1&startTime={start}&endTime={end}&timeframe=day"
)
_TIMEOUT = 10


def download_pykrx(symbol: str, period_days: int = 1100) -> pd.DataFrame:
    """Download OHLCV data for a Korean ETF ticker.

    Tries pykrx first; falls back to Naver chart API on failure.

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
    try:
        df = _download_via_pykrx(symbol, period_days)
        if not df.empty:
            return df
    except Exception as e:
        _warn(f"pykrx failed for {symbol}: {e} — trying Naver fallback")

    # Fallback: Naver chart API
    try:
        df = _download_via_naver(symbol, period_days)
        if not df.empty:
            return df
    except Exception as e:
        _warn(f"Naver fallback also failed for {symbol}: {e}")

    raise ValueError(f"No data returned from pykrx or Naver for symbol {symbol}")


def _download_via_pykrx(symbol: str, period_days: int) -> pd.DataFrame:
    """Fetch OHLCV data directly from pykrx.

    Parameters
    ----------
    symbol:
        KRX ticker code.
    period_days:
        Calendar days to look back.

    Returns
    -------
    pd.DataFrame
        Normalised DataFrame with English column names.
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=period_days)).strftime("%Y%m%d")

    df = stock.get_market_ohlcv_by_date(start_date, end_date, symbol)

    if df.empty:
        return df

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


def _download_via_naver(symbol: str, period_days: int) -> pd.DataFrame:
    """Fetch OHLCV data from Naver's mobile chart API (fallback).

    Parameters
    ----------
    symbol:
        KRX ticker code (e.g. "360750").
    period_days:
        Calendar days to look back.

    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex and columns: Close, Open, High, Low, Volume.

    Notes
    -----
    This is an undocumented Naver frontend API.  It may change without
    notice and should only be used as a fallback when pykrx is unavailable.

    The response is a JSON-encoded list-of-lists::

        [
            ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"],
            ["20260102", 24535, 24630, 24480, 24620, 9724082, 0.0],
            ...
        ]

    The first row is the header; subsequent rows are data.
    """
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=period_days)).strftime("%Y%m%d")

    url = _NAVER_CHART_URL.format(symbol=symbol, start=start_date, end=end_date)
    resp = requests.get(
        url,
        timeout=_TIMEOUT,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    resp.raise_for_status()

    # The response may be a JS-style array literal (single quotes,
    # irregular whitespace) rather than strict JSON.  Try json first,
    # fall back to ast.literal_eval for Python-compatible literals.
    import ast
    import json

    text = resp.text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = ast.literal_eval(text)
        except (ValueError, SyntaxError) as e:
            raise ValueError(
                f"Cannot parse Naver chart response for {symbol}: {e}"
            ) from e

    if not isinstance(data, list) or len(data) < 2:
        raise ValueError(f"Unexpected Naver chart API response for {symbol}: expected list-of-lists")

    # First row is the header: ['날짜', '시가', '고가', '저가', '종가', '거래량', '외국인소진율']
    # Subsequent rows are data: ["20260102", 24535, 24630, 24480, 24620, 9724082, 0.0]
    header = data[0]

    # Map Korean column names to positional indices
    col_map = {name: idx for idx, name in enumerate(header)}
    idx_date = col_map.get("날짜", 0)
    idx_open = col_map.get("시가", 1)
    idx_high = col_map.get("고가", 2)
    idx_low = col_map.get("저가", 3)
    idx_close = col_map.get("종가", 4)
    idx_volume = col_map.get("거래량", 5)

    rows = []
    for row in data[1:]:
        try:
            date_str = str(row[idx_date])
            close = float(row[idx_close])
            open_ = float(row[idx_open])
            high = float(row[idx_high])
            low = float(row[idx_low])
            volume = float(row[idx_volume])

            if close > 0 and date_str:
                rows.append({
                    "Date": pd.Timestamp(date_str),
                    "Close": close,
                    "Open": open_,
                    "High": high,
                    "Low": low,
                    "Volume": volume,
                })
        except (ValueError, TypeError, IndexError):
            continue

    if not rows:
        raise ValueError(f"No valid price rows parsed from Naver for {symbol}")

    df = pd.DataFrame(rows).set_index("Date").sort_index()
    df.index.name = "Date"
    return df


def get_live_price_pykrx(symbol: str) -> float:
    """Get the latest close price for a Korean ETF.

    Tries pykrx first; falls back to Naver chart API on failure.

    Parameters
    ----------
    symbol:
        KRX ticker code.

    Returns
    -------
    float
        Latest close price in KRW.
    """
    try:
        end_date = datetime.today().strftime("%Y%m%d")
        start_date = (datetime.today() - timedelta(days=7)).strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(start_date, end_date, symbol)

        if not df.empty:
            close_col = "종가" if "종가" in df.columns else "Close"
            return float(df[close_col].iloc[-1])
    except Exception as e:
        _warn(f"pykrx live price failed for {symbol}: {e} — trying Naver fallback")

    # Fallback: fetch last 7 days from Naver and take the latest close
    try:
        df = _download_via_naver(symbol, period_days=7)
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception as e:
        _warn(f"Naver live price fallback also failed for {symbol}: {e}")

    raise ValueError(f"No recent data from pykrx or Naver for symbol {symbol}")


def _warn(msg: str) -> None:
    """Print a warning to stderr."""
    print(f"\033[33m⚠ [pykrx] {msg}\033[0m", file=sys.stderr)
