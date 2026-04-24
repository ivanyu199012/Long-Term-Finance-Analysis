"""Real-world scenario tests for the buy-in scoring system.

Each test simulates a specific market condition by constructing fake
MA values, RSI, and drawdown inputs, then verifies that
``_compute_buy_score`` produces a score in the expected range and
maps to the correct suggestion tier.

No network calls are made — all inputs are synthetic.
"""

from __future__ import annotations

import pandas as pd
import pytest

from data import _compute_buy_score


# ── Helpers ─────────────────────────────────────────────────────────


def _make_rsi(value: float) -> pd.Series:
    """Create a minimal RSI series with a single value."""
    return pd.Series([value])


def _mas_from_price(price: float, pct_diffs: dict[int, float]) -> dict[int, float]:
    """Derive MA values from a price and per-window % differences.

    ``pct_diffs`` maps window → fractional diff (e.g. 0.05 means
    price is 5 % *above* the MA).
    """
    return {w: price / (1 + d) for w, d in pct_diffs.items()}


# ── S&P 500 config ──────────────────────────────────────────────────

SP_WEIGHTS = {50: 0.5, 100: 1.5, 200: 5.0}
SP_FADE = {50: 0.07, 100: 0.10, 200: 0.15}
SP_DD_FULL = 0.25

# ── NASDAQ 100 config ───────────────────────────────────────────────

NDX_WEIGHTS = {50: 1.0, 100: 2.0, 200: 4.0}
NDX_FADE = {50: 0.10, 100: 0.14, 200: 0.20}
NDX_DD_FULL = 0.35

# ── Gold config ─────────────────────────────────────────────────────

GOLD_WEIGHTS = {50: 1.75, 100: 2.5, 200: 2.75}
GOLD_FADE = {50: 0.05, 100: 0.08, 200: 0.12}
GOLD_DD_FULL = 0.20


# ── Scenario 1: Normal bull market ──────────────────────────────────
# Price 5% above all MAs, RSI ~60, drawdown ~0%


class TestNormalBullMarket:
    """Steady uptrend — moderate scores, 'Regular buy-in' territory."""

    def test_sp500_bull(self):
        price = 5500.0
        mas = _mas_from_price(price, {50: 0.05, 100: 0.05, 200: 0.05})
        bs = _compute_buy_score(
            price, mas, _make_rsi(60), 0.0, -0.05,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        # MA fade gives partial credit, RSI=60 → 0, DD=0 → 0
        assert 3.5 <= bs.score <= 5.0
        assert "Regular" in bs.suggestion or "Reduce" in bs.suggestion

    def test_nasdaq_bull(self):
        price = 19000.0
        mas = _mas_from_price(price, {50: 0.05, 100: 0.05, 200: 0.05})
        bs = _compute_buy_score(
            price, mas, _make_rsi(60), 0.0, -0.08,
            NDX_WEIGHTS, NDX_FADE, NDX_DD_FULL,
        )
        # Wider fade bands → more partial credit than S&P
        assert 4.0 <= bs.score <= 5.5
        assert "Regular" in bs.suggestion

    def test_gold_bull(self):
        price = 2400.0
        mas = _mas_from_price(price, {50: 0.05, 100: 0.05, 200: 0.05})
        bs = _compute_buy_score(
            price, mas, _make_rsi(60), 0.0, -0.03,
            GOLD_WEIGHTS, GOLD_FADE, GOLD_DD_FULL,
        )
        # Gold has tighter bands — 5% above MA50 hits the threshold
        assert 2.0 <= bs.score <= 4.5


# ── Scenario 2: Moderate correction ─────────────────────────────────
# Price below short MAs, near/below long MA, RSI ~38, drawdown ~10%


class TestModerateCorrection:
    """Pullback — strong scores, 'Increase buy-in' territory."""

    def test_sp500_correction(self):
        price = 4800.0
        mas = _mas_from_price(price, {50: -0.03, 100: 0.0, 200: -0.05})
        bs = _compute_buy_score(
            price, mas, _make_rsi(38), -0.10, -0.12,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        # Below MA50 & MA200 → full weight, RSI 38 → half, DD 10%/25%
        assert 7.5 <= bs.score <= 9.0
        assert "Increase" in bs.suggestion or "Aggressive" in bs.suggestion

    def test_nasdaq_correction(self):
        price = 15000.0
        mas = _mas_from_price(price, {50: -0.05, 100: -0.02, 200: -0.08})
        bs = _compute_buy_score(
            price, mas, _make_rsi(38), -0.12, -0.15,
            NDX_WEIGHTS, NDX_FADE, NDX_DD_FULL,
        )
        assert 7.5 <= bs.score <= 9.5


# ── Scenario 3: Major crash ─────────────────────────────────────────
# Price well below all MAs, RSI ≤ 25, deep drawdown


class TestMajorCrash:
    """Bear market crash — near-max scores, 'Aggressive buy-in'."""

    def test_nasdaq_crash(self):
        price = 12000.0
        mas = _mas_from_price(price, {50: -0.15, 100: -0.20, 200: -0.25})
        bs = _compute_buy_score(
            price, mas, _make_rsi(25), -0.33, -0.35,
            NDX_WEIGHTS, NDX_FADE, NDX_DD_FULL,
        )
        # All MAs full (7.0) + RSI full (1.5) + DD near full (~1.41)
        assert bs.score >= 9.0
        assert "Aggressive" in bs.suggestion

    def test_sp500_crash(self):
        price = 3500.0
        mas = _mas_from_price(price, {50: -0.10, 100: -0.15, 200: -0.20})
        bs = _compute_buy_score(
            price, mas, _make_rsi(22), -0.25, -0.30,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        assert bs.score >= 9.5
        assert "Aggressive" in bs.suggestion


# ── Scenario 4: Gold parabolic rally ────────────────────────────────
# Price far above all MAs, high RSI, no drawdown


class TestGoldParabolicRally:
    """Gold way above all MAs — minimum score, don't chase."""

    def test_gold_parabolic(self):
        price = 2800.0
        mas = _mas_from_price(price, {50: 0.08, 100: 0.12, 200: 0.20})
        bs = _compute_buy_score(
            price, mas, _make_rsi(70), 0.0, -0.05,
            GOLD_WEIGHTS, GOLD_FADE, GOLD_DD_FULL,
        )
        # All MAs beyond fade threshold → 0, RSI 70 → 0, DD 0 → 0
        assert bs.score <= 1.0
        assert "Minimum" in bs.suggestion


# ── Scenario 5: Gold mild pullback ──────────────────────────────────
# Price slightly above short MA, at medium MA, below long MA


class TestGoldMildPullback:
    """Small Gold dip — solid buy signal for a mean-reverting asset."""

    def test_gold_pullback(self):
        price = 2300.0
        mas = _mas_from_price(price, {50: 0.02, 100: 0.0, 200: -0.05})
        bs = _compute_buy_score(
            price, mas, _make_rsi(42), -0.05, -0.08,
            GOLD_WEIGHTS, GOLD_FADE, GOLD_DD_FULL,
        )
        # MA50 partial, MA100 full, MA200 full, RSI half, DD partial
        assert 6.5 <= bs.score <= 8.5
        assert "Increase" in bs.suggestion or "Aggressive" in bs.suggestion


# ── Edge cases ──────────────────────────────────────────────────────


class TestEdgeCases:
    """Boundary conditions and clamping."""

    def test_score_never_exceeds_10(self):
        """Even with extreme inputs, score is clamped to 10."""
        price = 1000.0
        mas = _mas_from_price(price, {50: -0.50, 100: -0.50, 200: -0.50})
        bs = _compute_buy_score(
            price, mas, _make_rsi(10), -0.50, -0.60,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        assert bs.score == 10.0

    def test_score_never_below_zero(self):
        """All indicators neutral/negative → score stays at 0."""
        price = 6000.0
        mas = _mas_from_price(price, {50: 0.20, 100: 0.20, 200: 0.20})
        bs = _compute_buy_score(
            price, mas, _make_rsi(80), 0.0, 0.0,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        assert bs.score == 0.0

    def test_ma_at_exact_threshold_boundary(self):
        """Price exactly at fade threshold → score should be ~0."""
        price = 5000.0
        # Exactly at 7% above MA50
        mas = _mas_from_price(price, {50: 0.07, 100: 0.0, 200: 0.0})
        bs = _compute_buy_score(
            price, mas, _make_rsi(50), 0.0, 0.0,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        # MA50 at boundary → ~0, MA100 & MA200 at price → full
        assert bs.ma_breakdown[50] == pytest.approx(0.0, abs=0.01)
        assert bs.ma_breakdown[100] == pytest.approx(1.5, abs=0.01)
        assert bs.ma_breakdown[200] == pytest.approx(5.0, abs=0.01)

    def test_drawdown_capped_at_full_pct(self):
        """Drawdown beyond full_pct still gives max score, not more."""
        price = 3000.0
        mas = _mas_from_price(price, {50: 0.20, 100: 0.20, 200: 0.20})
        bs = _compute_buy_score(
            price, mas, _make_rsi(50), -0.50, -0.60,
            SP_WEIGHTS, SP_FADE, SP_DD_FULL,
        )
        assert bs.drawdown_score == pytest.approx(1.5, abs=0.01)
