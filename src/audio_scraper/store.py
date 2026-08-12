from __future__ import annotations

import re
from collections.abc import Iterable

from .models import ListingLead


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def deduplicate(rows: Iterable[ListingLead]) -> list[ListingLead]:
    seen_ids: set[tuple[str, str]] = set()
    seen_fingerprints: set[tuple[str, str, str, str]] = set()
    output: list[ListingLead] = []
    for row in rows:
        identity = (row.source, row.listing_id)
        fingerprint = (row.source, _norm(row.title), _norm(row.price_text), _norm(row.location_text))
        if identity in seen_ids or fingerprint in seen_fingerprints:
            continue
        seen_ids.add(identity)
        seen_fingerprints.add(fingerprint)
        output.append(row)
    return output
