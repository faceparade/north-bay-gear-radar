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
