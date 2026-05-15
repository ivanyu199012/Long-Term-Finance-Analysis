"""Tests for allocation logic: weight normalization, floor enforcement, edge cases."""

from __future__ import annotations

import pytest

from src.allocation import enforce_weight_floors


class TestEnforceWeightFloors:
    """Test the shared floor enforcement helper."""

    def test_no_floors_needed(self):
        """When all weights are above floors, return unchanged."""
        weights = {"A": 0.5, "B": 0.3, "C": 0.2}
        min_weights = {"A": 0.1, "B": 0.1, "C": 0.1}
        result = enforce_weight_floors(weights, min_weights)
        assert result == weights

    def test_one_below_floor(self):
        """One weight below floor gets raised, others redistributed."""
        weights = {"A": 0.05, "B": 0.55, "C": 0.40}
        min_weights = {"A": 0.20, "B": 0.05, "C": 0.05}
        result = enforce_weight_floors(weights, min_weights)

        assert result["A"] == 0.20
        assert sum(result.values()) == pytest.approx(1.0)
        # B and C share the remaining 0.80 proportionally
        assert result["B"] > result["C"]

    def test_multiple_below_floor(self):
        """Multiple weights below floor all get raised."""
        weights = {"A": 0.02, "B": 0.03, "C": 0.95}
        min_weights = {"A": 0.10, "B": 0.10, "C": 0.05}
        result = enforce_weight_floors(weights, min_weights)

        assert result["A"] == 0.10
        assert result["B"] == 0.10
        assert result["C"] == pytest.approx(0.80)
        assert sum(result.values()) == pytest.approx(1.0)

    def test_sum_always_one(self):
        """Result always sums to 1.0 regardless of input."""
        weights = {"A": 0.01, "B": 0.01, "C": 0.98}
        min_weights = {"A": 0.40, "B": 0.40, "C": 0.05}
        result = enforce_weight_floors(weights, min_weights)
        assert sum(result.values()) == pytest.approx(1.0)

    def test_all_at_floor(self):
        """When all weights equal their floors, no change needed."""
        weights = {"A": 0.40, "B": 0.30, "C": 0.30}
        min_weights = {"A": 0.40, "B": 0.30, "C": 0.30}
        result = enforce_weight_floors(weights, min_weights)
        assert result == weights
