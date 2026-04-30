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
        df, current_price, estimated_dates = _fetch_yfinance(symbol)
    elif source == "pykrx":
        df, current_price, estimated_dates = _fetch_pykrx(symbol)
    elif source == "krx_gold":
        df, current_price, estimated_dates = _fetch_krx_gold(symbol)
    else:
        raise ValueError(f"Unknown source: {source!r}")

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
    )


# ── Source-specific fetch helpers ───────────────────────────────────


def _fetch_yfinance(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Fetch data via yfinance with estimated-data handling."""
    from src.fetchers.yfinance import download, fill_estimated_data, get_live_price

    df = download(symbol, period=DOWNLOAD_PERIOD)
    current_price = get_live_price(symbol, df)
    estimated_dates = fill_estimated_data(df, current_price)
    return df, current_price, estimated_dates


def _fetch_pykrx(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Fetch data via pykrx (Korean ETFs). Placeholder until Phase 2."""
    raise NotImplementedError("pykrx fetcher not yet implemented (Phase 2)")


def _fetch_krx_gold(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Fetch data via KRX Gold API. Placeholder until Phase 3."""
    raise NotImplementedError("KRX Gold fetcher not yet implemented (Phase 3)")
