"""Mirror orthodox.net.nz into content/pages/ and static/ (network, run by hand).

Usage: uv run scripts/mirror.py [--offline]

Raw responses are cached in .cache/mirror/, so re-running only re-fetches what is not cached; delete the
cache to pick up changes on the old site. --offline uses the cache only (for tuning the cleanup rules).
Pages of kind "mirror" are rewritten every run; "frozen" pages are written only when missing, and a
warning says when their source on the old site has changed since (compared by a hash in their first line).
Every correction in scripts/corrections.py must match exactly as often as it says, otherwise the mirror
stops. Nothing is ever deleted: pages and files the old site no longer links to stay (old paths keep
working) and are only reported. Every path the site has ever had is recorded in old_paths.txt, which
scripts/check.py requires to exist.
"""

import argparse
import codecs
import hashlib
import json
import posixpath
import re
import struct
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corrections import CORRECTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "pages"
STATIC = ROOT / "static"
CACHE = ROOT / ".cache" / "mirror"
OLD_PATHS = ROOT / "old_paths.txt"
OLD_HOSTS = {"orthodox.net.nz", "www.orthodox.net.nz"}
# Images of ours hosted by Orthodox Web Solutions' image archive (the icon on the home page).
OWS_IMAGES = "images.orthodoxws.com"
USER_AGENT = "orthodox-nz-temp mirror (+https://github.com/crcrocor/orthodox-nz-temp)"
# The parish owns the old site, so we skip the crawl-delay of 60 s that OWS sets for search engines
# and only pause between requests.
DELAY = 2.0
SITE_SUFFIX = " | Resurrection of Christ Russian Orthodox Church"
NOT_FOUND = "The page you are looking for was not found"
ASSET_DIRS = ("/files/", "/images/", "/cache/images/")
SIGNATURES = {
    ".pdf": [b"%PDF-"],
    ".jpg": [b"\xff\xd8"],
    ".jpeg": [b"\xff\xd8"],
    ".png": [b"\x89PNG"],
    ".gif": [b"GIF8"],
}
AUDIO = (".m4a", ".mp3")
TODO_AUDIO = "audio recording {name} not moved to the new site yet (decided 2026-10-19); link removed"
TODO_AUDIO_BROKEN = "audio link to {name} was already broken on the old site; link removed"
TODO_BROKEN = "this link was already broken on the old site ({url}); link removed"
MAX_WORD_LOSS = 0.05
# Responses worth caching; anything else (rate limits, server errors) is retried and then stops the mirror,
# so a passing outage never turns a bulletin into a "missing" file.
FINAL_STATUSES = {200, 404, 410}
RETRIES = 3

# The old pages are UTF-8 with a few stray Windows-1252 bytes (an em dash in a CSS comment, a » in one
# article); decode those as Windows-1252 so they become visible text that corrections.py can fix.
codecs.register_error("cp1252", lambda e: (e.object[e.start:e.end].decode("cp1252", errors="replace"), e.end))

BLOCK = {
    "p", "div", "table", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "figure",
    "figcaption", "hr", "tbody", "thead", "tr", "td", "th", "dl", "dt", "dd", "pre", "center",
}
DROP = {
    "script", "style", "noscript", "form", "input", "button", "select", "textarea", "iframe", "object",
    "embed", "head", "title", "meta", "link", "audio", "video", "source", "map", "area", "svg",
}
# Dropped elements that carried content a visitor saw; each leaves a TODO.
EMBEDS = {"iframe", "object", "embed", "audio", "video"}
UNWRAP = {"font", "span", "center", "html", "body", "small", "big", "sup", "sub", "nobr", "o:p", "abbr"}
KEEP_ATTRS = {"a": {"href"}, "img": {"src", "alt", "width", "height"}, "td": {"colspan", "rowspan"},
              "th": {"colspan", "rowspan"}, "ol": {"start"}}
# Bright red inline colour marked sub-headings on the old site; the dark red body text (#550000) is not one.
RED = re.compile(r"(color\s*:\s*)?(\bred\b|#[89a-f][0-9a-f]0000\b|#[c-f]00\b)", re.I)


class Mirror:
    def __init__(self, offline):
        self.offline = offline
        self.last_request = 0.0
        self.site = tomllib.loads((ROOT / "site.toml").read_text(encoding="utf-8"))
        self.by_source = {meta["source"].strip("/").removesuffix(".html"): path
                          for path, meta in self.site["pages"].items() if "source" in meta}
        self.articles = {}  # article/<name>.html -> /article/<name>
        self.assets = {}  # static path -> list of (page, link text)
        self.missing = set()
        self.warnings = []

    # --- network and cache -------------------------------------------------------------------

    def fetch(self, url):
        """(status, body) for a URL, from the cache when possible."""
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        body_file, meta_file = CACHE / key, CACHE / f"{key}.json"
        if meta_file.exists():
            return json.loads(meta_file.read_text())["status"], body_file.read_bytes()
        if self.offline:
            sys.exit(f"mirror: {url} is not cached; run without --offline")
        status, body = self.request(url, "GET")
        CACHE.mkdir(parents=True, exist_ok=True)
        body_file.write_bytes(body)
        meta_file.write_text(json.dumps({"url": url, "status": status}))
        print(f"  fetched {status} {url}")
        return status, body

    def exists(self, url):
        """HEAD request, cached: audio files are too big to download just to see that they exist."""
        key = "head-" + hashlib.sha256(url.encode()).hexdigest()[:24]
        meta_file = CACHE / f"{key}.json"
        if meta_file.exists():
            return json.loads(meta_file.read_text())["status"] == 200
        if self.offline:
            sys.exit(f"mirror: HEAD {url} is not cached; run without --offline")
        status, _ = self.request(url, "HEAD")
        CACHE.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(json.dumps({"url": url, "status": status}))
        print(f"  checked {status} {url}")
        return status == 200

    def request(self, url, method):
        """(status, body), retrying rate limits, server errors and network failures."""
        for attempt in range(1, RETRIES + 1):
            wait = DELAY * attempt - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    status, body = response.status, response.read()
                    if method == "HEAD" and "text/html" in response.headers.get("Content-Type", ""):
                        status = 404  # the old site answers a missing file with its HTML error page
            except urllib.error.HTTPError as e:
                status, body = e.code, e.read()
            except (urllib.error.URLError, TimeoutError) as e:
                status, body = None, str(e).encode()
            self.last_request = time.monotonic()
            if status in FINAL_STATUSES:
                return status, body
            print(f"  attempt {attempt}: {status or body.decode()} for {url}")
        sys.exit(f"mirror: the old site keeps failing for {url} (last: {status}); try again later")

    def fetch_page(self, path):
        status, body = self.fetch(self.site["site"]["old_site"] + path)
        text = body.decode("utf-8", errors="cp1252")
        if status != 200 or NOT_FOUND in text:
            sys.exit(f"mirror: {path} is missing on the old site (HTTP {status})")
        return text

    def fetch_asset(self, url, target):
        """Download an asset into static/; False when the old site does not have it."""
        if target in self.missing:
            return False
        status, body = self.fetch(url)
        signatures = SIGNATURES.get(Path(target).suffix.lower())
        looks_html = body[:400].lstrip().lower().startswith((b"<!doctype", b"<html"))
        if status != 200 or (signatures and not body.startswith(tuple(signatures))) or (
            not signatures and looks_html
        ):
            self.missing.add(target)
            return False
        out = STATIC / target
        if not out.exists() or out.read_bytes() != body:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(body)
        return True

    # --- links ------------------------------------------------------------------------------

    def resolve(self, url, page):
        """Map a URL of the old site to a path of the new one; None when it has no new counterpart.

        Returns (kind, value): ("external", url), ("page", path), ("asset", path), ("audio", name),
        ("broken", url) or ("drop", None).
        """
        url = url.strip()
        if not url or url.startswith(("javascript:", "#")) or url == "mailto":
            return "drop", None
        parts = urllib.parse.urlsplit(url)
        if parts.scheme == "tel":
            return "external", "tel:" + url[4:].lstrip("/").replace(" ", "")
        if parts.scheme in ("mailto",):
            return "external", url
        if parts.netloc == OWS_IMAGES:
            target = "images/orthodoxws/" + posixpath.basename(parts.path)
            return ("asset", target) if self.fetch_asset(url, target) else ("broken", url)
        if parts.netloc.endswith("webmail2.ec.auckland.ac.nz"):
            target = urllib.parse.parse_qs(parts.query).get("url", [""])[0]
            return ("external", target) if target else ("drop", None)
        if parts.netloc and parts.netloc not in OLD_HOSTS:
            return "external", url
        if parts.scheme and parts.scheme not in ("http", "https"):
            return "external", url
        path = urllib.parse.unquote(parts.path) if parts.netloc or parts.path.startswith("/") else (
            "/" + parts.path
        )
        if path.lower().endswith(AUDIO):
            exists = self.exists(self.site["site"]["old_site"] + urllib.parse.quote(path))
            return ("audio" if exists else "broken-audio"), posixpath.basename(path)
        if path.startswith(ASSET_DIRS):
            target = path.lstrip("/")
            if self.fetch_asset(self.site["site"]["old_site"] + urllib.parse.quote(path), target):
                return "asset", target
            return "broken", url
        if path.startswith("/article/"):
            name = path[len("/article/"):].replace(" ", "+")
            new = f"article/{name}.html"
            self.articles[new] = "/article/" + urllib.parse.quote(name, safe="+-")
            return "page", new
        key = path.strip("/").removesuffix(".html")
        if key in ("home", "index"):
            key = ""
        if key in self.by_source:
            return "page", self.by_source[key]
        status, body = self.fetch(self.site["site"]["old_site"] + urllib.parse.quote(path))
        if status == 200 and NOT_FOUND.encode() not in body:
            sys.exit(f"mirror: {page} links to {path}, a page of the old site that site.toml does not list; add it")
        return "broken", path

    def rewrite_links(self, root, page):
        for a in root.find_all("a"):
            href = a.get("href")
            if href is None:
                a.unwrap()
                continue
            kind, value = self.resolve(href, page)
            text = " ".join(a.get_text(" ").split())
            if kind in ("page", "asset"):
                a["href"] = relative(value, page)
                if kind == "asset":
                    self.assets.setdefault(value, []).append((page, text))
            elif kind == "external":
                a["href"] = value
            else:
                if kind == "audio":
                    a.insert_after(Comment(f" TODO(content): {TODO_AUDIO.format(name=value)} "))
                elif kind == "broken-audio":
                    a.insert_after(Comment(f" TODO(content): {TODO_AUDIO_BROKEN.format(name=value)} "))
                elif kind == "broken":
                    path = urllib.parse.urlsplit(href).path or href
                    a.insert_after(Comment(f" TODO(content): {TODO_BROKEN.format(url=path)} "))
                a.unwrap()

    def rewrite_images(self, root, page):
        for img in root.find_all("img"):
            kind, target = self.resolve(img.get("src", ""), page)
            if kind != "asset":
                if kind == "external":
                    self.warnings.append(f"{page}: removed a third-party image {target}")
                parent = img.parent
                img.decompose()
                if parent and parent.name == "a" and not has_content(parent):
                    parent.decompose()
                continue
            img["src"] = relative(target, page)
            size = image_size(STATIC / target)
            if size:
                img["width"], img["height"] = str(size[0]), str(size[1])
            if img.get("alt", "").strip().lower() in ("", "image"):
                heading = img.find_previous(["h2", "h3"])
                if heading:
                    img["alt"] = " ".join(heading.get_text(" ").split())
                else:
                    img["alt"] = ""
                    img.insert_after(Comment(" TODO(content): alt text for this image "))
            img["loading"] = "lazy"

    # --- pages ------------------------------------------------------------------------------

    def extract(self, html, page, is_article):
        soup = BeautifulSoup(html, "html5lib")
        if is_article:
            title_cell = soup.find("td", class_="PARAGRAPH_TITLE")
            if title_cell is None:
                sys.exit(f"mirror: {page}: no PARAGRAPH_TITLE cell")
            h1 = " ".join(title_cell.get_text(" ").split())
            root = soup.new_tag("div")
            for cell in soup.find_all("td", class_="PARAGRAPH_TEXT"):
                for child in list(cell.contents):
                    root.append(child.extract())
        else:
            root = soup.find(id="main_content_container_inside_div")
            if root is None:
                sys.exit(f"mirror: {page}: no #main_content_container_inside_div")
            title = soup.title.get_text().strip() if soup.title else ""
            h1 = self.site["pages"][page].get("h1") or title.removesuffix(SITE_SUFFIX.strip()).removesuffix(
                SITE_SUFFIX
            ).strip(" |")
        return soup, root, h1

    def source_hash(self, page, source):
        """Hash of the old page's content area, which is what a frozen page was seeded from."""
        _, root, _ = self.extract(self.fetch_page(source), page, False)
        return hashlib.sha256(str(root).encode()).hexdigest()[:16]

    def mirror_page(self, page, source, is_article=False):
        html = self.fetch_page(source)
        soup, root, h1 = self.extract(html, page, is_article)
        old_words = count_words(visible_text(root))
        clean(soup, root, page)
        self.rewrite_images(root, page)
        self.rewrite_links(root, page)
        finish(soup, root)
        body = serialize(root)
        if "�" in body:
            sys.exit(f"mirror: {page}: the extracted text contains U+FFFD (bad encoding)")
        fragment = f"<h1>{escape(h1)}</h1>\n{body}\n"
        fragment = apply_corrections(page, fragment)
        new_words = count_words(BeautifulSoup(fragment, "html.parser").get_text(" ")) - count_words(h1)
        return fragment, old_words, new_words

    def run(self):
        fragments, report = {}, []
        for path, meta in self.site["pages"].items():
            if "source" not in meta:
                continue
            if meta["kind"] == "frozen" and (CONTENT / path).exists():
                first = (CONTENT / path).read_text(encoding="utf-8").split("\n", 1)[0]
                now = self.source_hash(path, meta["source"])
                if now not in first:
                    self.warnings.append(
                        f"{path} is frozen but its source changed on the old site (now sha256 {now}); "
                        "merge the change by hand, then put that hash in its first line"
                    )
                continue
            fragments[path], old, new = self.mirror_page(path, meta["source"])
            report.append((path, old, new, meta["kind"]))
        for path, source in sorted(self.articles.items()):
            fragments[path], old, new = self.mirror_page(path, source, is_article=True)
            report.append((path, old, new, "mirror"))
        for path, note in self.shared_file_notes(fragments):
            fragments[path] = fragments[path].rstrip("\n") + f"\n<!-- TODO(content): {note} -->\n"

        print(f"\n{'page':48} {'old':>6} {'new':>6}  change")
        failed = False
        for path, old, new, kind in report:
            change = (new - old) / old if old else 0
            flag = ""
            if change < -MAX_WORD_LOSS and kind == "mirror":
                flag, failed = "  <-- text lost", True
            print(f"{path:48} {old:6} {new:6}  {change:+.1%}{flag}")
        if failed:
            sys.exit("mirror: some pages lost more than 5% of their words; nothing written; check the cleanup rules")

        for path, fragment in fragments.items():
            self.write(path, self.site["pages"].get(path, {"kind": "mirror"})["kind"], fragment)
        for p in sorted((CONTENT / "article").glob("*.html")):
            if p.relative_to(CONTENT).as_posix() not in self.articles:
                self.warnings.append(f"kept {p.relative_to(CONTENT)}: the old site no longer links to it")
        self.report_unlinked_static()
        self.record_old_paths()
        for w in self.warnings:
            print(f"warning: {w}")
        print(f"\nmirror: {len(report)} pages, {len(self.assets)} files, missing on the old site: {sorted(self.missing)}")

    def write(self, path, kind, fragment):
        out = CONTENT / path
        if kind == "frozen":
            source = self.site["pages"][path]["source"]
            fragment = f"<!-- frozen copy of {source}, source sha256 {self.source_hash(path, source)} -->\n" + fragment
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists() or out.read_text(encoding="utf-8") != fragment:
            out.write_text(fragment, encoding="utf-8")

    def report_unlinked_static(self):
        """Files no page links to any more stay, so their old URLs keep working; just say so."""
        for rel in sorted({r for r in static_files() if not r.startswith("css/")} - linked_paths()):
            self.warnings.append(f"kept static/{rel}: no page links to it any more")

    def record_old_paths(self):
        """Add every page and file path of the site to old_paths.txt; paths are never removed from it."""
        known = set(OLD_PATHS.read_text(encoding="utf-8").split()) if OLD_PATHS.exists() else set()
        current = {p.relative_to(CONTENT).as_posix() for p in CONTENT.rglob("*.html")}
        for meta in self.site["pages"].values():
            current.update(meta.get("aliases", []))
        current.update(rel for rel in static_files() if not rel.startswith("css/"))
        if not current <= known:
            OLD_PATHS.write_text("\n".join(sorted(known | current)) + "\n", encoding="utf-8")

    def shared_file_notes(self, fragments):
        """One file linked under different names is probably a wrong upload on the old site."""
        for target, all_uses in sorted(self.assets.items()):
            # A correction may already have removed one of the links.
            uses = [(page, text) for page, text in all_uses
                    if f'href="{relative(target, page)}"' in fragments.get(page, "")]
            if len({text for _, text in uses if text}) > 1:
                where = "; ".join(f"{page}: '{text}'" for page, text in uses)
                note = f"{target} is linked as different documents ({where}); check which one it is"
                self.warnings.append(note)
                for page in sorted({page for page, _ in uses}):
                    yield page, note


def static_files():
    return [f.relative_to(STATIC).as_posix() for f in STATIC.rglob("*") if f.is_file()]


def linked_paths():
    """Every local path the pages in content/pages/ link to."""
    used = set()
    for page in CONTENT.rglob("*.html"):
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        base = posixpath.dirname(page.relative_to(CONTENT).as_posix())
        for el in soup.find_all(["a", "img"]):
            ref = el.get("href") or el.get("src") or ""
            if ref and not urllib.parse.urlsplit(ref).scheme and not ref.startswith("#"):
                used.add(posixpath.normpath(posixpath.join(base, urllib.parse.unquote(ref))))
    return used


# --- cleanup ----------------------------------------------------------------------------------


def visible_text(root):
    """The text a visitor of the old page saw, for the word count."""
    copy = BeautifulSoup(str(root), "html5lib")
    for tag in copy.find_all(DROP):
        tag.decompose()
    for tag in copy.find_all(class_="highslide-caption"):
        tag.decompose()
    for tag in copy.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        tag.decompose()
    return copy.get_text(" ")


def count_words(text):
    return len(re.findall(r"\w+", text))


def clean(soup, root, page):
    for c in root.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for tag in root.find_all(EMBEDS):
        src = tag.get("src") or tag.get("data") or (tag.find("source") or {}).get("src", "")
        tag.insert_before(Comment(f" TODO(content): embedded <{tag.name}> {src} removed (no third-party resources) "))
    for tag in root.find_all(DROP):
        tag.decompose()
    # Articles use h4/h5 for their sections; renumber the levels a page uses from h2 down, so the
    # outline has no gaps (menu pages have no headings of their own: their titles are converted below).
    used = sorted({el.name for el in root.find_all(re.compile(r"^h[1-6]$"))})
    for el in root.find_all(used) if used else []:
        el.name = f"h{min(used.index(el.name) + 2, 4)}"
    for tag in root.find_all(class_="highslide-caption"):
        tag.decompose()
    for tag in root.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        tag.decompose()
    for img in root.find_all("img", src=re.compile(r"^(https?://(www\.)?orthodox\.net\.nz)?/interface/")):
        img.decompose()
    for div in root.find_all(class_="SECTION_TITLE"):
        h2 = soup.new_tag("h2")
        h2.string = " ".join(div.get_text(" ").split())
        div.replace_with(h2)
    for el in root.find_all(class_="PARAGRAPH_TITLE"):
        if el.find_parent(["li", "td", "p"]) or el.name in ("span", "a"):
            el.name = "strong"
        else:
            el.name = "h3"
    for el in root.find_all(["span", "font", "div", "p"], style=True):
        style = el["style"]
        if "underline" in style and not RED.search(style) and (el.find_parent("a") or el.find("a")):
            continue  # Word underlines links; that is not emphasis
        if ("underline" in style or RED.search(style)) and el.get_text(strip=True) and len(el.get_text()) < 160:
            if el.name in ("span", "font"):
                el.name = "strong"
            elif not el.find(BLOCK - {"div", "p"}):
                inner = soup.new_tag("strong")
                for child in list(el.contents):
                    inner.append(child.extract())
                el.append(inner)
    for el in root.find_all(color=RED):
        el.name = "strong"
    for el in root.find_all(["b", "u"]):
        el.name = "strong"
    for el in root.find_all("i"):
        el.name = "em"
    # Attributes go before unwrapping, so nothing of the old styling survives.
    for el in [root, *root.find_all(True)]:
        allowed = KEEP_ATTRS.get(el.name, set())
        el.attrs = {k: v for k, v in el.attrs.items() if k in allowed}
    for el in root.find_all(UNWRAP):
        el.unwrap()
    for table in reversed(root.find_all("table")):
        simplify_table(soup, table)
    for div in reversed(root.find_all("div")):
        flatten_div(soup, div)
    for strong in root.find_all("strong"):
        if strong.find_parent("strong") or strong.find_parent(["h2", "h3", "h4"]):
            strong.unwrap()


def simplify_table(soup, table):
    """Unwrap layout tables; keep tables where rows really have several cells with text."""
    rows = table.find_all("tr")
    multi = sum(1 for tr in rows if sum(1 for td in tr.find_all(["td", "th"], recursive=False)
                                        if td.get_text(strip=True)) >= 2)
    if multi >= 2:
        for el in table.find_all(["tbody", "thead", "tfoot"]):
            el.unwrap()
        return
    container = soup.new_tag("div")
    for cell in table.find_all(["td", "th"]):
        if cell.find_parent("table") is not table:
            continue
        box = soup.new_tag("div")
        for child in list(cell.contents):
            box.append(child.extract())
        container.append(box)
    table.replace_with(container)


def is_inline(node):
    if isinstance(node, Comment):
        return True
    if isinstance(node, NavigableString):
        return True
    return node.name not in BLOCK


def flatten_div(soup, div):
    """Turn a div into paragraphs: inline runs become <p>, block children stay as they are."""
    runs, current = [], []
    for child in list(div.contents):
        if is_inline(child):
            current.append(child)
        else:
            runs.append(current)
            runs.append(child)
            current = []
    runs.append(current)
    if div.parent and div.parent.name in ("li", "td", "th", "figcaption", "blockquote") and all(
        isinstance(r, list) for r in runs
    ):
        div.unwrap()
        return
    replacement = []
    for run in runs:
        if isinstance(run, list):
            if not any(has_content(n) for n in run):
                continue
            for part in split_on_double_br(soup, run):
                p = soup.new_tag("p")
                for node in part:
                    p.append(node.extract())
                replacement.append(p)
        else:
            replacement.append(run.extract())
    for node in replacement:
        div.insert_before(node)
    div.decompose()


def split_on_double_br(soup, nodes):
    """<br><br> inside one run separates paragraphs."""
    parts, current, brs = [], [], 0
    for node in nodes:
        if isinstance(node, Tag) and node.name == "br":
            brs += 1
            current.append(node)
            continue
        if isinstance(node, NavigableString) and not node.strip() and not isinstance(node, Comment):
            current.append(node)
            continue
        if brs >= 2:
            parts.append(current)
            current = []
        brs = 0
        current.append(node)
    parts.append(current)
    return [p for p in parts if any(has_content(n) for n in p)]


def has_content(node):
    if isinstance(node, Comment):
        return False
    if isinstance(node, NavigableString):
        return bool(node.replace("\xa0", " ").strip())
    return bool(node.get_text().replace("\xa0", " ").strip()) or node.find("img") is not None or node.name == "img"


def finish(soup, root):
    """Whitespace, empty elements and stray line breaks."""
    for s in root.find_all(string=True):
        if isinstance(s, Comment):
            continue
        new = re.sub(r"[ \t\r\n\xa0]+", " ", str(s))
        if new != s:
            s.replace_with(new)
    # Inline content left directly in the root becomes paragraphs too.
    wrapper = soup.new_tag("div")
    for child in list(root.contents):
        wrapper.append(child.extract())
    root.append(wrapper)
    flatten_div(soup, wrapper)
    changed = True
    while changed:
        changed = False
        for el in root.find_all(["p", "strong", "em", "a", "li", "ul", "ol", "h2", "h3", "h4", "div", "td", "tr",
                                 "table", "blockquote"]):
            if not has_content(el) and not el.find("hr"):
                comments = [c for c in el.find_all(string=lambda s: isinstance(s, Comment))]
                for c in comments:
                    el.insert_before(c.extract())
                el.decompose()
                changed = True
    for strong in root.find_all("strong"):
        move_edge_breaks_out(strong)
    for p in root.find_all("p"):
        parts = split_on_double_br(soup, list(p.contents))
        for part in reversed(parts[1:]):
            new = soup.new_tag("p")
            for node in part:
                new.append(node.extract())
            p.insert_after(new)
    for block in root.find_all(["p", "li", "td", "h2", "h3", "h4", "strong"]):
        trim_breaks(block)
    for br in root.find_all("br"):
        nxt = br.next_sibling
        while isinstance(nxt, NavigableString) and not nxt.strip() and not isinstance(nxt, Comment):
            nxt = nxt.next_sibling
        if isinstance(nxt, Tag) and nxt.name == "br":
            br.decompose()


def move_edge_breaks_out(el):
    """A <br> at the edge of an inline element separates it from its neighbour: keep it, outside."""
    while True:
        nodes = [n for n in el.contents if has_content(n) or (isinstance(n, Tag) and n.name == "br")]
        if nodes and isinstance(nodes[-1], Tag) and nodes[-1].name == "br":
            el.insert_after(nodes[-1].extract())
        elif nodes and isinstance(nodes[0], Tag) and nodes[0].name == "br":
            el.insert_before(nodes[0].extract())
        else:
            return


def trim_breaks(el):
    """No <br> or spaces at the start or end of a block."""
    for pick in (0, -1):
        while True:
            nodes = [n for n in el.contents if has_content(n) or (isinstance(n, Tag) and n.name in ("br", "img", "hr"))]
            if not nodes or not (isinstance(nodes[pick], Tag) and nodes[pick].name == "br"):
                break
            nodes[pick].decompose()
    texts = [n for n in el.contents if isinstance(n, NavigableString) and not isinstance(n, Comment)]
    if texts and texts[0] is el.contents[0]:
        texts[0].replace_with(texts[0].lstrip())
    texts = [n for n in el.contents if isinstance(n, NavigableString) and not isinstance(n, Comment)]
    if texts and texts[-1] is el.contents[-1]:
        texts[-1].replace_with(texts[-1].rstrip())


def serialize(root):
    out = []
    for child in root.contents:
        if isinstance(child, Comment):
            out.append(f"<!--{child}-->")
        elif isinstance(child, NavigableString):
            if child.strip():
                out.append(str(child).strip())
        else:
            out.append(str(child))
    return "\n".join(out)


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def relative(target, page):
    return posixpath.relpath(target, posixpath.dirname(page) or ".")


def apply_corrections(page, fragment):
    for c in CORRECTIONS:
        if c["page"] != page:
            continue
        found = fragment.count(c["find"])
        if found != c["count"]:
            sys.exit(f"mirror: correction for {page} expects {c['count']} × {c['find']!r}, found {found}")
        fragment = fragment.replace(c["find"], c["replace"])
    return fragment


def image_size(path):
    """(width, height) of a PNG, GIF or JPEG file, read from its header."""
    data = path.read_bytes()
    if data.startswith(b"\x89PNG"):
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"GIF8"):
        return struct.unpack("<HH", data[6:10])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + length
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use the cache only, never the network")
    Mirror(parser.parse_args().offline).run()
