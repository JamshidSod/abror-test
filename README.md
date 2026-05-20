# Abror Test Prep

A free, static flashcard web app for ~501 Uzbek-language professional-licensing test questions covering electrical engineering, plumbing, HVAC, building materials, and construction norms.

## Use

Open `index.html` in any modern browser, or visit the hosted version (link TBD on deploy).

## Hosting

Push to GitHub and enable Pages from `main` / root. No build step.

## Re-generating `questions.json`

```bash
uv run --with pypdf --with pillow scripts/extract_images.py
# Then run OCR on each data/pages/pNNN.jpg into data/pages_json/pNNN.json
uv run scripts/merge_pages.py
```
