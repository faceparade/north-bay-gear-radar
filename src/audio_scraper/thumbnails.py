from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_EDGE = 320
ALLOWED_IMAGE_HOSTS = {
    "facebook": (".fbcdn.net",),
    "craigslist": (".craigslist.org", ".craigslist.orgcdn.com"),
    "ebay": (".ebayimg.com",),
}
SAFE_LISTING_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _approved_host(source: str, image_url: str) -> bool:
    host = (urlparse(image_url).hostname or "").lower()
    return bool(host) and any(host.endswith(suffix) for suffix in ALLOWED_IMAGE_HOSTS.get(source, ()))


def _safe_thumbnail_path(source: str, listing_id: str) -> str | None:
    if source not in ALLOWED_IMAGE_HOSTS or not SAFE_LISTING_ID.fullmatch(listing_id):
        return None
    return f"images/listings/{source}-{listing_id}.webp"


def save_listing_thumbnail(
    *,
    source: str,
    listing_id: str,
    image_url: str,
    site_root: Path,
    client=None,
) -> str | None:
    """Download one listing image and publish only a stripped low-res derivative."""
    relative = _safe_thumbnail_path(source, listing_id)
    if relative is None or not _approved_host(source, image_url):
        return None
    http = client or httpx.Client(
        follow_redirects=True,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        response = http.get(image_url)
        if response.status_code >= 400:
            return None
        if not response.headers.get("content-type", "").lower().startswith("image/"):
            return None
        if len(response.content) > MAX_SOURCE_BYTES:
            return None
        if not _approved_host(source, str(getattr(response, "url", image_url))):
            return None
        with Image.open(BytesIO(response.content)) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
            target = site_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".webp.tmp")
            image.save(temporary, format="WEBP", quality=58, method=6)
            temporary.replace(target)
            return relative
    except (httpx.HTTPError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return None
    finally:
        if client is None:
            http.close()


def sync_listing_thumbnails(rows: list[dict], *, site_root: Path, client=None) -> dict[str, int]:
    """Materialize current thumbnails, strip signed URLs, and remove stale derivatives."""
    counts = {"saved": 0, "retained": 0, "failed": 0, "pruned": 0}
    expected: set[Path] = set()
    sources = {str(row.get("source", "")) for row in rows if row.get("source")}
    for row in rows:
        source = str(row.get("source", ""))
        listing_id = str(row.get("listing_id", ""))
        image_url = str(row.pop("image_url", "") or "")
        relative = _safe_thumbnail_path(source, listing_id)
        if relative is None:
            row.pop("thumbnail_path", None)
            if image_url:
                counts["failed"] += 1
            continue
        target = site_root / relative
        if image_url:
            saved = save_listing_thumbnail(
                source=source,
                listing_id=listing_id,
                image_url=image_url,
                site_root=site_root,
                client=client,
            )
            if saved:
                row["thumbnail_path"] = saved
                expected.add(site_root / saved)
                counts["saved"] += 1
                continue
        if target.exists():
            row["thumbnail_path"] = relative
            expected.add(target)
            counts["retained"] += 1
        else:
            row.pop("thumbnail_path", None)
            if image_url:
                counts["failed"] += 1
    directory = site_root / "images" / "listings"
    if directory.exists():
        for source in sources:
            for existing in directory.glob(f"{source}-*.webp"):
                if existing not in expected:
                    existing.unlink()
                    counts["pruned"] += 1
    return counts
