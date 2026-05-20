"""SQLite-backed per-user state for the bot."""
from __future__ import annotations
import random
import sqlite3
import time
from dataclasses import dataclass
from typing import Sequence


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  uid     INTEGER PRIMARY KEY,
  correct INTEGER NOT NULL DEFAULT 0,
  total   INTEGER NOT NULL DEFAULT 0,
  active  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS recent (
  uid     INTEGER NOT NULL,
  qid     INTEGER NOT NULL,
  seen_at INTEGER NOT NULL,
  PRIMARY KEY (uid, qid)
);
CREATE INDEX IF NOT EXISTS recent_uid_seen ON recent(uid, seen_at);
CREATE TABLE IF NOT EXISTS last_quiz (
  uid               INTEGER PRIMARY KEY,
  qid               INTEGER NOT NULL,
  poll_id           TEXT    NOT NULL,
  correct_option_id INTEGER NOT NULL,
  truncated         INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass(frozen=True)
class UserSnapshot:
    uid: int
    correct: int
    total: int
    active: bool


@dataclass(frozen=True)
class LastQuiz:
    question_id: int
    poll_id: str
    correct_option_id: int
    truncated: bool


class Store:
    def __init__(self, db_path: str, recent_history: int = 30) -> None:
        self.db_path = db_path
        self.recent_history = recent_history
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get_or_create(self, uid: int) -> UserSnapshot:
        cur = self._conn.execute(
            "SELECT correct, total, active FROM users WHERE uid = ?", (uid,)
        )
        row = cur.fetchone()
        if row is None:
            with self._conn:
                self._conn.execute("INSERT INTO users(uid) VALUES (?)", (uid,))
            return UserSnapshot(uid=uid, correct=0, total=0, active=False)
        correct, total, active = row
        return UserSnapshot(uid=uid, correct=correct, total=total, active=bool(active))

    def set_active(self, uid: int, active: bool) -> None:
        self.get_or_create(uid)
        with self._conn:
            self._conn.execute(
                "UPDATE users SET active = ? WHERE uid = ?",
                (1 if active else 0, uid),
            )

    def record_answer(self, uid: int, was_correct: bool) -> None:
        self.get_or_create(uid)
        with self._conn:
            self._conn.execute(
                "UPDATE users SET total = total + 1, correct = correct + ? WHERE uid = ?",
                (1 if was_correct else 0, uid),
            )

    def pick_next_question(
        self, uid: int, all_questions: Sequence[dict], rng: random.Random
    ) -> dict:
        recent_ids = {
            row[0]
            for row in self._conn.execute(
                "SELECT qid FROM recent WHERE uid = ? ORDER BY seen_at DESC LIMIT ?",
                (uid, self.recent_history),
            )
        }
        candidates = [q for q in all_questions if q["id"] not in recent_ids]
        if not candidates:
            with self._conn:
                self._conn.execute(
                    """
                    DELETE FROM recent
                    WHERE uid = ? AND qid IN (
                        SELECT qid FROM recent WHERE uid = ?
                        ORDER BY seen_at ASC LIMIT ?
                    )
                    """,
                    (uid, uid, self.recent_history // 2),
                )
            candidates = list(all_questions)
        chosen = rng.choice(candidates)
        now = int(time.time())
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO recent(uid, qid, seen_at) VALUES (?, ?, ?)",
                (uid, chosen["id"], now),
            )
            self._conn.execute(
                """
                DELETE FROM recent
                WHERE uid = ? AND qid NOT IN (
                    SELECT qid FROM recent WHERE uid = ?
                    ORDER BY seen_at DESC LIMIT ?
                )
                """,
                (uid, uid, self.recent_history),
            )
        return chosen

    def set_last_quiz(self, uid: int, lq: LastQuiz) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO last_quiz(uid, qid, poll_id, correct_option_id, truncated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uid, lq.question_id, lq.poll_id, lq.correct_option_id, 1 if lq.truncated else 0),
            )

    def get_last_quiz(self, uid: int) -> LastQuiz | None:
        cur = self._conn.execute(
            "SELECT qid, poll_id, correct_option_id, truncated FROM last_quiz WHERE uid = ?",
            (uid,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        qid, poll_id, coid, trunc = row
        return LastQuiz(
            question_id=qid, poll_id=poll_id, correct_option_id=coid, truncated=bool(trunc)
        )

    def find_user_by_poll(self, poll_id: str) -> int | None:
        cur = self._conn.execute(
            "SELECT uid FROM last_quiz WHERE poll_id = ?", (poll_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None
