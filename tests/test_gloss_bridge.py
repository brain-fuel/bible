# tests/test_gloss_bridge.py
from tools.relations.gloss_bridge import (
    FANOUT_PENALTY_SCALE,
    gloss_term_index,
    mine_relations,
)

ENTRIES = [
    {"strong":"G0026","lemma":"ἀγάπη","glosses":{"en":[{"text":"love, affection","src":"x"}]}},
    {"strong":"G5479","lemma":"χαρά","glosses":{"en":[{"text":"joy, gladness","src":"x"}]}},
    {"strong":"G3077","lemma":"λύπη","glosses":{"en":[{"text":"grief, sorrow","src":"x"}]}},
    {"strong":"G2167","lemma":"εὐφροσύνη","glosses":{"en":[{"text":"joy, gladness","src":"x"}]}},
]

def test_gloss_term_index_maps_term_to_keys():
    idx = gloss_term_index(ENTRIES, lang="en")
    assert idx["love"] == {"G0026"}
    assert idx["joy"] == {"G5479", "G2167"}

def test_mine_relations_bridges_headwords_to_keys():
    idx = gloss_term_index(ENTRIES, lang="en")
    links = [("joy", "gladness", "synonym"), ("joy", "sorrow", "antonym")]
    edges = mine_relations(idx, links, source="roget-1911", method="mined", base_rank=20000)
    syn = [e for e in edges if e.rel == "synonym"]
    ant = [e for e in edges if e.rel == "antonym"]
    # "joy"->{G5479,G2167} ; "gladness"->{G5479,G2167} ; "sorrow"->G3077
    # synonym link yields a real cross-lemma edge {G5479,G2167} (self-loops skipped)
    assert any({e.src, e.dst} == {"G5479", "G2167"} for e in syn)
    assert any({e.src, e.dst} == {"G5479", "G3077"} for e in ant)
    assert all(e.method == "mined" and e.source == "roget-1911" for e in edges)
    assert all(0 <= e.rank <= 65535 for e in edges)
    assert all(e.src != e.dst for e in edges)   # no self-loops


# Fixture for the fanout (polysemy) downweight test.
#   "alpha"/"beta" are each unique to one key      -> fanout = 1×1 = 1 (precise)
#   "bright" maps to {G0010,G0011}; "dark" maps to {G0020,G0021}
#                                                  -> fanout = 2×2 = 4 (vague)
FANOUT_ENTRIES = [
    {"strong": "G0001", "lemma": "α", "glosses": {"en": [{"text": "alpha", "src": "x"}]}},
    {"strong": "G0002", "lemma": "β", "glosses": {"en": [{"text": "beta", "src": "x"}]}},
    {"strong": "G0010", "lemma": "φ", "glosses": {"en": [{"text": "bright", "src": "x"}]}},
    {"strong": "G0011", "lemma": "ψ", "glosses": {"en": [{"text": "bright", "src": "x"}]}},
    {"strong": "G0020", "lemma": "σ", "glosses": {"en": [{"text": "dark", "src": "x"}]}},
    {"strong": "G0021", "lemma": "ω", "glosses": {"en": [{"text": "dark", "src": "x"}]}},
]


def test_fanout_downweight_ranks_vague_matches_lower():
    """A high-fanout (many↔many) link ranks strictly below a precise 1↔1 link."""
    idx = gloss_term_index(FANOUT_ENTRIES, lang="en")
    base = 40000
    links = [
        ("alpha", "beta", "synonym"),   # fanout = 1×1 = 1  (precise)
        ("bright", "dark", "antonym"),  # fanout = 2×2 = 4  (vague)
    ]
    edges = mine_relations(idx, links, source="t", method="mined", base_rank=base)

    precise = [e for e in edges if {e.src, e.dst} == {"G0001", "G0002"}]
    vague = [e for e in edges if e.rel == "antonym"]

    # fanout=1 → no fanout penalty, no word penalty → rank == base_rank.
    assert len(precise) == 1
    assert precise[0].rank == base

    # fanout=4 → penalty = round(SCALE * log2(4)) = 2*SCALE.  Strictly lower.
    expected_vague_rank = base - 2 * FANOUT_PENALTY_SCALE
    assert len(vague) == 4  # full 2×2 cross-product
    assert all(e.rank == expected_vague_rank for e in vague)
    assert all(e.rank < precise[0].rank for e in vague)  # monotone: vague < precise


# Fixture for the dedup test.  G0040 and G0041 are reachable as a pair via two
# different links with different fanout:
#   "happy" -> {G0040}; "merry" -> {G0041}           (a 1×1 link, fanout 1)
#   "glad"  -> {G0040,G0041}; "joyful" -> {G0040,G0041}  (a 2×2 link, fanout 4)
DEDUP_ENTRIES = [
    {"strong": "G0040", "lemma": "α", "glosses": {"en": [{"text": "happy, glad, joyful", "src": "x"}]}},
    {"strong": "G0041", "lemma": "β", "glosses": {"en": [{"text": "merry, glad, joyful", "src": "x"}]}},
]


def test_dedup_same_pair_collapses_to_max_rank():
    """Same (src,dst,rel,source) from two links → ONE edge at the MAX (best) rank."""
    idx = gloss_term_index(DEDUP_ENTRIES, lang="en")
    base = 40000
    links = [
        ("happy", "merry", "synonym"),    # fanout 1×1 = 1 → rank base (40000)
        ("glad", "joyful", "synonym"),    # fanout 2×2 = 4 → rank base - 2*SCALE
    ]
    edges = mine_relations(idx, links, source="t", method="mined", base_rank=base)

    pair_edges = [e for e in edges if {e.src, e.dst} == {"G0040", "G0041"}]
    # Exactly one edge per (src,dst,rel,source) — the redundant lower-rank row collapsed.
    assert len(pair_edges) == 1
    # Surviving rank is the MAX (smallest fanout = strongest evidence), not base-2*SCALE.
    assert pair_edges[0].rank == base
    assert pair_edges[0].rank != base - 2 * FANOUT_PENALTY_SCALE

    # No duplicate (src,dst,rel,source) keys anywhere in the output.
    keys = [(e.src, e.dst, e.rel, e.source) for e in edges]
    assert len(keys) == len(set(keys))
