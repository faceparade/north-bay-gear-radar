"""Evidence-backed candidate scoring.

The scorer deliberately separates seller/listing qualities from market value so
missing price research cannot silently turn into invented value points.
"""

from __future__ import annotations

from dataclasses import dataclass, field


RISK_PENALTIES: dict[str, int] = {
    "seller_disclosed_defect": 12,
    "legacy_driver_risk": 6,
    "exact_revision_unknown": 5,
    "missing_power_supply": 4,
    "parts_or_repair": 15,
}


@dataclass(frozen=True)
class PricingEvidence:
    used_low: float | None = None
    used_high: float | None = None
    confidence: float = 0.0

    @property
    def usable(self) -> bool:
        return (
            self.confidence > 0
            and self.used_low is not None
            and self.used_high is not None
            and self.used_low >= 0
            and self.used_high >= self.used_low
        )


@dataclass(frozen=True)
class ScoreInputs:
    gap_fit: float
    condition: float
    compatibility: float
    completeness: float
    freshness_proximity: float
    fun_factor: float
    resale_safety: float
    asking_price: float | None
    pricing: PricingEvidence = field(default_factory=PricingEvidence)
    risk_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoreResult:
    total: float
    value_points: float
    penalty_points: float
    notes: tuple[str, ...] = ()


# These are deliberately broad setup-fit profiles, not model-specific claims.
# They let the dashboard give every active listing a useful initial ordering
# while exact-model research continues to provide the higher-confidence scores.
CATEGORY_FIT_DIMENSIONS: dict[str, tuple[float, float, float, float, float, float, float]] = {
    # gap_fit, condition, compatibility, completeness, proximity, fun, resale
    "interfaces": (22, 4, 15, 5, 5, 5, 6),
    "mixers": (17, 4, 12, 5, 5, 5, 6),
    "monitors": (16, 4, 11, 5, 5, 5, 6),
    "microphones-preamps": (15, 4, 10, 5, 5, 6, 6),
    "synths-modules": (17, 4, 10, 5, 5, 10, 6),
    "samplers-drum-machines": (18, 4, 11, 5, 5, 9, 6),
    "recorders-samplers": (16, 4, 9, 5, 5, 8, 5),
    "keyboards-controllers": (16, 4, 12, 5, 5, 8, 6),
    "electronic-drums": (19, 4, 12, 5, 5, 8, 6),
    "drums-percussion": (12, 4, 8, 5, 5, 8, 5),
    "guitars-acoustic": (10, 4, 7, 5, 5, 8, 5),
    "loopers-effects": (15, 4, 10, 5, 5, 9, 6),
    "dj-gear": (12, 4, 9, 5, 5, 8, 5),
    "pa-headphones-utilities": (13, 4, 10, 5, 5, 5, 5),
    "bundles": (14, 4, 8, 6, 5, 7, 5),
    "other-audio": (8, 4, 6, 4, 5, 5, 4),
}


def _value_points(asking_price: float | None, pricing: PricingEvidence) -> tuple[float, tuple[str, ...]]:
    if asking_price is None or asking_price < 0 or not pricing.usable:
        return 0.0, ("insufficient_price_evidence",)

    low = float(pricing.used_low)
    high = float(pricing.used_high)
    confidence = min(1.0, max(0.0, pricing.confidence))

    if asking_price <= low:
        # An item at the bottom of a supported range is already a strong value
        # (21/25). A meaningful discount below that floor earns up to four more.
        discount = 1.0 if low == 0 and asking_price == 0 else (
            0.0 if low == 0 else min(1.0, (low - asking_price) / low)
        )
        raw = 21.0 + 4.0 * discount
    elif asking_price <= high:
        span = max(high - low, 1.0)
        raw = 18.0 - 10.0 * ((asking_price - low) / span)
    else:
        # Above the observed range, retain at most a few points and quickly
        # decay to zero rather than allowing an expensive item to look useful.
        overage = (asking_price - high) / max(high, 1.0)
        raw = max(0.0, 8.0 * (1.0 - overage))

    # Evidence confidence is a haircut, not a second estimate of price value.
    # Once evidence is usable, 90% confidence should not erase a clearly large
    # discount; thin but nonzero evidence receives a larger (up to 25%) haircut.
    confidence_factor = 0.75 + 0.25 * confidence
    return round(raw * confidence_factor, 2), ()


def score_candidate(inputs: ScoreInputs) -> ScoreResult:
    """Return a transparent score; caller-provided dimensions are additive."""

    value, notes = _value_points(inputs.asking_price, inputs.pricing)
    penalty = float(sum(RISK_PENALTIES.get(flag, 0) for flag in set(inputs.risk_flags)))
    base = sum((
        inputs.gap_fit,
        inputs.condition,
        inputs.compatibility,
        inputs.completeness,
        inputs.freshness_proximity,
        inputs.fun_factor,
        inputs.resale_safety,
    ))
    total = round(max(0.0, base + value - penalty), 2)
    return ScoreResult(total=total, value_points=value, penalty_points=penalty, notes=notes)


def score_category_screening_fit(*, category: str, asking_price: float | None) -> ScoreResult:
    """Score an unreviewed active listing without inventing model or market data.

    A missing asking price is intentionally allowed: it receives no value points,
    but the listing still gets a transparent setup-fit score rather than silently
    disappearing from the Best Fit ordering.
    """

    dimensions = CATEGORY_FIT_DIMENSIONS.get(category, CATEGORY_FIT_DIMENSIONS["other-audio"])
    result = score_candidate(
        ScoreInputs(
            gap_fit=dimensions[0],
            condition=dimensions[1],
            compatibility=dimensions[2],
            completeness=dimensions[3],
            freshness_proximity=dimensions[4],
            fun_factor=dimensions[5],
            resale_safety=dimensions[6],
            asking_price=asking_price,
        )
    )
    return ScoreResult(
        total=result.total,
        value_points=result.value_points,
        penalty_points=result.penalty_points,
        notes=(
            "category_screening_fit",
            "exact_model_condition_and_market_value_unverified",
            *result.notes,
        ),
    )
