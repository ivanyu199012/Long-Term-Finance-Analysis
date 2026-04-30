"""Allocation logic for FinAnalysis.

Maps scores to investment multipliers and computes portfolio allocation.
Used by both the dashboard and the backtest engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Allocation, TickerData


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


def compute_allocation(
    tickers: list[TickerData],
    ticker_configs: list[dict] | None = None,
    monthly_budget: float | None = None,
) -> list[Allocation]:
    """Compute portfolio allocation from scores and base weights.

    Parameters
    ----------
    tickers:
        List of TickerData with computed buy_score.
    ticker_configs:
        List of ticker config dicts (must have 'symbol', 'base_weight',
        'min_weight'). If None, falls back to TICKERS from config.
    monthly_budget:
        Total monthly budget (₩). If None, falls back to MONTHLY_BUDGET
        from config.

    Steps:
    1. Multiply each ticker's base_weight by its score multiplier.
    2. Normalize to 100%.
    3. Enforce minimum weight floors, re-normalizing the remainder.
    4. Convert to ₩ amounts using monthly_budget.
    """
    from src.models import Allocation as AllocationModel

    # Resolve defaults from config if not provided
    if ticker_configs is None:
        from src.config import TICKERS
        ticker_configs = TICKERS
    if monthly_budget is None:
        from src.config import MONTHLY_BUDGET
        monthly_budget = MONTHLY_BUDGET

    # Step 1: raw weights = base_weight × multiplier
    raw: dict[str, float] = {}
    base_weights: dict[str, float] = {}
    min_weights: dict[str, float] = {}
    for td in tickers:
        mult = score_to_multiplier(td.buy_score.score)
        cfg = next(t for t in ticker_configs if t["symbol"] == td.symbol)
        base_weights[td.label] = cfg["base_weight"]
        min_weights[td.label] = cfg["min_weight"]
        raw[td.label] = cfg["base_weight"] * mult

    # Step 2: normalize to 100%
    total = sum(raw.values())
    weights = {k: v / total for k, v in raw.items()}

    # Step 3: enforce minimum floors
    # If any weight is below its floor, set it to the floor and
    # redistribute the remaining budget proportionally.
    floored: dict[str, float] = {}
    free_labels: list[str] = []
    locked_total = 0.0

    for label, w in weights.items():
        if w < min_weights[label]:
            floored[label] = min_weights[label]
            locked_total += min_weights[label]
        else:
            free_labels.append(label)

    if floored:
        remaining = 1.0 - locked_total
        free_total = sum(weights[l] for l in free_labels)
        for label in free_labels:
            floored[label] = (
                weights[label] / free_total * remaining
                if free_total > 0
                else remaining / len(free_labels)
            )
        weights = floored

    # Step 4: convert to amounts
    result = []
    for td in tickers:
        w = weights[td.label]
        result.append(AllocationModel(
            label=td.label,
            weight_pct=w * 100,
            amount=w * monthly_budget,
        ))
    return result
