from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import json
import re

from audio_scraper.scoring import score_category_screening_fit


CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("interfaces", ("audio interface", "audiobox", "audio box", "scarlett", "komplete audio", "studio 26c", "studio 24c", "umc22", "umc202", "umc204", "u-phoria", "firebox", "motu 896", "motu ultralite", "steinberg ci", "steinberg ur", "tascam series", "apogee one", "pod studio ux", "pro tools 002")),
    ("mixers", ("mixer", "mixing console", "profx", "xenyx", "yamaha ag03", "yamaha ag06", "mixing station")),
    ("monitors", ("studio monitor", "powered monitor", "mediaone", "mackie mr", "eris 3.5", "eris 4.5", "monitor speakers")),
    ("subwoofers", ("subwoofer", "sub 8bt", "studio sub")),
    ("microphones-preamps", ("microphone", "mic preamp", "tube mp", "phantom powered di", "direct box", "channel strip", "preamp")),
    ("synths-modules", ("synthesizer", "synthesiser", "synth module", "rack synth", "sound module", "groovebox", "digitone", "micromonsta", "yamaha an200", "microbrute", "ultraproteus", "roland jv")),
    ("samplers-drum-machines", ("sampler", "drum machine", "roland ms-1", "roland tr-", "boss dr-", "mpc ", "sp-404", "volca sample", "volca beats", "rhythm designer", "maschine+")),
    ("recorders-samplers", ("digital recording studio", "multitrack recorder", "dps16", "digital recorder", "tascam portastudio")),
    ("keyboards-controllers", ("midi keyboard", "midi controller", "keystep", "digital piano", "casiotone", "casio ctk", "casio lk-", "casio sa-", "yamaha p-", "yamaha kx", "yamaha psr", "yamaha pss", "electronic keyboard", "m-audio usb midi")),
    ("electronic-drums", ("electronic drum", "alesis dm", "roland td-", "e-drum", "v-drums")),
    ("drums-percussion", ("drum kit", "drum pedal", "drum throne", "drum hardware", "cymbal", "zildjian", "bongo", "conga", "percussion", "glockenspiel", "snare", "dw pedal")),
    ("guitars-acoustic", ("electric guitar", "acoustic guitar", "ukulele", "makala", "guitar amp", "combo amp", "mini stack")),
    ("loopers-effects", ("looper", "loop station", "loopstation", "effects processor", "multi-effects", "multi effects", "guitar pedal", "synth pedal", "bass synth wah", "ms-70cdr", "rack effect")),
    ("dj-gear", ("dj equipment", "dj controller", "tractor dj", "equipo de dj")),
    ("pa-headphones-utilities", ("pa speaker", "powered speaker", "active speaker", "active loudspeaker", "headphone distribution", "headphone amp", "powerplay", "midi interface", "feedback destroyer", "stage monitor", "studio utility")),
    ("bundles", ("studio bundle", "recording equipment", "audio gear lot", "music equipment lot", "pedal lot", "liquidating audio gear")),
)

EXCLUDE_TERMS = (
    "logitech", "computer keyboard", "apple keyboard", "hp keyboard", "keyboard bag",
    "piano pedal extender", "music book", "jewel cases", "typewriter", "toy box",
    "keepsake box", "ammo box", "desktop intel", "apple desktop", "surround sound preamplifier",
    "wireless audio for biking", "dj controller case", "school of music", "partner listing",
    "dog gear", "canon camera", "bulk lot of", "recorder instruments and music books",
    "lg 27", "tool box", "cash box", "old lps", "tivoli audio", "bose 301",
    "audioengine p4", "edifier r1280", "boston acoustics", "pc speakers", "stero equipment",
    "integrated amp", "nobsound", "pac interface", "metra 95", "kids music instruments",
    "handcrafted moroccan", "music industry resource", "electronics",
    # Broad Marketplace searches can return unrelated listings that mention a
    # query word only in passing.  Keep those out of the public music-gear
    # inventory rather than labeling them as generic audio.
    "garden hose", "hose reel", "nintendo", "playstation", "iphone", "laptop",
    "dictionary", "looking for bass", "delivery box", "drop boxes", "vr espn",
    "package", "tv aquos", "tool/storage", "cash register", "cash drawer",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def parse_price(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", _text(value))
    return float(match.group(1).replace(",", "")) if match else None


PLACEHOLDER_PRICES = {0.0, 1.0, 123.0, 1234.0, 12345.0}


def _money_values(value: Any) -> list[float]:
    return [
        float(match.replace(",", ""))
        for match in re.findall(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", _text(value))
    ]


def _facebook_price_evidence(row: dict[str, Any]) -> dict[str, Any]:
    """Separate a Marketplace search-card number from a credible asking price."""

    headline = parse_price(row.get("price_text"))
    detail = parse_price(row.get("detail_price_text"))
    title = _text(row.get("title")).strip()
    struck_through_former_price = (
        bool(re.fullmatch(r"\$[\d,]+(?:\.\d{1,2})?", title))
        and parse_price(title) != headline
        and headline is not None
    )
    description = _text(row.get("description")).strip()
    description_prices = list(dict.fromkeys(_money_values(description)))
    free_headline = bool(re.search(r"\bfree\b", _text(row.get("price_text")), flags=re.I))
    placeholder = headline in PLACEHOLDER_PRICES or free_headline
    offer_only = bool(re.search(
        r"\b(?:make|send|shoot|message me with)\s+(?:me\s+)?(?:an?\s+)?offers?\b|\baccepting\s+(?:real\s+)?offers?\b",
        f"{row.get('title', '')} {description}",
        flags=re.I,
    ))
    trade_or_unclear = bool(re.search(
        r"\b(?:trade(?:s|d)?|swap|deposit|down payment|per item|each item|starting at)\b",
        description,
        flags=re.I,
    ))
    explicit_ask = bool(re.search(
        r"(?:\b(?:asking|ask|price(?:\s+is)?|selling(?:\s+it)?\s+for|sell(?:\s+it)?\s+for|take)\b[^$\n]{0,24}\$\s*[0-9])"
        r"|(?:\$\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?\s*(?:obo|firm)\b)",
        description,
        flags=re.I,
    ))
    actual_free = (
        free_headline
        and bool(re.search(r"\b(?:actually free|free to (?:a )?good home|giving (?:it|this|them) away|no charge|curb alert)\b", description, flags=re.I))
        and not re.search(r"\b(?:not free|want something for free)\b", description, flags=re.I)
        and not offer_only
        and not description_prices
    )

    if headline is None and not free_headline:
        return {
            "headline_price": None,
            "asking_price": None,
            "price_status": "missing",
            "price_note": "The source did not provide a usable asking price.",
        }
    if struck_through_former_price:
        former_price = parse_price(title)
        return {
            "headline_price": headline,
            "former_price": former_price,
            "asking_price": headline,
            "price_status": "reduced_headline",
            "price_note": (
                f"Marketplace shows a reduced asking price of ${headline:,.0f}; "
                f"the former ${former_price:,.0f} price is struck through."
            ),
        }
    if not placeholder:
        return {
            "headline_price": headline,
            "asking_price": detail if detail is not None and detail != headline else headline,
            "price_status": "verified_detail" if detail is not None and detail != headline else "headline",
            "price_note": "Price shown on the listing detail page." if detail is not None and detail != headline else "Headline asking price; detail text was not required for placeholder validation.",
        }
    if actual_free:
        return {
            "headline_price": headline,
            "asking_price": 0.0,
            "price_status": "verified_detail_free",
            "price_note": "The detail description confirms that the item is actually free.",
        }
    if detail is not None and detail not in PLACEHOLDER_PRICES:
        return {
            "headline_price": headline,
            "asking_price": detail,
            "price_status": "verified_detail",
            "price_note": f"Detail page shows ${detail:,.0f}; the search card's ${headline:,.0f} was stale or promotional.",
        }
    if len(description_prices) > 1:
        shown = ", ".join(f"${price:,.0f}" for price in description_prices[:6])
        return {
            "headline_price": headline,
            "asking_price": None,
            "price_status": "multiple_prices",
            "price_note": f"Placeholder headline. Description lists separate prices ({shown}); no single asking price.",
        }
    if offer_only:
        return {
            "headline_price": headline,
            "asking_price": None,
            "price_status": "make_offer",
            "price_note": "Placeholder headline. Seller requests offers; no fixed asking price is stated.",
        }
    if trade_or_unclear:
        return {
            "headline_price": headline,
            "asking_price": None,
            "price_status": "unclear_arrangement",
            "price_note": "Placeholder headline. The description describes a trade or unclear price arrangement.",
        }
    if len(description_prices) == 1 and explicit_ask:
        supported = description_prices[0]
        return {
            "headline_price": headline,
            "asking_price": supported,
            "price_status": "verified_description",
            "price_note": f"Description states one unambiguous asking price: ${supported:,.0f}.",
        }
    displayed = "FREE" if free_headline else f"${headline:,.0f}"
    return {
        "headline_price": headline,
        "asking_price": None,
        "price_status": "placeholder_unverified",
        "price_note": f"The {displayed} headline may be promotional and is not a verified asking price.",
    }


def categorize_title(title: str) -> str:
    lowered = " ".join(title.lower().split())
    if not lowered or lowered in {"just listed", "partner listing"}:
        return "excluded"
    if re.fullmatch(r"\$[\d,]+(?:\.\d{1,2})?", lowered):
        return "excluded"
    if any(term in lowered for term in EXCLUDE_TERMS):
        return "excluded"
    # A generic computer keyboard should not become a musical keyboard.
    if "keyboard" in lowered and not any(
        term in lowered
        for term in ("midi", "piano", "casio", "casiotone", "yamaha", "roland", "korg", "arturia", "novation", "akai", "synth", "musical")
    ):
        return "excluded"
    for category, terms in CATEGORY_RULES:
        if any(term in lowered for term in terms):
            return category
    return "other-audio"


def normalize_facebook_listing(row: dict[str, Any], as_of: str | None) -> dict[str, Any]:
    title = _text(row.get("detail_title") or row.get("title")).strip()
    category = categorize_title(title)
    record: dict[str, Any] = {
        "source": "facebook",
        "listing_type": "active",
        "listing_id": _text(row.get("listing_id")),
        "url": _text(row.get("url")),
        "title": title,
        "category": category,
        "price_text": _text(row.get("price_text")),
        "detail_price_text": _text(row.get("detail_price_text")),
        "description": _text(row.get("description")),
        "condition": _text(row.get("condition")),
        "listing_age_text": _text(row.get("listing_age_text")),
        "location_text": _text(row.get("location_text")),
        "thumbnail_url": _text(row.get("thumbnail_path")),
        "observed_at": as_of,
        "new_discovery": bool(row.get("new_vs_exact_checkpoint")),
        "discovery_groups": list(row.get("discovery_groups") or []),
        "discovery_queries": list(row.get("discovery_queries") or []),
    }
    record.update(_facebook_price_evidence(row))
    return record


def normalize_craigslist_listing(row: dict[str, Any]) -> dict[str, Any]:
    title = _text(row.get("title")).strip()
    return {
        "source": "craigslist",
        "listing_type": "active",
        "listing_id": _text(row.get("listing_id")),
        "url": _text(row.get("url")),
        "title": title,
        "category": categorize_title(title),
        "asking_price": parse_price(row.get("asking_price") or row.get("price_text")),
        "price_text": _text(row.get("price_text")),
        "location_text": _text(row.get("location_text")),
        "description": _text(row.get("description")),
        "posted_at": row.get("posted_at"),
        "updated_at": row.get("updated_at"),
        "distance_miles": row.get("distance_miles"),
        "thumbnail_url": _text(row.get("thumbnail_path")),
        "new_discovery": False,
    }


def normalize_sold_listing(row: dict[str, Any], as_of: str | None) -> dict[str, Any]:
    model = _text(row.get("model") or row.get("title")).strip()
    return {
        "source": "ebay",
        "listing_type": "sold",
        "listing_id": _text(row.get("listing_id")),
        "url": _text(row.get("url")),
        "title": _text(row.get("title")).strip(),
        "model": model,
        "category": categorize_title(model),
        "sold_price": parse_price(row.get("sold_price") or row.get("price_text")),
        "price_text": _text(row.get("price_text")),
        "location_text": _text(row.get("location_text")),
        "observed_at": as_of,
        "thumbnail_url": _text(row.get("thumbnail_path")),
        "new_discovery": False,
    }


def _score_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("total")
    return round(float(value), 2) if isinstance(value, (int, float)) else None


def _attach_scores(records: Iterable[dict[str, Any]], shortlist: dict[str, Any]) -> None:
    by_url = {row.get("listing_url"): row for row in shortlist.get("scored", []) if row.get("listing_url")}
    for record in records:
        score = by_url.get(record.get("url"))
        if not score:
            continue
        record.update(
            {
                "rank": score.get("rank"),
                "score": _score_value(score.get("score")),
                "model": score.get("model"),
                "risk_flags": list(score.get("risk_flags") or []),
                "market": score.get("market") or {},
                "research_notes": score.get("research_notes"),
                "windows_status": score.get("windows_status"),
            }
        )


def _attach_marketplace_triage(
    records: Iterable[dict[str, Any]], triage: dict[str, Any]
) -> None:
    by_id = triage.get("listings", {})
    for record in records:
        finding = by_id.get(record.get("listing_id"))
        if not finding:
            continue
        record.update(
            {
                "model": finding.get("model") or record.get("model"),
                "condition": finding.get("condition"),
                "accessories": finding.get("accessories"),
                "windows_status": finding.get("windows_status"),
                "market": finding.get("market") or {},
                "research_notes": finding.get("research_notes"),
                "risk_flags": list(finding.get("risk_flags") or []),
                "recommendation": finding.get("recommendation"),
            }
        )
        # Listing-level triage can supersede an older shortlist score when a
        # fresh Marketplace inspection has identified the exact unit and its
        # compatibility/value evidence.  This prevents an unreviewed legacy
        # listing from floating above newly reviewed modern alternatives.
        if "score" in finding:
            record["score"] = _score_value(finding.get("score"))
            record["score_basis"] = "listing_research"
        if "fit_rank" in finding:
            record["fit_rank"] = finding.get("fit_rank")


def _attach_screening_fit_scores(records: Iterable[dict[str, Any]]) -> None:
    """Attach category-screening scores only where they cannot look like deal research.

    An interface's generation, driver support, I/O, condition, accessories, and
    market value vary too much for a category baseline to be a deal score.
    """
    for record in records:
        if record.get("listing_type") != "active" or record.get("score") is not None:
            continue
        if record.get("category") == "interfaces":
            record["score_basis"] = "research_required"
            record["score_notes"] = [
                "exact_model_condition_compatibility_and_market_value_require_listing_research",
            ]
            continue
        result = score_category_screening_fit(
            category=_text(record.get("category")),
            asking_price=record.get("asking_price"),
        )
        record["score"] = result.total
        record["score_basis"] = "category_screening"
        record["score_notes"] = list(result.notes)


def _remove_price_dependent_guidance(records: Iterable[dict[str, Any]]) -> None:
    """Never rank or recommend an active listing whose real ask is unknown."""
    for record in records:
        if record.get("listing_type") != "active" or record.get("asking_price") is not None:
            continue
        # Fit remains available for every item. Only price-dependent guidance is
        # removed when a real ask cannot be verified.
        for field in ("rank", "fit_rank", "score", "market", "recommendation", "research_notes"):
            record.pop(field, None)
        flags = list(record.get("risk_flags") or [])
        if "unverified_asking_price" not in flags:
            flags.append("unverified_asking_price")
        record["risk_flags"] = flags


def build_site_payload(
    *,
    facebook: dict[str, Any],
    craigslist: dict[str, Any],
    shortlist: dict[str, Any],
    sold: dict[str, Any],
    marketplace_triage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fb_all = [normalize_facebook_listing(row, facebook.get("as_of")) for row in facebook.get("listings", [])]
    excluded_fb = sum(row["category"] == "excluded" for row in fb_all)
    active = [row for row in fb_all if row["category"] != "excluded"]
    active.extend(
        row
        for row in (normalize_craigslist_listing(item) for item in craigslist.get("accepted", []))
        if row["category"] != "excluded"
    )
    sold_rows = [normalize_sold_listing(row, sold.get("as_of")) for row in sold.get("listings", [])]
    _attach_scores(active, shortlist)
    _attach_marketplace_triage(active, marketplace_triage or {})
    _remove_price_dependent_guidance(active)
    _attach_screening_fit_scores(active)
    listings = sorted(
        active + sold_rows,
        key=lambda row: (
            row["listing_type"] != "active",
            row.get("asking_price") if row.get("asking_price") is not None else row.get("sold_price", 10**12),
            row["title"].lower(),
        ),
    )
    categories = Counter(row["category"] for row in listings)
    sources = Counter(row["source"] for row in listings)
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": generated_at,
        "source_as_of": {
            "facebook": facebook.get("as_of"),
            "ebay_sold": sold.get("as_of"),
        },
        "stats": {
            "active": len(active),
            "sold": len(sold_rows),
            "new_discoveries": sum(bool(row.get("new_discovery")) for row in active),
            "scored": sum(row.get("score") is not None for row in active),
            "excluded_facebook": excluded_fb,
            "total": len(listings),
        },
        "categories": dict(sorted(categories.items())),
        "sources": dict(sorted(sources.items())),
        "listings": listings,
    }


def build_site_payload_from_files(root: Path) -> dict[str, Any]:
    def load(relative: str) -> dict[str, Any]:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    return build_site_payload(
        facebook=load("data/checkpoints/facebook_expanded_discovery.json"),
        craigslist=load("data/normalized/craigslist.json"),
        shortlist=load("data/normalized/scored_shortlist.json"),
        sold=load("data/research/ebay_sold_exact_comparisons.json"),
        marketplace_triage=load("data/research/marketplace_triage.json"),
    )
