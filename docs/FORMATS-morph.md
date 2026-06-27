# FORMATS-morph.md — Morpho-Lexical Source Formats

Task 0 spike: data-acquisition + license verification.
Downstream tasks (1–8) build normalizers against this document.
All assertions were verified against real downloaded files; deviations from the
brief's assumptions are called out explicitly.

---

## Intermediate TSV contract (downstream target)

Task 1 normalizers emit one TSV per source, with exactly these columns:

```
ref  idx  surface  lemma  strong  xpos  feats  translit  edition
```

| Column    | Meaning |
|-----------|---------|
| `ref`     | `CODE.chapter.verse` (CODE from data/books.json, uppercase 3-char) |
| `idx`     | 1-based word index within the verse |
| `surface` | surface form as it appears in the source (with pointing for Hebrew) |
| `lemma`   | lexical/dictionary form |
| `strong`  | `G` or `H` + zero-padded 4 digits, e.g. `G0026`, `H0430` |
| `xpos`    | raw source morph code (no normalization) |
| `feats`   | placeholder `_` (CoNLL-U convention for unspecified; FEATS derived in a later task) |
| `translit`| source transliteration (if provided; else empty) |
| `edition` | `TR` for Greek Textus Receptus rows; `WLC` for Hebrew Masoretic rows |

Normalizers produce one row per word-token. The TR filter for Greek keeps only
rows where the `editions` column (col 5 in TAGNT) contains the string `TR`.

---

## Source 1: TAGNT — Translators Amalgamated Greek NT

### Canonical URL and license

- Repo: https://github.com/STEPBible/STEPBible-Data
- Path in repo: `Translators Amalgamated OT+NT/`
- License: **CC BY 4.0** — attribution to STEPBible + Tyndale House Cambridge required
- Attribution link: https://github.com/STEPBible

### Downloaded files (data/cache/morph/raw/)

| File | Size |
|------|------|
| `TAGNT_Mat-Jhn.txt` | 14 MB |
| `TAGNT_Act-Rev.txt` | 16 MB |

Two parts because a single file exceeds GitHub size limits.
Together they cover the entire NT (27 books).

### File structure — DEVIATION FROM BRIEF

TAGNT is **not** a flat TSV. It uses a semi-structured format:

1. A preamble (~88 lines) of copyright, abbreviations, and field descriptions.
2. For each verse: a cluster of `#`-prefixed summary lines (interlinear-style verse
   header, translation, word+grammar), then a `Word & Type<TAB>Greek<TAB>...`
   header line, then one data row per word.

The `Word & Type` header line is repeated for **every verse block**. Parsers must
skip any line whose first field begins with `#` or equals `Word & Type`.

### Column headers (exact text, tab-separated)

```
Word & Type	Greek	English translation	dStrongs = Grammar	Dictionary form =  Gloss	editions	Meaning variants	Spelling variants	Spanish translation	Sub-meaning	Conjoin word	sStrong+Instance	Alt Strongs
```

| Col# | Name | Example |
|------|------|---------|
| 0 | `Word & Type` | `Mat.1.1#01=NKO` |
| 1 | `Greek` | `Βίβλος (Biblos)` |
| 2 | `English translation` | `[The] book` |
| 3 | `dStrongs = Grammar` | `G0976=N-NSF` |
| 4 | `Dictionary form = Gloss` | `βίβλος=book` |
| 5 | `editions` | `NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz` |
| 6 | `Meaning variants` | (often empty) |
| 7 | `Spelling variants` | `+TR: Δαβὶδ ;` (or empty) |
| 8 | `Spanish translation` | `Libro` |
| 9 | `Sub-meaning` | `book` |
| 10 | `Conjoin word` | `#01` or `#01»02:G2464` |
| 11 | `sStrong+Instance` | `G0976` or `G5207_A` |
| 12 | `Alt Strongs` | (often empty) |

### Reference scheme

Column 0 format: `Book.Chapter.Verse#WordIdx=TypeCode`

- `Book` = 3–4 char abbreviation (see mapping table below)
- `Chapter`, `Verse` = integer (no leading zeros)
- `WordIdx` = 2-digit zero-padded 1-based word index within the verse
- `TypeCode` = edition type code

**TAGNT book abbreviation → our CODE**:

| TAGNT | CODE | | TAGNT | CODE |
|-------|------|-|-------|------|
| Mat   | MAT  | | 1Co   | 1CO  |
| Mrk   | MAR  | | 2Co   | 2CO  |
| Luk   | LUK  | | Gal   | GAL  |
| Jhn   | JOH  | | Eph   | EPH  |
| Act   | ACT  | | Php   | PHP  |
| Rom   | ROM  | | Col   | COL  |
| 1Th   | 1TH  | | 2Th   | 2TH  |
| 1Ti   | 1TI  | | 2Ti   | 2TI  |
| Tit   | TIT  | | Phm   | PHM  |
| Heb   | HEB  | | Jas   | JAM  |
| 1Pe   | 1PE  | | 2Pe   | 2PE  |
| 1Jn   | 1JO  | | 2Jn   | 2JO  |
| 3Jn   | 3JO  | | Jud   | JDE  |
| Rev   | REV  | | | |

TAGNT versification follows NRSV. Occasional KJV verse differences are noted in
the reference with square brackets but do not affect word indices.

### Word index derivation

Extract the 2-digit decimal after `#` in column 0. Convert to integer.
Example: `Mat.1.1#01=NKO` → idx = 1.

The index is **continuous within each verse** even when there are variant words
from different editions. Words that appear only in one edition (e.g., TR-only)
carry their own index within that verse block.

### Strong's field

Column 3 (`dStrongs = Grammar`), format: `STRONG=MORPH`

- Everything before `=` is the Strong's; everything after is the morph code.
- Strong's has prefix `G` + 4-digit zero-padded number + optional disambiguation
  suffix (a single uppercase letter, e.g. `G`, `H`, `I`, `J`, `N`).
  Strip the trailing alpha suffix to get the canonical Strong's: `G2424G` → `G2424`.
  The number is already 4-digit zero-padded; no further padding is needed.
- Proper nouns that correspond to a Hebrew person use a Hebrew Strong's embedded
  in the form `H1732|G1138` — take the `G` number after `|` as the Greek Strong's.
- Column 11 (`sStrong+Instance`) gives the simple (non-disambiguated) Strong's
  plus an instance marker (`_A`, `_B`, etc.) for repeated occurrences in the verse.
  Use this column only for cross-referencing; prefer col 3 for the canonical strong.

**Padded form**: `G` + 4-digit already present — no reformatting needed except
stripping the disambiguation suffix letter.

### Morph code (TAGNT Greek)

Column 3 after `=`. Full code reference: TEGMC.txt (downloaded).

Structure: `Function[-Case-Number-Gender[-Extra]]`

**Function codes** (first component):

| Code | Meaning |
|------|---------|
| `A` | Adjective |
| `N` | Noun |
| `T` | Article |
| `V` | Verb |
| `P` | Pronoun |
| `R` | Relative pronoun |
| `D` | Demonstrative pronoun |
| `I` | Interrogative pronoun |
| `CONJ` | Conjunction |
| `PREP` | Preposition |
| `PRT-N` | Negative particle |
| `ADV` | Adverb |

**Case codes**: `N`=Nom, `G`=Gen, `D`=Dat, `A`=Acc, `V`=Voc

**Number codes**: `S`=Singular, `P`=Plural, `D`=Dual

**Gender codes**: `M`=Masculine, `F`=Feminine, `N`=Neuter

**Extra suffix codes**: `C`=Comparative, `S`=Superlative, `T`=Title,
`P`=Person name, `L`=Location, `G`/`LG`/`PG`=Gentilic

**Verb codes** — structure: `V-Tense+VoiceIndicator-Person+Number`

Tense: `P`=Present, `I`=Imperfect, `F`=Future, `A`=Aorist (1st), `2A`=Aorist (2nd),
`R`=Perfect, `L`=Pluperfect, `FP`=Future Perfect

Voice/Mood indicators follow the tense:
- `A`=Active, `M`=Middle, `P`=Passive, `D`=Deponent
- `I`=Indicative, `S`=Subjunctive, `O`=Optative, `M`=Imperative,
  `N`=Infinitive, `P`=Participle

Person+Number: `1S`, `2S`, `3S`, `1P`, `2P`, `3P`

Example: `V-AAI-3S` = Verb, Aorist Active Indicative 3rd Singular;
`V-IAI-3S` = Verb, Imperfect Active Indicative 3rd Singular;
`N-NSF` = Noun Nominative Singular Feminine.

### Edition / TR identification

**TAGNT does not have a single boolean "is-TR" column.** TR presence is encoded
in two redundant ways:

1. **Column 0 type code** (after `=`): `N`=Nestle-Aland, `K`=Textus Receptus
   (Scrivener 1894), `O`=Other. Uppercase = translation-significant difference.
   Lowercase = minor (spelling/accent) difference. Parentheses around a letter
   mean that edition has a variant reading. The edition type codes observed:
   - `NKO` — word in NA, TR, and Others (the vast majority: 94%)
   - `NK(O)` / `NK(o)` — in NA and TR; Others differ
   - `N(K)(O)` / `N(k)(o)` — NA base; TR and Others have variants
   - `K(O)` / `k(o)` — in TR (and Others) but NOT in NA
   - `N(O)` / `n(o)` — in NA (and Others) but NOT in TR
   - `O` / `o` — in Other manuscripts only

2. **Column 5 (`editions`)**: a `+`-separated list of edition sigla, e.g.
   `NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz`. When a word is in TR, `TR` appears here.

**Filter rule for TR normalizer**: include the row if and only if the string `TR`
appears anywhere in the `editions` field (column 5). Set `edition = TR`.

Sample rows illustrating TR-only additions:

```
Mat.1.25#10=K	αὐτῆς (autēs)	of her	G0846=P-GSF	αὐτός=he/she/it/self	TR+Byz			...
Mat.1.25#11=K	τὸν (ton)	<the>	G3588=T-ASM	ὁ=the/this/who	TR+Byz			...
Mat.1.25#12=K	πρωτότοκον, (prōtotokon)	firstborn,	G4416=A-ASM-S	πρωτότοκος=firstborn	TR+Byz	...
```

These three words (type `K`) appear in TR+Byz but not in NA editions; they extend
the base verse wordlist.

---

## Source 2: TAHOT — Translators Amalgamated Hebrew OT

### Canonical URL and license

- Repo: https://github.com/STEPBible/STEPBible-Data
- Path in repo: `Translators Amalgamated OT+NT/`
- License: **CC BY 4.0** — attribution to STEPBible + Tyndale House Cambridge required
- Attribution link: https://github.com/STEPBible

### Downloaded files (data/cache/morph/raw/)

| File | Size |
|------|------|
| `TAHOT_Gen-Deu.txt` | 18 MB |
| `TAHOT_Jos-Est.txt` | 24 MB |
| `TAHOT_Job-Sng.txt` | 9.1 MB |
| `TAHOT_Isa-Mal.txt` | 18 MB |

Four parts covering the entire OT (39 books).

### File structure — same semi-structured format as TAGNT

Preamble (~80 lines), then for each verse: `#`-prefixed summary lines followed by
a `Eng (Heb) Ref & Type<TAB>Hebrew<TAB>...` header line, then one data row per
word.

### Column headers (exact text, tab-separated)

```
Eng (Heb) Ref & Type	Hebrew	Transliteration	Translation	dStrongs	Grammar	Meaning Variants	Spelling Variants	Root dStrong+Instance	Alternative Strongs+Instance	Conjoin word	Expanded Strong tags
```

| Col# | Name | Example |
|------|------|---------|
| 0 | `Eng (Heb) Ref & Type` | `Gen.1.1#01=L` |
| 1 | `Hebrew` | `בְּ/רֵאשִׁ֖ית` |
| 2 | `Transliteration` | `be./re.Shit` |
| 3 | `Translation` | `in/ beginning` |
| 4 | `dStrongs` | `H9003/{H7225G}` |
| 5 | `Grammar` | `HR/Ncfsa` |
| 6 | `Meaning Variants` | (often empty) |
| 7 | `Spelling Variants` | (often empty) |
| 8 | `Root dStrong+Instance` | `H7225G` or `H0853_A` |
| 9 | `Alternative Strongs+Instance` | (often empty) |
| 10 | `Conjoin word` | (not yet implemented) |
| 11 | `Expanded Strong tags` | `H9003=ב=in/{H7225G=רֵאשִׁית=: beginning»first:1_beginning}` |

### Reference scheme

Column 0 format: `Book.Chapter.Verse#WordIdx=TextType`

- `Book` = 3-char English abbreviation (see mapping table below)
- `Chapter`, `Verse` = integer
- When Hebrew versification differs from English, the English ref is used (Hebrew
  ref in parentheses in the field descriptions, but the column 0 uses English ref).
- `WordIdx` = 2-digit 1-based word index within the Hebrew verse
- `TextType` = text source code (see below)

**TAHOT book abbreviation → our CODE**:

| TAHOT | CODE | | TAHOT | CODE |
|-------|------|-|-------|------|
| Gen   | GEN  | | Exo   | EXO  |
| Lev   | LEV  | | Num   | NUM  |
| Deu   | DEU  | | Jos   | JOS  |
| Jdg   | JDG  | | Rut   | RUT  |
| 1Sa   | 1SA  | | 2Sa   | 2SA  |
| 1Ki   | 1KI  | | 2Ki   | 2KI  |
| 1Ch   | 1CH  | | 2Ch   | 2CH  |
| Ezr   | EZR  | | Neh   | NEH  |
| Est   | EST  | | Job   | JOB  |
| Psa   | PSA  | | Pro   | PRO  |
| Ecc   | ECC  | | Sng   | SOS  |
| Isa   | ISA  | | Jer   | JER  |
| Lam   | LAM  | | Ezk   | EZE  |
| Dan   | DAN  | | Hos   | HOS  |
| Jol   | JOE  | | Amo   | AMO  |
| Oba   | OBA  | | Jon   | JON  |
| Mic   | MIC  | | Nam   | NAH  |
| Hab   | HAB  | | Zep   | ZEP  |
| Hag   | HAG  | | Zec   | ZEC  |
| Mal   | MAL  | | | |

**Abbreviation divergences** (TAHOT differs from our CODE):
- `Sng` → `SOS` (Song of Solomon)
- `Ezk` → `EZE` (Ezekiel)
- `Jol` → `JOE` (Joel)
- `Nam` → `NAH` (Nahum)

### Word index derivation

Extract the 2-digit decimal after `#` in column 0. Convert to integer.
The index counts Hebrew words divided by spaces and metheg (as per TAHOT field
descriptions). Prefixes and suffixes (separated by `/` or `\` within column 1)
are part of the same word and share the same index.

Exception documented in TAHOT: Gen.14.17 `#09` counts `כְּדָרְ\־לָעֹ֔מֶר` as one
word despite the metheg separator.

### Strong's field

**Two Strong's fields are relevant**:

- **Column 4 (`dStrongs`)**: disambiguated Strong's for the entire token including
  prefixes/suffixes, slash-separated. Root word is enclosed in `{...}` braces.
  Example: `H9003/{H7225G}` → prefix Strong = `H9003`, root = `H7225G`.
  Form `{H1254A}` when the word has no prefix/suffix.

- **Column 8 (`Root dStrong+Instance`)**: the root's Strong's number without the
  curly braces, with an instance marker (`_A`, `_B`, etc.) for repeated roots in
  the same verse. This is the primary Strong's for the `strong` field in the
  normalized TSV.

**Strong's format in TAHOT**: `H` + 4-digit zero-padded number + optional
disambiguation suffix (a single uppercase letter: `G`, `A`, `B`, etc.).

To get the canonical `strong` field:
1. Take column 8.
2. Strip any instance marker (`_A`, `_B`, etc.) from the end.
3. Strip the single-letter disambiguation suffix from the end of the numeric
   portion: `H7225G` → `H7225`; `H1254A` → `H1254`; `H0853` stays `H0853`.
4. Numbers 9000–9999 are Tyndale-specific non-lexical tags for grammatical
   particles (prefixes, suffixes, punctuation); these are real Strong's-like
   entries in TBESG/TBESH, not in the original Strong's Hebrew.

**Padded form**: `H` + 4-digit already present — no further padding needed.

### Morph code (TAHOT Hebrew/Aramaic)

Column 5 (`Grammar`). Based on OpenScriptures morphology codes (Westminster-
compatible). Full reference: TEHMC.txt (downloaded).
Also see: http://openscriptures.github.io/morphhb/parsing/HebrewMorphologyCodes.html

When a word has prefixes/suffixes, codes are slash-separated, mirroring the
slash-separated dStrongs in column 4.

**First character**: `H`=Hebrew, `A`=Aramaic. When codes are joined for a
multi-element word, the first character becomes `/` for subsequent elements.
Example: `HC/Td/Ncfsa` = Hebrew Conjunction / Article definite / Noun common
feminine singular absolute.

**Function codes** (character after language prefix):

| Code | Meaning |
|------|---------|
| `C` | Conjunction |
| `c` | Consecutive conjunction |
| `D` | Adverb |
| `R` | Preposition |
| `Rd` | Preposition (Definite) |
| `T` | Article |
| `Td` | Definite article |
| `To` | Object marker |
| `S` | Suffix |
| `N` | Noun/Name/Pronoun |
| `A` | Adjective |
| `V` | Verb |

**Noun/Adjective suffix** — format `Ncfsa`:
- `N` = Noun (or Pronoun `Np`, Adjective `A`)
- `c`/`p` = common/proper
- `f`/`m` = feminine/masculine
- `s`/`p`/`d` = singular/plural/dual
- `a`/`c` = absolute/construct

**Verb suffix** — format `Vqp3ms`:
- `V` = Verb
- Stem: `q`=Qal, `N`=Niphal, `p`=Piel, `P`=Pual, `h`=Hiphil, `H`=Hophal,
  `t`=Hithpael, `A`=Aphel (Aramaic), etc.
- Form (per the TEHMC.txt reference codes):
  `p`=Perfect (qatal), `q`=Sequential perfect (weqatal),
  `i`=Imperfect (yiqtol), `w`=Sequential imperfect (wayyiqtol),
  `j`=Jussive, `v`=Imperative, `u`=Conjunction+imperfect,
  `r`=Participle active, `s`=Participle passive,
  `a`=Infinitive absolute, `c`=Infinitive construct
- Person: `1`, `2`, `3`
- Gender: `m`/`f`/`c`
- Number: `s`/`p`/`d`

Example: `HVqp3ms` = Hebrew Verb Qal Perfect 3rd Masculine Singular.

### Edition / WLC identification

**All TAHOT rows are from the Masoretic text (Leningrad Codex, WLC basis).**
Set `edition = WLC` for all TAHOT rows.

Column 0 type code after `=` indicates text source:
- `L` = Leningrad (primary text, ~97% of words)
- `Q` = Qere (scribal marginal correction; translators follow Q over K)
- `K` = Ketiv (original written text, recorded as variant)
- `R` = Restored text (Jos 21:36–37, Neh 7:67b from parallel passages)
- `X` = Extra words from LXX reconstructed in BHS/BHK apparatus

For the normalizer: include rows with type `L` and `Q` (the text translators
follow). Rows with `K` are variants. Rows `R` and `X` are annotated additions;
include them but note the type.

Sample rows:

```
Gen.1.1#01=L	בְּ/רֵאשִׁ֖ית	be./re.Shit	in/ beginning	H9003/{H7225G}	HR/Ncfsa		H7225G		H9003=ב=in/{H7225G=רֵאשִׁית=: beginning»first:1_beginning}
Gen.1.1#02=L	בָּרָ֣א	ba.Ra'	he created	{H1254A}	HVqp3ms		H1254A		{H1254A=בָּרָא=to create}
Gen.1.1#03=L	אֱלֹהִ֑ים	'E.lo.Him	God	{H0430G}	HNcmpa		H0430G		{H0430G=אֱלֹהִים=God»LORD@Gen.1.1-Heb}
Gen.1.1#07=L	הָ/אָֽרֶץ\׃	ha./'A.retz	the/ earth	H9009/{H0776G}\H9016	HTd/Ncfsa		H0776G		H9009=ה=the/{H0776G=אֶ֫רֶץ=: country;_planet»land:2_country;_planet}\H9016=׃=verseEnd
```

---

## Source 3: Lexicons

### 3a. Strong's Greek Dictionary

- Source: openscriptures/strongs (GitHub)
- File: `strongs-greek.xml` (2.6 MB)
- Format: XML with `<entry strongs="...">` elements containing
  `<greek BETA="..." unicode="..." translit="...">` (e.g.
  `<greek BETA="*A" unicode="Α" translit="A"/>` — `BETA` is Beta-code, `unicode`
  is the real Greek lemma, `translit` is SBL-style transliteration),
  plus `<strongs_def>`, `<kjv_def>`, `<strongs_derivation>`
- License: **Public Domain** — Strong's 1890 (James Strong, S.T.D., LL.D.)
  XML encoding by Ulrik Petersen, 2006. "Public Domain -- Copy Freely."
- URL: https://github.com/openscriptures/strongs

### 3b. Strong's Hebrew Dictionary

- Source: openscriptures/strongs (GitHub)
- File: `strongs-hebrew.xml` (6.2 MB)
- Format: XML, same structure as Greek
- License: **Public Domain** — same as above
- URL: https://github.com/openscriptures/strongs

### 3c. STEPBible TBESG — Translators Brief Greek Lexicon (Abbott-Smith base)

- Source: STEPBible-Data/Lexicons/
- File: `TBESG.txt` (4.6 MB)
- Format: semi-structured TSV, columns: `eStrong  dStrong  uStrong  Greek  Transliteration  Morph  Gloss  Meaning` — note the real header for column 8 (`Meaning`) reads verbatim: `Abbott-Smith lexicon (AS), with gaps occationally filled from edited versions of  Middle LSJ` [sic]
- License: **CC BY 4.0** — STEPBible + Tyndale House Cambridge
- Meaning field: based on Abbott-Smith (1922), which is **Public Domain**
  (Abbott-Smith, G., *A Manual Greek Lexicon of the New Testament*, 1922).
  Tyndale House edits and additions also CC-BY.
- URL: https://github.com/STEPBible/STEPBible-Data

### 3d. STEPBible TBESH — Translators Brief Hebrew Lexicon

- Source: STEPBible-Data/Lexicons/
- File: `TBESH.txt` (3.2 MB)
- Format: semi-structured TSV, same column structure as TBESG
- License: **CC BY 4.0** for structure and Tyndale edits
- **WARNING**: The `Meaning` field in TBESH is derived from Abridged BDB by
  Online Bible (© Larry Pierce, OnlineBible.net). TBESH header states:
  "Permission should be gained from Online Bible before these definitions are
  applied in any project." **Do NOT ship TBESH meaning text without permission.**
- For Hebrew definitions, use the PD source below instead.
- URL: https://github.com/STEPBible/STEPBible-Data

### 3e. Brown-Driver-Briggs Hebrew Lexicon (BDB)

- Source: openscriptures/HebrewLexicon (GitHub)
- File: `BrownDriverBriggs.xml` (2.8 MB)
- Format: XML with `<entry id="a.xx.xx">` elements. **IDs are alphabetic
  positional keys** (e.g. `a.aa.aa`, `a.ab.ab`, `a.ac.ac`), NOT Strong's numbers;
  there is no `strongs=` attribute on `<entry>`. Each entry holds `<w>` (Hebrew
  word), `<pos>`, `<def>`, and `<ref r="Book.C.V">` citations.
- **Strong's → BDB lookup requires a cross-reference layer** (Task 7 depends on
  this): the Strong's number is not in BrownDriverBriggs.xml directly. Map
  Strong's → BDB entry ID via TBESH (the `eStrong` field maps Strong's numbers to
  openscriptures BDB entry IDs); openscriptures also ships `LexicalIndex.xml` /
  `AugIndex.xml` in the same HebrewLexicon repo, which link Strong's `<entry>`
  augmented IDs to the alphabetic BDB IDs. Either index is the join key from a
  Strong's number to its BDB `id="a.xx.xx"` entry.
- License: **Public Domain** — BDB first published 1906; out of copyright.
  OpenScriptures XML encoding is also PD per their project terms.
- URL: https://github.com/openscriptures/HebrewLexicon

---

## Source 4: Domain spine — decision and fallback

### Question: does an open Strong's→Louw-Nida domain-NUMBER mapping exist?

**Research findings**:

1. **MACULA Greek** (Clear-Bible/macula-greek) contains `@ln` (Louw-Nida) and
   `@domain` columns with L-N section references (e.g., `33.38`, `10.24`).
   However, the LICENSE.md states this data comes from the UBS MARBLE project
   and is "Used with permission" — **NOT CC-BY**. It cannot be redistributed
   without UBS permission.

2. **STEPBible TBESG/TBESH**: contain no Louw-Nida domain numbers. Searching
   both files confirms no domain-number fields. The Sub-meaning column in TAGNT
   provides English semantic labels (e.g., `book`, `origin`, `to beget`) derived
   from TBESG, which are useful but are string labels, not L-N domain integers.

3. **openscriptures repos** (morphhb, strongs, HebrewLexicon): no Louw-Nida
   domain mapping present.

4. **SIL SDBG/SDBH** (semanticdictionary.org / marble.bible): the site resolves to
   the UBS MARBLE project. License unclear; appears to require permission.

**Conclusion**: No confirmed open (CC-BY or PD) Strong's→Louw-Nida domain-number
mapping exists as of 2026-06-27.

### Fallback decision: STEPBible TBESG/TBESH Sub-meaning labels

**Selected fallback**: the `Sub-meaning` column (col 9) in TAGNT and the
`Expanded Strong tags` semantic labels in TAHOT, sourced from TBESG/TBESH.

- License: CC-BY 4.0 (STEPBible) — compatible with our constraints
- These are English semantic-category labels, not integer domain numbers
- They provide useful semantic disambiguation (person names, sub-meanings like
  `book`, `to beget`, `the`, etc.) without the L-N copyright problem

If a numeric domain classification is needed in the future, the correct path is
to negotiate permission from UBS/MARBLE, or to use the SIL SDBG/SDBH data if
confirmed CC-BY. That is a future decision outside this task's scope.

---

## Morphology code reference files

Both downloaded and available for decoder implementation:

| File | Size | Content |
|------|------|---------|
| `TEGMC.txt` (457 KB) | CC-BY | Full expansion of every Greek morph code used in TAGNT |
| `TEHMC.txt` (386 KB) | CC-BY | Full expansion of every Hebrew/Aramaic morph code used in TAHOT |

TEGMC has two sections: "Brief" (lexicon-style) and "Full" (tagged-text).
Use the Full section (starts at line 124) for TAGNT morph codes.
TEHMC section boundary at line 128.

---

## Domain sources (Task 8)

Semantic domains are attached to each lexicon entry from MACULA linguistic datasets.

### Greek: Louw-Nida section references (source label `ln-map`)

- **File:** `Nestle1904/tsv/macula-greek-Nestle1904.tsv`, column `ln`
- **Format:** space-separated LN section references, e.g. `"25.43 25.44"`.
  A single Strong's number may map to multiple LN sections when the lemma
  appears in different sense-contexts in the NT.
- **Join key:** `strong` column (bare integer, e.g. `"26"`) normalised to `G####`.
- **Coverage:** 5079/5122 corpus Greek strongs (99.2%) received at least one LN code.
- **License:** CC-BY 4.0, Clear Bible Inc.
- **URL:** https://github.com/Clear-Bible/macula-greek

### Hebrew: SDBH LexDomain codes (source label `sdbh`)

- **File:** `WLC/nodes/{book}-{chapter}.xml`, attribute `LexDomain` on `<m>` elements
- **Format:** 12-digit hierarchical code, e.g. `"002003003004"`.
  Multiple codes per lemma are possible; all observed values are stored.
- **Join key:** `oshb-strongs` attribute (integer + optional letter suffix, e.g. `"1254a"`)
  normalised to `H####` by stripping the letter suffix and zero-padding.
- **Coverage:** 7564/8426 corpus Hebrew strongs (89.8%) received at least one SDBH code.
  The remaining ~10% are morphology-only entries (particles, prefixes, proper nouns)
  that MACULA does not assign a LexDomain to.
- **License:** CC-BY 4.0, Clear Bible Inc.
- **URL:** https://github.com/Clear-Bible/macula-hebrew

### Cache location

Both maps are cached (gitignored) under:
  `data/cache/morph/raw/macula/grc_domain_map.json`
  `data/cache/morph/raw/macula/hbo_domain_map.json`

The maps are built once by `tools/fetch_macula.py` and reused by `tools/build_lexicon.py`.
Re-run `python -m tools.fetch_macula --force` to refresh from MACULA upstream.

---

## Attribution requirements

Any downstream use of data from these sources must include:

| Source | Required attribution |
|--------|---------------------|
| TAGNT / TAHOT / TBESG / TBESH / TEGMC / TEHMC | "Data created by www.STEPBible.org based on work at Tyndale House Cambridge (CC BY 4.0). Source: https://github.com/STEPBible" |
| Strong's Greek/Hebrew XML | "Public Domain — Strong's Exhaustive Concordance, James Strong 1890. XML by Ulrik Petersen." |
| BrownDriverBriggs.xml | "Public Domain — Brown, Driver, Briggs, Hebrew and English Lexicon, 1906. XML by openscriptures.org." |
| Abbott-Smith (via TBESG) | "G. Abbott-Smith, A Manual Greek Lexicon of the New Testament, 1922. Public Domain." |
| MACULA Greek / Hebrew | "MACULA Greek/Hebrew Linguistic Datasets, Clear Bible Inc., CC-BY 4.0. https://github.com/Clear-Bible/macula-greek and https://github.com/Clear-Bible/macula-hebrew" |

---

## Summary of deviations from the brief's assumptions

1. **TAGNT is not a flat named-column TSV.** Each verse block has its own
   `Word & Type<TAB>...` header line (repeated hundreds of times). Parsers must
   skip lines starting with `#` and lines whose first field is `Word & Type`.

2. **There is no explicit boolean "is-TR" column in TAGNT.** TR presence is
   determined by checking whether `TR` appears in the `editions` field (col 5),
   or whether `K` (uppercase or lowercase) appears in the edition type code of
   col 0. Both signals are present; the col-5 check is simpler and unambiguous.

3. **Strong's numbers in TAGNT already include the 4-digit zero-padding**; no
   padding is needed. Only disambiguation letter suffixes need stripping.

4. **TAHOT word index counts the Hebrew words** (space/metheg-divided), not the
   English word count. The prefix-root-suffix elements within one Hebrew word
   are joined with `/` or `\` and share one index row.

5. **TBESH Meaning field requires Online Bible permission** and cannot be used
   as-is. Use openscriptures BrownDriverBriggs.xml (PD) for Hebrew definitions.

6. **UPDATE (Task 8): An open Louw-Nida domain mapping DOES exist via MACULA.**
   The original assessment ("no open mapping") was based on UBS MARBLE (restricted).
   MACULA Greek (Clear Bible, CC-BY 4.0) carries Louw-Nida section references in
   the `ln` column of `Nestle1904/tsv/macula-greek-Nestle1904.tsv`. MACULA Hebrew
   carries SDBH LexDomain codes in the `LexDomain` attribute of WLC node XML files.
   Both are usable without permission. See the Domain Sources section below.
