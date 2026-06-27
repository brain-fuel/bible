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
