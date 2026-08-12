import json

from audio_scraper.inspection import inspect_craigslist
from audio_scraper.models import ListingLead


HTML = '''<span id="titletextonly">Focusrite Scarlett 2i2</span><span class="price">$80</span>
<section id="postingbody">QR Code Link to This Post Includes USB cable.</section>
<time datetime="2026-08-08T10:00:00-0700">posted</time>
<div id="map" data-latitude="38.10" data-longitude="-122.57"></div>'''


class Fetcher:
    def get(self, url):
        return HTML, url


def test_inspection_writes_normalized_checkpoint(tmp_path):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"listings": [{
        "source": "craigslist", "listing_id": "abc", "url": "https://example.test/abc",
        "title": "Focusrite Scarlett 2i2", "price_text": "$80", "location_text": "Novato"
    }]}), encoding="utf-8")
    output = tmp_path / "normalized.json"
    summary = inspect_craigslist(raw, output, fetcher=Fetcher(), origin=(38.1074, -122.5697), max_candidates=10)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert summary["accepted"] == 1
    assert payload["accepted"][0]["asking_price"] == 80.0
    assert payload["accepted"][0]["description"] == "Includes USB cable."
