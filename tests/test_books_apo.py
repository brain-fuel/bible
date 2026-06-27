import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "1ES": ("I Esdras", 9), "2ES": ("II Esdras", 16), "TOB": ("Tobit", 14),
    "JDT": ("Judith", 16), "ADE": ("Additions to Esther", 16),
    "WIS": ("Wisdom", 19), "SIR": ("Sirach", 51), "BAR": ("Baruch", 6),
    "PAZ": ("Prayer of Azariah", 1), "SUS": ("Susanna", 1),
    "BEL": ("Bel and the Dragon", 1), "MAN": ("Prayer of Manasses", 1),
    "1MA": ("I Maccabees", 16), "2MA": ("II Maccabees", 15),
}


def _apo_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "apo"]


def test_fourteen_apo_books():
    books = _apo_books()
    assert len(books) == 14
    by = {b["code"]: b for b in books}
    assert set(by) == set(EXPECTED)


def test_apo_book_fields_and_chapters():
    by = {b["code"]: b for b in _apo_books()}
    for code, (name, chapters) in EXPECTED.items():
        b = by[code]
        # kjv_name MUST equal the KJVA dataset book name (source lookup key).
        assert b["english_name"] == name
        assert b["kjv_name"] == name
        assert b["chapters"] == chapters
        assert b.get("finnish_name")


def test_apo_finnish_spot_names():
    by = {b["code"]: b for b in _apo_books()}
    assert by["TOB"]["finnish_name"] == "Tobitin kirja"
    assert by["1MA"]["finnish_name"] == "Ensimmäinen makkabilaiskirja"
    assert by["SUS"]["finnish_name"] == "Susanna"
