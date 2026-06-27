from tools.editions import load_editions, editions_for

def test_three_canonical_editions_registered():
    ids = {e["id"] for e in load_editions()}
    assert {"latin_vulgate", "greek_textus_receptus", "king_james", "hebrew_masoretic"} <= ids

def test_ot_editions_are_latin_hebrew_kjv_in_order():
    ot = [e["id"] for e in editions_for("ot")]
    assert ot == ["king_james", "latin_vulgate", "hebrew_masoretic", "douay_rheims", "finnish_biblia"]

def test_kjv_is_base_versification():
    kjv = next(e for e in load_editions() if e["id"] == "king_james")
    assert kjv["versification"] == "kjv"
    heb = next(e for e in load_editions() if e["id"] == "hebrew_masoretic")
    assert heb["versification"] == "masoretic"


# --- self-describing rows: a new parallel text needs only a registry row ---

def _by_id():
    return {e["id"]: e for e in load_editions()}


def test_every_edition_has_display_name_field():
    """Header column name for each edition comes from a books.json field."""
    for e in load_editions():
        assert e.get("display_name_field"), f"{e['id']} missing display_name_field"


def test_display_name_fields_match_corpus_headers():
    eds = _by_id()
    assert eds["king_james"]["display_name_field"] == "english_name"
    assert eds["latin_vulgate"]["display_name_field"] == "latin_name"
    assert eds["hebrew_masoretic"]["display_name_field"] == "hebrew_name"
    assert eds["greek_textus_receptus"]["display_name_field"] == "greek_name"


def test_book_name_fields_select_source_book_name():
    """Which books.json field gives this source's per-book name."""
    eds = _by_id()
    assert eds["king_james"]["book_name_field"] == "kjv_name"
    assert eds["latin_vulgate"]["book_name_field"] == "vulgate_name"
    assert eds["hebrew_masoretic"]["book_name_field"] == "sefaria_name"


def test_vmap_key_only_on_diverging_editions():
    """Base (kjv) has no versification namespace; diverging editions name one."""
    eds = _by_id()
    assert "vmap_key" not in eds["king_james"]
    assert eds["latin_vulgate"]["vmap_key"] == "latin"
    assert eds["hebrew_masoretic"]["vmap_key"] == "hebrew"


def test_new_ot_editions_registered():
    eds = {e["id"]: e for e in load_editions()}
    drc = eds["douay_rheims"]
    fin = eds["finnish_biblia"]
    # Douay reuses the existing Latin versification map.
    assert drc["source"] == {"type": "scrollmapper", "key": "DRC"}
    assert drc["book_name_field"] == "kjv_name"
    assert drc["vmap_key"] == "latin"
    assert drc["display_name_field"] == "douay_name"
    assert drc["license"] == "PD"
    assert drc["testaments"] == ["ot"]
    # Finnish Biblia 1776 is already KJV-versified: identity, no vmap_key.
    assert fin["source"] == {"type": "scrollmapper", "key": "FinBiblia"}
    assert fin["book_name_field"] == "kjv_name"
    assert "vmap_key" not in fin
    assert fin["display_name_field"] == "finnish_name"
    assert fin["license"] == "PD"


def test_ot_output_order_with_new_editions():
    ot = [e["id"] for e in editions_for("ot")]
    assert ot == ["king_james", "latin_vulgate", "hebrew_masoretic",
                  "douay_rheims", "finnish_biblia"]
