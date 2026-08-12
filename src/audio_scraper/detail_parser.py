from __future__ import annotations

from datetime import datetime
import math
import re

from bs4 import BeautifulSoup

from .models import ListingDetail, ListingLead


def _parse_price(text: str) -> float | None:
    match = re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)", text)
    return float(match.group(1).replace(",", "")) if match else None


def _haversine_miles(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*origin, *destination))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3958.7613 * 2 * math.asin(math.sqrt(a))


def _datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_craigslist_detail(html: str, lead: ListingLead, *, origin: tuple[float, float]) -> ListingDetail:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one("#titletextonly")
    price_text = (soup.select_one(".price").get_text(" ", strip=True) if soup.select_one(".price") else lead.price_text)
    body = soup.select_one("#postingbody")
    description = body.get_text(" ", strip=True) if body else ""
    description = re.sub(r"^QR Code Link to This Post\s*", "", description, flags=re.I).strip()
    time_values = [node.get("datetime") for node in soup.select("time[datetime]")]
    parsed_times: list[datetime] = []
    for value in time_values:
        parsed = _datetime(value)
        if parsed and parsed not in parsed_times:
            parsed_times.append(parsed)
    posted = parsed_times[0] if parsed_times else None
    updated = parsed_times[-1] if len(parsed_times) > 1 else None
    map_node = soup.select_one("#map")
    latitude = float(map_node.get("data-latitude")) if map_node and map_node.get("data-latitude") else None
    longitude = float(map_node.get("data-longitude")) if map_node and map_node.get("data-longitude") else None
    distance = _haversine_miles(origin, (latitude, longitude)) if latitude is not None and longitude is not None else None
    attrs = [node.get_text(" ", strip=True) for node in soup.select(".attrgroup span")]
    condition = ""
    for attr in attrs:
        match = re.match(r"condition\s*:\s*(.+)", attr, flags=re.I)
        if match:
            condition = match.group(1).strip()
            break
    included = tuple(sorted(set(re.findall(
        r"\b(?:usb cable|power cable|power cord|case|manual|shock mount|mic clip|windscreen|stand|brackets|boom|pop filter|xlr cable)s?\b",
        description,
        flags=re.I,
    ))))
    image_anchor = soup.select_one('.gallery a[href*="craigslist"], a.thumb[href*="craigslist"]')
    image_node = soup.select_one('img[src*="craigslist"]')
    image_url = str(
        image_anchor.get("href") if image_anchor else image_node.get("src") if image_node else ""
    )
    return ListingDetail(
        source=lead.source,
        listing_id=lead.listing_id,
        url=lead.url,
        title=title_node.get_text(" ", strip=True) if title_node else lead.title,
        asking_price=_parse_price(price_text),
        price_text=price_text,
        location_text=lead.location_text,
        description=description,
        condition=condition,
        posted_at=posted,
        updated_at=updated,
        latitude=latitude,
        longitude=longitude,
        distance_miles=distance,
        included_items=included,
        image_url=image_url,
    )
