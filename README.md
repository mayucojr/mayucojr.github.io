# Mario's Personal Website

Live at <https://mayucojr.com>.

## Publishing (for Mario)

You don't need VSCode, the terminal, or any code.

1. Go to <https://app.pagescms.org> and sign in with GitHub.
2. Open **mayucojr.github.io**.
3. Choose **Writing** (articles) or **Curation** (exhibitions).
4. Click to add a new entry, fill in the form, add photos with the picture button, and **Save**.

About a minute after you save, the entry appears on the site. If it doesn't show up after
five minutes, tell Gabriel.

Tips:
- Dates are picked from a calendar, so there is nothing to type or format.
- To fix a typo in an old entry, open it from the list, change it, and save.
- Photos from an iPhone are fine. They're shrunk automatically so the site loads fast.
- Don't upload videos through the form (they're too big). Ask Gabriel.

---

## How it works (for developers)

```
Pages CMS form  ->  saves a .md file + photos to GitHub (master)
                ->  GitHub Actions runs scripts/build.py
                ->  the built site is deployed to GitHub Pages
```

- `.pages.yml` defines the CMS forms. Fields must match what `scripts/build.py` reads
  (`title`, `date` or `start-date` / `end-date`, `image-left/middle/right`, `tags`).
- `.github/workflows/deploy.yml` builds and deploys on every push to `master`.
- `scripts/build.py` turns the markdown into pages. A broken entry is skipped with a plain-English
  warning (shown on the Actions run) and the rest of the site still builds.
  Use `python3 scripts/build.py --strict` to make skipped entries an error.
- `scripts/optimize_images.py` runs first: converts `.heic` to `.jpg`, shrinks big photos, and
  updates links.
- The generated pages (`assets/articles/html/`, `assets/curation/html/`) are not stored in git.
  The list sections of `writing.html` and `curation.html` between the `AUTO:START` / `AUTO:END`
  markers are also regenerated on every deploy.

### Building locally

One-time setup (from the `mayucojr.github.io` folder):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Then, each time:
```bash
source .venv/bin/activate
python3 scripts/build.py
python3 -m http.server 8000 --bind 127.0.0.1   # open http://127.0.0.1:8000
```
Local builds rewrite the AUTO sections of `writing.html` / `curation.html`; you don't need to commit those changes.

### Entry file format

If you edit markdown directly instead of using the CMS:

```markdown
---
title: "Article title"
date: 2026-10-28            # curation entries use start-date: and optional end-date:
tags:
  - text: burnaway
    href: https://burnaway.org
---

Body text. Images: ![Caption shown under the photo](/assets/images/uploads/photo.jpg)
```
Curation entries also take `image-left`, `image-middle` and `image-right`
(e.g. `/assets/images/uploads/photo.jpg`). Older entries keep their photos in
`assets/images/article_*` and `assets/images/curation_*` folders, which still work.

### Project structure

- `index.html`, `writing.html`, `curation.html`, `contact.html`: the pages
- `assets/articles/markdown`, `assets/curation/markdown`: the entries (source of truth)
- `assets/images`: photos (`uploads/` is where the CMS saves new ones)
- `assets/templates`: HTML templates used by the build
- `assets/css/style.css`, `assets/js/`: styling and scripts
- `scripts/`: build and image tools
- `.pages.yml`, `.github/workflows/deploy.yml`: CMS form definitions and deploy workflow
