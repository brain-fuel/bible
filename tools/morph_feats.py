"""Task 3: Morph-code → (UPOS, FEATS) decoder.

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

Hebrew decoder
--------------
Minimal stub (Task 6 adds feature decoding): maps the leading function
character to a UPOS and always returns feats="_".

FEATS vocabulary
----------------
Keys  : Case, Degree, Gender, Mood, Number, Person, Tense, Voice
Values:
  Case   – Acc Dat Gen Nom Voc
  Degree – Cmp Sup
  Gender – Fem Masc Neut
  Mood   – Imp Ind Inf Opt Part Sub
  Number – Dual Plur Sing
  Person – 1 2 3
  Tense  – Aor Fut FutPerf Impf Perf Plup Pres
  Voice  – Act Mid Pass
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
    "PREP": ("ADP",   "_"),
    "CONJ": ("CCONJ", "_"),
    "ADV":  ("ADV",   "_"),
    "PRT-N": ("PART", "_"),
    "PRT":   ("PART", "_"),
    "INJ":   ("INTJ", "_"),
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
# Hebrew stub decoder (Task 6 adds full feature decoding)
# ---------------------------------------------------------------------------

# Map TAHOT function character → UPOS
_HBO_POS: dict[str, str] = {
    "N": "NOUN",
    "V": "VERB",
    "A": "ADJ",
    "P": "PRON",
    "R": "ADP",
    "C": "CCONJ",
    "c": "CCONJ",   # consecutive conjunction
    "D": "ADV",
    "T": "DET",
    "S": "PRON",    # pronominal suffix
}


def _decode_hebrew(xpos: str) -> tuple[str, str]:
    s = xpos
    # Strip the TAHOT language prefix (H=Hebrew, A=Aramaic) only when the
    # character that follows it is an uppercase function-code letter.
    # This avoids misidentifying "A" = Adjective as a language prefix when
    # the next character is a lowercase parsing letter (e.g. "Amsa").
    if (
        len(s) >= 2
        and s[0] in ("H", "A")
        and s[1].isupper()
    ):
        s = s[1:]
    head = s[0] if s else ""
    return _HBO_POS.get(head, "X"), "_"


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
