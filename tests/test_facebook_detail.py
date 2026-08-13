import pytest

from scripts.collect_facebook_expanded import requires_detail_evidence
from audio_scraper.facebook_detail import collect_facebook_detail, parse_facebook_detail_text


def test_parse_facebook_detail_extracts_visible_fields_without_seller_section():
    text = """Marketplace
Guitar effects pedals
$1
Listed 4 weeks ago in Petaluma, CA
Message
Details
Condition
Used - like new
Mooer pedal $30
Boost pedal $60
Ditto pedal $80 or $150 for all 3.
Petaluma, CA
Location is approximate
Seller information
Seller details
Example Seller
"""
    parsed = parse_facebook_detail_text(text, title="Guitar effects pedals")
    assert parsed["listing_age_text"] == "4 weeks ago"
    assert parsed["condition"] == "Used - like new"
    assert parsed["description"].startswith("Mooer pedal $30")
    assert "Example Seller" not in parsed["description"]


def test_parse_facebook_detail_allows_location_without_an_age():
    text = """Rocktron effects
$1
Listed in Sonoma, CA
Message
Details
Condition
Used - Good
Lexicon MPX1 $500
Rocktron Intellifex $600
Sonoma, CA
Location is approximate
Seller information
"""
    parsed = parse_facebook_detail_text(text, title="Rocktron effects")
    assert parsed["listing_age_text"] == ""
    assert parsed["description"] == "Lexicon MPX1 $500\nRocktron Intellifex $600"


class FakePage:
    def __init__(self, final_url: str):
        self.final_url = final_url

    def navigate(self, _url: str, timeout: int):
        assert timeout == 30

    def evaluate(self, _script: str):
        return {
            "url": self.final_url,
            "title": "Audio interface",
            "text": "Audio interface\n$80\nListed yesterday in Novato, CA\nMessage\nDetails",
        }


def test_collect_detail_rejects_a_stale_page_for_a_different_listing():
    with pytest.raises(RuntimeError, match="opened a different listing"):
        collect_facebook_detail(
            FakePage("https://www.facebook.com/marketplace/item/999/"),
            {"listing_id": "123", "url": "https://www.facebook.com/marketplace/item/123/"},
            settle_seconds=0,
        )


def test_collect_detail_accepts_the_requested_listing_id():
    parsed = collect_facebook_detail(
        FakePage("https://www.facebook.com/marketplace/item/123/?ref=search"),
        {"listing_id": "123", "url": "https://www.facebook.com/marketplace/item/123/"},
        settle_seconds=0,
    )
    assert parsed["detail_title"] == "Audio interface"
    assert parsed["listing_age_text"] == "yesterday"


@pytest.mark.parametrize("price_text", ["FREE", "$0", "$1", "$123", "$1,234", "$12,345"])
def test_placeholder_prices_require_detail_evidence(price_text):
    assert requires_detail_evidence({"price_text": price_text})


def test_ordinary_fixed_price_does_not_require_detail_navigation():
    assert not requires_detail_evidence({"price_text": "$80"})


def test_reduced_price_card_with_money_only_title_requires_detail_navigation():
    assert requires_detail_evidence({
        "title": "$125",
        "price_text": "$75",
        "discovery_groups": ["recording_foundation"],
    })