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


def test_normalize_surface_strips_pilcrow():
    # STEPBible appends .¶ on paragraph-final words; ¶ must not block matching.
    assert normalize_surface("ἀληθείᾳ.¶") == normalize_surface("ἀληθείᾳ")


def test_align_verse_resync_after_extra_source_row():
    # Source carries an extra row (ποτε) the L0 verse lacks; the matcher must
    # skip it and still align the following L0 word to its real source row.
    l0 = "ἐν ἀρχῇ"
    norm = [
        {"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"},
        {"idx": 2, "surface": "ποτε", "lemma": "ποτέ", "strong": "G4218", "xpos": "PRT", "translit": "pote", "edition": "TR"},
        {"idx": 3, "surface": "ἀρχῇ", "lemma": "ἀρχή", "strong": "G0746", "xpos": "N-DSF", "translit": "archē", "edition": "TR"},
    ]
    toks = align_verse("X.1.1", l0, norm, "grc")
    assert [t.form for t in toks] == ["ἐν", "ἀρχῇ"]
    # Second word resynced to its real source row, not marked unmatched.
    assert toks[1].lemma == "ἀρχή"
    assert "Strong=G0746" in toks[1].misc
    assert "unmatched" not in toks[1].misc
    # The skipped source row is accounted for as source_extra.
    assert "source_extra:1" in toks[1].misc


def test_align_verse_genuine_divergence_no_cascade():
    # δέ is truly absent from the source; it must stay unmatched WITHOUT
    # desyncing the following word, which still matches its source row.
    l0 = "ἐν δέ ἀρχῇ"
    norm = [
        {"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"},
        {"idx": 2, "surface": "ἀρχῇ", "lemma": "ἀρχή", "strong": "G0746", "xpos": "N-DSF", "translit": "archē", "edition": "TR"},
    ]
    toks = align_verse("X.1.1", l0, norm, "grc")
    assert "Align=unmatched" in toks[1].misc          # δέ stays unmatched
    assert toks[2].lemma == "ἀρχή"                     # ἀρχῇ NOT cascaded
    assert "Strong=G0746" in toks[2].misc
    assert "unmatched" not in toks[2].misc


def test_align_verse_source_extra_on_last_token():
    # A trailing source row beyond all L0 words is recorded as source_extra.
    l0 = "ἐν"
    norm = [
        {"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"},
        {"idx": 2, "surface": "ἀρχῇ", "lemma": "ἀρχή", "strong": "G0746", "xpos": "N-DSF", "translit": "archē", "edition": "TR"},
    ]
    toks = align_verse("X.1.1", l0, norm, "grc")
    assert "Align=source_extra:1" in toks[0].misc


def test_align_verse_single_align_key_when_both():
    # When the last token is both unmatched and gains source_extra, MISC must
    # carry ONE Align= key with comma-joined values, not two Align= fields.
    l0 = "ἐν δέ"
    norm = [
        {"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"},
        {"idx": 2, "surface": "καί", "lemma": "καί", "strong": "G2532", "xpos": "CONJ", "translit": "kai", "edition": "TR"},
        {"idx": 3, "surface": "λόγος", "lemma": "λόγος", "strong": "G3056", "xpos": "N-NSM", "translit": "logos", "edition": "TR"},
    ]
    toks = align_verse("X.1.1", l0, norm, "grc")
    misc = toks[1].misc
    assert misc.count("Align=") == 1
    assert "unmatched" in misc and "source_extra:2" in misc
