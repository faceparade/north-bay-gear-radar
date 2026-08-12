from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import ListingLead, ParsedPage


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_craigslist_results(html: str, base_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[ListingLead] = []
    cards = soup.select("li.cl-static-search-result, li.cl-search-result")
    for card in cards:
        anchor = card.select_one("a[href]")
        if not anchor:
            continue
        url = urljoin(base_url, anchor.get("href", ""))
        match = re.search(r"/(?:view/d/[^/]+/|[^?#]+/d/[^/]+/)([A-Za-z0-9_-]{7,}|\d{7,})", url)
        if not match:
            match = re.search(r"/(\d{7,})\.html", url)
        if not match:
            continue
        listings.append(ListingLead(
            "craigslist", match.group(1), url,
            _text(card.select_one(".title")) or card.get("title", "").strip(),
            _text(card.select_one(".price")),
            _text(card.select_one(".location")),
        ))
    next_anchor = soup.select_one("a.button.next[href], a.cl-next-page[href]")
    return ParsedPage(
        listings,
        has_next=next_anchor is not None,
        next_url=urljoin(base_url, next_anchor.get("href")) if next_anchor else None,
        has_numbered_pages=bool(soup.select(".paginator a, .cl-page-number")),
    )


def parse_ebay_results(html: str, base_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[ListingLead] = []
    for card in soup.select("li.s-item"):
        anchor = card.select_one("a.s-item__link[href]")
        if not anchor:
            continue
        raw_url = anchor.get("href", "")
        match = re.search(r"/itm/(?:[^/?]+/)?(\d{9,15})", raw_url)
        if not match:
            continue
        listing_id = match.group(1)
        canonical = f"https://www.ebay.com/itm/{listing_id}"
        title = _text(card.select_one(".s-item__title"))
        if title.lower() in {"shop on ebay", "explore more"}:
            continue
        listings.append(ListingLead(
            "ebay", listing_id, canonical, title,
            _text(card.select_one(".s-item__price")),
            _text(card.select_one(".s-item__location")),
        ))
    next_anchor = soup.select_one("a.pagination__next[href]")
    return ParsedPage(
        listings,
        has_next=next_anchor is not None and "disabled" not in (next_anchor.get("class") or []),
        next_url=urljoin(base_url, next_anchor.get("href")) if next_anchor else None,
        has_numbered_pages=bool(soup.select(".pagination__items a")),
    )
