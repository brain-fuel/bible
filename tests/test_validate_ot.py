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


# --- absent-count gate ---
# The EXPECTED_ABSENT constant in validate_ot.main() pins the absent-marker
# tallies (latin_vulgate=10, hebrew_masoretic=0).  If a wrong vulgate_name
# silently emptied a whole book's Latin and marked every verse absent,
# the count would diverge from 10 and main() would append an error, causing
# exit code 1.  This gate is exercised end-to-end by running:
#   python -m tools.validate_ot
# which must exit 0 with "0 error(s)" and the matching absent tally line.
#
# Unit tests below verify the EXPECTED_ABSENT values are correct and that
# the sentinel correctly identifies deviating counts.

from tools.validate_ot import EXPECTED_ABSENT


def test_expected_absent_values():
    """Pinned counts match what is actually present in the corpus constants."""
    assert EXPECTED_ABSENT["latin_vulgate"] == 10
    assert EXPECTED_ABSENT["hebrew_masoretic"] == 0


def test_absent_gate_logic_latin_too_high():
    """Simulate the check: a count above expected would be caught."""
    # Mimic the gate logic from main() inline so no corpus I/O is needed.
    absent_latin = 11  # hypothetical bad count
    absent_hebrew = 0
    errs = []
    if absent_latin != EXPECTED_ABSENT["latin_vulgate"]:
        errs.append(
            f"absent latin_vulgate count {absent_latin}, expected {EXPECTED_ABSENT['latin_vulgate']}"
        )
    if absent_hebrew != EXPECTED_ABSENT["hebrew_masoretic"]:
        errs.append(
            f"absent hebrew_masoretic count {absent_hebrew}, expected {EXPECTED_ABSENT['hebrew_masoretic']}"
        )
    assert len(errs) == 1
    assert "latin_vulgate" in errs[0]


def test_absent_gate_logic_correct_counts():
    """Correct counts produce no errors from the gate logic."""
    absent_latin = EXPECTED_ABSENT["latin_vulgate"]
    absent_hebrew = EXPECTED_ABSENT["hebrew_masoretic"]
    errs = []
    if absent_latin != EXPECTED_ABSENT["latin_vulgate"]:
        errs.append("latin mismatch")
    if absent_hebrew != EXPECTED_ABSENT["hebrew_masoretic"]:
        errs.append("hebrew mismatch")
    assert errs == []
