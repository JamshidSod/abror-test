"""Telegram update handlers."""
from __future__ import annotations
import json
import logging
import random
from typing import Sequence

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

from .quiz import build_quiz, Quiz, QuizSkip
from .store import LastQuiz, Store

log = logging.getLogger(__name__)

HELP_TEXT = (
    "Commands:\n"
    "/start  – begin or resume the quiz stream\n"
    "/stop   – pause the stream\n"
    "/score  – your lifetime tally\n"
    "/full   – show the last quiz's complete question and answer\n"
    "/help   – this message"
)

# Sent on every bot response to clear any persistent reply keyboard a user
# might still have from an earlier release. Harmless once the keyboard is gone.
HIDE_KEYBOARD = ReplyKeyboardRemove()


def load_questions(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise RuntimeError(f"{path}: expected a JSON list")
    return data


def load_distractors(path: str) -> dict[int, list[str]]:
    """Read the sidecar; convert string keys to int. Raise on malformed input."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise RuntimeError(f"{path}: expected a JSON object")
    out: dict[int, list[str]] = {}
    for k, v in raw.items():
        try:
            kid = int(k)
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"{path}: non-integer key {k!r}") from e
        if not isinstance(v, list) or len(v) != 3 or not all(
            isinstance(x, str) and x.strip() for x in v
        ):
            raise RuntimeError(
                f"{path}: entry for id {kid} must be a list of 3 non-empty strings"
            )
        out[kid] = v
    return out


async def _send_next_quiz(
    chat_id: int,
    uid: int,
    context: ContextTypes.DEFAULT_TYPE,
    store: Store,
    questions: Sequence[dict],
    distractors: dict[int, list[str]],
    rng: random.Random,
    poll_open_seconds: int,
) -> None:
    """Pick a non-recent question, build a quiz, send the poll, persist last_quiz."""
    for _ in range(5):  # at most 5 skip attempts
        q = store.pick_next_question(uid, questions, rng)
        try:
            quiz = build_quiz(q, distractors, rng)
        except QuizSkip:
            continue
        msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=quiz.question_text,
            options=list(quiz.options),
            type="quiz",
            correct_option_id=quiz.correct_option_id,
            is_anonymous=False,
            open_period=poll_open_seconds,
        )
        poll_id = msg.poll.id
        store.set_last_quiz(
            uid,
            LastQuiz(
                question_id=quiz.question_id,
                poll_id=poll_id,
                correct_option_id=quiz.correct_option_id,
                truncated=quiz.truncated,
            ),
        )
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text="No answerable questions found right now. Try /start again later.",
    )


def register_handlers(
    app: Application,
    questions: Sequence[dict],
    distractors: dict[int, list[str]],
    store: Store,
    rng: random.Random,
    poll_open_seconds: int,
) -> None:
    """Wire all commands and the poll_answer handler into the PTB Application."""

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        store.get_or_create(user.id)
        store.set_active(user.id, True)
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "Salom! I'll send you a random multiple-choice question. "
                "Answer the poll and I'll send the next one.\n"
                "/stop to pause, /score for your tally, /help for commands."
            ),
            reply_markup=HIDE_KEYBOARD,
        )
        await _send_next_quiz(
            chat.id, user.id, context, store, questions, distractors, rng, poll_open_seconds
        )

    async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        store.set_active(user.id, False)
        await context.bot.send_message(
            chat_id=chat.id,
            text="Paused. /start to resume.",
            reply_markup=HIDE_KEYBOARD,
        )

    async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        u = store.get_or_create(user.id)
        if u.total == 0:
            text = "No answers yet. /start to begin."
        else:
            pct = round(100 * u.correct / u.total)
            text = f"Lifetime: {u.correct}/{u.total} correct ({pct}%)."
        await context.bot.send_message(
            chat_id=chat.id, text=text, reply_markup=HIDE_KEYBOARD
        )

    async def full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        lq = store.get_last_quiz(user.id)
        if lq is None:
            await context.bot.send_message(
                chat_id=chat.id,
                text="No quiz yet. /start to begin.",
                reply_markup=HIDE_KEYBOARD,
            )
            return
        q = next((q for q in questions if q["id"] == lq.question_id), None)
        if q is None:
            await context.bot.send_message(
                chat_id=chat.id,
                text="Question not found.",
                reply_markup=HIDE_KEYBOARD,
            )
            return
        text = (
            f"Q{q['id']} (page {q['page']}):\n\n"
            f"{q['question']}\n\n"
            f"Canonical answer:\n{q['answer']}"
        )
        await context.bot.send_message(
            chat_id=chat.id, text=text, reply_markup=HIDE_KEYBOARD
        )

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if chat:
            await context.bot.send_message(
                chat_id=chat.id, text=HELP_TEXT, reply_markup=HIDE_KEYBOARD
            )

    async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ans = update.poll_answer
        if ans is None or ans.user is None:
            return
        uid = ans.user.id
        lq = store.get_last_quiz(uid)
        if lq is None or lq.poll_id != ans.poll_id:
            return
        chosen = ans.option_ids[0] if ans.option_ids else -1
        was_correct = chosen == lq.correct_option_id
        store.record_answer(uid, was_correct)
        if not store.get_or_create(uid).active:
            return
        await _send_next_quiz(
            uid, uid, context, store, questions, distractors, rng, poll_open_seconds
        )

    async def stray(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if chat:
            await context.bot.send_message(
                chat_id=chat.id,
                text="Tap an answer on the poll, or use /help.",
                reply_markup=HIDE_KEYBOARD,
            )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("full", full))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(PollAnswerHandler(on_poll_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stray))
