"""Derive OT versification map from STEPBible TVTMS Condensed file."""

import itertools
import json
import sys
from pathlib import Path

from tools.refs import expand

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "cache" / "tvtms.txt"
OUT_PATH = ROOT / "data" / "versification" / "ot-versification.json"
LXX_OUT_PATH = ROOT / "data" / "versification" / "lxx-versification.json"

TVTMS_URL = (
    "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
    "Versification/"
    "TVTMS%20-%20Translators%20Versification%20Traditions%20with%20"
    "Methodology%20for%20Standardisation%20for%20"
    "Eng%2BHeb%2BLat%2BGrk%2BOthers%20-%20STEPBible.org%20CC%20BY.txt"
)

# Map TVTMS book abbreviations to canonical uppercase codes.
ABBR = {
    "Gen": "GEN", "Exo": "EXO", "Lev": "LEV", "Num": "NUM", "Deu": "DEU",
    "Jos": "JOS", "Jdg": "JDG", "Rut": "RUT", "1Sa": "1SA", "2Sa": "2SA",
    "1Ki": "1KI", "2Ki": "2KI", "1Ch": "1CH", "2Ch": "2CH", "Ezr": "EZR",
    "Neh": "NEH", "Est": "EST", "Job": "JOB", "Psa": "PSA", "Pro": "PRO",
    "Ecc": "ECC", "Sng": "SOS", "Isa": "ISA", "Jer": "JER", "Lam": "LAM",
    "Ezk": "EZE", "Dan": "DAN", "Hos": "HOS", "Jol": "JOE", "Amo": "AMO",
    "Oba": "OBA", "Jon": "JON", "Mic": "MIC", "Nam": "NAH", "Hab": "HAB",
    "Zep": "ZEP", "Hag": "HAG", "Zec": "ZEC", "Mal": "MAL",
}

# Column label strings used in the TVTMS header rows.
_KJV_LABEL = "English KJV"
_HEB_LABEL = "Hebrew"
_LAT_LABEL = "Latin"
_GRK_LABEL = "Greek"


def _normalize_label(s):
    """Strip trailing modifiers like '*' or '?' from a column label."""
    return s.rstrip("*?+").strip()


def parse_condensed(text):
    """Parse the #DataStart(Condensed) section.

    Returns a list of per-verse alignment dicts, each with keys:
        kjv    -- a single ref dict (from expand) or None
        hebrew -- a single ref dict or None
        latin  -- a single ref dict or None
        greek  -- a single ref dict or None  (LXX / Greek tradition column)
    Ranges are expanded and zipped element-wise inside this function so that
    each returned dict represents exactly one aligned verse 4-tuple.
    """
    lines = text.splitlines()
    in_condensed = False
    kjv_idx = heb_idx = lat_idx = grk_idx = None
    result = []

    for line in lines:
        if not in_condensed:
            if line.strip() == "#DataStart(Condensed)":
                in_condensed = True
            continue

        # Block header: starts with '$'.  Reset indices and optionally parse
        # column labels if they appear inline (e.g. Malachi format).
        if line.startswith("$"):
            cells = line.split("\t")
            labels = [_normalize_label(c) for c in cells[1:]]
            kjv_idx = None
            heb_idx = None
            lat_idx = None
            grk_idx = None
            for i, lbl in enumerate(labels):
                if lbl == _KJV_LABEL and kjv_idx is None:
                    kjv_idx = i + 1  # +1 because cells[0] is the '$...' field
                elif lbl == _HEB_LABEL and heb_idx is None:
                    heb_idx = i + 1
                elif lbl == _LAT_LABEL and lat_idx is None:
                    lat_idx = i + 1
                elif lbl == _GRK_LABEL and grk_idx is None:
                    grk_idx = i + 1
            continue

        # BIBLES row: explicit column-header line used in many blocks (Psalms
        # and others).  Format: BIBLES<TAB>English KJV<TAB>Hebrew<TAB>...
        if line.startswith("BIBLES\t"):
            cells = line.split("\t")
            kjv_idx = None
            heb_idx = None
            lat_idx = None
            grk_idx = None
            for i, lbl in enumerate(cells[1:], start=1):
                lbl = _normalize_label(lbl)
                if lbl == _KJV_LABEL and kjv_idx is None:
                    kjv_idx = i
                elif lbl == _HEB_LABEL and heb_idx is None:
                    heb_idx = i
                elif lbl == _LAT_LABEL and lat_idx is None:
                    lat_idx = i
                elif lbl == _GRK_LABEL and grk_idx is None:
                    grk_idx = i
            continue

        # Skip comment/empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Data row -- only if we have valid column indices
        if kjv_idx is None:
            continue

        cells = line.split("\t")

        def _get(idx):
            if idx is None or idx >= len(cells):
                return []
            return expand(cells[idx].strip())

        kjv_refs = _get(kjv_idx)
        heb_refs = _get(heb_idx)
        lat_refs = _get(lat_idx)
        grk_refs = _get(grk_idx)

        # Expand ranges and zip element-wise to produce one dict per verse.
        for kjv_ref, heb_ref, lat_ref, grk_ref in itertools.zip_longest(
                kjv_refs, heb_refs, lat_refs, grk_refs):
            result.append({
                "kjv": kjv_ref,
                "hebrew": heb_ref,
                "latin": lat_ref,
                "greek": grk_ref,
            })

    return result


def build_map(text):
    """Build versification map from TVTMS condensed text.

    Returns a dict with keys 'hebrew', 'latin', and 'greek':
      - 'hebrew' and 'latin': map canonical KJV keys ('BOOK C:V') to the
        target tradition's chapter:verse string, only for verses that differ
        from KJV.  (Existing behaviour, unchanged.)
      - 'greek': map LXX ('BOOK C:V' using LXX numbering) to the MT Hebrew
        chapter:verse string, only for verses that differ between LXX and MT.
        Key = LXX position; value = MT 'chapter:verse'.
    """
    result = {"hebrew": {}, "latin": {}, "greek": {}}
    unmapped_books = set()

    for entry in parse_condensed(text):
        kjv_ref = entry["kjv"]
        heb_ref = entry["hebrew"]
        lat_ref = entry["latin"]
        grk_ref = entry.get("greek")

        # Skip absent/noverse/title entries on the KJV side
        if kjv_ref is None:
            continue
        if kjv_ref.get("absent") or kjv_ref.get("noverse"):
            continue
        if kjv_ref.get("title"):
            continue

        book = kjv_ref.get("book")
        canon = ABBR.get(book) if book else None
        if not canon:
            if book:
                unmapped_books.add(book)
            continue

        chap = kjv_ref["chapter"]
        verse = kjv_ref["verse"]
        kjv_key = f"{canon} {chap}:{verse}"

        # Hebrew comparison (existing behaviour)
        if (heb_ref is not None
                and not heb_ref.get("absent")
                and not heb_ref.get("noverse")
                and not heb_ref.get("title")):
            if (heb_ref["chapter"] != chap or heb_ref["verse"] != verse):
                result["hebrew"][kjv_key] = (
                    f"{heb_ref['chapter']}:{heb_ref['verse']}"
                )

        # Latin comparison (existing behaviour)
        if (lat_ref is not None
                and not lat_ref.get("absent")
                and not lat_ref.get("noverse")
                and not lat_ref.get("title")):
            if (lat_ref["chapter"] != chap or lat_ref["verse"] != verse):
                result["latin"][kjv_key] = (
                    f"{lat_ref['chapter']}:{lat_ref['verse']}"
                )

        # Greek/LXX column: build LXX-keyed -> MT (Hebrew) map.
        # Key = LXX position "CANON grk_chap:grk_verse"
        # Value = MT "heb_chap:heb_verse"
        # Only record when LXX position differs from MT position.
        if (grk_ref is not None
                and not grk_ref.get("absent")
                and not grk_ref.get("noverse")
                and not grk_ref.get("title")
                and heb_ref is not None
                and not heb_ref.get("absent")
                and not heb_ref.get("noverse")
                and not heb_ref.get("title")):
            grk_book = grk_ref.get("book")
            grk_canon = ABBR.get(grk_book) if grk_book else None
            if grk_canon:
                grk_chap = grk_ref["chapter"]
                grk_verse = grk_ref["verse"]
                heb_chap = heb_ref["chapter"]
                heb_verse = heb_ref["verse"]
                heb_book = heb_ref.get("book")
                # Record if position differs (different chapter, verse, or book)
                if (grk_chap != heb_chap
                        or grk_verse != heb_verse
                        or grk_book != heb_book):
                    grk_key = f"{grk_canon} {grk_chap}:{grk_verse}"
                    result["greek"][grk_key] = (
                        f"{heb_chap}:{heb_verse}"
                    )

    if unmapped_books:
        known_nt = {
            "Mat", "Mrk", "Luk", "Jhn", "Act", "Rom", "1Co", "2Co",
            "Gal", "Eph", "Php", "Col", "1Th", "2Th", "1Ti", "2Ti",
            "Tit", "Phm", "Heb", "Jas", "1Pe", "2Pe", "1Jn", "2Jn",
            "3Jn", "Jud", "Rev",
        }
        ot_unmapped = unmapped_books - known_nt
        if ot_unmapped:
            print(f"WARNING: unmapped OT abbreviations: {sorted(ot_unmapped)}",
                  file=sys.stderr)

    return result


def _fetch_tvtms():
    """Fetch TVTMS file from STEPBible GitHub, using disk cache.

    Does NOT reuse tools.fetch.fetch_cached: the TVTMS file has a UTF-8 BOM
    and must be decoded with 'utf-8-sig' to strip it; fetch_cached uses plain
    'utf-8' which would leave the BOM in the text and break header parsing.
    """
    if CACHE_PATH.exists():
        return CACHE_PATH.read_text(encoding="utf-8")

    import urllib.request
    print(f"Fetching TVTMS from {TVTMS_URL} ...", file=sys.stderr)
    req = urllib.request.Request(
        TVTMS_URL,
        headers={"User-Agent": "bible-corpus-builder/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8-sig", errors="replace")

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(raw, encoding="utf-8")
    print(f"Cached to {CACHE_PATH}", file=sys.stderr)
    return raw


def main():
    text = _fetch_tvtms()
    m = build_map(text)

    heb_count = len(m["hebrew"])
    lat_count = len(m["latin"])
    grk_count = len(m["greek"])
    print(f"Hebrew divergences: {heb_count}", file=sys.stderr)
    print(f"Latin divergences:  {lat_count}", file=sys.stderr)
    print(f"Greek divergences:  {grk_count}", file=sys.stderr)

    # --- OT versification (Hebrew + Latin) ---
    ot_output = {
        "_attribution": (
            "Derived from STEPBible TVTMS Condensed "
            "(https://github.com/STEPBible/STEPBible-Data) "
            "CC BY 4.0 Tyndale House, Cambridge"
        ),
        "hebrew": m["hebrew"],
        "latin": m["latin"],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(ot_output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Written: {OUT_PATH}", file=sys.stderr)

    # --- LXX versification (Greek column: LXX ref -> MT chapter:verse) ---
    lxx_output = {
        "_attribution": (
            "Derived from STEPBible TVTMS Condensed "
            "(https://github.com/STEPBible/STEPBible-Data) "
            "CC BY 4.0 Tyndale House, Cambridge. "
            "Greek (LXX) column: LXX ref -> MT (Hebrew) chapter:verse, "
            "only for verses where LXX numbering diverges from MT."
        ),
        "greek": m["greek"],
    }

    LXX_OUT_PATH.write_text(
        json.dumps(lxx_output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Written: {LXX_OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
