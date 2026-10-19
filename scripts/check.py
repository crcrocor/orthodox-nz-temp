"""Build the site and check it; the one command that decides "done". Exit code 1 on any failure.

Usage: uv run scripts/check.py [--base-path /orthodox-nz-temp]

Checks: every old path exists; nothing points at orthodox.net.nz; no third-party resources, scripts or
forms; every internal link resolves; CSS/JS budgets; page structure and footer; known stale facts are
gone and required facts are present. Then lists every TODO(content) and "needs blessing:" marker.
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
from build import CONTENT, DIST, STATIC, build, pages  # noqa: E402

CSS_BUDGET = 40 * 1024  # gzip bytes per page (orthodox-nz docs/design/compat.md)
JS_BUDGET = 50 * 1024
OLD_DOMAIN = "orthodox.net.nz"
RESOURCE_ATTRS = ("src", "srcset", "poster", "data", "background", "action", "formaction")
FORBIDDEN_TAGS = ("script", "form", "iframe", "object", "embed", "audio", "video", "source", "track", "base",
                  "input", "frame", "frameset", "applet", "portal")
LINK_SCHEMES = ("http", "https", "mailto", "tel")
GENERIC_ALT = {"", "image", "img", "photo", "picture"}
STALE = [
    "Mt Albert",
    "Mount Albert",
    "Taylors",
    "frvlad@",
    "Auckland 1025",
    "Митрополит Иларион (Капраль) является Первоиерархом",
    "Metropolitan Hilarion (Kapral), is the First Hierarch",
]
PURPOSE = (
    "A church community created and maintained to serve the spiritual needs of the Russian Orthodox community "
    "on the greater Auckland area, with some outreach into the broader community. Where possible, material aid "
    "is also proffered."
)
REQUIRED = {
    "clergy.html": ["Archbishop George (Schaefer)", "Архиепископ Георгий (Шефер)", "Metropolitan Nicholas (Olhovsky)"],
    "about.html": [
        PURPOSE,
        "https://register.charities.govt.nz/Charity/CC42458",
        "https://register.charities.govt.nz/Charity/CC33927",
        "455–461 Dominion Rd",
        "info@orthodox.nz",
    ],
    "contact.html": ["455–461 Dominion Rd", "Mt Eden, Auckland 1024", "+64 21 260 9247", "mailto:info@orthodox.nz"],
    "privacy.html": ["info@orthodox.nz", "GitHub Pages"],
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
    css = path.read_text(encoding="utf-8")
    rel = path.relative_to(DIST).as_posix()
    if OLD_DOMAIN in css:
        report.fail(rel, f"mentions {OLD_DOMAIN}")
    if "@font-face" in css:
        report.fail(rel, "@font-face: no web fonts on this site")
    for url in css_urls(css):
        if not is_local(url) and not url.startswith("data:"):
            report.fail(rel, f"loads a third-party resource: {url}")


def check_page(path, html, report, base_path, required_paths):
    page = path.relative_to(DIST).as_posix()
    soup = BeautifulSoup(html, "html.parser")
    css_bytes = js_bytes = img_bytes = 0

    if OLD_DOMAIN in html:
        report.fail(page, f"mentions {OLD_DOMAIN}")
    for text in STALE:
        if text in html:
            report.fail(page, f"stale fact still present: {text!r}")

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
            report.fail(page, "@font-face: no web fonts on this site")

    for link in soup.find_all("link"):
        href = link.get("href", "")
        if not is_local(href):
            report.fail(page, f"<link rel={link.get('rel')}> points to another site: {href}")
            continue
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
        target = resolve(href, page, base_path)
        if target and not (DIST / target).is_file():
            report.fail(page, f"broken link: {href}")
        if not a.get_text(strip=True) and not a.find("img"):
            report.fail(page, f"empty link: {href}")

    if css_bytes > CSS_BUDGET:
        report.fail(page, f"CSS {css_bytes} B gzip > budget {CSS_BUDGET} B")
    if js_bytes > JS_BUDGET:
        report.fail(page, f"JS {js_bytes} B gzip > budget {JS_BUDGET} B")

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
    for name in ("about.html", "contact.html", "privacy.html"):
        if not footer or not any(
            resolve(a["href"], page, base_path) == name for a in footer.find_all("a", href=True) if is_local(a["href"])
        ):
            report.fail(page, f"footer lacks a link to {name}")

    for needle in REQUIRED.get(page, []):
        if needle not in html:
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
    base_path = parser.parse_args().base_path.rstrip("/")
    site = build(base_path)
    report = Report()

    required_paths = set()
    for path, meta in pages(site).items():
        required_paths.add(path)
        required_paths.update(meta.get("aliases", []))
    required_paths.add("404.html")
    for path in sorted(required_paths):
        if not (DIST / path).is_file():
            report.fail(path, "missing in dist/")

    weights = []
    for html_path in sorted(DIST.rglob("*.html")):
        page_base = base_path if html_path.name == "404.html" and html_path.parent == DIST else ""
        img = check_page(html_path, html_path.read_text(encoding="utf-8"), report, page_base, required_paths)
        weights.append((img, html_path.relative_to(DIST).as_posix()))
    for css in sorted(DIST.rglob("*.css")):
        check_css_file(css, report)

    for pdf in sorted(DIST.rglob("*.pdf")):
        if OLD_DOMAIN.encode() in pdf.read_bytes():
            report.note(f"{pdf.relative_to(DIST)} mentions {OLD_DOMAIN} inside the PDF (cannot be fixed here)")
    used = set()
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
