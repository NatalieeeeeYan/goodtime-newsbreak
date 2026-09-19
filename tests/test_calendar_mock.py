import json
from datetime import timedelta

from headsup.integrations.calendar_mock import MockCalendar


def test_mock_calendar_resolves_relative_times_and_inserts(tmp_path, now):
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({"events": [
        {"id": "c1", "title": "School drop-off", "start": "+1h", "end": "+1h30m", "location": "Berkeley", "geo": {"lat": 37.87, "lon": -122.27}},
        {"id": "c2", "title": "Zoom", "start": "tomorrow 19:00", "end": "tomorrow 20:00"},
    ]}))
    cal = MockCalendar(p, now_fn=lambda: now)
    todays = cal.list_events(now, now + timedelta(hours=24))
    assert [e.id for e in todays] == ["c1"]
    assert [e.id for e in cal.list_events(now, now + timedelta(hours=48))] == ["c1", "c2"]
    slots = cal.free_slots(now, now + timedelta(hours=8), min_minutes=120)
    assert slots[0].start == now + timedelta(hours=1, minutes=30)
    new = cal.insert_event("Night market", now + timedelta(hours=10), now + timedelta(hours=12), "Oakland")
    assert new.id.startswith("mock:")
    assert any(e.id == new.id for e in cal.list_events(now, now + timedelta(hours=24)))
