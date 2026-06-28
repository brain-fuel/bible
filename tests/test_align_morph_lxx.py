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
    """Count mismatch (corpus longer than TSV): whole verse is aborted.

    Even when corpus has more words than TSV, a mid-verse deletion in the TSV
    would mistag all words after the deletion point.  Since there is no shared
    surface key to locate the deletion, the whole verse is aborted as
    count_mismatch -- prefer missing data over wrong data.
    """
    norm = [_LXX_ROW(1, "και", "καί", "G2532")]
    toks = align_verse("RUT.1.1", "ΚΑΙ ἐγένετο", norm, "grc", morph_scheme="none", positional=True)
    # Both corpus words emitted as count_mismatch; no lemma/Strong assigned.
    assert len(toks) == 2
    for tok in toks:
        assert tok.lemma == "_"
        assert "count_mismatch" in tok.misc
        assert "source_short:1" in tok.misc
        assert "Strong=" not in tok.misc


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


def test_positional_count_mismatch_aborts_verse():
    """Mid-verse insertion in TSV (count mismatch) must abort the whole verse.

    When TSV has M rows and corpus has N != M words, positional zip silently
    mistags every word after the insertion/deletion point -- no shared surface
    key can locate the divergence.  The fix: emit ALL tokens as
    Align=count_mismatch with empty lemma/Strong so no wrong data enters the
    floor.  Prefer missing data over wrong data.
    """
    # TSV has 5 rows (CCAT insertion at position 2: 'χ' row is extra).
    # Corpus has 4 words: α β γ δ (Swete text).
    # Naive positional zip would give corpus word 'β' the lemma for 'χ',
    # 'γ' the lemma for 'β', 'δ' the lemma for 'γ' -- all WRONG after position 2.
    norm = [
        _LXX_ROW(1, "α", "alpha", "G0001"),
        _LXX_ROW(2, "χ", "chi",   "G0000"),  # extra CCAT row (insertion)
        _LXX_ROW(3, "β", "beta",  "G0002"),
        _LXX_ROW(4, "γ", "gamma", "G0003"),
        _LXX_ROW(5, "δ", "delta", "G0004"),
    ]
    l0 = "α β γ δ"  # 4 corpus words vs 5 TSV rows -> count mismatch
    toks = align_verse("TST.1.1", l0, norm, "grc", morph_scheme="none", positional=True)

    # Whole verse must be aborted: every token has empty lemma + count_mismatch.
    assert len(toks) == 4, f"expected 4 tokens (one per corpus word), got {len(toks)}"
    for tok in toks:
        assert tok.lemma == "_", (
            f"token '{tok.form}' got unexpected lemma '{tok.lemma}'; "
            "count-mismatch verse must produce no lemma data"
        )
        assert "count_mismatch" in tok.misc, (
            f"token '{tok.form}' missing count_mismatch marker in misc: {tok.misc!r}"
        )
        assert "Strong=" not in tok.misc, (
            f"token '{tok.form}' wrongly carries Strong= in a count-mismatch verse: {tok.misc!r}"
        )

    # Key correctness check: corpus word 'γ' (index 2) must NOT carry beta/G0002
    # (which naive positional zip would assign because TSV row 2 is 'beta').
    gamma_tok = toks[2]
    assert gamma_tok.form == "γ"
    assert gamma_tok.lemma == "_"  # not "beta"
    assert "Strong=G0002" not in gamma_tok.misc
