from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from headsup.config import Settings
from headsup.integrations.protocols import Booking, Calendar, Channel, Maps, ProfileStore, Reminders


@dataclass
class Integrations:
    channel: Channel
    calendar: Calendar
    maps: Maps
    reminders: Reminders
    booking: Booking
    profile: ProfileStore


def _profile(name: str, settings: Settings, ctx: dict[str, Any]) -> ProfileStore:
    if name == "json":
        from headsup.integrations.profile_json import JsonProfileStore
        return JsonProfileStore(settings.profile_path)
    raise ValueError(f"unknown profile provider {name}")


def _calendar(name: str, settings: Settings, ctx: dict[str, Any]) -> Calendar:
    if name == "mock":
        from headsup.integrations.calendar_mock import MockCalendar
        return MockCalendar(settings.calendar_mock_path)
    if name == "google":
        from headsup.integrations.calendar_google import GoogleCalendar
        return GoogleCalendar(settings.google_oauth_client_json)
    raise ValueError(f"unknown calendar provider {name}")


def _maps(name: str, settings: Settings, ctx: dict[str, Any]) -> Maps:
    if name == "google":
        from headsup.integrations.maps_google import GoogleMaps
        return GoogleMaps(settings.google_maps_api_key or "")
    raise ValueError(f"unknown maps provider {name}")


def _channel(name: str, settings: Settings, ctx: dict[str, Any]) -> Channel:
    if name == "telegram":
        from headsup.integrations.channel_telegram import TelegramChannel
        return TelegramChannel(settings.telegram_bot_token or "", ctx["storage"])
    raise ValueError(f"unknown channel provider {name}")


def _reminders(name: str, settings: Settings, ctx: dict[str, Any]) -> Reminders:
    if name == "scheduler":
        from headsup.integrations.reminders_scheduler import SchedulerReminders
        return SchedulerReminders(ctx["scheduler"], ctx["channel"])
    raise ValueError(f"unknown reminders provider {name}")


def _booking(name: str, settings: Settings, ctx: dict[str, Any]) -> Booking:
    if name == "open_url":
        from headsup.integrations.booking_openurl import OpenUrlBooking
        return OpenUrlBooking()
    raise ValueError(f"unknown booking provider {name}")


def load_integrations(config: dict[str, str], settings: Settings, scheduler: Any, storage: Any) -> Integrations:
    ctx: dict[str, Any] = {"scheduler": scheduler, "storage": storage}
    channel = _channel(config["channel"], settings, ctx)
    ctx["channel"] = channel
    return Integrations(
        channel=channel,
        calendar=_calendar(config["calendar"], settings, ctx),
        maps=_maps(config["maps"], settings, ctx),
        reminders=_reminders(config["reminders"], settings, ctx),
        booking=_booking(config["booking"], settings, ctx),
        profile=_profile(config["profile"], settings, ctx),
    )
