# Morpho-Lexical Floor (L1 + L2a) — Design Spec

**Date:** 2026-06-27
**Status:** Approved (brainstorming complete)
**Repo:** `~/matt/bible`

## Purpose

The existing corpus (`bible/`) is verse-aligned parallel surface text (L0). This
spec defines the first layer *above* it: a morpho-lexical floor that tags every
word with its lemma, morphology, and Strong's number, and a lemma-keyed lexicon
with multilingual glosses and a semantic-domain thesaurus spine.

This floor is sub-project #1 of a larger layered stack. The full stack (named so
the schema leaves room, NOT built here):

- **L0 — Text** (DONE): verse-aligned surface text.
- **L1 — Morpho-lexical** (THIS SPEC): per-token lemma + morphology + Strong's.
- **L2a — Lexicon entry** (THIS SPEC): per-lemma dictionary + sense + domain.
- **L2b — Lemma relation-graph** (NEXT SPEC): synonym/antonym/cognate edges.
- **L3 — Syntax** (later): dependency trees.
- **L4/L5 — Logic / rhetoric / argument / theology / paradox graph** (telos).

## Scope

**First build covers NT Greek + OT Hebrew.** Apocrypha and any further parallel
editions extend the floor additively later (same engine, more registry rows).

**Deferred (named, schema leaves room, NOT built in this spec):**

- L2b lemma relation-graph (builds on this spec's `senses` / `domains` / `root` hooks).
- L3 syntax (CoNLL-U `HEAD`/`DEPREL` columns sit empty, ready).
- L4/L5 logic / argument / theology / paradox graph.
- "Author your own translation" composition feature (`MISC` / glosses schema-ready; engine later).

## Architecture: two-form (sources are truth, DB is derived)

Mirrors the existing repo philosophy (`generate_ot.py` builds artifacts from
self-describing sources).

```
CANONICAL (truth, hand-editable, git-diffable)        DERIVED (built, queryable)
  morph/<test>/<CODE>/NNN.conllu   ── L1 tokens ──┐
  lexicon/<lang>/<STRONG>.json     ── L2a entries ─┼──► tools.build_db ──► data/tokens.sqlite
                                                   │
  bible/  (L0, NEVER mutated) ──────────────────── ┘
```

- **DB is derived, never authored.** Pure projection of the canonical files.
  Drop and rebuild anytime. Gitignored.
- **Canonical = CoNLL-U token files + lexicon JSON.** The truth. Hand-edited to
  fix alignments, add glosses, and author your own renderings.
- **L0 text never mutated.** Existing validators / byte-stable pins survive.
  Your own translations become a new *derived* column composed from per-token
  glosses — same move as adding a parallel edition today.

## L1 — Token layer

### Sources (PD / open, registry-driven)

A new registry `data/morph-sources.json` carries one row per language and drives
the build (the aligner names no language, exactly as `generate_ot.py` names no
edition).

- **Greek NT:** Scrivener 1894 Textus Receptus tagged with Strong's + Robinson
  morphology. Scrivener's TR is the Greek text reconstructed behind the KJV, so
  it is the native match to the `greek_textus_receptus` column. Exact best source
  file is a research/verify task in the plan (candidates: Scrivener TR with
  Strong's+morph; Stephanus 1550 with parsing).
- **Hebrew OT:** OpenScriptures Hebrew Bible (OSHB / morphhb) — Strong's +
  morphology on the Westminster Leningrad Codex, CC-BY. Native match to the
  Sefaria WLC `hebrew_masoretic` column.

### CoNLL-U token schema

Canonical files: `morph/<testament>/<CODE>/NNN.conllu`. Sentence = verse,
anchored by a `# ref = JOH.1.1` comment to the L0 verse ID.

| Column | Holds |
|--------|-------|
| ID | token index in verse; ranges (`5-6`) for crasis/elision (1 surface → many lemmas) |
| FORM | surface token, taken from L0 corpus text (authoritative) |
| LEMMA | dictionary headword |
| UPOS | normalized part-of-speech (universal) |
| XPOS | raw source code verbatim (Robinson tag / OSHB code) |
| FEATS | normalized morph features (Case, Tense, Person, Binyan, …) |
| HEAD | empty now → L3 syntax later |
| DEPREL | empty now → L3 syntax later |
| MISC | `Strong=G3056`, `Translit=…`, `gloss_*`, your renderings, `Align=` provenance |

CoNLL-U gives morph normalization for free: every token is both verbatim-source
(XPOS) and queryable-structured (UPOS + FEATS).

### Alignment method (the data risk)

L0 corpus text is **authoritative** — tags map onto it, never overwrite it.

1. Tokenize the L0 surface verse.
2. Match against the tagged-source tokens by normalized surface (strip
   accents/pointing for matching; keep originals in FORM).
3. Attach lemma / morph / Strong's from the matched source token.
4. Where the tagged edition's wording diverges from the corpus edition
   (different TR printing, ketiv/qere, verse merges): record a token-level
   `Align=` note in MISC; the validator flags and counts it.

No silent guesses. Mismatches are visible, countable, and pinned so coverage
cannot drift — same oracle/pin discipline as `validate_ot.py`.

## L2a — Lexicon entry (dictionary + thesaurus spine)

One file per lemma, keyed by Strong's: `lexicon/grc/G0026.json`,
`lexicon/hbo/H0430.json`. Human-editable, git-diffable, slurped to DB.

### Entry schema

```json
{
  "strong": "G26",
  "lemma": "ἀγάπη",
  "translit": "agapē",
  "lang": "grc",
  "pos": "noun",
  "glosses": {
    "en": [{"text": "love, affection", "src": "abbott-smith"}],
    "la": [{"text": "caritas, dilectio", "src": "vulgate-link"}],
    "fi": [{"text": "rakkaus", "src": "..."}]
  },
  "senses": [
    {"id": 1, "gloss_en": "God's love", "domain": "25.43"},
    {"id": 2, "gloss_en": "love-feast",  "domain": "23.28"}
  ],
  "domains": ["25.43"],
  "root": "G25",
  "sources": ["strongs", "abbott-smith", "ln-domain-map"]
}
```

### Sources (PD / open)

- **Spine:** Strong's dictionary (PD) — headword, transliteration, base gloss, root pointer.
- **Greek definitions:** Abbott-Smith (1922, PD); Thayer (PD) fallback.
- **Hebrew definitions:** BDB (PD); Strong's Hebrew; Gesenius fallback.
- **Domain spine (thesaurus):** Louw-Nida domain *numbers* via an open
  Strong's→domain mapping. **Licensing must be verified in the plan**; the L-N
  lexicon *text* is UBS-copyright, only open *mappings* are usable. If no open
  mapping is confirmed, fall back to an open taxonomy (SDBH/SDBG — Semantic
  Dictionary of Biblical Hebrew/Greek, UBS open — or SIL domains). The domain
  number clusters words by meaning, powering "connections."
- **Multilingual glosses:** seed every PD-available language now; each gloss
  tagged with `src` provenance. English certain; Latin derived by linking the
  lemma to the aligned Vulgate token; Finnish/others where Strong's-linkable.
  Empty languages = ready slots, filled later in the editable layer.

### Hooks for later layers

`senses`, `root`, and `domains` are the attach points L2b and L5 grab later.
Sense divisions are split here so the relation-graph spec builds *on* them rather
than redoing them. The floor lays honest sense + domain data; the deep
relational / synonym authoring is the next spec's job, working from these hooks.

### Provenance

`src` / `sources` everywhere, so attribution is mechanical at ship time — the
repo's CC-BY / PD discipline holds.

## Derived DB

**Engine: SQLite.** Single file, relational joins, zero-server, rebuildable.
(DuckDB swappable later with the same build code.)

**Build:** `tools.build_db` slurps canonical CoNLL-U + lexicon JSON → emits
`data/tokens.sqlite`. Deterministic, idempotent, never hand-edited, gitignored.

**Schema:**

```
verses(ref PK, testament, book, chapter, verse, kjv, vulgate, greek, hebrew, ...)
tokens(id PK, ref FK→verses, idx, range, form, lemma, strong FK→lexicon,
       upos, xpos, feats, translit, align_note)
lexicon(strong PK, lemma, translit, lang, pos, root FK→lexicon)
glosses(strong FK, lang, text, src)          -- multilingual, provenance
senses(strong FK, sense_id, gloss_en, domain)
domains(strong FK, domain)                    -- thesaurus join table
```

**Unlocks immediately (floor-level):**

- **Concordance** — every occurrence of a Strong's = one `WHERE strong=` join (free).
- **Thesaurus / connections** — "all words in domain 25.43" = `domains`→`lexicon`→`tokens` join.
- **Cross-translation** — token ↔ L0 verse ↔ every parallel column = joins on `ref`.
- **Morph search** — "every aorist passive participle" = `WHERE feats LIKE`.
- **Coverage reports** — tagged vs exception tokens, gloss coverage per language, pinned.

The DB carries no truth the canonical files lack — drop and rebuild anytime.

## Repo layout

Same repo (`~/matt/bible`); additive trees beside `bible/`; no L0 edits. (Another
agent is live on Apocrypha; collision surface is near-zero — new dirs + new
tools, and a new `morph-sources.json` registry rather than editing `editions.json`.)

```
bible/                          L0 (untouched)
morph/<test>/<CODE>/NNN.conllu  L1 canonical
lexicon/<lang>/<STRONG>.json    L2a canonical
data/morph-sources.json         registry (1 row/language, drives build)
data/tokens.sqlite              derived (gitignored)
tools/
  align.py            L0 + tagged source → CoNLL-U   (scheme-parametric)
  build_lexicon.py    PD sources → lexicon JSON
  build_db.py         canonical → sqlite
  validate_morph.py   oracles + pinned counts
  sources/            new backends: tagged-TR, OSHB, abbott-smith, bdb, ln-map
tests/
```

Tools mirror the existing pattern — registry-driven, scheme-parametric (Greek vs
Hebrew = data rows, not code forks), exactly as `generate_ot.py` names no edition.

## Testing

TDD, incremental verified MO. Every claim has an oracle. `validate_morph.py` pins:

- per-verse token coverage (every L0 verse has a CoNLL-U sentence),
- FORM ↔ L0 text reconciliation (every token's FORM reconciles to L0),
- Strong's resolvability (every token's Strong → a lexicon entry),
- gloss-coverage counts per language,
- alignment-exception counts.

Small green increments: Greek floor green before Hebrew starts; one book green
before the rest. Nothing claimed done until `validate_morph.py` passes and counts
are pinned.

## Out of scope

L2b relation-graph, L3 syntax, L4/L5 graph, and the translation-composition
engine are all deferred to their own specs. This spec ships only L1 + L2a for NT
Greek and OT Hebrew, with the DB projection over them.
