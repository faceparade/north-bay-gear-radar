from audio_scraper.sources import DEFAULT_SEARCHES, build_search_urls


def test_every_core_source_has_broad_category_searches():
    assert {"craigslist", "ebay", "facebook"}.issubset(DEFAULT_SEARCHES)
    for source in ("craigslist", "ebay", "facebook"):
        assert len(DEFAULT_SEARCHES[source]) >= 4


def test_craigslist_urls_use_north_bay_music_category_and_radius():
    urls = build_search_urls("craigslist", postal_code="94945", radius_miles=20)
    assert urls
    assert all("sfbay.craigslist.org/search/nby/msa" in item.url for item in urls)
    assert all("postal=94945" in item.url and "search_distance=20" in item.url for item in urls)
    assert any(item.kind == "category" for item in urls)


def test_facebook_urls_are_category_or_broad_query_routes():
    urls = build_search_urls("facebook", postal_code="94945", radius_miles=20)
    assert any("category" in item.kind for item in urls)
    assert any("query" in item.kind for item in urls)


def test_ebay_urls_are_read_only_nationwide_searches():
    urls = build_search_urls("ebay", postal_code="94945", radius_miles=20)
    assert urls
    assert all("/sch/i.html" in item.url for item in urls)
    assert all("LH_PrefLoc" not in item.url for item in urls)
