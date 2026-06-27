# tests/test_domains.py
from tools.build_lexicon import attach_domains


def test_attach_domains_adds_domain_list():
    entry = {
        "strong": "G0026",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "love"}],
        "sources": ["strongs-greek"],
    }
    dmap = {"G0026": ["25.43"]}
    out = attach_domains(entry, dmap)
    assert out["domains"] == ["25.43"]
    assert "ln-map" in out["sources"] or "sdbh" in out["sources"]


def test_attach_domains_source_recorded():
    entry = {
        "strong": "G0026",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "love"}],
        "sources": ["strongs-greek"],
    }
    dmap = {"G0026": ["25.43"]}
    out = attach_domains(entry, dmap)
    # Greek entries use "ln-map"; Hebrew entries use "sdbh"
    assert "ln-map" in out["sources"]


def test_attach_domains_no_entry_stays_empty():
    entry = {
        "strong": "G9999",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "unknown"}],
        "sources": ["strongs-greek"],
    }
    out = attach_domains(entry, {"G0026": ["25.43"]})
    assert out["domains"] == []
    # Source label NOT added when strong is not in the domain map
    assert "ln-map" not in out["sources"]
    assert "sdbh" not in out["sources"]


def test_attach_domains_sorted():
    entry = {
        "strong": "G0025",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "to love"}],
        "sources": ["strongs-greek"],
    }
    dmap = {"G0025": ["25.44", "25.43"]}
    out = attach_domains(entry, dmap)
    assert out["domains"] == ["25.43", "25.44"]


def test_attach_domains_atomizes_compound_codes():
    """A compound 'a b c' domain value is split into atomic codes."""
    entry = {
        "strong": "H0430",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "God"}],
        "sources": ["strongs-hebrew"],
    }
    # MACULA-style compound LexDomain values mixed with atomic ones
    dmap = {"H0430": ["001001001", "001001001 001001001", "004003 001001001"]}
    out = attach_domains(entry, dmap)
    assert out["domains"] == ["001001001", "004003"]
    # no domain contains a space
    assert all(" " not in d for d in out["domains"])
    assert "sdbh" in out["sources"]


def test_attach_domains_atomizes_greek_compound():
    """Greek compound 'ln' values split into atomic LN refs."""
    entry = {
        "strong": "G0025",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "to love"}],
        "sources": ["strongs-greek"],
    }
    dmap = {"G0025": ["25.43 25.44", "25.104"]}
    out = attach_domains(entry, dmap)
    assert out["domains"] == ["25.104", "25.43", "25.44"]
    assert all(" " not in d for d in out["domains"])


def test_attach_domains_idempotent():
    """Calling twice does not duplicate source entries."""
    entry = {
        "strong": "G0026",
        "domains": [],
        "senses": [{"id": 1, "gloss_en": "love"}],
        "sources": ["strongs-greek"],
    }
    dmap = {"G0026": ["25.43"]}
    out = attach_domains(entry, dmap)
    assert out["sources"].count("ln-map") == 1
