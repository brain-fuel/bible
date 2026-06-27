"""Tests for Task 1: STEPBible TAGNT/TAHOT normalizers.

Fixtures use the REAL semi-structured block format (# summary lines + repeated
column-header line + data rows), NOT a flat single-header TSV.  This exercises
the actual parser logic.
"""
import unicodedata
from pathlib import Path

import pytest

from tools.morph_norm.stepbible_greek import normalize_greek, pad_strong
from tools.morph_norm.stepbible_hebrew import normalize_hebrew


# ---------------------------------------------------------------------------
# pad_strong
# ---------------------------------------------------------------------------

def test_pad_strong_zero_pads_to_four_digits():
    assert pad_strong("G", "26") == "G0026"
    assert pad_strong("H", "430") == "H0430"
    assert pad_strong("G", "3056") == "G3056"
    assert pad_strong("G", "1") == "G0001"


# ---------------------------------------------------------------------------
# Greek normalizer — block-format fixture
# ---------------------------------------------------------------------------

GREEK_BLOCK = """\
# Mat.1.1\tBiblos\t...\t...
#_Translation\t[The] book\tof [the] genealogy\tof Jesus
#_Word=Grammar\tG0976=N-NSF\tG1078=N-GSF\tG2424G=N-GSM-P

Word & Type\tGreek\tEnglish translation\tdStrongs = Grammar\tDictionary form =  Gloss\teditions\tMeaning variants\tSpelling variants\tSpanish translation\tSub-meaning\tConjoin word\tsStrong+Instance\tAlt Strongs
Mat.1.1#01=NKO\tΒίβλος (Biblos)\t[The] book\tG0976=N-NSF\tβίβλος=book\tNA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t\t\tLibro\tbook\t#01\tG0976\t
Mat.1.1#02=NKO\tγενέσεως (geneseos)\tof [the] genealogy\tG1078=N-GSF\tγένεσις=origin\tNA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t\t\tde origen\torigin\t#02\tG1078\t
Mat.1.1#03=NKO\tΙησοῦ (Iesou)\tof Jesus\tG2424G=N-GSM-P\tΙησοῦς=Jesus/Joshua\tNA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t\t\tde Jesus\tJesus\t#03\tG2424\t
"""


def test_normalize_greek_block_row(tmp_path):
    """Parser must skip # lines and the repeated Word-&-Type header, then
    correctly parse the data rows in the verse block."""
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(GREEK_BLOCK, encoding="utf-8")
    rows = normalize_greek(raw)

    assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}: {rows}"

    r = rows[0]
    assert r["ref"] == "MAT.1.1"
    assert r["idx"] == 1
    assert r["surface"] == "Βίβλος"
    assert r["lemma"] == "βίβλος"
    assert r["strong"] == "G0976"
    assert r["xpos"] == "N-NSF"
    assert r["edition"] == "TR"
    assert r["feats"] == "_"


def test_normalize_greek_transliteration_extracted(tmp_path):
    """Transliteration is pulled from the parenthesised part of the Greek col."""
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(GREEK_BLOCK, encoding="utf-8")
    rows = normalize_greek(raw)
    assert rows[0]["translit"] == "Biblos"


def test_normalize_greek_disambiguation_suffix_strip(tmp_path):
    """G2424G (row 3) must produce strong == G2424 (trailing G stripped)."""
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(GREEK_BLOCK, encoding="utf-8")
    rows = normalize_greek(raw)
    r = rows[2]
    assert r["strong"] == "G2424", f"Expected G2424, got {r['strong']}"
    assert r["idx"] == 3


def test_normalize_greek_hash_and_header_lines_skipped(tmp_path):
    """# lines and the Word-&-Type column-header line must not produce rows."""
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(GREEK_BLOCK, encoding="utf-8")
    rows = normalize_greek(raw)
    # All returned refs must be real verse refs, not junk from skipped lines.
    for r in rows:
        assert r["ref"].startswith("MAT.")
        assert isinstance(r["idx"], int)


def test_normalize_greek_filters_non_TR_rows(tmp_path):
    """Rows whose editions column does not contain TR must be excluded."""
    block = (
        "Word & Type\tGreek\tEnglish translation\tdStrongs = Grammar\t"
        "Dictionary form =  Gloss\teditions\tMeaning variants\tSpelling variants\t"
        "Spanish translation\tSub-meaning\tConjoin word\tsStrong+Instance\tAlt Strongs\n"
        "Jhn.1.1#01=N\tἐν (en)\tin\tG1722=PREP\tἐν=in\t"
        "NA28+NA27+Tyn+SBL+WH+Treg+Byz\t\t\ten\tin\t#01\tG1722\t\n"
        "Jhn.1.1#02=NKO\tἀρχῇ (arche)\tbeginning\tG0746=N-DSF\t"
        "ἀρχή=beginning\tNA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t"
        "\t\ten\tbeginning\t#02\tG0746\t\n"
    )
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(block, encoding="utf-8")
    rows = normalize_greek(raw)
    assert len(rows) == 1, f"Expected 1 TR row, got {len(rows)}"
    assert rows[0]["idx"] == 2
    assert rows[0]["strong"] == "G0746"


def test_normalize_greek_hebrew_pipe_strong(tmp_path):
    """H####|G#### compound strongs -> take the G portion, strip suffix."""
    block = (
        "Word & Type\tGreek\tEnglish translation\tdStrongs = Grammar\t"
        "Dictionary form =  Gloss\teditions\tMeaning variants\tSpelling variants\t"
        "Spanish translation\tSub-meaning\tConjoin word\tsStrong+Instance\tAlt Strongs\n"
        "Mat.1.1#06=NKO\tΔαυίδ (Dauid)\tof David\t"
        "H1732|G1138=N-GSM-P\tΔαυίδ=David\t"
        "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t\t\tDavid\tDavid\t#06\tG1138\t\n"
    )
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(block, encoding="utf-8")
    rows = normalize_greek(raw)
    assert len(rows) == 1
    assert rows[0]["strong"] == "G1138"


# ---------------------------------------------------------------------------
# Hebrew normalizer — block-format fixture
# ---------------------------------------------------------------------------

HEBREW_BLOCK = """\
# Gen.1.1\tbe.re.Shit\tba.Ra'\t'E.lo.Him
#_Translation\tin/ beginning\the created\tGod
#_Word+Grammar\tH9003/H7225G=HR/Ncfsa\tH1254A=HVqp3ms\tH0430G=HNcmpa

Eng (Heb) Ref & Type\tHebrew\tTransliteration\tTranslation\tdStrongs\tGrammar\tMeaning Variants\tSpelling Variants\tRoot dStrong+Instance\tAlternative Strongs+Instance\tConjoin word\tExpanded Strong tags
Gen.1.1#01=L\tבְּ/רֵאשִׁית\tbe./re.Shit\tin/ beginning\tH9003/{H7225G}\tHR/Ncfsa\t\t\tH7225G\t\t\tH9003=ב=in/{H7225G=רֵאשִׁית=: beginning}
Gen.1.1#02=L\tבָּרָאָ\tba.Ra'\the created\t{H1254A}\tHVqp3ms\t\t\tH1254A\t\t\t{H1254A=בָּרָא=to create}
Gen.1.1#03=L\tאֱלֹהִים\t'E.lo.Him\tGod\t{H0430G}\tHNcmpa\t\t\tH0430G\t\t\t{H0430G=אֱלֹהִים=God}
"""


def test_normalize_hebrew_block_row(tmp_path):
    """Parser must skip # lines and Eng-(Heb)-Ref header, then parse data rows."""
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(HEBREW_BLOCK, encoding="utf-8")
    rows = normalize_hebrew(raw)

    assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}: {rows}"

    r = rows[0]
    assert r["ref"] == "GEN.1.1"
    assert r["idx"] == 1
    assert r["strong"] == "H7225"
    assert r["xpos"] == "HR/Ncfsa"
    assert r["edition"] == "WLC"
    assert r["feats"] == "_"
    assert r["translit"] == "be./re.Shit"


def test_normalize_hebrew_disambiguation_suffix_stripped(tmp_path):
    """H7225G -> H7225; H1254A -> H1254; H0430G -> H0430."""
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(HEBREW_BLOCK, encoding="utf-8")
    rows = normalize_hebrew(raw)
    assert rows[0]["strong"] == "H7225"   # H7225G stripped
    assert rows[1]["strong"] == "H1254"   # H1254A stripped
    assert rows[2]["strong"] == "H0430"   # H0430G stripped


def test_normalize_hebrew_instance_marker_stripped(tmp_path):
    """H0853_A -> H0853 (instance marker _A removed before disambiguation strip)."""
    block = (
        "Eng (Heb) Ref & Type\tHebrew\tTransliteration\tTranslation\t"
        "dStrongs\tGrammar\tMeaning Variants\tSpelling Variants\t"
        "Root dStrong+Instance\tAlternative Strongs+Instance\tConjoin word\tExpanded Strong tags\n"
        "Gen.1.1#04=L\tאֵת\t'et\t<obj.>\t{H0853}\tHTo\t\t\t"
        "H0853_A\t\t\t{H0853=אֵת=[Obj.]}\n"
    )
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(block, encoding="utf-8")
    rows = normalize_hebrew(raw)
    assert len(rows) == 1
    assert rows[0]["strong"] == "H0853"


def test_normalize_hebrew_book_divergences(tmp_path):
    """Sng->SOS, Ezk->EZE, Jol->JOE, Nam->NAH are correctly mapped."""
    block = (
        "Eng (Heb) Ref & Type\tHebrew\tTransliteration\tTranslation\t"
        "dStrongs\tGrammar\tMeaning Variants\tSpelling Variants\t"
        "Root dStrong+Instance\tAlternative Strongs+Instance\tConjoin word\tExpanded Strong tags\n"
        "Sng.1.1#01=L\tשִׁיר\t'shi.r\tsong\t{H7892A}\tHNcmsa\t\t\tH7892A\t\t\t\n"
        "Ezk.1.1#01=L\tוַיְהִי\tva.ye.hi\tand it was\t{H1961}\tHVqw3ms\t\t\tH1961\t\t\t\n"
        "Jol.1.1#01=L\tדְבַר\tdvar\tword\t{H1697G}\tHNcmsc\t\t\tH1697G\t\t\t\n"
        "Nam.1.1#01=L\tמַשָּא\tmassa\tburden\t{H4853A}\tHNcmsa\t\t\tH4853A\t\t\t\n"
    )
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(block, encoding="utf-8")
    rows = normalize_hebrew(raw)
    refs = [r["ref"] for r in rows]
    assert "SOS.1.1" in refs
    assert "EZE.1.1" in refs
    assert "JOE.1.1" in refs
    assert "NAH.1.1" in refs


def test_normalize_hebrew_hash_and_header_lines_skipped(tmp_path):
    """# lines and Eng-(Heb)-Ref header line must not produce rows."""
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(HEBREW_BLOCK, encoding="utf-8")
    rows = normalize_hebrew(raw)
    for r in rows:
        assert r["ref"].startswith("GEN.")
        assert isinstance(r["idx"], int)


def test_normalize_hebrew_comma_strong_qk_row(tmp_path):
    """A Q(K) row with comma-joined col 8 (Qere,Ketiv) takes the Qere token.

    Real example: Gen.30.11#03=Q(K) has col 8 "H0935G, H1409" -> H0935.
    """
    block = (
        "Eng (Heb) Ref & Type\tHebrew\tTransliteration\tTranslation\t"
        "dStrongs\tGrammar\tMeaning Variants\tSpelling Variants\t"
        "Root dStrong+Instance\tAlternative Strongs+Instance\tConjoin word\tExpanded Strong tags\n"
        "Gen.30.11#03=Q(K)\tבָּא\tba\tcame\t{H0935G}\tHVqp3ms\t\t\t"
        "H0935G, H1409\t\t\t\n"
    )
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(block, encoding="utf-8")
    rows = normalize_hebrew(raw)
    assert len(rows) == 1
    assert rows[0]["strong"] == "H0935"


def test_normalize_hebrew_empty_col8(tmp_path):
    """A row with a blank col 8 yields an empty-string strong (absent)."""
    block = (
        "Eng (Heb) Ref & Type\tHebrew\tTransliteration\tTranslation\t"
        "dStrongs\tGrammar\tMeaning Variants\tSpelling Variants\t"
        "Root dStrong+Instance\tAlternative Strongs+Instance\tConjoin word\tExpanded Strong tags\n"
        "Gen.30.11#04=Q(K)\tשֵׁם\tshem\tname\t{H8034}\tHNcmsa\t\t\t"
        "\t\t\t\n"
    )
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(block, encoding="utf-8")
    rows = normalize_hebrew(raw)
    assert len(rows) == 1
    assert rows[0]["strong"] == ""


def test_normalize_greek_surface_is_nfc(tmp_path):
    """surface and lemma must be NFC-normalised."""
    raw = tmp_path / "tagnt_test.txt"
    raw.write_text(GREEK_BLOCK, encoding="utf-8")
    rows = normalize_greek(raw)
    for r in rows:
        assert r["surface"] == unicodedata.normalize("NFC", r["surface"])
        assert r["lemma"] == unicodedata.normalize("NFC", r["lemma"])


def test_normalize_hebrew_surface_is_nfc(tmp_path):
    """surface must be NFC-normalised."""
    raw = tmp_path / "tahot_test.txt"
    raw.write_text(HEBREW_BLOCK, encoding="utf-8")
    rows = normalize_hebrew(raw)
    for r in rows:
        assert r["surface"] == unicodedata.normalize("NFC", r["surface"])
