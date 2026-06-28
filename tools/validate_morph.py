"""Task 5: Structural validator and coverage oracle for morpho-lexical CoNLL-U output.

Validates morph/<testament>/<CODE>/NNN.conllu files against the L0 corpus.

Structural assertions (raise AssertionError on violation):
  - Every L0 verse has exactly one CoNLL-U sentence in morph/.
  - Every token FORM reconciles to its L0 verse text via reconcile_form().
  - Multiword ID ranges (e.g. "5-6") are well-formed integers if present.

Counters returned by validate():
  verses         -- total L0 verses processed
  tokens         -- total regular tokens (non-range rows)
  unmatched      -- tokens with Align=unmatched in MISC
  count_mismatch -- tokens with Align=count_mismatch in MISC (LXX: whole-verse-abort)
  source_extra   -- sum of source_extra:<n> values across all tokens
  missing_strong -- tokens with no Strong= field in MISC
  with_morph     -- tokens with any non-empty UPOS/XPOS/FEATS column

Pinned expected values for the NT (recorded from actual generation run):
EXPECTED_NT_VERSES     = 7957
EXPECTED_NT_TOKENS     = 140610
EXPECTED_NT_UNMATCHED  = 6615
EXPECTED_NT_SRC_EXTRA  = 3549
EXPECTED_NT_MISSING_STRONG = 6615
"""

import json
import sys
from pathlib import Path

from tools.align_morph import normalize_surface, tokenize_l0
from tools.conllu import parse_file
from tools.lxx_versification import lxx_books as _lxx_books_fn

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Pinned expected constants for the NT.
# These are real observed values from the generation run -- do not invent.
# Unmatched reflects genuine L0 (Textus Receptus) vs STEPBible-TR surface
# divergence; it is not an error. missing_strong == unmatched because
# only unmatched tokens lack a Strong= field (matched tokens always get one
# from the normalized TSV).
# ---------------------------------------------------------------------------
EXPECTED_NT_VERSES = 7957
EXPECTED_NT_TOKENS = 140610
EXPECTED_NT_UNMATCHED = 6615    # 4.70% genuine TR/STEPBible surface divergence
EXPECTED_NT_SRC_EXTRA = 3549
EXPECTED_NT_MISSING_STRONG = 6615  # unmatched tokens lack Strong= by design

# ---------------------------------------------------------------------------
# Pinned expected constants for the OT.
# Observed from the Task-6 generation run over the full 39-book Hebrew OT.
# Unmatched (4.74%) is caused by three known sources:
#   1. Ketiv/Qere variants: TAHOT follows Q (Qere) but L0 occasionally has
#      slightly different pointing that resists normalization.
#   2. Compound word segmentation: a few multi-morpheme compounds where the
#      TAHOT surface even after slash-stripping doesn't match the L0 surface
#      (e.g. pronominal suffixes on rare verb forms, hapax morphology).
#   3. Restored/LXX-extra words (type R, X in TAHOT) that have no L0 parallel.
# missing_strong == unmatched: only unmatched tokens lack Strong=.
# ---------------------------------------------------------------------------
EXPECTED_OT_VERSES = 23145
EXPECTED_OT_TOKENS = 312079
EXPECTED_OT_UNMATCHED = 14794   # 4.74% genuine WLC/TAHOT surface divergence
EXPECTED_OT_SRC_EXTRA = 7889
EXPECTED_OT_MISSING_STRONG = 14794  # unmatched tokens lack Strong= by design

# ---------------------------------------------------------------------------
# Pinned expected constants for the LXX (54 books; Swete/NETS Greek corpus).
# Generated from Task 5 full-corpus run (python -m tools.generate_morph --testament lxx).
#
# LXX uses POSITIONAL alignment (morph_scheme="none"): each Swete verse-word is
# matched by position to its CCAT-sourced lemma/Strong's row.  When the Swete
# word-count != CCAT word-count for a verse, the WHOLE verse is aborted and all
# its tokens receive Align=count_mismatch (Task 4 design; wrong-data-silent is
# worse than no-data-loud).
#
# count_mismatch: 186680/583148 = 32.01% of tokens are in count_mismatch verses.
#   This reflects genuine Swete-vs-CCAT edition divergence (additions, omissions,
#   verse-splits) -- it is NOT an error and must NOT be "improved" by altering
#   the abort logic.
#
# missing_strong: 235275 total tokens lack Strong=.
#   - 186680 from count_mismatch verses (whole-verse-abort emits no Strong=).
#   - 48595 from matched verses where the CCAT-LXX TSV has no Strong's entry
#     (LXX-only vocabulary -- deuterocanon words, proper nouns, etc. -- that
#     were not numbered in the NT-based Strong's Greek system).
#   Strong's link rate on matched tokens = 347873/396468 = 87.75%.
#
# with_morph == 0: LXX morph columns (UPOS/XPOS/FEATS) are intentionally empty.
#   Morphological tagging is deferred to TAGOT (a future task that will add
#   CATSS/OpenGNT-style part-of-speech tags).  This pin enforces the invariant.
# ---------------------------------------------------------------------------
EXPECTED_LXX_VERSES = 28873       # total L0 verses across 54 LXX books
EXPECTED_LXX_TOKENS = 583148      # total tokens (from positional alignment)
EXPECTED_LXX_UNMATCHED = 0        # positional alignment does not emit "unmatched"
EXPECTED_LXX_COUNT_MISMATCH = 186680  # 32.01% Swete-vs-CCAT edition divergence
EXPECTED_LXX_SRC_EXTRA = 286769   # sum of source_extra:<n> across all tokens
EXPECTED_LXX_MISSING_STRONG = 235275  # count_mismatch (186680) + LXX-only no-Strong= (48595)
EXPECTED_LXX_WITH_MORPH = 0       # morph deferred to TAGOT; lemma+Strong's only


def reconcile_form(form: str, l0_text: str) -> bool:
    """Return True if *form* appears as a word in *l0_text* (normalized comparison).

    Normalization mirrors how align_morph tokenizes and compares: NFD-decompose,
    drop combining characters (accents), strip common punctuation, lowercase.
    The form is considered present if its normalized version matches any
    normalized token from the L0 verse text.

    Args:
        form:     A token FORM string from a CoNLL-U file.
        l0_text:  The raw L0 verse string (e.g. from greek_textus_receptus).

    Returns:
        True if normalize_surface(form) matches normalize_surface(w) for some
        word w in tokenize_l0(l0_text); False otherwise.
    """
    norm_form = normalize_surface(form)
    for word in tokenize_l0(l0_text):
        if normalize_surface(word) == norm_form:
            return True
    return False


def _load_nt_books() -> list:
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "nt"]


def _load_ot_books() -> list:
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def books_lxx() -> list:
    """Return the full LXX book list (synthesized at runtime by lxx_versification).

    IMPORTANT: Do NOT filter data/books.json by testament=="lxx" here -- that
    returns only the 4 new LXX-only codes (3MA, 4MA, ODE, PSS).  The canonical
    LXX book set is built by lxx_versification.lxx_books() which merges OT rows
    carrying lxx_order, apo rows carrying lxx_order, and the 4 native lxx rows.
    """
    return _lxx_books_fn()


def _load_morph_sources() -> dict:
    """Return dict mapping testament -> lang entry dict."""
    registry = json.loads((ROOT / "data" / "morph-sources.json").read_text(encoding="utf-8"))
    return {e["testament"]: e for e in registry["languages"]}


def validate(testament: str) -> dict:
    """Validate morph CoNLL-U output against the L0 corpus for *testament*.

    Raises AssertionError on structural violations.
    Returns a dict with keys: verses, tokens, unmatched, source_extra, missing_strong.
    """
    sources = _load_morph_sources()
    assert testament in sources, f"No morph source registered for testament '{testament}'"
    entry = sources[testament]
    l0_field = entry["l0_field"]

    if testament == "nt":
        books = _load_nt_books()
    elif testament == "ot":
        books = _load_ot_books()
    elif testament == "lxx":
        # MUST use lxx_books() -- do NOT filter books.json by testament=="lxx"
        # (that returns only 4 codes; the full LXX set has 56 synthesised entries).
        books = books_lxx()
    else:
        raise NotImplementedError(f"validate() only supports 'nt', 'ot', 'lxx'; got '{testament}'")

    total_verses = 0
    total_tokens = 0
    total_unmatched = 0
    total_count_mismatch = 0
    total_src_extra = 0
    total_missing_strong = 0
    total_with_morph = 0

    for book in books:
        code = book["code"]
        num_chapters = book["chapters"]

        for ch_num in range(1, num_chapters + 1):
            l0_path = ROOT / "bible" / testament / code / f"{ch_num:03d}.json"
            if not l0_path.exists():
                continue

            chapter_data = json.loads(l0_path.read_text(encoding="utf-8"))
            verses = chapter_data.get("verses", [])
            if not verses:
                continue

            conllu_path = ROOT / "morph" / testament / code / f"{ch_num:03d}.conllu"

            # Build a map of ref -> token list from the CoNLL-U file.
            assert conllu_path.exists(), (
                f"Missing CoNLL-U file: {conllu_path} "
                f"(expected one sentence per L0 verse)"
            )
            sentences = parse_file(conllu_path)
            conllu_by_ref = {}
            for ref, tokens in sentences:
                assert ref not in conllu_by_ref, (
                    f"Duplicate ref '{ref}' in {conllu_path}"
                )
                conllu_by_ref[ref] = tokens

            for verse_obj in verses:
                v_num = verse_obj["verse"]
                l0_text = verse_obj.get(l0_field, "")
                if not l0_text:
                    continue

                ref = f"{code}.{ch_num}.{v_num}"
                total_verses += 1

                # Structural assertion: exactly one CoNLL-U sentence per L0 verse.
                assert ref in conllu_by_ref, (
                    f"L0 verse {ref} has no CoNLL-U sentence in {conllu_path}"
                )
                tokens = conllu_by_ref[ref]

                for tok in tokens:
                    # Validate multiword ID ranges if present.
                    if "-" in tok.idx:
                        parts = tok.idx.split("-")
                        assert len(parts) == 2, (
                            f"Malformed multiword ID '{tok.idx}' in {ref}"
                        )
                        lo, hi = parts
                        assert lo.isdigit() and hi.isdigit(), (
                            f"Multiword ID '{tok.idx}' not integer bounds in {ref}"
                        )
                        assert int(lo) < int(hi), (
                            f"Multiword ID '{tok.idx}' not lo < hi in {ref}"
                        )
                        # Multiword range rows are not counted as regular tokens.
                        continue

                    total_tokens += 1

                    # Structural assertion: FORM must reconcile to L0 verse text.
                    assert reconcile_form(tok.form, l0_text), (
                        f"Token FORM '{tok.form}' in {ref} not found in L0 text: "
                        f"'{l0_text}'"
                    )

                    # OT-only contract: Hebrew LEMMA must not contain morpheme-
                    # boundary markers (/ or \).  Their presence indicates the old
                    # behaviour of using the TAHOT pointed surface as LEMMA rather
                    # than the Strong's dictionary headword.
                    if testament == "ot":
                        assert "/" not in tok.lemma and "\\" not in tok.lemma, (
                            f"Hebrew LEMMA '{tok.lemma}' in {ref} contains a slash "
                            f"(morpheme-boundary marker must not appear in LEMMA; "
                            f"LEMMA must be a Strong's dictionary headword)"
                        )

                    # Count alignment markers.
                    for part in tok.misc.split("|"):
                        if not part.startswith("Align="):
                            continue
                        for val in part[len("Align="):].split(","):
                            if val == "unmatched":
                                total_unmatched += 1
                            elif val == "count_mismatch":
                                total_count_mismatch += 1
                            elif val.startswith("source_extra:"):
                                try:
                                    total_src_extra += int(val.split(":")[1])
                                except ValueError:
                                    pass

                    # Count missing Strong=.
                    has_strong = any(
                        p.startswith("Strong=") for p in tok.misc.split("|")
                    )
                    if not has_strong:
                        total_missing_strong += 1

                    # Count tokens with non-empty morph columns (UPOS/XPOS/FEATS).
                    # For LXX this must be 0 (morph deferred to TAGOT).
                    if tok.upos != "_" or tok.xpos != "_" or tok.feats != "_":
                        total_with_morph += 1

    return {
        "verses": total_verses,
        "tokens": total_tokens,
        "unmatched": total_unmatched,
        "count_mismatch": total_count_mismatch,
        "source_extra": total_src_extra,
        "missing_strong": total_missing_strong,
        "with_morph": total_with_morph,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tools.validate_morph <testament>")
        print("  testament: nt | ot | lxx")
        sys.exit(1)

    testament = sys.argv[1].lower()
    print(f"Validating morph output for testament: {testament} ...")
    result = validate(testament)

    print(
        f"verses={result['verses']} "
        f"tokens={result['tokens']} "
        f"unmatched={result['unmatched']} "
        f"count_mismatch={result['count_mismatch']} "
        f"source_extra={result['source_extra']} "
        f"missing_strong={result['missing_strong']} "
        f"with_morph={result['with_morph']}"
    )

    pct_unmatched = 100.0 * result["unmatched"] / result["tokens"] if result["tokens"] else 0
    pct_count_mismatch = 100.0 * result["count_mismatch"] / result["tokens"] if result["tokens"] else 0
    print(f"unmatched %: {pct_unmatched:.2f}%")
    print(f"count_mismatch %: {pct_count_mismatch:.2f}%")

    errors = []
    if testament == "nt":
        if result["verses"] != EXPECTED_NT_VERSES:
            errors.append(
                f"verses {result['verses']} != expected {EXPECTED_NT_VERSES}"
            )
        if result["tokens"] != EXPECTED_NT_TOKENS:
            errors.append(
                f"tokens {result['tokens']} != expected {EXPECTED_NT_TOKENS}"
            )
        if result["unmatched"] != EXPECTED_NT_UNMATCHED:
            errors.append(
                f"unmatched {result['unmatched']} != expected {EXPECTED_NT_UNMATCHED}"
            )
        if result["source_extra"] != EXPECTED_NT_SRC_EXTRA:
            errors.append(
                f"source_extra {result['source_extra']} != expected {EXPECTED_NT_SRC_EXTRA}"
            )
        if result["missing_strong"] != EXPECTED_NT_MISSING_STRONG:
            errors.append(
                f"missing_strong {result['missing_strong']} != expected {EXPECTED_NT_MISSING_STRONG}"
            )
    elif testament == "ot":
        if result["verses"] != EXPECTED_OT_VERSES:
            errors.append(
                f"verses {result['verses']} != expected {EXPECTED_OT_VERSES}"
            )
        if result["tokens"] != EXPECTED_OT_TOKENS:
            errors.append(
                f"tokens {result['tokens']} != expected {EXPECTED_OT_TOKENS}"
            )
        if result["unmatched"] != EXPECTED_OT_UNMATCHED:
            errors.append(
                f"unmatched {result['unmatched']} != expected {EXPECTED_OT_UNMATCHED}"
            )
        if result["source_extra"] != EXPECTED_OT_SRC_EXTRA:
            errors.append(
                f"source_extra {result['source_extra']} != expected {EXPECTED_OT_SRC_EXTRA}"
            )
        if result["missing_strong"] != EXPECTED_OT_MISSING_STRONG:
            errors.append(
                f"missing_strong {result['missing_strong']} != expected {EXPECTED_OT_MISSING_STRONG}"
            )
    elif testament == "lxx":
        if result["verses"] != EXPECTED_LXX_VERSES:
            errors.append(
                f"verses {result['verses']} != expected {EXPECTED_LXX_VERSES}"
            )
        if result["tokens"] != EXPECTED_LXX_TOKENS:
            errors.append(
                f"tokens {result['tokens']} != expected {EXPECTED_LXX_TOKENS}"
            )
        if result["unmatched"] != EXPECTED_LXX_UNMATCHED:
            errors.append(
                f"unmatched {result['unmatched']} != expected {EXPECTED_LXX_UNMATCHED}"
            )
        if result["count_mismatch"] != EXPECTED_LXX_COUNT_MISMATCH:
            errors.append(
                f"count_mismatch {result['count_mismatch']} != expected {EXPECTED_LXX_COUNT_MISMATCH}"
            )
        if result["source_extra"] != EXPECTED_LXX_SRC_EXTRA:
            errors.append(
                f"source_extra {result['source_extra']} != expected {EXPECTED_LXX_SRC_EXTRA}"
            )
        if result["missing_strong"] != EXPECTED_LXX_MISSING_STRONG:
            errors.append(
                f"missing_strong {result['missing_strong']} != expected {EXPECTED_LXX_MISSING_STRONG}"
            )
        # Hard invariant: LXX morph columns must be empty (morph deferred to TAGOT).
        assert result["with_morph"] == 0, (
            f"with_morph={result['with_morph']} != 0 "
            f"(morph deferred to TAGOT; lemma+Strong's only)"
        )
        if result["with_morph"] != EXPECTED_LXX_WITH_MORPH:
            errors.append(
                f"with_morph {result['with_morph']} != expected {EXPECTED_LXX_WITH_MORPH}"
            )
    else:
        print(f"WARNING: No pinned constants for testament '{testament}'; skipping pin check.")

    for e in errors:
        print("PIN MISMATCH:", e)

    if errors:
        sys.exit(1)
    else:
        print("All pins match. Validation passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
