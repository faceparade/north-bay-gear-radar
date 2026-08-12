from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from collections.abc import Iterable

from .models import ListingDetail, ListingLead


ROLE_PATTERN = re.compile(
    r"\b(interface|focusrite|scarlett|audiobox|motu|antelope|apogee|studio monitor|powered (?:monitor|speaker)|"
    r"microphone|\bmic\b|synth(?:esizer)?|sampler|groovebox|drum machine|mixer|keyboard|digital piano|"
    r"electric guitar|electric bass|acoustic guitar|ukulele|looper|loop station|midi controller|pa speaker)\b",
    re.I,
)
REJECT_PATTERN = re.compile(r"\b(wanted|looking for|wtb|case only|bag only|cover only)\b", re.I)
ACCESSORY_PATTERN = re.compile(r"\b(case|bag|cover|stand)\b", re.I)


@dataclass(frozen=True, slots=True)
class FilterPolicy:
    max_age_days: int = 42
    hard_max_age_days: int = 140
    radius_miles: float = 20.0
    exceptional_value_ratio: float = 0.55


@dataclass(frozen=True, slots=True)
class Rejection:
    detail: ListingDetail
    reason: str


def prefilter_leads(leads: Iterable[ListingLead], *, max_price: float = 1000) -> list[ListingLead]:
    kept: list[ListingLead] = []
    for lead in leads:
        title = lead.title.strip()
        if not ROLE_PATTERN.search(title) or REJECT_PATTERN.search(title):
            continue
        price_match = re.search(r"([\d,]+(?:\.\d+)?)", lead.price_text)
        price = float(price_match.group(1).replace(",", "")) if price_match else None
        if price is not None and (price > max_price or price <= 1):
            continue
        if re.search(r"\b(case|bag|cover|stand)\b", title, re.I) and re.search(r"\b(case|bag|cover|stand)\b", title, re.I).start() > 0:
            if not re.search(r"\bwith\s+(?:case|bag|cover|stand)\b", title, re.I):
                continue
        kept.append(lead)
    return kept


def filter_details(
    details: Iterable[ListingDetail], *, policy: FilterPolicy, now: datetime
) -> tuple[list[ListingDetail], list[Rejection]]:
    accepted: list[ListingDetail] = []
    rejected: list[Rejection] = []
    for detail in details:
        age = detail.age_days(now)
        if age is not None and age > policy.hard_max_age_days:
            rejected.append(Rejection(detail, "older_than_20_weeks"))
        elif detail.distance_miles is not None and detail.distance_miles > policy.radius_miles:
            rejected.append(Rejection(detail, "outside_radius"))
        elif age is not None and age > policy.max_age_days:
            rejected.append(Rejection(detail, "outside_freshness_window"))
        else:
            accepted.append(detail)
    return accepted, rejected
