"""Tests for LXX book registry + LXX<->MT versification map."""
from tools.lxx_versification import mt_ref, lxx_books


def test_psalms_offset_known_case():
    # LXX Psalm 9 merges MT Psalms 9 + 10.  The LXX superscription counts as
    # verse 1 (shifting content by +1), so LXX Ps 9:2-21 = MT Ps 9:1-20, and
    # LXX Ps 9:22 is the first verse of MT Ps 10.  This pair is recorded in
    # docs/FORMATS-lxx.md (TVTMS Psalms offset) and verified in the TVTMS file:
    #   BIBLES row for $Psa.9:1-10:18 has column "Greek" -> Psa.9:22-39 aligned
    #   to Hebrew column Psa.10:1-18 (i.e. LXX Psa.9:22 == MT Psa.10:1).
    assert mt_ref("PSA", 9, 22) == "10:1"


def test_deuterocanon_has_no_mt():
    # 1 Maccabees has no MT (Hebrew) counterpart.
    assert mt_ref("1MA", 1, 1) is None


def test_non_lxx_code_has_no_mt():
    # 2ES = 4 Ezra / Latin apocalypse; NOT a Greek LXX book and has no MT
    # counterpart.  mt_ref must return None, not an identity string.
    assert mt_ref("2ES", 1, 1) is None


def test_lxx_books_present_with_codes():
    books = lxx_books()
    assert len(books) >= 39
    codes = {b["code"] for b in books}
    assert {"GEN", "PSA", "1MA", "3MA", "4MA", "ODE", "PSS"} <= codes
    assert all(b.get("testament") == "lxx" for b in books)
