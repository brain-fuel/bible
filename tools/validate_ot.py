"""Structural validation and alignment oracles for the OT corpus.

Edition columns, the base, and absent/divergence semantics are derived from the
edition registry, so this validator does not hardcode which texts exist. Refs
are the normalized shape ``refs[<edition_id>] = {"src": "c:v", "absent": true}``.
"""
import json
import sys
from pathlib import Path

from tools.editions import editions_for

ROOT = Path(__file__).resolve().parents[1]


def _ot_output_editions():
    eds = editions_for("ot")
    base = next(e for e in eds if e.get("base"))
    out = [e for e in eds if not e.get("base")] + [base]
    return out, base["id"]


_OUT_EDS, BASE_ID = _ot_output_editions()
BODY = tuple(e["id"] for e in _OUT_EDS)
NONBASE = tuple(eid for eid in BODY if eid != BASE_ID)

TOTAL_OT_VERSES = 23145
# Verses where a non-base edition is genuinely absent (no text at any position).
EXPECTED_ABSENT = {"latin_vulgate": 10, "hebrew_masoretic": 0,
                   "douay_rheims": 13, "finnish_biblia": 0}
# Verses relocated by versification divergence (a recorded src pointer).
EXPECTED_SRC = {"latin_vulgate": 2835, "hebrew_masoretic": 1971,
                "douay_rheims": 2835, "finnish_biblia": 0}

# (code, kjv_chapter, kjv_verse, expected hebrew src "chap:verse")
ALIGNMENT_ORACLES = [
    ("PSA", 3, 1, "3:2"),
    ("PSA", 3, 8, "3:9"),
    ("MAL", 4, 4, "3:22"),
    ("MAL", 4, 6, "3:24"),
    ("JOE", 2, 28, "3:1"),
]


def validate_chapter_ot(obj):
    errs = []
    tag = f"{obj.get('book_id','?')} {obj.get('chapter','?')}"
    verses = obj.get("verses", [])
    if not verses:
        return [f"{tag}: no verses"]
    nums = [v["verse"] for v in verses]
    if nums != list(range(1, len(nums) + 1)):
        errs.append(f"{tag}: verse numbers not contiguous from 1: {nums}")
    for v in verses:
        refs = v.get("refs") or {}
        for eid in BODY:
            if not v.get(eid):
                # The base edition is never absent -- always an error.
                if eid == BASE_ID:
                    errs.append(f"{tag}:{v.get('verse')}: empty {eid}")
                elif refs.get(eid, {}).get("absent") is not True:
                    errs.append(f"{tag}:{v.get('verse')}: empty {eid}")
        for eid, entry in refs.items():
            src = entry.get("src", "")
            if src and len(src.split(":")) != 2:
                errs.append(f"{tag}:{v.get('verse')}: malformed src {src}")
    return errs


def _load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def main():
    errs = []
    total = 0
    found_src = {}
    absent = {eid: 0 for eid in NONBASE}
    src_count = {eid: 0 for eid in NONBASE}
    for meta in _load_books():
        code = meta["code"]
        found = 0
        for chapter in range(1, meta["chapters"] + 1):
            p = ROOT / "bible" / "ot" / code / f"{chapter:03d}.json"
            if not p.exists():
                errs.append(f"{code} {chapter}: missing file")
                continue
            found += 1
            obj = json.loads(p.read_text(encoding="utf-8"))
            errs.extend(validate_chapter_ot(obj))
            total += len(obj.get("verses", []))
            for v in obj.get("verses", []):
                refs = v.get("refs") or {}
                for eid, entry in refs.items():
                    if eid not in absent:
                        continue
                    if entry.get("absent") is True:
                        absent[eid] += 1
                    if entry.get("src"):
                        src_count[eid] += 1
                        if eid == "hebrew_masoretic":
                            found_src[(code, chapter, v["verse"])] = entry["src"]
        if found != meta["chapters"]:
            errs.append(f"{code}: expected {meta['chapters']} files, found {found}")
    if total != TOTAL_OT_VERSES:
        errs.append(f"total OT verses {total}, expected {TOTAL_OT_VERSES}")
    for eid, expected in EXPECTED_ABSENT.items():
        if absent.get(eid, 0) != expected:
            errs.append(f"absent {eid} count {absent.get(eid, 0)}, expected {expected}")
    for eid, expected in EXPECTED_SRC.items():
        if src_count.get(eid, 0) != expected:
            errs.append(f"src {eid} count {src_count.get(eid, 0)}, expected {expected}")
    for code, ch, v, expected in ALIGNMENT_ORACLES:
        got = found_src.get((code, ch, v))
        if got != expected:
            errs.append(f"alignment oracle {code} {ch}:{v}: expected hebrew {expected}, got {got}")
    for e in errs:
        print("ERROR:", e)
    print(f"OT validation: {len(errs)} error(s); {total} verses")
    print(f"absent markers: {absent}")
    print(f"src pointers: {src_count}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
