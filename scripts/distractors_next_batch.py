# scripts/distractors_next_batch.py
"""List ids missing from data/distractors.json, with their page-file location.

Also validates data/distractors.json against questions.json. Exits non-zero on
validation failure so a bad sidecar blocks the workflow.

Usage:
    python3 scripts/distractors_next_batch.py [LIMIT]

Prints a JSON array of batch records to stdout.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS = ROOT / "questions.json"
DEFAULT_DISTRACTORS = ROOT / "data" / "distractors.json"
DEFAULT_PAGES_DIR = ROOT / "data" / "pages_json"
DEFAULT_LIMIT = 50

PAGE_FILE_RE = re.compile(r"p(\d+)\.json")


def load_questions(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_distractors(path: Path) -> dict[int, list[str]]:
    p = Path(path)
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"{p}: expected a JSON object")
    out: dict[int, list[str]] = {}
    for k, v in raw.items():
        try:
            kid = int(k)
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"{p}: non-integer key {k!r}") from e
        out[kid] = v
    return out


def validate(distractors: dict[int, list[str]], questions: list[dict]) -> list[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: list[str] = []
    known_ids = {q["id"]: q for q in questions}
    for kid, v in distractors.items():
        if kid not in known_ids:
            errors.append(f"id {kid} not present in questions.json")
            continue
        if not isinstance(v, list) or len(v) != 3 or not all(
            isinstance(x, str) and x.strip() for x in v
        ):
            errors.append(f"id {kid}: entry must be a list of 3 non-empty strings")
            continue
        normalized = [x.strip().lower() for x in v]
        if len(set(normalized)) != 3:
            errors.append(f"id {kid}: distractors not distinct")
        correct = known_ids[kid].get("answer", "").strip().lower()
        if correct and correct in normalized:
            errors.append(f"id {kid}: a distractor matches correct answer")
    return errors


def missing_ids(
    distractors: dict[int, list[str]], questions: list[dict], limit: int
) -> list[int]:
    covered = set(distractors.keys())
    out: list[int] = []
    for q in questions:
        if q["id"] in covered:
            continue
        out.append(q["id"])
        if len(out) >= limit:
            break
    return out


def _page_number(path: Path) -> int:
    m = PAGE_FILE_RE.match(path.name)
    if not m:
        raise ValueError(f"unexpected page filename: {path.name}")
    return int(m.group(1))


def find_page_location(id_: int, pages_dir: Path) -> tuple[Path, int] | None:
    for path in sorted(Path(pages_dir).glob("p*.json"), key=_page_number):
        rows = json.loads(path.read_text(encoding="utf-8"))
        for idx, row in enumerate(rows):
            if row.get("n") == id_:
                return path, idx
    return None


def build_batch(
    ids: list[int], pages_dir: Path, questions: list[dict]
) -> list[dict]:
    by_id = {q["id"]: q for q in questions}
    out: list[dict] = []
    for kid in ids:
        q = by_id.get(kid)
        if q is None:
            continue
        loc = find_page_location(kid, pages_dir)
        if loc is None:
            continue
        path, idx = loc
        out.append({
            "id": kid,
            "page": q.get("page"),
            "page_file": str(path),
            "page_index": idx,
            "question": q.get("question", ""),
            "answer": q.get("answer", ""),
        })
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    limit = DEFAULT_LIMIT
    if argv:
        try:
            limit = int(argv[0])
        except ValueError:
            print("usage: distractors_next_batch.py [LIMIT]", file=sys.stderr)
            return 2

    questions = load_questions(DEFAULT_QUESTIONS)
    distractors = load_distractors(DEFAULT_DISTRACTORS)
    errors = validate(distractors, questions)
    if errors:
        print("data/distractors.json failed validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    ids = missing_ids(distractors, questions, limit=limit)
    batch = build_batch(ids, DEFAULT_PAGES_DIR, questions)
    print(json.dumps(batch, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
