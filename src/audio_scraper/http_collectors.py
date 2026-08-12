from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class HttpFetcher:
    """Read-only HTTP fetcher. This class intentionally exposes GET only."""

    client: Any = field(default=None)
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = httpx.Client(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
                },
                follow_redirects=True,
                timeout=self.timeout_seconds,
            )

    def get(self, url: str) -> tuple[str, str]:
        response = self.client.get(url)
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"GET {url} returned {response.status_code}",
                request=getattr(response, "request", None),
                response=response,
            )
        return response.text, str(response.url)
