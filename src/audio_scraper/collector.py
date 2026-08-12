from __future__ import annotations

from collections.abc import Callable

from .models import CollectionResult, ParsedPage
from .store import deduplicate


def collect_paginated(start_url: str, fetch_page: Callable[[str], ParsedPage], *, max_pages: int = 10) -> CollectionResult:
    current = start_url
    visited: set[str] = set()
    listings = []
    stop_reason = "page_limit"

    while current and len(visited) < max_pages:
        if current in visited:
            stop_reason = "repeated_page_url"
            break
        visited.add(current)
        page = fetch_page(current)
        listings.extend(page.listings)
        if not page.has_next or not page.next_url:
            stop_reason = "no_next_page"
            break
        current = page.next_url
    return CollectionResult(deduplicate(listings), len(visited), stop_reason)
