# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo shape

Two deliverables share one data file:

- **Static flashcard web app** at the repo root (`index.html`, `app.js`, `styles.css`) — vanilla JS, no build step. Fetches `questions.json` at runtime.
- **Telegram quiz bot** in `bot/` — Python, `python-telegram-bot==21.6`, long-polling, SQLite for per-user state. Reads the same `questions.json`.

Both consume `questions.json` with shape `[{id, page, question, answer}, ...]`. Preserve this shape when editing the data pipeline.

## Data pipeline

`questions.json` is **generated**, but committed. Source of truth for content is `data/pages_json/p*.json` (one file per PDF page, each row keyed by `n` = per-page question number). `scripts/merge_pages.py` renumbers `n` → global `id`, attaches `page`, sorts by id, warns on duplicates, and writes `questions.json`.

A sidecar `data/distractors.json` (committed) holds three pre-generated plausible wrong answers per question id, used by the bot at runtime. It is populated in batches by Claude Code: `python3 scripts/distractors_next_batch.py [N]` prints the next N question ids missing from the sidecar (with their page-file location for in-place corrections) and validates the existing entries — a malformed sidecar exits non-zero and blocks the workflow. The full generation contract and rules are in `docs/superpowers/specs/2026-05-21-realistic-distractors-design.md`.

To regenerate `questions.json` after editing `data/pages_json/*`:
```bash
uv run python3 scripts/merge_pages.py
```

`scripts/extract_images.py` rips one JPG per page from `jpg2pdf (11).pdf` into `data/pages/` (gitignored — regenerable). Only re-run if the source PDF changes.

## Bot architecture

Entrypoint `bot/bot.py` wires four single-responsibility modules:

- **`config.py`** — strict env-var parsing. `BOT_TOKEN` required and regex-validated (`\d{6,}:[A-Za-z0-9_-]{30,}`). Other env: `QUESTIONS_PATH`, `DISTRACTORS_PATH` (default `data/distractors.json`), `DB_PATH` (default `/data/bot.sqlite`, the Fly volume mount), `RECENT_HISTORY` (default 30), `POLL_OPEN_SECONDS` (default 600), `LOG_LEVEL`.
- **`store.py`** — SQLite (WAL mode) wrapping three tables: `users` (lifetime tally + active flag), `recent` (per-user FIFO of last N question ids, evicted half-batch when exhausted), `last_quiz` (the in-flight poll keyed by uid). `pick_next_question` excludes recent ids.
- **`quiz.py`** — pure function `build_quiz(q, distractors, rng)` builds the 4-option MCQ from the question's correct answer plus three pre-curated distractors looked up by id in the sidecar dict. Truncates to Telegram limits (`QUESTION_LIMIT=300`, `OPTION_LIMIT=100`); if truncation collides two options, the duplicate is disambiguated by appending `·`. Raises `QuizSkip` if the question has no distractors entry, the entry is malformed, the distractors aren't distinct, a distractor equals the correct answer, or the question/answer is empty — the caller's 5-attempt retry loop in `_send_next_quiz` absorbs these and picks another question.
- **`handlers.py`** — PTB command handlers + `PollAnswerHandler`. `_send_next_quiz` wraps `build_quiz` in a 5-attempt loop to absorb `QuizSkip`. `on_poll_answer` validates the answered poll_id matches the user's stored `last_quiz` (so stale or cross-user polls are ignored), records the result, and chains the next quiz only if `users.active = 1`.

Non-obvious: the bot keys everything off `uid`, not `chat_id`. Private chats only — `_send_next_quiz` is called with `chat_id=uid`.

## Common commands

```bash
# Web app — local server (fetch() requires http://, not file://)
python3 -m http.server 8000

# Bot — local run (BOT_TOKEN required, DB_PATH overridden to avoid /data)
export BOT_TOKEN=<token from @BotFather>
export DB_PATH=$(pwd)/bot.sqlite
uv run --with python-telegram-bot==21.6 python -m bot.bot

# Tests — pytest; tests/conftest.py injects repo root into sys.path so `bot` imports without install
uv run --with python-telegram-bot==21.6 --with pytest pytest
# Single test:
uv run --with python-telegram-bot==21.6 --with pytest pytest tests/test_quiz.py::test_builds_four_distinct_options
```

## Deployment

Fly.io app `abror-test-bot`, region `fra`, shared-cpu-1x / 256 MB. SQLite lives on the `bot_data` volume mounted at `/data`. GitHub Actions (`.github/workflows/deploy-bot.yml`) auto-deploys on push to `main` only when `bot/**`, `Dockerfile`, `fly.toml`, `questions.json`, `data/distractors.json`, or the workflow itself changes — pure web-app or docs edits do not redeploy. Manual deploy: `flyctl deploy`.

**Do not deploy until `data/distractors.json` covers every question.** With partial or empty coverage the bot stays up but `QuizSkip`s every quiz attempt, so the user just sees "No answerable questions found right now." Sanity check before pushing: `python3 scripts/distractors_next_batch.py 1` must print `[]`.
