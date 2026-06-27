# LXX Integration — Design Spec

**Date:** 2026-06-27
**Status:** Approved (brainstorming complete)
**Repo:** `~/matt/bible`

## Purpose

Add the Septuagint (LXX, the ancient Greek translation of the Hebrew Old
Testament) to the corpus as a tagged, MT-aligned text. Its primary motivation is
to provide an **attested cross-language bridge**: a Hebrew word maps to the Greek
word the LXX translators used to render it — far cleaner than gloss/WordNet
pivoting. This bridge is consumed by the next sub-project (L2b lemma
relation-graph) for high-confidence Greek↔Hebrew edges.

LXX integration is a **precursor** to L2b. It produces a corpus + morphology +
MT↔LXX alignment artifact; it does **not** build lemma relation edges (that is
L2b).

## Roadmap context

The morpho-lexical floor (L1 morphology + L2a lexicon + `tokens.sqlite`) is built
and merged. The deferred stack: **LXX integration (THIS SPEC) → L2b lemma
relation-graph → L3 syntax → L4/L5 argument/theology/paradox graph**. L2b was
going to be next, but cross-language edges want the LXX bridge, so LXX is pulled
ahead as the precursor.

## Scope

**Full Greek OT (LXX): protocanon + deuterocanon.**

- **Protocanon** (~39 books with a Hebrew MT counterpart): corpus + morphology +
  **MT↔LXX alignment**.
- **Deuterocanon** (Greek-only books: Tobit, Judith, I–IV Maccabees, Sirach,
  Wisdom, Baruch, additions, etc.): corpus + morphology only. No MT counterpart
  exists, so no alignment — these get Greek text + morph tags, nothing more.

**Out of scope (deferred to their own specs):**

- L2b lemma relation edges (synonym/antonym/cognate/domain-sibling/etymology) —
  L2b consumes this spec's alignment artifact; it does not live here.
- L3 syntax, L4/L5 graph.

## Apocrypha coexistence

Another agent is concurrently producing `bible/apo/` — the Authorized
KJV-with-Apocrypha (KJVA) spine with English (KJV) and Finnish (Biblia 1776)
columns. The LXX deuterocanon covers the same books but is a **different
tradition** (Greek text, LXX versification).

Resolution: the LXX lives in its **own `bible/lxx/` tree**, structurally separate
from `bible/apo/`. A deuterocanonical book appears in both — Greek in `lxx/`,
English/Finnish in `apo/` — as parallel traditions, exactly as a protocanon book
appears in both MT (`bible/ot/`) and LXX (`bible/lxx/`). The only shared surface
is `data/books.json` (book codes and names): reuse the codes the Apocrypha agent
already added (TOB, JDT, 1MA, …) and extend with any LXX-specific books. L0 (MT
Hebrew, TR Greek) is never modified. Integration proceeds in an isolated worktree
and merges with the same care the floor used.

## Architecture: two-form, additive, maximal reuse

Mirrors the floor (sources are truth; derived artifacts are generated). The LXX is
a new edition/corpus driven by a registry row; the engines stay edition-agnostic.

```
CANONICAL (truth, generated from sources)            DERIVED (built, queryable)
  bible/lxx/<CODE>/NNN.json      ── LXX text ──┐
  morph/lxx/<CODE>/NNN.conllu    ── LXX morph ─┤
  align/mt-lxx/<CODE>/NNN.json   ── alignment ─┼──► tools.build_db ──► data/tokens.sqlite
  lexicon/grc/*.json (extended)  ── lexicon ───┘     (+lxx tokens, +mt_lxx table)
  bible/ (MT, TR — NEVER mutated)
```

Reuse from the floor:

- **Greek morphology decoder** — `morph_feats.decode(code, "grc")` already exists
  (built for the NT). The LXX is Greek; it reuses the decoder unchanged.
- **Alignment engine** — `align_morph.py` (FORM-from-L0, K=2 resync, `Align=`
  markers) aligns the tagged-LXX source onto `bible/lxx/` text exactly as it
  aligns TAGNT onto the NT.
- **Lexicon** — LXX Greek lemmas join the existing `lexicon/grc/` by lemma →
  Strong's; LXX-only vocabulary extends `lexicon/grc/` additively (no fabricated
  Strong's; lemma-keyed where no Strong's exists).
- **Generator/validator pattern** — registry-driven, scheme-parametric.

## Data sources (Task-0 research/license gate)

A **Task 0 spike** verifies every source and license before any code, exactly as
the floor's Task 0 did. PD / CC-BY only; restricted-license sources are rejected
and the fallback recorded. Four data problems:

### 1. LXX text + morphology

A morphologically-analyzed LXX (Greek text + lemma + morph code). Candidates,
best open one chosen in Task 0:

- **MACULA Septuagint** (Clear Bible, CC-BY) — preferred if coverage is complete
  (already our domain-data provider).
- **CATSS / CCAT** Rahlfs-based LXX morphology — verify redistribution terms
  (scholarly license may restrict).
- **STEPBible** tagged LXX, if available, CC-BY.
- **Swete** (PD, 1909) — text only; would need separate morph tagging.

Morph codes are decoded by the existing Greek decoder; if the chosen source uses a
different Greek code scheme than TAGNT/Robinson, Task 0 documents it and the
decoder gains a source-tagged mapping (additive).

### 2. Strong's linkage

The LXX is not natively Strong's-tagged. Each LXX lemma maps to a Greek Strong's
via the existing `lexicon/grc/` lemma index. LXX-only lemmas (no Strong's) get
lemma-keyed lexicon entries added to `lexicon/grc/` — no fabricated Strong's. LXX
morph tokens carry `Strong=` in MISC where resolvable, lemma only otherwise.

### 3. MT↔LXX word alignment (the cross-language payload)

The standard is the **CATSS / Tov Hebrew-Greek parallel alignment** (verify
redistribution) or an open **MACULA MT↔LXX alignment** if available. Output
artifact `align/mt-lxx/<CODE>/NNN.json` maps each MT Hebrew word (by Strong's /
ref) ↔ the LXX Greek word(s) rendering it (by Strong's / lemma / ref). If no open
word-level alignment exists, the fallback is verse-level lemma co-occurrence,
flagged lower-confidence. Coverage is pinned. Protocanon only.

### 4. LXX↔MT versification

LXX numbering diverges (Psalms offsets, Jeremiah reordering, Greek-Esther and
Greek-Daniel additions). A LXX↔MT verse map is required for alignment and for
honest verse placement. **Reuse STEPBible TVTMS** (already in the repo) if it
carries LXX traditions; otherwise a small hand-authored CC0 supplement. Same
`refs` divergence/absent discipline as the existing OT corpus.

## Repo layout

```
bible/lxx/<CODE>/NNN.json          LXX Greek text, LXX versification
morph/lxx/<CODE>/NNN.conllu        LXX morphology (reuses grc decoder)
align/mt-lxx/<CODE>/NNN.json       MT↔LXX word alignment (protocanon only)
data/versification/lxx-*.json      LXX↔MT verse map (TVTMS-derived + supplement)
data/morph-sources.json            +1 row: lxx (lang=grc, source=tagged-LXX)
data/books.json                    extend: LXX book codes/order (reuse apo codes)
lexicon/grc/*.json                 extended additively with LXX-only lemmas
data/tokens.sqlite                 +lxx tokens, +mt_lxx alignment table (derived)
docs/FORMATS-lxx.md                Task-0 output: source layouts + licenses
tools/sources/<lxx_backend>.py     new source backend (Task 0's chosen source)
tools/generate_lxx.py              emit bible/lxx/ from the source
tools/align_mt_lxx.py             build align/mt-lxx/ artifact
tools/validate_lxx.py             LXX corpus structural + versification oracles
tools/validate_morph.py            extend: LXX morph coverage pins
tools/build_db.py                  extend: load LXX tokens + mt_lxx table
tests/                             per-tool tests
```

Tools extend the existing registry-driven, scheme-parametric pattern — LXX is
data rows plus one source backend, not a parallel code fork.

## Testing

TDD, pinned counts, incremental-verified MO. Per-book green before full corpus;
Greek-decoder reuse means the morph stage should green quickly. Oracles pin:

- LXX verse coverage (per the chosen edition's book/chapter/verse counts),
- FORM ↔ `bible/lxx/` text reconciliation for every morph token,
- LXX morph coverage (tagged vs exception tokens) + Strong's-link coverage,
- MT↔LXX alignment coverage for protocanon (pinned; honest partials),
- LXX↔MT versification oracles (known divergences: Psalms, Jeremiah, Esther,
  Daniel).

Restricted or partial sources are logged with pinned coverage, never silently
dropped.

## Boundary

This spec ends when the LXX is a tagged, MT-aligned corpus. It produces no lemma
relation edges. The **L2b lemma relation-graph** is the next spec and consumes the
`align/mt-lxx/` artifact (and the `mt_lxx` DB table) as its high-confidence
cross-language edge source, alongside derived within-language edges, an authored
CC0 overlay, and (lower-confidence) Open English WordNet mining.
