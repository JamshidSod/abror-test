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
DISTRACTORS = {
    1: ["wrong-1a", "wrong-1b", "wrong-1c"],
    2: ["wrong-2a", "wrong-2b", "wrong-2c"],
    3: ["wrong-3a", "wrong-3b", "wrong-3c"],
    4: ["wrong-4a", "wrong-4b", "wrong-4c"],
    5: ["wrong-5a", "wrong-5b", "wrong-5c"],
}


def test_builds_four_distinct_options():
    rng = random.Random(0)
    q = QUESTIONS[0]
    quiz = build_quiz(q, DISTRACTORS, rng)
    assert isinstance(quiz, Quiz)
    assert len(quiz.options) == 4
    assert len(set(quiz.options)) == 4
    assert quiz.options[quiz.correct_option_id] == q["answer"]


def test_options_are_exactly_correct_plus_distractors():
    rng = random.Random(0)
    q = QUESTIONS[1]
    quiz = build_quiz(q, DISTRACTORS, rng)
    assert set(quiz.options) == {"A2", "wrong-2a", "wrong-2b", "wrong-2c"}


def test_correct_answer_present_for_all():
    rng = random.Random(7)
    for q in QUESTIONS:
        quiz = build_quiz(q, DISTRACTORS, rng)
        assert q["answer"] in quiz.options


def test_skip_when_no_distractors_entry():
    rng = random.Random(0)
    q = {"id": 99, "page": 1, "question": "Q?", "answer": "A"}
    with pytest.raises(QuizSkip):
        build_quiz(q, DISTRACTORS, rng)


def test_skip_when_distractors_not_three():
    rng = random.Random(0)
    bad = {1: ["only-two", "wrong"]}
    with pytest.raises(QuizSkip):
        build_quiz(QUESTIONS[0], bad, rng)


def test_skip_when_distractor_equals_correct():
    rng = random.Random(0)
    bad = {1: ["A1", "wrong-1b", "wrong-1c"]}
    with pytest.raises(QuizSkip):
        build_quiz(QUESTIONS[0], bad, rng)


def test_skip_when_distractors_not_distinct():
    rng = random.Random(0)
    bad = {1: ["dup", "dup", "wrong-1c"]}
    with pytest.raises(QuizSkip):
        build_quiz(QUESTIONS[0], bad, rng)


def test_skip_when_empty_question():
    rng = random.Random(0)
    q = {"id": 1, "page": 1, "question": "  ", "answer": "A1"}
    with pytest.raises(QuizSkip):
        build_quiz(q, DISTRACTORS, rng)


def test_skip_when_empty_answer():
    rng = random.Random(0)
    q = {"id": 1, "page": 1, "question": "Q?", "answer": ""}
    with pytest.raises(QuizSkip):
        build_quiz(q, DISTRACTORS, rng)


def test_truncates_long_question():
    rng = random.Random(0)
    long_q = {"id": 1, "page": 1, "question": "Q" * 400, "answer": "A1"}
    quiz = build_quiz(long_q, DISTRACTORS, rng)
    assert len(quiz.question_text) <= 300
    assert quiz.question_text.endswith("…")
    assert quiz.truncated is True


def test_truncates_long_option():
    rng = random.Random(0)
    long_correct = {"id": 1, "page": 1, "question": "Q?", "answer": "X" * 150}
    quiz = build_quiz(long_correct, DISTRACTORS, rng)
    correct = quiz.options[quiz.correct_option_id]
    assert len(correct) <= 100
    assert correct.endswith("…")
    assert quiz.truncated is True


def test_disambiguates_truncation_collision():
    rng = random.Random(0)
    # Both correct and one distractor exceed the option cap with the same prefix.
    prefix = "X" * 99
    q = {"id": 1, "page": 1, "question": "Q?", "answer": prefix + "A"}
    distractors = {1: [prefix + "B", "wrong-1b", "wrong-1c"]}
    quiz = build_quiz(q, distractors, rng)
    # After truncation both would have been prefix + "…"; disambiguator replaces
    # the final char of the duplicate with "·".
    assert len(set(quiz.options)) == 4
    assert quiz.options[quiz.correct_option_id].endswith("…") or quiz.options[
        quiz.correct_option_id
    ].endswith("·")
