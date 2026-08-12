"""Minimal read-only Chrome DevTools Protocol bridge for browser sources."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Mapping, Sequence
from itertools import count
from typing import Any
from urllib.request import urlopen
from urllib.parse import urlparse

from websockets.sync.client import connect

from .browser_extractors import parse_browser_payload
from .browser_scripts import extractor_script
from .models import ListingLead
from .store import deduplicate


def cdp_targets(port: int, *, host: str = "127.0.0.1") -> list[dict[str, Any]]:
    with urlopen(f"http://{host}:{port}/json/list", timeout=10) as response:
        payload = json.load(response)
    return [dict(item) for item in payload]


def choose_page_target(
    targets: Sequence[Mapping[str, Any]], url_fragment: str
) -> Mapping[str, Any] | None:
    fragment = url_fragment.casefold()
    for target in targets:
        if (
            target.get("type") == "page"
            and fragment in str(target.get("url", "")).casefold()
            and target.get("webSocketDebuggerUrl")
        ):
            return target
    return None


def scroll_expression() -> str:
    """Return a scroll command safe during transient document replacement."""
    return "window.scrollTo(0, document.documentElement?.scrollHeight ?? document.body?.scrollHeight ?? 0); true"


class CdpPage:
    """Issue bounded CDP commands to one existing dedicated browser tab."""

    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self._ids = count(1)

    def command(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        command_id = next(self._ids)
        request = {"id": command_id, "method": method, "params": dict(params or {})}
        with connect(
            self.websocket_url,
            # CDP does not require a web-page Origin. Sending localhost causes
            # modern Edge to reject the upgrade unless launched with a broad
            # allow-origins flag, so intentionally omit it.
            origin=None,
            open_timeout=10,
            close_timeout=2,
            max_size=16 * 1024 * 1024,
        ) as socket:
            socket.send(json.dumps(request))
            while True:
                response = json.loads(socket.recv(timeout=30))
                if response.get("id") != command_id:
                    continue
                if "error" in response:
                    raise RuntimeError(f"CDP {method} failed: {response['error']}")
                return dict(response.get("result", {}))

    def evaluate(self, expression: str) -> Any:
        result = self.command("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        remote = result.get("result", {})
        if remote.get("subtype") == "error":
            raise RuntimeError(remote.get("description", "browser evaluation failed"))
        return remote.get("value")

    def navigate(self, url: str, *, timeout: float = 30.0) -> None:
        self.command("Page.navigate", {"url": url})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self.evaluate("document.readyState") in {"interactive", "complete"}:
                    return
            except RuntimeError:
                pass
            time.sleep(0.25)
        raise TimeoutError(f"page did not become ready within {timeout:g}s: {url}")


def validate_search_page(
    *, source: str, url: str, title: str, has_login_form: bool
) -> None:
    expected_host = "facebook.com" if source == "facebook" else "ebay.com"
    host = (urlparse(url).hostname or "").casefold()
    sign_in = has_login_form or "sign in" in title.casefold() or host.startswith("signin.")
    if sign_in:
        raise RuntimeError(f"{source} authentication required at {url}")
    if not (host == expected_host or host.endswith("." + expected_host)):
        raise RuntimeError(f"{source} navigation left expected domain: {url}")


def collect_search(
    page: CdpPage,
    *,
    source: str,
    url: str,
    max_scrolls: int = 12,
    settle_seconds: float = 1.0,
) -> list[ListingLead]:
    """Navigate and collect until two scrolls reveal no new listing IDs."""

    page.navigate(url)
    time.sleep(settle_seconds)
    state = page.evaluate("({url:location.href,title:document.title,has_login_form:!!document.querySelector('input[type=password],input[name=email]')})")
    if not isinstance(state, Mapping):
        raise RuntimeError(f"{source} page-state check returned a non-object payload")
    validate_search_page(
        source=source,
        url=str(state.get("url", "")),
        title=str(state.get("title", "")),
        has_login_form=bool(state.get("has_login_form")),
    )
    script = extractor_script(source)
    listings: list[ListingLead] = []
    seen_ids: set[str] = set()
    stable_rounds = 0

    for _ in range(max_scrolls + 1):
        payload = page.evaluate(script)
        if not isinstance(payload, Mapping):
            raise RuntimeError(f"{source} extractor returned a non-object payload")
        parsed, observation = parse_browser_payload(source, payload)
        listings.extend(parsed.listings)
        current = set(observation.listing_ids)
        if current <= seen_ids:
            stable_rounds += 1
        else:
            stable_rounds = 0
            seen_ids.update(current)
        if stable_rounds >= 2:
            break
        page.evaluate(scroll_expression())
        time.sleep(settle_seconds)

    return deduplicate(listings)


def collect_queries(
    page: CdpPage,
    *,
    source: str,
    search_urls: Iterable[str],
    max_scrolls: int = 12,
    settle_seconds: float = 1.0,
) -> tuple[list[ListingLead], list[dict[str, str]]]:
    listings: list[ListingLead] = []
    failures: list[dict[str, str]] = []
    for url in search_urls:
        try:
            listings.extend(collect_search(
                page,
                source=source,
                url=url,
                max_scrolls=max_scrolls,
                settle_seconds=settle_seconds,
            ))
        except Exception as exc:
            failures.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
    return deduplicate(listings), failures
