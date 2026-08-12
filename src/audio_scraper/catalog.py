"""Catalog records and validation for sourced market/compatibility claims."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class CatalogEntry:
    model: str
    release_year: int | None = None
    msrp: float | None = None
    used_low: float | None = None
    used_high: float | None = None
    sources: tuple[str, ...] = ()
    windows_status: str = "unknown"
    compatibility_notes: str = ""


def _is_web_source(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_catalog(entries: list[CatalogEntry]) -> list[str]:
    """Return human-readable errors without discarding partially researched rows."""

    errors: list[str] = []
    for index, entry in enumerate(entries):
        label = entry.model.strip() or f"entry {index}"
        if not entry.model.strip():
            errors.append(f"{label}: model is required")

        if entry.used_low is not None and entry.used_high is not None and entry.used_low > entry.used_high:
            errors.append(f"{label}: used range low exceeds high")
        if entry.used_low is not None and entry.used_low < 0:
            errors.append(f"{label}: used range cannot be negative")
        if entry.used_high is not None and entry.used_high < 0:
            errors.append(f"{label}: used range cannot be negative")
        if entry.msrp is not None and entry.msrp < 0:
            errors.append(f"{label}: MSRP cannot be negative")
        if entry.release_year is not None and not 1900 <= entry.release_year <= 2100:
            errors.append(f"{label}: release year is implausible")

        has_claims = any((
            entry.release_year is not None,
            entry.msrp is not None,
            entry.used_low is not None,
            entry.used_high is not None,
            entry.windows_status != "unknown",
            bool(entry.compatibility_notes.strip()),
        ))
        valid_sources = tuple(source for source in entry.sources if _is_web_source(source))
        if has_claims and not valid_sources:
            errors.append(f"{label}: at least one valid source URL is required for market or compatibility claims")
        elif len(valid_sources) != len(entry.sources):
            errors.append(f"{label}: every source must be an http(s) URL")

    return errors
