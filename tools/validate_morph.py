"""Task 5: Structural validator and coverage oracle for morpho-lexical CoNLL-U output.

Validates morph/<testament>/<CODE>/NNN.conllu files against the L0 corpus.

Structural assertions (raise AssertionError on violation):
  - Every L0 verse has exactly one CoNLL-U sentence in morph/.
  - Every token FORM reconciles to its L0 verse text via reconcile_form().
  - Multiword ID ranges (e.g. "5-6") are well-formed integers if present.

Counters returned by validate():
  verses        -- total L0 verses processed
  tokens        -- total regular tokens (non-range rows)
  unmatched     -- tokens with Align=unmatched in MISC
  source_extra  -- sum of source_extra:<n> values across all tokens
  missing_strong -- tokens with no Strong= field in MISC

Pinned expected values for the NT (recorded from actual generation run):
EXPECTED_NT_VERSES     = 7957
EXPECTED_NT_TOKENS     = <filled after first run>
EXPECTED_NT_UNMATCHED  = <filled after first run>
EXPECTED_NT_SRC_EXTRA  = <filled after first run>
EXPECTED_NT_MISSING_STRONG = <filled after first run>
"""

import json
import sys
from pathlib import Path

from tools.align_morph import normalize_surface, tokenize_l0
from tools.conllu import parse_file

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
    else:
        raise NotImplementedError(f"validate() only supports 'nt' for now; got '{testament}'")

    total_verses = 0
    total_tokens = 0
    total_unmatched = 0
    total_src_extra = 0
    total_missing_strong = 0

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

                    # Count alignment markers.
                    is_unmatched = False
                    for part in tok.misc.split("|"):
                        if not part.startswith("Align="):
                            continue
                        for val in part[len("Align="):].split(","):
                            if val == "unmatched":
                                is_unmatched = True
                                total_unmatched += 1
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

    return {
        "verses": total_verses,
        "tokens": total_tokens,
        "unmatched": total_unmatched,
        "source_extra": total_src_extra,
        "missing_strong": total_missing_strong,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tools.validate_morph <testament>")
        print("  testament: nt")
        sys.exit(1)

    testament = sys.argv[1].lower()
    print(f"Validating morph output for testament: {testament} ...")
    result = validate(testament)

    print(
        f"verses={result['verses']} "
        f"tokens={result['tokens']} "
        f"unmatched={result['unmatched']} "
        f"source_extra={result['source_extra']} "
        f"missing_strong={result['missing_strong']}"
    )

    pct_unmatched = 100.0 * result["unmatched"] / result["tokens"] if result["tokens"] else 0
    print(f"unmatched %: {pct_unmatched:.2f}%  (genuine TR/STEPBible surface divergence)")

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
