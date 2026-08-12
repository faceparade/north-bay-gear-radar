from audio_scraper.collector import collect_paginated
from audio_scraper.models import ListingLead, ParsedPage


def test_collect_paginated_follows_next_and_stops_when_page_repeats():
    pages = {
        "https://example.test/1": ParsedPage(
            [ListingLead("x", "1", "https://x/1", "one", "$1", "Novato")],
            has_next=True,
            next_url="https://example.test/2",
        ),
        "https://example.test/2": ParsedPage(
            [ListingLead("x", "2", "https://x/2", "two", "$2", "Novato")],
            has_next=True,
            next_url="https://example.test/2",
        ),
    }

    def fetch(url):
        return pages[url]

    result = collect_paginated("https://example.test/1", fetch, max_pages=10)
    assert [row.listing_id for row in result.listings] == ["1", "2"]
    assert result.pages_visited == 2
    assert result.stop_reason == "repeated_page_url"
