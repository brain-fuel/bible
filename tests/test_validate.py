import json
from pathlib import Path
from tools.parse import parse_chapter
from tools.validate import validate_chapter, compare_to_james

ROOT = Path(__file__).resolve().parents[1]
META = {"code":"JAM","latin_name":"Epistula Jacobi","greek_name":"Ἰάκωβος",
        "english_name":"The General Epistle of James"}

def _james_ch(n):
    html = (ROOT / "tests" / "fixtures" / "jam01.htm").read_text(encoding="utf-8")
    return parse_chapter(html, META, 1)  # only chapter 1 fixture available

def test_clean_chapter_has_no_errors():
    assert validate_chapter(_james_ch(1)) == []

def test_missing_verse_number_is_flagged():
    bad = _james_ch(1)
    bad["verses"][3]["verse"] = 9  # break contiguity (was 4)
    errs = validate_chapter(bad)
    assert any("contiguous" in e for e in errs)

def test_empty_latin_is_flagged():
    bad = _james_ch(1)
    bad["verses"][0]["latin_vulgate"] = ""
    assert any("latin" in e.lower() for e in validate_chapter(bad))

def test_james_oracle_matches_reference_chapter_one():
    generated = _james_ch(1)
    ref = json.loads((ROOT/"tests"/"fixtures"/"james_ref"/"jas001.json").read_text(encoding="utf-8"))
    assert compare_to_james(generated, ref) == []
