from __future__ import annotations

import argparse
import json
from pathlib import Path

from audio_scraper.site_data import build_site_payload_from_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized data for the gear dashboard")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output or root / "site" / "data" / "listings.json"
    payload = build_site_payload_from_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    normalized = root / "data" / "normalized" / "listings.json"
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Wrote {payload['stats']['total']} rows "
        f"({payload['stats']['active']} active, {payload['stats']['sold']} sold) to {output}"
    )


if __name__ == "__main__":
    main()
