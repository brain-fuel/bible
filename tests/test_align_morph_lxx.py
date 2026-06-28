# tests/test_align_morph_lxx.py
"""Task 4: Tests for LXX-specific morph engine generalization."""

from tools.align_morph import align_verse, load_norm, normalize_surface


def test_load_norm_takes_explicit_path(tmp_path):
    """load_norm must accept a file-path string, not a lang code."""
    p = tmp_path / "lxx.tsv"
    p.write_text(
        "ref\tidx\tsurface\tlemma\tstrong\txpos\tfeats\ttranslit\tedition\n"
        "GEN.1.1\t1\tεν\tἐν\tG1722\t_\t_\t_\tLXX\n",
        encoding="utf-8",
    )
    by_ref = load_norm(str(p))
    assert by_ref["GEN.1.1"][0]["strong"] == "G1722"
    assert by_ref["GEN.1.1"][0]["lemma"] == "ἐν"


def test_normalize_surface_casefolds_majuscule():
    """All-caps majuscule incipits (e.g. 'ΚΑΙ') must normalize to same key as 'και'."""
    assert normalize_surface("ΚΑΙ") == normalize_surface("και")
    assert normalize_surface("ΕΝ") == normalize_surface("εν")
    assert normalize_surface("ΛΟΓΟΙ") == normalize_surface("λογοι")


def test_normalize_surface_strips_disambiguation_suffix():
    """LxxLemmas uses 'word.N' suffixes (e.g. 'ασμα.1') for disambiguation; strip them."""
    assert normalize_surface("ασμα.1") == normalize_surface("ασμα")
    assert normalize_surface("ασμα.12") == normalize_surface("ασμα")
    # Existing pilcrow test must still pass after this change
    assert normalize_surface("ἀληθείᾳ.¶") == normalize_surface("ἀληθείᾳ")


# ---------------------------------------------------------------------------
# Positional alignment (LXX) -- morph_scheme="none", positional=True
# ---------------------------------------------------------------------------

_LXX_ROW = lambda idx, surface, lemma, strong: {
    "idx": idx, "surface": surface, "lemma": lemma, "strong": strong,
    "xpos": "_", "translit": "_", "edition": "LXX",
}


def test_align_verse_lxx_positional_aligns_by_idx():
    """LXX positional mode matches corpus word i to TSV row idx=i (lemma form ok)."""
    # TSV uses lemma "γινομαι" for corpus "ἐγένετο" -- surface mismatch OK
    norm = [
        _LXX_ROW(1, "και", "καί", "G2532"),
        _LXX_ROW(2, "γινομαι", "γίνομαι", "G1096"),
        _LXX_ROW(3, "εν", "ἐν", "G1722"),
    ]
    l0 = "ΚΑΙ ἐγένετο ἐν"
    toks = align_verse("RUT.1.1", l0, norm, "grc", morph_scheme="none", positional=True)
    assert [t.form for t in toks] == ["ΚΑΙ", "ἐγένετο", "ἐν"]
    # Position 2: ἐγένετο -> row with idx=2 (lemma "γίνομαι")
    assert toks[1].lemma == "γίνομαι"
    assert "Strong=G1096" in toks[1].misc
    assert toks[1].upos == "_"
    assert "unmatched" not in toks[1].misc


def test_align_verse_lxx_positional_empty_morph():
    """Positional LXX tokens have UPOS/XPOS/FEATS all '_' (morph_scheme='none')."""
    norm = [_LXX_ROW(1, "εν", "ἐν", "G1722")]
    toks = align_verse("GEN.1.1", "ἐν", norm, "grc", morph_scheme="none", positional=True)
    assert toks[0].upos == "_"
    assert toks[0].xpos == "_"
    assert toks[0].feats == "_"
    assert toks[0].lemma == "ἐν"
    assert "Strong=G1722" in toks[0].misc


def test_align_verse_lxx_positional_corpus_longer():
    """Count mismatch (corpus > TSV): difflib resync pairs the anchor, marks divergence.

    Previously the whole verse was aborted as count_mismatch.  The new difflib
    resync recovers: "ΚΑΙ" matches "και" (Align=exact, Strong=G2532) and only the
    genuinely-unmatched word "ἐγένετο" (which has no TSV row) gets Align=unmatched.
    """
    norm = [_LXX_ROW(1, "και", "καί", "G2532")]
    toks = align_verse("RUT.1.1", "ΚΑΙ ἐγένετο", norm, "grc", morph_scheme="none", positional=True)
    assert len(toks) == 2
    # "ΚΑΙ" matches "και" in the TSV → paired as an exact anchor.
    assert toks[0].lemma == "καί"
    assert "Strong=G2532" in toks[0].misc
    assert "Align=exact" in toks[0].misc
    assert "count_mismatch" not in toks[0].misc
    # "ἐγένετο" has no TSV counterpart (delete block) → Align=unmatched.
    assert toks[1].lemma == "_"
    assert "Align=unmatched" in toks[1].misc
    assert "Strong=" not in toks[1].misc
    assert "count_mismatch" not in toks[1].misc


def test_align_verse_lxx_positional_tsv_longer_source_extra():
    """Extra TSV rows (beyond corpus words) are recorded as source_extra."""
    norm = [
        _LXX_ROW(1, "και", "καί", "G2532"),
        _LXX_ROW(2, "γινομαι", "γίνομαι", "G1096"),
        _LXX_ROW(3, "εν", "ἐν", "G1722"),
    ]
    toks = align_verse("RUT.1.1", "ΚΑΙ", norm, "grc", morph_scheme="none", positional=True)
    assert len(toks) == 1
    assert "source_extra:2" in toks[0].misc


def test_difflib_resync_mid_verse_insert():
    """difflib resync: a mid-verse TSV insertion is identified; all corpus words get lemmas.

    The old behavior aborted the whole verse as count_mismatch.  The new difflib
    resync correctly identifies "χ" as a TSV-only insertion (source_extra) and pairs
    each of α β γ δ with their correct lemma row -- no naive positional shift.
    """
    # TSV has 5 rows (CCAT insertion at position 2: 'χ' row is extra).
    # Corpus has 4 words: α β γ δ (Swete text).
    # Naive positional zip would give 'β' -> chi, 'γ' -> beta, 'δ' -> gamma (all wrong).
    # difflib sees: equal[α,α], insert[χ], equal[β,β][γ,γ][δ,δ].
    norm = [
        _LXX_ROW(1, "α", "alpha", "G0001"),
        _LXX_ROW(2, "χ", "chi",   "G0000"),  # extra CCAT row -- should become source_extra
        _LXX_ROW(3, "β", "beta",  "G0002"),
        _LXX_ROW(4, "γ", "gamma", "G0003"),
        _LXX_ROW(5, "δ", "delta", "G0004"),
    ]
    l0 = "α β γ δ"  # 4 corpus words vs 5 TSV rows
    toks = align_verse("TST.1.1", l0, norm, "grc", morph_scheme="none", positional=True)

    assert len(toks) == 4, f"expected 4 tokens, got {len(toks)}"

    # All four corpus words are correctly paired with their TSV rows.
    assert toks[0].form == "α" and toks[0].lemma == "alpha"
    assert "Strong=G0001" in toks[0].misc

    assert toks[1].form == "β" and toks[1].lemma == "beta"
    assert "Strong=G0002" in toks[1].misc

    assert toks[2].form == "γ" and toks[2].lemma == "gamma"
    assert "Strong=G0003" in toks[2].misc

    assert toks[3].form == "δ" and toks[3].lemma == "delta"
    assert "Strong=G0004" in toks[3].misc

    # No count_mismatch anywhere -- difflib resync replaces the whole-verse-abort.
    for tok in toks:
        assert "count_mismatch" not in tok.misc, (
            f"token '{tok.form}' still has count_mismatch in misc: {tok.misc!r}"
        )

    # The extra TSV row "χ" must be accounted for as source_extra:1 on the last token.
    source_extra_total = 0
    for tok in toks:
        for part in tok.misc.split("|"):
            if part.startswith("Align="):
                for val in part[len("Align="):].split(","):
                    if val.startswith("source_extra:"):
                        source_extra_total += int(val.split(":")[1])
    assert source_extra_total == 1, (
        f"expected source_extra:1 (the 'χ' TSV row), got total {source_extra_total}"
    )


# ---------------------------------------------------------------------------
# New tests for the difflib-anchored resync algorithm
# ---------------------------------------------------------------------------

def test_difflib_resync_equal_length_replace_positional():
    """Equal-length replace block: paired positionally with Align=positional and lemma attached.

    When a corpus word doesn't normalize to the same key as its TSV counterpart
    (inflected vs. lemma form), but is in an equal-length replace block, the pair
    is marked Align=positional (lower confidence) with the lemma attached.
    """
    norm = [
        _LXX_ROW(1, "α", "alpha", "G0001"),   # "α"=="α" → equal block, Align=exact
        _LXX_ROW(2, "φ", "phi",   "G9999"),   # "β"!="φ" → equal-length replace → Align=positional
    ]
    l0 = "α β"
    toks = align_verse("TST.1.2", l0, norm, "grc", morph_scheme="none", positional=True)

    assert len(toks) == 2
    # "α" is an exact anchor.
    assert toks[0].lemma == "alpha"
    assert "Strong=G0001" in toks[0].misc
    assert "Align=exact" in toks[0].misc

    # "β" is in an equal-length replace block with "φ" → paired positionally.
    assert toks[1].lemma == "phi"
    assert "Strong=G9999" in toks[1].misc
    assert "Align=positional" in toks[1].misc
    assert "unmatched" not in toks[1].misc
    assert "count_mismatch" not in toks[1].misc


def test_difflib_resync_unequal_replace_unmatched():
    """Unequal-length replace block: corpus words get Align=unmatched, flanking anchors paired.

    When a corpus-side block has 2 words but the TSV side has only 1 row (or vice
    versa), pairing would silently mistag at least one word.  Both corpus words in
    the block are marked Align=unmatched (no Strong=).  The flanking anchor words
    (which ARE in equal blocks) are correctly paired.
    """
    # ck = ["α", "β", "γ", "δ"]
    # tk = ["α", "φψ", "δ"]
    # difflib: equal[α,α], replace([β,γ] vs [φψ]) -- unequal 2 vs 1, equal[δ,δ]
    norm = [
        _LXX_ROW(1, "α",  "alpha",  "G0001"),
        _LXX_ROW(2, "φψ", "phipsi", "G8888"),  # 1 TSV row vs 2 corpus words
        _LXX_ROW(3, "δ",  "delta",  "G0004"),
    ]
    l0 = "α β γ δ"  # "β","γ" vs single TSV row "φψ" → unequal replace
    toks = align_verse("TST.1.3", l0, norm, "grc", morph_scheme="none", positional=True)

    assert len(toks) == 4

    # "α" and "δ" are flanking anchors, correctly paired.
    assert toks[0].lemma == "alpha" and "Strong=G0001" in toks[0].misc
    assert toks[3].lemma == "delta" and "Strong=G0004" in toks[3].misc

    # "β" and "γ" are in an unequal replace block → Align=unmatched, no Strong=.
    assert toks[1].lemma == "_"
    assert "Align=unmatched" in toks[1].misc
    assert "Strong=" not in toks[1].misc

    assert toks[2].lemma == "_"
    assert "Align=unmatched" in toks[2].misc
    assert "Strong=" not in toks[2].misc
