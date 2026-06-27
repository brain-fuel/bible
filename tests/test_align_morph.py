# tests/test_align_morph.py
import unicodedata

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


# ---------------------------------------------------------------------------
# Hebrew headword substitution in align_verse
# ---------------------------------------------------------------------------

def test_align_verse_hebrew_uses_headword_lemma():
    """For hbo + headwords, matched tokens must take LEMMA from headwords map."""
    # Simulate GEN.1.3 word 1: surface=וַיֹּ֥אמֶר strong=H0559
    surface = "וַיֹּ֥אמֶר"
    surface_no_cantil = "ויאמר"  # normalized by align; we feed surface direct
    headwords = {"H0559": "אָמַר"}  # clean Strong's headword
    l0 = surface
    norm = [
        {
            "idx": 1,
            "surface": surface,
            "lemma": "וַ/יֹּ֥אמֶר",   # old TAHOT surface-as-lemma (has slash + cantillation)
            "strong": "H0559",
            "xpos": "Hc/Vqw3ms",
            "translit": "va/i.Yo.mer",
            "edition": "WLC",
        }
    ]
    toks = align_verse("GEN.1.3", l0, norm, "hbo", headwords=headwords)
    assert len(toks) == 1
    assert toks[0].lemma == "אָמַר"           # headword, not surface
    assert "/" not in toks[0].lemma          # no morpheme-boundary slash
    assert "Strong=H0559" in toks[0].misc


def test_align_verse_hebrew_fallback_when_strong_absent():
    """Unmatched Hebrew tokens (no strong) keep lemma='_' (not the headword map)."""
    headwords = {"H0430": "אֱלֹהִים"}
    l0 = "אֱלֹהִ֑ים XYZZY"
    norm = [
        {
            "idx": 1,
            "surface": "אֱלֹהִ֑ים",
            "lemma": "אֱלֹהִ֑ים",
            "strong": "H0430",
            "xpos": "HNcmpa",
            "translit": "'E.lo.Him",
            "edition": "WLC",
        }
    ]
    toks = align_verse("GEN.1.1", l0, norm, "hbo", headwords=headwords)
    assert len(toks) == 2
    assert toks[0].lemma == "אֱלֹהִים"        # matched: from headwords
    assert toks[1].lemma == "_"               # unmatched: placeholder
    assert "Align=unmatched" in toks[1].misc


def test_align_verse_hebrew_fallback_when_strong_not_in_map():
    """If a matched token's strong is absent from headwords, lemma falls back to '_'.

    This covers Tyndale 9xxx grammatical-particle codes (e.g. H9033) which are
    not present in strongs-hebrew.xml.  The TAHOT surface-form (which contains
    morpheme-boundary slashes) must never be used as the LEMMA.
    """
    headwords = {}  # empty map simulates H9xxx not-found situation
    l0 = "בָּרָ֣א"
    norm = [
        {
            "idx": 1,
            "surface": "בָּרָ֣א",
            "lemma": "בָּרָ֣א",    # TAHOT surface (would contain slash in real data)
            "strong": "H9033",   # Tyndale particle code: not in real strongs.xml
            "xpos": "HRd/Sp3ms",
            "translit": "v/o",
            "edition": "WLC",
        }
    ]
    toks = align_verse("GEN.1.11", l0, norm, "hbo", headwords=headwords)
    assert toks[0].lemma == "_"   # fallback to underscore, not TAHOT surface


def test_align_verse_greek_unaffected_by_headwords_arg():
    """Passing headwords to a Greek verse must not change LEMMA (Greek path unchanged)."""
    headwords = {"G0746": "SHOULD_NOT_BE_USED"}
    l0 = "ἐν ἀρχῇ"
    norm = [
        {"idx": 1, "surface": "ἐν", "lemma": "ἐν", "strong": "G1722", "xpos": "PREP", "translit": "en", "edition": "TR"},
        {"idx": 2, "surface": "ἀρχῇ", "lemma": "ἀρχή", "strong": "G0746", "xpos": "N-DSF", "translit": "archē", "edition": "TR"},
    ]
    toks = align_verse("JOH.1.1", l0, norm, "grc", headwords=headwords)
    assert toks[1].lemma == "ἀρχή"   # TAGNT form, not the headwords entry


# ---------------------------------------------------------------------------
# load_hebrew_headwords helper
# ---------------------------------------------------------------------------

def test_load_hebrew_headwords_parses_real_xml(tmp_path):
    """load_hebrew_headwords extracts NFC headwords from a minimal OSIS snippet."""
    xml = tmp_path / "strongs-hebrew.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">'
        '<osisText><div type="entry" n="430">'
        '<w lemma="אֱלֹהִים" xlit="elohim"/>'
        '</div></osisText></osis>',
        encoding="utf-8",
    )
    from tools.strongs_headwords import load_hebrew_headwords
    hw = load_hebrew_headwords(xml)
    assert "H0430" in hw
    lemma = hw["H0430"]
    assert unicodedata.is_normalized("NFC", lemma)
    assert "elohim" not in lemma   # Hebrew script, not transliteration


def test_load_hebrew_headwords_skips_empty_lemma(tmp_path):
    """Entries with empty lemma attribute are silently omitted."""
    xml = tmp_path / "strongs-hebrew.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">'
        '<osisText>'
        '<div type="entry" n="1"><w lemma=""/></div>'
        '<div type="entry" n="2"><w lemma="בָּרָא"/></div>'
        '</osisText></osis>',
        encoding="utf-8",
    )
    from tools.strongs_headwords import load_hebrew_headwords
    hw = load_hebrew_headwords(xml)
    assert "H0001" not in hw      # empty lemma omitted
    assert "H0002" in hw          # non-empty included
