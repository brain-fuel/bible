# tests/test_gloss_bridge.py
from tools.relations.gloss_bridge import gloss_term_index, mine_relations

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
