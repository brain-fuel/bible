"""Task 4: CoNLL-U generation driver.

Reads the morph registry (data/morph-sources.json), loads each language's
normalized TSV via load_norm(), walks the L0 chapter files for that testament,
and writes morph/<testament>/<CODE>/NNN.conllu files.

CLI flags:
    --lang LANG    Only process this language code (e.g. grc, hbo).
    --book CODE    Only process this book code (e.g. 3JO).

Usage:
    python -m tools.generate_morph --lang grc --book 3JO
"""

import argparse
import json
from pathlib import Path

from tools.align_morph import align_verse, load_norm
from tools.conllu import write_file
from tools.strongs_headwords import load_hebrew_headwords

ROOT = Path(__file__).resolve().parents[1]


def _zero_pad(n: int) -> str:
    return f"{n:03d}"


def generate(lang_entry: dict, norm_by_ref: dict, book_filter: str | None) -> dict:
    """Write CoNLL-U files for all books in lang_entry's testament.

    Returns a summary dict: {code: {chapters, verses, tokens, unmatched, source_extra}}.
    """
    testament = lang_entry["testament"]
    l0_field = lang_entry["l0_field"]
    lang = lang_entry["lang"]

    # For Hebrew, load the Strong's headword map once so LEMMA = dictionary
    # headword (shared with build_lexicon) rather than the TAHOT pointed surface.
    # Greek is unchanged: TAGNT already supplies the dictionary form as lemma.
    headwords: "dict[str, str] | None" = None
    if lang == "hbo":
        xml_path = ROOT / "data" / "cache" / "morph" / "raw" / "strongs-hebrew.xml"
        headwords = load_hebrew_headwords(xml_path)
        print(f"  [hbo] Loaded {len(headwords)} Strong's headwords from strongs-hebrew.xml")

    # Load book list filtered to this testament
    books_path = ROOT / "data" / "books.json"
    all_books = json.loads(books_path.read_text(encoding="utf-8"))["books"]
    books = [b for b in all_books if b["testament"] == testament]

    if book_filter:
        books = [b for b in books if b["code"] == book_filter]
        if not books:
            raise SystemExit(f"Book '{book_filter}' not found in {testament} books list.")

    stats: dict = {}

    for book in books:
        code = book["code"]
        num_chapters = book["chapters"]
        book_stats = {"chapters": 0, "verses": 0, "tokens": 0, "unmatched": 0, "source_extra": 0}

        out_dir = ROOT / "morph" / testament / code
        out_dir.mkdir(parents=True, exist_ok=True)

        for ch_num in range(1, num_chapters + 1):
            ch_path = ROOT / "bible" / testament / code / f"{_zero_pad(ch_num)}.json"
            if not ch_path.exists():
                continue

            chapter_data = json.loads(ch_path.read_text(encoding="utf-8"))
            verses = chapter_data.get("verses", [])
            if not verses:
                continue

            sentences = []
            for verse_obj in verses:
                v_num = verse_obj["verse"]
                l0_text = verse_obj.get(l0_field, "")
                if not l0_text:
                    continue

                ref = f"{code}.{ch_num}.{v_num}"
                norm_rows = norm_by_ref.get(ref, [])
                tokens = align_verse(ref, l0_text, norm_rows, lang, headwords=headwords)

                # Accumulate stats. Align values are comma-joined under a
                # single Align= key, e.g. "Align=unmatched,source_extra:1".
                book_stats["verses"] += 1
                book_stats["tokens"] += len(tokens)
                for tok in tokens:
                    for part in tok.misc.split("|"):
                        if not part.startswith("Align="):
                            continue
                        for val in part[len("Align="):].split(","):
                            if val == "unmatched":
                                book_stats["unmatched"] += 1
                            elif val.startswith("source_extra:"):
                                try:
                                    book_stats["source_extra"] += int(val.split(":")[1])
                                except ValueError:
                                    pass

                sentences.append((ref, tokens))

            if sentences:
                out_path = out_dir / f"{_zero_pad(ch_num)}.conllu"
                write_file(out_path, sentences)
                book_stats["chapters"] += 1

        stats[code] = book_stats
        print(
            f"  {code}: {book_stats['chapters']} ch, {book_stats['verses']} vv, "
            f"{book_stats['tokens']} tok, "
            f"{book_stats['unmatched']} unmatched, "
            f"{book_stats['source_extra']} source_extra"
        )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate morpho-lexical CoNLL-U files.")
    parser.add_argument("--lang", required=False, help="Language code to process (grc or hbo).")
    parser.add_argument("--book", required=False, help="Book code to process (e.g. 3JO).")
    args = parser.parse_args()

    registry_path = ROOT / "data" / "morph-sources.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    for entry in registry["languages"]:
        if args.lang and entry["lang"] != args.lang:
            continue

        lang = entry["lang"]
        norm_path = ROOT / entry["norm"]
        if not norm_path.exists():
            print(f"[{lang}] Normalized TSV not found at {norm_path}; skipping.")
            print(f"  Run: python -m tools.morph_norm.stepbible_greek  (for grc)")
            continue

        print(f"[{lang}] Loading normalized TSV ...")
        norm_by_ref = load_norm(lang)
        print(f"  {len(norm_by_ref)} refs loaded.")

        print(f"[{lang}] Generating CoNLL-U files ...")
        stats = generate(entry, norm_by_ref, book_filter=args.book)
        total_tok = sum(s["tokens"] for s in stats.values())
        total_unmatched = sum(s["unmatched"] for s in stats.values())
        total_extra = sum(s["source_extra"] for s in stats.values())
        print(
            f"[{lang}] Done. Total: {total_tok} tokens, "
            f"{total_unmatched} unmatched, {total_extra} source_extra."
        )


if __name__ == "__main__":
    main()
