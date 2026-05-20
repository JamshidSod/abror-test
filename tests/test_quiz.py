# tests/test_quiz.py
import random
import pytest
from bot.quiz import build_quiz, Quiz, QuizSkip

QUESTIONS = [
    {"id": 1, "page": 1, "question": "Q1?", "answer": "A1"},
    {"id": 2, "page": 1, "question": "Q2?", "answer": "A2"},
    {"id": 3, "page": 1, "question": "Q3?", "answer": "A3"},
    {"id": 4, "page": 1, "question": "Q4?", "answer": "A4"},
    {"id": 5, "page": 1, "question": "Q5?", "answer": "A5"},
]


def test_builds_four_distinct_options():
    rng = random.Random(0)
    q = QUESTIONS[0]
    quiz = build_quiz(q, QUESTIONS, rng)
    assert isinstance(quiz, Quiz)
    assert len(quiz.options) == 4
    assert len(set(quiz.options)) == 4
    assert quiz.options[quiz.correct_option_id] == q["answer"]


def test_correct_answer_present():
    rng = random.Random(7)
    for q in QUESTIONS:
        quiz = build_quiz(q, QUESTIONS, rng)
        assert q["answer"] in quiz.options


def test_truncates_long_question():
    rng = random.Random(0)
    long_q = {"id": 99, "page": 1, "question": "Q" * 400, "answer": "A"}
    pool = QUESTIONS + [long_q]
    quiz = build_quiz(long_q, pool, rng)
    assert len(quiz.question_text) <= 300
    assert quiz.question_text.endswith("…")
    assert quiz.truncated is True


def test_truncates_long_option():
    rng = random.Random(0)
    long_a = {"id": 99, "page": 1, "question": "Q?", "answer": "X" * 150}
    pool = QUESTIONS + [long_a]
    quiz = build_quiz(long_a, pool, rng)
    correct = quiz.options[quiz.correct_option_id]
    assert len(correct) <= 100
    assert correct.endswith("…")
    assert quiz.truncated is True


def test_skips_empty_question():
    rng = random.Random(0)
    empty = {"id": 99, "page": 1, "question": "  ", "answer": "A"}
    with pytest.raises(QuizSkip):
        build_quiz(empty, QUESTIONS + [empty], rng)


def test_skips_empty_answer():
    rng = random.Random(0)
    empty = {"id": 99, "page": 1, "question": "Q?", "answer": ""}
    with pytest.raises(QuizSkip):
        build_quiz(empty, QUESTIONS + [empty], rng)


def test_dedups_duplicate_correct_answers():
    rng = random.Random(0)
    pool = [
        {"id": 1, "page": 1, "question": "Q1?", "answer": "SAME"},
        {"id": 2, "page": 1, "question": "Q2?", "answer": "SAME"},
        {"id": 3, "page": 1, "question": "Q3?", "answer": "X"},
        {"id": 4, "page": 1, "question": "Q4?", "answer": "Y"},
        {"id": 5, "page": 1, "question": "Q5?", "answer": "Z"},
    ]
    quiz = build_quiz(pool[0], pool, rng)
    assert quiz.options.count("SAME") == 1


def test_falls_back_when_length_filter_too_strict():
    rng = random.Random(0)
    pool = [
        {"id": 1, "page": 1, "question": "Q1?", "answer": "X"},
        {"id": 2, "page": 1, "question": "Q2?", "answer": "a" * 200},
        {"id": 3, "page": 1, "question": "Q3?", "answer": "b" * 200},
        {"id": 4, "page": 1, "question": "Q4?", "answer": "c" * 200},
    ]
    quiz = build_quiz(pool[0], pool, rng)
    assert len(quiz.options) == 4
