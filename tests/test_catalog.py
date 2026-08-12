from audio_scraper.catalog import CatalogEntry, validate_catalog


def test_catalog_requires_sources_for_market_claims():
    entry = CatalogEntry(
        model="Arturia MiniFuse 2", release_year=2021, msrp=149,
        used_low=74, used_high=118,
        sources=("https://www.arturia.com/products/audio/minifuse/minifuse-2", "https://reverb.com/p/arturia-minifuse-2-usb-c-audio-interface"),
        windows_status="supported", compatibility_notes="Official Windows ASIO driver",
    )
    assert validate_catalog([entry]) == []


def test_catalog_rejects_unbounded_ranges_and_unsourced_claims():
    entry = CatalogEntry(model="Mystery", used_low=100, used_high=50, sources=())
    errors = validate_catalog([entry])
    assert any("used range" in error for error in errors)
    assert any("source" in error for error in errors)
