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
