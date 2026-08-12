from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .detail_parser import parse_craigslist_detail
from .filters import FilterPolicy, filter_details, prefilter_leads
from .http_collectors import HttpFetcher
from .models import ListingLead


def _serializable(item):
    data = asdict(item)
    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data


def inspect_craigslist(
    raw_path: str | Path,
    output_path: str | Path,
    *,
    fetcher=None,
    origin: tuple[float, float],
    max_candidates: int = 100,
    policy: FilterPolicy | None = None,
    now: datetime | None = None,
) -> dict:
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    leads = [ListingLead(**item) for item in raw.get("listings", [])]
    candidates = prefilter_leads(leads)[:max_candidates]
    http = fetcher or HttpFetcher()
    details = []
    failures = []
    for lead in candidates:
        try:
            html, _ = http.get(lead.url)
            details.append(parse_craigslist_detail(html, lead, origin=origin))
        except Exception as exc:
            failures.append({"listing_id": lead.listing_id, "error": f"{type(exc).__name__}: {exc}"})
    accepted, rejected = filter_details(
        details,
        policy=policy or FilterPolicy(),
        now=now or datetime.now(timezone.utc),
    )
    payload = {
        "source": "craigslist",
        "read_only": True,
        "origin": {"latitude": origin[0], "longitude": origin[1]},
        "prefiltered": len(candidates),
        "inspected": len(details),
        "accepted": [_serializable(item) for item in accepted],
        "rejected": [{"reason": item.reason, "detail": _serializable(item.detail)} for item in rejected],
        "failures": failures,
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)
    return {
        "prefiltered": len(candidates),
        "inspected": len(details),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "failures": len(failures),
    }
