from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from .identification import identify_listing
from .models import ListingDetail
from .shortlist import shortlist


def _detail(raw: dict) -> ListingDetail:
    data = dict(raw)
    for key in ("posted_at", "updated_at"):
        if data.get(key):
            data[key] = datetime.fromisoformat(data[key])
    data["included_items"] = tuple(data.get("included_items", ()))
    return ListingDetail(**data)


def build_shortlist(input_path: str | Path, output_path: str | Path) -> dict:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    details = {_detail(raw).title: _detail(raw) for raw in payload.get("accepted", [])}
    identified = shortlist(identify_listing(detail) for detail in details.values())
    rows = []
    for item in identified:
        detail = details[item.title]
        rows.append({"identification": asdict(item), "listing": {
            **asdict(detail),
            "posted_at": detail.posted_at.isoformat() if detail.posted_at else None,
            "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
        }})
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"read_only": True, "shortlist": rows}, indent=2), encoding="utf-8")
    return {"shortlisted": len(rows), "output": str(target)}
