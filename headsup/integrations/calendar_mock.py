from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from headsup.models import CalendarEvent, FreeSlot, GeoPoint
from headsup.timeutil import compute_free_slots, parse_relative, utcnow


class MockCalendar:
    def __init__(self, path: Path, now_fn: Callable[[], datetime] = utcnow):
        self.path = path
        self.now_fn = now_fn
        self.inserted: list[CalendarEvent] = []

    def _load(self) -> list[CalendarEvent]:
        now = self.now_fn()
        raw = json.loads(self.path.read_text()).get("events", [])
        events = [
            CalendarEvent(
                id=r["id"], title=r["title"],
                start=parse_relative(r["start"], now), end=parse_relative(r["end"], now),
                location=r.get("location"), geo=GeoPoint(**r["geo"]) if r.get("geo") else None,
            )
            for r in raw
        ]
        return sorted(events + self.inserted, key=lambda e: e.start)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [e for e in self._load() if e.end >= start and e.start <= end]

    def free_slots(self, start: datetime, end: datetime, min_minutes: int) -> list[FreeSlot]:
        return compute_free_slots(self.list_events(start, end), start, end, min_minutes)

    def insert_event(self, title: str, start: datetime, end: datetime, location: str | None = None) -> CalendarEvent:
        ev = CalendarEvent(id=f"mock:{uuid4().hex[:8]}", title=title, start=start, end=end, location=location)
        self.inserted.append(ev)
        return ev
