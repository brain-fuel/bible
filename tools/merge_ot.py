"""Merge registry editions into OT chapter objects, driven by the edition registry.

The base edition (KJV) defines verse positions. Every other edition's text is
placed at the base position it corresponds to; when its source versification
diverges, the source "chapter:verse" is recorded in ``refs[<edition_id>].src``.
Empty text is recorded as ``refs[<edition_id>].absent = true``. Both markers are
uniform across editions, so a new parallel text needs only a registry row.
"""
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


def source_ref(code, kjv_chapter, kjv_verse, vmap, vmap_key):
    """Map a base (KJV) ref to an edition's source 'chap:verse'.

    Returns the identity ``f"{chapter}:{verse}"`` when the edition has no
    versification namespace (``vmap_key`` is falsy) or no mapping for this ref.
    """
    identity = f"{kjv_chapter}:{kjv_verse}"
    if not vmap_key:
        return identity
    key = f"{code} {kjv_chapter}:{kjv_verse}"
    return vmap.get(vmap_key, {}).get(key, identity)


def build_chapter(meta, output_editions, base_id, chapter, columns):
    """Assemble one chapter object from per-edition columns.

    ``output_editions`` are edition dicts in column order (base last).
    ``columns`` maps ``edition_id -> {verse:int -> {"text": str, "src": str|None}}``.
    Verse numbers are taken from the base edition's column. The ``src`` of a cell
    is the diverging source ref (or ``None`` for identity / the base edition).
    """
    base_col = columns[base_id]
    verses = []
    for v in sorted(base_col):
        verse = {"verse": v}
        for ed in output_editions:
            verse[ed["id"]] = columns[ed["id"]][v]["text"]
        refs = {}
        for ed in output_editions:
            if ed["id"] == base_id:
                continue
            cell = columns[ed["id"]][v]
            entry = {}
            if cell.get("src"):
                entry["src"] = cell["src"]
            if cell["text"] == "":
                entry["absent"] = True
            if entry:
                refs[ed["id"]] = entry
        if refs:
            verse["refs"] = refs
        verses.append(verse)
    obj = {"book_id": meta["code"]}
    for ed in output_editions:
        obj[ed["display_name_field"]] = meta[ed["display_name_field"]]
    obj["chapter"] = chapter
    obj["verses"] = verses
    return obj
