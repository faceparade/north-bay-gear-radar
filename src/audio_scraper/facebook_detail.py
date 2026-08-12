from __future__ import annotations

from collections.abc import Mapping
import re
import time
from typing import Any

from .cdp_browser import CdpPage


_DETAIL_SCRIPT = r'''(() => {
  const root = document.querySelector('main') || document.body;
  const title = document.querySelector('h1')?.innerText?.trim() || '';
  return {
    url: location.href,
    title,
    text: (root?.innerText || '').trim(),
  };
})()'''

_MONEY = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")
_ITEM_ID = re.compile(r"/marketplace/item/(\d+)")
_LISTED = re.compile(r"^Listed(?:\s+(.+?))?\s+in\s+.+$", re.IGNORECASE)
_LOCATION = re.compile(r"^[^\n,]{1,80},\s*[A-Z]{2}$")
_DESCRIPTION_END = {
    "seller information",
    "seller details",
    "shipping & returns",
    "delivery options",
    "related searches",
    "send seller a message",
}


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\xa0", " ").splitlines() if line.strip()]


def parse_facebook_detail_text(text: str, *, title: str = "") -> dict[str, str]:
    """Extract listing-owned detail fields from the visible Marketplace item text.

    Parsing deliberately stops before seller metadata and recommendations so neither
    can be mistaken for the listing description or its price evidence.
    """

    lines = _clean_lines(text)
    start = next((index for index, line in enumerate(lines) if title and line == title), -1)
    listing_lines = lines[start + 1 :] if start >= 0 else lines

    message_index = next(
        (index for index, line in enumerate(listing_lines) if line.casefold() in {"message", "buy now"}),
        len(listing_lines),
    )
    header = listing_lines[:message_index]
    header_prices = [match.group(0).replace(" ", "") for line in header for match in _MONEY.finditer(line)]
    detail_price_text = header_prices[-1] if header_prices else ""

    listing_age_text = ""
    for line in header + listing_lines[: min(len(listing_lines), message_index + 4)]:
        match = _LISTED.match(line)
        if match:
            listing_age_text = (match.group(1) or "").strip()
            break

    details_index = next(
        (index for index, line in enumerate(listing_lines) if line.casefold() == "details"),
        -1,
    )
    condition = ""
    description_lines: list[str] = []
    if details_index >= 0:
        cursor = details_index + 1
        if cursor < len(listing_lines) and listing_lines[cursor].casefold() == "condition":
            cursor += 1
            if cursor < len(listing_lines):
                condition = listing_lines[cursor]
                cursor += 1
        for line in listing_lines[cursor:]:
            lowered = line.casefold()
            if lowered in _DESCRIPTION_END or lowered.startswith("seller information"):
                break
            if lowered == "location is approximate":
                break
            if _LOCATION.fullmatch(line) and cursor < len(listing_lines):
                # Marketplace repeats the listing location immediately before
                # "Location is approximate"; it is not seller-authored prose.
                next_index = listing_lines.index(line, cursor) + 1
                if next_index < len(listing_lines) and listing_lines[next_index].casefold() == "location is approximate":
                    break
            description_lines.append(line)

    return {
        "detail_price_text": detail_price_text,
        "listing_age_text": listing_age_text,
        "condition": condition,
        "description": "\n".join(description_lines).strip(),
    }


def collect_facebook_detail(
    page: CdpPage,
    row: Mapping[str, Any],
    *,
    settle_seconds: float = 0.7,
) -> dict[str, str]:
    url = str(row.get("url", ""))
    page.navigate(url, timeout=30)
    time.sleep(settle_seconds)
    payload = page.evaluate(_DETAIL_SCRIPT)
    if not isinstance(payload, Mapping):
        raise RuntimeError("Facebook detail extraction returned a non-object payload")
    final_url = str(payload.get("url", ""))
    final_match = _ITEM_ID.search(final_url)
    if final_match is None:
        raise RuntimeError(f"Facebook detail navigation left the listing page: {final_url}")
    requested_id = str(row.get("listing_id", "")).strip()
    if requested_id and final_match.group(1) != requested_id:
        raise RuntimeError(
            "Facebook detail navigation opened a different listing: "
            f"requested {requested_id}, received {final_match.group(1)}"
        )
    visible_text = str(payload.get("text", ""))
    if not visible_text:
        raise RuntimeError("Facebook detail page had no visible text")
    page_title = str(payload.get("title", "")).strip()
    parsed = parse_facebook_detail_text(
        visible_text,
        title=page_title or str(row.get("title", "")),
    )
    if page_title:
        parsed["detail_title"] = page_title
    return parsed
