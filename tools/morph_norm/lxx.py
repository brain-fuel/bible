"""openscriptures LxxLemmas normalizer -> fixed-schema TSV.

Source: openscriptures GreekResources, LxxLemmas/
License: CC BY 4.0 (Open Scriptures Septuagint Project, David Troidl)
Attribution: https://github.com/openscriptures/GreekResources

Format (per docs/FORMATS-lxx.md §Source 1b):
  JSON object keyed by "Book.Chapter.Verse", value = ordered word list:
  [{"key": "<lowercase unaccented>", "lemma": "<precomposed polytonic>"}]

This module provides:
  lemma_strong_index()         -> dict[str,str]  raw lemma -> "Gxxxx"
  normalize_lxx(raw_path_or_dir) -> list[dict]  one dict per token
  CLI: python -m tools.morph_norm.lxx  writes data/cache/morph/lxx.tsv

IMPORTANT (per docs/FORMATS-lxx.md §Source 2):
  LxxLemmas lemmas use precomposed polytonic Greek with OXIA accents (U+1F7x),
  NOT NFC tonos (U+03xx).  lexicon/grc lemmas use the same encoding.
  DO NOT call unicodedata.normalize("NFC", ...) on lemmas — it breaks the join.
"""

import csv
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ["ref", "idx", "surface", "lemma", "strong", "xpos", "feats", "translit", "edition"]

# ---------------------------------------------------------------------------
# Book order (determines deterministic output order across files)
# Matches the LXX canon order.  Stems not listed are processed last.
# ---------------------------------------------------------------------------
_BOOK_ORDER = [
    "Gen", "Exod", "Lev", "Num", "Deut",
    "JoshB",            # Joshua B text-form -> JOS
    "JudgA",            # Judges A text-form -> JDG
    "Ruth",
    "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr", "2Chr",
    "1Esd", "2Esd",     # 2Esd = Esdras B = EZR (ch1-10) + NEH (ch11-23)
    "Esth", "Jdt", "TobBA",
    "1Macc", "2Macc", "3Macc", "4Macc",
    "Ps", "Odes",       # Odes includes MAN (Prayer of Manasseh = Ode 12)
    "Prov", "Eccl", "Song", "Job", "Wis", "Sir", "PsSol",
    "Hos", "Mic", "Amos", "Joel", "Jonah", "Obad",
    "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
    "Isa", "Jer", "Bar", "EpJer", "Lam", "Ezek",
    "BelTh", "DanTh", "SusTh",
]

# Stems to skip: OG forms when Theodotion is shipped, Sinaiticus Tobit, etc.
_SKIP_STEMS = frozenset([
    "JoshA",   # Joshua A (OG variant); shipping JoshB
    "JudgB",   # Judges B; shipping JudgA
    "TobS",    # Tobit Sinaiticus; shipping TobBA
    "BelOG",   # Bel Old Greek; shipping Theodotion
    "DanOG",   # Daniel Old Greek; shipping Theodotion
    "SusOG",   # Susanna Old Greek; shipping Theodotion
    "1En",     # 1 Enoch: not in Rahlfs LXX canon
])

# Simple stem -> CODE mapping.
# Special stems (2Esd, EpJer, Odes) are handled explicitly in _normalize_file.
_STEM_TO_CODE = {
    "Gen":   "GEN",  "Exod": "EXO",  "Lev":  "LEV",  "Num":  "NUM",
    "Deut":  "DEU",  "JoshB": "JOS", "JudgA": "JDG", "Ruth": "RUT",
    "1Sam":  "1SA",  "2Sam": "2SA",  "1Kgs": "1KI",  "2Kgs": "2KI",
    "1Chr":  "1CH",  "2Chr": "2CH",  "1Esd": "1ES",
    "Esth":  "EST",  "Jdt":  "JDT",  "TobBA": "TOB",
    "1Macc": "1MA",  "2Macc": "2MA", "3Macc": "3MA", "4Macc": "4MA",
    "Ps":    "PSA",  "Odes": "ODE",  "Prov": "PRO",  "Eccl": "ECC",
    "Song":  "SOS",  "Job":  "JOB",  "Wis":  "WIS",  "Sir":  "SIR",
    "PsSol": "PSS",
    "Hos":   "HOS",  "Mic":  "MIC",  "Amos": "AMO",  "Joel": "JOE",
    "Jonah": "JON",  "Obad": "OBA",  "Nah":  "NAH",  "Hab":  "HAB",
    "Zeph":  "ZEP",  "Hag":  "HAG",  "Zech": "ZEC",  "Mal":  "MAL",
    "Isa":   "ISA",  "Jer":  "JER",  "Bar":  "BAR",  "Lam":  "LAM",
    "Ezek":  "EZE",  "BelTh": "BEL", "DanTh": "DAN", "SusTh": "SUS",
}


# ---------------------------------------------------------------------------
# Verse sort key: integer prefix first, then trailing suffix alphabetically
# Handles "1", "1a", "1b", "68t", etc.
# ---------------------------------------------------------------------------
_VERSE_SORT_RE = re.compile(r"^(\d+)(.*)$")


def _verse_sort_key(v: str):
    m = _VERSE_SORT_RE.match(v)
    if m:
        return (int(m.group(1)), m.group(2))
    return (10 ** 9, v)


# ---------------------------------------------------------------------------
# lemma_strong_index
# ---------------------------------------------------------------------------

def lemma_strong_index() -> dict:
    """Read lexicon/grc/*.json and return {raw_lemma: "Gxxxx"}.

    Keys are the RAW lemma string (precomposed polytonic with oxia accents).
    NFC normalization is deliberately NOT applied: both LxxLemmas lemmas and
    lexicon/grc lemmas use oxia (U+1F7x), not tonos (U+03xx); applying NFC
    would fold them to tonos and break the byte-identical match.
    """
    lex_dir = ROOT / "lexicon" / "grc"
    index: dict[str, str] = {}
    for path in sorted(lex_dir.glob("G*.json")):
        with open(path, encoding="utf-8") as fh:
            entry = json.load(fh)
        strong = entry.get("strong", "")
        lemma = entry.get("lemma", "")
        if strong and lemma:
            index[lemma] = strong
    return index


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_man_chapter(data: dict) -> int:
    """Find the Ode chapter that is the Prayer of Manasseh by its title lemmas.

    In LxxLemmas Odes.js, each chapter's verse 0 is a heading.  We look for
    the chapter whose verse-0 lemmas include 'Μανασσῆς' (Manasseh), which
    marks the Prayer of Manasseh.  Falls back to None if not found.

    Verified on disk: LxxLemmas Odes.js Ode 12 v0 = ['προσευχή', 'Μανασσῆς'].
    """
    # Group keys by chapter
    chapters: dict[int, dict[str, list]] = {}
    for key, words in data.items():
        parts = key.split(".", 2)
        if len(parts) < 3:
            continue
        ch_str = parts[1]
        v_str = parts[2]
        try:
            ch = int(ch_str)
        except ValueError:
            continue
        chapters.setdefault(ch, {})[v_str] = words

    for ch in sorted(chapters.keys()):
        # verse 0 is the title/heading for this Ode
        v0_words = chapters[ch].get("0", [])
        v0_lemmas = [w.get("lemma", "") for w in v0_words]
        # 'Μανασσῆς' in any of the heading lemmas -> Prayer of Manasseh
        if any("Μανασσ" in lem for lem in v0_lemmas):
            return ch
    return None


def _normalize_file(js_path: Path, index: dict) -> list:
    """Parse one LxxLemmas .js file and return normalized row dicts.

    Handles special-case remappings:
      - Stem "2Esd":  ch1-10 -> EZR.ch.v,  ch11-23 -> NEH.(ch-10).v
      - Stem "EpJer": ch1 -> BAR.6.v   (Epistle of Jeremiah appended to Baruch)
      - Stem "Odes":  the Prayer of Manasseh ode (found by heading lemma content)
                      -> MAN.1.v (v0 title row included as MAN.1.0);
                      all other odes -> ODE.ch.v as normal
    """
    stem = js_path.stem  # e.g. "Gen", "JoshB", "2Esd"

    with open(js_path, encoding="utf-8") as fh:
        data = json.load(fh)

    rows: list[dict] = []

    # --- Odes: locate MAN chapter first ---
    man_chapter: int | None = None
    if stem == "Odes":
        man_chapter = _find_man_chapter(data)

    # Sort keys for deterministic output: by chapter int, then verse sort key
    def _sort_key(key: str):
        parts = key.split(".", 2)
        try:
            ch = int(parts[1]) if len(parts) > 1 else 0
        except ValueError:
            ch = 10 ** 9
        v_str = parts[2] if len(parts) > 2 else ""
        return (ch, _verse_sort_key(v_str))

    sorted_keys = sorted(data.keys(), key=_sort_key)

    for raw_key in sorted_keys:
        words = data[raw_key]
        # Parse: PREFIX.CHAPTER.VERSE_STR
        parts = raw_key.split(".", 2)
        if len(parts) < 3:
            continue
        ch_str = parts[1]
        v_str = parts[2]

        try:
            ch = int(ch_str)
        except ValueError:
            # Skip malformed chapter keys
            continue

        # --- Route to target CODE/chapter ---
        if stem == "2Esd":
            if ch <= 10:
                code = "EZR"
                out_ch = ch
            else:
                code = "NEH"
                out_ch = ch - 10  # 2Esd.11 -> NEH.1, 2Esd.23 -> NEH.13
            out_v = v_str
        elif stem == "EpJer":
            # All of EpJer -> BAR chapter 6
            code = "BAR"
            out_ch = 6
            out_v = v_str
        elif stem == "Odes":
            if man_chapter is not None and ch == man_chapter:
                # Prayer of Manasseh -> MAN chapter 1
                code = "MAN"
                out_ch = 1
                out_v = v_str
            else:
                code = "ODE"
                out_ch = ch
                out_v = v_str
        else:
            code = _STEM_TO_CODE.get(stem)
            if code is None:
                continue
            out_ch = ch
            out_v = v_str

        ref = f"{code}.{out_ch}.{out_v}"

        # Emit one row per word, 1-based idx
        for idx, word in enumerate(words, start=1):
            key_surface = word.get("key", "")   # lowercase unaccented
            lemma = word.get("lemma", "")        # precomposed polytonic (raw, no NFC)
            strong = index.get(lemma, "")

            rows.append({
                "ref":      ref,
                "idx":      idx,
                "surface":  key_surface,
                "lemma":    lemma,
                "strong":   strong,
                "xpos":     "_",
                "feats":    "_",
                "translit": "_",
                "edition":  "LXX",
            })

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_lxx(raw_path) -> list:
    """Parse LxxLemmas JSON data and return normalized row dicts.

    Args:
        raw_path: Path (or str) to either:
          - a single .js file (e.g. "Gen.js") — parse that file
          - a directory — parse all .js files in it (in BOOK_ORDER order)

    Returns:
        List of dicts with keys: ref, idx, surface, lemma, strong,
        xpos, feats, translit, edition.
        ref format: "CODE.chapter.verse" (LxxLemmas versification).
        strong: "Gxxxx" if the lemma matches lexicon/grc, else "".
        xpos, feats, translit: always "_" (no open morph source for LXX).
        edition: always "LXX".
    """
    raw_path = Path(raw_path)
    index = lemma_strong_index()

    if raw_path.is_file():
        stem = raw_path.stem
        if stem in _SKIP_STEMS:
            return []
        return _normalize_file(raw_path, index)

    # Directory: collect files, order by _BOOK_ORDER, then alphabetically for remainder
    js_files: dict[str, Path] = {}
    for p in raw_path.glob("*.js"):
        if p.stem not in _SKIP_STEMS:
            js_files[p.stem] = p

    order = [s for s in _BOOK_ORDER if s in js_files]
    remainder = sorted(s for s in js_files if s not in set(_BOOK_ORDER))

    all_rows: list[dict] = []
    for stem in order + remainder:
        file_rows = _normalize_file(js_files[stem], index)
        all_rows.extend(file_rows)

    return all_rows


# ---------------------------------------------------------------------------
# Shared _write_tsv (mirrors tools/morph_norm/stepbible_greek.py)
# ---------------------------------------------------------------------------

def _write_tsv(rows: list, out_path: Path) -> None:
    """Write normalized rows to a tab-separated file with header."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SCHEMA, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    raw_dir = ROOT / "data" / "cache" / "morph" / "raw" / "lxx" / "lxxlemmas"
    out_path = ROOT / "data" / "cache" / "morph" / "lxx.tsv"

    print(f"Reading LxxLemmas from {raw_dir} ...")
    rows = normalize_lxx(raw_dir)
    print(f"Total rows: {len(rows)}")

    # Build per-CODE coverage report
    from collections import Counter
    code_counts: Counter = Counter()
    strong_hit = 0
    for r in rows:
        code_counts[r["ref"].split(".")[0]] += 1
        if r["strong"]:
            strong_hit += 1

    rate = strong_hit / len(rows) * 100 if rows else 0
    print(f"Strong's link rate: {strong_hit}/{len(rows)} = {rate:.1f}%")

    print("\nPer-CODE token counts:")
    for code, cnt in sorted(code_counts.items()):
        print(f"  {code}: {cnt}")

    print(f"\nWriting {out_path} ...")
    _write_tsv(rows, out_path)
    print("Done.")
