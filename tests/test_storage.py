from datetime import timedelta

from headsup.models import Action, Card
from headsup.storage import Storage


def card(event_id="e1"):
    return Card(event_id=event_id, headline="H", impact="I", actions=[Action(id="a1", label="Go", kind="open_url", payload={"url": "https://x"})])


def test_seen_roundtrip(tmp_path, now):
    s = Storage(tmp_path / "t.db")
    assert not s.seen("e1")
    s.mark_seen("e1", now)
    assert s.seen("e1")


def test_cards_and_message_map(tmp_path, now):
    s = Storage(tmp_path / "t.db")
    cid = s.save_card(42, card())
    assert s.get_card(cid) == card()
    s.map_message(42, 777, cid)
    assert s.card_for_message(42, 777) == (cid, card())
    assert s.latest_card_for_chat(42) == (cid, card())
    cid2 = s.save_card(42, card("e2"))
    assert s.latest_card_for_chat(42)[0] == cid2


def test_thread_and_push_log(tmp_path, now):
    s = Storage(tmp_path / "t.db")
    cid = s.save_card(1, card())
    s.append_thread(cid, "user", "what if 880?")
    s.append_thread(cid, "assistant", "880 adds 5 min")
    assert s.get_thread(cid) == [("user", "what if 880?"), ("assistant", "880 adds 5 min")]
    s.record_push("e1", now)
    s.record_push("e2", now - timedelta(hours=2))
    assert s.pushes_since(now - timedelta(hours=1)) == 1
