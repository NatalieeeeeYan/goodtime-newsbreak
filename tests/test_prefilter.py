from datetime import timedelta

import pytest

from headsup.models import CalendarEvent, FreeSlot, GeoPoint, LocalEvent, Profile
from headsup.relevance import prefilter

HOME = GeoPoint(lat=37.8044, lon=-122.2712, label="home")
SCHOOL = GeoPoint(lat=37.8716, lon=-122.2727, label="school")


@pytest.fixture
def profile():
    return Profile(name="Nat", home=HOME, school=SCHOOL, preferences=["live music"])


def make_event(now, **kw):
    base = dict(
        id="inject:x", source="inject", type="traffic", title="Crash on I-580",
        summary="Two-car collision", lat=37.83, lon=-122.27, radius_km=3,
        starts_at=now, ends_at=now + timedelta(hours=2), severity=4,
    )
    base.update(kw)
    return LocalEvent(**base)


def test_event_far_away_is_dropped(now, profile):
    ev = make_event(now, lat=34.05, lon=-118.24)
    assert prefilter(ev, profile, [], [], now) is None


def test_event_in_past_is_dropped(now, profile):
    ev = make_event(now, starts_at=now - timedelta(hours=5), ends_at=now - timedelta(hours=1))
    assert prefilter(ev, profile, [], [], now) is None


def test_event_near_home_passes_and_matches_calendar(now, profile):
    school_run = CalendarEvent(id="c1", title="School drop-off", start=now + timedelta(hours=1), end=now + timedelta(hours=1, minutes=30), geo=SCHOOL)
    later = CalendarEvent(id="c2", title="Dinner", start=now + timedelta(hours=12), end=now + timedelta(hours=13))
    cand = prefilter(make_event(now), profile, [school_run, later], [], now)
    assert cand is not None
    assert [e.id for e in cand.matched_events] == ["c1"]


def test_traffic_on_commute_corridor_passes(now, profile):
    on_route = make_event(now, lat=37.84, lon=-122.272, radius_km=1)
    assert prefilter(on_route, profile, [], [], now) is not None


def test_event_type_requires_free_slot(now, profile):
    market = make_event(now, type="event", title="Night market", starts_at=now + timedelta(hours=10), ends_at=now + timedelta(hours=14), lat=HOME.lat, lon=HOME.lon)
    assert prefilter(market, profile, [], [], now) is None
    free = [FreeSlot(start=now + timedelta(hours=9), end=now + timedelta(hours=15))]
    assert prefilter(market, profile, [], free, now) is not None
