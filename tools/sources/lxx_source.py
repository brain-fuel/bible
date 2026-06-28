"""Swete 1909 LXX text source backend.

Reads cached CSV files from data/cache/morph/raw/lxx/:
  swete_versification.csv    -- word_index<TAB>Book.Chapter:Verse
  swete_word_with_punct.csv  -- word_index<TAB>word

Text is Public Domain: H. B. Swete, The Old Testament in Greek, 1909.
The CSV packaging (eliranwong/LXX-Swete-1930, GPL-3.0) is NOT redistributed;
only the PD text content is used.

Interface (mirrors other tools/sources/ backends):
    handle.chapters(book_meta) -> list[int]       sorted chapter numbers
    handle.chapter(book_meta, chapter) -> dict     verse_int -> Greek text (NFC)
"""

import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CSV_DIR = ROOT / "data" / "cache" / "morph" / "raw" / "lxx"

# ---------------------------------------------------------------------------
# CSV abbreviation -> output CODE
# The "shipped" form for text-form doublets is listed; alternatives are skipped.
# ---------------------------------------------------------------------------
_ABBREV_TO_CODE = {
    # Numbered books
    "1Ch": "1CH", "1Es": "1ES", "1Ki": "1KI", "1Ma": "1MA", "1Sa": "1SA",
    "2Ch": "2CH", "2Ki": "2KI", "2Ma": "2MA", "2Sa": "2SA",
    "3Ma": "3MA", "4Ma": "4MA",
    # Protocanon (simple uppercase)
    "Amo": "AMO", "Deu": "DEU", "Ecc": "ECC",
    "Est": "EST", "Exo": "EXO", "Eze": "EZE", "Ezr": "EZR",
    "Gen": "GEN", "Hab": "HAB", "Hag": "HAG", "Hos": "HOS",
    "Isa": "ISA", "Jdg": "JDG", "Jer": "JER", "Job": "JOB",
    "Joe": "JOE", "Jon": "JON", "Jos": "JOS", "Lam": "LAM",
    "Lev": "LEV", "Mal": "MAL", "Mic": "MIC", "Nah": "NAH",
    "Neh": "NEH", "Num": "NUM", "Oba": "OBA", "Pro": "PRO",
    "Psa": "PSA", "Rut": "RUT", "Zec": "ZEC", "Zep": "ZEP",
    # Deuterocanon
    "Bar": "BAR", "Jdt": "JDT", "Ode": "ODE", "Pss": "PSS",
    "Sir": "SIR", "Tob": "TOB", "Wis": "WIS",
    # Text-form selections
    "Sol": "SOS",   # Song of Solomon
    "Dat": "DAN",   # Daniel Theodotion -> DAN   (skip OG form "Dan")
    "Bet": "BEL",   # Bel Theodotion    -> BEL   (skip OG form "Bel")
    "Sut": "SUS",   # Susanna Theodotion -> SUS  (skip OG "Sus" and "Sip")
    # Epj -> BAR chapter 6 is handled explicitly below; not in this dict.
}

# Abbreviations to skip entirely (duplicates or out-of-scope books).
_SKIP = frozenset([
    "1En",   # 1 Enoch: not in Rahlfs LXX canon
    "Dan",   # Daniel OG: shipping Theodotion (Dat) as DAN
    "Bel",   # Bel OG: shipping Theodotion (Bet) as BEL
    "Sus",   # Susanna OG: shipping Theodotion (Sut) as SUS
    "Sip",   # Susanna "in place" excerpt: only 22 verses, not shipped
    "Tbs",   # Tobit Sinaiticus: shipping BA form (Tob) as TOB
])


class LxxSource:
    """Source handle for the Swete 1909 LXX text (CSV-based).

    Lazily loads and indexes the CSV on first use.
    Handles the Epj->BAR.6 remap and MAN->ODE.8 aliasing internally.
    """

    def __init__(self, csv_dir=None):
        self._csv_dir = Path(csv_dir) if csv_dir else _DEFAULT_CSV_DIR
        self._index = None  # code -> chapter -> verse -> text

    def _ensure_loaded(self):
        if self._index is None:
            self._index = _build_index(self._csv_dir)

    def chapters(self, book_meta) -> list:
        """Return sorted list of chapter numbers available for this book."""
        self._ensure_loaded()
        return sorted(self._index.get(book_meta["code"], {}))

    def chapter(self, book_meta, chapter: int) -> dict:
        """Return {verse_int: greek_text} for the given chapter (NFC-normalized)."""
        self._ensure_loaded()
        return dict(self._index.get(book_meta["code"], {}).get(chapter, {}))


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def _build_index(csv_dir: Path) -> dict:
    """Load both CSVs and return code -> chapter -> verse -> text."""
    csv_dir = Path(csv_dir)

    # 1. Load word table: idx -> surface form
    words: dict[int, str] = {}
    word_path = csv_dir / "swete_word_with_punct.csv"
    with open(word_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if "\t" not in line:
                continue
            idx_s, word = line.split("\t", 1)
            words[int(idx_s)] = word

    # 2. Load versification: sorted list of (word_idx, abbrev, chapter, verse)
    vers_list: list[tuple] = []
    vers_path = csv_dir / "swete_versification.csv"
    with open(vers_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if "\t" not in line:
                continue
            idx_s, ref = line.split("\t", 1)
            dot = ref.index(".")
            abbrev = ref[:dot]
            rest = ref[dot + 1:]
            ch_s, v_s = rest.split(":")
            vers_list.append((int(idx_s), abbrev, int(ch_s), int(v_s)))
    vers_list.sort(key=lambda x: x[0])

    max_idx = max(words) if words else 0

    # 3. Collect words for each verse and route to target CODE/chapter
    raw: dict = defaultdict(lambda: defaultdict(dict))  # code -> ch -> verse -> text

    for i, (start, abbrev, csv_ch, csv_v) in enumerate(vers_list):
        end = vers_list[i + 1][0] if i + 1 < len(vers_list) else max_idx + 1

        if abbrev in _SKIP:
            continue

        if abbrev == "Epj":
            # Epistle of Jeremiah -> BAR chapter 6, verse numbering from csv_v
            code, tgt_ch, tgt_v = "BAR", 6, csv_v
        else:
            code = _ABBREV_TO_CODE.get(abbrev)
            if code is None:
                continue
            tgt_ch, tgt_v = csv_ch, csv_v

        verse_words = [words[j] for j in range(start, end) if j in words]
        text = unicodedata.normalize("NFC", " ".join(verse_words))
        if not text:
            # Verse slot with no words: LXX genuinely omits this verse.
            # Skip rather than storing an empty string.
            continue
        raw[code][tgt_ch][tgt_v] = text

    # 4. MAN (Prayer of Manasses) = Ode chapter 8 ("Προσευχὴ Μαννασσή"),
    #    aliased into MAN chapter 1.  ODE chapter 8 remains in ODE (the alias
    #    copies content; it does not remove it from the Odes collection).
    #    Note: ODE chapter 12 is "Προσευχὴ Συμεών" (Nunc Dimittis, Luke
    #    2:29-32), which is NOT the Prayer of Manasseh.
    if "ODE" in raw and 8 in raw["ODE"]:
        raw["MAN"][1] = dict(raw["ODE"][8])

    # Convert nested defaultdicts to plain dicts
    return {code: {ch: dict(vv) for ch, vv in chs.items()}
            for code, chs in raw.items()}
