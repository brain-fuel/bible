from tools.validate_ot import validate_chapter_ot

GOOD = {"book_id":"GEN","latin_name":"L","hebrew_name":"H","english_name":"E",
        "chapter":1,"verses":[
            {"verse":1,"latin_vulgate":"a","hebrew_masoretic":"x","king_james":"k"},
            {"verse":2,"latin_vulgate":"b","hebrew_masoretic":"y","king_james":"m"}]}

def test_clean_chapter_ok():
    assert validate_chapter_ot(GOOD) == []

def test_noncontiguous_flagged():
    bad = {**GOOD, "verses":[{"verse":1,"latin_vulgate":"a","hebrew_masoretic":"x","king_james":"k"},
                              {"verse":3,"latin_vulgate":"b","hebrew_masoretic":"y","king_james":"m"}]}
    assert any("contiguous" in e for e in validate_chapter_ot(bad))

def test_empty_hebrew_flagged():
    bad = {**GOOD, "verses":[{"verse":1,"latin_vulgate":"a","hebrew_masoretic":"","king_james":"k"}]}
    assert any("hebrew" in e.lower() for e in validate_chapter_ot(bad))

# --- TDD: absent marker tests ---

def test_empty_latin_with_absent_marker_ok():
    verses = [{"verse":1,"latin_vulgate":"","hebrew_masoretic":"x","king_james":"k",
               "refs":{"latin_vulgate":"absent"}}]
    obj = {**GOOD, "verses": verses}
    errs = validate_chapter_ot(obj)
    assert not any("latin" in e.lower() for e in errs), f"Unexpected errors: {errs}"

def test_empty_latin_without_marker_errors():
    verses = [{"verse":1,"latin_vulgate":"","hebrew_masoretic":"x","king_james":"k"}]
    obj = {**GOOD, "verses": verses}
    errs = validate_chapter_ot(obj)
    assert any("latin" in e.lower() for e in errs), "Expected empty latin to be flagged"

def test_empty_kjv_always_errors_even_with_marker():
    verses = [{"verse":1,"latin_vulgate":"l","hebrew_masoretic":"x","king_james":"",
               "refs":{"latin_vulgate":"absent"}}]
    obj = {**GOOD, "verses": verses}
    errs = validate_chapter_ot(obj)
    assert any("king_james" in e.lower() for e in errs), "KJV must always be flagged"

def test_empty_hebrew_with_absent_marker_ok():
    verses = [{"verse":1,"latin_vulgate":"l","hebrew_masoretic":"","king_james":"k",
               "refs":{"hebrew_masoretic_absent": True}}]
    obj = {**GOOD, "verses": verses}
    errs = validate_chapter_ot(obj)
    assert not any("hebrew" in e.lower() for e in errs), f"Unexpected errors: {errs}"

def test_empty_hebrew_without_marker_errors():
    verses = [{"verse":1,"latin_vulgate":"l","hebrew_masoretic":"","king_james":"k"}]
    obj = {**GOOD, "verses": verses}
    errs = validate_chapter_ot(obj)
    assert any("hebrew" in e.lower() for e in errs), "Expected empty hebrew to be flagged"
