"""Allocation logic for FinAnalysis.

Maps scores to investment multipliers and computes portfolio allocation.
"""

from __future__ import annotations


def score_to_multiplier(score: float) -> float:
    """Map a buy-in score (0–10) to an investment multiplier.

    Thresholds:
        >= 8.5 → 2.25x (Aggressive)
        >= 6.5 → 1.50x (Increase)
        >= 4.5 → 1.00x (Regular)
        >= 2.5 → 0.50x (Reduce)
        <  2.5 → 0.25x (Minimum)
    """
    if score >= 8.5:
        return 2.25
    if score >= 6.5:
        return 1.5
    if score >= 4.5:
        return 1.0
    if score >= 2.5:
        return 0.5
    return 0.25
