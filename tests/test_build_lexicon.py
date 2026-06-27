# tests/test_build_lexicon.py
from tools.build_lexicon import build_entry

FAKE = {
    "strongs-greek": {"G0026": {"lemma": "ἀγάπη", "translit": "agapē", "gloss": "love, affection", "root": "G0025"}},
    "abbott-smith":  {"G0026": {"gloss": "love"}},
}


def test_build_entry_has_schema_fields():
    e = build_entry("G0026", "grc", FAKE)
    assert e["strong"] == "G0026"
    assert e["lemma"] == "ἀγάπη"
    assert e["glosses"]["en"][0]["text"]
    assert e["glosses"]["en"][0]["src"]
    assert e["root"] == "G0025"
    assert "strongs-greek" in e["sources"]


def test_glosses_is_lang_keyed_map():
    e = build_entry("G0026", "grc", FAKE)
    assert isinstance(e["glosses"], dict)
    assert "en" in e["glosses"]


def test_schema_all_keys_present():
    e = build_entry("G0026", "grc", FAKE)
    for key in ("strong", "lemma", "translit", "lang", "pos", "glosses", "senses", "domains", "root", "sources"):
        assert key in e, f"missing key: {key}"


def test_senses_seeded():
    e = build_entry("G0026", "grc", FAKE)
    assert isinstance(e["senses"], list)
    assert len(e["senses"]) >= 1
    assert e["senses"][0]["id"] == 1
    assert e["senses"][0]["domain"] is None


def test_domains_empty_list():
    e = build_entry("G0026", "grc", FAKE)
    assert e["domains"] == []


def test_multiple_gloss_sources():
    e = build_entry("G0026", "grc", FAKE)
    srcs = {g["src"] for g in e["glosses"]["en"]}
    assert "strongs-greek" in srcs
    assert "abbott-smith" in srcs


def test_missing_strong_returns_empty_lemma():
    e = build_entry("G9999", "grc", FAKE)
    assert e["strong"] == "G9999"
    assert e["lemma"] == ""
    assert e["glosses"]["en"] == []


def test_hebrew_entry():
    fake_hbo = {
        "strongs-hebrew": {"H1254": {"lemma": "בָּרָא", "translit": "bârâʼ", "gloss": "to create", "root": None}},
    }
    e = build_entry("H1254", "hbo", fake_hbo)
    assert e["strong"] == "H1254"
    assert e["lang"] == "hbo"
    assert e["lemma"] == "בָּרָא"
    assert e["glosses"]["en"][0]["text"] == "to create"
    assert e["root"] is None
