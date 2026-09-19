from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from headsup.models import Card

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_events (event_id TEXT PRIMARY KEY, seen_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, event_id TEXT NOT NULL, json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS channel_messages (chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL, card_id INTEGER NOT NULL, PRIMARY KEY (chat_id, message_id));
CREATE TABLE IF NOT EXISTS threads (id INTEGER PRIMARY KEY AUTOINCREMENT, card_id INTEGER NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pushes (event_id TEXT NOT NULL, pushed_at TEXT NOT NULL);
"""


class Storage:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def seen(self, event_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM seen_events WHERE event_id=?", (event_id,)).fetchone()
        return row is not None

    def mark_seen(self, event_id: str, at: datetime) -> None:
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO seen_events VALUES (?, ?)", (event_id, at.isoformat()))

    def save_card(self, chat_id: int, card: Card) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO cards (chat_id, event_id, json, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, card.event_id, card.model_dump_json(), datetime.now().isoformat()),
            )
        return int(cur.lastrowid)

    def get_card(self, card_id: int) -> Card | None:
        row = self.conn.execute("SELECT json FROM cards WHERE id=?", (card_id,)).fetchone()
        return Card.model_validate_json(row[0]) if row else None

    def map_message(self, chat_id: int, message_id: int, card_id: int) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO channel_messages VALUES (?, ?, ?)", (chat_id, message_id, card_id))

    def card_for_message(self, chat_id: int, message_id: int) -> tuple[int, Card] | None:
        row = self.conn.execute(
            "SELECT card_id FROM channel_messages WHERE chat_id=? AND message_id=?", (chat_id, message_id)
        ).fetchone()
        if not row:
            return None
        card = self.get_card(int(row[0]))
        return (int(row[0]), card) if card else None

    def latest_card_for_chat(self, chat_id: int) -> tuple[int, Card] | None:
        row = self.conn.execute(
            "SELECT id, json FROM cards WHERE chat_id=? ORDER BY id DESC LIMIT 1", (chat_id,)
        ).fetchone()
        return (int(row[0]), Card.model_validate_json(row[1])) if row else None

    def append_thread(self, card_id: int, role: str, text: str) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO threads (card_id, role, text) VALUES (?, ?, ?)", (card_id, role, text))

    def get_thread(self, card_id: int) -> list[tuple[str, str]]:
        rows = self.conn.execute("SELECT role, text FROM threads WHERE card_id=? ORDER BY id", (card_id,)).fetchall()
        return [(r[0], r[1]) for r in rows]

    def record_push(self, event_id: str, at: datetime) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO pushes VALUES (?, ?)", (event_id, at.isoformat()))

    def pushes_since(self, at: datetime) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM pushes WHERE pushed_at >= ?", (at.isoformat(),)).fetchone()
        return int(row[0])
