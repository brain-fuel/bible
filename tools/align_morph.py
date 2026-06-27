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

# Punctuation to strip for matching (not removed from FORM, only for normalization).
# Includes:  . , ; :  ·(U+00B7 middle dot)  ¶(U+00B6 pilcrow, STEPBible appends
# .¶/;¶ on paragraph-final words)  ;(U+037E Greek question mark)  ·(U+0387 ano
# teleia)  ‘ ’(U+2018/U+2019 curly quotes, elision/koronis)  ' " ? !  [ ]
_PUNCT = re.compile(r"[\.,;:·¶;·‘’'\"?!\[\]]")

# Bounded source-skip lookahead window for matcher resync.
_LOOKAHEAD = 2


def _append_align(misc: str, value: str) -> str:
    """Append an Align value to a MISC string under a single Align= key.

    If MISC already carries an Align= field, the new value is comma-joined to
    the existing one (CoNLL-U requires unique feature keys) rather than adding
    a second Align= field.
    """
    if misc == "_":
        return f"Align={value}"
    parts = misc.split("|")
    for j, p in enumerate(parts):
        if p.startswith("Align="):
            parts[j] = f"{p},{value}"
            return "|".join(parts)
    parts.append(f"Align={value}")
    return "|".join(parts)


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

    Two-pointer walk of L0 words against source rows:

    * Direct hit: normalize_surface(L0[i]) == normalize_surface(TR[si]) -> match,
      advance si.
    * Resync: on a miss, look ahead up to ``_LOOKAHEAD`` source rows; if TR[si+k]
      matches L0[i] (k in 1.._LOOKAHEAD), the intervening rows TR[si..si+k-1] are
      treated as source-only (counted toward source_extra), si jumps past them,
      and L0[i] matches TR[si+k].  This recovers from a single divergent/extra
      source word without desyncing the rest of the verse.
    * Genuine divergence: if no lookahead position matches, L0[i] is emitted with
      placeholder tags + Align=unmatched and si is NOT advanced, preserving the
      source pointer for words truly absent from the source (e.g. TR omissions).

    Any source rows left unconsumed (mid-verse skips + trailing leftover) are
    recorded as a single Align=source_extra:<n> on the last token.

    Args:
        ref:       Reference string, e.g. '3JO.1.1'.
        l0_text:   Raw verse string from the L0 corpus (authoritative).
        norm_rows: List of normalized row dicts for this ref (idx-ordered).
        lang:      'grc' or 'hbo', passed to decode().

    Returns:
        List of Token objects in L0 word order.
    """
    words = tokenize_l0(l0_text)
    rows = list(norm_rows)
    norm_rows_surf = [normalize_surface(r["surface"]) for r in rows]
    tokens = []
    si = 0           # source index pointer
    skipped_extra = 0  # mid-verse source-only rows consumed by resync

    for i, w in enumerate(words, start=1):
        nw = normalize_surface(w)
        match = None

        if si < len(rows):
            if nw == norm_rows_surf[si]:
                match = rows[si]
                si += 1
            else:
                # Bounded source-skip lookahead to resync after a divergence.
                for k in range(1, _LOOKAHEAD + 1):
                    j = si + k
                    if j < len(rows) and nw == norm_rows_surf[j]:
                        skipped_extra += k          # rows si..j-1 are source-only
                        si = j + 1                  # consume up to and incl. match
                        match = rows[j]
                        break

        if match:
            upos, feats = decode(match["xpos"], lang)
            misc = format_misc(match["strong"], match.get("translit", "_"), {}, None)
            tokens.append(Token(str(i), w, match["lemma"], upos, match["xpos"], feats, misc=misc))
        else:
            tokens.append(Token(
                str(i), w, "_", "X", "_", "_",
                misc=format_misc("", "_", {}, "unmatched"),
            ))

    # Attach all unconsumed source rows (skips + trailing leftover) to last token.
    leftover = (len(rows) - si) + skipped_extra
    if leftover > 0 and tokens:
        tokens[-1].misc = _append_align(tokens[-1].misc, f"source_extra:{leftover}")

    return tokens
