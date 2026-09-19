from pathlib import Path

from headsup.config import load_integrations_config, load_settings


def test_load_settings_reads_env_and_defaults():
    s = load_settings({"DEEPSEEK_API_KEY": "k", "DEMO_MODE": "0"})
    assert s.deepseek_api_key == "k"
    assert s.demo_mode is False
    assert s.push_rate_cap == 3
    assert s.deepseek_model == "deepseek-chat"


def test_load_integrations_config(tmp_path: Path):
    p = tmp_path / "integrations.yaml"
    p.write_text("channel: telegram\ncalendar: mock\n")
    assert load_integrations_config(p) == {"channel": "telegram", "calendar": "mock"}
