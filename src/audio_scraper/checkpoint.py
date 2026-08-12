from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from collections.abc import Iterable

from .models import ListingLead


def write_checkpoint(
    path: str | Path,
    *,
    source: str,
    searches_completed: int,
    listings: Iterable[ListingLead],
    metadata: dict | None = None,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    payload = {
        "source": source,
        "read_only": True,
        "searches_completed": searches_completed,
        "metadata": metadata or {},
        "listings": [asdict(item) for item in listings],
    }
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)
