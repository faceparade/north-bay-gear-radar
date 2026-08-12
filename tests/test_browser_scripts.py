from audio_scraper.browser_scripts import extractor_script


def test_ebay_script_uses_current_card_and_title_fallbacks():
    script = extractor_script("ebay")
    assert ".su-card-container" in script
    assert ".s-card__title" in script
    assert "img[alt]" in script
    assert "document.documentElement?.scrollHeight" in script
