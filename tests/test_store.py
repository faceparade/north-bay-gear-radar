from audio_scraper.models import ListingLead
from audio_scraper.store import deduplicate


def lead(source, listing_id, url, title, price="$100", location="Novato"):
    return ListingLead(source, listing_id, url, title, price, location)


def test_deduplicates_by_source_and_listing_id():
    rows = [
        lead("craigslist", "1", "https://x/1", "Scarlett 2i2"),
        lead("craigslist", "1", "https://x/1?x=1", "Scarlett 2i2 duplicate"),
    ]
    assert len(deduplicate(rows)) == 1


def test_secondary_fingerprint_catches_reposted_card():
    rows = [
        lead("facebook", "a", "https://x/a", "PreSonus Eris E5 Pair", "$100", "San Rafael"),
        lead("facebook", "b", "https://x/b", "presonus eris e5 pair", "$100", "San Rafael"),
    ]
    assert len(deduplicate(rows)) == 1
