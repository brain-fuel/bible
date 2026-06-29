# tests/test_build_cross_language.py
from tools.relations.build_cross_language import cross_language_edges
from tools.relations.rank import bridge_rank, DEFAULT_RANK_THRESHOLD

def test_bridge_rank_monotone_and_noise_floor():
    strong = {"cooccur": 50, "exact": 45}
    noise  = {"cooccur": 1, "exact": 0}
    assert bridge_rank(strong) > bridge_rank(noise)
    assert bridge_rank(noise) < DEFAULT_RANK_THRESHOLD   # cooccur=1 is below default view
    assert 0 <= bridge_rank(noise) <= 65535

def test_cross_language_edge_shape():
    rows = [{"mt_strong":"H7225","lxx_strong":"G0746","lxx_lemma":"ἀρχή","cooccur":16,"exact":12,"positional":4}]
    edges = cross_language_edges(rows)
    e = edges[0]
    assert e.src == "H7225" and e.dst == "G0746" and e.rel == "cross-language"
    assert e.source == "mt-lxx-bridge" and e.method == "projection"
    assert 0 <= e.rank <= 65535
