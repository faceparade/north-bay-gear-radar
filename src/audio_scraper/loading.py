from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib


class LoadingMode(str, Enum):
    UNKNOWN = "unknown"
    STATIC = "static"
    PAGINATION = "pagination"
    INFINITE_SCROLL = "infinite_scroll"
    LOAD_MORE = "load_more"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class LoadObservation:
    listing_ids: frozenset[str]
    has_next: bool = False
    has_numbered_pages: bool = False
    has_load_more: bool = False
    scroll_height: int = 0

    @property
    def fingerprint(self) -> str:
        joined = "\x1f".join(sorted(self.listing_ids))
        return hashlib.sha256(joined.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class LoadingDecision:
    mode: LoadingMode
    should_scroll: bool = False
    should_click_next: bool = False
    should_click_load_more: bool = False
    stop: bool = False
    reason: str = "continue"


class LoadingDetector:
    def __init__(self, *, no_growth_limit: int = 3, repeated_fingerprint_limit: int = 2):
        self.no_growth_limit = no_growth_limit
        self.repeated_fingerprint_limit = repeated_fingerprint_limit

    def classify(self, observations: list[LoadObservation]) -> LoadingDecision:
        if not observations:
            return LoadingDecision(LoadingMode.UNKNOWN, stop=True, reason="no_observations")

        latest = observations[-1]
        controls_pagination = latest.has_next or latest.has_numbered_pages
        grew = any(
            len(current.listing_ids - previous.listing_ids) > 0
            or current.scroll_height > previous.scroll_height
            for previous, current in zip(observations, observations[1:])
        )

        if controls_pagination and latest.has_load_more:
            mode = LoadingMode.HYBRID
        elif latest.has_load_more:
            mode = LoadingMode.LOAD_MORE
        elif controls_pagination:
            mode = LoadingMode.PAGINATION
        elif grew:
            mode = LoadingMode.INFINITE_SCROLL
        else:
            mode = LoadingMode.STATIC

        recent = observations[-(self.no_growth_limit + 1):]
        if len(recent) == self.no_growth_limit + 1:
            no_growth = all(
                current.listing_ids.issubset(previous.listing_ids)
                and current.scroll_height <= previous.scroll_height
                for previous, current in zip(recent, recent[1:])
            )
            if no_growth and not controls_pagination:
                return LoadingDecision(mode, stop=True, reason="no_new_listings")

        repeats_needed = self.repeated_fingerprint_limit + 1
        if len(observations) >= repeats_needed:
            recent_fingerprints = [item.fingerprint for item in observations[-repeats_needed:]]
            if len(set(recent_fingerprints)) == 1 and controls_pagination:
                return LoadingDecision(mode, stop=True, reason="repeated_fingerprint")

        return LoadingDecision(
            mode,
            should_scroll=mode in {LoadingMode.INFINITE_SCROLL, LoadingMode.STATIC, LoadingMode.HYBRID},
            should_click_next=controls_pagination,
            should_click_load_more=latest.has_load_more,
        )
