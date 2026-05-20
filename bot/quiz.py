"""Build a 4-option multiple-choice quiz from one question."""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Sequence

QUESTION_LIMIT = 300
OPTION_LIMIT = 100


class QuizSkip(Exception):
    """Raised when the question is unsuitable (empty fields)."""


@dataclass(frozen=True)
class Quiz:
    question_id: int
    question_text: str
    options: tuple[str, str, str, str]
    correct_option_id: int
    truncated: bool


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[: limit - 1] + "…", True


def build_quiz(q: dict, all_questions: Sequence[dict], rng: random.Random) -> Quiz:
    question_text = q.get("question", "")
    correct = q.get("answer", "")
    if not question_text.strip() or not correct.strip():
        raise QuizSkip(f"empty question or answer for id={q.get('id')}")

    # Build the wrong-answer pool: other questions, non-empty, not equal to correct.
    seen: set[str] = {correct}
    raw_pool: list[str] = []
    for r in all_questions:
        if r is q:
            continue
        a = r.get("answer", "").strip()
        if not a or a in seen:
            continue
        seen.add(a)
        raw_pool.append(a)

    # Prefer length-similar answers.
    lo = 0.6 * len(correct)
    hi = 1.6 * len(correct)
    filtered = [a for a in raw_pool if lo <= len(a) <= hi]
    pool = filtered if len(filtered) >= 3 else raw_pool

    if len(pool) < 3:
        raise QuizSkip(f"insufficient distinct wrong-answer pool for id={q.get('id')}")

    wrong = rng.sample(pool, 3)
    options = wrong + [correct]
    rng.shuffle(options)
    correct_option_id = options.index(correct)

    # Truncate to Telegram caps.
    q_text, q_trunc = _truncate(question_text, QUESTION_LIMIT)
    truncated_options: list[str] = []
    opt_trunc = False
    for opt in options:
        t, was_trunc = _truncate(opt, OPTION_LIMIT)
        truncated_options.append(t)
        opt_trunc = opt_trunc or was_trunc

    # If truncation made the correct option collide with a wrong one, disambiguate.
    seen_opts: dict[str, int] = {}
    for i, t in enumerate(truncated_options):
        if t in seen_opts:
            truncated_options[i] = t[:-1] + "·"
        seen_opts[t] = i

    new_correct = truncated_options[correct_option_id]
    correct_option_id = truncated_options.index(new_correct)

    return Quiz(
        question_id=q["id"],
        question_text=q_text,
        options=tuple(truncated_options),
        correct_option_id=correct_option_id,
        truncated=q_trunc or opt_trunc,
    )
