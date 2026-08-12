from audio_scraper.site_data import (
    build_site_payload,
    categorize_title,
    normalize_facebook_listing,
)


def test_verified_marketplace_triage_is_attached_to_matching_listing():
    payload = build_site_payload(
        facebook={
            "as_of": "2026-08-12T00:00:00Z",
            "listings": [{"listing_id": "abc", "title": "Steinberg audio interface", "price_text": "$30"}],
        },
        craigslist={"accepted": []},
        shortlist={"scored": []},
        sold={"listings": []},
        marketplace_triage={
            "listings": {
                "abc": {
                    "model": "Steinberg UR22mkII",
                    "condition": "Used-like-new",
                    "accessories": "Cable unconfirmed",
                    "windows_status": "Windows 11 supported",
                    "market": {"used_low": 38, "used_high": 69},
                    "research_notes": "Exact model confirmed from photos.",
                    "risk_flags": ["accessories_unconfirmed"],
                    "recommendation": "buy",
                }
            }
        },
    )
    row = payload["listings"][0]
    assert row["model"] == "Steinberg UR22mkII"
    assert row["market"]["used_low"] == 38
    assert row["recommendation"] == "buy"
    assert row["risk_flags"] == ["accessories_unconfirmed"]


def test_categorize_title_prefers_audio_interface_over_generic_recording_terms():
    assert categorize_title("Native Instruments Komplete Audio 2 USB Audio Interface") == "interfaces"


def test_categorize_title_rejects_computer_keyboards_from_music_keyboard_category():
    assert categorize_title("Logitech G915 TKL keyboard") == "excluded"


def test_categorize_title_finds_monitors_and_loopers():
    assert categorize_title("Samson MediaOne M30 Powered Studio Monitors Pair") == "monitors"
    assert categorize_title("Boss RC-3 Loop Station Pedal") == "loopers-effects"


def test_categorize_title_filters_malformed_and_non_music_results():
    assert categorize_title("$1,234") == "excluded"
    assert categorize_title("two brand-new LG 27 monitors") == "excluded"
    assert categorize_title("Weather Guard Truck Tool Box") == "excluded"


def test_categorize_title_expands_real_instrument_categories():
    assert categorize_title("Makala Ukulele Model MK-TE") == "guitars-acoustic"
    assert categorize_title("Zildjian 16 dark S crash") == "drums-percussion"
    assert categorize_title("AKAI DPS16 Digital Recording Studio") == "recorders-samplers"
    assert categorize_title("Yamaha P-45 digital piano") == "keyboards-controllers"


def test_normalize_facebook_listing_preserves_link_and_marks_discovery_state():
    record = normalize_facebook_listing(
        {
            "listing_id": "123",
            "url": "https://www.facebook.com/marketplace/item/123/",
            "title": "PreSonus Studio 26c USB Audio Interface",
            "price_text": "$120",
            "location_text": "Petaluma, CA",
            "new_vs_exact_checkpoint": True,
            "discovery_groups": ["recording_foundation"],
            "discovery_queries": ["audio interface"],
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["source"] == "facebook"
    assert record["listing_type"] == "active"
    assert record["category"] == "interfaces"
    assert record["asking_price"] == 120.0
    assert record["url"].endswith("/123/")
    assert record["new_discovery"] is True


def test_build_site_payload_keeps_active_asks_and_sold_values_distinct():
    payload = build_site_payload(
        facebook={
            "as_of": "2026-08-12T12:00:00-07:00",
            "listings": [
                {
                    "listing_id": "fb1",
                    "url": "https://facebook.example/fb1",
                    "title": "Focusrite Scarlett Solo 3rd Gen Audio Interface",
                    "price_text": "$50",
                    "location_text": "Petaluma, CA",
                    "new_vs_exact_checkpoint": True,
                    "discovery_groups": ["recording_foundation"],
                    "discovery_queries": ["audio interface"],
                },
                {
                    "listing_id": "bad",
                    "url": "https://facebook.example/bad",
                    "title": "Logitech keyboard",
                    "price_text": "$10",
                    "location_text": "Novato, CA",
                },
            ],
        },
        craigslist={
            "accepted": [
                {
                    "source": "craigslist",
                    "listing_id": "cl1",
                    "url": "https://craigslist.example/cl1",
                    "title": "Mackie ProFX10v3",
                    "asking_price": 190.0,
                    "price_text": "$190",
                    "location_text": "Novato",
                }
            ]
        },
        shortlist={
            "scored": [
                {
                    "rank": 1,
                    "model": "Mackie ProFX10v3",
                    "listing_url": "https://craigslist.example/cl1",
                    "score": {"total": 89.89},
                    "market": {"used_low": 210.0, "used_high": 300.0, "sample_size": 10},
                    "risk_flags": [],
                }
            ]
        },
        sold={
            "as_of": "2026-08-12T12:00:00-07:00",
            "listings": [
                {
                    "source": "ebay",
                    "listing_id": "e1",
                    "url": "https://ebay.example/e1",
                    "title": "Mackie ProFX10v3 Mixer",
                    "model": "Mackie ProFX10v3",
                    "sold_price": 250.0,
                    "price_text": "$250",
                }
            ],
        },
    )
    assert payload["stats"]["active"] == 2
    assert payload["stats"]["sold"] == 1
    assert payload["stats"]["excluded_facebook"] == 1
    active = next(row for row in payload["listings"] if row["listing_id"] == "cl1")
    sold = next(row for row in payload["listings"] if row["listing_id"] == "e1")
    assert active["listing_type"] == "active"
    assert active["score"] == 89.89
    assert sold["listing_type"] == "sold"
    assert sold["sold_price"] == 250.0
    assert "asking_price" not in sold
