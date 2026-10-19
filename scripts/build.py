"""Render content/pages/ through templates/base.html into dist/ (offline).

Usage: uv run scripts/build.py [--base-path /orthodox-nz-temp]

--base-path is the site's path on its host (actions/configure-pages gives it). Only 404.html needs it:
GitHub Pages serves that page at any depth, so its links cannot be relative.
"""

import argparse
import re
import shutil
import sys
import tomllib
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "pages"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
LATIN = re.compile(r"[A-Za-z]")
# Elements whose text decides their own language when it differs from the page's.
LANG_BLOCKS = {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "figcaption", "blockquote", "div", "dd", "dt", "ul", "ol"}
# Containers that never take a lang themselves but whose cells do.
LANG_CONTAINERS = {"table", "thead", "tbody", "tfoot", "tr", "section", "dl"}
# A run of Russian inside other text: from a Cyrillic letter to the last one, with no Latin letters between.
CYRILLIC_RUN = re.compile(r"[\u0400-\u04FF](?:[^A-Za-z<>]*[\u0400-\u04FF])?[»\".!?)…]*")


def load_site():
    with open(ROOT / "site.toml", "rb") as f:
        return tomllib.load(f)


def script_of(text):
    """'ru', 'en' or None when the text has no clear majority of one script."""
    cyr = len(CYRILLIC.findall(text))
    lat = len(LATIN.findall(text))
    if cyr + lat < 3:
        return None
    if cyr >= 0.8 * (cyr + lat):
        return "ru"
    if lat >= 0.8 * (cyr + lat):
        return "en"
    return None


def page_language(soup):
    text = soup.get_text(" ")
    return "ru" if len(CYRILLIC.findall(text)) > len(LATIN.findall(text)) else "en"


def mark_languages(node, page_lang):
    """Put lang on the largest blocks written in the other language, as WCAG asks."""
    for child in node.children:
        if not isinstance(child, Tag) or child.has_attr("lang"):
            continue
        if child.name in LANG_CONTAINERS:
            mark_languages(child, page_lang)
            continue
        if child.name not in LANG_BLOCKS:
            continue
        lang = script_of(child.get_text(" "))
        if lang and lang != page_lang:
            child["lang"] = lang
        else:
            mark_languages(child, page_lang)


def effective_lang(node, page_lang):
    holder = node if isinstance(node, Tag) and node.has_attr("lang") else node.find_parent(
        lambda t: t.has_attr("lang")
    )
    return holder["lang"] if holder else page_lang


def mark_russian_runs(soup, page_lang):
    """Russian words left inside English text (bilingual headings, table cells) get <span lang="ru">."""
    for text in list(soup.find_all(string=CYRILLIC)):
        if isinstance(text, Comment) or effective_lang(text, page_lang) == "ru":
            continue
        parent = text.parent
        if text.strip() and CYRILLIC_RUN.fullmatch(text.strip()) and parent.name != "[document]" and all(
            c is text or (isinstance(c, NavigableString) and not c.strip()) for c in parent.contents
        ):
            parent["lang"] = "ru"
            continue
        pieces, last = [], 0
        for m in CYRILLIC_RUN.finditer(text):
            pieces.append(NavigableString(text[last:m.start()]))
            span = soup.new_tag("span", lang="ru")
            span.string = m.group()
            pieces.append(span)
            last = m.end()
        pieces.append(NavigableString(text[last:]))
        for piece in pieces:
            if not (isinstance(piece, NavigableString) and not str(piece)):
                text.insert_before(piece)
        text.extract()
    for img in soup.find_all("img", alt=CYRILLIC):
        if script_of(img["alt"]) == "ru" and effective_lang(img, page_lang) != "ru":
            img["lang"] = "ru"


def pages(site):
    """(path, meta) for every page: the ones listed in site.toml plus the mirrored articles."""
    listed = dict(site["pages"])
    for path in sorted(p.relative_to(CONTENT).as_posix() for p in (CONTENT / "article").glob("*.html")):
        listed.setdefault(path, {"kind": "mirror"})
    on_disk = {p.relative_to(CONTENT).as_posix() for p in CONTENT.rglob("*.html")}
    missing = sorted(set(listed) - on_disk)
    unlisted = sorted(on_disk - set(listed))
    if missing or unlisted:
        sys.exit(f"build: content/pages and site.toml disagree. missing: {missing} unlisted: {unlisted}")
    return listed


def render_page(env, site, path, meta, root, current):
    fragment = (CONTENT / path).read_text(encoding="utf-8")
    soup = BeautifulSoup(fragment, "html.parser")
    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        sys.exit(f"build: {path} must have exactly one <h1>, found {len(h1s)}")
    lang = meta.get("lang") or page_language(soup)
    mark_languages(soup, lang)
    mark_russian_runs(soup, lang)
    title = " ".join(h1s[0].get_text(" ").split())
    return env.get_template("base.html").render(
        site=site["site"],
        menu=site["menu"],
        footer=site["footer"],
        lang=lang,
        title=title,
        is_home=path == "index.html",
        description=meta.get("description") or site["site"]["description"],
        root=root,
        current=current,
        content=Markup(str(soup).strip()),
    )


def build(base_path=""):
    site = load_site()
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), undefined=StrictUndefined, autoescape=True)
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)
    for path, meta in pages(site).items():
        depth = path.count("/")
        html = render_page(env, site, path, meta, "../" * depth, path)
        for out in [path, *meta.get("aliases", [])]:
            target = DIST / out
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")
    base = base_path.rstrip("/") + "/"
    not_found = (
        "<h1>Page not found</h1>"
        f'<p>This page does not exist. Please start from the <a href="{base}index.html">home page</a>.</p>'
        f'<p lang="ru">Такой страницы нет. Начните, пожалуйста, с <a href="{base}index.html">главной страницы</a>.</p>'
    )
    (DIST / "404.html").write_text(
        env.get_template("base.html").render(
            site=site["site"],
            menu=site["menu"],
            footer=site["footer"],
            lang="en",
            title="Page not found",
            is_home=False,
            description=site["site"]["description"],
            root=base,
            current="",
            content=Markup(not_found),
        ),
        encoding="utf-8",
    )
    return site


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-path", default="", help="path of the site on its host, e.g. /orthodox-nz-temp")
    args = parser.parse_args()
    build(args.base_path)
    print(f"build: wrote {sum(1 for p in DIST.rglob('*.html'))} pages to {DIST.relative_to(ROOT)}/")
