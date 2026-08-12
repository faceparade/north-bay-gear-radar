from audio_scraper.cdp_browser import choose_page_target, scroll_expression


def test_choose_page_target_uses_matching_page_and_ignores_extensions():
    targets = [
        {"type": "background_page", "url": "chrome-extension://abc/help", "webSocketDebuggerUrl": "ws://extension"},
        {"type": "page", "url": "https://www.facebook.com/marketplace/", "webSocketDebuggerUrl": "ws://facebook"},
        {"type": "page", "url": "edge://newtab/", "webSocketDebuggerUrl": "ws://newtab"},
    ]
    assert choose_page_target(targets, "facebook.com")["webSocketDebuggerUrl"] == "ws://facebook"


def test_choose_page_target_returns_none_without_matching_page():
    assert choose_page_target([{"type": "page", "url": "https://example.com"}], "facebook.com") is None


def test_scroll_expression_tolerates_transient_missing_document_element():
    expression = scroll_expression()
    assert "document.documentElement?.scrollHeight" in expression
    assert "document.body?.scrollHeight" in expression
