import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))["books"]

NT_CODES = ["MAT","MAR","LUK","JOH","ACT","ROM","1CO","2CO","GAL","EPH","PHP",
            "COL","1TH","2TH","1TI","2TI","TIT","PHM","HEB","JAM","1PE","2PE",
            "1JO","2JO","3JO","JDE","REV"]
NT_CHAPTERS = {"MAT":28,"MAR":16,"LUK":24,"JOH":21,"ACT":28,"ROM":16,"1CO":16,
               "2CO":13,"GAL":6,"EPH":6,"PHP":4,"COL":4,"1TH":5,"2TH":3,"1TI":6,
               "2TI":4,"TIT":3,"PHM":1,"HEB":13,"JAM":5,"1PE":5,"2PE":3,"1JO":5,
               "2JO":1,"3JO":1,"JDE":1,"REV":22}

def nt_rows():
    return [b for b in BOOKS if b["testament"] == "nt"]

def test_all_nt_books_present_in_canonical_order():
    assert [b["code"] for b in nt_rows()] == NT_CODES

def test_codes_unique_and_three_chars():
    codes = [b["code"] for b in BOOKS]
    assert len(codes) == len(set(codes))
    assert all(len(c) == 3 for c in codes)

def test_nt_rows_fully_populated():
    for b in nt_rows():
        for key in ("dir","prefix","chapters","latin_name","greek_name","english_name"):
            assert b[key], f"{b['code']} missing {key}"
        assert b["chapters"] == NT_CHAPTERS[b["code"]]

def test_no_dashes_in_names():
    bad = re.compile("[\u2013\u2014]")
    for b in BOOKS:
        for key in ("latin_name","greek_name","english_name"):
            assert not bad.search(b.get(key) or ""), f"dash in {b['code']} {key}"
