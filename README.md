# orthodox-nz-temp

Temporary website of the New Zealand Deanery of the Russian Orthodox Church Outside of Russia, published by the Church of the Resurrection of Christ Russian Orthodox Church Abroad Trust (registered charity CC42458).

- Address: https://orthodox.nz/ (connected 2026-10-19 by Fr Alexander's decision; https://crcrocor.github.io/orthodox-nz-temp/ redirects there).
- What it is: a deanery home page, a copy of the old Auckland parish site orthodox.net.nz on one template, and the About, Contact and Privacy pages, in English (default) and Russian (under `ru/`). The Wagtail portal in [crcrocor/orthodox-nz](https://github.com/crcrocor/orthodox-nz) replaces it later (task 008, decision 0004 there).
- Rules for people and agents: [AGENTS.md](AGENTS.md).

## How it is built

```
orthodox.net.nz ──scripts/mirror.py──▶ content/pages/ + static/ ──scripts/build.py──▶ dist/ ──GitHub Actions──▶ Pages
```

- `site.toml` lists the menu, the footer and every page with its kind:
  - `mirror` — regenerated from the old site on every mirror run (pages in one language only: the English bulletin, the Russian newsletter, the Creed lectures, the online catechism and the 53 articles);
  - `frozen` — copied from the old site once, then split into English and Russian and edited by hand (the parish page `home.html`, schedule, news, donations, benevolent fund, school, about Orthodoxy, links, contact, clergy);
  - `local` — written by hand (the deanery home page `index.html`, about, privacy).
- `content/pages/` holds the page bodies in English (HTML without header, menu or footer); `content/pages/ru/` holds the Russian versions of the hand-made pages; `templates/base.html` adds the header, menu, language switch and footer; `static/` holds the CSS and the files and images from the old site, under their old paths.
- Every page is built twice: in English at its path and in Russian under `ru/`. Local and frozen pages have a Russian file in `content/pages/ru/`. Mirrored pages exist in one language only: both versions show the same body with the interface (and the heading, `h1_ru` in `site.toml`) in the reader's language and a short note (`note_en` / `note_ru`).
- `scripts/corrections.py` holds the fixes for mirrored pages, so they survive every new mirror run.
- `old_paths.txt` lists every path the site has ever had. The mirror only adds to it, and the check fails if one of them is missing, so old links keep working.
- Every push to `main` runs `.github/workflows/pages.yml`: it builds the site, runs all checks and deploys only if they pass.

You need [uv](https://docs.astral.sh/uv/); it installs Python 3.14 and the three dependencies (`jinja2`, `beautifulsoup4`, `html5lib`) by itself. `scripts/fonts.py`, which makes the web fonts, brings its own (`fonttools`) and is needed only when the fonts change.

## Rebuild and check

```bash
uv run scripts/check.py
```

This builds `dist/` and checks it: every path in `old_paths.txt` exists, nothing points at orthodox.net.nz, no third-party resources, scripts (so the JS budget is 0) or forms, every internal link is relative and works, the CSS and font budgets (at most two families and four WOFF2 files of this site, each with its licence), headings, `lang` on Russian text, the footer, and the corrected facts. At the end it lists every open `TODO(content)` and `needs blessing:` item. The site is done only when it prints `check: OK`.

To look at the result:

```bash
python3 -m http.server -d dist 8000
```

and open http://localhost:8000/.

## Refresh from the old site

The old site keeps changing (monthly schedule, weekly English bulletin, weekly Russian newsletter), so the copy needs a refresh while both sites exist — for example every Friday, by whoever looks after this site.

```bash
rm -rf .cache/mirror
uv run scripts/mirror.py
uv run scripts/check.py
git diff --stat
```

Read the diff, then commit and push. The mirror fetches one page or file at a time with a pause between requests; the parish owns the old site, so it does not wait the 60 seconds that the old site's robots.txt asks of search engines. It stops when a correction no longer matches or a page loses text, and warns when the source of a frozen page has changed: it leaves a cleaned copy of the new source, with its files, in `.cache/mirror/frozen/`; copy the change into both language versions of the page by hand, copy the new files it lists into `static/`, and put the new hash it prints in the page's first line. The monthly service schedule is such a frozen page, so a new month means two new PDF links in `schedule.html` and `ru/schedule.html`. Nothing is deleted: pages and files the old site no longer links to stay, so their addresses keep working. Temporary errors of the old site are retried, and the mirror stops rather than mark a file as missing.

## Edit texts

- **Local and frozen pages** (deanery home, About, Privacy; the parish page, schedule, news, donations and the rest): edit `content/pages/<page>.html` (English) and `content/pages/ru/<page>.html` (Russian) and keep them in step. Write links in the Russian file as seen from the English page (`files/x.pdf`, `contact.html`); the build adjusts them. Keep the first line of a frozen page: it records which version of the old page it was copied from.
- **Other pages** (`mirror`): change the text on the old site and refresh, or add a fix to `scripts/corrections.py` (the exact text to find, the replacement, how many times it occurs and why).
- **Menu, footer, interface texts in both languages and descriptions**: `site.toml`. A page's title is its `<h1>`: edit it in the page, or for a mirrored page set `h1` in `site.toml` and refresh. **Layout and colours**: `templates/base.html`, `static/css/site.css`. **Fonts**: PT Serif, subset to Latin and Cyrillic and renamed "Deanery Serif" (its licence reserves the original name) by `uv run scripts/fonts.py` into `static/fonts/`; the characters it keeps are listed in the script.
- Facts about the trust come only from the Charities Register; anything unknown is written as a hidden `<!-- TODO(content): … -->`, anything that needs a decision as `<!-- needs blessing: … -->`. The list printed by the check goes to Fr Pavel first; what he cannot answer goes to Fr Vladimir. A grouped snapshot of it, in Russian, is in [docs/todo-and-blessings.md](docs/todo-and-blessings.md).

Then run `uv run scripts/check.py`, commit on a branch and open a pull request. Since the custom domain was connected (2026-10-19), changes reach `main` only through pull requests: the check runs on every pull request, and every push to `main` deploys.
