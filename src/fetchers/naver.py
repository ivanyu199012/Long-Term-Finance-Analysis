"""Real-time price from Naver Finance JSON APIs.

Provides near-real-time prices for Korean tickers via Naver's mobile stock API.
Falls back gracefully (returns None) on any failure.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import requests

_ETF_URL = "https://m.stock.naver.com/front-api/realTime/marketPrice?itemCodes={code}&endType=stock&stockType=domestic"
_GOLD_URL = "https://m.stock.naver.com/front-api/marketIndex/metals?category=metals&reutersCode=M04020000"
_TIMEOUT = 5


@dataclass
class LivePrice:
    """Real-time price with timestamp."""

    price: float
    traded_at: str  # formatted as "MM/DD HH:MM"


def get_realtime_price_etf(ticker_code: str) -> LivePrice | None:
    """Get current ETF price from Naver's real-time market API.

    Parameters
    ----------
    ticker_code:
        KRX ticker code (e.g. "360750", "133690").

    Returns
    -------
    LivePrice | None
        Price with timestamp, or None if request fails.
    """
    url = _ETF_URL.format(code=ticker_code)
    try:
        resp = requests.get(
            url,
            timeout=_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        data = resp.json()
        datas = data.get("result", {}).get("datas", [])

        if not datas:
            _warn(f"ETF {ticker_code}: no data in API response")
            return None

        item = datas[0]
        price_str = item.get("closePrice", "").replace(",", "")
        if not price_str:
            _warn(f"ETF {ticker_code}: closePrice not found")
            return None

        traded_at = _parse_datetime(item.get("localTradedAt", ""))
        return LivePrice(price=float(price_str), traded_at=traded_at)

    except Exception as e:
        _warn(f"ETF {ticker_code}: {e}")
        return None


def get_realtime_price_gold() -> LivePrice | None:
    """Get current KRX gold price from Naver's market index API.

    Returns
    -------
    LivePrice | None
        Price with timestamp, or None if request fails.
    """
    try:
        resp = requests.get(
            _GOLD_URL,
            timeout=_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        data = resp.json()
        items = data.get("result", {}).get("mainList", [])

        for item in items:
            if item.get("name") == "국내 금":
                price_str = item.get("closePrice", "").replace(",", "")
                if price_str:
                    traded_at = _parse_datetime(item.get("localTradedAt", ""))
                    return LivePrice(price=float(price_str), traded_at=traded_at)

        _warn("Gold: '국내 금' not found in API response")
        return None

    except Exception as e:
        _warn(f"Gold: {e}")
        return None


def _parse_datetime(iso_str: str) -> str:
    """Parse ISO datetime string to 'MM/DD HH:MM' format.

    Handles formats like:
    - "2026-05-07T14:36:31.862301+09:00"
    - "2026-05-07T14:21:56"
    """
    if not iso_str:
        return ""
    try:
        # Take just the date and time parts (ignore timezone/microseconds)
        dt_part = iso_str[:16]  # "2026-05-07T14:36"
        date_part, time_part = dt_part.split("T")
        month = date_part[5:7]
        day = date_part[8:10]
        return f"{month}/{day} {time_part}"
    except (ValueError, IndexError):
        return ""


def get_realtime_price_intl_gold() -> LivePrice | None:
    """Get international gold price (USD/OZS) from Naver's market index API.

    This provides a 10-minute delayed quote that works even when
    the US stock market is closed (gold futures trade ~24h).

    Returns
    -------
    LivePrice | None
        Price in USD/OZS with timestamp, or None if request fails.
    """
    try:
        resp = requests.get(
            _GOLD_URL,
            timeout=_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        data = resp.json()
        items = data.get("result", {}).get("mainList", [])

        for item in items:
            if item.get("name") == "국제 금":
                price_str = item.get("closePrice", "").replace(",", "")
                if price_str:
                    traded_at = _parse_datetime(item.get("localTradedAt", ""))
                    return LivePrice(price=float(price_str), traded_at=traded_at)

        _warn("Intl Gold: '국제 금' not found in API response")
        return None

    except Exception as e:
        _warn(f"Intl Gold: {e}")
        return None


def _warn(msg: str) -> None:
    """Print a warning to stderr."""
    print(f"\033[33m⚠ [Naver] Failed to get live price — {msg}\033[0m", file=sys.stderr)
