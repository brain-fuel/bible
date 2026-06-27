"""STEPBible TAGNT normalizer -> fixed-schema intermediate TSV.

TAGNT is semi-structured: each verse is a block of #-prefixed summary lines
followed by a repeated "Word & Type<TAB>..." column-header line and then the
per-word data rows.  A single csv.DictReader over the whole file does NOT work.
We parse positionally, skipping # lines and repeated headers.

TR filter: only rows where the editions column (col 5) contains the string "TR"
are emitted.  All such rows get edition="TR".

Strong's numbers in TAGNT are already 4-digit zero-padded.  We only strip:
  - H####|G#### compound forms -> take the G#### part
  - Trailing single-letter disambiguation suffix: G2424G -> G2424

Lemma: col 4 "Dictionary form = Gloss" before the first "=".
Surface: col 1 "Greek" before the first " ("; transliteration is inside "()".
"""

import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = ["ref", "idx", "surface", "lemma", "strong", "xpos", "feats", "translit", "edition"]

# Column indices in TAGNT data rows (0-based)
_COL_REF = 0
_COL_GREEK = 1
_COL_STRONGS_MORPH = 3
_COL_DICT_FORM = 4
_COL_EDITIONS = 5

# The repeated column-header line starts with this string (first field).
_TAGNT_HEADER_SENTINEL = "Word & Type"


def pad_strong(prefix: str, number: str) -> str:
    """Return prefix + 4-digit zero-padded number.

    Example: pad_strong("G", "26") -> "G0026"
    For most TAGNT/TAHOT usage the number is already 4-digit; this function
    exists for the general case (e.g. constructing strongs from scratch).
    """
    return f"{prefix}{int(number):04d}"


def _strip_grk_strong(raw: str) -> str:
    """Canonicalize a raw TAGNT Strong's string from col 3 (before '=').

    Handles:
      - Plain: "G0976" -> "G0976"
      - Disambiguation suffix: "G2424G" -> "G2424"
      - Hebrew|Greek compound: "H1732|G1138" -> "G1138"
      - Compound + suffix: "H1732|G1138N" -> "G1138"
    """
    s = raw.strip()
    # H####|G#### compound: take the G portion
    if "|" in s:
        s = s.split("|")[-1]
    # Strip trailing single-letter disambiguation suffix after 4-digit number
    # Pattern: G + 4 digits + optional alpha (1 char)
    m = re.match(r"^(G\d{4})([A-Za-z])$", s)
    if m:
        return m.group(1)
    return s


def _osis_to_code() -> dict:
    """Map TAGNT book abbreviations to corpus CODE.

    Divergences from the upper-cased abbrev are: Jhn->JOH, 1Jn->1JO,
    2Jn->2JO, 3Jn->3JO, Jas->JAM, Jud->JDE.
    All others are just the abbreviation uppercased.
    """
    return {
        "Mat": "MAT", "Mrk": "MAR", "Luk": "LUK", "Jhn": "JOH",
        "Act": "ACT", "Rom": "ROM", "1Co": "1CO", "2Co": "2CO",
        "Gal": "GAL", "Eph": "EPH", "Php": "PHP", "Col": "COL",
        "1Th": "1TH", "2Th": "2TH", "1Ti": "1TI", "2Ti": "2TI",
        "Tit": "TIT", "Phm": "PHM", "Heb": "HEB", "Jas": "JAM",
        "1Pe": "1PE", "2Pe": "2PE", "1Jn": "1JO", "2Jn": "2JO",
        "3Jn": "3JO", "Jud": "JDE", "Rev": "REV",
    }


def _parse_ref(col0: str, book_map: dict) -> tuple:
    """Parse col 0 of a TAGNT data row into (ref, idx).

    Col 0 format: Book.Chapter.Verse#WordIdx=TypeCode
    Example: "Mat.1.1#01=NKO" -> ("MAT.1.1", 1)

    Versification annotations (square, round, or curly brackets) can appear
    inside the verse portion and sometimes contain embedded dots, e.g.:
      "Mat.15.6{15.5}#01=k"  -> locus "Mat.15.6{15.5}"
      "Luk.1.74[1.74]#01=N"  -> locus "Luk.1.74[1.74]"
    We strip the bracketed parts before splitting on "." so only the canonical
    Book.Chapter.Verse is used.
    """
    # Strip type code after "#NN=..." — keep only the locus + word index
    ref_part, _, _ = col0.partition("=")
    # ref_part = "Mat.1.1#01" or "Mat.15.6{15.5}#01"
    locus, _, widx_str = ref_part.partition("#")
    # Remove versification-difference annotations: [...], (...), {...}
    locus_clean = re.sub(r"[\[({][^\])}]*[\])}]", "", locus)
    parts = locus_clean.split(".")
    book, chap, verse = parts[0], parts[1], parts[2]
    code = book_map[book]
    return f"{code}.{int(chap)}.{int(verse)}", int(widx_str)


_DATA_ROW_RE = re.compile(r"^[A-Z1-9][A-Za-z]{1,2}\.\d+\.\d")


def _is_data_row(col0: str) -> bool:
    """Return True if col 0 looks like a TAGNT data-row reference.

    Data rows have the form Book.Chapter.Verse#WordIdx=TypeCode where Book is
    a 3-char abbreviation starting with a capital letter (or digit for books
    like 1Co).  Preamble prose lines may contain book refs but their col 0
    starts with long prose, so the strict regex rejects them.
    """
    return bool(_DATA_ROW_RE.match(col0))


def normalize_greek(raw_path) -> list:
    """Parse a TAGNT .txt file and return a list of normalized word dicts.

    Only words present in the Textus Receptus (TR appears in col 5 editions)
    are returned.  edition is always set to "TR" for returned rows.

    Args:
        raw_path: path-like object pointing to a TAGNT_*.txt file.

    Returns:
        List of dicts with keys: ref, idx, surface, lemma, strong, xpos,
        feats, translit, edition.
    """
    book_map = _osis_to_code()
    out = []

    # utf-8-sig strips the BOM present in the TAGNT files
    with open(raw_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            cols = line.split("\t")
            col0 = cols[0]

            # Skip blank/whitespace-only lines
            if not col0.strip() and all(c == "" or c.isspace() for c in cols):
                continue

            # Skip #-prefixed summary lines and preamble
            if col0.startswith("#"):
                continue

            # Skip the repeated column-header line
            if col0 == _TAGNT_HEADER_SENTINEL:
                continue

            # Skip preamble prose lines that are not data rows
            if not _is_data_row(col0):
                continue

            # Filter: only TR-attested rows
            editions = cols[_COL_EDITIONS] if len(cols) > _COL_EDITIONS else ""
            if "TR" not in editions:
                continue

            # --- parse ---
            ref, idx = _parse_ref(col0, book_map)

            # Surface and transliteration from col 1 "Greek"
            greek_raw = cols[_COL_GREEK] if len(cols) > _COL_GREEK else ""
            if " (" in greek_raw:
                paren_pos = greek_raw.index(" (")
                surface_raw = greek_raw[:paren_pos].strip()
                translit = greek_raw[paren_pos + 2:].rstrip(")")
            else:
                surface_raw = greek_raw.strip()
                translit = "_"
            surface = unicodedata.normalize("NFC", surface_raw)

            # Strong's and morph from col 3 "dStrongs = Grammar"
            strongs_morph = cols[_COL_STRONGS_MORPH] if len(cols) > _COL_STRONGS_MORPH else ""
            strong_raw, _, morph = strongs_morph.partition("=")
            strong = _strip_grk_strong(strong_raw)

            # Lemma from col 4 "Dictionary form = Gloss"
            dict_form = cols[_COL_DICT_FORM] if len(cols) > _COL_DICT_FORM else ""
            lemma = unicodedata.normalize("NFC", dict_form.partition("=")[0])

            out.append({
                "ref": ref,
                "idx": idx,
                "surface": surface,
                "lemma": lemma,
                "strong": strong,
                "xpos": morph.strip(),
                "feats": "_",
                "translit": translit or "_",
                "edition": "TR",
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
    out_path = ROOT / "data" / "cache" / "morph" / "grc.tsv"

    all_rows = []
    for raw_file in sorted(glob.glob(str(raw_dir / "TAGNT_*.txt"))):
        print(f"  normalizing {Path(raw_file).name} ...")
        rows = normalize_greek(Path(raw_file))
        all_rows.extend(rows)
        print(f"    {len(rows)} TR rows")

    print(f"Total: {len(all_rows)} rows -> {out_path}")
    _write_tsv(all_rows, out_path)
    print("Done.")
