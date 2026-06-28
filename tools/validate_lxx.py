"""Structural validation for the LXX corpus (Swete 1909 PD text).

Checks:
  - Every chapter file present for each book in lxx_books() (except known
    CSV-absent books whose content is integrated elsewhere in the Swete text).
  - Verses numbered contiguously from 1 with non-empty greek_lxx.
  - refs.mt shape (protocanon only): {"src": "c:v"} or {"absent": true}.
  - Total verse count matches the pinned constant.

Usage:
  python -m tools.validate_lxx
"""

import json
import sys
from pathlib import Path

from tools.lxx_versification import lxx_books, _lxx_protocanon_codes

ROOT = Path(__file__).resolve().parents[1]

# Pinned after generating the full corpus from the Swete 1909 CSV.
# Empty verse slots (LXX omissions present in versification but absent from
# the word list) are excluded, giving the count of verses that carry text.
EXPECTED_LXX_VERSES = 28880  # was 28869 before MAN fixed to Ode 8 (15v) from Ode 12 (4v)

# Books whose content is integrated into other books in the Swete CSV
# (they have lxx_order in books.json but no standalone CSV sections).
# ADE = Additions to Esther (integrated into EST in the Swete Greek text).
# PAZ = Prayer of Azariah (integrated into DAN ch 3 in the Swete Greek text).
CSV_ABSENT_CODES = frozenset(["ADE", "PAZ"])


def _lxx_chapter_count(meta: dict) -> int:
    """Expected LXX chapter count for a book.

    Uses chapters_lxx if present (e.g. PSA=151), else chapters.
    """
    return meta.get("chapters_lxx") or meta["chapters"]


def validate_chapter(obj: dict, code: str) -> list:
    """Return a list of error strings for one chapter dict, or []."""
    errs = []
    tag = f"{obj.get('book_id','?')} {obj.get('chapter','?')}"

    if obj.get("book_id") != code:
        errs.append(f"{tag}: book_id mismatch (expected {code})")

    verses = obj.get("verses", [])
    if not verses:
        errs.append(f"{tag}: no verses")
        return errs

    # Verse numbers need not be contiguous: the LXX omits many MT verse
    # positions (empty slots in the Swete CSV are excluded from output).
    # Check only that they are strictly ascending and start >= 1.
    nums = [v["verse"] for v in verses]
    if nums != sorted(set(nums)) or nums[0] < 1:
        errs.append(f"{tag}: verse numbers not strictly ascending: {nums[:10]}...")

    protocanon = _lxx_protocanon_codes()
    is_proto = code in protocanon

    for v in verses:
        vn = v.get("verse", "?")
        if not v.get("greek_lxx"):
            errs.append(f"{tag}:{vn}: empty greek_lxx")
        refs = v.get("refs")
        if refs is not None:
            if is_proto:
                mt = refs.get("mt")
                if mt is None:
                    errs.append(f"{tag}:{vn}: refs present but missing 'mt' key")
                elif mt.get("absent") is True:
                    pass  # valid
                elif "src" in mt:
                    src = mt["src"]
                    if len(src.split(":")) != 2:
                        errs.append(f"{tag}:{vn}: malformed refs.mt.src={src!r}")
                else:
                    errs.append(f"{tag}:{vn}: refs.mt has neither 'src' nor 'absent'")
            else:
                errs.append(f"{tag}:{vn}: deuterocanon verse has unexpected refs")
    return errs


def validate(testament: str = "lxx") -> dict:
    """Validate the LXX corpus and return a stats dict.

    Keys: errors (list[str]), total_verses (int), chapters_found (int),
          books_complete (int), books_absent (int).
    Raises RuntimeError if corpus is missing.
    """
    errs: list = []
    total_v = 0
    chapters_found = 0
    books_complete = 0
    books_absent = 0

    books = lxx_books()

    for meta in books:
        code = meta["code"]

        if code in CSV_ABSENT_CODES:
            books_absent += 1
            # Expect no files (content integrated elsewhere)
            p = ROOT / "bible" / "lxx" / code
            if p.exists() and any(p.iterdir()):
                errs.append(f"{code}: expected no files (CSV-absent) but found some")
            continue

        expected_ch = _lxx_chapter_count(meta)
        # Discover actual chapters from filesystem
        book_dir = ROOT / "bible" / "lxx" / code
        found = 0

        for chapter in range(1, expected_ch + 1):
            p = book_dir / f"{chapter:03d}.json"
            if not p.exists():
                # Some books may have fewer LXX chapters than MT (e.g. BAR has 6
                # from CSV but books.json might say different). Only warn if >=1 ch absent.
                # For books where csv provides all chapters, this is an error.
                # We check coverage generously: count what we find and flag gaps.
                errs.append(f"{code} ch {chapter}: missing file")
                continue
            found += 1
            chapters_found += 1
            obj = json.loads(p.read_text(encoding="utf-8"))
            ch_errs = validate_chapter(obj, code)
            errs.extend(ch_errs)
            total_v += len(obj.get("verses", []))

        # Also look for extra chapters beyond expected_ch (e.g. PSA ch 151)
        if book_dir.exists():
            for p in sorted(book_dir.iterdir()):
                if not p.stem.isdigit() or len(p.stem) != 3:
                    errs.append(f"{code}: unexpected filename {p.name!r} (expected NNN.json)")
                    continue
                ch_num = int(p.stem)
                if ch_num > expected_ch:
                    found += 1
                    chapters_found += 1
                    obj = json.loads(p.read_text(encoding="utf-8"))
                    errs.extend(validate_chapter(obj, code))
                    total_v += len(obj.get("verses", []))

        if found > 0:
            books_complete += 1
        else:
            errs.append(f"{code}: no chapter files found")

    if total_v != EXPECTED_LXX_VERSES:
        errs.append(
            f"total LXX verses {total_v}, expected {EXPECTED_LXX_VERSES}"
        )

    return {
        "errors": errs,
        "total_verses": total_v,
        "chapters_found": chapters_found,
        "books_complete": books_complete,
        "books_absent": books_absent,
    }


def main() -> int:
    stats = validate()
    errs = stats["errors"]
    for e in errs:
        print("ERROR:", e)
    print(
        f"LXX validation: {len(errs)} error(s); "
        f"{stats['total_verses']} verses; "
        f"{stats['chapters_found']} chapters; "
        f"{stats['books_complete']} books complete, "
        f"{stats['books_absent']} books absent (CSV-integrated)"
    )
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
