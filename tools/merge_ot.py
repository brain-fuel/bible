"""Merge KJV base with Latin and Hebrew editions into OT chapter objects."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_vmap():
    p = ROOT / "data" / "versification" / "ot-versification.json"
    return json.loads(p.read_text(encoding="utf-8"))


def masoretic_ref(code, kjv_chapter, kjv_verse, vmap):
    key = f"{code} {kjv_chapter}:{kjv_verse}"
    return vmap["hebrew"].get(key, f"{kjv_chapter}:{kjv_verse}")


def build_chapter(meta, kjv_chapter, kjv_verses, latin_by_kjv, hebrew_by_kjv,
                  hebrew_ref_by_kjv):
    verses = []
    for v in sorted(kjv_verses):
        verse = {
            "verse": v,
            "latin_vulgate": latin_by_kjv.get(v, ""),
            "hebrew_masoretic": hebrew_by_kjv.get(v, ""),
            "king_james": kjv_verses[v],
        }
        href = hebrew_ref_by_kjv.get(v, f"{kjv_chapter}:{v}")
        if href != f"{kjv_chapter}:{v}":
            verse["refs"] = {"hebrew_masoretic": href}
        verses.append(verse)
    return {
        "book_id": meta["code"],
        "latin_name": meta["latin_name"],
        "hebrew_name": meta["hebrew_name"],
        "english_name": meta["english_name"],
        "chapter": kjv_chapter,
        "verses": verses,
    }
