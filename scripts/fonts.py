# /// script
# requires-python = ">=3.14"
# dependencies = ["fonttools[woff]==4.66.1"]
# ///
"""Make the web fonts in static/fonts/ from PT Serif (network, manual; only when the font or the subset changes).

Usage: uv run scripts/fonts.py

Downloads PT Serif (ParaType, 2010; SIL Open Font License 1.1) from a fixed commit of github.com/google/fonts,
keeps only the characters this site needs and writes one WOFF2 file per style, each with Latin and Cyrillic.
A subset is a Modified Version under the licence, and "PT Serif" is a Reserved Font Name, so the files are
renamed "Deanery Serif"; the copyright and licence entries stay. ParaType's hinting stays too: it keeps the
text crisp on old Windows screens. fonttools is this script's own dependency (uv installs it for the script
only), not the site's.
"""

import io
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "static" / "fonts"
SOURCE = "https://raw.githubusercontent.com/google/fonts/80327115aa6e63ea8947558e5fb676f5287878ba/ofl/ptserif/"
FAMILY = "Deanery Serif"
STYLES = {  # source file → output file; Bold Italic is left out, the content has none
    "PT_Serif-Web-Regular.ttf": "deanery-serif-400.woff2",
    "PT_Serif-Web-Italic.ttf": "deanery-serif-400-italic.woff2",
    "PT_Serif-Web-Bold.ttf": "deanery-serif-700.woff2",
}
UNICODES = [
    "U+0020-007E",  # Basic Latin
    "U+00A0-00FF",  # Latin-1: no-break space, « », ©, accented letters
    "U+0100-0101,U+0112-0113,U+012A-012B,U+014C-014D,U+016A-016B",  # macrons of Māori words in NZ English
    "U+0400-045F",  # Cyrillic: Russian with ё, and the letters of names in other Slavonic languages
    "U+0301",  # combining acute, for stress marks
    "U+2009,U+200A,U+202F",  # thin, hair and narrow no-break spaces
    "U+2010-2015,U+2018-201E,U+2020-2022,U+2026,U+2039,U+203A",  # dashes, quotes, † ‡ •, …, ‹ ›
    "U+2116,U+2212",  # №, minus
]


def fetch(name):
    with urllib.request.urlopen(SOURCE + name, timeout=60) as response:
        return response.read()


def rename(font):
    """Replace the reserved name in every name record that carries it (family, full name, PostScript name)."""
    for record in font["name"].names:
        if record.nameID in (0, 7, 13, 14):  # copyright, trademark, licence: keep as they are
            continue
        text = record.toUnicode()
        new = text.replace("PT Serif", FAMILY).replace("PTSerif", FAMILY.replace(" ", ""))
        if new != text:
            record.string = new


def main():
    FONTS.mkdir(parents=True, exist_ok=True)
    options = subset.Options()
    options.flavor = "woff2"
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.hinting = True
    options.notdef_outline = True
    options.layout_features = ["*"]
    for source, target in STYLES.items():
        font = TTFont(io.BytesIO(fetch(source)))
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=subset.parse_unicodes(",".join(UNICODES)))
        subsetter.subset(font)
        rename(font)
        font.flavor = "woff2"
        font.save(FONTS / target)
        print(f"static/fonts/{target}: {(FONTS / target).stat().st_size // 1024} KB")
    (FONTS / "OFL.txt").write_bytes(fetch("OFL.txt"))
    print("static/fonts/OFL.txt")


if __name__ == "__main__":
    main()
