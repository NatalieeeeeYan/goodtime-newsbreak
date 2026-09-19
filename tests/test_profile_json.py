import json

from headsup.integrations.profile_json import JsonProfileStore


def test_profile_store_get_and_update(tmp_path):
    p = tmp_path / "profile.json"
    p.write_text(json.dumps({"name": "Nat", "home": {"lat": 37.8, "lon": -122.27, "label": "home"}}))
    store = JsonProfileStore(p)
    assert store.get().name == "Nat"
    updated = store.update({"telegram_chat_id": 123})
    assert updated.telegram_chat_id == 123
    assert JsonProfileStore(p).get().telegram_chat_id == 123
