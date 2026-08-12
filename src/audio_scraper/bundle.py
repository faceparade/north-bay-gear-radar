"""Budget-path selection with foundational recording gear prioritized."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


FOUNDATION_ROLES = frozenset({"audio_interface", "studio_monitor_system"})
MINIMUM_RECOMMENDABLE_SCORE = 40.0


@dataclass(frozen=True)
class BundleCandidate:
    name: str
    price: float
    score: float
    role: str


@dataclass(frozen=True)
class Bundle:
    budget: float
    names: tuple[str, ...]
    total_price: float
    total_score: float


def _rank(combo: tuple[BundleCandidate, ...]) -> tuple[float, ...]:
    roles = {item.role for item in combo}
    has_interface = "audio_interface" in roles
    foundation_count = len(roles & FOUNDATION_ROLES)
    total_score = sum(item.score for item in combo)
    total_price = sum(item.price for item in combo)
    # Interface ownership unlocks the rest of the user's recording setup. After
    # that hard preference, compare evidence-backed item scores and then broader
    # foundational coverage. Lower spend wins exact ties.
    return (float(has_interface), total_score, float(foundation_count), -total_price)


def choose_bundles(
    items: list[BundleCandidate], budgets: tuple[float, ...] = (100, 300, 500)
) -> dict[float, Bundle]:
    """Choose one deterministic, non-duplicative path for each budget."""

    viable = [
        item for item in items
        if item.price >= 0 and item.score >= MINIMUM_RECOMMENDABLE_SCORE
    ]
    result: dict[float, Bundle] = {}

    for budget in budgets:
        affordable = [item for item in viable if item.price <= budget]
        choices: list[tuple[BundleCandidate, ...]] = [()]
        for count in range(1, len(affordable) + 1):
            choices.extend(
                combo for combo in combinations(affordable, count)
                if sum(item.price for item in combo) <= budget
                and len({item.role for item in combo}) == len(combo)
            )
        best = max(choices, key=_rank)
        result[budget] = Bundle(
            budget=budget,
            names=tuple(item.name for item in best),
            total_price=round(sum(item.price for item in best), 2),
            total_score=round(sum(item.score for item in best), 2),
        )

    return result
