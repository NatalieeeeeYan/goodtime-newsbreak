from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str | None
    deepseek_model: str
    telegram_bot_token: str | None
    google_maps_api_key: str | None
    bay511_token: str | None
    ticketmaster_key: str | None
    google_oauth_client_json: Path
    demo_mode: bool
    push_rate_cap: int
    poll_interval_minutes: int
    db_path: Path
    integrations_path: Path
    profile_path: Path
    calendar_mock_path: Path
    scenarios_dir: Path
    demo_allowed_sources: frozenset[str]


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        load_dotenv(ROOT / ".env")
        env = os.environ
    return Settings(
        deepseek_api_key=env.get("DEEPSEEK_API_KEY") or None,
        deepseek_model=env.get("DEEPSEEK_MODEL", "deepseek-chat"),
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN") or None,
        google_maps_api_key=env.get("GOOGLE_MAPS_API_KEY") or None,
        bay511_token=env.get("BAY511_TOKEN") or None,
        ticketmaster_key=env.get("TICKETMASTER_KEY") or None,
        google_oauth_client_json=ROOT / env.get("GOOGLE_OAUTH_CLIENT_JSON", "credentials.json"),
        demo_mode=env.get("DEMO_MODE", "1") == "1",
        push_rate_cap=int(env.get("PUSH_RATE_CAP", "3")),
        poll_interval_minutes=int(env.get("POLL_INTERVAL_MINUTES", "5")),
        db_path=ROOT / env.get("DB_PATH", "headsup.db"),
        integrations_path=ROOT / "integrations.yaml",
        profile_path=ROOT / "profile.json",
        calendar_mock_path=ROOT / "calendar.mock.json",
        scenarios_dir=ROOT / "scenarios",
        demo_allowed_sources=frozenset({"nws", "inject"}),
    )


def load_integrations_config(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text()) or {}
    return {str(k): str(v) for k, v in data.items()}
