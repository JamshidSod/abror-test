# Realistic distractors + source-text verification

**Date:** 2026-05-21
**Status:** Draft (awaiting user review)

## Problem

The Telegram quiz bot (`bot/quiz.py:build_quiz`) currently builds 3 wrong answers by sampling other questions' correct answers from the same `questions.json` pool. This pool is heterogeneous — a question about voltage class can end up with distractors that are document codes, procedure descriptions, or unrelated units. The quizzes are therefore trivially guessable and feel nonsensical.

Compounding the problem, the source text in `data/pages_json/p*.json` was transcribed by hand from PDF page images and contains visible OCR/transcription errors: misspellings (e.g. `иқисқлик`, `Куримзиннинг`), broken word fragments (`ч ни`, `к а б о ?`), and lexical drift away from the standard Cyrillic-Uzbek register used in the official norms.

## Goals

1. Every quiz shows one correct answer and three **domain-appropriate, type-matched** wrong answers (same conceptual category — a voltage class is matched with other voltage classes; a document code with other document codes; a procedure with alternative procedures).
2. Misspelled or garbled words in question and answer text are corrected before they reach the user.
3. The pipeline is **resumable** across sessions and **diff-reviewable** — every change is a human-readable git diff before it ships.
4. No new production runtime dependencies, no external API key in the deployed bot.

## Non-goals

- Runtime / per-session distractor variation (distractors are static once generated).
- Per-user distractor personalization.
- Re-OCR of the source PDF.
- Translation, transliteration, or modernization of the Uzbek text beyond fixing clear errors.
- Changing the web flashcard app's behavior (it shows the canonical answer only; distractors are bot-only).

## Architecture

```
                          ┌─────────────────────────────────────┐
                          │ data/pages_json/p001.json … p020.json│  ← human-authored source of truth
                          │   [{n, question, answer}, …]         │     (auto-corrected in place by this pipeline)
                          └────────────────┬─────────────────────┘
                                           │ scripts/merge_pages.py
                                           ▼
                                    questions.json                 ← generated, committed
                                           │
                                           │ scripts/distractors_next_batch.py
                                           ▼
        ┌───────────────────────────────────────────────────────────┐
        │ Claude Code session (runner):                              │
        │   • read batch of N rows missing from distractors.json     │
        │   • for each row: propose corrected question/answer +      │
        │     3 distractors                                          │
        │   • write corrections back into pages_json/*               │
        │   • append distractor entries to data/distractors.json     │
        │   • re-run merge_pages.py                                  │
        │   • commit the batch                                       │
        └───────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                              data/distractors.json                 ← generated, committed
                                           │
                                           │ loaded at bot startup
                                           ▼
                                  bot/quiz.py::build_quiz
```

There is no production API call. Generation happens once, offline, in interactive Claude Code sessions; the bot only reads the committed artifacts.

## Data shapes

### `data/distractors.json` (new, committed)

```json
{
  "1": ["Кабел линиялари ва электр узатиш қурилмалари", "Подстанциялар ва ҳимоя релелари", "Электр энергия истеъмолчилари ва уларнинг тармоғи"],
  "2": ["Иссиқлик электростанцияси", "Гидроэлектростанция", "Шамол электростанцияси"],
  ...
}
```

- Top-level object keyed by question `id` as a **string** (JSON has no integer keys).
- Each value is exactly 3 distinct non-empty Cyrillic-Uzbek strings.
- File is sorted by numeric id at write time for stable diffs.
- Missing ids are valid — the bot treats them as `QuizSkip` and the retry loop picks another question.

### `data/pages_json/p*.json` (existing, edited in place)

Schema unchanged. Edits during generation are limited to the `question` and `answer` string fields when the runner identifies a clear error. The `n` (per-page number) field is never touched.

## Workflow

### Per-batch loop (run by the user in a Claude Code session)

1. `python3 scripts/distractors_next_batch.py 50` — prints the next 50 question ids missing from `data/distractors.json`, along with the page file and per-page index needed to locate each row. Exit code 0 with empty output means done.
2. Claude reads the indicated rows from `data/pages_json/p*.json`.
3. For each row, Claude works out an internal record of this shape (in-memory only — not written to any file as a whole):
   ```json
   {
     "id": 24,
     "question_corrected": "...",
     "answer_corrected": "...",
     "distractors": ["...", "...", "..."]
   }
   ```
   `question_corrected` / `answer_corrected` are populated only when a correction is being proposed; otherwise the original text is used. **Distractors are always generated against the corrected text**, so the three wrong answers stay aligned with the cleaned-up correct answer.
4. Claude then writes the record out to two different files:
   - **Corrections** → edit the relevant `data/pages_json/p*.json` file in place, replacing only the `question` and/or `answer` string for that row.
   - **Distractors** → set `data/distractors.json["<id>"]` to the 3-string list.
   - Re-run `python3 scripts/merge_pages.py` to refresh `questions.json` from the corrected page sources.
5. User reviews `git status` + `git diff` for the batch.
6. Claude commits the batch with message `data(distractors): generate batch N (ids X–Y)`.

The pipeline is naturally resumable — interrupting between batches loses at most the current batch's in-flight work.

### Forcing regeneration

To re-do a single id whose output looked bad in review:
- Delete that key from `data/distractors.json`.
- Run the loop again — the batch helper will surface only the missing ids.

## Generation rules (the runner's contract)

"Correct answer" in the rules below means the **corrected** answer text — corrections are applied first, distractors generated against the cleaned-up text. For each question, Claude must produce distractors that satisfy **all** of:

1. **Same conceptual type as the correct answer.** Examples:
   - Correct = `"1 тоифа"` → distractors are other category labels (`"2 тоифа"`, `"3 тоифа"`, `"махсус тоифа"`), not unrelated documents or units.
   - Correct = `"500кВ"` → distractors are other voltage classes (`"35кВ"`, `"110кВ"`, `"220кВ"`).
   - Correct = `"ПУЭ"` → distractors are other regulatory documents (`"СНиП"`, `"ГОСТ"`, `"СП"`).
   - Correct = a procedure / multi-clause sentence → distractors are alternative procedures of similar length and register.
2. **Same language and script.** Cyrillic-Uzbek. Same level of formality as the correct answer.
3. **Length similar to the correct answer.** Roughly within ×0.6 to ×1.6 of the correct answer's length so all four options look symmetric in the poll.
4. **Distinct.** No two distractors are equal (case-insensitive, trimmed), and none equals the correct answer.
5. **Plausible to a test-taker who has skimmed the material** but unambiguously wrong to one who has studied it.
6. **No leading numbering or labels** (`"A) "`, `"1. "`, etc.) — Telegram renders option lettering itself.

Correction rules:

7. Fix obvious misspellings, broken word fragments, and missing diacritics. Do not rewrite sentences for style. Do not change technical meaning.
8. If the correct answer itself looks corrupt and you cannot recover it confidently, **skip the row** (do not write distractors for it). The bot will fall through to the next question.
9. Preserve composite-answer constructs like `"А ва Б жавоблар (ПУЭ ва СП 256.1325800.2006)"` verbatim — these reference quiz-internal answer choices and must not be paraphrased.

## Validation (script-side)

`scripts/distractors_next_batch.py` and `scripts/merge_pages.py` are responsible for sanity-checking outputs after each batch:

- `distractors.json` parses as object.
- Every value is a list of exactly 3 strings.
- For every key present, the corresponding question id exists in `questions.json`.
- Within each entry, all 3 strings are distinct (case-insensitive, trimmed) and none equals the question's `answer` field.
- File is sorted by numeric id.

Validation runs as part of the batch helper's default mode and exits non-zero on failure, blocking the commit.

## Bot changes

### `bot/config.py`

Add one field:

```python
distractors_path: str   # default: "data/distractors.json"
```

Sourced from `DISTRACTORS_PATH` env var; in `fly.toml` set to `/app/data/distractors.json`.

### `bot/handlers.py`

- New `load_distractors(path) -> dict[int, list[str]]` mirroring `load_questions`. Returns `{int(id): [a,b,c], …}`. Validates list-of-3 shape and raises at startup on malformed input.
- `register_handlers(app, questions, distractors, store, rng, poll_open_seconds)` — distractors threaded through.
- `_send_next_quiz` passes the distractors dict to `build_quiz`.

### `bot/quiz.py`

```python
def build_quiz(q: dict, distractors: dict[int, list[str]], rng: random.Random) -> Quiz: ...
```

Changes:

- Wrong-answer **pool / length-similar filter / fallback** path is **deleted**. The function no longer needs the full question list.
- Look up `distractors.get(q["id"])`. If absent or fails shape check, raise `QuizSkip`.
- Build the 4-option list from `[correct] + distractors[q["id"]]`, shuffle, record `correct_option_id`.
- Truncation (300 / 100 char caps) and post-truncation `·` disambiguation stay unchanged.

### `bot/bot.py`

Load distractors after questions and pass them into `register_handlers`.

## Dockerfile

Add `COPY data/distractors.json /app/data/distractors.json` (and `RUN mkdir -p /app/data` before that). `fly.toml` gets `DISTRACTORS_PATH = "/app/data/distractors.json"` in `[env]`.

## CI / deploy

`.github/workflows/deploy-bot.yml` `paths` filter gains `data/distractors.json` so distractor-only batches trigger a redeploy. (`data/pages_json/**` does not need to trigger deploy — its content only reaches prod via `questions.json` and `distractors.json`, both already covered.)

## Tests

### Updated: `tests/test_quiz.py`

Rewrite all cases to pass a distractors dict instead of relying on the question pool:

- 4 distinct options, correct one at `correct_option_id`.
- `QuizSkip` when the id is missing from the dict.
- `QuizSkip` when the dict entry isn't a list of 3.
- `QuizSkip` when a distractor equals the correct answer (post-trim, case-insensitive).
- Truncation still triggers `truncated=True` for >300-char questions and >100-char options.
- Post-truncation collision still disambiguated with `·`.

### New: `tests/test_distractors_next_batch.py`

Pure unit tests for the helper's validation (no Telegram, no LLM, no I/O beyond `tmp_path`):

- Surfaces only ids missing from `distractors.json`.
- `--limit N` caps batch size.
- Detects bad shape (not list-of-3, duplicates, equals-correct) and exits non-zero with a useful message.

### Existing: `tests/test_store.py`, `tests/test_config.py`

`test_config.py` gains coverage for `distractors_path` (default + override). `test_store.py` is untouched.

## Migration / rollout

1. Land the spec, plan, and bot code changes behind a startup check: if `data/distractors.json` is empty `{}` and the bot is run, every quiz will hit `QuizSkip` and the user gets the "no answerable questions" message. That's acceptable in dev; **do not deploy** until generation has covered all ids.
2. Generate distractors in batches of 50, committing each batch.
3. Once `data/distractors.json` covers every id in `questions.json`, deploy.
4. Final deploy triggers the GH Actions workflow; Fly volume retains `bot.sqlite` so user progress is preserved across the rollover.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Claude proposes a "correction" that silently changes a question's meaning. | Every correction is a git diff. Reviewer (you) reads the diff before commit. Spec rule 7 forbids meaning changes. |
| Claude generates distractors that are too similar to the correct answer (ambiguous quiz). | Validation rule + per-batch human review. If a batch looks weak, delete those ids from `distractors.json` and re-run. |
| Generation context limit reached mid-batch. | Batch size capped at 50. Helper script makes resumption trivial. |
| Bot deployed before `distractors.json` is complete → users see "no answerable questions". | Rollout step 1 explicitly gates deploy on full coverage. |
| Source pages_json edited in parallel by something else and the runner clobbers changes. | Single human editor by convention; reviewer catches via git diff. |

## Out of scope (deliberately deferred)

- Per-question difficulty tagging.
- Distractor refresh on a schedule.
- Quiz analytics / "which distractors fool users most often."
- Multi-language support beyond Uzbek.
- Web app changes — flashcards remain question + canonical answer only.
