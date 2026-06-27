import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))["books"]

OT_CODES = ["GEN","EXO","LEV","NUM","DEU","JOS","JDG","RUT","1SA","2SA","1KI","2KI",
            "1CH","2CH","EZR","NEH","EST","JOB","PSA","PRO","ECC","SOS","ISA","JER",
            "LAM","EZE","DAN","HOS","JOE","AMO","OBA","JON","MIC","NAH","HAB","ZEP",
            "HAG","ZEC","MAL"]
OT_CHAPTERS = {"GEN":50,"EXO":40,"LEV":27,"NUM":36,"DEU":34,"JOS":24,"JDG":21,"RUT":4,
               "1SA":31,"2SA":24,"1KI":22,"2KI":25,"1CH":29,"2CH":36,"EZR":10,"NEH":13,
               "EST":10,"JOB":42,"PSA":150,"PRO":31,"ECC":12,"SOS":8,"ISA":66,"JER":52,
               "LAM":5,"EZE":48,"DAN":12,"HOS":14,"JOE":3,"AMO":9,"OBA":1,"JON":4,
               "MIC":7,"NAH":3,"HAB":3,"ZEP":3,"HAG":2,"ZEC":14,"MAL":4}

def ot():
    return [b for b in BOOKS if b["testament"] == "ot"]

def test_all_ot_books_present_in_order():
    assert [b["code"] for b in ot()] == OT_CODES

def test_ot_rows_fully_populated():
    for b in ot():
        for k in ("english_name","hebrew_name","chapters","kjv_name","vulgate_name","sefaria_name"):
            assert b.get(k), f"{b['code']} missing {k}"
        assert b["chapters"] == OT_CHAPTERS[b["code"]]

def test_nt_rows_untouched():
    nt = [b for b in BOOKS if b["testament"] == "nt"]
    assert len(nt) == 27
    assert nt[0]["code"] == "MAT" and "greek_name" in nt[0]


def _ot_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def test_all_ot_books_have_new_display_names():
    for b in _ot_books():
        assert b.get("douay_name"), f"{b['code']} missing douay_name"
        assert b.get("finnish_name"), f"{b['code']} missing finnish_name"


def test_display_name_spot_values():
    by = {b["code"]: b for b in _ot_books()}
    # Douay uses the Vulgate-style English titles (cf. latin_name).
    assert by["1KI"]["douay_name"] == "3 Kings"
    assert by["1CH"]["douay_name"] == "1 Paralipomenon"
    assert by["HOS"]["douay_name"] == "Osee"
    assert by["SOS"]["douay_name"] == "Canticle of Canticles"
    # Finnish standard book names.
    assert by["GEN"]["finnish_name"] == "1. Mooseksen kirja"
    assert by["PSA"]["finnish_name"] == "Psalmit"
    assert by["MAL"]["finnish_name"] == "Malakia"
