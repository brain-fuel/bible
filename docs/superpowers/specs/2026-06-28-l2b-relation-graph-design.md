# L2b Lemma Relation-Graph — Design Spec

**Date:** 2026-06-28
**Status:** Proposed (awaiting approval)
**Repo:** `~/matt/bible`

## Purpose

Build the layer above the morpho-lexical floor + LXX: a **many-valued relation
graph between lemmas**. Edges connect dictionary headwords (lemmas) by meaning
and origin — synonym, antonym, cognate/shared-root, semantic-domain sibling, and
attested cross-language (Hebrew↔Greek) equivalence. Each edge carries
**provenance** (which canon / calculation / projection produced it) and an integer
**rank** (a `0..65535` quality score). This is the substrate the later
argument/theology/paradox graph
(L4/L5) walks to find connections, contrasts, and conceptual bridges across the
whole corpus and across languages.

## Roadmap context

Stack: **L0 text → L1 morpho-lexical → L2a lexicon → [LXX precursor] → L2b
relation-graph (THIS SPEC) → L3 syntax → L4/L5 argument/theology/paradox graph.**
The floor (L1+L2a) and the LXX precursor are built and merged. L2b consumes the
floor's `senses`/`domains`/`root` hooks and the LXX `mt_lxx` bridge.

## Scope (full L2b, one build)

Five relation types, **all many-valued and never capped** (a word with N
domain-siblings keeps all N; a word with multiple etymological origins keeps every
origin edge; antonyms/synonyms are not limited to one):

1. **domain-sibling** — lemmas sharing a semantic-domain code (Louw-Nida for grc,
   SDBH for hbo). Derived from the floor `domains` hook.
2. **shared-root** (cognate) — lemmas sharing a Strong's `root` pointer. Derived.
3. **cross-language** — Hebrew↔Greek translational equivalence, projected from the
   shipped `mt_lxx` bridge (weighted by `cooccur` / exact-ratio).
4. **synonym** — near-equivalence. Authored CC0 overlay + mined from public-domain
   / CC-BY dictionaries and thesauri (English, Greek, Hebrew, Latin) + Open
   English WordNet.
5. **antonym** — opposition. Authored CC0 overlay + thesaurus/WordNet pointers.

**Out of scope (own later specs):** L3 syntax (the CoNLL-U HEAD/DEPREL columns
stay empty), L4/L5 argument/theology/paradox graph, and the translation-authoring
feature. L2b produces the relation graph; it does not interpret it.

## Lemma-key model

Edges connect **lemma keys**, reusing the floor/LXX identifiers already in the DB:

- `G####` / `H####` — Strong's-keyed lemmas (the lexicon PK).
- `lemma-<sha1[:12]>` — the slug key for the 10,133 null-strong LXX-only lemmas
  (already in `lexicon/grc/lemma-*.json`, indexed by `idx_lexicon_lemma`).

Every edge endpoint is one of these keys, so the graph joins cleanly to
`lexicon`, `tokens`, and the LXX corpus. Cross-language edges connect an `H####`
to a `G####`.

## Provenance model (core requirement)

Every edge records **where it came from** and how, so hand-authored truth,
mechanical derivation, projection, and lower-confidence mining are always
distinguishable and auditable:

```json
{
  "src": "G0026",
  "dst": "G0025",
  "rel": "shared-root",
  "directed": false,
  "provenance": { "source": "strongs-root", "method": "derived" },
  "rank": 65535,
  "note": null
}
```

- `rel` ∈ {`domain-sibling`, `shared-root`, `cross-language`, `synonym`, `antonym`}.
- `method` ∈ {`authored`, `derived`, `projection`, `mined`}.
- `source` — the specific canon/calc, e.g. `louw-nida`, `sdbh`, `strongs-root`,
  `mt-lxx-bridge`, `open-english-wordnet`, `roget-1911`, `bdb`, `abbott-smith`,
  `lewis-short`, `hand`.
- `rank` — an unsigned **16-bit integer quality score, `0..65535` (2^16 − 1)**.
  This is the single filter/sort key (a quantized confidence). It is how the
  graph is "materialize everything, filter by quality" rather than "drop weak
  edges": every edge is kept and committed; weak ones simply get a low `rank`.
  Per relation:
  - exact derivations (`shared-root`, authored edges) → `65535`.
  - `domain-sibling` → ranked by **code specificity**: a finest-subdomain match
    (`25.43`) ranks high; a same-top-level-only match (`25`) ranks low. All
    granularities are materialized; the rank encodes how tight the sibling link is.
  - `cross-language` → ranked from the `mt_lxx` signal: a monotone quantization of
    `exact_ratio × log(cooccur)` onto `0..65535`. A `cooccur=1` verse-noise pair
    gets a near-zero rank but is still kept.
  - `mined` (synonym/antonym) → source prior × gloss-match tightness, quantized.
  The exact rank functions are pinned in Task code with unit tests.
- `directed` — `false` for symmetric relations (synonym, antonym, shared-root,
  domain-sibling); cross-language edges are stored once per `(H,G)` with
  `directed:false` (the pair is the fact) — direction of translation is recoverable
  from `mt_lxx` if needed.
- **Many-valued, never capped:** multiple edges may share a `(src, rel)`; nothing
  is deduped to one and no per-word count limit is ever applied. Multi-origin
  lemmas keep every origin edge.

## Storage architecture (two-form, scalable)

Mirrors the floor: **canonical line-oriented JSONL is truth; the DB relations
table is a derived projection.** Edges are materialized as committed canonical
files (git-diffable, auditable, each tagged with provenance) — but split so that
hand truth is never clobbered by regeneration and so high-cardinality derived
sets stay tractable:

```
relations/authored/<rel>.jsonl     CANONICAL, hand-edited CC0 truth (synonym, antonym, …).
                                   Never overwritten by a builder. The curated overlay.
relations/derived/<rel>.jsonl      CANONICAL but REGENERATED by builders from floor data +
                                   bridge + mined sources. Committed for auditability;
                                   rebuilt deterministically. Provenance = derived/projection/mined.
data/relations.sqlite (or +tokens.sqlite)   DERIVED projection: `relations` table over ALL
                                   the above, indexed for query. Gitignored, rebuildable.
```

One JSONL line per edge, sorted deterministically (by `src`, `rel`, `dst`,
`source`) so regenerated files diff cleanly.

### Rank, not drop (materialize everything; filter by quality)

Every derivable edge is **materialized and committed** — including the
combinatorially large, low-signal ones (full cross-language bridge incl.
`cooccur=1`; domain-sibling pairs at every code granularity). Nothing is dropped.
The size and noise are tamed by the integer **`rank`** field (`0..65535`), not by
deletion:

- Each edge gets a `rank` quantizing its quality (see the rank rules above):
  exact derivations max out; `domain-sibling` ranks by code specificity;
  `cross-language` ranks by the `mt_lxx` signal so `cooccur=1` pairs sit near the
  bottom; mined edges rank by source prior × match tightness.
- A single pinned constant **`DEFAULT_RANK_THRESHOLD`** reproduces the "bounded
  default" view: the DB exposes a default filtered view `WHERE rank >=
  DEFAULT_RANK_THRESHOLD` (and the canonical files carry the full set). Raising the
  threshold narrows to the highest-confidence graph; lowering it (to 0) returns
  everything. The threshold is configuration, not a cap — it filters quality, never
  a word's edge count.
- The full materialized derived set is committed as line-oriented JSONL (compact,
  git-diffable). Per-relation edge counts and the rank distribution are pinned so
  growth is visible and honest. (Order-of-magnitude expectation: cross-language
  ~hundreds of thousands of lines; domain-sibling bounded by subdomain sizes;
  shared-root small. These are committed canonical data, like `bible/lxx`.)

## Sources (PD / CC-BY only; Task-0 verify gate)

A Task-0 license/format spike (as in the floor and LXX) verifies every source
before code. Already-present, no new fetch: **Louw-Nida domains** (grc),
**SDBH domains** (hbo), **Strong's `root`**, the **`mt_lxx` bridge**. New mining
sources to verify (PD or CC-BY only; reject NC/closed):

- **Open English WordNet** (CC-BY 4.0) — English synonym/antonym synsets.
- **Roget's Thesaurus, 1911** (Public Domain) — English synonym/antonym groupings.
- **Abbott-Smith** (PD, already in floor) — Greek cross-references in entries.
- **BDB** (PD, already in floor) — Hebrew cross-references / "compare" notes.
- **Lewis & Short Latin Dictionary** (PD) — Latin synonym/related-word links;
  bridges via the lemma's Latin/Vulgate gloss. (verify obtainable cleanly)
- **Gesenius / LSJ** (PD) — Hebrew / Greek lexica, if a clean PD machine-readable
  edition is available (verify; otherwise deferred).

### Bridging method (how multilingual thesauri reach grc/hbo lemmas)

Each lemma already carries multilingual `glosses` (lang-keyed, with `src`). The
miner walks: **lemma → its glosses (en/la/…) → match each gloss term against a
thesaurus/WordNet headword or synset → collect that headword's synonyms/antonyms
→ map back to every lemma whose gloss contains those terms.** The resulting edge
is `method:"mined"`, `source:"<that thesaurus>"`, with confidence lowered for
loose/multi-word gloss matches. Authored CC0 edges override/augment mined ones;
both coexist (many-valued), distinguished by provenance.

## Derived DB

`build_db` (or a sibling `build_relations`) loads every `relations/**/*.jsonl`
into a `relations` table:

```
relations(src, dst, rel, directed, source, method, rank, note)
  indexes: (src), (dst), (rel), (src, rel), (rank)
  view relations_default = SELECT * FROM relations WHERE rank >= DEFAULT_RANK_THRESHOLD
```

Unlocks: "all synonyms/antonyms of X" (one `WHERE src=? AND rel=?`); "Hebrew word
→ its attested Greek equivalents" (`rel='cross-language'`, ordered by `rank`);
"every word in the same Louw-Nida subdomain"; multi-hop conceptual paths (graph
walk in SQL/app); and honest provenance + `rank` filtering for downstream L4/L5
(default view = high-quality; raise/lower the threshold per use).

## Testing

TDD, pinned counts, incremental-verified MO (the floor/LXX discipline). Per
builder: a unit test on the derivation logic with a tiny fixture, then a
corpus-level oracle pinning edge counts per relation + per source. Validate:
every edge endpoint resolves to a lexicon key; no self-loops; symmetric relations
stored consistently; `provenance.source`/`method`/`rank` present on every edge and
`rank` in `0..65535`; rank functions unit-tested (a `cooccur=1` cross-language pair
ranks below `DEFAULT_RANK_THRESHOLD`, a finest-subdomain sibling ranks above a
top-level-only one); per-relation edge counts + rank-distribution + the
default-view count pinned; deterministic regen (derived JSONL rebuilds
byte-identical). Restricted/partial sources logged with pinned coverage, never
silently dropped.

## Licensing

Per the repo policy (`docs/LICENSING.md`): builder **code = AGPL-3.0**; the
**authored CC0 overlay = CC0**; **derived edges inherit the most-restrictive
license of their inputs** — edges from Louw-Nida/SDBH/`mt_lxx` (CC-BY via
STEPBible/MACULA) are CC-BY; edges from PD sources (Roget/Abbott-Smith/BDB/Lewis
& Short) are CC0/PD; Open-English-WordNet-mined edges are CC-BY. The per-edge
`provenance.source` makes each edge's license mechanically traceable.

## Boundary

L2b ends at the relation graph: lemma↔lemma edges with provenance + `rank`,
canonical + queryable. It does not build syntax (L3) or argument/theology/paradox
structure (L4/L5) — those are later specs that consume this graph. No relation is
capped; every edge is provenance-tagged and license-traceable.
