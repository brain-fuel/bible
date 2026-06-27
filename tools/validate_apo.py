"""Structural validation for the Apocrypha corpus (KJVA spine + Finnish).

BODY/base derive from the registry. Finnish is placed by identity (no map),
so the only refs are absent markers; the pinned counts lock the partial
Finnish coverage (I/II Esdras placeholders + Additions to Esther are fully
absent; see plan/README).
"""
import json
import sys
from pathlib import Path

from tools.editions import editions_for
from tools.validate_ot import validate_chapter

ROOT = Path(__file__).resolve().parents[1]


def _apo_output_editions():
    eds = editions_for("apo")
    base = next(e for e in eds if e.get("base"))
    out = [e for e in eds if not e.get("base")] + [base]
    return out, base["id"]


_OUT, BASE_ID = _apo_output_editions()
BODY = tuple(e["id"] for e in _OUT)
NONBASE = tuple(eid for eid in BODY if eid != BASE_ID)

TOTAL_APO_VERSES = 5717
EXPECTED_ABSENT = {"finnish_biblia": 1505}
# Books FinBiblia ships empty / under a different unit -> fully Finnish-absent.
EXPECTED_BOOK_ABSENT = {"1ES": 448, "2ES": 874, "ADE": 117}


def _load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "apo"]


def main():
    errs = []
    total = 0
    absent = {eid: 0 for eid in NONBASE}
    book_finnish_absent = {}
    for meta in _load_books():
        code = meta["code"]
        found = 0
        ba = 0
        for chapter in range(1, meta["chapters"] + 1):
            p = ROOT / "bible" / "apo" / code / f"{chapter:03d}.json"
            if not p.exists():
                errs.append(f"{code} {chapter}: missing file")
                continue
            found += 1
            obj = json.loads(p.read_text(encoding="utf-8"))
            errs.extend(validate_chapter(obj, BODY, BASE_ID))
            total += len(obj.get("verses", []))
            for v in obj.get("verses", []):
                refs = v.get("refs") or {}
                for eid, entry in refs.items():
                    if eid in absent and entry.get("absent") is True:
                        absent[eid] += 1
                        if eid == "finnish_biblia":
                            ba += 1
        book_finnish_absent[code] = ba
        if found != meta["chapters"]:
            errs.append(f"{code}: expected {meta['chapters']} files, found {found}")
    if total != TOTAL_APO_VERSES:
        errs.append(f"total apo verses {total}, expected {TOTAL_APO_VERSES}")
    for eid, exp in EXPECTED_ABSENT.items():
        if absent.get(eid, 0) != exp:
            errs.append(f"absent {eid} count {absent.get(eid, 0)}, expected {exp}")
    for code, exp in EXPECTED_BOOK_ABSENT.items():
        got = book_finnish_absent.get(code, 0)
        if got != exp:
            errs.append(f"{code} finnish-absent {got}, expected {exp} (fully absent book)")
    for e in errs:
        print("ERROR:", e)
    print(f"Apo validation: {len(errs)} error(s); {total} verses")
    print(f"absent markers: {absent}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
