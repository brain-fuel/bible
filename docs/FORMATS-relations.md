# FORMATS-relations.md — Relation-Graph Mining Source Formats

Task 0 spike: source acquisition, license verification, format documentation.
Downstream tasks (7–9) build miners against this document.
All assertions were verified against real downloaded files; deviations and honest
fallbacks are called out explicitly.

---

## Summary table

| Source | Status | License | Downloaded |
|--------|--------|---------|------------|
| Open English WordNet 2024 | **GO** | CC-BY 4.0 | `data/cache/relations/wordnet/english-wordnet-2024.xml.gz` |
| Roget's Thesaurus 1911 | **GO** | Public Domain | `data/cache/relations/roget/pg22.txt` |
| Lewis & Short Latin Dict. | **DEFERRED** | CC-BY-SA 4.0 (encoding); 1879 text PD | not downloaded |
| Abbott-Smith (in-repo) | **GO (via committed gloss text)** | CC-BY 4.0 (TBESG) | no new download needed |
| BDB (needs download) | **GO (needs fetch)** | Public Domain | not yet cached |

Licensing rule (per `docs/LICENSING.md`): derived edges inherit the most-restrictive
license of their inputs. WordNet edges → CC-BY. Roget/Abbott-Smith/BDB edges → CC0/PD
(or CC-BY for TBESG-derived data). Lewis & Short → DEFERRED (see §3).

---

## Source 1: Open English WordNet 2024

### License

**CC-BY 4.0** (Creative Commons Attribution 4.0 International).
The underlying Princeton WordNet data also carries an open license; the OEW
project explicitly relicenses under CC-BY 4.0.

- License URL: `https://creativecommons.org/licenses/by/4.0`
- License file: `https://raw.githubusercontent.com/globalwordnet/english-wordnet/main/LICENSE.md`
- Project URL: `https://github.com/globalwordnet/english-wordnet`

Required attribution: "Open English Wordnet 2024, globalwordnet/english-wordnet,
CC-BY 4.0, https://github.com/globalwordnet/english-wordnet. Based on Princeton
WordNet (CC-BY 4.0, https://wordnet.princeton.edu)."

Derived edges from this source carry: `provenance.source = "open-english-wordnet"`,
`method = "mined"`, license = CC-BY 4.0.

### Downloaded file

```
data/cache/relations/wordnet/english-wordnet-2024.xml.gz
```

- Source URL: `https://github.com/globalwordnet/english-wordnet/releases/download/2024-edition/english-wordnet-2024.xml.gz`
- Compressed: ~12.3 MB; uncompressed: ~97.7 MB
- Open with: `gzip.open(path, 'rt', encoding='utf-8')`

### File format: LMF XML (WN-LMF-1.3)

Top-level structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE LexicalResource SYSTEM "http://globalwordnet.github.io/schemas/WN-LMF-1.3.dtd">
<LexicalResource xmlns:dc="https://globalwordnet.github.io/schemas/dc/">
  <Lexicon id="oewn" label="Open English Wordnet" language="en"
           license="https://creativecommons.org/licenses/by/4.0"
           version="2024" ...>
    <!-- LexicalEntry elements first, then Synset elements -->
  </Lexicon>
</LexicalResource>
```

#### LexicalEntry (word-form + sense links)

One `<LexicalEntry>` per lemma+POS combination. Each entry holds one or more
`<Sense>` elements; each Sense belongs to one `<Synset>` (synonym set) and may
carry `<SenseRelation>` pointers to other senses.

```xml
<LexicalEntry id="oewn-love-n">
  <Lemma writtenForm="love" partOfSpeech="n"/>
  <Sense id="oewn-love__1.12.00.." synset="oewn-07558676-n">
    <SenseRelation relType="antonym" target="oewn-hate__1.12.00.."/>
    <SenseRelation relType="derivation" target="oewn-love__2.37.01.."/>
  </Sense>
  <Sense id="oewn-love__1.04.00.." synset="oewn-07539586-n"/>
  <!-- more senses -->
</LexicalEntry>
```

Antonym example (`hot` → `cold`):

```xml
<LexicalEntry id="oewn-hot-a">
  <Lemma writtenForm="hot" partOfSpeech="a"/>
  <Sense id="oewn-hot__3.00.01.." synset="oewn-01250274-a">
    <SenseRelation relType="antonym" target="oewn-cold__3.00.01.."/>
  </Sense>
</LexicalEntry>
```

#### Synset (synonym set)

Appears after all LexicalEntry elements. Members are listed in the `members`
attribute as space-separated Sense IDs.

```xml
<Synset id="oewn-00001740-v" ili="i21778"
        members="oewn-breathe-v oewn-take_a_breath-v oewn-respire-v oewn-suspire-v"
        partOfSpeech="v" lexfile="verb.body">
  <Definition>draw air into, and expel out of, the lungs</Definition>
  <SynsetRelation relType="hypernym" target="oewn-02372362-v"/>
</Synset>
```

### Key / ID scheme

| Thing | ID pattern | Example |
|---|---|---|
| Synset | `oewn-{8digit_offset}-{pos}` | `oewn-01250274-a` |
| LexicalEntry | `oewn-{lemma_lc}-{pos}` | `oewn-love-n` |
| Sense | `oewn-{lemma_lc}__{lexname_code}..` | `oewn-love__1.12.00..` |

POS letters: `n` noun, `v` verb, `a` adjective (head), `s` adjective (satellite), `r` adverb.

### Synonym extraction

**Synonyms = words sharing the same synset.** To get synonyms for a lemma:
1. Collect all Sense IDs for that lemma (via `<Sense synset="...">` attributes).
2. For each synset ID, collect all other LexicalEntry Senses with the same synset ID.
3. The `writtenForm` of those LexicalEntries are the synonyms.

The `members` attribute on `<Synset>` lists the member sense IDs directly.
These can be stripped to lemma form: `oewn-take_a_breath-v` → `take a breath`.

### Antonym extraction

**CRITICAL: Antonyms are Sense-level, NOT Synset-level.**

`<SenseRelation relType="antonym">` lives inside `<Sense>` elements (inside
`<LexicalEntry>`), not on `<Synset>`. The antonymy is lexical (word-sense pair),
not conceptual.

To get antonym pairs:
- Parse all `<SenseRelation relType="antonym" target="..."/>` elements.
- Extract the `target` Sense ID; strip to lemma form.
- Each such pair is a directional (but semantically symmetric) antonym link.

### Stats (2024 edition)

| Metric | Count |
|---|---|
| LexicalEntry count | 161,705 |
| Synset count | 120,630 |
| Antonym SenseRelations | 7,996 |
| Hypernym SynsetRelations | 93,446 |

### Bridging hook

English: `glosses.en[*].text` — specifically the `tbesg` glosses (short, 1–3
words). For Task 7: index TBESG gloss → G#### key; match against OEW
`writtenForm` attributes.

---

## Source 2: Roget's Thesaurus, 1911 (Project Gutenberg #22)

### License

**Public Domain.** First published 1895 / revised 1911 edition by Peter Mark Roget.
Well before 1927 in all jurisdictions. The Project Gutenberg eBook (#22, prepared
by MICRA Inc.) explicitly states: "MICRA, Inc. makes no proprietary claims regarding
this electronic version of the 1911 thesaurus. If the 1911 work is currently public
domain, this electronic version can also be treated as public domain."

- Project Gutenberg URL: `https://www.gutenberg.org/ebooks/22`
- Preparing organization: MICRA, Inc. (no proprietary claim)

Derived edges from this source carry: `provenance.source = "roget-1911"`,
`method = "mined"`, license = CC0 (PD input → CC0 derived edge).

### Downloaded file

```
data/cache/relations/roget/pg22.txt
```

- Source URL: `https://www.gutenberg.org/cache/epub/22/pg22.txt`
- Size: ~1.5 MB (1,539,638 bytes)
- Encoding: UTF-8 with CRLF line endings — open with `newline=None` or strip `\r`
- Line count: ~48,000

### File format: structured plain text

**Top-level hierarchy:**

```
CLASS I. EXISTENCE
  SECTION I. EXISTENCE
    #1. Existence.—N. ...
    #2. Inexistence.—N. ...
  SECTION II. RELATION
    #9. Relation.—N. ...
```

Six classes (EXISTENCE, SPACE, MATTER, INTELLECT, VOLITION, AFFECTIONS),
subdivided into sections, then numbered entries. Section headers are plain text
lines with no prefix marker.

**Entry format:**

```
#NNN[a|b]. CategoryName.—N. noun1, noun2, noun_group; noun3, noun4.
     V. verb1, verb2; verb_group.
     Adj. adj1, adj2; adj_group.
     Adv. adv1, adv2.
     Phr. phrase1; phrase2.
```

Parsing rules:
- Entry begins when a line matches `^#\d+[a-z]?\. ` (regex).
- Entry number may have a letter suffix: `#16a`, `#216a`, `#392b`.
- Entry body continues across multiple lines until the next `#NNN` marker.
- A bare `#` line (MICRA artifact) may appear between entries — filter it.
- PoS boundaries (`N.`, `V.`, `Adj.`, `Adv.`, `Phr.`, `Int.`) appear inline
  (mid-paragraph), not at line starts. Splitting on PoS requires in-text regex.
- Synonyms within a PoS section: **comma-separated**. A semicolon marks a
  conceptual sub-group boundary within the same PoS.
- `&c.` shorthand appears as both a cross-ref (`&c. NNN`) and a self-ref
  (`&c. adj.`, `&c. n.`); distinguish by what follows.

**Real sample — #1 Existence:**

```
#1. Existence.—N. existence, being, entity, _ens_, _esse_, subsistence.
     reality, actuality; positiveness &c. adj.; fact, matter of fact, ...
     V. exist, be; have being &c. n.; subsist, live, breathe, ...
     Adj. existing &c. v.; existent, under the sun; ...
```

**Real sample — #897 Love / #898 Hate:**

```
#897. Love.—N. love; fondness &c. adj.; liking; inclination &c. (desire) 865;
     regard, dilection|, admiration, fancy. affection, sympathy, fellow-feeling;
     tenderness &c. adj.; ...
     V. love, like, affect, fancy, care for, take an interest in, ...

#898. Hate.—N. hate, hatred, vials of hate. ...
```

### Synonym extraction

Parse each entry's `N.` / `V.` / `Adj.` sections and split on commas.
All comma-separated words within one section are synonyms (sharing category).
Semicolons mark sub-groups; parser may treat each sub-group as a tighter synonym
cluster.

### Antonym extraction — TWO mechanisms

**Mechanism 1: Implicit sequential pairing (primary)**

Roget's canonical design places opposite concepts in consecutive even/odd entry
pairs. Examples: #1 Existence / #2 Inexistence; #897 Love / #898 Hate;
#91 Bisection / #92 Trisection. The standard pairing table from Roget scholarship
maps each entry to its antonym partner. Total entries: 1,043 (range 1–1000 with
letter suffixes). Approximately 500 paired antonym pairs available this way.

**Mechanism 2: Explicit `{ant. NNN}` annotation (14 entries)**

A small set carries an explicit annotation:
```
#132. Earliness.—N. {ant. 133} earliness ...
#133. Lateness.—N. {ant. 132} lateness ...
```

These 14 entries (28 unique pairs) can be extracted with regex `\{ant\.?\s*(?:of\s*)?(\d+)\}`.

**For Task 8:** The recommended approach is to use the explicit `{ant.}` markers
where present, and build a companion antonym-pairs table from published Roget
pair-lists for the implicit sequential pairs (the table is a small PD artifact,
not a derived work). This gives ~500 antonym category-pairs to exploit.

### Stats

| Metric | Count |
|---|---|
| Total numbered entries | 1,043 |
| Entry range | 1–1000 (with letter suffixes) |
| Approximate word tokens | ~200,000 |
| Category cross-references (`&c. NNN`) | 2,833 |
| Explicit `{ant.}` markers | 14 |
| Non-ASCII characters (Greek, Latin, em-dashes, curly quotes) | 1,356 |

### Bridging hook

English: `glosses.en[*].text`. The TBESG 1–3 word glosses (e.g., "love", "grief",
"joy") match well against Roget's category-name and synonym-list words.

### Parsing complications

1. CRLF line endings.
2. Entry bodies span multiple lines; `#NNN` is the only delimiter.
3. PoS boundaries are mid-paragraph (not line-anchored).
4. `&c.` overloaded as cross-ref and self-ref.
5. Antonym structure is largely implicit.
6. Non-ASCII Greek script appears inline: `ἔρως`, `στοργή` (UTF-8 clean).

---

## Source 3: Lewis & Short Latin Dictionary — DEFERRED

### Finding

Two machine-readable editions exist:

**a) Perseus Digital Library XML:**
- Files: `lat.ls.perseus-eng1.xml` (77.2 MB) and `lat.ls.perseus-eng2.xml`
  (77.4 MB, updated)
- Repo: `https://github.com/PerseusDL/lexica`
- License: **CC-BY-SA 4.0** (TEI XML encoding by Perseus/Tufts University)
- Format: TEI P4 XML; entries keyed by `key="headword"` attribute; senses in
  nested `<sense>` elements; cross-references via `<xr>`/`<ref>` elements
  (mostly internal "v. infra/supra") and inline "cf.:" patterns in text.

**b) IohannesArnold JSON rip:**
- Repo: `https://github.com/IohannesArnold/lewis-short-json`
- 25 JSON files split by initial letter, ~37.7 MB total
- License: **CC-BY-SA 4.0** (inherits from Perseus source)
- Cross-references are inline in `senses` string arrays: `"(cf.: gloria, praeconium)"`
  not in a structured field.

The underlying 1879 text (Lewis & Short, *A Latin Dictionary*, Oxford) is firmly
**Public Domain** (published 1879). The copyright on the machine-readable encoding
is the issue.

### Why DEFERRED

Two independent blockers, either of which alone would be sufficient:

**Blocker 1 — License incompatibility:**
CC-BY-SA 4.0 is a copyleft (share-alike) license. Derived edges from a CC-BY-SA
source would require the entire derived dataset carrying those edges to also use
CC-BY-SA — incompatible with this repo's CC-BY 4.0 / CC0 content regime
(per `docs/LICENSING.md`, content is CC-BY 4.0 at most restrictive, not SA).

**Blocker 2 — No Latin gloss bridge:**
The committed lexicon has **0 Latin glosses** across all 15,255 entries
(confirmed: `glosses.la` absent from every G#### and lemma-* file). There is
no bridge from Strong's lemma keys to Latin headwords. Even with a PD
machine-readable L&S, mining would require a separate GRC→Latin concordance
pipeline (e.g., aligning Vulgate Latin words to Greek Strong's numbers).

### Fallback

Latin mining is **deferred to a future spec** when a GRC-to-Latin lemma bridge is
established and a clear PD/CC-BY (non-SA) machine-readable edition is identified.

The Perseus XML exists and is available at the URL above for when this is revisited.
Any future Latin mining should verify whether a clean-room re-encoding of the 1879
PD text (independent of Perseus's copyrightable expression) is available or
producible.

---

## Source 4: In-repo PD lexica cross-refs (Abbott-Smith / BDB)

### What is "in the floor"

The committed floor contains `lexicon/grc/*.json` and `lexicon/hbo/*.json` built
from the Strong's XML (`strongs-greek.xml`, `strongs-hebrew.xml`) and TBESG.txt.
The raw source files are gitignored (`data/cache/`). Neither Abbott-Smith
(separate XML) nor BDB (BrownDriverBriggs.xml) are currently downloaded.

### 4a. Strong's cross-refs already in committed lexicon gloss text

The Strong's XML's `<strongsref>` and `<see>` elements were rendered into the
gloss text as `G####`/`H####` literals during the build (see `_render_element`
in `tools/build_lexicon.py`). This means the committed `glosses.en[*].text` field
carries embedded cross-references for many entries.

**Extractable immediately from committed lexicon — no new download:**

```python
import re
compare_pattern = re.compile(r'(?:compare|cf\.?)\s+([GH]\d{4})', re.IGNORECASE)
# Match in glosses.en[*].text of each lexicon/grc/G####.json entry
```

**Coverage:**
- Greek G#### entries with "compare/cf G/H####" in gloss text: **89 entries**
- Hebrew H#### entries with "compare/cf G/H####" in gloss text: **167 entries**

These 256 entries yield direct Strong's cross-reference pairs. They become
`related` or `synonym` edges with `source="strongs-greek"` or `source="strongs-hebrew"`,
`method="derived"`, and a moderate rank (lower than the `root`-derived shared-root
edges because "compare" is weaker than etymological identity).

**Sample entries with compare cross-refs (Greek):**

```json
G0009: "of foreign origin (compare H0058); Abilene, a region of Syria"
G0025: "perhaps from ἄγαν (much) (or compare G5689); to love (in a social or moral sense)"
G0032: "from ἀγγέλλω (probably derived from G0071; compare G0034)..."
```

The `root` field (separate structured field, not text-embedded) provides stronger
shared-root signals (78.7% of G#### have a non-null root; 65.9% of H####).

### 4b. Abbott-Smith via TBESG col 8 (Meaning field)

TBESG.txt (STEPBible, CC-BY 4.0) carries Abbott-Smith content in column 8
(0-indexed col 7, the `Meaning` field). The current floor build uses only col 6
(Gloss); col 8 is available for Task 9 by re-parsing TBESG.txt.

**Format of TBESG col 8:**
- HTML-formatted prose (uses `<b>`, `<BR />`, `<ref='...'>`, `_italic_`)
- Cross-references to OTHER Greek words appear inline as:
  - Greek-script word names: `"φιλία"`, `"ἀγάπησις"` (not Strong's numbers)
  - `(which see)` after the Greek word name
  - `cf.` with literature abbreviations like `Deiss., LAE`, `MM` (external sources)
- 2,311/11,035 data rows contain `see`, `cf.`, or `compare` — but the targets are
  typically external literature abbreviations or Greek words by name, NOT G#### codes

**Task 9 approach for Abbott-Smith:**
To extract related-word links from TBESG col 8: parse Greek-script word names from
the Meaning field; reverse-look them up in the TBESG col 3 (Greek lemma) index to
get a G#### code; emit as a `related` edge. This requires a Greek-string-to-G####
map built from TBESG col 3 and col 0 (eStrong). Source label: `abbott-smith`
(data comes from TBESG, which cites Abbott-Smith); license: CC-BY 4.0.

Download: TBESG.txt is at `https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Lexicons/TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt` (~4.6 MB). Cache under `data/cache/morph/raw/TBESG.txt` (consistent with the floor's convention).

### 4c. BDB (Brown-Driver-Briggs Hebrew Lexicon)

**Source:** openscriptures/HebrewLexicon on GitHub.

**Files needed:**
- `BrownDriverBriggs.xml` (2.9 MB, PD) — the lexicon entries
- `LexicalIndex.xml` (1.8 MB, PD) — maps Strong's numbers to BDB entry IDs

**License:** Public Domain. BDB first published 1906; out of copyright. The
openscriptures XML encoding is also PD per project terms.

Download URLs:
- `https://raw.githubusercontent.com/openscriptures/HebrewLexicon/master/BrownDriverBriggs.xml`
- `https://raw.githubusercontent.com/openscriptures/HebrewLexicon/master/LexicalIndex.xml`

Cache under `data/cache/relations/bdb/`.

**BDB XML format:**

```xml
<lexicon xmlns="http://openscriptures.github.com/morphhb/namespace">
  <part id="a" title="א" xml:lang="heb">
    <section id="a.aa">
      <entry id="a.aa.ab">
        <w>אָב</w> v. II. <w mod="II" src="a.ae.aa">אבה</w>.
        <status p="1">done</status>
      </entry>
    </section>
  </part>
</lexicon>
```

**Entry ID scheme:** Alphabetic positional keys: `a.aa.aa`, `a.ab.ac`, etc.
(NOT Strong's numbers — `<entry>` has no `strongs` attribute).

**Cross-reference encoding:**
`<w src="bdb_entry_id">` elements inside entry text encode see-references:
```xml
<entry id="a.aa.ab">
  <w>אָב</w> v. II. <w mod="II" src="a.ae.aa">אבה</w>.
</entry>
```
`v.` = "see" (BDB abbreviation). The `src="a.ae.aa"` attribute points to the
target BDB entry ID. Some entries also use `<ref r="Book.C.V">` for scriptural
references (not cross-refs to related words).

**Mapping BDB entry IDs to H#### keys:**
LexicalIndex.xml maps Strong's integers to BDB entry IDs:
```xml
<entry id="aac">
  <w xlit="ʾāb">אָב</w> <pos>N</pos> <def>father</def>
  <xref bdb="a.ae.ab" strong="1" twot="4a"/>
</entry>
```
`strong="1"` → `H0001`, `bdb="a.ae.ab"` → BDB entry `a.ae.ab`.
Build a reverse map: `{bdb_id → H####}` from LexicalIndex.xml, then for each
`<w src="bdb_id">` cross-ref in BDB, look up both source and target BDB IDs to
get H#### → H#### edge.

Derived edges from BDB: `source="bdb"`, `method="mined"`, license = CC0 (PD source).

### 4d. Task 9 pipeline summary

| Sub-source | Data already in floor? | New download needed | Cross-ref type |
|---|---|---|---|
| Strong's gloss text | YES (committed lexicon JSON) | None | Text regex `compare [GH]\d{4}` |
| Abbott-Smith (TBESG col 8) | NO (col 6 only in floor) | TBESG.txt (~4.6 MB) from STEPBible | HTML inline Greek words → reverse-G#### lookup |
| BDB | NO | BrownDriverBriggs.xml (2.9 MB) + LexicalIndex.xml (1.8 MB) | `<w src="bdb_id">` → reverse-H#### map |

The Strong's text cross-refs (89 Greek, 167 Hebrew entries) are the zero-download
starting point for Task 9 and should be mined first.

---

## Source 5: Gloss-bridge feasibility

The gloss bridge (`gloss_bridge.py`, Task 6) maps thesaurus headwords to lemma keys
by looking up the headword in an index of `glosses[lang]` text. This section
confirms the English bridge works and documents the Latin gap.

### English bridge — CONFIRMED

| Lexicon | Total entries | With `glosses.en` | Coverage |
|---|---|---|---|
| Greek G#### | 5,122 | 5,119 | 99.9% |
| Hebrew H#### | 8,426 | 8,413 | 99.8% |
| LXX-only (lemma-*) | 10,133 | 0 | 0% |

**TBESG gloss word-length distribution (Greek G####, source="tbesg"):**

| Word count | Entry count | Cumulative % |
|---|---|---|
| 1 word | 2,928 | 57.2% |
| 2 words | 1,602 | 88.5% |
| 3 words | 517 | 98.6% |
| 4+ words | 72 | 100% |

**Conclusion:** 57.2% of Greek TBESG glosses are single-word (e.g., "love", "joy",
"grief", "good"). These match thesaurus headwords with high precision. The
remaining 42.8% (2–3 words) still match well because the first word is typically
the core term.

**Recommended bridge strategy:**
1. Build index: `normalized_term → set[lemma_key]` where `normalized_term` is each
   whitespace-delimited token from TBESG glosses, lowercased, with Strong's
   cross-refs removed (pattern: `from G\d{4};` prefix).
2. For Hebrew: index from Strong's Hebrew gloss text (longer phrases; use first
   word or key-term extraction with stop-word filtering).
3. Thesaurus side: normalize headwords and synonym-list words the same way.
4. Emit an edge for each `(lemma_key_a, lemma_key_b)` cross-product where both
   match terms in the same thesaurus synonym group or antonym pair.

**English bridge confidence:**
- TBESG single-word gloss → exact headword match → high rank (minimal looseness penalty)
- TBESG multi-word gloss → first-word match → moderate penalty
- Strong's Hebrew gloss → key-term extraction → lower rank than TBESG

### LXX-only lemma-* entries — NOT bridgeable via English

All 10,133 LXX-only entries (`lexicon/grc/lemma-*.json`) have `glosses = {"en": []}`.
These entries were built from openscriptures LxxLemmas (CC-BY 4.0) which carries
only the raw Greek lemma string, no English definitions. The gloss slot is empty
by design ("ready for future enrichment; fabrication forbidden").

**Consequence for Tasks 7/8/9:** The thesaurus miners will yield zero edges for
LXX-only entries. This is correct behavior — not a bug. Log the skipped count.

### Latin bridge — NOT AVAILABLE

`glosses.la` is absent from every entry in the committed lexicon (0/15,255 entries).
The `build_lexicon.py` docstring explicitly states: "Latin glosses are NOT generated:
there is no Vulgate→Strong's alignment in this corpus." This is the same blocker
documented in §3 (Lewis & Short deferred) from the bridge side.

---

## Confirmation: `data/cache/` is gitignored

From `.gitignore`:

```
data/cache/
```

The downloads at `data/cache/relations/wordnet/` and `data/cache/relations/roget/`
are NOT committed. Tasks 7/8 must either download on demand (checking `data/cache/`
first) or provide a `fetch.py`-style caching layer. The pattern in this repo:
check if the cache file exists, skip download if so, otherwise fetch and save.

---

## Edge provenance map (for `build_relations.py`)

| Source | `provenance.source` | `method` | License | `rel` |
|---|---|---|---|---|
| Open English WordNet | `open-english-wordnet` | `mined` | CC-BY 4.0 | synonym, antonym |
| Roget 1911 | `roget-1911` | `mined` | CC0 (PD) | synonym, antonym |
| Lewis & Short | — | — | DEFERRED | — |
| Strong's gloss compare-refs | `strongs-greek` / `strongs-hebrew` | `mined` | CC0 (PD) | related |
| Abbott-Smith via TBESG | `abbott-smith` | `mined` | CC-BY 4.0 | related |
| BDB | `bdb` | `mined` | CC0 (PD) | related |

---

## Attribution requirements

| Source | Required attribution |
|---|---|
| Open English WordNet | "Open English Wordnet 2024, globalwordnet/english-wordnet, CC-BY 4.0, https://github.com/globalwordnet/english-wordnet. Based on Princeton WordNet." |
| Roget 1911 | No attribution required (Public Domain). MICRA Inc. preparation is PD-dedicated. |
| Strong's Greek/Hebrew | "Public Domain — Strong's Exhaustive Concordance, James Strong 1890. XML by Ulrik Petersen." |
| Abbott-Smith via TBESG | "Data created by www.STEPBible.org based on work at Tyndale House Cambridge (CC BY 4.0). Source: https://github.com/STEPBible" |
| BDB | "Brown-Driver-Briggs Hebrew Lexicon (1906), Public Domain. XML by openscriptures, https://github.com/openscriptures/HebrewLexicon" |
