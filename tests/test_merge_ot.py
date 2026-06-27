import json
import tempfile
from pathlib import Path
from tools.merge_ot import masoretic_ref, build_chapter, merge_vmaps

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

# --- TDD: supplement merging ---

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

# --- TDD: absent markers in build_chapter ---

def test_build_chapter_empty_latin_adds_absent_ref():
    meta = {"code":"LEV","latin_name":"L","hebrew_name":"H","english_name":"E"}
    ch = build_chapter(meta, 26, {1:"k"}, {}, {1:"h"}, {1:"26:1"})
    v = ch["verses"][0]
    assert v["latin_vulgate"] == ""
    assert v.get("refs", {}).get("latin_vulgate") == "absent"

def test_build_chapter_empty_latin_key_order():
    meta = {"code":"LEV","latin_name":"L","hebrew_name":"H","english_name":"E"}
    ch = build_chapter(meta, 26, {1:"k"}, {}, {1:"h"}, {1:"26:1"})
    v = ch["verses"][0]
    assert list(v) == ["verse","latin_vulgate","hebrew_masoretic","king_james","refs"]

def test_build_chapter_nonempty_both_no_absent_marker():
    meta = {"code":"GEN","latin_name":"L","hebrew_name":"H","english_name":"E"}
    ch = build_chapter(meta, 1, {1:"k"}, {1:"l"}, {1:"h"}, {1:"1:1"})
    v = ch["verses"][0]
    refs = v.get("refs", {})
    assert "latin_vulgate" not in refs
    assert "hebrew_masoretic_absent" not in refs

def test_build_chapter_both_ref_types_together():
    """Verse with diverging hebrew ref AND empty latin gets both in refs."""
    meta = {"code":"PSA","latin_name":"L","hebrew_name":"H","english_name":"E"}
    ch = build_chapter(meta, 3, {1:"k"}, {}, {1:"h"}, {1:"3:2"})
    v = ch["verses"][0]
    refs = v.get("refs", {})
    assert refs.get("latin_vulgate") == "absent"
    assert refs.get("hebrew_masoretic") == "3:2"
