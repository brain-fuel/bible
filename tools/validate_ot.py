"""Structural validation and alignment oracles for the OT corpus."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BODY = ("latin_vulgate", "hebrew_masoretic", "king_james")
TOTAL_OT_VERSES = 23145
EXPECTED_ABSENT = {"latin_vulgate": 10, "hebrew_masoretic": 0}

# (code, kjv_chapter, kjv_verse, expected hebrew "chap:verse")
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
        for key in BODY:
            if not v.get(key):
                # king_james is never absent -- always an error
                if key == "king_james":
                    errs.append(f"{tag}:{v.get('verse')}: empty {key}")
                elif key == "latin_vulgate":
                    if refs.get("latin_vulgate") != "absent":
                        errs.append(f"{tag}:{v.get('verse')}: empty {key}")
                elif key == "hebrew_masoretic":
                    if refs.get("hebrew_masoretic_absent") is not True:
                        errs.append(f"{tag}:{v.get('verse')}: empty {key}")
        if refs:
            hv = refs.get("hebrew_masoretic", "")
            if hv and len(hv.split(":")) != 2:
                errs.append(f"{tag}:{v.get('verse')}: malformed ref {hv}")
    return errs


def _load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def main():
    errs = []
    total = 0
    found_ref = {}
    absent_latin = 0
    absent_hebrew = 0
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
                if "hebrew_masoretic" in refs:
                    found_ref[(code, chapter, v["verse"])] = refs["hebrew_masoretic"]
                if refs.get("latin_vulgate") == "absent":
                    absent_latin += 1
                if refs.get("hebrew_masoretic_absent") is True:
                    absent_hebrew += 1
        if found != meta["chapters"]:
            errs.append(f"{code}: expected {meta['chapters']} files, found {found}")
    if total != TOTAL_OT_VERSES:
        errs.append(f"total OT verses {total}, expected {TOTAL_OT_VERSES}")
    if absent_latin != EXPECTED_ABSENT["latin_vulgate"]:
        errs.append(
            f"absent latin_vulgate count {absent_latin}, expected {EXPECTED_ABSENT['latin_vulgate']}"
        )
    if absent_hebrew != EXPECTED_ABSENT["hebrew_masoretic"]:
        errs.append(
            f"absent hebrew_masoretic count {absent_hebrew}, expected {EXPECTED_ABSENT['hebrew_masoretic']}"
        )
    for code, ch, v, expected in ALIGNMENT_ORACLES:
        got = found_ref.get((code, ch, v))
        if got != expected:
            errs.append(f"alignment oracle {code} {ch}:{v}: expected hebrew {expected}, got {got}")
    for e in errs:
        print("ERROR:", e)
    print(f"OT validation: {len(errs)} error(s); {total} verses")
    print(f"absent markers: latin_vulgate={absent_latin}, hebrew_masoretic={absent_hebrew}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
