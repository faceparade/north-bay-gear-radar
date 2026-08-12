from __future__ import annotations

from audio_scraper.inspection import inspect_craigslist


def main() -> None:
    summary = inspect_craigslist(
        "data/raw/craigslist.json",
        "data/normalized/craigslist.json",
        origin=(38.1074, -122.5697),
        max_candidates=100,
    )
    print(summary)


if __name__ == "__main__":
    main()
