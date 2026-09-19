from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from headsup.models import CalendarEvent, FreeSlot

_OFFSET = re.compile(r"^([+-])((?:\d+[mhd])+)$")
_PART = re.compile(r"(\d+)([mhd])")
_DAY_TIME = re.compile(r"^(today|tomorrow)\s+(\d{1,2}):(\d{2})$")
_UNIT = {"m": "minutes", "h": "hours", "d": "days"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_relative(value: str | datetime, now: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    text = value.strip()
    if m := _OFFSET.match(text):
        sign, body = m.groups()
        delta = sum((timedelta(**{_UNIT[u]: int(n)}) for n, u in _PART.findall(body)), timedelta())
        return now + delta if sign == "+" else now - delta
    if m := _DAY_TIME.match(text):
        day, hh, mm = m.groups()
        base = now + timedelta(days=1) if day == "tomorrow" else now
        return base.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def compute_free_slots(
    events: list[CalendarEvent], start: datetime, end: datetime, min_minutes: int
) -> list[FreeSlot]:
    cursor = start
    slots: list[FreeSlot] = []
    for ev in sorted(events, key=lambda e: e.start):
        if ev.start > cursor and (ev.start - cursor) >= timedelta(minutes=min_minutes):
            slots.append(FreeSlot(start=cursor, end=min(ev.start, end)))
        cursor = max(cursor, ev.end)
        if cursor >= end:
            break
    if cursor < end and (end - cursor) >= timedelta(minutes=min_minutes):
        slots.append(FreeSlot(start=cursor, end=end))
    return slots
