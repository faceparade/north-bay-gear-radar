from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
UV = shutil.which("uv") or "uv"


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=ROOT, text=True, check=check)


def collection_is_healthy(path: Path, *, minimum: int, max_failures: int = 0) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return len(payload.get("listings", [])) >= minimum and len(payload.get("failures", [])) <= max_failures


def refresh_craigslist() -> None:
    raw = ROOT / "data" / "raw" / "craigslist.json"
    normalized = ROOT / "data" / "normalized" / "craigslist.json"
    raw_backup = raw.with_suffix(".json.previous")
    normalized_backup = normalized.with_suffix(".json.previous")
    for source, backup in ((raw, raw_backup), (normalized, normalized_backup)):
        if source.exists():
            shutil.copy2(source, backup)
    try:
        run([
            str(PYTHON), "-m", "audio_scraper.cli", "collect",
            "--source", "craigslist", "--postal-code", "94945", "--radius", "20",
            "--max-searches", "25", "--output", str(raw),
        ])
        if not collection_is_healthy(raw, minimum=40):
            raise RuntimeError("Craigslist collection failed health checks")
        run([str(PYTHON), "scripts/inspect_craigslist.py"])
        payload = json.loads(normalized.read_text(encoding="utf-8"))
        if len(payload.get("accepted", [])) < 5 or len(payload.get("failures", [])) > 10:
            raise RuntimeError("Craigslist inspection failed health checks")
    except Exception:
        for target, backup in ((raw, raw_backup), (normalized, normalized_backup)):
            if backup.exists():
                shutil.copy2(backup, target)
        raise
    finally:
        raw_backup.unlink(missing_ok=True)
        normalized_backup.unlink(missing_ok=True)


def refresh_facebook() -> None:
    target = ROOT / "data" / "checkpoints" / "facebook_expanded_discovery.json"
    backup = target.with_suffix(".json.previous")
    if target.exists():
        shutil.copy2(target, backup)
    try:
        run([str(PYTHON), "scripts/collect_facebook_expanded.py"])
        if not collection_is_healthy(target, minimum=40):
            raise RuntimeError("Facebook refresh failed health checks")
    except Exception:
        if backup.exists():
            shutil.copy2(backup, target)
        raise
    finally:
        backup.unlink(missing_ok=True)


def refresh_ebay() -> None:
    target = ROOT / "data" / "research" / "ebay_sold_exact_comparisons.json"
    backup = target.with_suffix(".json.previous")
    if target.exists():
        shutil.copy2(target, backup)
    try:
        run([str(PYTHON), "scripts/collect_ebay_sold.py"])
        if not collection_is_healthy(target, minimum=30):
            raise RuntimeError("eBay refresh failed health checks")
    except Exception:
        if backup.exists():
            shutil.copy2(backup, target)
        raise
    finally:
        backup.unlink(missing_ok=True)


def publish_if_changed() -> None:
    paths = [
        "data/raw/craigslist.json",
        "data/normalized/craigslist.json",
        "data/checkpoints/facebook_expanded_discovery.json",
        "data/research/ebay_sold_exact_comparisons.json",
        "data/normalized/listings.json",
        "site/data/listings.json",
    ]
    run(["git", "add", *paths])
    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False
    ).returncode != 0
    if not changed:
        print("No listing changes to publish.")
        return
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d")
    run(["git", "commit", "-m", f"data: refresh listings {stamp}"])
    run(["git", "push", "origin", "main"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely refresh gear data, verify it, and optionally publish it")
    parser.add_argument("--publish", action="store_true", help="commit and push changed data after verification")
    parser.add_argument("--skip-facebook", action="store_true")
    parser.add_argument("--skip-ebay", action="store_true")
    parser.add_argument("--skip-craigslist", action="store_true")
    args = parser.parse_args()

    if not PYTHON.exists():
        run([UV, "sync", "--extra", "dev"])
    if not args.skip_craigslist:
        refresh_craigslist()
    if not args.skip_facebook:
        refresh_facebook()
    if not args.skip_ebay:
        refresh_ebay()
    run([str(PYTHON), "scripts/score_shortlist.py"])
    run([str(PYTHON), "scripts/build_site_data.py"])
    run([str(PYTHON), "-m", "pytest"])
    if args.publish:
        publish_if_changed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
