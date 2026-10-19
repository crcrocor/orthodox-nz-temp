"""Build the site and check it; the one command that decides "done". Exit code 1 on any failure.

Usage: uv run scripts/check.py [--base-path /orthodox-nz-temp] [--base-url https://crcrocor.github.io/orthodox-nz-temp]

Checks: every path in old_paths.txt exists; nothing points at orthodox.net.nz; no third-party resources,
scripts or forms; every internal link is relative and resolves; the CSS and font budgets; page structure, heading
order, language marking, the language switch and the footer of both versions; known stale facts are gone
and required facts are present. Then
lists every TODO(content) and "needs blessing:" marker.
"""

import argparse
import gzip
import posixpath
import re
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup, Comment

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import CONTENT, CYRILLIC, DIST, ROOT, STATIC, build, effective_lang  # noqa: E402

# Budgets per page (orthodox-nz docs/design/compat.md): CSS in gzip bytes; fonts at most two families and
# four WOFF2 files of this site, with their licence beside them. The JS budget (50 KB) needs no measuring:
# any <script> fails the check.
CSS_BUDGET = 40 * 1024
FONT_FAMILIES = 2
FONT_FILES = 4
FONT_LICENCES = ("OFL.txt",)
OLD_DOMAIN = "orthodox.net.nz"
RESOURCE_ATTRS = ("src", "srcset", "poster", "data", "background", "action", "formaction")
FORBIDDEN_TAGS = ("script", "form", "iframe", "object", "embed", "audio", "video", "source", "track", "base",
                  "input", "button", "select", "textarea", "frame", "frameset", "applet", "portal", "svg")
LINK_SCHEMES = ("http", "https", "mailto", "tel")
GENERIC_ALT = {"", "image", "img", "photo", "picture"}
STALE = [  # case-insensitive patterns
    r"m(oun)?t\.?\s+albert",
    r"taylors",
    r"frvlad@",
    r"auckland\s+1025",
    r"Митрополит Иларион \(Капраль\) является Первоиерархом",
    r"Metropolitan Hilarion \(Kapral\), is the First Hierarch",
]
PURPOSE = (
    "A church community created and maintained to serve the spiritual needs of the Russian Orthodox community "
    "on the greater Auckland area, with some outreach into the broader community. Where possible, material aid "
    "is also proffered."
)
REGISTER = ["https://register.charities.govt.nz/Charity/CC42458", "https://register.charities.govt.nz/Charity/CC33927"]
CONTACTS = ["455–461 Dominion Rd", "Mt Eden, Auckland 1024", "+64 21 260 9247", "mailto:info@orthodox.nz"]
REQUIRED = {
    "index.html": ["New Zealand Deanery of the Russian Orthodox Church Outside of Russia", "Archbishop George (Schaefer)"],
    "ru/index.html": ["Новозеландское благочиние", "архиепископ Георгий (Шефер)"],
    "clergy.html": ["Archbishop George (Schaefer)", "Metropolitan Nicholas (Olhovsky)"],
    "ru/clergy.html": ["Архиепископ Георгий (Шефер)", "Митрополит Николай (Ольховский)"],
    "about.html": [PURPOSE, *REGISTER, "455–461 Dominion Rd", "info@orthodox.nz", "New Zealand Deanery"],
    "ru/about.html": [*REGISTER, "455–461 Dominion Rd", "info@orthodox.nz", "Новозеландского благочиния"],
    "contact.html": CONTACTS,
    "ru/contact.html": CONTACTS,
    "privacy.html": ["info@orthodox.nz", "GitHub Pages"],
    "ru/privacy.html": ["info@orthodox.nz", "GitHub Pages"],
}
MARKER = re.compile(r"(TODO\(content\)|needs blessing):\s*(.*)", re.S)


class Report:
    def __init__(self):
        self.failures = []
        self.notes = []

    def fail(self, page, message):
        self.failures.append(f"{page}: {message}")

    def note(self, message):
        self.notes.append(message)


def is_local(url):
    parts = urllib.parse.urlsplit(url)
    return not parts.scheme and not parts.netloc and not url.startswith("//")


def resolve(url, page, base_path):
    """dist path of a local URL as seen from page, or None for a same-page anchor."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parts.path)  # not unquote_plus: '+' in article names is literal
    if not path:
        return None
    if path.startswith("/"):
        if base_path and not path.startswith(base_path.rstrip("/") + "/"):
            return "(outside the site) " + path
        path = path[len(base_path.rstrip("/")):].lstrip("/")
    else:
        path = posixpath.normpath(posixpath.join(posixpath.dirname(page), path))
    if path.endswith("/") or path in (".", ""):
        path = posixpath.join(path, "index.html")
    return path


def css_urls(css):
    return re.findall(r"url\(\s*['\"]?([^'\")]+)", css) + re.findall(r"@import\s+['\"]([^'\"]+)", css)


def check_css_file(path, report):
    """Check a stylesheet; return the dist paths it loads (fonts), which count as linked."""
    css = path.read_text(encoding="utf-8")
    rel = path.relative_to(DIST).as_posix()
    if OLD_DOMAIN in css:
        report.fail(rel, f"mentions {OLD_DOMAIN}")
    loaded = set()
    for url in css_urls(css):
        if not is_local(url) and not url.startswith("data:"):
            report.fail(rel, f"loads a third-party resource: {url}")
        elif is_local(url):
            target = resolve(url, rel, "")
            if not target or not (DIST / target).is_file():
                report.fail(rel, f"points to a missing file: {url}")
            else:
                loaded.add(target)
    # Web fonts: WOFF2 files of this site only, within the budget, each with its licence beside it.
    # A face with only local() sources (a metric-matched fallback) downloads nothing and does not count.
    families, files = set(), set()
    for face in re.findall(r"@font-face\s*{([^}]*)}", css):
        urls = css_urls(face)
        if not urls:
            continue
        family = re.search(r"font-family:\s*['\"]?([^'\";]+)", face)
        families.add(family.group(1).strip() if family else "?")
        for url in urls:
            target = resolve(url, rel, "") if is_local(url) else None
            if not target or not target.endswith(".woff2"):
                report.fail(rel, f"@font-face must use a WOFF2 file of this site: {url}")
                continue
            files.add(target)
            folder = posixpath.dirname(target)
            licences = [posixpath.join(folder, name) for name in FONT_LICENCES]
            if not any((DIST / lic).is_file() for lic in licences):
                report.fail(rel, f"font {target} has no licence ({' or '.join(FONT_LICENCES)}) beside it")
            loaded.update(lic for lic in licences if (DIST / lic).is_file())
    if len(families) > FONT_FAMILIES:
        report.fail(rel, f"{len(families)} font families > budget {FONT_FAMILIES}: {', '.join(sorted(families))}")
    if len(files) > FONT_FILES:
        report.fail(rel, f"{len(files)} WOFF2 files > budget {FONT_FILES}")
    return loaded


def check_page(path, html, report, base_path, is_404=False, base_url=""):
    """Check one built page; the 404 page alone uses links from the site root (GitHub serves it at any depth)."""
    page = path.relative_to(DIST).as_posix()
    soup = BeautifulSoup(html, "html.parser")
    css_bytes = img_bytes = 0

    if OLD_DOMAIN in html.lower():
        report.fail(page, f"mentions {OLD_DOMAIN}")
    for pattern in STALE:
        if re.search(pattern, html, re.I):
            report.fail(page, f"stale fact still present: {pattern!r}")

    for tag in soup.find_all(FORBIDDEN_TAGS):
        report.fail(page, f"<{tag.name}> is not allowed (no scripts, forms or embeds)")
    for meta in soup.find_all("meta", attrs={"http-equiv": re.compile("refresh", re.I)}):
        report.fail(page, "meta refresh is not allowed")
    for tag in soup.find_all(True):
        for attr in RESOURCE_ATTRS:
            value = tag.get(attr)
            if value is None:
                continue
            urls = [u.strip().split(" ")[0] for u in value.split(",")] if attr == "srcset" else [value]
            for url in urls:
                if not is_local(url) and not url.startswith("data:"):
                    report.fail(page, f"<{tag.name} {attr}> loads a third-party resource: {url}")
                elif url.startswith("/") and not is_404:
                    report.fail(page, f"<{tag.name} {attr}> must be relative: {url}")
                elif attr in ("src", "srcset", "poster", "data", "background"):
                    target = resolve(url, page, base_path)
                    if target and not (DIST / target).is_file():
                        report.fail(page, f"<{tag.name} {attr}> points to a missing file: {url}")
                    elif target and tag.name == "img":
                        img_bytes += (DIST / target).stat().st_size
        style = tag.get("style", "")
        for url in css_urls(style):
            if not is_local(url):
                report.fail(page, f"inline style loads a third-party resource: {url}")
        if any(k.startswith("on") for k in tag.attrs):
            report.fail(page, f"<{tag.name}> has an inline event handler (no JS)")
    for style in soup.find_all("style"):
        check_inline = style.get_text()
        css_bytes += len(gzip.compress(check_inline.encode()))
        for url in css_urls(check_inline):
            if not is_local(url):
                report.fail(page, f"<style> loads a third-party resource: {url}")
        if "@font-face" in check_inline:
            report.fail(page, "@font-face belongs in css/site.css, where its budget is checked")

    for link in soup.find_all("link"):
        href = link.get("href", "")
        if base_url and "alternate" in (link.get("rel") or []) and href.startswith(base_url.rstrip("/") + "/"):
            target = href[len(base_url.rstrip("/")) + 1:] or "index.html"
            if target.endswith("/"):
                target += "index.html"
            if not (DIST / target).is_file():
                report.fail(page, f"hreflang alternate points to a missing page: {href}")
            continue
        if not is_local(href):
            report.fail(page, f"<link rel={link.get('rel')}> points to another site: {href}")
            continue
        if href.startswith("/") and not is_404:
            report.fail(page, f"<link> must be relative: {href}")
        target = resolve(href, page, base_path)
        if not target or not (DIST / target).is_file():
            report.fail(page, f"<link> points to a missing file: {href}")
        elif "stylesheet" in (link.get("rel") or []):
            css_bytes += len(gzip.compress((DIST / target).read_bytes()))

    ids = {t["id"] for t in soup.find_all(id=True)}
    for a in soup.find_all("a"):
        href = a.get("href")
        if href is None:
            report.fail(page, f"<a> without href: {a.get_text(' ', strip=True)[:60]!r}")
            continue
        scheme = urllib.parse.urlsplit(href).scheme
        if href.startswith("//") or (scheme and scheme not in LINK_SCHEMES):
            report.fail(page, f"link with a disallowed scheme: {href}")
            continue
        if scheme:
            continue
        if href.startswith("#"):
            if href[1:] and href[1:] not in ids:
                report.fail(page, f"anchor {href} has no target")
            continue
        if href.startswith("/") and not is_404:
            report.fail(page, f"links must be relative (the site lives under a path on github.io): {href}")
        target = resolve(href, page, base_path)
        if target and not (DIST / target).is_file():
            report.fail(page, f"broken link: {href}")
        # Inside a language version, links to pages stay in that version; only the switch crosses over.
        if target and target.endswith(".html") and not is_404 and "lang-switch" not in (a.get("class") or []):
            if page.startswith("ru/") != target.startswith("ru/"):
                report.fail(page, f"link leaves the {'Russian' if page.startswith('ru/') else 'English'} version: {href}")
        if not a.get_text(strip=True) and not a.find("img"):
            report.fail(page, f"empty link: {href}")

    if css_bytes > CSS_BUDGET:
        report.fail(page, f"CSS {css_bytes} B gzip > budget {CSS_BUDGET} B")

    main = soup.find("main")
    level = 1
    for h in main.find_all(re.compile(r"^h[1-6]$")) if main else []:
        new = int(h.name[1])
        if new > level + 1:
            report.fail(page, f"heading skips a level: <{h.name}> {h.get_text(' ', strip=True)[:50]!r} after <h{level}>")
        level = new
    for text in soup.body.find_all(string=CYRILLIC) if soup.body else []:
        if isinstance(text, Comment):
            continue
        holder = text.find_parent(lambda t: t.has_attr("lang"))
        if (holder["lang"] if holder else "") != "ru" and CYRILLIC.search(text):
            report.fail(page, f"Russian text without lang=\"ru\": {text.strip()[:50]!r}")
    if page.startswith("ru/") and soup.body:
        for text in soup.body.find_all(string=re.compile(r"[A-Za-z]{3,}")):
            if not isinstance(text, Comment) and effective_lang(text, "ru") == "ru":
                report.fail(page, f"Latin-script text without its lang on a Russian page: {text.strip()[:50]!r}")
    for img in soup.find_all("img", alt=CYRILLIC):
        holder = img if img.has_attr("lang") else img.find_parent(lambda t: t.has_attr("lang"))
        if (holder["lang"] if holder else "") != "ru":
            report.fail(page, f"Russian alt text without lang=\"ru\": {img['alt'][:50]!r}")

    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        report.fail(page, f"{len(h1s)} <h1> elements, expected 1")
    if not soup.html or not soup.html.get("lang"):
        report.fail(page, "<html> has no lang")
    if not soup.find("meta", attrs={"name": "viewport"}):
        report.fail(page, "no viewport meta")
    if not soup.title or not soup.title.get_text(strip=True):
        report.fail(page, "no <title>")
    for img in soup.find_all("img"):
        if img.get("alt") is None or img["alt"].strip().lower() in GENERIC_ALT:
            report.fail(page, f"<img src={img.get('src')}> needs a real alt text")
        if not img.get("width") or not img.get("height"):
            report.fail(page, f"<img src={img.get('src')}> needs width and height")

    footer = soup.find("footer")
    footer_text = footer.get_text(" ") if footer else ""
    if "Church of the Resurrection of Christ Russian Orthodox Church Abroad Trust" not in footer_text:
        report.fail(page, "footer lacks the legal name")
    if not footer or not footer.find("a", href="https://register.charities.govt.nz/Charity/CC42458", string="CC42458"):
        report.fail(page, "footer lacks CC42458 linked to the Charities Register")
    version = "ru" if page.startswith("ru/") else "en"
    prefix = "ru/" if version == "ru" else ""
    for name in ("about.html", "contact.html", "privacy.html"):
        if not footer or not any(
            resolve(a["href"], page, base_path) == prefix + name
            for a in footer.find_all("a", href=True) if is_local(a["href"])
        ):
            report.fail(page, f"footer lacks a link to {prefix + name}")

    if soup.html and soup.html.get("lang") != version and not is_404:
        report.fail(page, f'<html lang="{soup.html.get("lang")}"> on the {version} version')
    switch = soup.find("a", class_="lang-switch")
    counterpart = ("index.html" if is_404 else page.removeprefix("ru/")) if version == "ru" or is_404 else "ru/" + page
    if is_404:
        counterpart = "ru/index.html"
    if not switch or resolve(switch["href"], page, base_path) != counterpart:
        report.fail(page, f"the language switch must lead to {counterpart}")
    elif not (DIST / counterpart).is_file():
        report.fail(page, f"the language switch leads to a missing page {counterpart}")

    text = " ".join(soup.get_text(" ").split())
    for needle in REQUIRED.get(page, []):
        if needle not in html and needle not in text:
            report.fail(page, f"required text missing: {needle[:70]!r}")
    return img_bytes


def markers():
    found = defaultdict(list)
    for path in sorted(CONTENT.rglob("*.html")):
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
            m = MARKER.search(c)
            if m:
                found[(m.group(1), " ".join(m.group(2).split()))].append(path.relative_to(CONTENT).as_posix())
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-path", default="", help="path of the site on its host, e.g. /orthodox-nz-temp")
    parser.add_argument("--base-url", default="", help="full address of the site, for the hreflang alternates")
    args = parser.parse_args()
    base_path, base_url = args.base_path.rstrip("/"), args.base_url
    build(base_path, base_url)
    report = Report()

    # old_paths.txt only grows (scripts/mirror.py adds to it), so a page or file that once existed
    # cannot silently disappear.
    for path in [*(ROOT / "old_paths.txt").read_text(encoding="utf-8").split(), "404.html"]:
        if not (DIST / path).is_file():
            report.fail(path, "missing in dist/ (listed in old_paths.txt)")

    weights = []
    for html_path in sorted(DIST.rglob("*.html")):
        is_404 = html_path == DIST / "404.html"
        img = check_page(html_path, html_path.read_text(encoding="utf-8"), report, base_path if is_404 else "", is_404,
                         base_url)
        weights.append((img, html_path.relative_to(DIST).as_posix()))
    loaded_by_css = set()
    for css in sorted(DIST.rglob("*.css")):
        loaded_by_css |= check_css_file(css, report)

    for pdf in sorted(DIST.rglob("*.pdf")):
        if OLD_DOMAIN.encode() in pdf.read_bytes():
            report.note(f"{pdf.relative_to(DIST)} mentions {OLD_DOMAIN} inside the PDF (cannot be fixed here)")
    used = set(loaded_by_css)
    for html_path in DIST.rglob("*.html"):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        for el in soup.find_all(["a", "img", "link"]):
            ref = el.get("href") or el.get("src") or ""
            if ref and is_local(ref) and not ref.startswith("#"):
                used.add(resolve(ref, html_path.relative_to(DIST).as_posix(), ""))
    for f in sorted(STATIC.rglob("*")):
        rel = f.relative_to(STATIC).as_posix()
        if f.is_file() and rel not in used:
            report.note(f"static/{rel} is not linked from any page")

    print(f"check: {len(weights)} pages in dist/")
    heaviest = sorted(weights, reverse=True)[:3]
    print("check: heaviest pages by images: " + ", ".join(f"{p} {w // 1024} KB" for w, p in heaviest))
    for note in report.notes:
        print(f"note: {note}")

    found = markers()
    print(f"\nOpen items ({len(found)}):")
    for (kind, text), where in sorted(found.items()):
        print(f"- {kind}: {text} [{', '.join(where)}]")

    if report.failures:
        print(f"\ncheck: FAILED ({len(report.failures)})")
        for f in report.failures:
            print(f"  {f}")
        sys.exit(1)
    print("\ncheck: OK")


if __name__ == "__main__":
    main()
