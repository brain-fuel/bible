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
    """Extra corpus words (beyond TSV rows) are marked unmatched."""
    norm = [_LXX_ROW(1, "και", "καί", "G2532")]
    toks = align_verse("RUT.1.1", "ΚΑΙ ἐγένετο", norm, "grc", morph_scheme="none", positional=True)
    assert toks[0].lemma == "καί"
    assert "unmatched" not in toks[0].misc
    assert "Align=unmatched" in toks[1].misc


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
