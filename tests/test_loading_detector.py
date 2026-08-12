from audio_scraper.loading import LoadObservation, LoadingDetector, LoadingMode


def obs(ids, *, next_link=False, numbered=False, load_more=False, scroll_height=1000):
    return LoadObservation(
        listing_ids=frozenset(ids),
        has_next=next_link,
        has_numbered_pages=numbered,
        has_load_more=load_more,
        scroll_height=scroll_height,
    )


def test_detects_numbered_pagination_without_scrolling_growth():
    detector = LoadingDetector()
    result = detector.classify([
        obs({"a", "b"}, next_link=True, numbered=True),
        obs({"a", "b"}, next_link=True, numbered=True),
    ])
    assert result.mode is LoadingMode.PAGINATION
    assert result.should_click_next is True


def test_detects_infinite_scroll_when_new_ids_appear_after_scroll():
    detector = LoadingDetector()
    result = detector.classify([
        obs({"a", "b"}, scroll_height=1000),
        obs({"a", "b", "c"}, scroll_height=1600),
    ])
    assert result.mode is LoadingMode.INFINITE_SCROLL
    assert result.should_scroll is True


def test_detects_hybrid_when_load_more_and_pagination_are_present():
    detector = LoadingDetector()
    result = detector.classify([
        obs({"a"}, next_link=True, load_more=True),
        obs({"a", "b"}, next_link=True, load_more=True, scroll_height=1500),
    ])
    assert result.mode is LoadingMode.HYBRID


def test_stops_after_three_no_growth_observations():
    detector = LoadingDetector(no_growth_limit=3)
    observations = [obs({"a"}, scroll_height=1000)]
    observations.extend(obs({"a"}, scroll_height=1000) for _ in range(3))
    result = detector.classify(observations)
    assert result.stop is True
    assert result.reason == "no_new_listings"


def test_stops_on_repeated_page_fingerprint():
    detector = LoadingDetector(repeated_fingerprint_limit=2)
    result = detector.classify([
        obs({"a", "b"}, next_link=True),
        obs({"a", "b"}, next_link=True),
        obs({"a", "b"}, next_link=True),
    ])
    assert result.stop is True
    assert result.reason == "repeated_fingerprint"
