# Abror Test Prep

A free, static flashcard web app for ~470 Uzbek-language professional-licensing test questions extracted from `jpg2pdf (11).pdf` — covering electrical engineering, plumbing, HVAC, building materials, and construction norms.

## Use locally

Open `index.html` directly, or run a local server (recommended so `fetch` works on all browsers):

```bash
python3 -m http.server 8000
# then visit http://localhost:8000/
```

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `←` / `→` | Previous / next card |
| `Space` | Reveal / hide answer |
| `/` | Focus the search box |
| `Esc` | Clear the search box |

## Deploy to GitHub Pages (free)

1. Create a new GitHub repo and push this folder:

   ```bash
   git remote add origin https://github.com/<you>/abror-test.git
   git push -u origin main
   ```

2. In the repo settings, go to **Pages** → **Source: Deploy from a branch**, branch `main`, folder `/ (root)`. Save.

3. After a minute, the app is live at `https://<you>.github.io/abror-test/`.

Alternatives: drag-and-drop the folder onto [Netlify Drop](https://app.netlify.com/drop) or [Cloudflare Pages](https://pages.cloudflare.com/). Both are free.

## Re-generate `questions.json`

The shipped `questions.json` is the output of a one-time OCR pass on the source PDF. If the source changes, re-run:

```bash
uv run --with pypdf --with pillow scripts/extract_images.py
# Then transcribe data/pages/p*.jpg into data/pages_json/p*.json (one file per page).
uv run python3 scripts/merge_pages.py
```

## License

Personal study tool. Source content from the original PDF — verify with the source before relying on any answer.
