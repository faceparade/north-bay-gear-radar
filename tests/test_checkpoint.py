import json
from audio_scraper.checkpoint import write_checkpoint
from audio_scraper.models import ListingLead


def test_checkpoint_is_atomic_json(tmp_path):
    target = tmp_path / "raw.json"
    write_checkpoint(target, source="craigslist", searches_completed=2, listings=[
        ListingLead("craigslist", "abc", "https://example.test/abc", "Mixer", "$40", "Novato")
    ])
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["read_only"] is True
    assert payload["searches_completed"] == 2
    assert not (tmp_path / "raw.json.tmp").exists()
