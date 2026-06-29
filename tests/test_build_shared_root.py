from tools.relations.build_shared_root import shared_root_edges

def test_shared_root_pairs_within_group():
    # three lemmas share root G0025 -> 3 undirected pairs (3 choose 2)
    entries = [
        {"strong": "G0026", "lemma": "ἀγάπη", "root": "G0025"},
        {"strong": "G0025", "lemma": "ἀγαπάω", "root": "G0025"},
        {"strong": "G0027", "lemma": "ἀγαπητός", "root": "G0025"},
        {"strong": "G1234", "lemma": "x", "root": None},   # no root -> no edge
    ]
    edges = shared_root_edges(entries)
    pairs = {(e.src, e.dst) for e in edges}
    assert pairs == {("G0025","G0026"), ("G0025","G0027"), ("G0026","G0027")}
    assert all(e.rel == "shared-root" and e.rank == 65535 and not e.directed for e in edges)
    assert all(e.src != e.dst for e in edges)
