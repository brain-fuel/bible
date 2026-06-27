from tools.validate_ot import validate_chapter_ot, EXPECTED_ABSENT, BODY, BASE_ID

GOOD = {"book_id":"GEN","latin_name":"L","hebrew_name":"H","english_name":"E",
        "chapter":1,"verses":[
            {"verse":1,"latin_vulgate":"a","hebrew_masoretic":"x","king_james":"k"},
            {"verse":2,"latin_vulgate":"b","hebrew_masoretic":"y","king_james":"m"}]}


def test_body_is_registry_driven_base_last():
    assert BODY == ("latin_vulgate", "hebrew_masoretic", "king_james")
    assert BASE_ID == "king_james"


def test_clean_chapter_ok():
    assert validate_chapter_ot(GOOD) == []


def test_noncontiguous_flagged():
    bad = {**GOOD, "verses":[{"verse":1,"latin_vulgate":"a","hebrew_masoretic":"x","king_james":"k"},
                              {"verse":3,"latin_vulgate":"b","hebrew_masoretic":"y","king_james":"m"}]}
    assert any("contiguous" in e for e in validate_chapter_ot(bad))


def test_empty_hebrew_flagged():
    bad = {**GOOD, "verses":[{"verse":1,"latin_vulgate":"a","hebrew_masoretic":"","king_james":"k"}]}
    assert any("hebrew" in e.lower() for e in validate_chapter_ot(bad))


# --- normalized absent markers: refs[edition] = {"absent": true} ---

def test_empty_latin_with_absent_marker_ok():
    verses = [{"verse":1,"latin_vulgate":"","hebrew_masoretic":"x","king_james":"k",
               "refs":{"latin_vulgate":{"absent":True}}}]
    errs = validate_chapter_ot({**GOOD, "verses": verses})
    assert not any("latin" in e.lower() for e in errs), f"Unexpected errors: {errs}"


def test_empty_latin_without_marker_errors():
    verses = [{"verse":1,"latin_vulgate":"","hebrew_masoretic":"x","king_james":"k"}]
    errs = validate_chapter_ot({**GOOD, "verses": verses})
    assert any("latin" in e.lower() for e in errs)


def test_empty_kjv_always_errors_even_with_marker():
    verses = [{"verse":1,"latin_vulgate":"l","hebrew_masoretic":"x","king_james":"",
               "refs":{"king_james":{"absent":True}}}]
    errs = validate_chapter_ot({**GOOD, "verses": verses})
    assert any("king_james" in e.lower() for e in errs)


def test_empty_hebrew_with_absent_marker_ok():
    verses = [{"verse":1,"latin_vulgate":"l","hebrew_masoretic":"","king_james":"k",
               "refs":{"hebrew_masoretic":{"absent":True}}}]
    errs = validate_chapter_ot({**GOOD, "verses": verses})
    assert not any("hebrew" in e.lower() for e in errs), f"Unexpected errors: {errs}"


def test_empty_hebrew_without_marker_errors():
    verses = [{"verse":1,"latin_vulgate":"l","hebrew_masoretic":"","king_james":"k"}]
    errs = validate_chapter_ot({**GOOD, "verses": verses})
    assert any("hebrew" in e.lower() for e in errs)


def test_malformed_src_flagged():
    verses = [{"verse":1,"latin_vulgate":"a","hebrew_masoretic":"x","king_james":"k",
               "refs":{"hebrew_masoretic":{"src":"3:2:9"}}}]
    errs = validate_chapter_ot({**GOOD, "verses": verses})
    assert any("malformed" in e.lower() for e in errs)


def test_well_formed_src_ok():
    verses = [{"verse":1,"latin_vulgate":"a","hebrew_masoretic":"x","king_james":"k",
               "refs":{"hebrew_masoretic":{"src":"3:2"}}}]
    assert validate_chapter_ot({**GOOD, "verses": verses}) == []


# --- absent-count gate ---

def test_expected_absent_values():
    assert EXPECTED_ABSENT["latin_vulgate"] == 10
    assert EXPECTED_ABSENT["hebrew_masoretic"] == 0
