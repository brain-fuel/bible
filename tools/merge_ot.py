"""Merge KJV base with Latin and Hebrew editions into OT chapter objects."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def merge_vmaps(base, supp):
    """Deep-merge supplement onto base, returning only {'hebrew':..., 'latin':...}."""
    merged_hebrew = {**base.get("hebrew", {}), **supp.get("hebrew", {})}
    merged_latin = {**base.get("latin", {}), **supp.get("latin", {})}
    return {"hebrew": merged_hebrew, "latin": merged_latin}


def load_vmap():
    p = ROOT / "data" / "versification" / "ot-versification.json"
    base = json.loads(p.read_text(encoding="utf-8"))
    supp_p = ROOT / "data" / "versification" / "ot-versification-supplement.json"
    if supp_p.exists():
        supp = json.loads(supp_p.read_text(encoding="utf-8"))
        return merge_vmaps(base, supp)
    return {"hebrew": base.get("hebrew", {}), "latin": base.get("latin", {})}


def masoretic_ref(code, kjv_chapter, kjv_verse, vmap):
    key = f"{code} {kjv_chapter}:{kjv_verse}"
    return vmap["hebrew"].get(key, f"{kjv_chapter}:{kjv_verse}")


def build_chapter(meta, kjv_chapter, kjv_verses, latin_by_kjv, hebrew_by_kjv,
                  hebrew_ref_by_kjv):
    verses = []
    for v in sorted(kjv_verses):
        latin_text = latin_by_kjv.get(v, "")
        hebrew_text = hebrew_by_kjv.get(v, "")
        verse = {
            "verse": v,
            "latin_vulgate": latin_text,
            "hebrew_masoretic": hebrew_text,
            "king_james": kjv_verses[v],
        }
        refs = {}
        href = hebrew_ref_by_kjv.get(v, f"{kjv_chapter}:{v}")
        if href != f"{kjv_chapter}:{v}":
            refs["hebrew_masoretic"] = href
        if latin_text == "":
            refs["latin_vulgate"] = "absent"
        if hebrew_text == "":
            refs["hebrew_masoretic_absent"] = True
        if refs:
            verse["refs"] = refs
        verses.append(verse)
    return {
        "book_id": meta["code"],
        "latin_name": meta["latin_name"],
        "hebrew_name": meta["hebrew_name"],
        "english_name": meta["english_name"],
        "chapter": kjv_chapter,
        "verses": verses,
    }
