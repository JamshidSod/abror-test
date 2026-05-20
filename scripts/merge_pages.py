# scripts/merge_pages.py
"""Merge data/pages_json/p*.json into a single questions.json with global ids."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "data" / "pages_json"
OUT = ROOT / "questions.json"


def page_num(path: Path) -> int:
    m = re.match(r"p(\d+)\.json", path.name)
    if not m:
        raise ValueError(f"unexpected filename: {path.name}")
    return int(m.group(1))


def main() -> None:
    merged = []
    for path in sorted(PAGES.glob("p*.json"), key=page_num):
        page = page_num(path)
        for row in json.loads(path.read_text(encoding="utf-8")):
            merged.append({
                "id": row["n"],
                "page": page,
                "question": row["question"],
                "answer": row["answer"],
            })
    # Sort by id, then warn on duplicates
    merged.sort(key=lambda r: r["id"])
    for i in range(1, len(merged)):
        if merged[i]["id"] == merged[i - 1]["id"]:
            print(f"WARNING: duplicate id {merged[i]['id']}")
    OUT.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(merged)} questions to {OUT}")


if __name__ == "__main__":
    main()
