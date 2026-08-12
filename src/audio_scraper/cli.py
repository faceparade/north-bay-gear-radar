from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote_plus

from .cdp_browser import CdpPage, cdp_targets, choose_page_target, collect_queries
from .checkpoint import write_checkpoint
from .http_collectors import HttpFetcher
from .parsers import parse_craigslist_results
from .sources import DEFAULT_SEARCHES, build_search_urls
from .store import deduplicate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audio-scraper")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="emit the read-only search plan")
    plan.add_argument("--source", choices=sorted(DEFAULT_SEARCHES), required=True)
    plan.add_argument("--postal-code", default="94945")
    plan.add_argument("--radius", type=int, default=20)
    plan.add_argument("--json", action="store_true")

    collect = sub.add_parser("collect", help="collect read-only HTTP sources to a JSON checkpoint")
    collect.add_argument("--source", choices=["craigslist"], required=True)
    collect.add_argument("--postal-code", default="94945")
    collect.add_argument("--radius", type=int, default=20)
    collect.add_argument("--max-searches", type=int, default=25)
    collect.add_argument("--output", type=Path, required=True)

    browser = sub.add_parser(
        "browser-collect",
        help="collect an existing authenticated browser tab through local CDP",
    )
    browser.add_argument("--source", choices=["facebook", "ebay"], required=True)
    browser.add_argument("--port", type=int, required=True)
    browser.add_argument("--query", action="append", required=True)
    browser.add_argument("--max-scrolls", type=int, default=8)
    browser.add_argument("--settle-seconds", type=float, default=1.0)
    browser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None, *, fetcher=None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "browser-collect":
        fragment = "facebook.com" if args.source == "facebook" else "ebay.com"
        target = choose_page_target(cdp_targets(args.port), fragment)
        if target is None:
            print(json.dumps({
                "source": args.source,
                "read_only": True,
                "error": f"no open {fragment} page found on CDP port {args.port}",
            }))
            return 2
        if args.source == "facebook":
            urls = [
                f"https://www.facebook.com/marketplace/search/?query={quote_plus(query)}"
                for query in args.query
            ]
        else:
            urls = [
                f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}"
                for query in args.query
            ]
        page = CdpPage(str(target["webSocketDebuggerUrl"]))
        listings, failures = collect_queries(
            page,
            source=args.source,
            search_urls=urls,
            max_scrolls=args.max_scrolls,
            settle_seconds=args.settle_seconds,
        )
        completed = len(urls) - len(failures)
        write_checkpoint(
            args.output,
            source=args.source,
            searches_completed=completed,
            listings=listings,
            metadata={
                "queries": args.query,
                "cdp_port": args.port,
                "failures": failures,
            },
        )
        print(json.dumps({
            "source": args.source,
            "read_only": True,
            "searches_completed": completed,
            "unique_listings": len(listings),
            "failures": len(failures),
            "output": str(args.output),
        }))
        return 0 if completed else 2

    targets = build_search_urls(args.source, postal_code=args.postal_code, radius_miles=args.radius)

    if args.command == "collect":
        http = fetcher or HttpFetcher()
        listings = []
        completed = 0
        failures: list[dict[str, str]] = []
        for target in targets[:args.max_searches]:
            try:
                html, final_url = http.get(target.url)
                page = parse_craigslist_results(html, final_url)
                listings.extend(page.listings)
                completed += 1
            except Exception as exc:
                failures.append({"label": target.label, "error": f"{type(exc).__name__}: {exc}"})
        unique = deduplicate(listings)
        write_checkpoint(
            args.output,
            source=args.source,
            searches_completed=completed,
            listings=unique,
            metadata={"postal_code": args.postal_code, "radius_miles": args.radius, "failures": failures},
        )
        print(json.dumps({
            "source": args.source,
            "read_only": True,
            "searches_completed": completed,
            "unique_listings": len(unique),
            "failures": len(failures),
            "output": str(args.output),
        }))
        return 0 if completed else 2

    payload = {
        "source": args.source,
        "read_only": True,
        "postal_code": args.postal_code,
        "radius_miles": args.radius,
        "searches": [
            {"label": item.label, "kind": item.kind, "url": item.url}
            for item in targets
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for target in targets:
            print(f"{target.kind:8} {target.label:24} {target.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
