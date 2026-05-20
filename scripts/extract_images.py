# scripts/extract_images.py
"""Extract embedded JPGs from each page of jpg2pdf (11).pdf."""
from pathlib import Path
from pypdf import PdfReader

PDF = Path(__file__).resolve().parent.parent / "jpg2pdf (11).pdf"
OUT = Path(__file__).resolve().parent.parent / "data" / "pages"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(PDF))
    saved = 0
    for i, page in enumerate(reader.pages):
        for img in page.images:
            name = OUT / f"p{i + 1:03d}.jpg"
            name.write_bytes(img.data)
            saved += 1
            break  # one image per page in this PDF
    print(f"Saved {saved} page images to {OUT}")


if __name__ == "__main__":
    main()
