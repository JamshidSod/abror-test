# tests/test_config.py
import pytest
from bot.config import Config, ConfigError


def test_loads_required_token(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1234567890:AAH" + "x" * 30)
    cfg = Config.from_env()
    assert cfg.bot_token.startswith("1234567890:")
    assert cfg.questions_path == "questions.json"
    assert cfg.db_path == "/data/bot.sqlite"
    assert cfg.recent_history == 30
    assert cfg.poll_open_seconds == 600
    assert cfg.log_level == "INFO"


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        Config.from_env()


def test_bad_token_format_raises(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "garbage")
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        Config.from_env()


def test_overrides(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1234567890:AAH" + "x" * 30)
    monkeypatch.setenv("QUESTIONS_PATH", "/tmp/q.json")
    monkeypatch.setenv("DB_PATH", "/tmp/bot.sqlite")
    monkeypatch.setenv("RECENT_HISTORY", "50")
    monkeypatch.setenv("POLL_OPEN_SECONDS", "120")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = Config.from_env()
    assert cfg.questions_path == "/tmp/q.json"
    assert cfg.db_path == "/tmp/bot.sqlite"
    assert cfg.recent_history == 50
    assert cfg.poll_open_seconds == 120
    assert cfg.log_level == "DEBUG"


def test_distractors_path_default(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1234567890:AAH" + "x" * 30)
    cfg = Config.from_env()
    assert cfg.distractors_path == "data/distractors.json"


def test_distractors_path_override(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1234567890:AAH" + "x" * 30)
    monkeypatch.setenv("DISTRACTORS_PATH", "/tmp/d.json")
    cfg = Config.from_env()
    assert cfg.distractors_path == "/tmp/d.json"
