import json
from pathlib import Path

import pytest

from scripts.refresh_and_publish import (
    collection_is_healthy,
    publish_if_changed,
    refresh_craigslist,
    refresh_facebook,
)


def write_payload(path: Path, listings: int, failures: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"listings": [{}] * listings, "failures": [{}] * failures}), encoding="utf-8")


def test_collection_health_requires_minimum_rows_and_no_failures(tmp_path):
    target = tmp_path / "data.json"
    write_payload(target, 50)
    assert collection_is_healthy(target, minimum=40)
    write_payload(target, 39)
    assert not collection_is_healthy(target, minimum=40)
    write_payload(target, 50, failures=1)
    assert not collection_is_healthy(target, minimum=40)


def test_craigslist_refresh_runs_collection_and_inspection(monkeypatch, tmp_path):
    import scripts.refresh_and_publish as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "PYTHON", Path("python.exe"))
    commands = []

    def fake_run(command):
        commands.append(command)
        if "collect" in command:
            write_payload(tmp_path / "data" / "raw" / "craigslist.json", 50)
        else:
            target = tmp_path / "data" / "normalized" / "craigslist.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"accepted": [{}] * 10, "failures": []}), encoding="utf-8")

    monkeypatch.setattr(module, "run", fake_run)
    refresh_craigslist()
    assert len(commands) == 2
    assert commands[0][1:4] == ["-m", "audio_scraper.cli", "collect"]
    assert commands[1][1:] == ["scripts/inspect_craigslist.py"]


def test_facebook_refresh_restores_previous_data_on_failed_health_check(tmp_path, monkeypatch):
    import scripts.refresh_and_publish as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "PYTHON", Path("python.exe"))
    target = tmp_path / "data" / "checkpoints" / "facebook_expanded_discovery.json"
    original = {"listings": [{"listing_id": "good"}] * 50, "failures": []}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(original), encoding="utf-8")

    def bad_run(_command):
        write_payload(target, 2)

    monkeypatch.setattr(module, "run", bad_run)
    with pytest.raises(RuntimeError, match="health checks"):
        refresh_facebook()
    assert json.loads(target.read_text(encoding="utf-8")) == original
    assert not target.with_suffix(".json.previous").exists()


def test_publish_stages_catalog_and_scored_shortlist(monkeypatch, tmp_path):
    import scripts.refresh_and_publish as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    commands = []

    def fake_run(command):
        commands.append(command)

    class Changed:
        returncode = 1

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: Changed())
    publish_if_changed()
    add = commands[0]
    assert add[:2] == ["git", "add"]
    assert "data/research/catalog.json" in add
    assert "data/normalized/scored_shortlist.json" in add
