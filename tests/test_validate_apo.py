from tools.validate_apo import (BODY, BASE_ID, TOTAL_APO_VERSES,
                                EXPECTED_ABSENT, EXPECTED_BOOK_ABSENT)


def test_apo_body_base_from_registry():
    assert BODY == ("finnish_biblia", "king_james_apocrypha")
    assert BASE_ID == "king_james_apocrypha"


def test_apo_pinned_oracles():
    assert TOTAL_APO_VERSES == 5717
    assert EXPECTED_ABSENT == {"finnish_biblia": 1505}
    assert EXPECTED_BOOK_ABSENT == {"1ES": 448, "2ES": 874, "ADE": 117}
