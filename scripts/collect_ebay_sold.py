"""Collect and conservatively filter exact-model eBay completed listings."""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from audio_scraper.cdp_browser import CdpPage, cdp_targets, choose_page_target, collect_search
from audio_scraper.ebay_sold import (
    comparable_variant,
    is_exact_sale_title,
    is_plausible_sale_price,
)

ROOT = Path(__file__).resolve().parents[1]

QUERIES = {
    "Line 6 POD Studio UX2": ("Line 6 POD Studio UX2", r"(?i)(line\s*6|pod studio|toneport).*ux\s*2|ux\s*2.*(line\s*6|pod studio|toneport)"),
    "Apogee ONE (generation unspecified) bundle": ("Apogee ONE audio interface", r"(?i)apogee\s+one.*(audio|interface)|(?:audio|interface).*apogee\s+one"),
    "PreSonus Eris 3.5 + Eris Sub 8BT": ("PreSonus Eris 3.5 Sub 8BT", r"(?i)(presonus|personus).*eris.*(3\.5|sub\s*8)|eris.*(3\.5|sub\s*8).*(presonus|personus)"),
    "Rockville RPG12": ("Rockville RPG12", r"(?i)rockville.*rpg\s*12(?!2)"),
    "Mackie ProFX10v3": ("Mackie ProFX10v3", r"(?i)mackie.*pro\s*fx\s*10\s*v?3(?!\+)"),
    "AudioThingies MicroMonsta 1": ("AudioThingies MicroMonsta", r"(?i)(audiothingies.*micro\s*monsta|micro\s*monsta.*audiothingies)(?!.*\b2\b)"),
    "Elektron Digitone (original)": ("Elektron Digitone", r"(?i)elektron.*digitone(?!.*(?:ii|keys))|digitone.*elektron(?!.*(?:ii|keys))"),
    "Roland MS-1 Sampler": ("Roland MS-1 Sampler", r"(?i)roland.*ms[- ]?1.*sampl|ms[- ]?1.*sampl.*roland"),
    "Roland AIRA TR-8": ("Roland AIRA TR-8", r"(?i)roland.*(?:aira\s*)?tr[- ]?8(?!s)|aira.*tr[- ]?8(?!s)"),
    "Casio CT-X700": ("Casio CT-X700", r"(?i)casio.*ct[- ]?x700"),
    "Casio CTK-1000": ("Casio CTK-1000", r"(?i)casio.*ctk[- ]?1000"),
    "Makala MK-TE": ("Makala MK-TE", r"(?i)(makala|kala).*mk[- ]?te|mk[- ]?te.*(makala|kala)"),
}

MODEL_EXCLUDE = {
    "Apogee ONE (generation unspecified) bundle": re.compile(r"(?i)\b(no cables?|no cabels?)\b"),
    "PreSonus Eris 3.5 + Eris Sub 8BT": re.compile(r"(?i)\b(passive speaker|speaker only|speakers only)\b"),
    "Rockville RPG12": re.compile(r"(?i)\b(pair|2[- ]pack|two speakers)\b"),
    "AudioThingies MicroMonsta 1": re.compile(r"(?i)\b(micromonsta|micro monsta)\s*(?:2|ii)\b"),
    "Elektron Digitone (original)": re.compile(r"(?i)\b(digitone\s*(?:2|ii)|digitone keys|overlay|skin)\b"),
    "Roland AIRA TR-8": re.compile(r"(?i)\b(tr[- ]?8s|t[- ]?8|tier|oak)\b"),
    "Casio CT-X700": re.compile(r"(?i)\b(bundle|value bundle)\b"),
}
PRICE = re.compile(r"\$([\d,]+(?:\.\d{1,2})?)")


def main() -> None:
    target = choose_page_target(cdp_targets(9223), "ebay.com")
    if target is None:
        raise SystemExit("no open eBay page on CDP port 9223")
    page = CdpPage(str(target["webSocketDebuggerUrl"]))
    rows = []
    failures = []

    for model, (query, pattern) in QUERIES.items():
        url = "https://www.ebay.com/sch/i.html?" + urlencode({
            "_nkw": query,
            "_sacat": "619",
            "LH_Sold": "1",
            "LH_Complete": "1",
            "_sop": "13",
        })
        try:
            listings = collect_search(page, source="ebay", url=url, max_scrolls=2, settle_seconds=.5)
        except Exception as exc:
            failures.append({"model": model, "url": url, "error": f"{type(exc).__name__}: {exc}"})
            continue
        accepted: dict[str, list[float]] = {}
        for listing in listings:
            model_exclude = MODEL_EXCLUDE.get(model)
            if (
                not is_exact_sale_title(model, listing.title, pattern)
                or (model_exclude and model_exclude.search(listing.title))
            ):
                continue
            match = PRICE.search(listing.price_text)
            if not match:
                continue
            price = float(match.group(1).replace(",", ""))
            if not is_plausible_sale_price(model, price):
                continue
            variant = comparable_variant(model, listing.title)
            if variant is None:
                continue
            row = asdict(listing) | {
                "model": model,
                "variant": variant,
                "sold_price": price,
                "search_url": url,
            }
            rows.append(row)
            accepted.setdefault(variant, []).append(price)
        summary = "no exact matches"
        if accepted:
            parts = []
            for variant, prices in accepted.items():
                parts.append(
                    f"{variant}: n={len(prices)} low={min(prices):.2f} "
                    f"median={statistics.median(prices):.2f} high={max(prices):.2f}"
                )
            summary = "; ".join(parts)
        print(f"{model}: {summary}")

    payload = {
        "as_of": datetime.now().astimezone().isoformat(),
        "source": "ebay",
        "kind": "completed_sold_exact_model_comparisons",
        "filters": "Exact model and generation title rules; accessories, adjacent models, bundles/pairs where inappropriate, empty boxes, parts-only, untested, as-is, junk, and non-working listings excluded by title. PreSonus monitor and subwoofer components are labeled separately. Shipping is not included in sold_price.",
        "failures": failures,
        "listings": rows,
    }
    output = ROOT / "data" / "research" / "ebay_sold_exact_comparisons.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} exact sold comparisons to {output}; failures={len(failures)}")


if __name__ == "__main__":
    main()
