"""Fixes applied to mirrored pages after cleanup, so they survive every re-run of scripts/mirror.py.

Each entry replaces `find` with `replace` in the cleaned HTML of `page` and must match exactly `count`
times; otherwise the mirror stops, because the old page has changed and the fix needs a look.
Frozen pages (site.toml) are edited by hand instead.
"""

STRONG_PAGES = ['A+History+of+the+Orthodox+Church.html', 'Church+Mysteries.html', 'Communing+with+God+in+Prayer.html', 'Fasting+Rules.html', 'Fasting+Seasons+and+Days.html', 'Fasting.html', 'Glossary+of+Liturgical+Terms.html', 'Great+Lent+and+Pascha.html', 'Holy+Baptism.html', 'Holy+Chrismation.html', 'Holy+Communion.html', 'Holy+Icons.html', 'Holy+Matrimony.html', 'Holy+Orders.html', 'Holy+Repentance.html', 'Holy+Tradition.html', 'Holy+Unction.html', 'Icon+Not-Made-By-Hands.html', 'Icons+of+the+Mother+of+God.html', 'Liturgical+Books.html', 'Liturgical+Gestures.html', 'Liturgical+Music.html', 'Orthodoxy+in+America.html', 'Orthodoxy+in+the+World.html', 'The+Altar+and+Its+Furnishings.html', 'The+Beatitudes.html', 'The+Bells.html', 'The+Candles+and+Their+Symbolism.html', 'The+Christian+Ethic.html', 'The+Church+Building.html', 'The+Churchs+Prayer+for+the+Dead.html', 'The+Clergy.html', 'The+Cross.html', 'The+Feast+of+Feasts+-+Pascha.html', 'The+Holy+Bible.html', 'The+Iconostasis.html', 'The+Monastic+Grades.html', 'The+Monastic+Tonsure.html', 'The+Mother+of+God.html', 'The+New+Testament.html', 'The+Old+Testament+Apocrypha.html', 'The+Old+Testament.html', 'The+Other+Symbols.html', 'The+Sacristy+and+Vestry.html', 'The+Symbol+of+Faith.html', 'The+Ten+Commandments.html', 'The+Twelve+Great+Feasts.html', 'Used+in+Church.html', 'Various+Other+Feasts.html', 'Where+to+Find.html']
PLAIN_PAGES = ['Services+of+the+Daily+Cycle.html', 'The+Five+Cycles.html']

CORRECTIONS = [
    {
        "page": page,
        "find": "contact Fr Vladimir at frvlad@xtra.co.nz",
        "replace": 'contact Fr Vladimir at <a href="mailto:info@orthodox.nz">info@orthodox.nz</a>',
        "count": 1,
        "why": "the public address is info@orthodox.nz, not Fr Vladimir's personal one (decided 2026-10-19)",
    }
    for page in ("donations.html", "benevolent_fund.html")
] + [
    {
        "page": "about_orthodoxy.html",
        "find": "<h1>About Orthodoxy</h1>",
        "replace": "<h1>About Orthodoxy</h1>\n<!-- TODO(content): the articles are scanned text from the old site; the "
        "certain scanning errors are fixed in scripts/corrections.py, but they need a proofread if they stay -->"
        "\n<!-- needs blessing: 52 of the 53 linked articles (article/…) are excerpts from "
        "'These Truths We Hold – The Holy Orthodox Church: Her Life and Teachings' (© 1986 St Tikhon's Seminary Press), "
        "republished from the old site with no known permission; 'The Divine Liturgy' has no credit line; keep, ask "
        "St Tikhon's, or remove? (mirrored as on the old site, 2026-10-19) -->\n<!-- TODO(content): the St Tikhon's "
        "bookstore link in the articles (http://stots.edu/bookstore_contact.html) is dead (HTTP 410, checked "
        "2026-10-19) and was removed; link https://stots.edu/ instead? -->",
        "count": 1,
        "why": "flag the copyrighted article texts and the removed dead link for Fr Vladimir",
    },
    {
        "page": "article/Various+Other+Feasts.html",
        "find": "The »Feast",
        "replace": "The Feast",
        "count": 1,
        "why": "a stray Windows-1252 byte on the old site (shown there as �)",
    },
    {
        "page": "schedule.html",
        "find": ' <a href="files/--.pdf">текст</a>',
        "replace": ' <!-- TODO(content): the text of the Akathist "Нечаянная Радость" is missing: the old link /files/--.pdf '
        "opens the A. Basyuk exhibition flyer (already wrong on the old site); link removed -->",
        "count": 1,
        "why": "the linked file is the exhibition flyer, which news.html links correctly",
    },
    {
        "page": "news.html",
        "find": "<h1>News and Photos</h1>",
        "replace": "<h1>News and Photos</h1>\n<!-- needs blessing: the news items 'Festival of Kindness' (26 July 2026) and "
        "'New Exhibition' (30 November 2025 – 31 January 2026) are past; keep them, mark them as past, or remove? -->",
        "count": 1,
        "why": "past events read as current news",
    },
    {
        "page": "news.html",
        "find": 'alt="Festival of Kindness"',
        "replace": 'alt="Poster: The Legacy of Kindness, Sunday 26 July. After the Divine Liturgy and Panikhida, a parish '
        "fellowship meal and an evening in memory of Father Alexander. Parish Hall, 455–461 Dominion Road, Mt Eden, "
        'Auckland, 12:00 pm – 3:00 pm."',
        "count": 1,
        "why": "the event details exist only in the image",
    },
    {
        "page": "news.html",
        "find": '<p><a href="images/The-legacy-of-kindness.png"><img ',
        "replace": "<p><img ",
        "count": 1,
        "why": "the 'full size' image the poster linked to is smaller than the poster itself",
    },
    {"page": "news.html", "find": 'width="576"/></a></p>', "replace": 'width="576"/></p>', "count": 1, "why": "as above"},
    {
        "page": "news.html",
        "find": "<h2>Festival of Kindness</h2>",
        "replace": "<h2>Festival of Kindness / Фестиваль Добра</h2>",
        "count": 1,
        "why": "one heading for both languages instead of an empty Russian sub-heading",
    },
    {"page": "news.html", "find": "\n<h3>Фестиваль Добра</h3>", "replace": "", "count": 1, "why": "merged above"},
    {
        "page": "news.html",
        "find": "<h2>Новая выставка</h2>\n<h3>New Exhibition</h3>",
        "replace": "<h2>Новая выставка / New Exhibition</h2>",
        "count": 1,
        "why": "the translation is not a sub-section of the original",
    },
    {
        "page": "news.html",
        "find": "<h2>Запись в школу</h2>\n<h3>Parish school application</h3>",
        "replace": "<h2>Запись в школу / Parish school application</h2>",
        "count": 1,
        "why": "the translation is not a sub-section of the original",
    },
    {
        "page": "links.html",
        "find": "<td>Диакон Андрей Кураев</td>",
        "replace": "<td>Диакон Андрей Кураев<!-- needs blessing: link to Andrei Kuraev: he was deposed in 2023, so the title "
        "is out of date, and www.kuraev.ru no longer answers (checked 2026-10-19); keep, retitle or remove? --></td>",
        "count": 1,
        "why": "an out-of-date title of a person, for Fr Vladimir to decide",
    },
    {
        "page": "links.html",
        "find": "<h1>Links</h1>",
        "replace": "<h1>Links</h1>\n<!-- TODO(content): external links dead on 2026-10-19 (HTTP 404/410): "
        "rocor.org.au/official/14th_assembly_ru.html (the diocese name; rocor.org.au itself works), "
        "ispovednik.ru/izd_max.htm, fomacenter.ru, novgorod.ru/city/culture/cd2/rus/pp_r_f.htm, "
        "orthodoxes-kloster.at/menu.htm, aksion.republika.pl/multimedia-ru.html, pravbeseda.org/library/, "
        "orthotracts.org/musicpage.html, pagez.ru/prolog/; many other hosts did not answer; remove or replace? -->",
        "count": 1,
        "why": "inherited dead links, listed for whoever updates the page",
    },
] + [
    # The section rows of the links table become headings, so the groups stand out (and read as sections).
    {
        "page": "links.html",
        "find": find,
        "replace": replace,
        "count": 1,
        "why": "section titles of the links table",
    }
    for find, replace in [
        (
            '<table> <tr> <td colspan="2"><p>English is used for websites having an English version.</p></td> </tr> '
            '<tr> <td colspan="2"><p><strong> Официальные Сайты <br/> Official WebSites</strong></p></td> </tr>',
            "<p>English is used for websites having an English version.</p>\n"
            "<h2>Официальные Сайты / Official WebSites</h2>\n<table>",
        ),
        (
            '<tr> <td colspan="2"><p><strong> Рекомендуем <br/> Recommendations</strong></p></td> </tr>',
            "</table>\n<h2>Рекомендуем / Recommendations</h2>\n<table>",
        ),
        (
            '<tr> <td colspan="2"><p><strong> Проповеди и Лекции<br/> Sermons &amp; Lectures</strong></p></td> </tr>',
            "</table>\n<h2>Проповеди и Лекции / Sermons &amp; Lectures</h2>\n<table>",
        ),
        (
            '<tr> <td colspan="2"><p><strong>Православные Библиотеки<br/>  Orthodox Libraries</strong></p></td> </tr>',
            "</table>\n<h2>Православные Библиотеки / Orthodox Libraries</h2>\n<table>",
        ),
        (
            '<tr> <td colspan="2"><p><strong>Песнопения<br/>  Music</strong></p></td> </tr>',
            "</table>\n<h2>Песнопения / Music</h2>\n<table>",
        ),
    ]
] + [
    # The St Tikhon's bookstore page is gone (HTTP 410); keep the name, drop the dead link.
    {
        "page": f"article/{name}",
        "find": find,
        "replace": "<strong>St. Tikhon's Orthodox Seminary Bookstore</strong>" if "<strong>" in find
        else "St. Tikhon's Orthodox Seminary Bookstore",
        "count": 1,
        "why": "dead link (HTTP 410, checked 2026-10-19); one TODO on about_orthodoxy.html",
    }
    for names, find in [
        (STRONG_PAGES,
         '<a href="http://stots.edu/bookstore_contact.html"><strong>St. Tikhon\'s Orthodox Seminary Bookstore</strong></a>'),
        (PLAIN_PAGES, '<a href="http://stots.edu/bookstore_contact.html">St. Tikhon\'s Orthodox Seminary Bookstore</a>'),
    ]
    for name in names
] + [
    # Scanning errors inherited from the old site, only where the right reading is certain.
    {"page": f"article/{page}", "find": find, "replace": replace, "count": 1, "why": "scanning error on the old site"}
    for page, find, replace in [
        ("Various+Other+Feasts.html", "\\vas the beginning", "was the beginning"),
        ("Various+Other+Feasts.html", "bound hint in prison", "bound him in prison"),
        ("Various+Other+Feasts.html", "go be fore the Lord", "go before the Lord"),
        ("Various+Other+Feasts.html", "/ have seen and", "I have seen and"),
        ("Holy+Baptism.html", "/ baptize you", "I baptize you"),
        ("The+Divine+Liturgy.html", "/ received from the Lord", "I received from the Lord"),
        ("The+Divine+Liturgy.html", "/ will bless the Lord", "I will bless the Lord"),
        ("The+Beatitudes.html", "/ appeal to you", "I appeal to you"),
        ("Holy+Icons.html", "I7ou shall not make", "You shall not make"),
        ("Holy+Icons.html", "(f776)", "(†776)"),
        ("Holy+Icons.html", "(f379)", "(†379)"),
        ("Liturgical+Books.html", "(f532)", "(†532)"),
        ("The+New+Testament.html", "nor a6outyour body, what you shod put on", "nor about your body, what you shall put on"),
        ("Where+to+Find.html", "not wont", "not want"),
        ("Where+to+Find.html", "de down in green", "lie down in green"),
        ("Where+to+Find.html", "I shall dwetl in", "I shall dwell in"),
        ("The+New+Testament.html", "about your fife", "about your life"),
        ("The+New+Testament.html", "Look at the fords of the air", "Look at the birds of the air"),
        ("The+New+Testament.html", "span of fife", "span of life"),
        ("The+New+Testament.html", "lilies of the field) how", "lilies of the field, how"),
        ("The+New+Testament.html", "toil nor spin) yet", "toil nor spin; yet"),
        ("The+New+Testament.html", "loses his fife", "loses his life"),
        ("The+New+Testament.html", "that/aitfi by itself", "that faith by itself"),
        ("The+Divine+Liturgy.html", "unto fife everlasting", "unto life everlasting"),
        ("Great+Lent+and+Pascha.html", "The table is fully-laden) all of you", "The table is fully-laden; all of you"),
        ("Icons+of+the+Mother+of+God.html", "llth-12th", "11th-12th"),
        ("A+History+of+the+Orthodox+Church.html", "Phllokalia", "Philokalia"),
        ("The+Old+Testament+Apocrypha.html", "Deutero-canonicalas contrasted", "Deutero-canonical as contrasted"),
        ("The+Other+Symbols.html", "Nazaremus Rex Indaeorum", "Nazarenus Rex Iudaeorum"),
        ("The+Churchs+Prayer+for+the+Dead.html", "Komvoschoinlon", "Komvoschoinion"),
    ]
] + [
    {
        "page": "article/Used+in+Church.html",
        "find": "<h1>Used in Church</h1>",
        "replace": "<h1>Used in Church</h1>\n<!-- TODO(content): the table of readings on this page was already flattened "
        "into run-on lines on the old site; restore it from the book if the article stays -->",
        "count": 1,
        "why": "inherited flattened table",
    },
]
