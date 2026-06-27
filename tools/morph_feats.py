"""Task 3: Morph-code -> (UPOS, FEATS) decoder.

Entry point
-----------
    decode(xpos: str, lang: str) -> tuple[str, str]

``lang`` is ``"grc"`` (Greek TAGNT) or ``"hbo"`` (Hebrew TAHOT).
Returns ``(upos, feats)`` where ``feats`` is a ``Key=Val|...`` string with
keys sorted alphabetically, or ``"_"`` when no features are available.
Unknown / empty / placeholder codes return ``("X", "_")``.

Greek decoder
-------------
Implements the full TAGNT morph-code scheme (Robinson / TEGMC).
POS codes covered: N, A, T, V, P, R, D, I, CONJ, PREP, PRT-N, ADV, INJ.

Hebrew / Aramaic decoder  (Task 6)
-----------------------------------
Implements the full TAHOT morph-code scheme (TEHMC / OpenScriptures).
Codes are slash-separated for compound (clitic) words; the head morpheme
is the first segment whose function code is NOT a proclitic prefix
(C, c, R, Rd, T, Td, To) and NOT a pronominal suffix (S).  For single-
segment tokens the segment IS the head and is decoded directly.

FEATS vocabulary
----------------
Greek keys  : Case, Degree, Gender, Mood, Number, Person, Tense, Voice
Greek values:
  Case   - Acc Dat Gen Nom Voc
  Degree - Cmp Sup
  Gender - Fem Masc Neut
  Mood   - Imp Ind Inf Opt Part Sub
  Number - Dual Plur Sing
  Person - 1 2 3
  Tense  - Aor Fut FutPerf Impf Perf Plup Pres
  Voice  - Act Mid Pass

Hebrew keys : Aspect, Gender, HebBinyan, Mood, Number, Person, State, Tense,
              VerbForm, Voice
Hebrew values:
  Aspect    - Abs (inf. absolute), Cons (consecutive/sequential)
  Gender    - Com Fem Masc
  HebBinyan - Qal Nif Piel Pual Hif Hof Htpa Htpaal Nithpa Tif
               Aph Shaph Peil Ithpeel Hitpeel Ishtaph  (verb stem)
  Mood      - Coh (cohortative) Imp (imperative) Jus (jussive)
  Number    - Dual Plur Sing
  Person    - 1 2 3
  State     - Abs Cns Def
  Tense     - Fut Past
  VerbForm  - Fin Inf Part
  Voice     - Act Pass
"""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _feats(d: dict) -> str:
    """Render a feature dict to a sorted CoNLL-U FEATS string."""
    if not d:
        return "_"
    return "|".join(f"{k}={d[k]}" for k in sorted(d))


# ---------------------------------------------------------------------------
# Greek decoder
# ---------------------------------------------------------------------------

# POS codes that stand alone (no case/number/gender suffix)
_GRC_FIXED: dict[str, tuple[str, str]] = {
    "PREP":    ("ADP",   "_"),
    "CONJ":    ("CCONJ", "_"),
    "CONJ-N":  ("CCONJ", "_"),
    "COND":    ("SCONJ", "_"),   # εἰ/ἐάν conditional conjunction
    "ADV":     ("ADV",   "_"),
    "ADV-I":   ("ADV",   "_"),
    "PRT-N":   ("PART",  "_"),
    "PRT-I":   ("PART",  "_"),
    "PRT":     ("PART",  "_"),
    "INJ":     ("INTJ",  "_"),
    "INJ-HEB": ("INTJ",  "_"),
}

# Inflected POS head → UPOS
_GRC_POS: dict[str, str] = {
    "N": "NOUN",
    "A": "ADJ",
    "T": "DET",
    "V": "VERB",
    "P": "PRON",   # personal pronoun
    "R": "PRON",   # relative pronoun
    "D": "PRON",   # demonstrative pronoun
    "I": "PRON",   # interrogative pronoun
}

# Case, Number, Gender for nominal/adjectival/pronominal/article forms
_CASE: dict[str, str] = {"N": "Nom", "G": "Gen", "D": "Dat", "A": "Acc", "V": "Voc"}
_NUM:  dict[str, str] = {"S": "Sing", "P": "Plur", "D": "Dual"}
_GEN:  dict[str, str] = {"M": "Masc", "F": "Fem",  "N": "Neut"}

# Verb feature maps
_TENSE: dict[str, str] = {
    "P":  "Pres",
    "I":  "Impf",
    "F":  "Fut",
    "A":  "Aor",
    "2A": "Aor",      # 2nd aorist — same Tense value as 1st aorist
    "R":  "Perf",
    "L":  "Plup",
    "FP": "FutPerf",
}

_VOICE: dict[str, str] = {
    "A": "Act",
    "M": "Mid",
    "P": "Pass",
    "D": "Mid",   # Deponent — treated as Middle in features
}

_MOOD: dict[str, str] = {
    "I": "Ind",
    "S": "Sub",
    "O": "Opt",
    "M": "Imp",   # Imperative
    "N": "Inf",   # Infinitive
    "P": "Part",  # Participle
}

_PERSON: dict[str, str] = {"1": "1", "2": "2", "3": "3"}

# Adjective degree extra-suffix codes
_DEGREE: dict[str, str] = {"C": "Cmp", "S": "Sup"}


def _decode_cng(cng: str, d: dict) -> None:
    """Decode a 3-char Case-Number-Gender suffix into dict ``d`` in-place."""
    if len(cng) >= 1 and cng[0] in _CASE:
        d["Case"] = _CASE[cng[0]]
    if len(cng) >= 2 and cng[1] in _NUM:
        d["Number"] = _NUM[cng[1]]
    if len(cng) >= 3 and cng[2] in _GEN:
        d["Gender"] = _GEN[cng[2]]


def _decode_greek_verb(tvm_str: str, suffix: str | None) -> dict:
    """Decode the tense-voice-mood string and optional suffix for verbs.

    ``tvm_str`` is the segment after the first '-', e.g. ``'AAI'``, ``'2AAI'``,
    ``'FPAI'``, ``'AAN'``, ``'AAP'``.
    ``suffix`` is the segment after the second '-' (may be None), e.g. ``'3S'``,
    ``'NSM'``.
    """
    if len(tvm_str) < 3:
        return {}

    mood_code  = tvm_str[-1]
    voice_code = tvm_str[-2]
    tense_code = tvm_str[:-2]  # 1 or 2 chars: P/I/F/A/R/L/2A/FP

    d: dict = {}

    tense = _TENSE.get(tense_code)
    if tense:
        d["Tense"] = tense

    voice = _VOICE.get(voice_code)
    if voice:
        d["Voice"] = voice

    mood = _MOOD.get(mood_code)
    if mood:
        d["Mood"] = mood

    if suffix is None:
        # Infinitive: no further encoding
        return d

    if mood_code == "P":
        # Participle: suffix is Case-Number-Gender (3 chars)
        _decode_cng(suffix, d)
    else:
        # Finite form: suffix is Person+Number, e.g. '3S', '1P'
        if suffix and suffix[0] in _PERSON:
            d["Person"] = _PERSON[suffix[0]]
        if len(suffix) >= 2 and suffix[1] in _NUM:
            d["Number"] = _NUM[suffix[1]]

    return d


def _decode_greek(xpos: str) -> tuple[str, str]:
    # Check for invariant codes first (may contain '-', e.g. 'PRT-N')
    if xpos in _GRC_FIXED:
        return _GRC_FIXED[xpos]

    parts = xpos.split("-")
    head  = parts[0]

    upos = _GRC_POS.get(head)
    if upos is None:
        return "X", "_"

    d: dict = {}

    if head == "V":
        if len(parts) < 2:
            return upos, "_"
        tvm_str = parts[1]
        suffix  = parts[2] if len(parts) >= 3 else None
        d = _decode_greek_verb(tvm_str, suffix)

    elif head in _GRC_POS:
        # 1st/2nd person personal pronouns use Person-Case-Number order
        # (no gender), e.g. P-1GS = Person 1, Gen, Sing; P-2DP = Person 2,
        # Dat, Plur.  The Case letter D (Dative) would otherwise collide with
        # the Dual number code under the CNG parser, so route these first.
        if head == "P" and len(parts) >= 2 and parts[1][:1] in ("1", "2"):
            pcn = parts[1]
            d["Person"] = pcn[0]
            if len(pcn) >= 2 and pcn[1] in _CASE:
                d["Case"] = _CASE[pcn[1]]
            if len(pcn) >= 3 and pcn[2] in _NUM:
                d["Number"] = _NUM[pcn[2]]
            return upos, _feats(d)
        # Nominal/adjectival/pronominal/article: second segment is CNG
        if len(parts) >= 2:
            _decode_cng(parts[1], d)
        # Adjective: optional third segment is degree marker
        if head == "A" and len(parts) >= 3:
            deg = _DEGREE.get(parts[2])
            if deg:
                d["Degree"] = deg
        # Extra suffixes for other POS (T, P, L, G, …) are not FEATS; ignore.

    return upos, _feats(d)


# ---------------------------------------------------------------------------
# Hebrew / Aramaic decoder  (Task 6)
# ---------------------------------------------------------------------------

# Function codes that are TWO characters and need special recognition.
# All recognised 2-char T-family codes are listed here; only Td, To (plus the
# standalone R compound Rd) are proclitics.  The remaining T-subtypes (Tc, Tn,
# Ti, Tm, Tj, Tr, Ta) are head morphemes in their own right.
_HBO_T2 = frozenset({"Rd", "Ta", "Tc", "Td", "Ti", "Tj", "Tm", "Tn", "To", "Tr"})

# Function codes that mark proclitic prefixes or pronominal suffixes
# (non-head in a compound word).  S is listed here but is decoded when
# it appears as a standalone single-segment token.
_HBO_PROCLITICS = frozenset({"C", "c", "R", "Rd", "S", "T", "Td", "To"})

# Verb stem code -> HebBinyan label
_HBO_STEM: dict[str, str] = {
    # Hebrew stems
    "q": "Qal",    "N": "Nif",   "p": "Piel",    "P": "Pual",
    "h": "Hif",    "H": "Hof",   "t": "Htpa",    "u": "Htpaal",
    "D": "Nithpa", "c": "Tif",
    # Aramaic stems (appear in Daniel / Ezra / Nehemiah portions)
    "a": "Aph",    "e": "Shaph", "Q": "Peil",    "M": "Ithpeel",
    "i": "Hitpeel","v": "Ishtaph",
}

# Verb finite-form codes -> (VerbForm, Tense, Mood, Aspect)
# None means the feature is not set.
_HBO_VFORM_FIN: dict[str, tuple] = {
    "p": ("Fin", "Past", None,  None),   # Perfect
    "i": ("Fin", "Fut",  None,  None),   # Imperfect (indicative/jussive ambiguous)
    "j": ("Fin", "Fut",  "Jus", None),   # Jussive
    "n": ("Fin", "Fut",  None,  None),   # Imperfect Indicative (theoretical)
    "v": ("Fin", None,   "Imp", None),   # Imperative
    "w": ("Fin", "Past", None,  "Cons"), # Consecutive Imperfect (wayyiqtol)
    "q": ("Fin", "Fut",  None,  "Cons"), # Consecutive Perfect (weqatal)
    "u": ("Fin", "Fut",  None,  None),   # Conjunction+Imperfect
}

# Gender codes (shared by nouns, adjectives, verbs, pronouns)
_HBO_GENDER: dict[str, str] = {
    "m": "Masc", "f": "Fem", "b": "Com", "c": "Com",
}

# Number codes
_HBO_NUMBER: dict[str, str] = {"s": "Sing", "p": "Plur", "d": "Dual"}

# State codes (absolute / construct / Aramaic definite)
_HBO_STATE: dict[str, str] = {"a": "Abs", "c": "Cns", "d": "Def"}

# Adjective form-subtype codes (first char of adjective rest)
_HBO_ADJ_FORM = frozenset({"a", "c", "o"})


def _heb_get_func(seg: str) -> str:
    """Return the 1- or 2-character function code from a stripped segment.

    Two-character codes (Rd and the T-family) are recognised first.
    """
    if len(seg) >= 2 and seg[:2] in _HBO_T2:
        return seg[:2]
    return seg[:1] if seg else ""


def _heb_strip_prefix(seg: str) -> str:
    """Strip the TAHOT language prefix (H=Hebrew, A=Aramaic).

    H is always the Hebrew language prefix; strip it unconditionally when
    followed by any character (including lowercase 'c' = consecutive conj).

    A is ambiguous: when followed by an UPPERCASE function-code letter it is
    the Aramaic language prefix; when followed by a lowercase letter it IS
    the Adjective function code (e.g. 'Amsa').
    """
    if len(seg) < 2:
        return seg
    if seg[0] == "H":
        return seg[1:]
    if seg[0] == "A" and seg[1].isupper():
        return seg[1:]
    return seg


def _decode_heb_noun(rest: str) -> tuple[str, str]:
    """Decode noun after N function code.

    Format: subtype(c=common, p=proper) + gender + number + state  (4 chars).
    Subtype p -> PROPN; for proper nouns, number/state may be absent.
    """
    if not rest:
        return "NOUN", "_"
    subtype = rest[0]
    upos = "PROPN" if subtype == "p" else "NOUN"
    d: dict = {}
    if len(rest) >= 2:
        g = _HBO_GENDER.get(rest[1])
        if g:
            d["Gender"] = g
    if len(rest) >= 3:
        n = _HBO_NUMBER.get(rest[2])
        if n:
            d["Number"] = n
    if len(rest) >= 4:
        st = _HBO_STATE.get(rest[3])
        if st:
            d["State"] = st
    return upos, _feats(d)


def _decode_heb_adj(rest: str) -> tuple[str, str]:
    """Decode adjective after A function code.

    Real TAHOT format: form-subtype(a/c/o) + gender + number + state (4 chars).
    Backward-compat 3-char format (no subtype): gender + number + state.
    """
    d: dict = {}
    # Determine starting position: skip form-subtype if present
    if rest and rest[0] in _HBO_ADJ_FORM and len(rest) >= 4:
        start = 1  # skip subtype
    else:
        start = 0  # direct gender+number+state
    if len(rest) > start:
        g = _HBO_GENDER.get(rest[start])
        if g:
            d["Gender"] = g
    if len(rest) > start + 1:
        n = _HBO_NUMBER.get(rest[start + 1])
        if n:
            d["Number"] = n
    if len(rest) > start + 2:
        st = _HBO_STATE.get(rest[start + 2])
        if st:
            d["State"] = st
    return "ADJ", _feats(d)


def _decode_heb_verb(rest: str) -> tuple[str, str]:
    """Decode verb after V function code.

    Format: stem(1) + form(1) + suffix.
    Finite suffix:        person(1) + gender(1) + number(1).
    Participle suffix:    gender(1) + number(1) + state(1).
    Infinitive suffix:    state(1).
    Cohortative ('c'):    disambiguated by next char (digit=finite, else inf).
    """
    d: dict = {}
    if not rest:
        return "VERB", "_"

    stem = _HBO_STEM.get(rest[0])
    if stem:
        d["HebBinyan"] = stem

    if len(rest) < 2:
        return "VERB", _feats(d)

    form = rest[1]

    # -- Participles ---------------------------------------------------
    if form == "r":
        d["VerbForm"] = "Part"
        d["Voice"] = "Act"
        if len(rest) >= 3:
            g = _HBO_GENDER.get(rest[2])
            if g:
                d["Gender"] = g
        if len(rest) >= 4:
            n = _HBO_NUMBER.get(rest[3])
            if n:
                d["Number"] = n
        if len(rest) >= 5:
            st = _HBO_STATE.get(rest[4])
            if st:
                d["State"] = st
        return "VERB", _feats(d)

    if form == "s":
        d["VerbForm"] = "Part"
        d["Voice"] = "Pass"
        if len(rest) >= 3:
            g = _HBO_GENDER.get(rest[2])
            if g:
                d["Gender"] = g
        if len(rest) >= 4:
            n = _HBO_NUMBER.get(rest[3])
            if n:
                d["Number"] = n
        if len(rest) >= 5:
            st = _HBO_STATE.get(rest[4])
            if st:
                d["State"] = st
        return "VERB", _feats(d)

    # -- Infinitive Absolute -------------------------------------------
    if form == "a":
        d["VerbForm"] = "Inf"
        if len(rest) >= 3:
            st = _HBO_STATE.get(rest[2])
            if st:
                d["State"] = st
        return "VERB", _feats(d)

    # -- 'c': Cohortative (finite) or Infinitive Construct (non-finite) --
    if form == "c":
        next_ch = rest[2] if len(rest) >= 3 else ""
        if next_ch in ("1", "2", "3"):
            # Cohortative finite: person + gender + number
            d["VerbForm"] = "Fin"
            d["Tense"] = "Fut"
            d["Mood"] = "Coh"
            d["Person"] = next_ch
            if len(rest) >= 4:
                g = _HBO_GENDER.get(rest[3])
                if g:
                    d["Gender"] = g
            if len(rest) >= 5:
                n = _HBO_NUMBER.get(rest[4])
                if n:
                    d["Number"] = n
        else:
            # Infinitive Construct
            d["VerbForm"] = "Inf"
            if next_ch in _HBO_STATE:
                d["State"] = _HBO_STATE[next_ch]
        return "VERB", _feats(d)

    # -- All other finite forms ----------------------------------------
    info = _HBO_VFORM_FIN.get(form)
    if info:
        vf, tense, mood, aspect = info
        d["VerbForm"] = vf
        if tense:
            d["Tense"] = tense
        if mood:
            d["Mood"] = mood
        if aspect:
            d["Aspect"] = aspect
        # Finite suffix: person + gender + number
        if len(rest) >= 3 and rest[2] in ("1", "2", "3"):
            d["Person"] = rest[2]
        if len(rest) >= 4:
            g = _HBO_GENDER.get(rest[3])
            if g:
                d["Gender"] = g
        if len(rest) >= 5:
            n = _HBO_NUMBER.get(rest[4])
            if n:
                d["Number"] = n

    return "VERB", _feats(d)


def _decode_heb_pron(rest: str) -> tuple[str, str]:
    """Decode pronoun after P function code.

    Format: subtype(p=personal, i=interrogative) + person + gender + number.
    """
    d: dict = {}
    if not rest or rest[0] != "p":
        # Interrogative or empty: no person/gender/number feats
        return "PRON", "_"
    # Personal: p + person + gender + number
    if len(rest) >= 2 and rest[1] in ("1", "2", "3"):
        d["Person"] = rest[1]
    if len(rest) >= 3:
        g = _HBO_GENDER.get(rest[2])
        if g:
            d["Gender"] = g
    if len(rest) >= 4:
        n = _HBO_NUMBER.get(rest[3])
        if n:
            d["Number"] = n
    return "PRON", _feats(d)


def _decode_heb_suffix(rest: str) -> tuple[str, str]:
    """Decode pronominal suffix after S function code (standalone segment).

    Format: subtype + person + gender + number.
    Non-personal subtypes (d=directional, h=paragogic-he, n=paragogic-nun)
    have no person/gender/number feats.
    """
    d: dict = {}
    if not rest or rest[0] != "p":
        return "PRON", "_"
    if len(rest) >= 2 and rest[1] in ("1", "2", "3"):
        d["Person"] = rest[1]
    if len(rest) >= 3:
        g = _HBO_GENDER.get(rest[2])
        if g:
            d["Gender"] = g
    if len(rest) >= 4:
        n = _HBO_NUMBER.get(rest[3])
        if n:
            d["Number"] = n
    return "PRON", _feats(d)


def _decode_heb_head(seg: str) -> tuple[str, str]:
    """Decode a language-prefix-stripped segment by its function code."""
    func = _heb_get_func(seg)
    rest = seg[len(func):]

    if func == "N":
        return _decode_heb_noun(rest)
    if func == "A":
        return _decode_heb_adj(rest)
    if func == "V":
        return _decode_heb_verb(rest)
    if func == "D":
        return "ADV", "_"
    if func == "P":
        return _decode_heb_pron(rest)
    if func == "S":
        return _decode_heb_suffix(rest)
    if func in ("R", "Rd"):
        return "ADP", "_"
    if func in ("C", "c"):
        return "CCONJ", "_"
    if func in ("T", "Td", "Ta", "Tm"):
        return "DET", "_"
    if func == "To":
        return "PART", "_"
    if func == "Tn":
        return "PART", "_"
    if func in ("Tc", "Tr"):
        return "SCONJ", "_"
    if func == "Ti":
        return "PART", "_"
    if func == "Tj":
        return "INTJ", "_"
    return "X", "_"


def _decode_hebrew(xpos: str) -> tuple[str, str]:
    """Decode a TAHOT morph code to (UPOS, FEATS).

    Handles:
    * Single-segment codes (e.g. HVqp3ms, HNcmpa, HR): decoded directly.
    * Slash-separated compound codes (e.g. HC/Td/Ncfsa): head is the first
      segment that is not a proclitic prefix (C, c, R, Rd, T, Td, To) and
      not a pronominal suffix (S).  If no such segment is found the last
      segment is decoded as fallback.
    """
    if "/" not in xpos:
        # Single-segment: this IS the token head.
        seg = _heb_strip_prefix(xpos)
        return _decode_heb_head(seg)

    # Multi-segment compound: find first non-proclitic / non-suffix segment.
    parts = xpos.split("/")
    for part in parts:
        seg = _heb_strip_prefix(part)
        func = _heb_get_func(seg)
        if func and func not in _HBO_PROCLITICS:
            return _decode_heb_head(seg)

    # Fallback: decode last segment (e.g. all-proclitic edge case).
    seg = _heb_strip_prefix(parts[-1])
    return _decode_heb_head(seg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decode(xpos: str, lang: str) -> tuple[str, str]:
    """Decode a raw STEPBible morph code to (UPOS, FEATS).

    Parameters
    ----------
    xpos:
        Raw morph code from the normalised TSV ``xpos`` column.
        For Greek (TAGNT): e.g. ``'N-NSF'``, ``'V-AAI-3S'``, ``'PREP'``.
        For Hebrew (TAHOT): e.g. ``'Ncfsa'``, ``'Vqp3ms'``, ``'HVqp3ms'``.
    lang:
        ``'grc'`` or ``'hbo'``.

    Returns
    -------
    (upos, feats):
        ``upos`` is a Universal POS tag string.
        ``feats`` is a ``Key=Val|...`` string with alphabetically sorted keys,
        or ``'_'`` when no features are decoded.
        Unknown / empty / placeholder codes return ``('X', '_')``.
    """
    if not xpos or xpos == "_":
        return "X", "_"

    if lang == "grc":
        return _decode_greek(xpos)

    # lang == "hbo" (or anything else falls back to Hebrew stub)
    return _decode_hebrew(xpos)
