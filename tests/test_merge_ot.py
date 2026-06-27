from tools.merge_ot import masoretic_ref, build_chapter

VMAP = {"hebrew": {"PSA 3:1": "3:2", "PSA 3:2": "3:3"}, "latin": {}}

def test_masoretic_ref_identity_when_absent():
    assert masoretic_ref("GEN", 1, 1, VMAP) == "1:1"

def test_masoretic_ref_uses_map():
    assert masoretic_ref("PSA", 3, 1, VMAP) == "3:2"

def test_build_chapter_adds_refs_only_when_diverging():
    meta = {"code":"PSA","latin_name":"L","hebrew_name":"H","english_name":"E"}
    ch = build_chapter(
        meta, 3,
        kjv_verses={1:"kjv1", 2:"kjv2"},
        latin_by_kjv={1:"lat1", 2:"lat2"},
        hebrew_by_kjv={1:"heb1", 2:"heb2"},
        hebrew_ref_by_kjv={1:"3:2", 2:"3:3"},
    )
    assert ch["book_id"] == "PSA" and ch["chapter"] == 3
    v1 = ch["verses"][0]
    assert v1["verse"] == 1 and v1["king_james"] == "kjv1"
    assert v1["hebrew_masoretic"] == "heb1"
    assert v1["refs"] == {"hebrew_masoretic": "3:2"}  # diverges from 3:1
    # header key order
    assert list(ch) == ["book_id","latin_name","hebrew_name","english_name","chapter","verses"]
    # verse key order
    assert list(v1) == ["verse","latin_vulgate","hebrew_masoretic","king_james","refs"]

def test_build_chapter_omits_refs_when_identity():
    meta = {"code":"GEN","latin_name":"L","hebrew_name":"H","english_name":"E"}
    ch = build_chapter(meta, 1, {1:"k"}, {1:"l"}, {1:"h"}, {1:"1:1"})
    assert "refs" not in ch["verses"][0]
