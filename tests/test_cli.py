import json
from audio_scraper.cli import main


def test_cli_plan_emits_machine_readable_search_plan(capsys):
    code = main(["plan", "--source", "craigslist", "--postal-code", "94945", "--radius", "20", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "craigslist"
    assert payload["searches"]
