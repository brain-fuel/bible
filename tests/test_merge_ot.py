from tools.merge_ot import source_ref, build_chapter, merge_vmaps

VMAP = {"hebrew": {"PSA 3:1": "3:2", "PSA 3:2": "3:3"}, "latin": {"PSA 9:1": "9:2"}}

# Edition dicts as the generator passes them: column order, base last.
LAT = {"id": "latin_vulgate", "display_name_field": "latin_name"}
HEB = {"id": "hebrew_masoretic", "display_name_field": "hebrew_name"}
KJV = {"id": "king_james", "display_name_field": "english_name", "base": True}
OUT = [LAT, HEB, KJV]
META = {"code": "PSA", "latin_name": "L", "hebrew_name": "H", "english_name": "E"}


def _cell(text, src=None):
    return {"text": text, "src": src}


# --- generic source_ref (replaces hardcoded masoretic_ref/_latin_by_kjv) ---

def test_source_ref_identity_when_no_vmap_key():
    assert source_ref("GEN", 1, 1, VMAP, None) == "1:1"


def test_source_ref_identity_when_unmapped():
    assert source_ref("GEN", 1, 1, VMAP, "hebrew") == "1:1"


def test_source_ref_uses_namespace():
    assert source_ref("PSA", 3, 1, VMAP, "hebrew") == "3:2"
    assert source_ref("PSA", 9, 1, VMAP, "latin") == "9:2"


# --- build_chapter: normalized per-edition refs, base last ---

def test_build_chapter_records_src_pointer_when_diverging():
    columns = {
        "king_james": {1: _cell("kjv1"), 2: _cell("kjv2")},
        "latin_vulgate": {1: _cell("lat1"), 2: _cell("lat2")},
        "hebrew_masoretic": {1: _cell("heb1", "3:2"), 2: _cell("heb2", "3:3")},
    }
    ch = build_chapter(META, OUT, "king_james", 3, columns)
    assert ch["book_id"] == "PSA" and ch["chapter"] == 3
    v1 = ch["verses"][0]
    assert v1["verse"] == 1 and v1["king_james"] == "kjv1"
    assert v1["hebrew_masoretic"] == "heb1"
    assert v1["refs"] == {"hebrew_masoretic": {"src": "3:2"}}
    # header key order: book_id, display names (base last), chapter, verses
    assert list(ch) == ["book_id", "latin_name", "hebrew_name", "english_name",
                        "chapter", "verses"]
    # verse key order: verse, editions (base last), refs
    assert list(v1) == ["verse", "latin_vulgate", "hebrew_masoretic",
                        "king_james", "refs"]


def test_build_chapter_omits_refs_when_identity():
    columns = {
        "king_james": {1: _cell("k")},
        "latin_vulgate": {1: _cell("l")},
        "hebrew_masoretic": {1: _cell("h")},
    }
    ch = build_chapter(META, OUT, "king_james", 1, columns)
    assert "refs" not in ch["verses"][0]


def test_build_chapter_empty_text_marks_absent_uniformly():
    columns = {
        "king_james": {1: _cell("k")},
        "latin_vulgate": {1: _cell("")},
        "hebrew_masoretic": {1: _cell("h")},
    }
    v = build_chapter(META, OUT, "king_james", 26, columns)["verses"][0]
    assert v["latin_vulgate"] == ""
    assert v["refs"] == {"latin_vulgate": {"absent": True}}


def test_build_chapter_src_and_absent_together():
    """Same edition can be both relocated (src) and empty (absent)."""
    columns = {
        "king_james": {1: _cell("k")},
        "latin_vulgate": {1: _cell("")},
        "hebrew_masoretic": {1: _cell("", "3:2")},
    }
    v = build_chapter(META, OUT, "king_james", 3, columns)["verses"][0]
    assert v["refs"]["latin_vulgate"] == {"absent": True}
    assert v["refs"]["hebrew_masoretic"] == {"src": "3:2", "absent": True}


def test_build_chapter_base_never_in_refs():
    columns = {
        "king_james": {1: _cell("k")},
        "latin_vulgate": {1: _cell("l")},
        "hebrew_masoretic": {1: _cell("h", "1:1")},  # src equals identity -> already None upstream
    }
    # base column carries src=None; even if a stray src appeared it is skipped
    v = build_chapter(META, OUT, "king_james", 1, columns)["verses"][0]
    assert "king_james" not in (v.get("refs") or {})


# --- supplement merging (unchanged contract) ---

def test_merge_vmaps_supplement_adds_entry():
    base = {"hebrew": {"GEN 1:1": "1:2"}, "latin": {}}
    supp = {"_note": "test", "hebrew": {"EXO 20:24": "20:21"}, "latin": {}}
    merged = merge_vmaps(base, supp)
    assert merged["hebrew"]["GEN 1:1"] == "1:2"
    assert merged["hebrew"]["EXO 20:24"] == "20:21"
    assert "_note" not in merged


def test_merge_vmaps_supplement_overrides_base():
    base = {"hebrew": {"PSA 3:1": "3:2"}, "latin": {}}
    supp = {"_note": "override", "hebrew": {"PSA 3:1": "3:99"}, "latin": {}}
    merged = merge_vmaps(base, supp)
    assert merged["hebrew"]["PSA 3:1"] == "3:99"


def test_merge_vmaps_drops_meta_keys():
    base = {"_attribution": "old", "hebrew": {}, "latin": {}}
    supp = {"_note": "n", "hebrew": {}, "latin": {}}
    merged = merge_vmaps(base, supp)
    assert list(merged.keys()) == ["hebrew", "latin"]
