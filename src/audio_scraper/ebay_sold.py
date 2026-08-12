"""Conservative title classification for exact-model eBay sold evidence."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable

MODEL_PATTERNS = {
    "Mackie ProFX10v3": re.compile(r"(?i)mackie.*pro\s*fx\s*10\s*v?3(?!\+)"),
    "Roland AIRA TR-8": re.compile(r"(?i)roland.*(?:aira\s*)?tr[- ]?8(?!s)|aira.*tr[- ]?8(?!s)"),
}

GENERAL_EXCLUDE = re.compile(
    r"(?i)\b(power supply|adapter|manual|box only|empty box|case|carry bag|bag only|"
    r"parts only|for parts|not working|untested|not tested|junk|as[ -]is|please read|"
    r"stand|mount|dust cover|decksaver|fader|potentiometer|slider|replacement|"
    r"battery cover|door)\b"
)

MODEL_EXCLUDE = {
    "Roland AIRA TR-8": re.compile(r"(?i)\b(tr[- ]?8s|tr[- ]?08|t[- ]?8|tier|oak)\b"),
    "Elektron Digitone (original)": re.compile(
        r"(?i)\b(cover|protector|decksaver|e25|remix edition|digitone\s*(?:2|ii)|digitone keys)\b"
    ),
}

# Deliberately broad lower bounds. Their only purpose is to reject malformed
# search-card prices (for example, a $269 sale extracted as $2.69). They are
# not market estimates and must never be used to impute or "fix" a price.
MIN_PLAUSIBLE_PRICE = {
    "Mackie ProFX10v3": 50.0,
    "Casio CT-X700": 50.0,
}


def is_exact_sale_title(model: str, title: str, pattern: str | None = None) -> bool:
    """Return whether a sold title is a comparable, working exact-model unit."""
    required = re.compile(pattern) if pattern is not None else MODEL_PATTERNS.get(model)
    model_exclude = MODEL_EXCLUDE.get(model)
    return bool(
        required
        and required.search(title)
        and not GENERAL_EXCLUDE.search(title)
        and not (model_exclude and model_exclude.search(title))
    )


def is_plausible_sale_price(model: str, price: float) -> bool:
    """Reject known-impossible card prices without rewriting evidence."""

    return price >= MIN_PLAUSIBLE_PRICE.get(model, 1.0)


def comparable_variant(model: str, title: str) -> str | None:
    """Label component sales while rejecting incomparable combined bundles."""

    if model == "PreSonus Eris 3.5 + Eris Sub 8BT":
        has_monitors = bool(re.search(r"(?i)3\.5", title))
        has_sub = bool(re.search(r"(?i)sub\s*8", title))
        if has_monitors and has_sub:
            return None
        if has_sub:
            return "Eris Sub 8BT"
        return "Eris 3.5 pair"
    return model


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def market_evidence(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    """Build central sold ranges, combining components only where appropriate."""

    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["model"]), str(row["variant"]))].append(float(row["sold_price"]))

    result: dict[str, dict[str, float | int]] = {}
    by_model: dict[str, list[tuple[str, list[float]]]] = defaultdict(list)
    for (model, variant), prices in grouped.items():
        by_model[model].append((variant, prices))

    for model, variants in by_model.items():
        if model == "PreSonus Eris 3.5 + Eris Sub 8BT":
            wanted = {variant: prices for variant, prices in variants}
            monitors = wanted.get("Eris 3.5 pair", [])
            sub = wanted.get("Eris Sub 8BT", [])
            if monitors and sub:
                result[model] = {
                    "used_low": round(_percentile(monitors, .2) + _percentile(sub, .2), 2),
                    "used_high": round(_percentile(monitors, .8) + _percentile(sub, .8), 2),
                    "sample_size": len(monitors) + len(sub),
                }
            continue
        prices = [price for _variant, values in variants for price in values]
        if prices:
            result[model] = {
                "used_low": round(_percentile(prices, .2), 2),
                "used_high": round(_percentile(prices, .8), 2),
                "sample_size": len(prices),
            }
    return result
