"""Data fetcher dispatcher — routes to the correct source based on ticker config.

This module provides the main ``fetch_ticker()`` function that:
1. Downloads data from the appropriate source (yfinance, pykrx, krx_gold)
2. Computes technical indicators (MA, RSI, drawdown, score)
3. Returns a fully-populated TickerData object
"""

from __future__ import annotations

import pandas as pd

from src.config import (
    DOWNLOAD_PERIOD,
    DRAWDOWN_MAX_SCORE,
    DRAWDOWN_WINDOW,
    MA_WINDOWS,
    RSI_MAX_SCORE,
    RSI_PERIOD,
    TAIL_DAYS,
    BASE_AMOUNT,
)
from src.indicators import calc_drawdown, calc_rsi, compute_buy_score, compute_score_series
from src.models import TickerData


def fetch_ticker(
    symbol: str,
    label: str,
    ma_weights: dict[int, float],
    ma_fade_thresholds: dict[int, float],
    drawdown_full_pct: float,
    source: str = "yfinance",
    **kwargs: object,
) -> TickerData:
    """Download daily data and compute indicators for a single ticker.

    Routes to the appropriate data source based on ``source``:
    - "yfinance" — Yahoo Finance (international tickers)
    - "pykrx" — Korean ETFs via pykrx library
    - "krx_gold" — KRX Gold Spot via KRX Open API

    Parameters
    ----------
    symbol:
        Ticker symbol (format depends on source).
    label:
        Human-readable name used in chart titles.
    ma_weights:
        Per-window MA weights for scoring.
    ma_fade_thresholds:
        Per-window fade thresholds for scoring.
    drawdown_full_pct:
        Drawdown percentage at which full score is awarded.
    source:
        Data source identifier.

    Returns
    -------
    TickerData
        A container with price history, moving averages, RSI, and
        the most recent TAIL_DAYS slice for charting.
    """
    if source == "yfinance":
        df, current_price, estimated_dates, close_price, is_live, live_time, close_date = _fetch_yfinance(symbol)
    elif source == "pykrx":
        df, current_price, estimated_dates, close_price, is_live, live_time, close_date = _fetch_pykrx(symbol)
    elif source == "krx_gold":
        df, current_price, estimated_dates, close_price, is_live, live_time, close_date = _fetch_krx_gold(symbol)
    else:
        raise ValueError(f"Unknown source: {source!r}")

    # Generate warning if live price failed (Korean tickers only)
    live_price_warning: str | None = None
    if source in ("pykrx", "krx_gold") and not is_live:
        live_price_warning = f"Live price unavailable for {label} — using last close"

    # ── Compute indicators ──
    moving_averages: dict[int, float] = {}
    ma_pct_diffs: dict[int, float] = {}
    for window in MA_WINDOWS:
        ma_value = float(df["Close"].rolling(window=window).mean().iloc[-1])
        moving_averages[window] = ma_value
        ma_pct_diffs[window] = (current_price - ma_value) / ma_value * 100

    rsi = calc_rsi(df["Close"], period=RSI_PERIOD)
    current_dd, max_dd = calc_drawdown(df["Close"], window=DRAWDOWN_WINDOW)
    buy_score = compute_buy_score(
        current_price,
        moving_averages,
        rsi,
        current_dd,
        max_dd,
        ma_weights,
        ma_fade_thresholds,
        drawdown_full_pct,
        rsi_max_score=RSI_MAX_SCORE,
        drawdown_max_score=DRAWDOWN_MAX_SCORE,
        base_amount=BASE_AMOUNT,
    )
    score_series = compute_score_series(
        df["Close"],
        rsi,
        ma_weights,
        ma_fade_thresholds,
        drawdown_full_pct,
        ma_windows=MA_WINDOWS,
        rsi_max_score=RSI_MAX_SCORE,
        drawdown_max_score=DRAWDOWN_MAX_SCORE,
        drawdown_window=DRAWDOWN_WINDOW,
    )

    return TickerData(
        symbol=symbol,
        label=label,
        ma_weights=ma_weights,
        ma_fade_thresholds=ma_fade_thresholds,
        drawdown_full_pct=drawdown_full_pct,
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
        close_price=close_price,
        is_live_price=is_live,
        live_price_warning=live_price_warning,
        live_price_time=live_time,
        close_price_date=close_date,
    )


# ── Source-specific fetch helpers ───────────────────────────────────


def _fetch_yfinance(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Fetch data via yfinance with estimated-data handling."""
    import yfinance as yf

    from src.fetchers.yfinance import download, fill_estimated_data, get_live_price

    df = download(symbol, period=DOWNLOAD_PERIOD)
    live_price = get_live_price(symbol, df)
    estimated_dates = fill_estimated_data(df, live_price)

    # Get previous close from yfinance (the official last session close)
    try:
        prev_close = float(yf.Ticker(symbol).fast_info.previous_close)
    except Exception:
        prev_close = float(df["Close"].dropna().iloc[-1])

    # Close date: last row in the DataFrame (yesterday's completed session)
    close_date = df.index[-1].strftime("%m/%d") if not df.empty else None

    # For gold (GC=F), try Naver's international gold API for a more reliable live price
    if symbol == "GC=F":
        from src.fetchers.naver import get_realtime_price_intl_gold
        naver_gold = get_realtime_price_intl_gold()
        if naver_gold:
            return df, naver_gold.price, estimated_dates, prev_close, True, naver_gold.traded_at, close_date

    # For other yfinance tickers, use fast_info timestamp
    try:
        ticker_info = yf.Ticker(symbol)
        # regularMarketTime gives the last trade timestamp
        import datetime as dt
        market_time = ticker_info.fast_info.get("regularMarketTime", None)
        if market_time:
            live_time = dt.datetime.fromtimestamp(market_time).strftime("%m/%d %H:%M")
        else:
            live_time = df.index[-1].strftime("%m/%d") + " (close)"
    except Exception:
        live_time = df.index[-1].strftime("%m/%d") + " (close)"

    is_live = True
    return df, live_price, estimated_dates, prev_close, is_live, live_time, close_date


def _fetch_pykrx(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Fetch data via pykrx (Korean ETFs) with real-time price from Naver."""
    from src.fetchers.naver import get_realtime_price_etf
    from src.fetchers.pykrx import download_pykrx, get_live_price_pykrx

    df = download_pykrx(symbol)
    close_price = get_live_price_pykrx(symbol)

    # Try real-time price from Naver
    live_result = get_realtime_price_etf(symbol)
    if live_result:
        current_price = live_result.price
        is_live = True
        live_time = live_result.traded_at
    else:
        current_price = close_price
        is_live = False
        live_time = None

    # Get close date from the last row of data
    close_date = df.index[-1].strftime("%m/%d") if not df.empty else None

    return df, current_price, [], close_price, is_live, live_time, close_date


def _fetch_krx_gold(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Fetch data via KRX Gold API with real-time price from Naver."""
    from src.config import KRX_AUTH_KEY
    from src.fetchers.krx_gold import download_krx_gold, get_live_price_krx_gold
    from src.fetchers.naver import get_realtime_price_gold

    df = download_krx_gold(KRX_AUTH_KEY)
    close_price = get_live_price_krx_gold(KRX_AUTH_KEY)

    # Try real-time price from Naver
    live_result = get_realtime_price_gold()
    if live_result:
        current_price = live_result.price
        is_live = True
        live_time = live_result.traded_at
    else:
        current_price = close_price
        is_live = False
        live_time = None

    # Get close date from the last row of data
    close_date = df.index[-1].strftime("%m/%d") if not df.empty else None

    return df, current_price, [], close_price, is_live, live_time, close_date
