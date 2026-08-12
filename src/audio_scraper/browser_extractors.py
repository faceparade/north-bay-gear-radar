from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .loading import LoadObservation
from .models import ListingLead, ParsedPage
from .store import deduplicate


_ITEM_ID = {
    "facebook": re.compile(r"/marketplace/item/(\d+)"),
    "ebay": re.compile(r"/itm/(?:[^/?]+/)?(\d{9,15})"),
}


def parse_browser_payload(source: str, payload: Mapping[str, Any]) -> tuple[ParsedPage, LoadObservation]:
    if source not in _ITEM_ID:
        raise ValueError(f"unsupported browser source: {source}")
    leads: list[ListingLead] = []
    observed_ids = {str(item) for item in payload.get("listing_ids", []) if item}

    for raw in payload.get("listings", []):
        url = str(raw.get("url", ""))
        listing_id = str(raw.get("id", ""))
        if not listing_id:
            match = _ITEM_ID[source].search(url)
            listing_id = match.group(1) if match else ""
        title = str(raw.get("title", "")).strip()
        if not listing_id or not title:
            continue
        if source == "ebay" and (listing_id == "123456" or title.lower() in {"shop on ebay", "explore more"}):
            continue
        if source == "ebay":
            url = f"https://www.ebay.com/itm/{listing_id}"
        elif source == "facebook":
            url = f"https://www.facebook.com/marketplace/item/{listing_id}/"
        leads.append(ListingLead(
            source=source,
            listing_id=listing_id,
            url=url,
            title=title,
            price_text=str(raw.get("price", "")).strip(),
            location_text=str(raw.get("location", "")).strip(),
            image_url=str(raw.get("image_url", "")).strip(),
        ))
        observed_ids.add(listing_id)

    page = ParsedPage(
        listings=deduplicate(leads),
        has_next=bool(payload.get("has_next")),
        next_url=str(payload.get("next_url")) if payload.get("next_url") else None,
        has_numbered_pages=bool(payload.get("has_numbered_pages")),
        has_load_more=bool(payload.get("has_load_more")),
    )
    observation = LoadObservation(
        listing_ids=frozenset(observed_ids),
        has_next=page.has_next,
        has_numbered_pages=page.has_numbered_pages,
        has_load_more=page.has_load_more,
        scroll_height=int(payload.get("scroll_height", 0) or 0),
    )
    return page, observation
