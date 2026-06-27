"""Task 6: Full Hebrew / Aramaic decode tests.

These tests assert REAL feature values (not the stub "_").
They fail until _decode_hebrew is fully implemented with the TAHOT scheme.

FEATS vocabulary chosen for Hebrew (documented in morph_feats.py):
  Aspect      -- Abs (infinitive absolute), Cons (consecutive/sequential)
  Gender      -- Com, Fem, Masc
  HebBinyan   -- Qal Nif Piel Pual Hif Hof Htpa Htpaal Nithpa Tif
                  Aph Shaph Peil Ithpeel Hitpeel Ishtaph  (verb stem)
  Mood        -- Coh (cohortative), Imp (imperative), Jus (jussive)
  Number      -- Dual, Plur, Sing
  Person      -- 1, 2, 3
  State       -- Abs, Cns, Def
  Tense       -- Fut, Past
  VerbForm    -- Fin, Inf, Part
  Voice       -- Act, Pass
"""

from tools.morph_feats import decode


# ---------------------------------------------------------------------------
# Required minimal tests from task-6-brief.md
# ---------------------------------------------------------------------------

def test_hebrew_noun_upos():
    """decode("Ncfsa","hbo")[0] == "NOUN"  (task brief requirement)."""
    upos, _ = decode("Ncfsa", "hbo")
    assert upos == "NOUN"


def test_hebrew_verb_upos():
    """decode("Vqp3ms","hbo")[0] == "VERB"  (task brief requirement)."""
    upos, _ = decode("Vqp3ms", "hbo")
    assert upos == "VERB"


# ---------------------------------------------------------------------------
# Noun / Proper noun full FEATS
# ---------------------------------------------------------------------------

def test_noun_common_fem_sing_abs_feats():
    """Noun common feminine singular absolute (bare form, no H prefix)."""
    upos, feats = decode("Ncfsa", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Fem|Number=Sing|State=Abs"


def test_noun_common_masc_plur_abs_with_H():
    """Noun common masculine plural absolute (real TAHOT form with H prefix)."""
    upos, feats = decode("HNcmpa", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Masc|Number=Plur|State=Abs"


def test_noun_common_masc_sing_construct():
    """Noun common masculine singular construct."""
    upos, feats = decode("HNcmsc", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Masc|Number=Sing|State=Cns"


def test_proper_noun_masculine():
    """Proper noun masculine (PROPN)."""
    upos, feats = decode("HNpm", "hbo")
    assert upos == "PROPN"
    assert "Gender=Masc" in feats


def test_proper_noun_feminine():
    """Proper noun feminine (PROPN)."""
    upos, feats = decode("HNpf", "hbo")
    assert upos == "PROPN"
    assert "Gender=Fem" in feats


def test_proper_noun_location():
    """Proper noun location — no gender feat."""
    upos, feats = decode("HNpl", "hbo")
    assert upos == "PROPN"


# ---------------------------------------------------------------------------
# Verb full FEATS
# ---------------------------------------------------------------------------

def test_verb_qal_perfect_3ms_full():
    """Qal Perfect 3ms — full sorted feats string."""
    upos, feats = decode("Vqp3ms", "hbo")
    assert upos == "VERB"
    assert feats == "Gender=Masc|HebBinyan=Qal|Number=Sing|Person=3|Tense=Past|VerbForm=Fin"


def test_verb_qal_perfect_with_H():
    """Same with H prefix (real TAHOT form HVqp3ms)."""
    upos, feats = decode("HVqp3ms", "hbo")
    assert upos == "VERB"
    assert feats == "Gender=Masc|HebBinyan=Qal|Number=Sing|Person=3|Tense=Past|VerbForm=Fin"


def test_verb_niphal_imperfect_3ms():
    """Niphal Imperfect 3ms — tense=Fut, binyan=Nif."""
    upos, feats = decode("HVNi3ms", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Nif" in feats
    assert "Tense=Fut" in feats
    assert "VerbForm=Fin" in feats
    assert "Person=3" in feats
    assert "Gender=Masc" in feats
    assert "Number=Sing" in feats


def test_verb_piel_participle_active_fem_sing():
    """Piel Participle active feminine singular absolute."""
    upos, feats = decode("HVprfsa", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Piel" in feats
    assert "VerbForm=Part" in feats
    assert "Voice=Act" in feats
    assert "Gender=Fem" in feats
    assert "Number=Sing" in feats
    assert "State=Abs" in feats


def test_verb_hiphil_participle_active_masc_sing():
    """Hiphil Participle active masculine singular absolute."""
    upos, feats = decode("HVhrmsa", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Hif" in feats
    assert "VerbForm=Part" in feats
    assert "Voice=Act" in feats


def test_verb_qal_infinitive_construct():
    """Qal Infinitive Construct."""
    upos, feats = decode("HVqcc", "hbo")
    assert upos == "VERB"
    assert "VerbForm=Inf" in feats
    assert "State=Cns" in feats


def test_verb_qal_infinitive_absolute():
    """Qal Infinitive Absolute."""
    upos, feats = decode("HVqaa", "hbo")
    assert upos == "VERB"
    assert "VerbForm=Inf" in feats
    assert "State=Abs" in feats


def test_verb_wayyiqtol_consecutive_imperfect_3ms():
    """Consecutive Imperfect (wayyiqtol) Qal 3ms — past aspect=Cons."""
    upos, feats = decode("HVqw3ms", "hbo")
    assert upos == "VERB"
    assert "Aspect=Cons" in feats
    assert "Tense=Past" in feats
    assert "VerbForm=Fin" in feats
    assert "HebBinyan=Qal" in feats


def test_verb_weqatal_consecutive_perfect_3ms():
    """Consecutive Perfect (weqatal) Qal 3ms — future aspect=Cons."""
    upos, feats = decode("HVqq3ms", "hbo")
    assert upos == "VERB"
    assert "Aspect=Cons" in feats
    assert "VerbForm=Fin" in feats


def test_verb_imperative_qal_2ms():
    """Qal Imperative 2ms."""
    upos, feats = decode("HVqv2ms", "hbo")
    assert upos == "VERB"
    assert "Mood=Imp" in feats
    assert "VerbForm=Fin" in feats
    assert "Person=2" in feats
    assert "Gender=Masc" in feats


def test_verb_jussive_qal_3ms():
    """Qal Jussive 3ms."""
    upos, feats = decode("HVqj3ms", "hbo")
    assert upos == "VERB"
    assert "Mood=Jus" in feats
    assert "VerbForm=Fin" in feats


def test_verb_hophal_participle_passive():
    """Hophal Participle passive — Voice=Pass."""
    upos, feats = decode("HVHsmsa", "hbo")
    assert upos == "VERB"
    assert "VerbForm=Part" in feats
    assert "Voice=Pass" in feats
    assert "HebBinyan=Hof" in feats


# ---------------------------------------------------------------------------
# Clitic compounds — head detection
# ---------------------------------------------------------------------------

def test_clitic_conj_art_noun_head():
    """HC/Td/Ncfsa: conjunction + article + noun → noun is head."""
    upos, feats = decode("HC/Td/Ncfsa", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Fem|Number=Sing|State=Abs"


def test_clitic_prep_noun_head():
    """HR/Ncfsa: preposition + noun → noun is head."""
    upos, feats = decode("HR/Ncfsa", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Fem|Number=Sing|State=Abs"


def test_clitic_consec_conj_verb_head():
    """Hc/Vqw3ms: consecutive conjunction + verb → verb is head."""
    upos, feats = decode("Hc/Vqw3ms", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Qal" in feats
    assert "Aspect=Cons" in feats


def test_clitic_art_noun_with_suffix():
    """HTd/Ncfsa: article + noun (suffix compound) → noun head."""
    upos, feats = decode("HTd/Ncfsa", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Fem|Number=Sing|State=Abs"


def test_noun_with_pronominal_suffix():
    """HNcmsc/Sp3ms: noun-construct + pronominal-suffix → noun head."""
    upos, feats = decode("HNcmsc/Sp3ms", "hbo")
    assert upos == "NOUN"
    assert "Gender=Masc" in feats
    assert "State=Cns" in feats


# ---------------------------------------------------------------------------
# Adjective full FEATS
# ---------------------------------------------------------------------------

def test_adjective_common_masc_sing_abs():
    """Adjective common masculine singular absolute (real 4-char form)."""
    upos, feats = decode("HAamsa", "hbo")
    assert upos == "ADJ"
    assert "Gender=Masc" in feats
    assert "Number=Sing" in feats
    assert "State=Abs" in feats


def test_adjective_common_fem_plur_abs():
    """Adjective common feminine plural absolute."""
    upos, feats = decode("HAafpa", "hbo")
    assert upos == "ADJ"
    assert "Gender=Fem" in feats
    assert "Number=Plur" in feats


# ---------------------------------------------------------------------------
# Standalone function words (should decode to non-X UPOS even though proclitic)
# ---------------------------------------------------------------------------

def test_standalone_preposition_is_adp():
    """Standalone preposition HR."""
    upos, feats = decode("HR", "hbo")
    assert upos == "ADP"
    assert feats == "_"


def test_standalone_preposition_definite():
    """Standalone preposition-definite HRd."""
    upos, feats = decode("HRd", "hbo")
    assert upos == "ADP"
    assert feats == "_"


def test_standalone_definite_article():
    """Standalone definite article HTd."""
    upos, feats = decode("HTd", "hbo")
    assert upos == "DET"
    assert feats == "_"


def test_standalone_object_marker():
    """Standalone object marker HTo."""
    upos, feats = decode("HTo", "hbo")
    assert upos == "PART"
    assert feats == "_"


def test_standalone_conjunction():
    """Standalone conjunction HC."""
    upos, feats = decode("HC", "hbo")
    assert upos == "CCONJ"
    assert feats == "_"


# ---------------------------------------------------------------------------
# Aramaic (Daniel / Ezra portions)
# ---------------------------------------------------------------------------

def test_aramaic_verb_peal_perfect_3ms():
    """Aramaic Peal Perfect 3ms — same Qal binyan name used."""
    upos, feats = decode("AVqp3ms", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Qal" in feats
    assert "Tense=Past" in feats
    assert "VerbForm=Fin" in feats


def test_aramaic_noun_common_masc_sing_abs():
    """Aramaic noun common masculine singular absolute."""
    upos, feats = decode("ANcmsa", "hbo")
    assert upos == "NOUN"
    assert feats == "Gender=Masc|Number=Sing|State=Abs"


def test_aramaic_verb_aphel_perfect_3ms():
    """Aramaic Aphel (causative) Perfect 3ms."""
    upos, feats = decode("AVap3ms", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Aph" in feats
    assert "Tense=Past" in feats


def test_aramaic_verb_peil_passive():
    """Aramaic Peil (passive) code Q."""
    upos, feats = decode("AVQp3ms", "hbo")
    assert upos == "VERB"
    assert "HebBinyan=Peil" in feats


# ---------------------------------------------------------------------------
# Doc-table lock: cohortative, ADV, and u-form (conjunction+imperfect).
# These pin the form codes whose meanings are documented in FORMATS-morph.md
# so the table and the implementation cannot silently diverge.
# ---------------------------------------------------------------------------

def test_verb_cohortative_qal_1cs():
    """Cohortative ('c'+person) Qal 1st common singular — Mood=Coh, finite, Fut."""
    upos, feats = decode("HVqc1cs", "hbo")
    assert upos == "VERB"
    assert "Mood=Coh" in feats
    assert "VerbForm=Fin" in feats
    assert "Tense=Fut" in feats
    assert "Person=1" in feats
    assert "HebBinyan=Qal" in feats


def test_standalone_adverb_is_adv():
    """Adverb function code 'D' decodes to ADV."""
    upos, feats = decode("HD", "hbo")
    assert upos == "ADV"
    assert feats == "_"


def test_verb_conjunction_imperfect_uform_3ms():
    """u-form (conjunction+imperfect) Qal 3ms — finite future, no Cons aspect."""
    upos, feats = decode("HVqu3ms", "hbo")
    assert upos == "VERB"
    assert "VerbForm=Fin" in feats
    assert "Tense=Fut" in feats
    assert "Person=3" in feats
    assert "HebBinyan=Qal" in feats
    assert "Aspect=Cons" not in feats
