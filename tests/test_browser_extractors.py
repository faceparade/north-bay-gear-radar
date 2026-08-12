from audio_scraper.browser_extractors import parse_browser_payload
from audio_scraper.loading import LoadingMode


def test_facebook_browser_payload_normalizes_and_deduplicates():
    payload = {
        "listing_ids": ["123", "123", "456"],
        "listings": [
            {"id": "123", "url": "https://www.facebook.com/marketplace/item/123/?ref=x", "title": "$80 Focusrite 2i2 Novato", "price": "$80", "location": "Novato", "image_url": "https://scontent.example.fbcdn.net/photo.jpg?temporary=1"},
            {"id": "123", "url": "https://www.facebook.com/marketplace/item/123/", "title": "$80 Focusrite 2i2 Novato", "price": "$80", "location": "Novato"},
        ],
        "has_next": False,
        "has_numbered_pages": False,
        "has_load_more": False,
        "scroll_height": 4100,
    }
    page, observation = parse_browser_payload("facebook", payload)
    assert len(page.listings) == 1
    assert page.listings[0].listing_id == "123"
    assert page.listings[0].image_url.endswith("photo.jpg?temporary=1")
    assert observation.listing_ids == frozenset({"123", "456"})


def test_ebay_payload_excludes_placeholder_and_detects_pagination():
    payload = {
        "listing_ids": ["123456", "187112110122"],
        "listings": [
            {"id": "123456", "url": "https://www.ebay.com/itm/123456", "title": "Shop on eBay", "price": "$20"},
            {"id": "187112110122", "url": "https://www.ebay.com/itm/187112110122", "title": "Focusrite Scarlett 2i2", "price": "$90"},
        ],
        "has_next": True,
        "next_url": "https://www.ebay.com/sch/i.html?_pgn=2",
        "has_numbered_pages": True,
        "has_load_more": False,
        "scroll_height": 20000,
    }
    page, observation = parse_browser_payload("ebay", payload)
    assert [x.listing_id for x in page.listings] == ["187112110122"]
    assert page.has_next
    assert observation.has_numbered_pages
