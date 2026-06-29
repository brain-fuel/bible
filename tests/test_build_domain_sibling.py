from tools.relations.build_domain_sibling import domain_sibling_edges
from tools.relations.rank import DEFAULT_RANK_THRESHOLD, specificity_rank

def test_specificity_rank_monotone():
    assert specificity_rank("25.43") > specificity_rank("25")

def test_specificity_rank_sdbh_monotone():
    assert specificity_rank("004") < DEFAULT_RANK_THRESHOLD
    assert specificity_rank("004003") > DEFAULT_RANK_THRESHOLD
    assert specificity_rank("004003002") > specificity_rank("004003")
    assert specificity_rank("002001002010") > specificity_rank("004003002")

def test_specificity_rank_no_clamp_collision():
    ranks = [specificity_rank("0" * (3 * d)) for d in range(1, 6)]
    assert ranks == sorted(ranks) and len(set(ranks)) == 5

def test_domain_sibling_pairs_per_code():
    entries = [
        {"strong": "G0026", "lemma": "ἀγάπη", "lang": "grc", "domains": ["25.43"]},
        {"strong": "G0025", "lemma": "ἀγαπάω", "lang": "grc", "domains": ["25.43"]},
        {"strong": "G5368", "lemma": "φιλέω", "lang": "grc", "domains": ["25.33"]},  # different subdomain
    ]
    edges = domain_sibling_edges(entries)
    pairs = {(e.src, e.dst, e.rel) for e in edges}
    assert ("G0025", "G0026", "domain-sibling") in pairs
    assert all(e.source == "louw-nida" for e in edges)
    assert all(e.rank == specificity_rank("25.43") for e in edges)
