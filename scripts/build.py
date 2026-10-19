"""Render content/pages/ through templates/base.html into dist/ (offline), in English and Russian.

Usage: uv run scripts/build.py [--base-path /orthodox-nz-temp] [--base-url https://crcrocor.github.io/orthodox-nz-temp]

Every page is written twice: in English at its own path (the default, as on the old site) and in Russian
under ru/. A page with a hand-written Russian version takes it from content/pages/ru/<path>; the others
show the same body in both versions and only the header, menu and footer change. Page bodies always link
as seen from the English page; the Russian copy gets its links to files adjusted.

--base-path is the site's path on its host (actions/configure-pages gives it). Only 404.html needs it:
GitHub Pages serves that page at any depth, so its links cannot be relative. --base-url, the site's full
address (also from configure-pages), turns on the hreflang alternates, which must be absolute; without it
(a local build) they are left out, so the address never has to be written into the repository.
"""

import argparse
import posixpath
import re
import shutil
import sys
import tomllib
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "pages"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
LANGS = ("en", "ru")
PREFIX = {"en": "", "ru": "ru/"}

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
LATIN = re.compile(r"[A-Za-z]")
# Elements whose text decides their own language when it differs from the page's.
LANG_BLOCKS = {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "figcaption", "blockquote", "div", "dd", "dt", "ul", "ol"}
# Containers that never take a lang themselves but whose cells do.
LANG_CONTAINERS = {"table", "thead", "tbody", "tfoot", "tr", "section", "dl"}
# A run of one language inside the other: from its first letter to its last, with no letter of the other
# script between. A Latin run counts only with a word of three letters or more, so "CC42458" stays as it is.
RUNS = {
    "ru": re.compile(r"[Ѐ-ӿ](?:[^A-Za-z<>]*[Ѐ-ӿ])?[»\".!?)…]*"),
    "en": re.compile(r"[A-Za-z](?:[^Ѐ-ӿ<>]*[A-Za-z])?[\".!?)…]*"),
}
LATIN_WORD = re.compile(r"[A-Za-z]{3,}")


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


def mark_runs(soup, page_lang):
    """Words of one language left inside text of the other (bilingual headings, table cells) get a <span lang>."""
    for lang, run in RUNS.items():
        script = CYRILLIC if lang == "ru" else LATIN_WORD
        for text in list(soup.find_all(string=script)):
            if isinstance(text, Comment) or effective_lang(text, page_lang) == lang:
                continue
            parent = text.parent
            if text.strip() and run.fullmatch(text.strip()) and parent.name != "[document]" and all(
                c is text or (isinstance(c, NavigableString) and not c.strip()) for c in parent.contents
            ):
                parent["lang"] = lang
                continue
            pieces, last = [], 0
            for m in run.finditer(text):
                if lang == "en" and not LATIN_WORD.search(m.group()):
                    continue
                pieces.append(NavigableString(text[last:m.start()]))
                span = soup.new_tag("span", lang=lang)
                span.string = m.group()
                pieces.append(span)
                last = m.end()
            if not pieces:
                continue
            pieces.append(NavigableString(text[last:]))
            for piece in pieces:
                if not (isinstance(piece, NavigableString) and not str(piece)):
                    text.insert_before(piece)
            text.extract()
    for img in soup.find_all("img", alt=True):
        lang = script_of(img["alt"])
        if lang and lang != effective_lang(img, page_lang):
            img["lang"] = lang


def pages(site):
    """(path, meta) for every page: the ones listed in site.toml plus the mirrored articles."""
    listed = dict(site["pages"])
    for path in sorted(p.relative_to(CONTENT).as_posix() for p in (CONTENT / "article").glob("*.html")):
        listed.setdefault(path, {"kind": "mirror"})
    on_disk = {p.relative_to(CONTENT).as_posix() for p in CONTENT.rglob("*.html")}
    russian = {p.removeprefix("ru/") for p in on_disk if p.startswith("ru/")}
    on_disk = {p for p in on_disk if not p.startswith("ru/")}
    missing = sorted(set(listed) - on_disk)
    unlisted = sorted(on_disk - set(listed))
    orphans = sorted(russian - set(listed))
    untranslated = sorted(p for p, meta in listed.items() if meta["kind"] in ("local", "frozen") and p not in russian)
    if untranslated:
        sys.exit(f"build: hand-made pages need a Russian version in content/pages/ru/: {untranslated}")
    if missing or unlisted or orphans:
        sys.exit(
            f"build: content/pages and site.toml disagree. missing: {missing} unlisted: {unlisted} "
            f"Russian versions of unknown pages: {orphans}"
        )
    return listed


def localise_links(soup, path):
    """Move the links of an English page body to its Russian copy under ru/: pages stay in ru/, files do not."""
    for el, attr in [(a, "href") for a in soup.find_all("a", href=True)] + [
        (img, "src") for img in soup.find_all("img", src=True)
    ]:
        url = el[attr]
        parts = urllib.parse.urlsplit(url)
        if parts.scheme or parts.netloc or url.startswith(("#", "/", "?")):
            continue
        # Pages (and directories, whose index is a page) have a Russian twin at the same relative place.
        if parts.path in ("", ".", "..") or parts.path.endswith(("/", ".html")):
            continue
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path), parts.path))
        new = posixpath.relpath(target, posixpath.dirname("ru/" + path))
        el[attr] = urllib.parse.urlunsplit(("", "", new, parts.query, parts.fragment))


def prepare_menu(site, lang, page_root, current):
    groups = []
    for group in site["menu"]:
        title = group.get("title", {}).get(lang)
        items = []
        for item in group["items"]:
            label = item[lang]
            label_lang = script_of(label)
            items.append({
                "href": item.get("url") or page_root + item["path"],
                "label": label,
                "lang": label_lang if label_lang and label_lang != lang else None,
                "current": item.get("path") == current,
            })
        groups.append({"title": title, "items": items})
    footer = [{"href": page_root + f["path"], "label": f[lang], "current": f["path"] == current}
              for f in site["footer"]]
    return groups, footer


def render(env, site, lang, path, body, *, asset_root, page_root, base_url="", title=None, description=None):
    """asset_root leads to the site root (CSS, files), page_root to the root of this language's pages."""
    other = "ru" if lang == "en" else "en"
    menu, footer = prepare_menu(site, lang, page_root, path)
    ui = site["ui"][lang]
    return env.get_template("base.html").render(
        site=site["site"],
        ui=ui,
        lang=lang,
        other_lang=other,
        menu=menu,
        footer=footer,
        page_root=page_root,
        title=title,
        is_home=path == "index.html",
        description=description or ui["description"],
        asset_root=asset_root,
        here={code: asset_root + PREFIX[code] + path for code in LANGS},
        alternates={code: base_url.rstrip("/") + "/" + PREFIX[code] + ("" if path == "index.html" else path)
                    for code in LANGS} if base_url and path else None,
        content=Markup(body),
    )


def render_page(env, site, path, meta, lang, base_url=""):
    own = CONTENT / "ru" / path
    shared = lang == "ru" and not own.exists()
    source = own if lang == "ru" and own.exists() else CONTENT / path
    soup = BeautifulSoup(source.read_text(encoding="utf-8"), "html.parser")
    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        sys.exit(f"build: {source.relative_to(ROOT)} must have exactly one <h1>, found {len(h1s)}")
    if shared and meta.get("h1_ru"):
        h1s[0].string = meta["h1_ru"]
    if lang == "ru":
        localise_links(soup, path)
    if (shared or lang == "en") and script_of(soup.get_text(" ")) not in (None, lang):
        # Inside the body, so that foreign words in it get their lang like the rest.
        note = soup.new_tag("p", attrs={"class": "note"})
        note.string = meta.get(f"note_{lang}") or site["ui"][lang]["other_language_note"]
        h1s[0].insert_after(note)
    mark_languages(soup, lang)
    mark_runs(soup, lang)
    return render(
        env, site, lang, path, str(soup).strip(),
        asset_root="../" * (path.count("/") + (lang == "ru")),
        page_root="../" * path.count("/"),
        base_url=base_url,
        title=" ".join(h1s[0].get_text(" ").split()),
        description=meta.get("description_ru" if lang == "ru" else "description"),
    )


def build(base_path="", base_url=""):
    site = load_site()
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), undefined=StrictUndefined, autoescape=True)
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)
    for path, meta in pages(site).items():
        for lang in LANGS:
            target = DIST / PREFIX[lang] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_page(env, site, path, meta, lang, base_url), encoding="utf-8")
    base = base_path.rstrip("/") + "/"
    en, ru = site["ui"]["en"], site["ui"]["ru"]
    not_found = (
        f"<h1>{en['not_found_title']}</h1>"
        f'<p>{en["not_found_text"]} <a href="{base}index.html">{en["not_found_link"]}</a>.</p>'
        f'<p lang="ru">{ru["not_found_text"]} <a href="{base}ru/index.html">{ru["not_found_link"]}</a>.</p>'
    )
    (DIST / "404.html").write_text(
        render(env, site, "en", "", not_found, asset_root=base, page_root=base, title=en["not_found_title"]),
        encoding="utf-8",
    )
    return site


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-path", default="", help="path of the site on its host, e.g. /orthodox-nz-temp")
    parser.add_argument("--base-url", default="", help="full address of the site, for the hreflang alternates")
    args = parser.parse_args()
    build(args.base_path, args.base_url)
    print(f"build: wrote {sum(1 for p in DIST.rglob('*.html'))} pages to {DIST.relative_to(ROOT)}/")
