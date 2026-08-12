from urllib.parse import parse_qs, urlparse

from audio_scraper.sources import DEFAULT_SEARCHES, build_search_urls


def test_ebay_builds_nationwide_active_and_sold_searches_with_clickable_urls():
    targets = build_search_urls("ebay", postal_code="94945", radius_miles=20)

    assert len(targets) == 2 * len(DEFAULT_SEARCHES["ebay"])
    assert {target.kind for target in targets} == {"active", "sold"}

    for target in targets:
        assert target.url.startswith("https://www.ebay.com/sch/i.html?")
        params = parse_qs(urlparse(target.url).query)
        assert "_stpos" not in params
        assert "_sadis" not in params
        assert "LH_PrefLoc" not in params
        if target.kind == "sold":
            assert params["LH_Sold"] == ["1"]
            assert params["LH_Complete"] == ["1"]
        else:
            assert "LH_Sold" not in params
            assert "LH_Complete" not in params
