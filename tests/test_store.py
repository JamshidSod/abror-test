# tests/test_store.py
import random
import pytest
from bot.store import Store, LastQuiz

QS = [{"id": i, "page": 1, "question": f"Q{i}?", "answer": f"A{i}"} for i in range(1, 11)]


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "test.sqlite"), recent_history=3)
    yield s
    s.close()


def test_get_or_create_returns_zero_counts(store):
    u = store.get_or_create(42)
    assert u.correct == 0
    assert u.total == 0
    assert u.active is False


def test_record_answer_increments(store):
    store.get_or_create(1)
    store.record_answer(1, True)
    store.record_answer(1, False)
    store.record_answer(1, True)
    u = store.get_or_create(1)
    assert u.total == 3
    assert u.correct == 2


def test_set_active(store):
    store.get_or_create(1)
    store.set_active(1, True)
    assert store.get_or_create(1).active is True
    store.set_active(1, False)
    assert store.get_or_create(1).active is False


def test_pick_next_avoids_recent(store):
    rng = random.Random(0)
    store.get_or_create(1)
    seen: list[int] = []
    for _ in range(3):
        q = store.pick_next_question(1, QS, rng)
        seen.append(q["id"])
    nxt = store.pick_next_question(1, QS, rng)
    assert nxt["id"] not in seen


def test_recent_evicts_fifo(store):
    rng = random.Random(0)
    store.get_or_create(1)
    for _ in range(5):
        store.pick_next_question(1, QS, rng)
    with store._conn:
        rows = list(store._conn.execute(
            "SELECT qid FROM recent WHERE uid = ?", (1,)
        ))
    assert len(rows) <= 3


def test_last_quiz_roundtrip(store):
    store.get_or_create(1)
    lq = LastQuiz(question_id=5, poll_id="poll-abc", correct_option_id=2, truncated=False)
    store.set_last_quiz(1, lq)
    got = store.get_last_quiz(1)
    assert got == lq


def test_get_last_quiz_returns_none_when_missing(store):
    store.get_or_create(1)
    assert store.get_last_quiz(1) is None


def test_persists_across_instances(tmp_path):
    db = str(tmp_path / "p.sqlite")
    a = Store(db, recent_history=10)
    a.get_or_create(99)
    a.record_answer(99, True)
    a.close()
    b = Store(db, recent_history=10)
    u = b.get_or_create(99)
    assert u.correct == 1
    assert u.total == 1
    b.close()
