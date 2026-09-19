from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal["traffic", "weather", "outage", "event", "closure", "news"]
ActionKind = Literal["remind", "navigate", "calendar_add", "open_url", "chat"]


class GeoPoint(BaseModel):
    lat: float
    lon: float
    label: str = ""


class LocalEvent(BaseModel):
    id: str
    source: str
    type: EventType
    title: str
    summary: str
    lat: float
    lon: float
    radius_km: float = 5.0
    starts_at: datetime
    ends_at: datetime | None = None
    severity: int = Field(default=3, ge=1, le=5)
    url: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def point(self) -> GeoPoint:
        return GeoPoint(lat=self.lat, lon=self.lon, label=self.title)


class Impact(BaseModel):
    affected: bool
    why: str
    severity: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0, le=1)
    calendar_event_id: str | None = None


class Action(BaseModel):
    id: str
    label: str = Field(max_length=40)
    kind: ActionKind
    payload: dict[str, Any] = Field(default_factory=dict)


class Card(BaseModel):
    event_id: str
    headline: str
    impact: str
    detail: str | None = None
    actions: list[Action] = Field(min_length=1, max_length=3)


class Profile(BaseModel):
    name: str
    home: GeoPoint
    work: GeoPoint | None = None
    school: GeoPoint | None = None
    commute_start: str = "08:30"
    preferences: list[str] = Field(default_factory=list)
    timezone: str = "America/Los_Angeles"
    telegram_chat_id: int | None = None

    def anchors(self) -> list[GeoPoint]:
        return [p for p in (self.home, self.work, self.school) if p is not None]


class CalendarEvent(BaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    location: str | None = None
    geo: GeoPoint | None = None


class FreeSlot(BaseModel):
    start: datetime
    end: datetime


class RouteEta(BaseModel):
    origin: str
    destination: str
    minutes: int
    distance_km: float
    summary: str = ""


class Place(BaseModel):
    name: str
    address: str
    lat: float
    lon: float
    open_now: bool | None = None
    rating: float | None = None
    maps_url: str
