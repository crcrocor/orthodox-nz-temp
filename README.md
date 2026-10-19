# orthodox-nz-temp

Temporary website of the Church of the Resurrection of Christ, Auckland (Russian Orthodox Church Outside of Russia), published by the Church of the Resurrection of Christ Russian Orthodox Church Abroad Trust (registered charity CC42458).

- Now: https://crcrocor.github.io/orthodox-nz-temp/ — later at https://orthodox.nz/ (planned, after Fr Vladimir's blessing).
- What it is: a copy of the old parish site orthodox.net.nz on one neutral template, plus the About, Contact and Privacy pages. The Wagtail portal in [crcrocor/orthodox-nz](https://github.com/crcrocor/orthodox-nz) replaces it later (task 008, decision 0004 there).
- Rules for people and agents: [AGENTS.md](AGENTS.md).

## How it is built

```
orthodox.net.nz ──scripts/mirror.py──▶ content/pages/ + static/ ──scripts/build.py──▶ dist/ ──GitHub Actions──▶ Pages
```

- `site.toml` lists every page with its kind:
  - `mirror` — regenerated from the old site on every mirror run;
  - `frozen` — copied from the old site once, then edited by hand (home, contact, clergy);
  - `local` — written by hand (about, privacy).
- `content/pages/` holds the page bodies (HTML without header, menu or footer); `templates/base.html` adds those; `static/` holds the CSS and the files and images from the old site, under their old paths.
- `scripts/corrections.py` holds the fixes for mirrored pages, so they survive every new mirror run.
- Every push to `main` runs `.github/workflows/pages.yml`: it builds the site, runs all checks and deploys only if they pass.

You need [uv](https://docs.astral.sh/uv/); it installs Python 3.14 and the three dependencies (`jinja2`, `beautifulsoup4`, `html5lib`) by itself.

## Rebuild and check

```bash
uv run scripts/check.py
```

This builds `dist/` and checks it: every old path exists, nothing points at orthodox.net.nz, no third-party resources, scripts or forms, every internal link works, CSS and JS budgets, the footer, and the corrected facts. At the end it lists every open `TODO(content)` and `needs blessing:` item. The site is done only when it prints `check: OK`.

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

Read the diff, then commit and push. The mirror fetches one page or file at a time with a pause between requests; the parish owns the old site, so it does not wait the 60 seconds that the old site's robots.txt asks of search engines. It stops when a correction no longer matches, and warns when the source of a frozen page has changed (then copy the change into the frozen page by hand). Files no page links to any more are deleted from `static/`.

## Edit texts

- **About, Privacy** (`local`) and **home, Contact, Clergy** (`frozen`): edit `content/pages/<page>.html` directly. Keep the first line of a frozen page: it records which version of the old page it was copied from.
- **Other pages** (`mirror`): change the text on the old site and refresh, or add a fix to `scripts/corrections.py` (the exact text to find, the replacement, how many times it occurs and why).
- **Menu, footer, page titles and descriptions**: `site.toml`. **Layout and colours**: `templates/base.html`, `static/css/site.css`.
- Facts about the trust come only from the Charities Register; anything unknown is written as a hidden `<!-- TODO(content): … -->`, anything that needs Fr Vladimir's decision as `<!-- needs blessing: … -->`.

Then run `uv run scripts/check.py`, commit and push. Until the custom domain is connected we work directly in `main`; after that, only through pull requests.
