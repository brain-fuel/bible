# tests/test_build_cross_language.py
from tools.relations.build_cross_language import cross_language_edges
from tools.relations.rank import bridge_rank, DEFAULT_RANK_THRESHOLD

def test_bridge_rank_monotone_and_noise_floor():
    strong = {"cooccur": 50, "exact": 45}
    noise  = {"cooccur": 1, "exact": 0}
    assert bridge_rank(strong) > bridge_rank(noise)
    assert bridge_rank(noise) < DEFAULT_RANK_THRESHOLD   # cooccur=1 is below default view
    assert 0 <= bridge_rank(noise) <= 65535

def test_bridge_rank_ubiquity_downweight():
    # Linear ubiquity downweight: same signal row; a Greek lemma translating many
    # distinct Hebrew lemmas (high fan/ubiquity) is a weaker, more generic signal
    # and must rank strictly lower.  ubiquity=1 -> no penalty.
    row = {"cooccur": 20, "exact": 18}
    distinctive = bridge_rank(row, ubiquity=1)        # no penalty
    ubiquitous  = bridge_rank(row, ubiquity=4096)     # heavy fan -> downweighted
    assert ubiquitous < distinctive
    # The distinctive (low-fan) row stays above the default-view threshold while
    # the ubiquitous (high-fan) one is pushed below it.
    assert distinctive >= DEFAULT_RANK_THRESHOLD
    assert ubiquitous < DEFAULT_RANK_THRESHOLD
    assert 0 <= ubiquitous <= 65535


def test_cross_language_edge_shape():
    rows = [{"mt_strong":"H7225","lxx_strong":"G0746","lxx_lemma":"ἀρχή","cooccur":16,"exact":12,"positional":4}]
    edges = cross_language_edges(rows)
    e = edges[0]
    assert e.src == "H7225" and e.dst == "G0746" and e.rel == "cross-language"
    assert e.source == "mt-lxx-bridge" and e.method == "projection"
    assert 0 <= e.rank <= 65535
