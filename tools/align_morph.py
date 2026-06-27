"""Task 4: Morpho-lexical alignment engine.

align_verse() fuses an L0 verse surface string with normalized morph rows,
producing CoNLL-U Token objects. FORM is authoritative from L0; lemma/xpos/
Strong/translit come from the matched normalized source row.

Unmatched L0 words get Align=unmatched in MISC.
Leftover source rows (source_extra) are recorded on the last token.
"""

import csv
import re
import unicodedata
from pathlib import Path

from tools.conllu import Token, format_misc
from tools.morph_feats import decode

ROOT = Path(__file__).resolve().parents[1]

# Punctuation to strip for matching (not removed from FORM, only for normalization)
_PUNCT = re.compile(r"[\.,;:·''\"\?\!·\[\]]")


def normalize_surface(s: str) -> str:
    """Strip diacritics/pointing and lowercase for fuzzy surface matching.

    Decompose to NFD, drop combining characters (accents, cantillation),
    strip common punctuation, recase to lower.  The result is used only for
    alignment matching, never written to output.
    """
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _PUNCT.sub("", s).lower().strip()


def tokenize_l0(text: str) -> list:
    """Split an L0 verse string into a list of surface word strings.

    Punctuation characters are converted to spaces so they act as delimiters;
    the resulting tokens preserve the original Unicode including accents.
    """
    return [w for w in _PUNCT.sub(" ", text).split() if w]


def load_norm(lang: str) -> dict:
    """Load the normalized morph TSV for *lang* into a ref->rows mapping.

    Returns:
        dict mapping ref strings (e.g. '3JO.1.1') to sorted lists of row dicts.
    """
    path = ROOT / "data" / "cache" / "morph" / f"{lang}.tsv"
    by_ref: dict = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            row["idx"] = int(row["idx"])
            by_ref.setdefault(row["ref"], []).append(row)
    for ref in by_ref:
        by_ref[ref].sort(key=lambda r: r["idx"])
    return by_ref


def align_verse(ref: str, l0_text: str, norm_rows: list, lang: str) -> list:
    """Align an L0 verse string against normalized morph rows.

    Strategy: walk L0 words left-to-right; advance the source pointer when
    normalize_surface matches.  Unmatched L0 words get placeholder tags and
    Align=unmatched.  After all L0 words are processed, any leftover source
    rows are appended as Align=source_extra:<n> on the last token.

    Args:
        ref:       Reference string, e.g. '3JO.1.1'.
        l0_text:   Raw verse string from the L0 corpus (authoritative).
        norm_rows: List of normalized row dicts for this ref (idx-ordered).
        lang:      'grc' or 'hbo' -- passed to decode().

    Returns:
        List of Token objects in L0 word order.
    """
    words = tokenize_l0(l0_text)
    rows = list(norm_rows)
    tokens = []
    si = 0  # source index pointer

    for i, w in enumerate(words, start=1):
        match = None
        if si < len(rows) and normalize_surface(w) == normalize_surface(rows[si]["surface"]):
            match = rows[si]
            si += 1

        if match:
            upos, feats = decode(match["xpos"], lang)
            misc = format_misc(match["strong"], match.get("translit", "_"), {}, None)
            tokens.append(Token(str(i), w, match["lemma"], upos, match["xpos"], feats, misc=misc))
        else:
            tokens.append(Token(
                str(i), w, "_", "X", "_", "_",
                misc=format_misc("", "_", {}, "unmatched"),
            ))

    # Attach any leftover source rows to the last token
    if si < len(rows) and tokens:
        leftover = len(rows) - si
        extra = f"source_extra:{leftover}"
        last = tokens[-1]
        last.misc = (last.misc + f"|Align={extra}") if last.misc != "_" else f"Align={extra}"

    return tokens
