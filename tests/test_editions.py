from tools.editions import load_editions, editions_for

def test_three_canonical_editions_registered():
    ids = {e["id"] for e in load_editions()}
    assert {"latin_vulgate", "greek_textus_receptus", "king_james", "hebrew_masoretic"} <= ids

def test_ot_editions_are_latin_hebrew_kjv_in_order():
    ot = [e["id"] for e in editions_for("ot")]
    assert ot == ["king_james", "latin_vulgate", "hebrew_masoretic"]

def test_kjv_is_base_versification():
    kjv = next(e for e in load_editions() if e["id"] == "king_james")
    assert kjv["versification"] == "kjv"
    heb = next(e for e in load_editions() if e["id"] == "hebrew_masoretic")
    assert heb["versification"] == "masoretic"
