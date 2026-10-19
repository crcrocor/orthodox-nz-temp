"""Fixes applied to mirrored pages after cleanup, so they survive every re-run of scripts/mirror.py.

Each entry replaces `find` with `replace` in the cleaned HTML of `page` and must match exactly `count`
times; otherwise the mirror stops, because the old page has changed and the fix needs a look.
Frozen pages (site.toml) are edited by hand instead; the fixes they once had here live in the pages now.
"""

STRONG_PAGES = ['A+History+of+the+Orthodox+Church.html', 'Church+Mysteries.html', 'Communing+with+God+in+Prayer.html', 'Fasting+Rules.html', 'Fasting+Seasons+and+Days.html', 'Fasting.html', 'Glossary+of+Liturgical+Terms.html', 'Great+Lent+and+Pascha.html', 'Holy+Baptism.html', 'Holy+Chrismation.html', 'Holy+Communion.html', 'Holy+Icons.html', 'Holy+Matrimony.html', 'Holy+Orders.html', 'Holy+Repentance.html', 'Holy+Tradition.html', 'Holy+Unction.html', 'Icon+Not-Made-By-Hands.html', 'Icons+of+the+Mother+of+God.html', 'Liturgical+Books.html', 'Liturgical+Gestures.html', 'Liturgical+Music.html', 'Orthodoxy+in+America.html', 'Orthodoxy+in+the+World.html', 'The+Altar+and+Its+Furnishings.html', 'The+Beatitudes.html', 'The+Bells.html', 'The+Candles+and+Their+Symbolism.html', 'The+Christian+Ethic.html', 'The+Church+Building.html', 'The+Churchs+Prayer+for+the+Dead.html', 'The+Clergy.html', 'The+Cross.html', 'The+Feast+of+Feasts+-+Pascha.html', 'The+Holy+Bible.html', 'The+Iconostasis.html', 'The+Monastic+Grades.html', 'The+Monastic+Tonsure.html', 'The+Mother+of+God.html', 'The+New+Testament.html', 'The+Old+Testament+Apocrypha.html', 'The+Old+Testament.html', 'The+Other+Symbols.html', 'The+Sacristy+and+Vestry.html', 'The+Symbol+of+Faith.html', 'The+Ten+Commandments.html', 'The+Twelve+Great+Feasts.html', 'Used+in+Church.html', 'Various+Other+Feasts.html', 'Where+to+Find.html']
PLAIN_PAGES = ['Services+of+the+Daily+Cycle.html', 'The+Five+Cycles.html']

CORRECTIONS = [
    {
        "page": "article/Various+Other+Feasts.html",
        "find": "The »Feast",
        "replace": "The Feast",
        "count": 1,
        "why": "a stray Windows-1252 byte on the old site (shown there as �)",
    },
] + [
    # The St Tikhon's bookstore page is gone (HTTP 410); keep the name, drop the dead link.
    {
        "page": f"article/{name}",
        "find": find,
        "replace": "<strong>St. Tikhon's Orthodox Seminary Bookstore</strong>" if "<strong>" in find
        else "St. Tikhon's Orthodox Seminary Bookstore",
        "count": 1,
        "why": "dead link (HTTP 410, checked 2026-10-19); one TODO on the frozen about_orthodoxy.html",
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
