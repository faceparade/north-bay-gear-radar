from scripts.collect_facebook_expanded import (
    CATEGORY_URLS,
    INITIAL_CATEGORY_SCROLLS,
    QUERY_GROUPS,
    REFRESH_CATEGORY_SCROLLS,
    category_discovery_plan,
)


def test_facebook_discovery_includes_the_broad_audio_interface_query():
    queries = {query for group in QUERY_GROUPS.values() for query in group}

    assert "audio interface" in queries
    # Sellers frequently title listings only with a brand/model, so recall
    # cannot rely on Marketplace's generic category or keyword ranking.
    assert "PreSonus AudioBox" in queries


def test_facebook_category_plan_deeply_backfills_then_uses_shallow_newest_refreshes():
    initial = category_discovery_plan(has_completed_initial_backfill=False)
    refresh = category_discovery_plan(has_completed_initial_backfill=True)

    assert [run[1] for run in initial] == list(CATEGORY_URLS)
    assert all(run[2] == INITIAL_CATEGORY_SCROLLS for run in initial)
    assert all(run[2] == REFRESH_CATEGORY_SCROLLS for run in refresh)
    assert all("sortBy=creation_time_descend" in url for url in CATEGORY_URLS.values())
    assert INITIAL_CATEGORY_SCROLLS > REFRESH_CATEGORY_SCROLLS >= 12
