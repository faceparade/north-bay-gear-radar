# North Bay Gear Radar

A read-only local music-gear discovery and valuation workflow for the North Bay, California area. It keeps current Facebook Marketplace and Craigslist asking prices separate from conservatively filtered exact-model eBay sold evidence.

## Dashboard

The static dashboard is generated into `site/` and is designed for GitHub Pages. It includes:

- Full-text search
- Active versus sold-evidence views
- Category and source filters
- Price filters
- Setup-fit scores and exact-model market ranges
- Direct links to original listings
- Responsive desktop/mobile layout

### Build locally

```bash
uv sync --extra dev
uv run python scripts/build_site_data.py
uv run python -m pytest
python -m http.server 8765 --directory site
```

Open [http://localhost:8765](http://localhost:8765).

## Data boundaries

- **Active finds** are asking prices and may be stale or unavailable.
- **Sold evidence** is historical valuation evidence, not inventory.
- Facebook collection is read-only and uses an authenticated local Edge profile via CDP port `9223`.
- Credentials, browser profiles, cookies, and tokens are never committed.

## Publishing

GitHub Pages deploys the checked-in `site/` artifact on pushes to `main`. Authenticated Facebook refreshes must run on the local Windows machine; GitHub-hosted runners cannot access the local browser session.

The local refresh runner:

```bash
uv run python scripts/refresh_and_publish.py --publish
```

It refuses to overwrite good data if a collector fails, rebuilds the dashboard, runs the full regression suite, commits only changed research/site artifacts, and pushes when GitHub authentication is available.

## Local schedule

Windows Task Scheduler runs `scripts/run_scheduled_refresh.cmd` daily at 10:00 AM under the local user. The wrapper is silent on success, writes `data/refresh-failure.log` on failure, and shows a local actionable failure notification. Check prerequisites without collecting or publishing:

```bash
uv run python scripts/scheduled_refresh.py --check
```

The public dashboard also links to `site/buying-guide.html`, a budget-aware Windows 11 guide grounded in verified listing photos, seller disclosures, official compatibility pages, and separately labeled market evidence.
