"""Tests for the backtest module using synthetic price data."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest import BacktestResult, _run_strategy, run_backtest
from src.allocation import score_to_multiplier


# ── Multiplier mapping tests ────────────────────────────────────────


class TestScoreToMultiplier:
    """Verify multiplier thresholds match _score_to_suggestion."""

    def test_aggressive(self):
        assert score_to_multiplier(9.0) == 2.25

    def test_increase(self):
        assert score_to_multiplier(7.0) == 1.5

    def test_regular(self):
        assert score_to_multiplier(5.0) == 1.0

    def test_reduce(self):
        assert score_to_multiplier(3.0) == 0.5

    def test_minimum(self):
        assert score_to_multiplier(1.0) == 0.25

    def test_boundary_8_5(self):
        assert score_to_multiplier(8.5) == 2.25

    def test_boundary_6_5(self):
        assert score_to_multiplier(6.5) == 1.5


# ── Strategy simulation tests ──────────────────────────────────────


def _make_monthly_prices(values: list[float]) -> pd.Series:
    """Create a monthly price series from a list of values."""
    dates = pd.date_range("2020-01-31", periods=len(values), freq="ME")
    return pd.Series(values, index=dates)


class TestRunStrategy:
    """Test the core DCA simulation."""

    def test_flat_dca_constant_price(self):
        """Flat DCA with constant price → return = 0%."""
        prices = _make_monthly_prices([100.0] * 12)
        result = _run_strategy(prices, multipliers=None)
        assert result.n_months == 12
        assert result.total_return_pct == pytest.approx(0.0, abs=0.01)

    def test_flat_dca_rising_price(self):
        """Flat DCA with steadily rising price → positive return."""
        prices = _make_monthly_prices([100.0 + i * 5 for i in range(12)])
        result = _run_strategy(prices, multipliers=None)
        assert result.total_return_pct > 0

    def test_flat_dca_falling_price(self):
        """Flat DCA with steadily falling price → negative return."""
        prices = _make_monthly_prices([200.0 - i * 10 for i in range(12)])
        result = _run_strategy(prices, multipliers=None)
        assert result.total_return_pct < 0

    def test_score_dca_buys_more_at_low(self):
        """Score DCA with higher multiplier at low prices should outperform flat."""
        # V-shaped: drops then recovers
        values = [100, 90, 80, 70, 60, 50, 60, 70, 80, 90, 100, 110]
        prices = _make_monthly_prices(values)

        flat = _run_strategy(prices, multipliers=None)

        # Higher multiplier during the dip, lower during recovery
        mults = pd.Series(
            [0.5, 1.0, 1.5, 2.0, 2.25, 2.25, 2.0, 1.5, 1.0, 0.5, 0.25, 0.25],
            index=prices.index,
        )
        score = _run_strategy(prices, multipliers=mults)

        # Score strategy should have better return (bought more cheap units)
        assert score.total_return_pct > flat.total_return_pct

    def test_max_drawdown_is_negative(self):
        """Max drawdown should be negative or zero."""
        prices = _make_monthly_prices([100, 90, 80, 70, 80, 90])
        result = _run_strategy(prices, multipliers=None)
        assert result.max_drawdown_pct <= 0

    def test_normalized_same_total_invested(self):
        """Normalized score DCA should invest the same total as flat DCA."""
        values = [100, 90, 80, 70, 80, 90, 100, 110, 120, 110, 100, 105]
        prices = _make_monthly_prices(values)

        flat = _run_strategy(prices, multipliers=None)

        mults = pd.Series(
            [0.5, 1.0, 1.5, 2.0, 1.5, 1.0, 0.5, 0.25, 0.25, 0.5, 1.0, 1.0],
            index=prices.index,
        )
        raw = _run_strategy(prices, multipliers=mults)

        # Normalize
        scale = flat.total_invested / raw.total_invested
        normalized = _run_strategy(prices, multipliers=mults * scale)

        assert normalized.total_invested == pytest.approx(flat.total_invested, rel=0.01)
