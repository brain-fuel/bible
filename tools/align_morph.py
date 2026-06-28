"""Task 4: Morpho-lexical alignment engine.

align_verse() fuses an L0 verse surface string with normalized morph rows,
producing CoNLL-U Token objects. FORM is authoritative from L0; lemma/xpos/
Strong/translit come from the matched normalized source row.

Unmatched L0 words get Align=unmatched in MISC.
Leftover source rows (source_extra) are recorded on the last token.
"""

import csv
import difflib
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
_PUNCT = re.compile(r"[\.,;:·¶;·‘’'\"?!\[\]־׃\\/]")

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

    LXX-specific: LxxLemmas uses dotted disambiguation suffixes like
    "ασμα.1" (Song of Songs) to distinguish homographs.  The trailing
    ".<digits>" is stripped before general punctuation removal so the digit
    does not survive into the match key.  Additive-safe for NT/OT because
    those surface forms never carry such suffixes.

    Casefold: .lower() handles Greek majuscule incipits (e.g. "ΚΑΙ" ->
    "και") so all-caps corpus-initial words align to lowercase TSV keys.
    """
    # Strip LXX disambiguation suffix (e.g. "ασμα.1" -> "ασμα").
    s = re.sub(r"\.\d+$", "", s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _PUNCT.sub("", s).lower().strip()


def tokenize_l0(text: str) -> list:
    """Split an L0 verse string into a list of surface word strings.

    Punctuation characters are converted to spaces so they act as delimiters;
    the resulting tokens preserve the original Unicode including accents.
    """
    return [w for w in _PUNCT.sub(" ", text).split() if w]


def load_norm(norm_path: str) -> dict:
    """Load a normalized morph TSV at the given path into a ref->rows mapping.

    Args:
        norm_path: Absolute or ROOT-relative path to the TSV file.  The path
                   is taken directly from the registry entry's ``"norm"`` key
                   so that two entries sharing the same lang (e.g. nt/grc and
                   lxx/grc) can point at different TSV files without collision.

    Returns:
        dict mapping ref strings (e.g. '3JO.1.1') to sorted lists of row dicts.
    """
    path = Path(norm_path)
    if not path.is_absolute():
        path = ROOT / path
    by_ref: dict = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            row["idx"] = int(row["idx"])
            by_ref.setdefault(row["ref"], []).append(row)
    for ref in by_ref:
        by_ref[ref].sort(key=lambda r: r["idx"])
    return by_ref


def _build_token(
    i: int,
    w: str,
    match: "dict | None",
    lang: str,
    morph_scheme: str,
    headwords: "dict[str, str] | None",
) -> "Token":
    """Build a single CoNLL-U Token from a corpus word and (optionally) a matched
    norm row.  Shared by both surface-matching and positional alignment paths.
    """
    if match is None:
        # For morph_scheme="none" (LXX), keep UPOS empty ("_") consistent with
        # the empty-morph convention.  Other schemes use placeholder "X".
        upos = "_" if morph_scheme == "none" else "X"
        return Token(
            str(i), w, "_", upos, "_", "_",
            misc=format_misc("", "_", {}, "unmatched"),
        )

    if morph_scheme == "none":
        # LXX (and future morph_scheme="none" entries): emit lemma +
        # Strong= only; leave UPOS/XPOS/FEATS empty until a morph
        # source (e.g. TAGOT) is available.
        upos, xpos, feats = "_", "_", "_"
    else:
        upos, feats = decode(match["xpos"], lang)
        xpos = match["xpos"]

    misc = format_misc(match["strong"], match.get("translit", "_"), {}, None)

    # Hebrew LEMMA: use Strong's headword from shared map when available.
    # Tyndale 9xxx grammatical-particle codes (H9005-H9039) are not in
    # strongs-hebrew.xml; tokens with such codes fall back to "_" rather
    # than the TAHOT pointed surface (which contains morpheme-boundary
    # slashes and must never appear as a LEMMA value).
    # Greek LEMMA: keep the TAGNT/LxxLemmas dictionary form unchanged.
    lemma = match["lemma"]
    if lang == "hbo" and headwords is not None and match.get("strong"):
        lemma = headwords.get(match["strong"], "_")

    return Token(str(i), w, lemma, upos, xpos, feats, misc=misc)


def align_verse(
    ref: str,
    l0_text: str,
    norm_rows: list,
    lang: str,
    headwords: "dict[str, str] | None" = None,
    morph_scheme: str = "",
    positional: bool = False,
) -> list:
    """Align an L0 verse string against normalized morph rows.

    Two alignment modes are supported:

    **Surface matching** (default, ``positional=False``):
    Two-pointer walk of L0 words against source rows.

    * Direct hit: normalize_surface(L0[i]) == normalize_surface(TR[si]) -> match,
      advance si.
    * Resync: on a miss, look ahead up to ``_LOOKAHEAD`` source rows; if TR[si+k]
      matches L0[i] (k in 1.._LOOKAHEAD), the intervening rows TR[si..si+k-1] are
      treated as source-only (counted toward source_extra), si jumps past them,
      and L0[i] matches TR[si+k].  This recovers from a single divergent/extra
      source word without desyncing the rest of the verse.
    * Genuine divergence: if no lookahead position matches, L0[i] is emitted with
      placeholder tags + Align=unmatched and si is NOT advanced.

    **Positional alignment** (``positional=True``):
    Used for the LXX because LxxLemmas stores LEMMA forms (not inflected surface
    forms) as the TSV surface key, making surface matching unreliable.  Instead,
    TSV rows are matched to corpus words purely by position (corpus word i <->
    TSV row with idx=i).  Excess corpus words (TSV shorter than corpus) are marked
    unmatched; excess TSV rows (corpus shorter than TSV) are counted as source_extra
    on the last token.

    Any source rows left unconsumed are recorded as a single
    ``Align=source_extra:<n>`` on the last token.

    Args:
        ref:          Reference string, e.g. '3JO.1.1'.
        l0_text:      Raw verse string from the L0 corpus (authoritative).
        norm_rows:    List of normalized row dicts for this ref (idx-ordered).
        lang:         'grc' or 'hbo', passed to decode().
        headwords:    Optional {H#### -> clean_headword} dict.  When supplied
                      and lang is 'hbo', the CoNLL-U LEMMA for each matched
                      Hebrew token is taken from this map (keyed by the token's
                      Strong's number) instead of from the TAHOT surface column.
                      Tokens with no Strong's number or with a Strong's absent
                      from the map fall back to "_".
                      Greek path is unchanged (headwords is ignored for 'grc').
        morph_scheme: When ``"none"``, skip decode() entirely and leave
                      UPOS/XPOS/FEATS as ``"_"`` (LXX: lemma+Strong's only;
                      no open morph source yet).  Any other value (or empty
                      string) uses the full decode() path.
        positional:   When ``True``, use positional (idx-based) alignment instead
                      of surface matching.  Set by generate() when morph_scheme
                      is ``"none"`` (LXX).

    Returns:
        List of Token objects in L0 word order.
    """
    words = tokenize_l0(l0_text)
    rows = list(norm_rows)
    tokens = []

    if positional:
        # --- Positional alignment (LXX) with difflib-anchored resync ---
        #
        # LxxLemmas stores LEMMA forms (not inflected surfaces) as the TSV key, so
        # a straight positional zip silently mistags everything after the first
        # Swete-vs-CCAT edition divergence (insertion / deletion / substitution).
        #
        # Strategy: normalise both sequences and run difflib.SequenceMatcher to find
        # the anchors (words that match in both editions).  For each opcode block:
        #
        #   equal   → corpus[i] and tsv[j] share the same normalized key (article,
        #             particle, proper noun, indeclinable).  Pair them; Align=exact.
        #
        #   replace, equal lengths → inflected form vs lemma form between anchors.
        #             Pair positionally (corpus[i1+k] ↔ tsv[j1+k]); Align=positional.
        #             Lower confidence than exact, but no worse than the old whole-
        #             verse-abort since the flanking anchors constrain the block.
        #
        #   replace, unequal lengths / delete → genuine edition divergence.  Corpus
        #             words in this block have no reliable TSV counterpart; emit as
        #             Align=unmatched (no lemma/Strong=).  TSV rows on the j-side of
        #             an unequal replace are also unmatched → counted as source_extra.
        #
        #   insert  → TSV-only rows (CCAT has a word Swete omits).  Counted as
        #             source_extra on the last token (mirrors the surface-match path).
        #
        # This replaces the old whole-verse-abort for count mismatches, recovering
        # ~68% of previously dropped tokens while remaining auditable (Align markers
        # let the bridge weight confidence).  The only residual mistag risk is an
        # equal-length replace that happens to be a wholesale word swap rather than
        # inflection; those are tagged Align=positional, not Align=exact.

        ck = [normalize_surface(w) for w in words]
        tk = [normalize_surface(r["surface"]) for r in rows]

        # Default: every slot unmatched; will be overwritten by opcodes below.
        # Each slot is (row_or_None, align_tag_str).
        slots: list = [(None, "unmatched")] * len(words)
        pending_source_extra = 0

        matcher = difflib.SequenceMatcher(None, ck, tk, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    slots[i1 + k] = (rows[j1 + k], "exact")
            elif tag == "replace":
                corp_len = i2 - i1
                tsv_len = j2 - j1
                if corp_len == tsv_len:
                    # Equal-length block between anchors: pair positionally.
                    for k in range(corp_len):
                        slots[i1 + k] = (rows[j1 + k], "positional")
                else:
                    # Unequal lengths: cannot pair safely.
                    # Corpus words → unmatched; TSV rows → source_extra.
                    for k in range(corp_len):
                        slots[i1 + k] = (None, "unmatched")
                    pending_source_extra += tsv_len
            elif tag == "delete":
                # Corpus words with no TSV counterpart → unmatched (already default).
                pass  # slots[i1:i2] already (None, "unmatched")
            elif tag == "insert":
                # TSV rows with no corpus counterpart → source_extra.
                pending_source_extra += (j2 - j1)

        for i, w in enumerate(words, start=1):
            match_row, align_tag = slots[i - 1]
            tok = _build_token(i, w, match_row, lang, morph_scheme, headwords)
            if match_row is not None:
                # _build_token emitted Strong= etc. but no Align=.  Add it now.
                tok.misc = _append_align(tok.misc, align_tag)
            # When match_row is None, _build_token already set Align=unmatched.
            tokens.append(tok)

        # Attach accumulated source_extra to the last token (mirrors surface path).
        if pending_source_extra > 0 and tokens:
            tokens[-1].misc = _append_align(tokens[-1].misc, f"source_extra:{pending_source_extra}")

    else:
        # --- Surface matching (NT/OT) ---
        norm_rows_surf = [normalize_surface(r["surface"]) for r in rows]
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
                            skipped_extra += k      # rows si..j-1 are source-only
                            si = j + 1              # consume up to and incl. match
                            match = rows[j]
                            break

            tokens.append(_build_token(i, w, match, lang, morph_scheme, headwords))

        # Attach all unconsumed source rows (skips + trailing leftover) to last token.
        leftover = (len(rows) - si) + skipped_extra
        if leftover > 0 and tokens:
            tokens[-1].misc = _append_align(tokens[-1].misc, f"source_extra:{leftover}")

    return tokens
