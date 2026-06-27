"""STEPBible TAHOT normalizer -> fixed-schema intermediate TSV.

TAHOT is semi-structured: each verse is a block of #-prefixed summary lines
followed by a repeated "Eng (Heb) Ref & Type<TAB>..." column-header line and
then the per-word data rows.  A single csv.DictReader over the whole file does
NOT work.  We parse positionally, skipping # lines and repeated headers.

All TAHOT rows are from the Masoretic text (WLC); edition is always "WLC".

Strong's: we use col 8 "Root dStrong+Instance".  Canonical form obtained by:
  1. Stripping the instance marker (_A, _B, etc.)
  2. Stripping the trailing single-letter disambiguation suffix (H7225G -> H7225)

Lemma deviation: TAHOT has no explicit "dictionary form" column analogous to
TAGNT col 4.  Col 1 (Hebrew surface with full pointing and prefix/suffix
slashes) is used for both surface and lemma.  Downstream tasks that build the
lexicon layer (Tasks 4-5) will replace lemma with the BDB/Strong's form.
"""

import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = ["ref", "idx", "surface", "lemma", "strong", "xpos", "feats", "translit", "edition"]

# Column indices in TAHOT data rows (0-based)
_COL_REF = 0
_COL_HEBREW = 1
_COL_TRANSLIT = 2
_COL_GRAMMAR = 5
_COL_ROOT_STRONG = 8

# The repeated column-header line starts with this string (first field).
_TAHOT_HEADER_SENTINEL = "Eng (Heb) Ref & Type"


def _strip_heb_strong(raw: str) -> str:
    """Canonicalize a raw TAHOT Root dStrong+Instance string (col 8).

    Steps:
      1. Strip trailing instance marker _A, _B, etc.: H0853_A -> H0853
      2. Strip trailing single-letter disambiguation suffix: H7225G -> H7225
         (only if char at position 5 is alpha and positions 1-4 are digits)

    Numbers 9000-9999 are Tyndale-specific grammatical-particle tags; they
    are kept as-is (no disambiguation suffix in practice, but the rule still
    applies correctly).
    """
    s = raw.strip()
    if not s:
        return s

    # Remove instance marker _X (single uppercase or lowercase letter after _)
    s = re.sub(r"_[A-Za-z]$", "", s)

    # Remove trailing disambiguation letter after H + 4 digits
    m = re.match(r"^(H\d{4})([A-Za-z])$", s)
    if m:
        return m.group(1)
    return s


def _osis_to_code() -> dict:
    """Map TAHOT book abbreviations to corpus CODE.

    Most are simply the abbreviation uppercased (Gen->GEN, etc.).
    Documented divergences: Sng->SOS, Ezk->EZE, Jol->JOE, Nam->NAH.
    """
    mapping = {}
    # Build the default (uppercase) map for all 39 OT books
    for abbrev in (
        "Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki "
        "1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Isa Jer Lam "
        "Dan Hos Amo Oba Jon Mic Hab Zep Hag Zec Mal"
    ).split():
        mapping[abbrev] = abbrev.upper()
    # Four divergences where upper-case of the abbrev does NOT equal our CODE
    mapping["Sng"] = "SOS"
    mapping["Ezk"] = "EZE"
    mapping["Jol"] = "JOE"
    mapping["Nam"] = "NAH"
    return mapping


def _parse_ref(col0: str, book_map: dict) -> tuple:
    """Parse col 0 of a TAHOT data row into (ref, idx).

    Col 0 format: Book.Chapter.Verse#WordIdx=TextType
    Example: "Gen.1.1#01=L" -> ("GEN.1.1", 1)

    Hebrew versification annotations appear as a parenthetical English ref,
    e.g. "Deu.12.32(13.1)#01=L".  These contain embedded dots; we strip the
    bracketed portions before splitting on "." so only the canonical
    Book.Chapter.Verse (English-order) is used.
    """
    ref_part, _, _ = col0.partition("=")
    locus, _, widx_str = ref_part.partition("#")
    # Remove versification annotations: [...], (...), {...}
    locus_clean = re.sub(r"[\[({][^\])}]*[\])}]", "", locus)
    parts = locus_clean.split(".")
    book, chap, verse = parts[0], parts[1], parts[2]
    code = book_map[book]
    return f"{code}.{int(chap)}.{int(verse)}", int(widx_str)


_DATA_ROW_RE = re.compile(r"^[A-Z1-9][A-Za-z]{1,2}\.\d+\.\d")


def _is_data_row(col0: str) -> bool:
    """Return True if col 0 looks like a TAHOT data-row reference.

    Data rows have the form Book.Chapter.Verse#WordIdx=TextType where Book is
    a 3-char abbreviation.  Preamble prose lines that contain verse refs (e.g.
    the Qere list) have long col 0 values and fail this strict regex check.
    """
    return bool(_DATA_ROW_RE.match(col0))


def normalize_hebrew(raw_path) -> list:
    """Parse a TAHOT .txt file and return a list of normalized word dicts.

    edition is always "WLC" for all TAHOT rows.

    Args:
        raw_path: path-like object pointing to a TAHOT_*.txt file.

    Returns:
        List of dicts with keys: ref, idx, surface, lemma, strong, xpos,
        feats, translit, edition.
    """
    book_map = _osis_to_code()
    out = []

    # utf-8-sig strips the BOM that may be present in TAHOT files
    with open(raw_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            cols = line.split("\t")
            col0 = cols[0]

            # Skip blank/whitespace-only lines
            if not col0.strip() and all(c == "" or c.isspace() for c in cols):
                continue

            # Skip #-prefixed summary lines
            if col0.startswith("#"):
                continue

            # Skip the repeated column-header line
            if col0 == _TAHOT_HEADER_SENTINEL:
                continue

            # Skip preamble prose lines
            if not _is_data_row(col0):
                continue

            # --- parse ---
            ref, idx = _parse_ref(col0, book_map)

            # Surface: col 1 "Hebrew" (with full pointing and prefix/suffix slashes)
            hebrew_raw = cols[_COL_HEBREW] if len(cols) > _COL_HEBREW else ""
            surface = unicodedata.normalize("NFC", hebrew_raw.strip())

            # Lemma: same as surface (TAHOT has no separate dictionary-form column;
            # downstream lexicon tasks will supply the canonical lemma via Strong's).
            lemma = surface

            # Transliteration: col 2
            translit = cols[_COL_TRANSLIT].strip() if len(cols) > _COL_TRANSLIT else "_"
            if not translit:
                translit = "_"

            # Morph code: col 5 "Grammar"
            morph = cols[_COL_GRAMMAR].strip() if len(cols) > _COL_GRAMMAR else "_"

            # Root Strong's: col 8 "Root dStrong+Instance"
            root_strong_raw = cols[_COL_ROOT_STRONG].strip() if len(cols) > _COL_ROOT_STRONG else ""
            strong = _strip_heb_strong(root_strong_raw) if root_strong_raw else "_"

            out.append({
                "ref": ref,
                "idx": idx,
                "surface": surface,
                "lemma": lemma,
                "strong": strong,
                "xpos": morph,
                "feats": "_",
                "translit": translit,
                "edition": "WLC",
            })

    return out


def _write_tsv(rows: list, out_path: Path) -> None:
    """Write normalized rows to a tab-separated file with header."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    import glob

    raw_dir = ROOT / "data" / "cache" / "morph" / "raw"
    out_path = ROOT / "data" / "cache" / "morph" / "heb.tsv"

    all_rows = []
    for raw_file in sorted(glob.glob(str(raw_dir / "TAHOT_*.txt"))):
        print(f"  normalizing {Path(raw_file).name} ...")
        rows = normalize_hebrew(Path(raw_file))
        all_rows.extend(rows)
        print(f"    {len(rows)} rows")

    print(f"Total: {len(all_rows)} rows -> {out_path}")
    _write_tsv(all_rows, out_path)
    print("Done.")
