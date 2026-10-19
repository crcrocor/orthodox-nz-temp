"""Fixes applied to mirrored pages after cleanup, so they survive every re-run of scripts/mirror.py.

Each entry replaces `find` with `replace` in the cleaned HTML of `page` and must match exactly `count`
times; otherwise the mirror stops, because the old page has changed and the fix needs a look.
Frozen pages (site.toml) are edited by hand instead.
"""

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
        "replace": "<h1>About Orthodoxy</h1>\n<!-- needs blessing: the 53 linked articles (article/…) come from the Orthodox Web "
        "Solutions article library; their source and rights are not stated; mirrored as they were on the old site "
        "(decided 2026-10-19) -->",
        "count": 1,
        "why": "flag the OWS library texts for Fr Vladimir",
    },
    {
        "page": "article/Various+Other+Feasts.html",
        "find": "The »Feast",
        "replace": "The Feast",
        "count": 1,
        "why": "a stray Windows-1252 byte on the old site (shown there as �)",
    },
]
