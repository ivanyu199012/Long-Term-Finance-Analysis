"""KRX Gold Spot data fetcher.

Fetches daily gold price data from the KRX Open API (금현물 1Kg).
Implements local CSV caching to avoid repeated API calls since the
API only returns one day per request.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

# ── Constants ───────────────────────────────────────────────────────

_API_URL = "https://data-dbg.krx.co.kr/svc/apis/gen/gold_bydd_trd"
_CACHE_PATH = "data/gold_krx.csv"
_GOLD_PRODUCT_NAME = "금 99.99_1Kg"
_EARLIEST_DATE = "20140324"  # KRX Gold data available from this date
_RATE_LIMIT_SLEEP = 0.2  # seconds between API calls


# ── Public API ──────────────────────────────────────────────────────


def download_krx_gold(auth_key: str, period_days: int = 1100) -> pd.DataFrame:
    """Download KRX Gold Spot daily close prices with local caching.

    On first run, fetches all data from ``_EARLIEST_DATE`` (or
    ``period_days`` back, whichever is more recent) to today.
    On subsequent runs, loads the cache and only fetches missing dates.

    Parameters
    ----------
    auth_key:
        KRX Open API authentication key.
    period_days:
        Minimum number of calendar days of history to maintain.

    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex and at least a 'Close' column.

    Raises
    ------
    ValueError
        If auth_key is empty or no data could be fetched.
    """
    if not auth_key:
        raise ValueError(
            "KRX_AUTH_KEY is not set. Add it to your .env file or environment."
        )

    # Determine start date
    min_start = datetime.today() - timedelta(days=period_days)
    earliest = datetime.strptime(_EARLIEST_DATE, "%Y%m%d")
    start_date = max(min_start, earliest)

    # Load existing cache
    cached_df = _load_cache()

    if cached_df is not None and not cached_df.empty:
        last_cached = cached_df.index.max()
        # Only fetch dates after the last cached date
        fetch_start = last_cached + timedelta(days=1)
    else:
        cached_df = pd.DataFrame()
        fetch_start = start_date

    # Fetch new data
    today = datetime.today()
    if fetch_start.date() <= today.date():
        new_data = _fetch_date_range(auth_key, fetch_start, today)
        if new_data:
            new_df = pd.DataFrame(new_data)
            new_df["Date"] = pd.to_datetime(new_df["Date"])
            new_df = new_df.set_index("Date").sort_index()

            # Merge with cache
            if not cached_df.empty:
                combined = pd.concat([cached_df, new_df])
                combined = combined[~combined.index.duplicated(keep="last")]
                combined = combined.sort_index()
            else:
                combined = new_df
        else:
            combined = cached_df
    else:
        combined = cached_df

    if combined.empty:
        raise ValueError("No KRX Gold data available. Check your API key and date range.")

    # Trim to requested period
    cutoff = datetime.today() - timedelta(days=period_days)
    combined = combined[combined.index >= pd.Timestamp(cutoff)]

    # Save updated cache
    _save_cache(combined)

    return combined


def get_live_price_krx_gold(auth_key: str) -> float:
    """Get the most recent KRX Gold close price.

    Tries today first, then walks back up to 30 days to find the
    last trading day. Falls back to cache if API has no recent data.

    Parameters
    ----------
    auth_key:
        KRX Open API authentication key.

    Returns
    -------
    float
        Latest close price in KRW per gram.
    """
    if not auth_key:
        raise ValueError("KRX_AUTH_KEY is not set.")

    for days_back in range(31):
        date = datetime.today() - timedelta(days=days_back)
        date_str = date.strftime("%Y%m%d")
        price = _fetch_single_day(auth_key, date_str)
        if price is not None:
            return price

    # Fallback: try loading from cache
    cached = _load_cache()
    if cached is not None and not cached.empty:
        return float(cached["Close"].iloc[-1])

    raise ValueError("Could not get live KRX Gold price.")


# ── Private helpers ─────────────────────────────────────────────────


def _fetch_date_range(
    auth_key: str,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Fetch gold prices for a date range, one day at a time.

    Respects rate limits with sleep between requests.
    Skips non-trading days (empty API responses).
    """
    results: list[dict] = []
    current = start

    while current.date() <= end.date():
        date_str = current.strftime("%Y%m%d")
        price = _fetch_single_day(auth_key, date_str)
        if price is not None:
            results.append({"Date": date_str, "Close": price})

        current += timedelta(days=1)
        time.sleep(_RATE_LIMIT_SLEEP)

    return results


def _fetch_single_day(auth_key: str, date_str: str) -> float | None:
    """Fetch gold close price for a single date.

    Returns None if the date is a non-trading day or the API returns
    no matching data.
    """
    try:
        resp = requests.get(
            _API_URL,
            headers={"AUTH_KEY": auth_key},
            params={"basDd": date_str},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    # The API returns a list of products; filter for 금 1Kg
    items = data.get("output", data.get("OutBlock_1", []))
    if not items:
        # Try alternative response structure
        items = data if isinstance(data, list) else []

    for item in items:
        product_name = item.get("ISU_NM", "")
        if _GOLD_PRODUCT_NAME in product_name:
            close_str = item.get("TDD_CLSPRC", "")
            if close_str:
                try:
                    return float(str(close_str).replace(",", ""))
                except (ValueError, TypeError):
                    pass

    return None


def _load_cache() -> pd.DataFrame | None:
    """Load cached gold data from CSV, or return None if not found."""
    if not os.path.exists(_CACHE_PATH):
        return None

    try:
        df = pd.read_csv(_CACHE_PATH, parse_dates=["Date"], index_col="Date")
        df = df.sort_index()
        return df
    except Exception:
        return None


def _save_cache(df: pd.DataFrame) -> None:
    """Save gold data to CSV cache."""
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    df.to_csv(_CACHE_PATH)
