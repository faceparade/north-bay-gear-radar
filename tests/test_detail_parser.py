from datetime import datetime, timezone

from audio_scraper.detail_parser import parse_craigslist_detail
from audio_scraper.models import ListingLead


HTML = '''
<html><head><title>Line 6 UX2 USB Audio Interface - craigslist</title></head><body>
<span id="titletextonly">Line 6 UX2 USB Audio Interface</span>
<span class="price">$25</span>
<section id="postingbody">QR Code Link to This Post Great interface. Includes USB cable.</section>
<time class="date timeago" datetime="2026-08-07T10:58:09-0700">Aug 7</time>
<time class="date timeago" datetime="2026-08-10T10:58:09-0700">updated</time>
<div id="map" data-latitude="38.214688" data-longitude="-122.629652"></div>
<p class="attrgroup"><span>condition: excellent</span></p>
<div class="gallery"><a href="https://images.craigslist.org/abc_1200x900.jpg"><img src="https://images.craigslist.org/abc_300x300.jpg"></a></div>
</body></html>
'''


def test_parse_craigslist_detail_extracts_structured_fields_and_distance():
    lead = ListingLead("craigslist", "abc", "https://example.test/abc", "Line 6 UX2", "$25", "Petaluma")
    detail = parse_craigslist_detail(HTML, lead, origin=(38.1074, -122.5697))
    assert detail.title == "Line 6 UX2 USB Audio Interface"
    assert detail.price == 25.0
    assert detail.description == "Great interface. Includes USB cable."
    assert detail.posted_at.isoformat().startswith("2026-08-07")
    assert detail.updated_at.isoformat().startswith("2026-08-10")
    assert detail.condition == "excellent"
    assert detail.image_url.endswith("abc_1200x900.jpg")
    assert 7 < detail.distance_miles < 9


def test_freshness_uses_original_posting_date_not_update_date():
    lead = ListingLead("craigslist", "abc", "https://example.test/abc", "Line 6 UX2", "$25", "Petaluma")
    detail = parse_craigslist_detail(HTML, lead, origin=(38.1074, -122.5697))
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    assert detail.age_days(now) == 4
