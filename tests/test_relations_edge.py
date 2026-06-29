from tools.relations.edge import Edge, canonical_orient, write_jsonl, read_jsonl
from tools.relations.rank import RANK_MAX, clamp_rank


def test_edge_roundtrip(tmp_path):
    e = Edge(src="G0026", dst="G0025", rel="shared-root", directed=False,
             source="strongs-root", method="derived", rank=RANK_MAX, note=None)
    d = e.to_json()
    assert d["provenance"] == {"source": "strongs-root", "method": "derived"}
    assert d["rank"] == 65535
    assert Edge.from_json(d) == e
    p = tmp_path / "e.jsonl"
    write_jsonl(p, [e])
    assert read_jsonl(p) == [e]


def test_canonical_orient_and_clamp():
    assert canonical_orient("G0025", "G0026") == ("G0025", "G0026")
    assert canonical_orient("G0026", "G0025") == ("G0025", "G0026")
    assert clamp_rank(70000) == 65535 and clamp_rank(-5) == 0
