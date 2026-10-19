# Typography of the texts from the old site — proposed fixes

Status: proposed 2026-10-19, **nothing applied**. Waits for Fr Pavel; the Russian summary for him is group 9 of `docs/todo-and-blessings.md`. This is priority 4 of `docs/context.md`: it comes after the details, the current facts and the deanery frame.

Decide first the open question on the 52 book excerpts (`docs/todo-and-blessings.md`, group 8, «Права на статьи»). If they are removed, most of what follows goes with them.

## How it was found

A scan of `content/pages/` on 2026-10-19, then four editors (dashes and ranges; quotes, apostrophes and ellipses; headings; markup) and a sweep for what they missed. A second editor checked every item against the files and corrected counts and line numbers. Everything is in `findings.json`: for each issue the cases, pages, examples, exceptions, how to apply, and the second editor's corrections.

## The decisions

| | What | Cases | Words change | Ready as |
|---|---|---|---|---|
| A1 | Spaced hyphen used as a dash → spaced en dash in English, em dash after a no-break space in Russian | 74 EN, 5 RU, plus 17 RU em dashes that lack the no-break space | no | a rule in `scripts/build.py` `typeset()` |
| A2 | Hyphen in ranges → en dash (verses, years, centuries, pages) in the articles | 885, plus 6 that need a hand fix | no | a rule in `typeset()`, articles only; account and phone numbers are never touched |
| A3 | Straight quotes and apostrophes → “ ” ‘ ’ and ’ | 214 double, 684 apostrophes, 40 single (4 unpaired: fix first) | no | a rule in `typeset()` |
| A4 | Three dots → ellipsis … | 218 (the 586 leader dots are layout, see C) | no | a rule in `typeset()` |
| A5 | `St.` → `St` (NZ English; the new pages already write `St Nicholas`) | 626 | style | a rule, or leave the book's style |
| A6 | Full stop at the end of article headings (the book's run-in style) | 369 | style | keep, or drop by a rule |
| B | Scanning errors: misread words (86), punctuation (50), lost † before years of death (45), Scripture references and dates (9), names (27), split paragraphs, spacing | 237 entries | yes, mostly letters | `corrections_proposed.py`, groups G1–G9b, each a separate decision |
| C | Markup: bold paragraphs that are headings, split sentences, quotations, lists typed as lines, dot-leader lists → description lists, the kathisma table and the readings in Used in Church rebuilt, creed lecture titles as headings | 46 entries | no (one table restores scanned characters) | `markup_proposed.py` (uses `kathisma_block.txt`) |
| D | Hand-edited pages (frozen and local): street-number ranges `455-461` → `455–461` (8), heading case (about 40 headings and menu labels), clergy photo captions → `<figure>` (4), English details (9); Russian: ё (12), «Вы» → «вы» (6), abbreviations and no-break spaces (10), the creed title «Символ веры — во что мы верим?», ranks in running text (6) | about 95 | some | hand edits in both language files; see `findings.json` |
| E | Unsure: words lost in the scan, Greek and Slavonic glyphs lost (the old site was ASCII only) | 16 | — | needs the printed book; nothing proposed |

## Applying, after approval

- Rules (A): add them to `typeset()` in `scripts/build.py`; it already fixes typography without changing a word.
- Mirrored pages (B, C): append the approved groups to `scripts/corrections.py`, then `uv run scripts/mirror.py --offline`. The mirror stops when a count no longer matches, which also catches overlaps: a few items in `findings.json` (lost daggers, stray punctuation) are already in `corrections_proposed.py`.
- Both draft files can be run as scripts to check their counts against the current pages (`.venv/bin/python docs/typography/markup_proposed.py`; for `corrections_proposed.py`, apply `PROPOSED` in order). On 2026-10-19: 237 and 46 entries, all counts match.
- Frozen and local pages (D): edit the English and the Russian file by hand, then `uv run scripts/check.py`.
- Remove this folder once the fixes are applied or rejected.
