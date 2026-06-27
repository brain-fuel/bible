# FORMATS-lxx.md — LXX (Septuagint) Source Formats + License Verification

Task 0 spike for the **LXX integration** sub-project (precursor to L2b).
Data-acquisition + license gate. No production code ships from this task; this
document is the contract Tasks 1–8 build against.

All assertions were verified against real downloaded files (cached, gitignored,
under `data/cache/morph/raw/lxx/`) or against the live upstream repos on
2026-06-27. Licenses were read from the actual LICENSE/README files, quoted
verbatim, and URLs recorded. Deviations from the brief's assumptions and open
risks are called out explicitly.

**Hard constraint:** every *shipped* datum must be **Public Domain or CC-BY**.
Restricted-redistribution sources (CATSS/CCAT and its derivatives; UBS MARBLE)
are **rejected**; the chosen fallback is recorded.

---

## Executive summary — the four data problems

| # | Data problem | Chosen source | License | Status |
|---|--------------|---------------|---------|--------|
| 1 | LXX text + morphology | **STEPBible TAGOT** (preferred, *pending upstream release*); interim open materials: **openscriptures LxxLemmas** (lemma+verse) + **Swete 1909** (PD text) | CC-BY 4.0 / PD | **CONCERN** — no CC-BY/PD morph corpus is downloadable *today*; the clean one (TAGOT) is announced but unreleased |
| 2 | Strong's linkage (lemma → `lexicon/grc`) | LXX Greek lemma, **byte-identical** to existing `lexicon/grc` lemmas | n/a (join feasibility) | **OK** — exact-match join verified |
| 3 | MT↔LXX word alignment | **No open word-level set exists.** Fallback: verse-level lemma/Strong's co-occurrence over the LXX↔MT verse map | fallback is CC0-derivable | **CONCERN (fallback recorded)** |
| 4 | LXX↔MT versification | **STEPBible TVTMS** Greek tradition column (extend existing `tools/tvtms.py`) + small CC0 supplement | CC-BY 4.0 / CC0 | **OK** |

**Overall Task-0 verdict: DONE_WITH_CONCERNS.** Problems 2 and 4 are fully
solved with open data. Problem 1's *morphology* layer and Problem 3's
*word-level* alignment have **no shippable open source available today**; both
have recorded fallbacks, and the clean answer for #1 (STEPBible TAGOT) is a
forthcoming CC-BY release that downstream tasks should track.

---

## Source 1 — LXX text + morphology

### 1a. STEPBible TAGOT — *chosen production source, pending release*

- **Repo:** https://github.com/STEPBible/STEPBible-Data
- **Dataset:** **TAGOT** — "Translators Amalgamated Greek OT" (the Greek-OT
  sibling of TAGNT/TAHOT, which the floor already consumes). Announced to cover
  `LXXo` (Rahlfs oldest), `LXXn` (Swete newer), `LXXe` (ecclesiastical /
  Apostolic Bible). A related `TOTGT` (Tagged Greek OT, Rahlfs base + Apostolic
  variants) is also announced.
- **License:** **CC BY 4.0** — "Data created for www.STEPBible.org … available
  to other projects under CC BY 4.0 … you can include any part of STEPBible-Data
  in any software or publications without requesting permission." Same license,
  same attribution as the TAGNT/TAHOT/TBESG already shipped by the floor.
- **STATUS (2026-06-27): NOT YET DOWNLOADABLE.** The STEPBible-Data repo lists
  TAGOT under "Datasets coming … still being finished and/or being checked." The
  `Translators Amalgamated OT+NT/` directory currently contains only TAGNT and
  TAHOT files; no `TAGOT_*.txt` exists yet.
- **Why it is the preferred source anyway:** when released it is a *drop-in* for
  this project — it uses the **same semi-structured tab format and the same
  STEPBible Greek morph-code scheme as TAGNT** (documented in `FORMATS-morph.md`
  §"Source 1: TAGNT"). That means:
  - the existing Greek morph decoder (`morph_feats.decode(code,"grc")`) works
    unchanged — **no new morph scheme to add**;
  - the existing `tools/morph_norm/stepbible_greek.py` normalizer works
    unchanged — it already emits lemmas that match `lexicon/grc` (the NT floor
    proves this);
  - it carries `dStrongs`, the dictionary-form lemma, and the morph code per
    word, so Problems 1, 2 are solved in one source.
- **Expected on-disk layout** (by analogy to TAGNT, to be re-verified on
  release): files split by book range (`TAGOT_*.txt`), preamble (~80–90 lines),
  per-verse `#`-prefixed summary lines, a repeated `Word & Type<TAB>…` header,
  then one tab-separated data row per word. Reference scheme
  `Book.Chapter.Verse#WordIdx=Type`. Strong's in col `dStrongs = Grammar` as
  `Gxxxx=MORPH`; dictionary lemma in `Dictionary form = Gloss`.

> **Downstream action:** Task 1 should poll the STEPBible-Data repo for TAGOT.
> When present, re-verify the column headers (they may differ slightly from
> TAGNT) and wire it as the `lxx` source in `data/morph-sources.json`. Until
> then, the morphology layer is blocked on this release (see Open Risks).

### 1b. openscriptures GreekResources — `LxxLemmas` (interim, lemma+verse only, CC-BY)

- **Repo:** https://github.com/openscriptures/GreekResources
- **Path:** `LxxLemmas/<Book>.js` (one file per book/text-form) +
  `LxxFileNames.txt` (CCAT→SBL filename map).
- **License:** **CC BY 4.0** — "These files are released under a Creative
  Commons Attribution 4.0 International License" (Open Scriptures Septuagint
  Project, David Troidl).
- **Format (verified, cached as `oslxx_Gen.js`):** JSON object keyed by
  `Book.Chapter.Verse`, value = ordered list of word objects:
  ```json
  "Gen.1.1": [
      {"key": "εν", "lemma": "ἐν"},
      {"key": "αρχη", "lemma": "ἀρχή"},
      {"key": "ποιεω", "lemma": "ποιέω"},
      {"key": "ο", "lemma": "ὁ"},
      {"key": "θεος", "lemma": "θεός"}
  ]
  ```
  - `key` = lowercased, unaccented lookup key.
  - `lemma` = **precomposed polytonic Greek dictionary form** (with breathings
    and oxia accents).
- **What it gives:** a CC-BY **lemma per word, keyed by verse**, for the full LXX
  canon (60 book/text-form files; see Book List below). **What it does NOT
  give:** surface text with accents, morphology codes, or Strong's numbers.
- **Provenance caveat:** the verse/word *structure* tracks the CCAT verse
  division (openscriptures README: "the actual text of the Septuagint may be
  downloaded from the CCAT website"); openscriptures' *lemma corrections* are
  the CC-BY contribution. The lemma strings themselves are uncopyrightable
  lexical facts. Usable as a CC-BY lemma index / Strong's-join helper and as a
  word-order skeleton, but it is not a morphology corpus.

### 1c. Swete 1909/1930 — PD text only

- **Underlying text:** Swete, *The Old Testament in Greek* (1909–1930). **Public
  Domain by age** (H. B. Swete d. 1917; > 70 years).
- **Convenience packaging (cached for inspection):**
  https://github.com/eliranwong/LXX-Swete-1930 — CSVs:
  `01-Swete_word_with_punctuations.csv` (format: `wordindex<TAB>word`, e.g.
  `3<TAB>ἐποίησεν`), `00-Swete_versification.csv` (`wordindex<TAB>Book.C:V`),
  `03-Swete_SBL_transliterations.csv`.
- **License caveat:** **the eliranwong repo is GPL-3.0**, which is *not* in our
  PD/CC-BY allow-list. The *Swete text itself* is PD and may be shipped, but it
  must be sourced/re-derived from a PD edition, **not copied from the GPL CSV**.
- **Limitation:** text only — **no lemma, no morph, no Strong's** (matches the
  brief's "Swete (PD, text only)").

### 1d. REJECTED morphology sources (restricted license)

| Source | What it is | License finding | Verdict |
|--------|-----------|-----------------|---------|
| **CATSS / CCAT LXXM** (Univ. of Pennsylvania, R. Kraft) | the field-standard morphologically-analyzed Rahlfs LXX (betacode) | Analogous to **CC BY-NC-SA**: *no commercial use*, *share-alike*, and a signed **CCAT user declaration** is required before download. ccat.sas.upenn.edu | **REJECTED** — non-commercial + not openly redistributable |
| **eliranwong/LXX-Rahlfs-1935** | Rahlfs 1935 + split morph features + glosses (Text-Fabric) | Repo states verbatim: *"LXX-Rahlfs-1935 by Copyright 2017 Eliran Wong is licensed under a Creative Commons Attribution-**NonCommercial-ShareAlike** 4.0 International License."* Derived from CATSS. | **REJECTED** — NC, and CATSS-derived |
| **CenterBLC/LXX** | Rahlfs 1935 with Text-Fabric features | Repo LICENSE = MIT, **but** the morphology is built on eliranwong's CATSS-derived RLXX1935 + dictionary forms "as found in the BibleOL" (separate license). The MIT label does not cleanly cover the CATSS-derived morph upstream. | **REJECTED for shipped morph** — provenance conflict; treat MIT claim as not dispositive over CATSS terms |

> CATSS-derived data may be cached locally for *research/format inspection*
> only; none of it may be shipped in `bible/lxx/` or `morph/lxx/`.

### Morph-code scheme note (for the decoder)

- **STEPBible TAGOT** (chosen) uses the **same Greek morph scheme as TAGNT**
  (`N-NSF`, `V-AAI-3S`, …) — already handled by `morph_feats.decode(…,"grc")`.
  **No additive scheme needed.**
- **CATSS** (rejected) uses a *different* positional parse scheme (POS letter +
  fixed-width parse string over betacode lemmas), incompatible with the Robinson/
  TAGNT codes. Were a CATSS-derived source ever licensed, the decoder would need
  an **additive `lxx-catss` scheme** — recorded here so the decision is explicit.

---

## Source 2 — Strong's linkage (lemma → `lexicon/grc` → Strong's)

**Question:** does the chosen LXX source give a Greek *lemma* per word, and does
that lemma normalize to the existing `lexicon/grc` lemma keys so a
lemma→Strong's join is feasible?

**Answer: YES, with an exact string match — no normalization layer required.**

Verified on disk (2026-06-27):

| Field | `lexicon/grc/G2316.json` lemma | openscriptures LxxLemmas `θεος` lemma |
|-------|-------------------------------|----------------------------------------|
| string | `θεός` | `θεός` |
| codepoints | `θ ε ό(U+1F79) ς` | `θ ε ό(U+1F79) ς` |
| byte-identical? | — | **YES** |

Key normalization facts:

- Both use **precomposed polytonic Greek with `oxia` accents (U+1F71, U+1F79,
  …)**, *not* NFC. NFC would fold oxia → `tonos` (U+03AC/U+03CC); these lemmas
  deliberately do **not**. `lexicon/grc` lemmas test `NFC == False`.
- The LXX lemma and the lexicon lemma are NFC-equal **and** raw-equal.
- Therefore the join key is the **raw lemma string** (do **not** NFC-normalize
  it, or you will break the match against `lexicon/grc`).
- `lexicon/grc` is keyed by `strong` (`Gxxxx`) with a `lemma` field; build a
  `lemma → strong` reverse index once and join LXX lemmas against it.

Consequences for the build:

- LXX tokens carry `Strong=Gxxxx` in CoNLL-U MISC where the lemma resolves to a
  `lexicon/grc` entry; **lemma-only** where it does not.
- **LXX-only vocabulary** (Greek words occurring in the LXX but not the TR/NT, so
  absent from `lexicon/grc`) gets **lemma-keyed** entries added to `lexicon/grc`
  additively — **no fabricated Strong's** (per the design spec).
- When TAGOT lands it carries `dStrongs` directly, so most tokens get a Strong's
  without needing the lemma join at all; the lemma join remains the mechanism for
  LXX-only words and as a cross-check.

---

## Source 3 — MT↔LXX word alignment

**Goal:** a word-level Hebrew(MT)↔Greek(LXX) alignment so each MT word maps to
the LXX word(s) rendering it (the cross-language payload consumed later by L2b).

### Finding: no OPEN word-level MT↔LXX alignment exists

- **CATSS Tov Hebrew-Greek Parallel Alignment** (E. Tov / CATSS) is the scholarly
  standard, but it lives under the **same restricted CCAT license** as the CATSS
  morphology (non-commercial, share-alike, signed user declaration). **REJECTED.**
- **Clear-Bible/Alignments** (https://github.com/Clear-Bible/Alignments) *is*
  CC BY 4.0 ("All alignment data is licensed under a Creative Commons Attribution
  4.0 International License"), **but it does not contain an MT↔LXX pair.** Its
  `data/` directory is organized by *modern* target language (`arb eng fra hau
  hin por rus spa …`); these are modern-translation ↔ original-language
  alignments (Hebrew/Greek-NT sources to vernacular Bibles). There is no
  Hebrew→Greek-OT (MT→LXX) alignment among them. (`catalog.tsv` is a Git-LFS
  pointer; the directory taxonomy is conclusive.)
- **MACULA** (Clear-Bible) carries Hebrew and Greek-**NT** linguistic data but no
  LXX alignment.

### Recorded fallback (per brief / design spec)

**Verse-level lemma / Strong's co-occurrence, flagged lower-confidence.**

- **Key:** for each protocanon verse, use the **LXX↔MT verse map** (Source 4) to
  pair an MT verse with its LXX verse, then co-occur **MT word Strong's (H####)**
  against **LXX word lemma → Strong's (G####)** within that verse pair.
- **Output artifact:** `align/mt-lxx/<CODE>/NNN.json` — but every edge is marked
  `confidence: "verse-cooccurrence"` rather than a true word link.
- **Coverage is pinned and honest** (design spec: "honest partials"); this is a
  weaker signal than a real word alignment and L2b must treat it as such.
- Protocanon only (deuterocanon has no MT counterpart → no alignment).

> **Downstream risk:** the headline motivation of the sub-project (an attested
> word-level Hebrew↔Greek bridge) degrades to verse-level co-occurrence unless a
> CC-BY/PD word alignment appears, or TAGOT ships with embedded alignment data.
> Flag for the L2b spec.

---

## Source 4 — LXX↔MT versification

### Finding: STEPBible TVTMS already carries a Greek/LXX tradition — reuse it

- **File:** `Versification/TVTMS - Translators Versification Traditions with
  Methodology for Standardisation for Eng+Heb+Lat+Grk+Others - STEPBible.org CC
  BY.txt`
- **Repo / License:** STEPBible-Data, **CC BY 4.0**.
- **The floor already fetches and parses this exact file** in `tools/tvtms.py`
  (it derives `data/versification/ot-versification.json` for the Hebrew and Latin
  traditions). The TVTMS columns are **English KJV, Hebrew, Latin, Greek (LXX),
  Greek2 (NETS), Slavonic, …** — the **Greek column is the LXX tradition** and is
  currently *parsed-past but unused*.
- **Extraction path (additive, low-risk):** extend `tools/tvtms.py` to also pick
  up the `Greek` column index (alongside the existing `English KJV` / `Hebrew` /
  `Latin` index logic in `parse_condensed`/`build_map`) and emit a third
  tradition into a new `data/versification/lxx-versification.json`, keyed exactly
  like the existing file: `"<CODE> C:V": "lxxC:V"` for verses that differ.
  Attribution string identical to the existing
  `ot-versification.json._attribution`.
- **What TVTMS encodes** (verified against the live file):
  - **Psalms numbering offset** — LXX Psalms run one behind the Hebrew for most
    of the Psalter; superscriptions are handled as `Psa.N:Title` vs `Psa.N:1`
    rows (the existing parser already drops `title`/`absent`/`noverse` refs).
  - **Esther additions** — segregated refs `Est.A … Est.F` for the Greek-only
    additions.
  - **Daniel additions** — sub-verse notation for the Greek expansions.
  - General verse-boundary shifts (e.g. Exo 8 LXX vs Hebrew 7:26–29).

### CC0 supplement for what TVTMS does NOT cover

TVTMS is a *verse-mapping* file; it does not model **structural/chapter
reordering or book-level segmentation differences**. A small **hand-authored CC0
supplement** (mirroring the existing `ot-versification-supplement.json` pattern)
captures:

- **Jeremiah chapter reorder** — LXX Jeremiah is ~1/8 shorter and the Oracles
  Against the Nations sit mid-book (LXX chs ~25–31) vs end-of-book in the MT
  (chs 46–51); chapter-level remap, not just verse offsets.
- **Greek Esther** — additions A–F integrated into the running text (vs the KJVA
  `ADE` split).
- **Greek Daniel** — Susanna / Song of the Three / Bel integrated into the Daniel
  book (and the OG vs Theodotion text-form split).
- Any book whose LXX chapter count differs from the MT counterpart.

These are factual correspondences → **CC0**, same discipline as the existing
`ot-versification-supplement.json`.

---

## LXX book list, order, chapter counts, and CODEs

Chapter counts below are from the cached Swete versification CSV (verified) and
the standard Rahlfs canon; re-pin against the chosen edition in Task 4. The
canonical LXX (Rahlfs) book set is confirmed by the openscriptures `LxxLemmas/`
file set (60 book/text-form files).

### Protocanon → existing OT codes (GEN…MAL)

All map to the `testament:"ot"` codes already in `data/books.json`. Corpus +
morphology + MT↔LXX alignment (alignment = verse-level fallback per Source 3).

| LXX book (Greek name) | CODE | chapters | Name / segmentation divergence to flag |
|------------------------|------|----------|----------------------------------------|
| Genesis | GEN | 50 | — |
| Exodus | EXO | 40 | verse offsets (TVTMS) |
| Leviticus | LEV | 27 | — |
| Numbers | NUM | 36 | — |
| Deuteronomy | DEU | 34 | — |
| Joshua (Ἰησοῦς) | JOS | 24 | **two Greek text-forms: JoshA / JoshB** (text-form variants, not new books) |
| Judges (Κριταί) | JDG | 21 | **two Greek text-forms: JudgA / JudgB** |
| Ruth | RUT | 4 | — |
| 1 Kingdoms (Βασιλειῶν Α´) | 1SA | 31 | LXX name "1 Reigns/Kingdoms" |
| 2 Kingdoms (Βασιλειῶν Β´) | 2SA | 24 | LXX name "2 Reigns/Kingdoms" |
| 3 Kingdoms (Βασιλειῶν Γ´) | 1KI | 22 | LXX name "3 Reigns/Kingdoms" |
| 4 Kingdoms (Βασιλειῶν Δ´) | 2KI | 25 | LXX name "4 Reigns/Kingdoms" |
| 1 Paralipomenon | 1CH | 29 | LXX name "Paralipomenon A" |
| 2 Paralipomenon | 2CH | 36 | LXX name "Paralipomenon B" |
| 2 Esdras (Esdras B) = Ezra+Nehemiah | EZR + NEH | 10 / 13 | **LXX "Esdras B" combines Ezra+Nehemiah**; split across the two existing codes |
| Esther (Greek) | EST | 10 (+ adds A–F) | additions A–F integrated (KJVA splits as `ADE`) |
| Job | JOB | 42 | LXX Job ~1/6 shorter than MT |
| Psalms | PSA | **151** | **Psalm 151 present** (LXX has 151; MT/`books.json` PSA=150) — see new-code note |
| Proverbs | PRO | 29 (Swete) / 31 | order/material divergences |
| Ecclesiastes (Ἐκκλησιαστής) | ECC | 12 | — |
| Song of Songs (Ἆσμα) | SOS | 8 | LXX name "Asma / Canticles" |
| Isaiah | ISA | 66 | — |
| Jeremiah | JER | 52 | **chapter reorder + ~1/8 shorter** (OAN mid-book); see CC0 supplement; OG `Jer1`/`Jer2` split in some editions |
| Lamentations | LAM | 5 | — |
| Ezekiel | EZE | 48 | — |
| Daniel (Greek) | DAN | 12 (+ adds) | **Theodotion (Th) vs Old Greek (OG) text-forms**; Susanna/Bel/Song-of-Three integrated |
| Hosea | HOS | 14 | **Minor Prophets order differs** (see note) |
| Joel | JOE | 3 | Minor Prophets order |
| Amos | AMO | 9 | Minor Prophets order |
| Obadiah | OBA | 1 | Minor Prophets order |
| Jonah | JON | 4 | Minor Prophets order |
| Micah | MIC | 7 | Minor Prophets order |
| Nahum | NAH | 3 | Minor Prophets order |
| Habakkuk | HAB | 3 | Minor Prophets order |
| Zephaniah | ZEP | 3 | Minor Prophets order |
| Haggai | HAG | 2 | Minor Prophets order |
| Zechariah | ZEC | 14 | Minor Prophets order |
| Malachi | MAL | 4 | Minor Prophets order |

> **Minor Prophets order:** the LXX orders the Twelve **Hosea, Amos, Micah,
> Joel, Obadiah, Jonah, Nahum, Habakkuk, Zephaniah, Haggai, Zechariah, Malachi**
> (Hosea–Amos–Micah–Joel head, vs MT Hosea–Joel–Amos–Obadiah). Codes are
> unchanged; only the `order` field / book sequence differs. Flag for `books.json`
> ordering when LXX sequence matters.

### Deuterocanon → existing `apo` codes (Greek text + morph only, no alignment)

| LXX book | CODE | chapters | Note |
|----------|------|----------|------|
| 1 Esdras (Esdras A, Greek) | 1ES | 9 | LXX "Esdras A"; distinct from Esdras B (Ezra+Neh) |
| Tobit | TOB | 14 | **two Greek forms: TobBA (short) / TobS (long, Sinaiticus)** |
| Judith | JDT | 16 | — |
| Additions to Esther | ADE | (A–F) | LXX integrates these into EST; `ADE` is the KJVA split (coexistence per design) |
| Wisdom of Solomon | WIS | 19 | — |
| Sirach (Ecclesiasticus) | SIR | 51 | — |
| Baruch | BAR | 5 | LXX Baruch is 5 chs; the **Epistle of Jeremiah is a *separate* LXX book** (KJVA folds it into Baruch ch 6) — see new-code note |
| Prayer of Azariah / Song of the Three | PAZ | 1 | integrated into Greek Daniel |
| Susanna | SUS | 1 | **OG / Th forms**; integrated into Greek Daniel |
| Bel and the Dragon | BEL | 1 | **OG / Th forms**; integrated into Greek Daniel |
| Prayer of Manasses | MAN | 1 | LXX places it as **Ode 12** within Odes |
| 1 Maccabees | 1MA | 16 | — |
| 2 Maccabees | 2MA | 15 | — |

### LXX-only books → propose NEW codes

| LXX book | proposed CODE | chapters | Note |
|----------|---------------|----------|------|
| 3 Maccabees | **3MA** | 7 | new |
| 4 Maccabees | **4MA** | 18 | new |
| Odes (Ὠδαί) | **ODE** | 14 | liturgical canticles; includes Prayer of Manasses (Ode 12) and Magnificat etc. — overlaps existing book material |
| Psalms of Solomon | **PSS** | 18 | new (present in Rahlfs, appended) |
| Epistle of Jeremiah | **EPJ** *(or keep as BAR ch 6)* | 1 | LXX treats it as a separate book; `books.json` BAR=6 already folds it in (KJVA style). **Decision needed:** ship separately as `EPJ` or as `BAR.6`. |
| Psalm 151 | *include as `PSA` ch 151* *(or new `P51`)* | 1 | single extra psalm; least-invasive = `PSA` chapter 151. **Decision needed.** |

### Important code-collision warnings

- **`2ES` collision:** `data/books.json` already has `2ES` = "II Esdras", **16
  chapters** — that is **4 Ezra (the Latin apocalypse)**, which is **NOT in the
  Greek LXX**. The LXX "2 Esdras / Esdras B" is **Ezra+Nehemiah**. **Do NOT map
  the LXX Esdras B to the existing `2ES` code** — map it to `EZR` + `NEH`. Leave
  `2ES` (4 Ezra) out of `bible/lxx/`.
- **Text-form doublets are not new books.** Joshua A/B, Judges A/B, Tobit BA/S,
  Daniel OG/Th, Susanna OG/Th, Bel OG/Th are *two Greek text forms of the same
  book*. Model them with an **edition / text-form tag** (e.g. a `text_form`
  field or a per-edition row), **not** new book codes — otherwise the canon
  inflates. Default ship = the standard form (Theodotion for Daniel/Sus/Bel;
  pick per chosen edition for Josh/Judg/Tob); keep the alternate as an additive
  variant edition.
- **`1En` (1 Enoch)** appears in the eliranwong Swete CSV but is **not** part of
  the Rahlfs LXX canon; treat as out of scope unless explicitly requested.

---

## Cache manifest (gitignored — `data/cache/morph/raw/lxx/`)

`data/cache/` is already covered by `.gitignore` (line 1: `data/cache/`); no
change needed. Files downloaded for inspection this task:

| File | Source | License of packaging | Use |
|------|--------|----------------------|-----|
| `oslxx_Gen.js` | openscriptures GreekResources `LxxLemmas/Gen.js` | CC-BY 4.0 | lemma format + lemma-join verification |
| `oslxx_FileNames.txt` | openscriptures `LxxFileNames.txt` | CC-BY 4.0 | LXX book/text-form list |
| `swete_word_with_punct.csv` | eliranwong/LXX-Swete-1930 | GPL-3.0 packaging (text is PD) | PD text format inspection only — re-derive from PD source before shipping |
| `swete_versification.csv` | eliranwong/LXX-Swete-1930 | GPL-3.0 packaging | chapter-count verification |
| `swete_LICENSE` | eliranwong/LXX-Swete-1930 | — | recorded the GPL-3.0 caveat |

Nothing under `data/cache/` is committed (correct).

---

## Attribution requirements (for shipped derivatives)

| Source | Required attribution |
|--------|---------------------|
| STEPBible TAGOT / TVTMS (when used) | "Data created by www.STEPBible.org based on work at Tyndale House Cambridge (CC BY 4.0). Source: https://github.com/STEPBible/STEPBible-Data" |
| openscriptures GreekResources (LxxLemmas) | "Open Scriptures Septuagint Project (David Troidl), CC BY 4.0. https://github.com/openscriptures/GreekResources" |
| Swete 1909 text | "Public Domain — H. B. Swete, *The Old Testament in Greek*, 1909." |
| CC0 versification supplement | authored facts, CC0 |

---

## Summary of deviations from the brief's assumptions + open risks

1. **STEPBible "tagged LXX" exists as a named dataset (TAGOT) but is NOT yet
   released.** The brief listed it as "if present"; it is *announced, not
   present*. It remains the best fit (zero new morph scheme, reuses the existing
   normalizer + decoder + lexicon join) — but Task 1's morphology is **blocked
   on its upstream release**. Poll the repo.

2. **No CC-BY/PD morphologically-tagged LXX is downloadable today.** Every
   ready-made morph LXX (CATSS, eliranwong RLXX, CenterBLC) traces to CATSS and
   is non-commercial/restricted → all rejected. Open materials available *now*
   are lemma-only (openscriptures, CC-BY) and PD text (Swete). → **Problem 1 is
   DONE_WITH_CONCERNS.**

3. **No open word-level MT↔LXX alignment exists.** CATSS/Tov is restricted;
   Clear-Bible/Alignments (CC-BY) has no MT↔LXX pair. → fallback = verse-level
   lemma/Strong's co-occurrence, lower-confidence. This **degrades the
   sub-project's headline value** (attested word bridge → verse co-occurrence);
   flag prominently for L2b.

4. **Strong's linkage is clean.** LXX lemmas are **byte-identical** to
   `lexicon/grc` lemmas (precomposed polytonic, oxia accents, *not* NFC). Join on
   the raw lemma string; do not NFC-normalize.

5. **Versification is clean.** TVTMS already carries the Greek/LXX tradition and
   is already fetched+parsed by `tools/tvtms.py`; the Greek column is parsed-past
   but unused. Extend that one tool additively + a small CC0 supplement for
   chapter-level reordering (Jeremiah) and integrated additions (Esther/Daniel).

6. **Book-code hazards:** `2ES` in `books.json` is 4 Ezra (NOT LXX Esdras B —
   map Esdras B to EZR+NEH); OG/Theodotion and A/B doublets are text-form
   variants, not new book codes; new codes proposed: `3MA`, `4MA`, `ODE`, `PSS`,
   and (decision-pending) `EPJ` and Psalm-151 handling.
