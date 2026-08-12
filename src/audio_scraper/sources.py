from __future__ import annotations

from urllib.parse import quote_plus, urlencode

from .models import SearchTarget


DEFAULT_SEARCHES = {
    "craigslist": [
        "audio interface", "recording equipment", "studio monitor", "powered speaker",
        "synthesizer", "keyboard", "sampler drum machine", "mixer microphone",
        "home studio", "musical instrument bundle",
    ],
    "ebay": [
        "audio interface", "studio monitor pair", "recording equipment", "powered speaker pair",
        "synthesizer", "sampler groovebox", "mixer", "microphone bundle",
    ],
    "facebook": [
        "audio interface", "recording equipment", "studio monitor", "powered speaker",
        "synthesizer", "sampler", "mixer", "home studio bundle",
    ],
    "reverb": ["audio interface", "studio monitors", "synthesizer", "sampler"],
    "guitar_center_used": ["audio interface", "studio monitor", "synthesizer", "sampler"],
}


def build_search_urls(source: str, *, postal_code: str, radius_miles: int) -> list[SearchTarget]:
    if source not in DEFAULT_SEARCHES:
        raise ValueError(f"unknown source: {source}")
    targets: list[SearchTarget] = []

    if source == "craigslist":
        base = "https://sfbay.craigslist.org/search/nby/msa"
        common = {"postal": postal_code, "search_distance": radius_miles, "sort": "date"}
        targets.append(SearchTarget(source, "musical instruments", "category", f"{base}?{urlencode(common)}"))
        for query in DEFAULT_SEARCHES[source]:
            params = urlencode({"query": query, **common})
            targets.append(SearchTarget(source, query, "query", f"{base}?{params}"))
    elif source == "ebay":
        # eBay is a nationwide discovery and market-pricing source. Preserve
        # directly clickable searches for both active and completed sales.
        base = "https://www.ebay.com/sch/i.html"
        for query in DEFAULT_SEARCHES[source]:
            active_params = urlencode({"_nkw": query, "_sacat": "619", "_sop": "10"})
            sold_params = urlencode({
                "_nkw": query,
                "_sacat": "619",
                "LH_Sold": "1",
                "LH_Complete": "1",
                "_sop": "13",
            })
            targets.append(SearchTarget(source, query, "active", f"{base}?{active_params}"))
            targets.append(SearchTarget(source, query, "sold", f"{base}?{sold_params}"))
    elif source == "facebook":
        targets.append(SearchTarget(source, "musical instruments", "category", "https://www.facebook.com/marketplace/category/musical-instruments/"))
        for query in DEFAULT_SEARCHES[source]:
            targets.append(SearchTarget(source, query, "query", f"https://www.facebook.com/marketplace/search/?query={quote_plus(query)}"))
    elif source == "reverb":
        for query in DEFAULT_SEARCHES[source]:
            targets.append(SearchTarget(source, query, "query", f"https://reverb.com/marketplace?query={quote_plus(query)}"))
    else:
        for query in DEFAULT_SEARCHES[source]:
            targets.append(SearchTarget(source, query, "query", f"https://www.guitarcenter.com/Used/?Ntt={quote_plus(query)}"))
    return targets
