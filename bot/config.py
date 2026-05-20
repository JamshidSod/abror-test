"""Bot configuration from environment variables."""
from __future__ import annotations
import os
import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r"^\d{6,}:[A-Za-z0-9_-]{30,}$")


class ConfigError(RuntimeError):
    """Raised when the environment is missing or malformed."""


@dataclass(frozen=True)
class Config:
    bot_token: str
    questions_path: str
    db_path: str
    recent_history: int
    poll_open_seconds: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            raise ConfigError("BOT_TOKEN env var is required.")
        if not TOKEN_RE.match(token):
            raise ConfigError(
                "BOT_TOKEN format invalid; expected '<id>:<secret>' from @BotFather."
            )
        return cls(
            bot_token=token,
            questions_path=os.environ.get("QUESTIONS_PATH", "questions.json"),
            db_path=os.environ.get("DB_PATH", "/data/bot.sqlite"),
            recent_history=int(os.environ.get("RECENT_HISTORY", "30")),
            poll_open_seconds=int(os.environ.get("POLL_OPEN_SECONDS", "600")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
