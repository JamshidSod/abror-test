# tests/test_distractors_next_batch.py
import json
import pytest
from pathlib import Path

from scripts.distractors_next_batch import (
    load_questions,
    load_distractors,
    find_page_location,
    validate,
    missing_ids,
    build_batch,
)


QUESTIONS = [
    {"id": 1, "page": 1, "question": "Q1?", "answer": "A1"},
    {"id": 2, "page": 1, "question": "Q2?", "answer": "A2"},
    {"id": 3, "page": 2, "question": "Q3?", "answer": "A3"},
]


def _write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def workspace(tmp_path):
    qpath = tmp_path / "questions.json"
    _write(qpath, QUESTIONS)
    pages = tmp_path / "pages_json"
    pages.mkdir()
    _write(pages / "p001.json", [
        {"n": 1, "question": "Q1?", "answer": "A1"},
        {"n": 2, "question": "Q2?", "answer": "A2"},
    ])
    _write(pages / "p002.json", [
        {"n": 3, "question": "Q3?", "answer": "A3"},
    ])
    return tmp_path


def test_load_distractors_missing_file_returns_empty(workspace):
    assert load_distractors(workspace / "missing.json") == {}


def test_load_distractors_parses_int_keys(workspace):
    p = workspace / "distractors.json"
    _write(p, {"1": ["a", "b", "c"]})
    assert load_distractors(p) == {1: ["a", "b", "c"]}


def test_validate_passes_on_well_formed(workspace):
    assert validate({1: ["x", "y", "z"]}, QUESTIONS) == []


def test_validate_rejects_wrong_list_length(workspace):
    errs = validate({1: ["only-two", "wrong"]}, QUESTIONS)
    assert errs and "id 1" in errs[0]


def test_validate_rejects_non_distinct(workspace):
    errs = validate({1: ["x", "x", "y"]}, QUESTIONS)
    assert errs and "distinct" in errs[0].lower()


def test_validate_rejects_distractor_equal_to_correct(workspace):
    errs = validate({1: ["A1", "x", "y"]}, QUESTIONS)
    assert errs and "matches correct" in errs[0].lower()


def test_validate_rejects_unknown_id(workspace):
    errs = validate({999: ["a", "b", "c"]}, QUESTIONS)
    assert errs and "999" in errs[0]


def test_missing_ids_returns_uncovered_in_order(workspace):
    assert missing_ids({2: ["a", "b", "c"]}, QUESTIONS, limit=10) == [1, 3]


def test_missing_ids_respects_limit(workspace):
    assert missing_ids({}, QUESTIONS, limit=2) == [1, 2]


def test_missing_ids_empty_when_all_covered(workspace):
    distractors = {q["id"]: ["a", "b", "c"] for q in QUESTIONS}
    assert missing_ids(distractors, QUESTIONS, limit=10) == []


def test_find_page_location(workspace):
    loc = find_page_location(3, workspace / "pages_json")
    assert loc is not None
    path, idx = loc
    assert path.name == "p002.json"
    assert idx == 0


def test_find_page_location_returns_none_when_absent(workspace):
    assert find_page_location(999, workspace / "pages_json") is None


def test_build_batch_attaches_page_info(workspace):
    batch = build_batch([1, 3], workspace / "pages_json", QUESTIONS)
    assert len(batch) == 2
    assert batch[0]["id"] == 1
    assert batch[0]["page"] == 1
    assert batch[0]["page_file"].endswith("p001.json")
    assert batch[0]["page_index"] == 0
    assert batch[0]["question"] == "Q1?"
    assert batch[0]["answer"] == "A1"
    assert batch[1]["id"] == 3
    assert batch[1]["page_file"].endswith("p002.json")
    assert batch[1]["page_index"] == 0
