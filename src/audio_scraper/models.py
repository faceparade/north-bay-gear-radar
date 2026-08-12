from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class SearchTarget:
    source: str
    label: str
    kind: str
    url: str


@dataclass(frozen=True, slots=True)
class ListingLead:
    source: str
    listing_id: str
    url: str
    title: str
    price_text: str = ""
    location_text: str = ""
    image_url: str = ""


@dataclass(frozen=True, slots=True)
class ListingDetail:
    source: str
    listing_id: str
    url: str
    title: str
    asking_price: float | None = None
    price_text: str = ""
    location_text: str = ""
    description: str = ""
    condition: str = ""
    posted_at: datetime | None = None
    updated_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_miles: float | None = None
    included_items: tuple[str, ...] = ()
    image_url: str = ""

    @property
    def price(self) -> float | None:
        return self.asking_price

    def age_days(self, now: datetime | None = None) -> int | None:
        if self.posted_at is None:
            return None
        current = now or datetime.now(timezone.utc)
        posted = self.posted_at
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return max(0, (current.astimezone(timezone.utc) - posted.astimezone(timezone.utc)).days)


@dataclass(slots=True)
class ParsedPage:
    listings: list[ListingLead] = field(default_factory=list)
    has_next: bool = False
    next_url: str | None = None
    has_numbered_pages: bool = False
    has_load_more: bool = False


@dataclass(slots=True)
class CollectionResult:
    listings: list[ListingLead]
    pages_visited: int
    stop_reason: str
