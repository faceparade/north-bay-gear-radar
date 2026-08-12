"""Run a broad, read-only Facebook Marketplace discovery pass via Edge CDP."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from audio_scraper.cdp_browser import CdpPage, cdp_targets, choose_page_target, collect_search
from audio_scraper.site_data import categorize_title
from audio_scraper.thumbnails import sync_listing_thumbnails

ROOT = Path(__file__).resolve().parents[1]

QUERY_GROUPS = {
    "recording_foundation": (
        "USB audio interface",
        "2 input audio interface",
        "recording mixer USB",
        "compact audio mixer",
        "studio monitor pair",
        "powered monitor speakers",
        "headphone amplifier",
        "microphone preamp",
    ),
    "creative_instruments": (
        "drum machine",
        "groovebox",
        "sampler music",
        "synth module",
        "desktop synthesizer",
        "MIDI sound module",
        "loop station",
        "music multi effects",
    ),
    "playable_instruments": (
        "digital piano keyboard",
        "vintage electronic keyboard",
        "electronic drum kit",
        "percussion instrument",
    ),
    "bundles_and_lots": (
        "home recording studio",
        "music gear bundle",
        "recording equipment lot",
        "DJ equipment lot",
    ),
    "seller_language_and_misspellings": (
        "audio interphase",
        "studio moniter speakers",
        "synthasizer keyboard",
        "drum mashine",
        "mezcladora audio",
        "equipo de grabacion",
    ),
}


def search_url(query: str) -> str:
    return f"https://www.facebook.com/marketplace/search/?query={quote_plus(query)}"


def main() -> None:
    target = choose_page_target(cdp_targets(9223), "facebook.com")
    if target is None:
        raise SystemExit("no open Facebook page on CDP port 9223")
    page = CdpPage(str(target["webSocketDebuggerUrl"]))

    previous_path = ROOT / "data" / "checkpoints" / "facebook_exact_models.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    known_ids = {str(row["listing_id"]) for row in previous.get("listings", [])}

    discovered: dict[str, dict] = {}
    failures: list[dict[str, str]] = []
    searches: list[dict[str, object]] = []

    for group, queries in QUERY_GROUPS.items():
        for query in queries:
            url = search_url(query)
            try:
                listings = collect_search(
                    page,
                    source="facebook",
                    url=url,
                    max_scrolls=5,
                    settle_seconds=.6,
                )
            except Exception as exc:
                failures.append({
                    "group": group,
                    "query": query,
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                print(f"FAIL {group:28} {query}: {type(exc).__name__}: {exc}")
                continue

            searches.append({"group": group, "query": query, "url": url, "results": len(listings)})
            print(f"{group:28} {query}: {len(listings)}")
            for listing in listings:
                row = discovered.setdefault(
                    listing.listing_id,
                    asdict(listing) | {
                        "discovery_queries": [],
                        "discovery_groups": [],
                        "new_vs_exact_checkpoint": listing.listing_id not in known_ids,
                    },
                )
                if query not in row["discovery_queries"]:
                    row["discovery_queries"].append(query)
                if group not in row["discovery_groups"]:
                    row["discovery_groups"].append(group)

    rows = sorted(
        discovered.values(),
        key=lambda row: (
            not row["new_vs_exact_checkpoint"],
            -len(row["discovery_queries"]),
            row["title"].lower(),
        ),
    )
    photo_rows = [row for row in rows if categorize_title(row["title"]) != "excluded"]
    thumbnail_summary = sync_listing_thumbnails(photo_rows, site_root=ROOT / "site")
    for row in rows:
        row.pop("image_url", None)
    payload = {
        "as_of": datetime.now().astimezone().isoformat(),
        "source": "facebook",
        "read_only": True,
        "cdp_port": 9223,
        "query_groups": {key: list(value) for key, value in QUERY_GROUPS.items()},
        "searches_completed": len(searches),
        "failures": failures,
        "searches": searches,
        "unique_listings": len(rows),
        "new_listings": sum(bool(row["new_vs_exact_checkpoint"]) for row in rows),
        "thumbnails": thumbnail_summary,
        "listings": rows,
    }
    output = ROOT / "data" / "checkpoints" / "facebook_expanded_discovery.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"wrote {len(rows)} unique listings ({payload['new_listings']} new) "
        f"to {output}; failures={len(failures)}"
    )


if __name__ == "__main__":
    main()
