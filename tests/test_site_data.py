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


def test_listing_triage_can_supply_an_authoritative_best_fit_score():
    payload = build_site_payload(
        facebook={"as_of": "2026-08-12T00:00:00Z", "listings": [{
            "listing_id": "reviewed", "title": "Focusrite Scarlett 4i4", "price_text": "$99"
        }]},
        craigslist={"accepted": []}, shortlist={"scored": []}, sold={"listings": []},
        marketplace_triage={"listings": {"reviewed": {
            "model": "Focusrite Scarlett 4i4 (3rd Gen)", "score": 91, "fit_rank": 1,
            "recommendation": "buy",
        }}},
    )
    row = payload["listings"][0]
    assert row["score"] == 91.0
    assert row["fit_rank"] == 1
    assert row["recommendation"] == "buy"


def test_categorize_title_prefers_audio_interface_over_generic_recording_terms():
    assert categorize_title("Native Instruments Komplete Audio 2 USB Audio Interface") == "interfaces"
    assert categorize_title("Presonus Audiobox USB interface") == "interfaces"


def test_categorize_title_rejects_computer_keyboards_from_music_keyboard_category():
    assert categorize_title("Logitech G915 TKL keyboard") == "excluded"


def test_categorize_title_finds_monitors_and_loopers():
    assert categorize_title("Samson MediaOne M30 Powered Studio Monitors Pair") == "monitors"
    assert categorize_title("Boss RC-3 Loop Station Pedal") == "loopers-effects"


def test_categorize_title_filters_malformed_and_non_music_results():
    assert categorize_title("$1,234") == "excluded"
    assert categorize_title("two brand-new LG 27 monitors") == "excluded"
    assert categorize_title("Weather Guard Truck Tool Box") == "excluded"
    assert categorize_title("Hosemobile Garden Hose Reel") == "excluded"
    assert categorize_title("Nintendo power A controller (new)") == "excluded"


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
            "thumbnail_path": "images/listings/facebook-123.webp",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["source"] == "facebook"
    assert record["listing_type"] == "active"
    assert record["category"] == "interfaces"
    assert record["asking_price"] == 120.0
    assert record["url"].endswith("/123/")
    assert record["thumbnail_url"] == "images/listings/facebook-123.webp"
    assert record["new_discovery"] is True


def test_placeholder_facebook_price_is_not_treated_as_an_asking_price_without_detail_evidence():
    record = normalize_facebook_listing(
        {
            "listing_id": "bait",
            "title": "DJ equipment - message with offers",
            "price_text": "$1",
            "location_text": "Novato, CA",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["headline_price"] == 1.0
    assert record["asking_price"] is None
    assert record["price_status"] == "placeholder_unverified"
    assert "not a verified asking price" in record["price_note"]


def test_detail_page_replacement_price_supersedes_stale_placeholder_headline():
    record = normalize_facebook_listing(
        {
            "listing_id": "reduced",
            "title": "Alesis Strike Multi Pad bundle",
            "price_text": "$1",
            "detail_price_text": "$1,500",
            "description": "Alesis Strike Multi Pad with three speakers and stands.",
            "listing_age_text": "31 weeks ago",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["headline_price"] == 1.0
    assert record["asking_price"] == 1500.0
    assert record["price_status"] == "verified_detail"
    assert record["listing_age_text"] == "31 weeks ago"


def test_one_unambiguous_description_price_can_validate_a_placeholder():
    record = normalize_facebook_listing(
        {
            "listing_id": "description-price",
            "title": "Rack effects unit",
            "price_text": "$1",
            "detail_price_text": "$1",
            "description": "Clean and fully working. Asking $500 OBO.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] == 500.0
    assert record["price_status"] == "verified_description"


def test_trade_or_unclear_single_description_amount_stays_unpriced():
    record = normalize_facebook_listing(
        {
            "listing_id": "trade",
            "title": "Synth trade",
            "price_text": "$123",
            "description": "Trade for another synth plus $300 cash.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "unclear_arrangement"


def test_offer_request_with_a_non_ask_amount_stays_unpriced():
    record = normalize_facebook_listing(
        {
            "listing_id": "offer-with-value",
            "title": "Audio lot",
            "price_text": "$1",
            "description": "Paid $500 new. Make me an offer.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "make_offer"


def test_single_historical_amount_without_ask_language_stays_unpriced():
    record = normalize_facebook_listing(
        {
            "listing_id": "historical-value",
            "title": "Audio interface",
            "price_text": "$1",
            "description": "Paid $500 new. Barely used.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "placeholder_unverified"


def test_unpriced_placeholder_keeps_screening_fit_but_cannot_inherit_rank_or_buying_guidance():
    payload = build_site_payload(
        facebook={
            "as_of": "2026-08-12T12:00:00-07:00",
            "listings": [{
                "listing_id": "bait",
                "url": "https://www.facebook.com/marketplace/item/bait",
                "title": "Audio interface",
                "price_text": "$1",
                "description": "Message for the price.",
            }],
        },
        craigslist={"accepted": []},
        shortlist={"scored": [{
            "listing_url": "https://www.facebook.com/marketplace/item/bait",
            "rank": 1,
            "score": {"total": 9.8},
            "market": {"used_low": 100, "used_high": 200},
            "research_notes": "Old bargain guidance based on the $1 headline.",
        }]},
        sold={"as_of": "2026-08-12T12:00:00-07:00", "listings": []},
        marketplace_triage={"listings": {"bait": {
            "recommendation": "strong-buy",
            "research_notes": "Buy immediately.",
            "market": {"used_low": 100, "used_high": 200},
        }}},
    )
    row = payload["listings"][0]
    assert row["asking_price"] is None
    assert row["score"] > 0
    assert row["score_basis"] == "category_screening"
    assert row.get("rank") is None
    assert row.get("market") is None
    assert row.get("recommendation") is None
    assert row.get("research_notes") is None
    assert "unverified_asking_price" in row["risk_flags"]


def test_every_active_listing_receives_fit_score_when_only_some_have_exact_scoring():
    payload = build_site_payload(
        facebook={"as_of": "2026-08-12T00:00:00Z", "listings": [
            {"listing_id": "exact", "url": "https://facebook.example/exact", "title": "Audio interface", "price_text": "$60"},
            {"listing_id": "screen", "url": "https://facebook.example/screen", "title": "Drum throne", "price_text": "$10"},
        ]},
        craigslist={"accepted": []},
        shortlist={"scored": [{
            "listing_url": "https://facebook.example/exact",
            "score": {"total": 88.0},
            "rank": 1,
        }]},
        sold={"listings": []},
    )
    active = [row for row in payload["listings"] if row["listing_type"] == "active"]
    assert len(active) == 2
    assert all(row["score"] is not None for row in active)
    screened = next(row for row in active if row["listing_id"] == "screen")
    assert screened["score_basis"] == "category_screening"
    assert payload["stats"]["scored"] == 2


def test_placeholder_lot_with_multiple_description_prices_stays_unpriced():
    record = normalize_facebook_listing(
        {
            "listing_id": "lot",
            "title": "Guitar effects pedals",
            "price_text": "$1",
            "detail_price_text": "$1",
            "description": "Mooer pedal $30. Boost pedal $60. Ditto pedal $80 or $150 for all 3.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "multiple_prices"
    assert "$30" in record["price_note"]


def test_offer_only_placeholder_stays_unpriced():
    record = normalize_facebook_listing(
        {
            "listing_id": "offer",
            "title": "DJ equipment - message with offers",
            "price_text": "$1",
            "description": "Everything works. Shoot me an offer for everything or individual items.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "make_offer"


def test_sequential_1234_detail_price_with_offer_language_stays_unpriced():
    record = normalize_facebook_listing(
        {
            "listing_id": "drum-lot",
            "title": "Tons of drums and cymbals",
            "price_text": "$1",
            "detail_price_text": "$1,234",
            "description": "Five drum sets, cymbals, and racks. Accepting real offers.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "make_offer"


def test_non_placeholder_facebook_value_is_labeled_as_a_headline_price():
    record = normalize_facebook_listing(
        {"listing_id": "normal", "title": "Audio interface", "price_text": "$60"},
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] == 60.0
    assert record["price_status"] == "headline"


def test_free_facebook_headline_is_not_assumed_to_be_a_real_zero_dollar_ask():
    record = normalize_facebook_listing(
        {"listing_id": "free", "title": "Free keyboard", "price_text": "FREE"},
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] is None
    assert record["price_status"] == "placeholder_unverified"
    assert "not a verified asking price" in record["price_note"]


def test_free_facebook_headline_requires_explicit_detail_confirmation():
    record = normalize_facebook_listing(
        {
            "listing_id": "actually-free",
            "title": "Keyboard",
            "price_text": "FREE",
            "description": "Giving it away to a good home. No charge.",
        },
        "2026-08-12T12:00:00-07:00",
    )
    assert record["asking_price"] == 0.0
    assert record["price_status"] == "verified_detail_free"


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
