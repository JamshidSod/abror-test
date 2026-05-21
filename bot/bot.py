"""Entrypoint: load config + questions + distractors, register handlers, run long-polling."""
from __future__ import annotations
import logging
import random
import signal
import sys

from telegram import BotCommand
from telegram.ext import Application

from .config import Config, ConfigError
from .handlers import load_distractors, load_questions, register_handlers
from .store import Store


COMMANDS = [
    BotCommand("start", "Begin or resume the quiz stream"),
    BotCommand("stop", "Pause the stream"),
    BotCommand("score", "Your lifetime tally"),
    BotCommand("full", "Show the last quiz's complete Q + A"),
    BotCommand("help", "List commands"),
]


async def _post_init(app: Application) -> None:
    await app.bot.set_my_commands(COMMANDS)


def main() -> None:
    try:
        cfg = Config.from_env()
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(2)

    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("bot")

    questions = load_questions(cfg.questions_path)
    log.info("Loaded %d questions from %s", len(questions), cfg.questions_path)

    distractors = load_distractors(cfg.distractors_path)
    log.info("Loaded distractors for %d questions from %s",
             len(distractors), cfg.distractors_path)

    store = Store(cfg.db_path, recent_history=cfg.recent_history)
    rng = random.Random()

    app = (
        Application.builder()
        .token(cfg.bot_token)
        .post_init(_post_init)
        .build()
    )
    register_handlers(app, questions, distractors, store, rng, cfg.poll_open_seconds)

    log.info("Starting polling")
    app.run_polling(
        allowed_updates=["message", "poll_answer"],
        stop_signals=(signal.SIGINT, signal.SIGTERM),
    )
    store.close()


if __name__ == "__main__":
    main()
