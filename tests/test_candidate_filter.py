from datetime import datetime, timedelta, timezone

from audio_scraper.filters import FilterPolicy, filter_details, prefilter_leads
from audio_scraper.models import ListingDetail, ListingLead


def lead(title, price="$100", location="Novato"):
    return ListingLead("craigslist", title, f"https://example.test/{title}", title, price, location)


def detail(title, *, age=5, distance=10, price=100):
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    return ListingDetail(
        source="craigslist", listing_id=title, url=f"https://example.test/{title}",
        title=title, asking_price=price, location_text="Novato",
        posted_at=now - timedelta(days=age), distance_miles=distance,
    )


def test_prefilter_keeps_broad_useful_roles_and_rejects_wanted_ads():
    leads = [
        lead("USB audio interface"), lead("analog synthesizer"), lead("electric guitar"),
        lead("Wanted vintage synthesizer", "$500000"), lead("keyboard carrying case"),
    ]
    kept = prefilter_leads(leads, max_price=600)
    assert {x.title for x in kept} == {"USB audio interface", "analog synthesizer", "electric guitar"}


def test_filter_enforces_freshness_and_radius_but_tracks_exception_reason():
    policy = FilterPolicy(max_age_days=42, hard_max_age_days=140, radius_miles=20)
    accepted, rejected = filter_details([
        detail("near and fresh", age=10, distance=12),
        detail("too old", age=150, distance=3),
        detail("too far", age=3, distance=40),
    ], policy=policy, now=datetime(2026, 8, 12, tzinfo=timezone.utc))
    assert [x.title for x in accepted] == ["near and fresh"]
    assert {x.detail.title: x.reason for x in rejected} == {
        "too old": "older_than_20_weeks",
        "too far": "outside_radius",
    }
