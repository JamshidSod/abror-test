# tests/test_handlers_loaders.py
"""Tests for bot.handlers.load_distractors (and its sibling load_questions)."""
import json
import pytest
from pathlib import Path

from bot.handlers import load_distractors, load_questions


def _write(path: Path, raw_text: str) -> None:
    path.write_text(raw_text, encoding="utf-8")


# ----- load_distractors -----


def test_load_distractors_happy_path(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"1": ["a", "b", "c"], "42": ["x", "y", "z"]}))
    assert load_distractors(str(p)) == {1: ["a", "b", "c"], 42: ["x", "y", "z"]}


def test_load_distractors_accepts_empty_object(tmp_path):
    p = tmp_path / "d.json"
    _write(p, "{}")
    assert load_distractors(str(p)) == {}


def test_load_distractors_raises_on_non_dict(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps([1, 2, 3]))
    with pytest.raises(RuntimeError, match="expected a JSON object"):
        load_distractors(str(p))


def test_load_distractors_raises_on_non_integer_key(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"abc": ["a", "b", "c"]}))
    with pytest.raises(RuntimeError, match="non-integer key"):
        load_distractors(str(p))


def test_load_distractors_raises_when_value_not_list(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"1": "not-a-list"}))
    with pytest.raises(RuntimeError, match="must be a list of 3 non-empty strings"):
        load_distractors(str(p))


def test_load_distractors_raises_when_list_wrong_length(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"1": ["a", "b"]}))
    with pytest.raises(RuntimeError, match="must be a list of 3 non-empty strings"):
        load_distractors(str(p))


def test_load_distractors_raises_on_non_string_element(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"1": ["a", 42, "c"]}))
    with pytest.raises(RuntimeError, match="must be a list of 3 non-empty strings"):
        load_distractors(str(p))


def test_load_distractors_raises_on_whitespace_only_string(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"1": ["a", "   ", "c"]}))
    with pytest.raises(RuntimeError, match="must be a list of 3 non-empty strings"):
        load_distractors(str(p))


def test_load_distractors_raises_on_empty_string(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps({"1": ["a", "", "c"]}))
    with pytest.raises(RuntimeError, match="must be a list of 3 non-empty strings"):
        load_distractors(str(p))


def test_load_distractors_error_includes_path(tmp_path):
    p = tmp_path / "d.json"
    _write(p, json.dumps([]))
    with pytest.raises(RuntimeError, match=str(p)):
        load_distractors(str(p))


# ----- load_questions (existing function — small sanity check now that we're here) -----


def test_load_questions_happy_path(tmp_path):
    p = tmp_path / "q.json"
    rows = [{"id": 1, "question": "Q?", "answer": "A"}]
    _write(p, json.dumps(rows))
    assert load_questions(str(p)) == rows


def test_load_questions_raises_on_non_list(tmp_path):
    p = tmp_path / "q.json"
    _write(p, json.dumps({"id": 1}))
    with pytest.raises(RuntimeError, match="expected a JSON list"):
        load_questions(str(p))
