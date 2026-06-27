# Task 3 Report: Morph-code → (UPOS, FEATS) Decoder

## TDD evidence

### RED phase
```
$ python -m pytest tests/test_morph_feats.py -v
collected 0 items / 1 error
ImportError: No module named 'tools.morph_feats'
```
Tests written first, confirmed failing before implementation.

### GREEN phase (after implementing tools/morph_feats.py)
```
$ python -m pytest tests/test_morph_feats.py -v
57 passed in 0.23s
```

### Full suite (no regressions)
```
$ python -m pytest -v
162 passed in 0.66s   (105 pre-existing + 57 new)
```

---

## FEATS key vocabulary

All keys are standard UD/CoNLL-U names. Keys are always sorted alphabetically in
the output string.

| Key    | Values used                                      |
|--------|--------------------------------------------------|
| Case   | Acc, Dat, Gen, Nom, Voc                          |
| Degree | Cmp, Sup                                         |
| Gender | Fem, Masc, Neut                                  |
| Mood   | Imp (imperative), Ind, Inf, Opt, Part, Sub       |
| Number | Dual, Plur, Sing                                 |
| Person | 1, 2, 3                                          |
| Tense  | Aor, Fut, FutPerf, Impf, Perf, Plup, Pres       |
| Voice  | Act, Mid, Pass                                   |

Notes:
- Deponent voice (TAGNT code `D`) is mapped to `Voice=Mid` (closest UD
  equivalent; full deponency is lexically marked, not a morphological feature).
- 2nd Aorist (`2A` tense code) maps to the same `Tense=Aor` as 1st aorist.
- Imperfect uses `Impf` (not `Imp`) to avoid collision with imperative mood.
- Future Perfect (`FP` tense code) → `Tense=FutPerf` (rare; not UD-standard
  but unambiguous; retained for completeness).

---

## Greek code coverage

### POS mapping (TAGNT function codes → UPOS)

| TAGNT code | UPOS  | Notes                              |
|------------|-------|------------------------------------|
| N          | NOUN  |                                    |
| A          | ADJ   | degree extras C/S decoded          |
| T          | DET   | article                            |
| V          | VERB  | full verb feature decode           |
| P          | PRON  | personal pronoun                   |
| R          | PRON  | relative pronoun                   |
| D          | PRON  | demonstrative pronoun              |
| I          | PRON  | interrogative pronoun              |
| CONJ       | CCONJ |                                    |
| PREP       | ADP   |                                    |
| PRT-N      | PART  | negative particle                  |
| PRT        | PART  | other particles                    |
| ADV        | ADV   |                                    |
| INJ        | INTJ  |                                    |

### Nominal/adjectival/pronominal/article suffix (CNG)

Format `head-CNG[-Extra]`. CNG = Case + Number + Gender (one char each).
Extra suffix for adjectives: C → Degree=Cmp, S → Degree=Sup.
Other extra suffixes (T=Title, P=Person name, L=Location, G/LG/PG=Gentilic)
are parsed and silently dropped (not FEATS-relevant at this level).

### Verb suffix

Structure: `V-TVM-Suffix` where TVM = Tense+Voice+Mood (2-4 chars).

Parsing: mood = TVM[-1], voice = TVM[-2], tense = TVM[:-2].

This cleanly handles multi-char tenses (2A, FP) without special-casing.

Suffix interpretation depends on mood:
- Mood=Part (P): suffix is CNG (Case/Number/Gender) → full nominal features
- Mood=Inf (N): no suffix → Tense+Voice+Mood only
- Finite (I/S/O/M): suffix is PersonNumber (`1S`/`2P`/`3P` etc.)

All tenses (P/I/F/A/2A/R/L/FP), voices (A/M/P/D), moods (I/S/O/M/N/P),
persons (1/2/3), and numbers (S/P/D) are decoded.

---

## What is deliberately left for Task 6 (Hebrew features)

The Hebrew decoder (`_decode_hebrew`) is a minimal stub:
- Strips the language prefix (H/A) when followed by an uppercase function
  letter; handles both raw TAHOT values (`HVqp3ms`) and prefix-stripped
  values (`Vqp3ms`).
- Maps the leading function character to UPOS only.
- Always returns `feats="_"`.

NOT implemented in Task 3 (reserved for Task 6):
- Noun/Adjective suffix decode: type (common/proper), gender, number, state
  (absolute/construct)
- Verb stem decode: Qal/Niphal/Piel/Pual/Hiphil/Hophal/Hithpael/Aramaic stems
- Verb form decode: Perfect/Imperfect/Imperative/Participle/Infinitive/Sequential
- Verb person/gender/number
- Pronoun suffix features
- Aramaic vs Hebrew distinction as a feature
- Slash-separated prefix-root-suffix compound forms (root extraction for FEATS)

---

## Files committed

- `tools/morph_feats.py` — implementation
- `tests/test_morph_feats.py` — 57 tests (3 baseline + 54 extended)
