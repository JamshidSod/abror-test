"""Build a 4-option multiple-choice quiz from one question + its distractors."""
from __future__ import annotations
import random
from dataclasses import dataclass

QUESTION_LIMIT = 300
OPTION_LIMIT = 100


class QuizSkip(Exception):
    """Raised when the question can't be turned into a usable quiz."""


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


def build_quiz(
    q: dict,
    distractors: dict[int, list[str]],
    rng: random.Random,
) -> Quiz:
    qid = q.get("id")
    question_text = q.get("question", "")
    correct = q.get("answer", "")
    if not question_text.strip() or not correct.strip():
        raise QuizSkip(f"empty question or answer for id={qid}")

    ds = distractors.get(qid)
    if not isinstance(ds, list) or len(ds) != 3 or not all(
        isinstance(d, str) and d.strip() for d in ds
    ):
        raise QuizSkip(f"no usable distractors for id={qid}")

    norm = [d.strip().lower() for d in ds]
    if len(set(norm)) != 3:
        raise QuizSkip(f"distractors not distinct for id={qid}")
    if correct.strip().lower() in norm:
        raise QuizSkip(f"distractor matches correct for id={qid}")

    options = list(ds) + [correct]
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
        question_id=qid,
        question_text=q_text,
        options=tuple(truncated_options),
        correct_option_id=correct_option_id,
        truncated=q_trunc or opt_trunc,
    )
