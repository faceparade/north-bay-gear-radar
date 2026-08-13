"""Run a broad, read-only Facebook Marketplace discovery pass via Edge CDP."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from audio_scraper.cdp_browser import CdpPage, cdp_targets, choose_page_target, collect_search
from audio_scraper.facebook_detail import collect_facebook_detail
from audio_scraper.site_data import PLACEHOLDER_PRICES, categorize_title, parse_price
from audio_scraper.thumbnails import sync_listing_thumbnails

ROOT = Path(__file__).resolve().parents[1]

# Marketplace categories establish broad inventory first.  Keyword searches then
# catch relevant gear listed in adjacent categories or described imprecisely.
# Explicit newest-first order makes the recurring shallow pass useful: after the
# initial archive backfill, the first few loaded pages contain newly listed gear.
# These are the authenticated Marketplace category links exposed for the configured
# Novato / 20-mile buying location.  On 2026-08-12, selecting the UI menu option
# “Date listed: Newest first” transformed this shape by adding
# ``sortBy=creation_time_descend`` and showed “Sort by: Date listed: Newest first”.
# The generic /marketplace/category/... paths redirect to the Marketplace home in
# this session, so retain the UI-issued location/category search shape instead.
CATEGORY_URLS = {
    "musical_instruments": "https://www.facebook.com/marketplace/107325029289930/search/?category_id=1078592699170502&query=Musical%20Instruments&exact=false&referral_ui_component=category_menu_item&sortBy=creation_time_descend",
    "hobbies": "https://www.facebook.com/marketplace/107325029289930/search/?category_id=459026188375950&query=Hobbies&exact=false&referral_ui_component=category_menu_item&sortBy=creation_time_descend",
    "electronics": "https://www.facebook.com/marketplace/107325029289930/search/?category_id=479353692612078&query=Electronics&exact=false&referral_ui_component=category_menu_item&sortBy=creation_time_descend",
}
INITIAL_CATEGORY_SCROLLS = 25
# Five scrolls is too shallow for a recurring inventory pass: Marketplace can
# interleave promoted and older items ahead of a fresh local listing.  Keep the
# one-time archive backfill bounded, but use a materially wider newest-first
# window on every refresh so that a single query's ranking does not decide
# recall.
REFRESH_CATEGORY_SCROLLS = 12
SEARCH_SCROLLS = 12


def category_discovery_plan(*, has_completed_initial_backfill: bool) -> list[tuple[str, str, int]]:
    """Return newest-first category passes, deep once and shallow thereafter."""
    scrolls = REFRESH_CATEGORY_SCROLLS if has_completed_initial_backfill else INITIAL_CATEGORY_SCROLLS
    return [("category", category, scrolls) for category in CATEGORY_URLS]

QUERY_GROUPS = {
    "recording_foundation": (
        # Start with Marketplace's natural broad query, then add narrower
        # discovery terms for listings sellers describe differently.
        "audio interface",
        "USB audio interface",
        "PreSonus AudioBox",
        "Focusrite Scarlett",
        "Behringer UMC",
        "Steinberg UR",
        "M-Audio interface",
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


def requires_detail_evidence(row: dict) -> bool:
    price_text = str(row.get("price_text", ""))
    return "free" in price_text.lower() or parse_price(price_text) in PLACEHOLDER_PRICES


def main() -> None:
    target = choose_page_target(cdp_targets(9223), "facebook.com")
    if target is None:
        raise SystemExit("no open Facebook page on CDP port 9223")
    page = CdpPage(str(target["webSocketDebuggerUrl"]))

    output = ROOT / "data" / "checkpoints" / "facebook_expanded_discovery.json"
    previous_expanded = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    previous_details = {
        str(row.get("listing_id")): row
        for row in previous_expanded.get("listings", [])
        if row.get("listing_id")
    }
    previous_path = ROOT / "data" / "checkpoints" / "facebook_exact_models.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    known_ids = {str(row["listing_id"]) for row in previous.get("listings", [])}

    discovered: dict[str, dict] = {}
    failures: list[dict[str, str]] = []
    searches: list[dict[str, object]] = []

    # Collect category inventory before keyword searches. Scoring decides what
    # is worth surfacing; discovery itself is intentionally expansive.
    has_completed_initial_backfill = bool(previous_expanded.get("initial_category_backfill_completed"))
    category_runs = category_discovery_plan(
        has_completed_initial_backfill=has_completed_initial_backfill,
    )
    discovery_runs = [
        (group, category, CATEGORY_URLS[category], max_scrolls)
        for group, category, max_scrolls in category_runs
    ] + [
        (group, query, search_url(query), SEARCH_SCROLLS)
        for group, queries in QUERY_GROUPS.items()
        for query in queries
    ]
    for group, label, url, max_scrolls in discovery_runs:
        try:
            listings = collect_search(
                page,
                source="facebook",
                url=url,
                max_scrolls=max_scrolls,
                settle_seconds=.8,
            )
        except Exception as exc:
            failures.append({
                "group": group,
                "query": label,
                "url": url,
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"FAIL {group:28} {label}: {type(exc).__name__}: {exc}")
            continue

        searches.append({
            "group": group,
            "query": label,
            "url": url,
            "max_scrolls": max_scrolls,
            "results": len(listings),
        })
        print(f"{group:28} {label}: {len(listings)}")
        for listing in listings:
            row = discovered.setdefault(
                listing.listing_id,
                asdict(listing) | {
                    "discovery_queries": [],
                    "discovery_groups": [],
                    "discovery_categories": [],
                    "new_vs_exact_checkpoint": listing.listing_id not in known_ids,
                },
            )
            row.setdefault("discovery_categories", [])
            if group == "category":
                if label not in row["discovery_categories"]:
                    row["discovery_categories"].append(label)
            else:
                if label not in row["discovery_queries"]:
                    row["discovery_queries"].append(label)
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
    detail_failures: list[dict[str, object]] = []
    details_fetched_current = 0
    detail_fields = ("detail_title", "detail_price_text", "listing_age_text", "condition", "description", "detail_checked_at")
    for row in photo_rows:
        old = previous_details.get(str(row.get("listing_id")), {})
        for field in detail_fields:
            if old.get(field) not in (None, ""):
                row[field] = old[field]
    detail_rows = [row for row in photo_rows if requires_detail_evidence(row)]
    for index, row in enumerate(detail_rows, start=1):
        try:
            row.update(collect_facebook_detail(page, row, settle_seconds=.25))
            row["detail_checked_at"] = datetime.now().astimezone().isoformat()
            details_fetched_current += 1
            print(f"DETAIL {index:3}/{len(detail_rows)} {row['listing_id']} {row.get('listing_age_text') or 'age unavailable'}")
        except Exception as exc:
            old = previous_details.get(str(row.get("listing_id")), {})
            detail_failures.append({
                "listing_id": str(row.get("listing_id", "")),
                "url": str(row.get("url", "")),
                "error": f"{type(exc).__name__}: {exc}",
                "preserved_previous_detail": bool(old.get("detail_checked_at")),
            })
            print(f"DETAIL FAIL {index:3}/{len(detail_rows)} {row['listing_id']}: {type(exc).__name__}: {exc}")
    for row in rows:
        row.pop("image_url", None)
    payload = {
        "as_of": datetime.now().astimezone().isoformat(),
        "source": "facebook",
        "read_only": True,
        "cdp_port": 9223,
        "initial_category_backfill_completed": (
            has_completed_initial_backfill or not any(failure["group"] == "category" for failure in failures)
        ),
        "category_refresh_strategy": {
            "sort": "creation_time_descend",
            "initial_category_scrolls": INITIAL_CATEGORY_SCROLLS,
            "recurring_category_scrolls": REFRESH_CATEGORY_SCROLLS,
            "keyword_search_scrolls": SEARCH_SCROLLS,
        },
        "query_groups": {key: list(value) for key, value in QUERY_GROUPS.items()},
        "searches_completed": len(searches),
        "failures": failures,
        "detail_failures": detail_failures,
        "details_checked": sum(bool(row.get("detail_checked_at")) for row in photo_rows),
        "detail_collection_scope": "placeholder_prices",
        "details_attempted": len(detail_rows),
        "details_fetched_current": details_fetched_current,
        "searches": searches,
        "unique_listings": len(rows),
        "new_listings": sum(bool(row["new_vs_exact_checkpoint"]) for row in rows),
        "thumbnails": thumbnail_summary,
        "listings": rows,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"wrote {len(rows)} unique listings ({payload['new_listings']} new) "
        f"to {output}; search_failures={len(failures)}; detail_failures={len(detail_failures)}"
    )


if __name__ == "__main__":
    main()
