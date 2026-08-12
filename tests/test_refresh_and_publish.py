import json
from pathlib import Path

import pytest

from scripts.refresh_and_publish import (
    collection_is_healthy,
    facebook_details_are_healthy,
    publish_if_changed,
    prune_unreferenced_public_thumbnails,
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


def test_facebook_detail_health_requires_broad_detail_coverage(tmp_path):
    target = tmp_path / "facebook.json"
    target.write_text(json.dumps({
        "detail_collection_scope": "placeholder_prices",
        "details_attempted": 100,
        "details_fetched_current": 75,
    }), encoding="utf-8")
    assert facebook_details_are_healthy(target)
    payload = {
        "detail_collection_scope": "placeholder_prices",
        "details_attempted": 100,
        "details_fetched_current": 74,
    }
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert not facebook_details_are_healthy(target)

    target.write_text(json.dumps({
        "detail_collection_scope": "placeholder_prices",
        "details_attempted": 0,
        "details_fetched_current": 0,
    }), encoding="utf-8")
    assert facebook_details_are_healthy(target)


def test_gallery_does_not_clamp_notes_and_displays_price_and_time_provenance():
    root = Path(__file__).resolve().parents[1]
    css = (root / "site" / "styles.css").read_text(encoding="utf-8")
    app = (root / "site" / "app.js").read_text(encoding="utf-8")
    assert "line-clamp" not in css
    assert "white-space: pre-line" in css
    assert 'fact(row.listing_type === "sold" ? "Observed" : "Listed"' in app
    assert 'multiple_prices: "Multiple prices"' in app
    assert "reconcileSavedPrices();" in app


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
    image_dir = tmp_path / "site" / "images" / "listings"
    image_dir.mkdir(parents=True)
    original_image = image_dir / "facebook-good.webp"
    original_image.write_bytes(b"original")

    def bad_run(_command):
        write_payload(target, 2)
        original_image.unlink()
        (image_dir / "facebook-bad.webp").write_bytes(b"bad")

    monkeypatch.setattr(module, "run", bad_run)
    with pytest.raises(RuntimeError, match="health checks"):
        refresh_facebook()
    assert json.loads(target.read_text(encoding="utf-8")) == original
    assert original_image.read_bytes() == b"original"
    assert not (image_dir / "facebook-bad.webp").exists()
    assert not target.with_suffix(".json.previous").exists()


def test_public_thumbnail_pruning_keeps_only_site_references(tmp_path, monkeypatch):
    import scripts.refresh_and_publish as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    data = tmp_path / "site" / "data"
    images = tmp_path / "site" / "images" / "listings"
    data.mkdir(parents=True)
    images.mkdir(parents=True)
    (data / "listings.json").write_text(
        json.dumps({"listings": [
            {"thumbnail_url": "images/listings/facebook-keep.webp"},
            {"thumbnail_url": "https://example.test/not-local.webp"},
        ]}),
        encoding="utf-8",
    )
    (images / "facebook-keep.webp").write_bytes(b"keep")
    (images / "facebook-stale.webp").write_bytes(b"stale")
    (images / "notes.txt").write_text("leave non-generated files alone", encoding="utf-8")

    assert prune_unreferenced_public_thumbnails() == 1
    assert (images / "facebook-keep.webp").read_bytes() == b"keep"
    assert not (images / "facebook-stale.webp").exists()
    assert (images / "notes.txt").exists()


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
    assert "site/images/listings" in add
