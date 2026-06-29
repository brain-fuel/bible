# bible

The Bible as structured JSON, one file per chapter, with multiple parallel texts per verse. New Testament: Latin Vulgate, Greek Textus Receptus, and English King James. Old Testament: Latin Vulgate, Hebrew Masoretic (full pointing), and English King James. Verse-by-verse alignment across traditions.

## Layout

    bible/<testament>/<CODE>/<NNN>.json

`testament` is `nt` (New Testament) or `ot` (Old Testament); `apo` is reserved for apocrypha. `CODE` is the canonical uppercase three-character book code. `NNN` is the chapter, zero-padded to three digits so every book (including Psalms with 150 chapters) sorts consistently.

## Schema

### New Testament Verse

    {
      "verse": 1,
      "latin_vulgate": "...",
      "greek_textus_receptus": "...",
      "king_james": "..."
    }

### Old Testament Verse

    {
      "verse": 1,
      "latin_vulgate": "...",
      "hebrew_masoretic": "...",
      "king_james": "...",
      "refs": {
        "hebrew_masoretic": { "src": "1:1" },
        "latin_vulgate": { "absent": true }
      }
    }

#### Schema notes

- The OT `verse` field uses KJV versification for all traditions.
- The `refs` field is present only when a tradition diverges, and is keyed by edition id with a uniform per-edition object:
  - `refs.<edition>.src` — the source `"chapter:verse"` when that edition's versification places the verse elsewhere than KJV numbering (e.g. Hebrew psalm titles, the Latin psalter).
  - `refs.<edition>.absent: true` — the edition has no text at that position (the edition's column is empty). Ten KJV verses are absent in the Clementine Vulgate; no Hebrew verse is currently absent.
  - Both keys can appear together for one edition (relocated *and* empty). The base edition (KJV) never appears in `refs`.
- Hebrew text includes full Masoretic pointing (vowels and cantillation marks), normalized to NFC form.

## Edition System

Each parallel text is registered in `data/editions.json`. A row is self-describing and **drives generation by itself** — the OT pipeline names no edition. A row carries:

- `id` — the verse-column key (and header is taken from `display_name_field`).
- `source` — `{ "type": ..., ... }`; `type` selects a source backend (`scrollmapper`, `sefaria`) via `tools/sources/registry.py`.
- `book_name_field` — which `data/books.json` field holds this source's per-book name.
- `vmap_key` — the versification namespace in `data/versification/ot-versification.json` (omitted for the base edition, which defines verse positions).
- `base: true` — the edition that defines verse positions (KJV). Non-base editions render first; the base renders last.

**Adding a new parallel OT text needs only a registry row** (plus the source's per-book name in `data/books.json`, and a cache/network fetch). The generator (`tools/generate_ot.py`), merge engine (`tools/merge_ot.py`), and validator (`tools/validate_ot.py`) iterate the registry and need no per-edition edits. Only a genuinely new *source backend* (a `source.type` not yet handled) requires one new class in `tools/sources/registry.py`.

### Apocrypha (`bible/apo/`)

The Apocrypha use the Authorized KJV-with-Apocrypha (Scrollmapper `KJVA`) as the
verse-position spine — 14 books, 5,717 verses, Greek/KJV-family versification, so
the English column stays KJV across the whole corpus. A second column carries the
Finnish Biblia 1776 (`FinBiblia`).

Cross-edition apocrypha alignment is **identity placement with no versification
map**: TVTMS treats KJVA and Biblia 1776 as the same tradition and provides no
verse map between them, so none is fabricated. Where Biblia 1776 has no text the
verse is marked `refs.finnish_biblia.absent`. Biblia 1776 ships empty placeholders
for I/II Esdras and a different Greek-Esther unit than KJV's "Additions to Esther",
so those three books are fully Finnish-absent; total Finnish-absent is 1,505 verses.

The Latin/Vulgate and Douay-Rheims Apocrypha belong to a different versification
family (e.g. Sirach diverges in 48 of 51 chapters, and the Daniel/Esther additions
are embedded rather than separate books) with no map in our sources — a future plan.

## Sources

All underlying texts are in the public domain:

- **King James Version** (1611): Sourced from Scrollmapper's bible_databases datasets.
- **Clementine Vulgate** (Latin, 1592): Sourced from Scrollmapper's bible_databases datasets. Ten OT verses are merged into the preceding verse in the Vulgate tradition (recorded as `refs.latin_vulgate.absent`).
- **Douay-Rheims (Challoner)** (English, 19th c. revision): Sourced from Scrollmapper's `DRC` dataset. Follows Vulgate versification, so it reuses the same KJV→Vulgate map as the Clementine Vulgate (`vmap_key: "latin"`); thirteen KJV verses are merged/absent in the Douay tradition.
- **Hebrew Masoretic Text** (Westminster Leningrad Codex): Sourced via the Sefaria API. Includes full Masoretic pointing with vowels and cantillation marks.
- **Biblia 1776** (Finnish, 1776): Sourced from Scrollmapper's `FinBiblia` dataset. Already KJV-versified for the protocanon, so it is placed by identity with no versification map.
- **Greek Textus Receptus** (NT only): Sourced from the Logos Apostolic interlinear (https://www.logosapostolic.org/bibles/latin_vulgate_textus_receptus_king_james/).
- **Swete 1909 Greek Old Testament** (Septuagint / LXX): H. B. Swete, *The Old Testament in Greek* (1909). Public Domain by age. Sourced as PD text, not from any GPL repackaging.

The morpho-lexical layer adds the following sources (see the Morpho-Lexical Floor section below):

- **STEPBible TAGNT** (Translators Amalgamated Greek NT), **TAHOT** (Translators Amalgamated Hebrew OT), and **TBESG** (Translators Brief Exhaustive Strong's Greek): CC BY 4.0, produced by STEPBible and Tyndale House Cambridge. Supply per-word lemma, morphology, Strong's numbers, and English glosses for the NT Greek and OT Hebrew. Credit STEPBible and link to https://github.com/STEPBible.
- **MACULA Greek and Hebrew Linguistic Datasets** (Clear Bible Inc.): CC BY 4.0. Supplies Louw-Nida section references (Greek) and SDBH LexDomain codes (Hebrew) for semantic domains. https://github.com/Clear-Bible/macula-greek and https://github.com/Clear-Bible/macula-hebrew.
- **Strong's Exhaustive Concordance** Greek and Hebrew dictionaries (James Strong, 1890): Public Domain. XML encoding by Ulrik Petersen / openscriptures. https://github.com/openscriptures/strongs.
- **openscriptures GreekResources LxxLemmas** (Open Scriptures Septuagint Project, David Troidl): CC BY 4.0. Supplies per-word Greek lemmas and the lemma-to-Strong's join for the LXX corpus. https://github.com/openscriptures/GreekResources.
## Versification Mapping and Attribution

The OT cross-tradition verse alignment is derived from **STEPBible's TVTMS** (Translators Versification Traditions Mapping System), produced by Tyndale House Cambridge. This data is licensed CC BY 4.0. A small hand-authored CC0 supplement (`data/versification/ot-versification-supplement.json`) aligns the Decalogue chapters (Exodus 20, Deuteronomy 5) to the Sefaria verse division.

The LXX versification map (`data/versification/lxx-versification.json`) is derived from the same TVTMS file's Greek/LXX tradition column (CC BY 4.0). A companion CC0 supplement (`data/versification/lxx-versification-supplement.json`) covers chapter-level reorderings and integrated additions that TVTMS does not model at the verse level: Jeremiah chapter reorder, Greek Esther additions A-F, and Greek Daniel integrated books.

**Credit STEPBible and link to** https://github.com/STEPBible when using this compilation.

## License

This project mixes three license regimes by artifact type. See
[`docs/LICENSING.md`](docs/LICENSING.md) for the authoritative, per-artifact map.

- **Software** (everything under `tools/`, build scripts, tests):
  **AGPL-3.0-or-later** — see [`LICENSE`](LICENSE).
- **Content, default**: **CC0-1.0** public-domain dedication
  ([`licenses/CC0-1.0.txt`](licenses/CC0-1.0.txt)). Covers the original
  compilation/schema, the hand-authored CC0 versification supplements, the
  public-domain biblical text corpora (Westminster Leningrad Codex, Clementine
  Vulgate, King James Version, Swete 1909 Greek OT), and the Strong's dictionary
  spine.
- **Content derived from CC-BY sources**: **CC-BY-4.0**
  ([`licenses/CC-BY-4.0.txt`](licenses/CC-BY-4.0.txt)), attribution required:
  - STEPBible **TVTMS** versification, and **TAGNT / TAHOT / TBESG / TAGOT**
    morpho-lexical data — STEPBible.org, Tyndale House Cambridge, CC-BY 4.0.
  - **MACULA** Greek/Hebrew semantic-domain data — Clear Bible Inc., CC-BY 4.0.
  - **openscriptures LxxLemmas** Septuagint lemmas — David Troidl, CC-BY 4.0.

Where a single datum combines a public-domain value with a CC-BY tag, the CC-BY
attribution above applies. Every generated datum carries `src`/`sources`
provenance so its governing license is traceable.

## Regenerate

### New Testament

Generate NT chapters from the Logos Apostolic interlinear:

    python -m tools.generate

Validate structure and pin output against the independently produced james JSON:

    python -m tools.validate

### Old Testament

Generate the OT versification map from STEPBible data and Sefaria sources:

    python -m tools.tvtms

Generate OT chapters:

    python -m tools.generate_ot

Validate OT structure. This checks all 23,145 OT verses, contiguity, non-empty verse bodies (except marked-absent), and alignment against versification oracles:

    python -m tools.validate_ot

### Apocrypha

Generate Apocrypha chapters:

    python -m tools.generate_apo

Validate Apocrypha structure:

    python -m tools.validate_apo

Raw sources are cached in `data/cache/` (gitignored).

### Septuagint (LXX)

Generate the LXX corpus from the Swete 1909 PD text (requires Swete CSVs in `data/cache/morph/raw/lxx/`):

    python -m tools.generate_lxx            # -> bible/lxx/   (Swete PD)

Normalize LxxLemmas to the intermediate TSV (requires openscriptures JS files in `data/cache/morph/raw/lxx/lxxlemmas/`):

    python -m tools.morph_norm.lxx          # -> data/cache/morph/lxx.tsv  (lemmas + Strong's join)

Generate CoNLL-U morphology files for the LXX (lemma + Strong's only; UPOS/XPOS/FEATS intentionally empty):

    python -m tools.generate_morph --testament lxx   # -> morph/lxx/

Validate LXX structure and morphology coverage:

    python -m tools.validate_lxx
    python -m tools.validate_morph lxx

Build lexicon (adds LXX-only lemma-keyed entries to `lexicon/grc/`):

    python -m tools.build_lexicon           # + LXX-only lemmas

Rebuild the derived MT<->LXX bridge and token database (both are gitignored):

    python -m tools.align_mt_lxx            # -> data/cache/mt-lxx-bridge.jsonl (derived aggregate)
    python -m tools.build_db                # -> data/tokens.sqlite (+ lxx tokens + mt_lxx table)

Raw source caches are in `data/cache/morph/raw/lxx/` (gitignored). See the Septuagint Layer section for artifact details.

### Morpho-Lexical Layer

Normalize STEPBible morphological data to the intermediate TSV format (requires raw STEPBible files in `data/cache/morph/raw/`):

    python -m tools.morph_norm.stepbible_greek      # raw -> data/cache/morph/grc.tsv
    python -m tools.morph_norm.stepbible_hebrew     # raw -> data/cache/morph/hbo.tsv

Generate canonical CoNLL-U morphology files:

    python -m tools.generate_morph                  # -> morph/**/*.conllu

Validate against the L0 corpus and pinned coverage oracles:

    python -m tools.validate_morph nt && python -m tools.validate_morph ot

Build MACULA semantic domain maps (downloads once, cached in `data/cache/`):

    python -m tools.fetch_macula                    # -> cached MACULA domain maps

Build lexicon entries from Strong's + TBESG + MACULA domains:

    python -m tools.build_lexicon                   # -> lexicon/**/*.json

Build the derived SQLite token database:

    python -m tools.build_db                        # -> data/tokens.sqlite

## Morpho-Lexical Floor

The morpho-lexical layer adds per-word lemma, morphology, Strong's numbers, lexicon entries, and semantic domains to the L0 verse corpus. It uses a two-form architecture: canonical hand-editable source files (version-controlled) and a derived projection (gitignored, rebuildable).

### Two-Form Architecture

**Canonical artifacts** (version-controlled, human-editable):

- `morph/<testament>/<CODE>/NNN.conllu` (L1) — CoNLL-U files; one file per chapter, one sentence per L0 verse, one token row per word. Each token carries FORM (from L0), LEMMA, XPOS (raw STEPBible morph code), FEATS (CoNLL-U features, reserved for future expansion), and MISC fields including `Strong=G####` (Strong's number), `Translit=...` (transliteration), and `Align=matched|unmatched` (alignment status). Mismatches between the L0 surface and the STEPBible text are marked `Align=unmatched` rather than silently dropped.
- `lexicon/<lang>/<STRONG>.json` (L2a) — one JSON entry per Strong's number present in the corpus (Greek under `lexicon/grc/`, Hebrew under `lexicon/hbo/`). Each entry carries: `strong`, `lemma`, `translit`, `lang` (ISO 639-3), `pos`, `glosses` (language-keyed map; currently English only), `senses` (one per gloss), `domains` (sorted atomic domain codes), `root` (Strong's ID of root word, or null), and `sources` (list of source labels that contributed data).

**Derived projection** (gitignored, rebuilt from canonical files):

- `data/tokens.sqlite` — SQLite database built from `morph/` + `lexicon/` + L0 corpus. Holds no truth the canonical files lack; delete and rebuild at any time. Supports four query classes: concordance (all verses containing a given Strong's), thesaurus (Strong's numbers sharing a semantic domain), cross-translation (L0 verse text alongside lemma and gloss), and morphological queries (verses filtered by FEATS pattern).

**Registry**:

- `data/morph-sources.json` — one entry per language; drives normalization, alignment, and lexicon building. Each row specifies the language code, testament, L0 field name, normalized TSV path, edition filter, and domain source label. Adding a new language requires only a new registry row; the generator and validator need no per-language edits.

### Coverage

| Dimension | NT (Greek) | OT (Hebrew) |
|-----------|-----------|-------------|
| Verses | 7,957 | 23,145 |
| Tokens | 140,610 | 312,079 |
| Unmatched tokens | 6,615 (4.70%) | 14,794 (4.74%) |

Unmatched tokens reflect genuine surface divergence between the L0 corpus (Textus Receptus / Westminster Leningrad Codex) and the STEPBible alignment text; they are not errors. Only unmatched tokens lack a `Strong=` field by design.

**Lexicon**: 13,548 entries total (5,122 Greek + 8,426 Hebrew).

| Dimension | Greek | Hebrew |
|-----------|-------|--------|
| Entries | 5,122 | 8,426 |
| English-gloss coverage | ~99% | ~99% |
| Semantic domain coverage | 99.2% (Louw-Nida) | 89.8% (SDBH) |

Greek semantic domains use Louw-Nida section references (e.g. `"25.43"`) sourced from the MACULA Greek Nestle1904 TSV (`ln` column). Hebrew semantic domains use SDBH LexDomain hierarchical codes (e.g. `"002003003004"`) sourced from MACULA Hebrew WLC node XML files. The ~10% of Hebrew strongs without SDBH codes are morphology-only entries (particles, prefixes, proper nouns) that MACULA does not classify.

### Attribution

- STEPBible TAGNT / TAHOT / TBESG: "Data created by www.STEPBible.org based on work at Tyndale House Cambridge (CC BY 4.0). Source: https://github.com/STEPBible"
- MACULA Greek / Hebrew: "MACULA Greek/Hebrew Linguistic Datasets, Clear Bible Inc., CC-BY 4.0. https://github.com/Clear-Bible/macula-greek and https://github.com/Clear-Bible/macula-hebrew"
- Strong's Greek / Hebrew dictionaries: Public Domain -- Strong's Exhaustive Concordance, James Strong 1890. XML by Ulrik Petersen / openscriptures.

## Septuagint Layer

The Septuagint (LXX) integration adds a Greek Old Testament corpus, a lemma+Strong's annotation layer, a LXX<->MT versification map, and an aggregated MT<->LXX bridge. It reuses the two-form architecture and registry-driven pipeline of the Morpho-Lexical Floor.

### Corpus: `bible/lxx/`

54 books of Swete's 1909 Greek OT (full LXX canon including deuterocanon; LXX versification). Chapter files have the same schema as the main corpus but use the `greek_lxx` field for the verse text. Protocanon books include a `refs.mt` field (present only when the LXX verse maps to a different MT position or has no MT counterpart).

**License:** CC0-1.0 (Swete 1909 is Public Domain by age; sourced as PD text, not from any GPL repackaging).

### Morphology: `morph/lxx/`

Per-token CoNLL-U files for all 54 LXX books. Each token carries:

- `FORM` (from the LXX verse text), `LEMMA` (polytonic Greek from LxxLemmas), `Strong=G####` in MISC where the lemma joins to `lexicon/grc`.
- `UPOS`, `XPOS`, `FEATS` are intentionally **empty** (`_`). No open LXX morphology source exists today; these columns backfill automatically when STEPBible TAGOT (CC-BY) releases by flipping the registry `morph_scheme` entry and rerunning `generate_morph --testament lxx`.
- `Align=matched|unmatched` records whether the surface form was found in the LxxLemmas word list for the verse.

**License:** CC-BY-4.0 (derived from openscriptures LxxLemmas, David Troidl, CC-BY 4.0 -- see `docs/LICENSING.md`).

### LXX<->MT Versification

`data/versification/lxx-versification.json` is derived from the Greek/LXX tradition column of STEPBible TVTMS (CC-BY 4.0). `data/versification/lxx-versification-supplement.json` (CC0) covers chapter-level structural differences not modeled at the verse level by TVTMS: Jeremiah chapter reorder (LXX ~1/8 shorter; Oracles Against the Nations relocated), Greek Esther additions A-F, and Greek Daniel integrated books (Susanna, Song of the Three, Bel).

### MT<->LXX Bridge (derived, gitignored)

`data/cache/mt-lxx-bridge.jsonl` and the `mt_lxx` DB table are **derived projections** (rebuildable, not committed). They aggregate verse-level co-occurrence of Hebrew Strong's (H####) and Greek Strong's / lemmas across protocanon LXX-MT verse pairs.

Each bridge row carries: `mt_strong`, `lxx_strong`, `lxx_lemma`, `cooccur` (verse-pair count), `exact` (positional-match verse-pairs), `positional` (word-index-ratio match verse-pairs). This is **verse-level co-occurrence, not word-level alignment** -- no open CC-BY/PD word-level MT<->LXX alignment exists. Consumers should weight pairs by `exact / cooccur` ratio; low-count pairs are noise. The bridge is the cross-language handoff for future L2b relation-graph work.

**Coverage:** 691,240 aggregate rows; protocanon books only (deuterocanon has no MT counterpart).

### Deferred (open-source gated)

**Full LXX morphology** (UPOS/XPOS/FEATS) awaits STEPBible TAGOT (CC-BY 4.0), announced but not yet released. When TAGOT lands it is a drop-in: same morph-code scheme as TAGNT, same normalizer, zero new decoder rules. Backfill: set `morph_scheme` in `data/morph-sources.json` to `"stepbible_greek"` and rerun `generate_morph --testament lxx`.

**Word-level MT<->LXX alignment** would upgrade the bridge from verse-level co-occurrence to attested word links, if and when an open CC-BY/PD source appears (the CATSS/Tov alignment is restricted-license and has been rejected).

See [`docs/LICENSING.md`](docs/LICENSING.md) for the per-artifact license map: `bible/lxx` is CC0; `morph/lxx` lemma+Strong's is CC-BY (openscriptures LxxLemmas); the versification map is CC-BY (TVTMS) + CC0 (supplement).

## Relation Graph (L2b)

The relation graph (L2b) adds a semantic-relation layer on top of the lexicon (L2a). It links lexical entries by five relation types, each edge carrying a rank score (0–65535) and full provenance.

### Relation Types

| Relation | Description | Edges | Orientation |
|----------|-------------|-------|-------------|
| `shared-root` | Etymological kin (same Strong's root) | 80,904 | canonical (src ≤ dst) |
| `domain-sibling` | Same Louw-Nida or SDBH semantic domain | 1,959,593 | canonical (src ≤ dst) |
| `cross-language` | MT Hebrew ↔ LXX Greek translation bridge | 691,240 | H#### → G#### (directed by design) |
| `synonym` | Synonymous meaning (WordNet, Roget, lexica cross-refs, authored) | 6,909,342 | canonical (src ≤ dst) |
| `antonym` | Antonymous meaning (WordNet, Roget, authored) | 1,955,929 | canonical (src ≤ dst) |

Total: **11,597,008** edges across all relations.

### Rank Model

Every edge carries an integer `rank` in `0..65535`. Higher rank = higher confidence / relevance.

`DEFAULT_RANK_THRESHOLD = 32768` is the default-view cut-off:

- Edges with `rank >= 32768` are in the **default view** (`relations_default` DB view): ~2,091,882 edges.
- Edges with `rank < 32768` are materialised in JSONL and the DB but excluded from the default view (low-confidence pairs such as single-verse co-occurrences or coarse domain codes).

### Two-Form Architecture

**Canonical artifacts** (version-controlled, human-editable):

- `relations/authored/synonym.jsonl`, `relations/authored/antonym.jsonl` — hand-authored CC0 truth edges (2 synonym + 2 antonym).

**Derived projection** (gitignored, deterministically regenerable):

- `relations/derived/{shared-root,domain-sibling,cross-language,synonym,antonym}.jsonl` — five canonical per-rel files produced deterministically by `tools/build_relations.py`. These files are **not committed** (gitignored). They are regenerated from version-controlled source files plus auto-downloaded cached sources. Any missing source files (WordNet LMF gz, Roget pg22.txt, BDB XML) are fetched automatically on first run.

### Rebuild From Scratch (one command)

    python -m tools.build_relations    # auto-downloads missing sources + regenerates relations/derived/*.jsonl
    python -m tools.build_db           # reload relations table + relations_default view
    python -m tools.validate_relations # pin check: all counts, provenance, orientation

`python -m tools.build_relations` is a single command that works from a clean clone with no manual setup: it fetches any missing cached source files and writes all five derived JSONL files. Rebuild is confirmed when `python -m tools.validate_relations` exits 0 with pinned counts holding.

### Attributions

- **Open English WordNet 2024** (synonym + antonym edges, source `open-english-wordnet`): "Open English Wordnet 2024, globalwordnet/english-wordnet, CC-BY 4.0, https://github.com/globalwordnet/english-wordnet. Based on Princeton WordNet (CC-BY 4.0, https://wordnet.princeton.edu)." License: **CC-BY 4.0**.
- **Roget's Thesaurus 1911** (synonym + antonym edges, source `roget-1911`): Public Domain. MICRA Inc. preparation is PD-dedicated. No attribution required. License: **CC0**.
- **Strong's Greek / Hebrew cross-refs** (synonym edges, sources `strongs-greek`, `strongs-hebrew`, `strongs-root`): "Public Domain — Strong's Exhaustive Concordance, James Strong 1890. XML by Ulrik Petersen / openscriptures." License: **CC0**.
- **Abbott-Smith via STEPBible TBESG** (synonym edges, source `abbott-smith`): "Data created by www.STEPBible.org based on work at Tyndale House Cambridge (CC BY 4.0). Source: https://github.com/STEPBible." License: **CC-BY 4.0**.
- **Brown-Driver-Briggs Hebrew Lexicon** (synonym edges, source `bdb`): "Brown-Driver-Briggs Hebrew Lexicon (1906), Public Domain. XML by openscriptures, https://github.com/openscriptures/HebrewLexicon." License: **CC0**.
- **MACULA Louw-Nida / SDBH domains** (domain-sibling edges, sources `louw-nida`, `sdbh`): "MACULA Greek/Hebrew Linguistic Datasets, Clear Bible Inc., CC-BY 4.0. https://github.com/Clear-Bible/macula-greek and macula-hebrew." License: **CC-BY 4.0**.
- **MT↔LXX bridge** (cross-language edges, source `mt-lxx-bridge`): Derived from STEPBible TAGNT/TAHOT + openscriptures LxxLemmas + Swete 1909 LXX (all CC-BY 4.0 or PD). License: **CC-BY 4.0**.
- **Hand-authored overlay** (source `hand`): CC0-1.0 public-domain dedication. License: **CC0**.
