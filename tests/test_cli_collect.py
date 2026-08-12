import json

from audio_scraper.cli import main


class FakeFetcher:
    def get(self, url):
        return '''<li class="cl-static-search-result" title="Focusrite 2i2">
        <a href="https://www.craigslist.org/view/d/novato-focusrite-2i2/AbCdEfGh123">
        <div class="title">Focusrite 2i2</div><div class="price">$80</div>
        <div class="location">novato</div></a></li>''', url


def test_cli_collect_craigslist_writes_checkpoint(tmp_path, capsys):
    output = tmp_path / "leads.json"
    code = main([
        "collect", "--source", "craigslist", "--postal-code", "94945",
        "--radius", "20", "--max-searches", "1", "--output", str(output),
    ], fetcher=FakeFetcher())
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["read_only"] is True
    assert payload["source"] == "craigslist"
    assert payload["listings"][0]["listing_id"] == "AbCdEfGh123"
    printed = json.loads(capsys.readouterr().out)
    assert printed["unique_listings"] == 1
