"""Proposed additions to scripts/corrections.py (markup that carries typography). NOT applied.

Run as a script to simulate them on the current content/pages files (which already carry the existing
corrections), in order, with the same exact-count rule as scripts/mirror.py apply_corrections().
"""

from pathlib import Path

# --- bold paragraphs that are headings of the same rank as their neighbours ---------------------------
BOLD_TO_HEADING = [
    ("The+New+Testament.html", "Second Corinthians.", "h2"),
    ("The+New+Testament.html", "Galatians.", "h2"),
    ("The+New+Testament.html", "Ephesians.", "h2"),
    ("The+New+Testament.html", "First Peter.", "h2"),
    ("The+New+Testament.html", "Second John.", "h2"),
    ("A+History+of+the+Orthodox+Church.html", "St. James the Elder.", "h3"),
    ("The+Divine+Liturgy.html", "Liturgy of the Faithful.", "h2"),
    ("The+Divine+Liturgy.html", "The Liturgy of St. Basil the Great.", "h2"),
    ("The+Divine+Liturgy.html", "The Liturgy of the Presanctified Gifts.", "h2"),
    ("Great+Lent+and+Pascha.html", "Sunday of the Publican and the Pharisee.", "h3"),
    ("Great+Lent+and+Pascha.html", "Second Sunday of Great Lent St. Gregory Palamas.", "h3"),
    ("Great+Lent+and+Pascha.html", "The Lenten Prayer of St. Ephrem the Syrian.", "h3"),
    ("The+Symbol+of+Faith.html", "Concerning the Life of the World to Come.", "h2"),
    ("The+Church+Building.html", "External Arrangement.", "h2"),
    ("The+Mother+of+God.html", "The Most-Holy Theotokos and Ever-Virgin Mary.", "h2"),
]

# --- one sentence broken into two paragraphs on the old site ------------------------------------------
JOINS = [
    ("A+History+of+the+Orthodox+Church.html", "the Council of</p>\n<p>Moscow, which met", "the Council of Moscow, which met"),
    ("Great+Lent+and+Pascha.html", "foreshadows the</p>\n<p>Lord's glorious", "foreshadows the Lord's glorious"),
    ("The+Churchs+Prayer+for+the+Dead.html", "drowned in the</p>\n<p>sea [Ode 9].", "drowned in the sea [Ode 9]."),
    ("Various+Other+Feasts.html", "advanced in years</p>\n<p>(Luke 1:5-7).</p>", "advanced in years (Luke 1:5-7).</p>"),
]

# --- Where to Find: "When …: Ps. …" lines -> description list -----------------------------------------
PSALMS_FOR_NEEDS = [
    ("When Afraid", "Ps. 27; Ps. 56"), ("When Anxious", "Ps. 46"), ("When Disaster Threatens", "Ps. 34; Ps. 91; Ps. 121"),
    ("When Discouraged", "Ps. 23; Ps. 37; Ps. 42; Ps. 55; Ps. 90"),
    ("When Facing a Crisis", "Ps. 34; Ps. 46; Ps. 118; Ps. 121"), ("When Friends Fail", "Ps. 27; Ps. 35"),
    ("When Leaving Home", "Ps. 27; Ps. 121"), ("When Needing God's Protection", "Ps. 27; Ps. 62; Ps. 91; Ps. 139"),
    ("When Needing Inward Peace", "Ps. 37; Ps. 85"),
    ("When Needing Prayer", "Ps. 4; Ps. 6; Ps. 20; Ps. 22; Ps. 25; Ps. 42; Ps. 51"),
    ("When Sick", "Ps. 32; Ps. 38; Ps. 91"), ("When We Sin", "Ps. 6; Ps. 51; Ps. 139"),
    ("When Sorrowing", "Ps. 40; Ps. 42; Ps. 43; Ps. 51"), ("When Tempted", "Ps. 1; Ps. 73; Ps. 101; Ps. 110; Ps. 139"),
    ("When Thankful", "Ps. 65; Ps. 84; Ps. 92; Ps. 95; Ps. 100; Ps. 103; Ps. 116; Ps. 136; Ps. 147"),
    ("When In Trouble", "Ps. 2; Ps. 16; Ps. 31; Ps. 34; Ps. 37; Ps. 38; Ps. 40; Ps. 139"),
    ("When Weary", "Ps. 6; Ps. 27; Ps. 55; Ps. 60; Ps. 90"),
]

# --- Liturgical Books: the kathisma table, flattened into lines on the old site --------------------------
# (kathisma, stasis 1, stasis 2, stasis 3), Hebrew numbering with the LXX in parentheses, as the note under
# the table says. Cells marked * differ from the old page: see SCAN_FIXES.
KATHISMAS = [
    ("1", "1-3 (1-3)*", "4-6 (4-6)", "7-8 (7-8)"),
    ("2", "9-11 (9-10)", "12-14 (11-13)", "15-17 (14-16)"),
    ("3", "18 (17)", "19-21 (18-20)", "22-24 (21-23)"),
    ("4", "25-27 (24-26)", "28-30 (27-29)", "31-32 (30-31)"),
    ("5", "33-34 (32-33)", "35-36 (34-35)", "37 (36)"),
    ("6", "38-40 (37-39)", "41-43 (40-42)", "44-46 (43-45)"),
    ("7", "47-49 (46-48)", "50-51 (49-50)", "52-55 (51-54)"),
    ("8", "56-58 (55-57)", "59-61 (58-60)", "62-64 (61-63)"),
    ("9", "65-67 (64-66)", "68 (67)", "69-70 (68-69)"),
    ("10", "71-72 (70-71)", "73-74 (72-73)", "75-77 (74-76)"),
    ("11", "78 (77)", "79-81 (78-80)", "82-85 (81-84)"),
    ("12", "86-88 (85-87)", "89 (88)", "90-91 (89-90)"),
    ("13", "92-94 (91-93)", "95-97 (94-96)", "98-101 (97-100)"),
    ("14", "102-103 (101-102)", "104 (103)", "105 (104)"),
    ("15", "106 (105)", "107 (106)", "108-109 (107-108)"),
    ("16", "110-112 (109-111)", "113-116:9 (112-114)", "116:10-19; 117-118 (115-117)*"),
    ("17", "119:1-72 (118:1-72)", "119:73-131 (118:73-131)", "119:132-176 (118:132-176)"),
    ("18", "120-124 (119-123)", "125-129 (124-128)", "130-134 (129-133)"),
    ("19", "135-137 (133-136)", "138-140 (137-139)", "141-143 (140-142)"),
    ("20", "144-145 (143-144)", "146-147 (145-147)", "148-150 (148-150)*"),
]
SCAN_FIXES = {
    "1-3 (1-3)*": "old page: '(D' for '(1-3)'",
    "116:10-19; 117-118 (115-117)*": "old page: '116:10-19;! 17-118'",
    "148-150 (148-150)*": "old page: '(148-' (cut off)",
    # plus the stray line '127' (a page number of the book) between kathismas 12 and 13, dropped
    # NOT fixed, needs the book: kathisma 19, stasis 1 reads '(133-136)'; the LXX of Ps 135-137 is 134-136
}
OLD_KATHISMA_LINES = (Path(__file__).with_name("kathisma_block.txt")).read_text(encoding="utf-8")


def cell(text):
    return text.rstrip("*")


KATHISMA_TABLE = (
    "<table>\n<tr><th>Kathisma</th><th>Stasis 1</th><th>Stasis 2</th><th>Stasis 3</th></tr>\n"
    + "".join(f"<tr><th>{k}</th><td>{cell(a)}</td><td>{cell(b)}</td><td>{cell(c)}</td></tr>\n" for k, a, b, c in KATHISMAS)
    + "</table>\n<!-- TODO(content): kathisma 19, stasis 1 reads \"(133-136)\" on the old page, but the LXX numbers of "
    "Ps 135-137 are 134-136; check the book -->"
)

# --- creed.html: lecture titles in capitals -> headings, with the case of pravoslavie.ru -----------------
CREED_LECTURES = [
    ("https://pravoslavie.ru/116171.html", "ЛЕКЦИЯ 1. ВЕРА В ЕДИНОГО БОГА ОТЦА", "Лекция 1. Вера в единого Бога Отца"),
    ("http://www.pravoslavie.ru/116288.html", "ЛЕКЦИЯ 2. ВЕРА В ЕДИНОГО ГОСПОДА ИИСУСА ХРИСТА, СЫНА БОЖИЯ",
     "Лекция 2. Вера в единого Господа Иисуса Христа, Сына Божия"),
    ("https://pravoslavie.ru/116622.html", "ЛЕКЦИЯ 3. ВЕРА В БОГОВОПЛОЩЕНИЕ", "Лекция 3. Вера в Боговоплощение"),
    ("https://pravoslavie.ru/116797.html", "ЛЕКЦИЯ 4. ВЕРА В СПАСИТЕЛЬНЫЕ СТРАДАНИЯ ГОСПОДА ИИСУСА ХРИСТА",
     "Лекция 4. Вера в спасительные страдания Господа Иисуса Христа"),
    ("https://pravoslavie.ru/116952.html", "ЛЕКЦИЯ 5. ВЕРА В ВОСКРЕСЕНИЕ ХРИСТОВО", "Лекция 5. Вера в Воскресение Христово"),
    ("https://pravoslavie.ru/117112.html", "ЛЕКЦИЯ 6. ВЕРА В ВОЗНЕСЕНИЕ ХРИСТОВО", "Лекция 6. Вера в Вознесение Христово"),
    ("https://pravoslavie.ru/117273.html", "ЛЕКЦИЯ 7. ВЕРА ВО ВТОРОЕ ПРИШЕСТВИЕ ХРИСТОВО", "Лекция 7. Вера во Второе пришествие Христово"),
    ("https://pravoslavie.ru/117412.html", "ЛЕКЦИЯ 8. ВЕРА В ДУХА СВЯТОГО", "Лекция 8. Вера в Духа Святого"),
    ("http://www.pravoslavie.ru/117573.html", "ЛЕКЦИЯ 9. ВЕРА В ЦЕРКОВЬ", "Лекция 9. Вера в Церковь"),
    ("https://pravoslavie.ru/117911.html", "ЛЕКЦИЯ 10. ВЕРА В БЛАГОДАТНУЮ СИЛУ КРЕЩЕНИЯ И ДРУГИХ ЦЕРКОВНЫХ ТАИНСТВ",
     "Лекция 10. Вера в благодатную силу Крещения и других церковных Таинств"),
    ("http://pravoslavie.ru/118062.html", "ЛЕКЦИЯ 11. ВЕРА В ВОСКРЕСЕНИЕ МЕРТВЫХ", "Лекция 11. Вера в воскресение мертвых"),
    ("https://pravoslavie.ru/118298.html", "ЛЕКЦИЯ 12. ВЕРА В БУДУЩУЮ ЖИЗНЬ", "Лекция 12. Вера в будущую жизнь"),
]
TOPICS = "<p>В лекции рассмотрены следующие темы:"

PROPOSED = [
    {"page": f"article/{page}", "find": f"<p><strong>{text}</strong></p>", "replace": f"<{tag}>{text}</{tag}>",
     "count": 1, "why": "a heading set as a bold paragraph on the old site; its neighbours are headings"}
    for page, text, tag in BOLD_TO_HEADING
] + [
    {"page": "article/Liturgical+Music.html", "find": "<p><strong>Liturgical Music.</strong></p>\n", "replace": "",
     "count": 1, "why": "repeats the page title right under it"},
] + [
    {"page": f"article/{page}", "find": find, "replace": replace, "count": 1,
     "why": "one sentence split into two paragraphs on the old site"}
    for page, find, replace in JOINS
] + [
    {"page": "article/The+Churchs+Prayer+for+the+Dead.html",
     "find": "<p>According to St. Isaac the Syrian,</p>\n<p>when the Spirit",
     "replace": "<p>According to St. Isaac the Syrian,</p>\n<blockquote>\n<p>when the Spirit", "count": 1,
     "why": "a quotation set as an ordinary paragraph"},
    {"page": "article/The+Churchs+Prayer+for+the+Dead.html",
     "find": "spontaneously [Mystical Treatises].</p>", "replace": "spontaneously [Mystical Treatises].</p>\n</blockquote>",
     "count": 1, "why": "end of the same quotation"},
] + [
    {"page": "article/Holy+Baptism.html", "find": find, "replace": replace, "count": 1,
     "why": "one bold phrase split into two <strong> on the old site"}
    for find, replace in [
        ("<strong>1.</strong> <strong>The Catechumenate</strong>", "<strong>1. The Catechumenate</strong>"),
        ("<strong>2.</strong> <strong>The Exorcism</strong>", "<strong>2. The Exorcism</strong>"),
        ("<strong>3. The</strong> <strong>Renunciation of the Devil</strong>",
         "<strong>3. The Renunciation of the Devil</strong>"),
    ]
] + [
    {"page": "article/The+Divine+Liturgy.html", "find": "\n<hr/>", "replace": "", "count": 1,
     "why": "a closing rule with nothing after it (the old page's source credit is empty)"},
    {"page": "article/Where+to+Find.html",
     "find": "<p>" + "<br/>".join(f"{t}: {r}" for t, r in PSALMS_FOR_NEEDS) + "</p>",
     "replace": "<dl>\n" + "".join(f"<dt>{t}</dt>\n<dd>{r}</dd>\n" for t, r in PSALMS_FOR_NEEDS) + "</dl>",
     "count": 1, "why": "a list of needs and psalms set as lines of one paragraph"},
    {"page": "article/Where+to+Find.html",
     "find": "<p>Numbers 6:24-26 Hebrews 13:20-21 1 Timothy 1:17</p>",
     "replace": "<ul>\n<li>Numbers 6:24-26</li>\n<li>Hebrews 13:20-21</li>\n<li>1 Timothy 1:17</li>\n</ul>",
     "count": 1, "why": "three references run together in one line on the old site"},
    {"page": "article/Used+in+Church.html",
     "find": "<p>1. Matthew 28:16-20 7. John 20:1-10</p>\n<p>2. Mark 16:1-8 8. John 20:11-18</p>\n"
             "<p>3. Mark 16:9-20 9. John 20:19-31</p>\n<p>4. Luke 24:1-12 10. John 21:1-14</p>\n"
             "<p>5. Luke 24:12-35 11. John 21:15-25</p>\n<p>6. Luke 24:36-53</p>",
     "replace": "<ol>\n" + "".join(f"<li>{r}</li>\n" for r in [
         "Matthew 28:16-20", "Mark 16:1-8", "Mark 16:9-20", "Luke 24:1-12", "Luke 24:12-35", "Luke 24:36-53",
         "John 20:1-10", "John 20:11-18", "John 20:19-31", "John 21:1-14", "John 21:15-25"]) + "</ol>",
     "count": 1, "why": "the eleven Resurrection Gospels, flattened from two columns into lines on the old site"},
    {"page": "article/Liturgical+Books.html",
     "find": OLD_KATHISMA_LINES.split("\n", 1)[1].rstrip("\n"),
     "replace": KATHISMA_TABLE, "count": 1,
     "why": "the kathisma table, flattened into lines on the old site; three scanning errors and a stray page number fixed"},
] + [
    {"page": "creed.html", "find": f'<p><a href="{url}">{caps}</a></p>', "replace": f'<h3><a href="{url}">{title}</a></h3>',
     "count": 1, "why": "lecture title in capitals in place of a heading; letter case as on pravoslavie.ru (checked 2026-10-19)"}
    for url, caps, title in CREED_LECTURES
] + [
    {"page": "creed.html", "find": TOPICS + "<br/>", "replace": TOPICS + "</p>\n<ul>\n<li>", "count": 1,
     "why": "list of topics typed as lines (lecture 12)"},
    {"page": "creed.html", "find": TOPICS + "</p>\n<p>", "replace": TOPICS + "</p>\n<ul>\n<li>", "count": 11,
     "why": "list of topics typed as lines"},
    {"page": "creed.html", "find": "<br/>", "replace": "</li>\n<li>", "count": 54, "why": "list of topics typed as lines"},
    {"page": "creed.html", "find": "?</p>", "replace": "?</li>\n</ul>", "count": 12, "why": "list of topics typed as lines"},
]

if __name__ == "__main__":
    import re
    import tempfile
    from bs4 import BeautifulSoup
    content = Path(__file__).resolve().parents[2] / "content" / "pages"
    out = Path(tempfile.mkdtemp(prefix="markup-proposed-"))  # the simulated pages, outside the repository
    pages = {}
    ok = True
    for c in PROPOSED:
        text = pages.get(c["page"]) or (content / c["page"]).read_text(encoding="utf-8")
        found = text.count(c["find"])
        if found != c["count"]:
            ok = False
            print(f"MISMATCH {c['page']}: expects {c['count']}, found {found}: {c['find'][:60]!r}")
        pages[c["page"]] = text.replace(c["find"], c["replace"])
    words = lambda h: len(re.findall(r"\w+", BeautifulSoup(h, "html.parser").get_text(" ")))
    for page, text in pages.items():
        before = (content / page).read_text(encoding="utf-8")
        target = out / page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"{page:48} words {words(before):6} -> {words(text):6}")
    print("entries:", len(PROPOSED), "all counts match" if ok else "SOME COUNTS DO NOT MATCH")
