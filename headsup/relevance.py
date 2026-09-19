from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from headsup.geo import distance_to_segment_km, haversine_km
from headsup.models import CalendarEvent, FreeSlot, LocalEvent, Profile

LOOKAHEAD = timedelta(hours=24)
DEFAULT_DURATION = timedelta(hours=6)
CALENDAR_PAD = timedelta(hours=2)
CORRIDOR_MIN_KM = 2.0
FREE_SLOT_MIN = timedelta(hours=2)


@dataclass
class Candidate:
    event: LocalEvent
    matched_events: list[CalendarEvent] = field(default_factory=list)
    free_slots: list[FreeSlot] = field(default_factory=list)
    reason: str = ""


def _window(event: LocalEvent) -> tuple[datetime, datetime]:
    return event.starts_at, event.ends_at or event.starts_at + DEFAULT_DURATION


def _in_time(event: LocalEvent, now: datetime) -> bool:
    start, end = _window(event)
    return start <= now + LOOKAHEAD and end >= now


def _geo_reason(event: LocalEvent, profile: Profile, calendar_events: list[CalendarEvent]) -> str | None:
    p = event.point
    for anchor in profile.anchors():
        if haversine_km(p, anchor) <= event.radius_km:
            return f"within {event.radius_km:.0f} km of {anchor.label or 'anchor'}"
    for ce in calendar_events:
        if ce.geo and haversine_km(p, ce.geo) <= event.radius_km:
            return f"near calendar event '{ce.title}'"
    if event.type == "traffic":
        width = max(event.radius_km, CORRIDOR_MIN_KM)
        for dest in (profile.work, profile.school):
            if dest and distance_to_segment_km(p, profile.home, dest) <= width:
                return f"on commute corridor home→{dest.label or 'destination'}"
    return None


def _matched(event: LocalEvent, calendar_events: list[CalendarEvent]) -> list[CalendarEvent]:
    start, end = _window(event)
    return [ce for ce in calendar_events if ce.end >= start - CALENDAR_PAD and ce.start <= end + CALENDAR_PAD]


def _overlapping_slots(event: LocalEvent, free_slots: list[FreeSlot]) -> list[FreeSlot]:
    start, end = _window(event)
    out = []
    for s in free_slots:
        lo, hi = max(s.start, start), min(s.end, end)
        if hi - lo >= FREE_SLOT_MIN:
            out.append(s)
    return out


def prefilter(
    event: LocalEvent,
    profile: Profile,
    calendar_events: list[CalendarEvent],
    free_slots: list[FreeSlot],
    now: datetime,
) -> Candidate | None:
    if not _in_time(event, now):
        return None
    reason = _geo_reason(event, profile, calendar_events)
    if reason is None:
        return None
    slots = _overlapping_slots(event, free_slots)
    if event.type == "event" and not slots:
        return None
    return Candidate(event=event, matched_events=_matched(event, calendar_events), free_slots=slots, reason=reason)
