"""Tests for compute_score_series: verify vectorized score matches point-wise computation."""

from __future__ import annotations

import pandas as pd
import pytest

from src.indicators import calc_rsi, compute_buy_score, compute_score_series


# ── Test config ─────────────────────────────────────────────────────

_MA_WEIGHTS = {50: 0.5, 100: 1.5, 200: 5.0}
_MA_FADE = {50: 0.07, 100: 0.10, 200: 0.15}
_DD_FULL = 0.25
_RSI_MAX = 1.5
_DD_MAX = 1.5
_DD_WINDOW = 500


def _make_price_series(n: int = 600) -> pd.Series:
    """Create a synthetic price series with a dip and recovery."""
    import numpy as np

    np.random.seed(42)
    # Trending up with a dip in the middle
    trend = 100 + np.cumsum(np.random.randn(n) * 0.5)
    # Add a dip
    dip = np.zeros(n)
    dip[300:350] = -20
    prices = trend + dip
    prices = prices.clip(min=10)  # no negative prices
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    return pd.Series(prices, index=dates, name="Close")


class TestScoreSeriesMatchesPointwise:
    """Verify that compute_score_series produces the same result as
    calling compute_buy_score on each day individually."""

    def test_last_day_matches(self):
        """Score series last value should match point-wise computation for last day."""
        close = _make_price_series(600)
        rsi = calc_rsi(close, period=14)

        # Vectorized
        score_series = compute_score_series(
            close, rsi, _MA_WEIGHTS, _MA_FADE, _DD_FULL,
            rsi_max_score=_RSI_MAX, drawdown_max_score=_DD_MAX,
            drawdown_window=_DD_WINDOW,
        )

        # Point-wise for last day
        mas = {w: float(close.rolling(w).mean().iloc[-1]) for w in _MA_WEIGHTS}
        peak = close.rolling(_DD_WINDOW, min_periods=1).max()
        dd = float((close - peak).iloc[-1] / peak.iloc[-1])
        max_dd = float(((close - peak) / peak).min())

        point_score = compute_buy_score(
            float(close.iloc[-1]), mas, rsi, dd, max_dd,
            _MA_WEIGHTS, _MA_FADE, _DD_FULL,
            rsi_max_score=_RSI_MAX, drawdown_max_score=_DD_MAX,
        )

        assert score_series.iloc[-1] == pytest.approx(point_score.score, abs=0.01)

    def test_score_range(self):
        """All scores should be in [0, 10]."""
        close = _make_price_series(600)
        rsi = calc_rsi(close, period=14)

        score_series = compute_score_series(
            close, rsi, _MA_WEIGHTS, _MA_FADE, _DD_FULL,
            rsi_max_score=_RSI_MAX, drawdown_max_score=_DD_MAX,
            drawdown_window=_DD_WINDOW,
        )

        assert score_series.min() >= 0.0
        assert score_series.max() <= 10.0

    def test_length_matches_input(self):
        """Score series should have the same length as the input close series."""
        close = _make_price_series(300)
        rsi = calc_rsi(close, period=14)

        score_series = compute_score_series(
            close, rsi, _MA_WEIGHTS, _MA_FADE, _DD_FULL,
        )

        assert len(score_series) == len(close)

    def test_multiple_days_match(self):
        """Spot-check several days to ensure vectorized matches point-wise."""
        close = _make_price_series(600)
        rsi = calc_rsi(close, period=14)

        score_series = compute_score_series(
            close, rsi, _MA_WEIGHTS, _MA_FADE, _DD_FULL,
            rsi_max_score=_RSI_MAX, drawdown_max_score=_DD_MAX,
            drawdown_window=_DD_WINDOW,
        )

        # Check days 300, 400, 500 (after MA warm-up)
        for idx in [300, 400, 500]:
            price = float(close.iloc[idx])
            mas = {w: float(close.rolling(w).mean().iloc[idx]) for w in _MA_WEIGHTS}
            peak = close.rolling(_DD_WINDOW, min_periods=1).max()
            dd = float((close.iloc[idx] - peak.iloc[idx]) / peak.iloc[idx])
            max_dd = float(((close[:idx + 1] - peak[:idx + 1]) / peak[:idx + 1]).min())

            rsi_slice = rsi.iloc[:idx + 1]
            point_score = compute_buy_score(
                price, mas, rsi_slice, dd, max_dd,
                _MA_WEIGHTS, _MA_FADE, _DD_FULL,
                rsi_max_score=_RSI_MAX, drawdown_max_score=_DD_MAX,
            )

            assert score_series.iloc[idx] == pytest.approx(point_score.score, abs=0.05), (
                f"Mismatch at index {idx}: series={score_series.iloc[idx]:.2f}, "
                f"point={point_score.score:.2f}"
            )
