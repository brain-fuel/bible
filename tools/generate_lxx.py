"""Generate the LXX corpus from the Swete 1909 public-domain text.

Reads:  data/cache/morph/raw/lxx/swete_*.csv (gitignored)
Writes: bible/lxx/<CODE>/NNN.json

Each chapter file has the shape:
  {
    "book_id": "GEN",
    "chapter": 1,
    "source": "Swete 1909 (Public Domain)",
    "verses": [
      {"verse": 1, "greek_lxx": "...", "refs": {"mt": {"src": "c:v"}}},
      ...
    ]
  }

refs.mt is included only for protocanon books:
  - {"src": "c:v"}  when the LXX verse maps to a different MT position
  - {"absent": true} when the verse has no MT counterpart (e.g. Psalm 151)
  - omitted entirely when LXX and MT numbering are identical (identity)

Deuterocanon / LXX-only books carry no refs at all.

Usage:
  python -m tools.generate_lxx            # full corpus
  python -m tools.generate_lxx --book RUT # single book
"""

import argparse
import json
import sys
from pathlib import Path

from tools.lxx_versification import lxx_books, mt_ref, _lxx_protocanon_codes
from tools.sources.lxx_source import LxxSource

ROOT = Path(__file__).resolve().parents[1]
PAD = 3
SOURCE_LABEL = "Swete 1909 (Public Domain)"


def build_chapter(code: str, chapter: int, src_verses: dict) -> dict:
    """Build a chapter JSON object from raw verse texts.

    Parameters
    ----------
    code       : str  -- e.g. "GEN", "PSA", "1MA"
    chapter    : int  -- chapter number (1-based)
    src_verses : dict -- {verse_int: greek_text}; text may already be NFC.

    Returns
    -------
    dict with keys: book_id, chapter, source, verses
    """
    protocanon = _lxx_protocanon_codes()
    is_protocanon = code in protocanon

    verses = []
    for v_num in sorted(src_verses):
        text = src_verses[v_num]
        verse_obj: dict = {"verse": v_num, "greek_lxx": text}

        if is_protocanon:
            mt = mt_ref(code, chapter, v_num)
            identity = f"{chapter}:{v_num}"
            if mt is None:
                verse_obj["refs"] = {"mt": {"absent": True}}
            elif mt != identity:
                verse_obj["refs"] = {"mt": {"src": mt}}
            # else identity -> no refs key

        verses.append(verse_obj)

    return {
        "book_id": code,
        "chapter": chapter,
        "source": SOURCE_LABEL,
        "verses": verses,
    }


def _out_path(code: str, chapter: int) -> Path:
    return ROOT / "bible" / "lxx" / code / f"{chapter:0{PAD}d}.json"


def write_book(meta: dict, src: LxxSource) -> int:
    """Generate all chapter files for one book. Returns number of chapters written."""
    code = meta["code"]
    chapters = src.chapters(meta)
    written = 0
    for chapter in chapters:
        verses = src.chapter(meta, chapter)
        if not verses:
            continue
        obj = build_chapter(code, chapter, verses)
        dest = _out_path(code, chapter)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bible/lxx/ corpus")
    parser.add_argument("--book", metavar="CODE",
                        help="Generate only this book code (e.g. RUT)")
    args = parser.parse_args()

    src = LxxSource()
    books = lxx_books()
    if args.book:
        books = [b for b in books if b["code"] == args.book]
        if not books:
            print(f"Unknown book code: {args.book}", file=sys.stderr)
            return 1

    total_ch = 0
    total_v = 0
    for meta in books:
        n = write_book(meta, src)
        total_ch += n
        if n > 0:
            # Count verses in written files
            code = meta["code"]
            for chapter in src.chapters(meta):
                p = _out_path(code, chapter)
                if p.exists():
                    obj = json.loads(p.read_text(encoding="utf-8"))
                    total_v += len(obj.get("verses", []))
        print(f"{meta['code']}: {n} chapters")

    print(f"done: {total_ch} chapters, {total_v} verses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
