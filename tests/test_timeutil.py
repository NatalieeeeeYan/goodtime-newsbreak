from datetime import datetime, timedelta, timezone

from headsup.models import CalendarEvent
from headsup.timeutil import compute_free_slots, parse_relative


def test_parse_relative_offsets(now):
    assert parse_relative("+45m", now) == now + timedelta(minutes=45)
    assert parse_relative("+2h", now) == now + timedelta(hours=2)
    assert parse_relative("+1d", now) == now + timedelta(days=1)
    assert parse_relative("+1h30m", now) == now + timedelta(hours=1, minutes=30)
    assert parse_relative("-15m", now) == now - timedelta(minutes=15)


def test_parse_relative_today_tomorrow(now):
    assert parse_relative("today 09:15", now) == now.replace(hour=9, minute=15)
    assert parse_relative("tomorrow 19:00", now) == (now + timedelta(days=1)).replace(hour=19, minute=0)


def test_parse_relative_iso_and_datetime(now):
    assert parse_relative("2026-09-26T10:00:00+00:00", now) == datetime(2026, 9, 26, 10, tzinfo=timezone.utc)
    assert parse_relative(now, now) == now


def test_compute_free_slots(now):
    ev = lambda i, s, e: CalendarEvent(id=i, title=i, start=now + timedelta(hours=s), end=now + timedelta(hours=e))
    events = [ev("a", 1, 2), ev("b", 5, 6)]
    slots = compute_free_slots(events, now, now + timedelta(hours=8), min_minutes=120)
    assert [(s.start, s.end) for s in slots] == [
        (now + timedelta(hours=2), now + timedelta(hours=5)),
        (now + timedelta(hours=6), now + timedelta(hours=8)),
    ]
