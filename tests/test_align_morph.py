# tests/test_align_morph.py
from tools.align_morph import normalize_surface, align_verse


def test_normalize_surface_strips_accents():
    assert normalize_surface("ἐν") == normalize_surface("εν")


def test_align_verse_form_comes_from_l0():
    l0 = "ἐν ἀρχῇ"
    norm = [
        {"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"},
        {"idx": 2, "surface": "ἀρχῇ", "lemma": "ἀρχή", "strong": "G0746", "xpos": "N-DSF", "translit": "archē", "edition": "TR"},
    ]
    toks = align_verse("JOH.1.1", l0, norm, "grc")
    assert [t.form for t in toks] == ["ἐν", "ἀρχῇ"]
    assert toks[1].lemma == "ἀρχή"
    assert "Strong=G0746" in toks[1].misc
    assert toks[1].upos == "NOUN"


def test_align_verse_unmatched_l0_word_marked():
    l0 = "ἐν δέ"  # δέ absent from source rows
    norm = [{"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"}]
    toks = align_verse("X.1.1", l0, norm, "grc")
    assert "Align=unmatched" in toks[1].misc
