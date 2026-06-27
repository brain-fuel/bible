"""Tests for Task 3: morph-code → (UPOS, FEATS) decoder.

Coverage:
  - Baseline tests from the task brief
  - Greek: nouns, adjectives (with degree), articles, pronouns (personal,
    relative, demonstrative, interrogative), prepositions, conjunctions,
    adverbs, negative particles
  - Greek verbs: finite (present/imperfect/aorist active indicative),
    subjunctive, imperative, infinitive, participle (with CNG suffix),
    second-aorist, future-perfect tense, middle/passive voice
  - Hebrew stub: leading POS letter → UPOS, feats always "_"
  - Edge cases: empty string, placeholder "_", unknown code

FEATS vocabulary settled here and used by downstream tasks (5, 6):
  Keys (all UD-standard):  Case, Degree, Gender, Mood, Number, Person, Tense, Voice
  Values:
    Case:    Acc, Dat, Gen, Nom, Voc
    Degree:  Cmp, Sup
    Gender:  Fem, Masc, Neut
    Mood:    Imp (imperative), Ind, Inf, Opt, Part, Sub
    Number:  Dual, Plur, Sing
    Person:  1, 2, 3
    Tense:   Aor, FutPerf, Fut, Impf, Perf, Plup, Pres
    Voice:   Act, Mid, Pass
"""
from tools.morph_feats import decode


# ---------------------------------------------------------------------------
# Baseline tests (from task-3-brief.md)
# ---------------------------------------------------------------------------

def test_greek_noun_nom_sg_fem():
    upos, feats = decode("N-NSF", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Nom|Gender=Fem|Number=Sing"


def test_greek_preposition():
    assert decode("PREP", "grc") == ("ADP", "_")


def test_unknown_code_is_x():
    assert decode("???", "grc") == ("X", "_")


# ---------------------------------------------------------------------------
# Greek nouns
# ---------------------------------------------------------------------------

def test_greek_noun_gen_pl_masc():
    upos, feats = decode("N-GPM", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Gen|Gender=Masc|Number=Plur"


def test_greek_noun_dat_sg_neut():
    upos, feats = decode("N-DSN", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Dat|Gender=Neut|Number=Sing"


def test_greek_noun_acc_dual_masc():
    upos, feats = decode("N-ADM", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Acc|Gender=Masc|Number=Dual"


def test_greek_noun_voc_sg_fem():
    upos, feats = decode("N-VSF", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Voc|Gender=Fem|Number=Sing"


# Person-name suffix (Extra code P) is ignored at FEATS level; UPOS still NOUN
def test_greek_noun_with_person_name_suffix():
    upos, feats = decode("N-GSM-P", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Gen|Gender=Masc|Number=Sing"


# ---------------------------------------------------------------------------
# Greek adjectives
# ---------------------------------------------------------------------------

def test_greek_adjective_nom_sg_masc():
    upos, feats = decode("A-NSM", "grc")
    assert upos == "ADJ"
    assert feats == "Case=Nom|Gender=Masc|Number=Sing"


def test_greek_adjective_superlative():
    # A-ASM-S = Adjective Accusative Singular Masculine Superlative
    upos, feats = decode("A-ASM-S", "grc")
    assert upos == "ADJ"
    assert feats == "Case=Acc|Degree=Sup|Gender=Masc|Number=Sing"


def test_greek_adjective_comparative():
    upos, feats = decode("A-NSF-C", "grc")
    assert upos == "ADJ"
    assert feats == "Case=Nom|Degree=Cmp|Gender=Fem|Number=Sing"


# ---------------------------------------------------------------------------
# Greek article
# ---------------------------------------------------------------------------

def test_greek_article_acc_sg_masc():
    upos, feats = decode("T-ASM", "grc")
    assert upos == "DET"
    assert feats == "Case=Acc|Gender=Masc|Number=Sing"


def test_greek_article_nom_pl_fem():
    upos, feats = decode("T-NPF", "grc")
    assert upos == "DET"
    assert feats == "Case=Nom|Gender=Fem|Number=Plur"


# ---------------------------------------------------------------------------
# Greek pronouns (personal, relative, demonstrative, interrogative)
# ---------------------------------------------------------------------------

def test_greek_personal_pronoun_gen_sg_fem():
    upos, feats = decode("P-GSF", "grc")
    assert upos == "PRON"
    assert feats == "Case=Gen|Gender=Fem|Number=Sing"


def test_greek_relative_pronoun_nom_sg_masc():
    upos, feats = decode("R-NSM", "grc")
    assert upos == "PRON"
    assert feats == "Case=Nom|Gender=Masc|Number=Sing"


def test_greek_demonstrative_pronoun_acc_pl_neut():
    upos, feats = decode("D-APN", "grc")
    assert upos == "PRON"
    assert feats == "Case=Acc|Gender=Neut|Number=Plur"


def test_greek_interrogative_pronoun_gen_sg_masc():
    upos, feats = decode("I-GSM", "grc")
    assert upos == "PRON"
    assert feats == "Case=Gen|Gender=Masc|Number=Sing"


# ---------------------------------------------------------------------------
# Greek invariant POS (no features)
# ---------------------------------------------------------------------------

def test_greek_conjunction():
    assert decode("CONJ", "grc") == ("CCONJ", "_")


def test_greek_adverb():
    assert decode("ADV", "grc") == ("ADV", "_")


def test_greek_negative_particle():
    assert decode("PRT-N", "grc") == ("PART", "_")


def test_greek_interjection():
    assert decode("INJ", "grc") == ("INTJ", "_")


# ---------------------------------------------------------------------------
# Greek verbs — finite forms
# ---------------------------------------------------------------------------

def test_greek_verb_aorist_active_indicative_3sg():
    # V-AAI-3S (example from docs and brief)
    upos, feats = decode("V-AAI-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=Aor|Voice=Act"


def test_greek_verb_present_active_indicative_3sg():
    upos, feats = decode("V-PAI-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=Pres|Voice=Act"


def test_greek_verb_imperfect_active_indicative_3sg():
    # V-IAI-3S (Imperfect Active Indicative 3rd Singular)
    upos, feats = decode("V-IAI-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=Impf|Voice=Act"


def test_greek_verb_future_active_indicative_1sg():
    upos, feats = decode("V-FAI-1S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=1|Tense=Fut|Voice=Act"


def test_greek_verb_perfect_active_indicative_3pl():
    upos, feats = decode("V-RAI-3P", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Plur|Person=3|Tense=Perf|Voice=Act"


def test_greek_verb_pluperfect_active_indicative_3sg():
    upos, feats = decode("V-LAI-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=Plup|Voice=Act"


def test_greek_verb_second_aorist_active_indicative_3sg():
    # 2A = 2nd Aorist tense; tvm='2AAI' → tense='2A', voice='A', mood='I'
    upos, feats = decode("V-2AAI-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=Aor|Voice=Act"


def test_greek_verb_aorist_active_subjunctive_3sg():
    upos, feats = decode("V-AAS-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Sub|Number=Sing|Person=3|Tense=Aor|Voice=Act"


def test_greek_verb_aorist_active_imperative_2sg():
    upos, feats = decode("V-AAM-2S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Imp|Number=Sing|Person=2|Tense=Aor|Voice=Act"


def test_greek_verb_optative_3sg():
    upos, feats = decode("V-PAO-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Opt|Number=Sing|Person=3|Tense=Pres|Voice=Act"


def test_greek_verb_present_middle_indicative_1pl():
    upos, feats = decode("V-PMI-1P", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Plur|Person=1|Tense=Pres|Voice=Mid"


def test_greek_verb_aorist_passive_indicative_3sg():
    upos, feats = decode("V-API-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=Aor|Voice=Pass"


def test_greek_verb_first_person_plural():
    upos, feats = decode("V-PAI-1P", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Plur|Person=1|Tense=Pres|Voice=Act"


def test_greek_verb_second_person():
    upos, feats = decode("V-PAI-2S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=2|Tense=Pres|Voice=Act"


# ---------------------------------------------------------------------------
# Greek verbs — infinitives
# ---------------------------------------------------------------------------

def test_greek_verb_aorist_active_infinitive():
    # V-AAN: tvm='AAN', no suffix → tense=Aor, voice=Act, mood=Inf
    upos, feats = decode("V-AAN", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Inf|Tense=Aor|Voice=Act"


def test_greek_verb_present_active_infinitive():
    upos, feats = decode("V-PAN", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Inf|Tense=Pres|Voice=Act"


def test_greek_verb_present_middle_infinitive():
    upos, feats = decode("V-PMN", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Inf|Tense=Pres|Voice=Mid"


# ---------------------------------------------------------------------------
# Greek verbs — participles (CNG suffix)
# ---------------------------------------------------------------------------

def test_greek_verb_aorist_active_participle_nom_sg_masc():
    # V-AAP-NSM: tvm='AAP', suffix='NSM'
    upos, feats = decode("V-AAP-NSM", "grc")
    assert upos == "VERB"
    assert feats == "Case=Nom|Gender=Masc|Mood=Part|Number=Sing|Tense=Aor|Voice=Act"


def test_greek_verb_present_active_participle_gen_pl_masc():
    upos, feats = decode("V-PAP-GPM", "grc")
    assert upos == "VERB"
    assert feats == "Case=Gen|Gender=Masc|Mood=Part|Number=Plur|Tense=Pres|Voice=Act"


def test_greek_verb_aorist_passive_participle_nom_sg_fem():
    upos, feats = decode("V-APP-NSF", "grc")
    assert upos == "VERB"
    assert feats == "Case=Nom|Gender=Fem|Mood=Part|Number=Sing|Tense=Aor|Voice=Pass"


def test_greek_verb_present_middle_participle_acc_sg_neut():
    upos, feats = decode("V-PMP-ASN", "grc")
    assert upos == "VERB"
    assert feats == "Case=Acc|Gender=Neut|Mood=Part|Number=Sing|Tense=Pres|Voice=Mid"


# ---------------------------------------------------------------------------
# Greek verb — future perfect (rare; 2-char tense FP)
# ---------------------------------------------------------------------------

def test_greek_verb_future_perfect_active_indicative():
    # V-FPAI-3S: tvm='FPAI' → tense=FP(FutPerf), voice=A(Act), mood=I(Ind)
    upos, feats = decode("V-FPAI-3S", "grc")
    assert upos == "VERB"
    assert feats == "Mood=Ind|Number=Sing|Person=3|Tense=FutPerf|Voice=Act"


# ---------------------------------------------------------------------------
# Hebrew stub
# ---------------------------------------------------------------------------

def test_hebrew_noun_stub_upos():
    # "Ncfsa" = Noun common feminine singular absolute (Task 6 decodes details)
    upos, feats = decode("Ncfsa", "hbo")
    assert upos == "NOUN"
    assert feats == "_"


def test_hebrew_verb_stub_upos():
    # "Vqp3ms" = Verb Qal Perfect 3rd Masculine Singular
    upos, feats = decode("Vqp3ms", "hbo")
    assert upos == "VERB"
    assert feats == "_"


def test_hebrew_adjective_stub():
    upos, feats = decode("Amsa", "hbo")
    assert upos == "ADJ"
    assert feats == "_"


def test_hebrew_preposition_stub():
    upos, feats = decode("Rd", "hbo")
    assert upos == "ADP"
    assert feats == "_"


def test_hebrew_conjunction_stub():
    upos, feats = decode("C", "hbo")
    assert upos == "CCONJ"
    assert feats == "_"


def test_hebrew_adverb_stub():
    upos, feats = decode("D", "hbo")
    assert upos == "ADV"
    assert feats == "_"


def test_hebrew_article_stub():
    upos, feats = decode("Td", "hbo")
    assert upos == "DET"
    assert feats == "_"


def test_hebrew_suffix_stub():
    upos, feats = decode("Sp3ms", "hbo")
    assert upos == "PRON"
    assert feats == "_"


def test_hebrew_with_language_prefix_H():
    # Raw TAHOT value includes H prefix; decoder must handle it
    upos, feats = decode("HVqp3ms", "hbo")
    assert upos == "VERB"
    assert feats == "_"


def test_hebrew_with_language_prefix_A():
    # Aramaic prefix A
    upos, feats = decode("ANcmsa", "hbo")
    assert upos == "NOUN"
    assert feats == "_"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_string_is_x():
    assert decode("", "grc") == ("X", "_")


def test_placeholder_underscore_is_x():
    assert decode("_", "grc") == ("X", "_")


def test_unknown_code_hbo():
    assert decode("???", "hbo") == ("X", "_")


def test_empty_string_hbo():
    assert decode("", "hbo") == ("X", "_")
