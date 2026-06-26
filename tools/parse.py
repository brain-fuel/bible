"""Parse a Logos Apostolic interlinear chapter page into a chapter dict."""
import html
import re
import unicodedata

_TABLE = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)
_ROW = re.compile(r"<tr\b.*?</tr>", re.IGNORECASE | re.DOTALL)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
_STRONG = re.compile(r"<strong\b[^>]*>(.*?)</strong>", re.IGNORECASE | re.DOTALL)
_GRC = re.compile(r'<span\b[^>]*class="grc"[^>]*>(.*?)</span>',
                  re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_VERSENUM = re.compile(r":(\d+)")


def clean_text(fragment: str) -> str:
    """Strip tags, unescape HTML entities, collapse whitespace."""
    text = _TAG.sub("", fragment)
    text = html.unescape(text)
    text = _WS.sub(" ", text).strip()
    # NFC: source HTML Greek is unnormalized; brain-fuel/james oracle is NFC, so normalize to match
    return unicodedata.normalize("NFC", text)


def _strip_strong(cell: str) -> str:
    return _STRONG.sub("", cell, count=1)


def parse_chapter(page_html: str, meta: dict, chapter: int) -> dict:
    table_match = _TABLE.search(page_html)
    if not table_match:
        raise ValueError(f"no <table> found for {meta['code']} {chapter}")
    table = table_match.group(0)

    verses = []
    for row in _ROW.findall(table):
        if "<th" in row.lower():
            continue
        cells = _CELL.findall(row)
        if len(cells) < 3:
            continue
        latin_cell, greek_cell, english_cell = cells[0], cells[1], cells[2]

        strong = _STRONG.search(latin_cell)
        if not strong:
            continue
        num_match = _VERSENUM.search(clean_text(strong.group(1)))
        if not num_match:
            continue
        verse_num = int(num_match.group(1))

        grc = _GRC.search(greek_cell)
        greek_src = grc.group(1) if grc else _strip_strong(greek_cell)

        verses.append({
            "verse": verse_num,
            "latin_vulgate": clean_text(_strip_strong(latin_cell)),
            "greek_textus_receptus": clean_text(greek_src),
            "king_james": clean_text(_strip_strong(english_cell)),
        })

    return {
        "book_id": meta["code"],
        "latin_name": meta["latin_name"],
        "greek_name": meta["greek_name"],
        "english_name": meta["english_name"],
        "chapter": chapter,
        "verses": verses,
    }
