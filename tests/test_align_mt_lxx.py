"""Tests for tools.align_mt_lxx — TDD phase (write tests first, watch fail).

Three minimal tests:
1. align_verse_pair provenance — edges carry all required fields.
2. no-Strong LXX token produces no edge.
3. aggregate_verse_pairs collapses repeated (mt_strong, lxx_strong) pairs
   across verse-pairs into one row with summed cooccur and correct
   exact/positional split.
"""
from tools.align_mt_lxx import align_verse_pair, aggregate_verse_pairs


def test_verse_level_edges_carry_provenance():
    """align_verse_pair emits edges with all required provenance fields."""
    mt = [{"strong": "H7225", "lemma": "רֵאשִׁית"}]
    lxx = [{"strong": "G0746", "lemma": "ἀρχή", "align": "exact"}]
    edges = align_verse_pair("GEN.1.1", "GEN.1.1", mt, lxx)
    assert len(edges) == 1, "expected one edge for one MT x one LXX token"
    e = edges[0]
    assert e["mt_strong"] == "H7225"
    assert e["lxx_strong"] == "G0746"
    assert e["lxx_lemma"] == "ἀρχή"
    assert e["confidence"] == "verse-cooccurrence"
    assert e["lxx_align"] == "exact"
    assert e["src"] == "derived:verse-cooccurrence"


def test_no_strong_lxx_token_yields_no_edge():
    """LXX tokens without a Strong= value (empty strong) produce no edges."""
    mt = [{"strong": "H7225", "lemma": "רֵאשִׁית"}]
    # empty strong — as produced by Align=unmatched or Align=exact-with-no-Strong tokens
    lxx = [{"strong": "", "lemma": "ἀκατασκεύαστος", "align": "exact"}]
    edges = align_verse_pair("GEN.1.2", "GEN.1.2", mt, lxx)
    assert edges == []


def test_aggregation_collapses_repeated_pairs():
    """aggregate_verse_pairs collapses the same (H,G) pair across two verse-pairs.

    Verse 1: H7225 x G0746 with align=exact   -> cooccur+1, exact+1
    Verse 2: H7225 x G0746 with align=positional -> cooccur+1, positional+1
    Result: ONE aggregate row with cooccur=2, exact=1, positional=1.
    """
    verse_pairs = [
        (
            "GEN.1.1",
            "GEN.1.1",
            [{"strong": "H7225"}],
            [{"strong": "G0746", "lemma": "ἀρχή", "align": "exact"}],
        ),
        (
            "GEN.1.2",
            "GEN.1.2",
            [{"strong": "H7225"}],
            [{"strong": "G0746", "lemma": "ἀρχή", "align": "positional"}],
        ),
    ]
    rows = aggregate_verse_pairs(verse_pairs)
    assert len(rows) == 1, f"expected 1 aggregate row, got {len(rows)}"
    r = rows[0]
    assert r["mt_strong"] == "H7225"
    assert r["lxx_strong"] == "G0746"
    assert r["cooccur"] == 2
    assert r["exact"] == 1
    assert r["positional"] == 1
