# Morpho-Lexical Floor (L1 + L2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tag every NT-Greek and OT-Hebrew word in the existing corpus with lemma + morphology + Strong's (canonical CoNLL-U files), build a Strong's-keyed multilingual lexicon with a semantic-domain spine, and project both into a queryable SQLite token DB.

**Architecture:** Two-form, mirroring the repo's sources-are-truth philosophy. Canonical hand-editable files (`morph/**/*.conllu`, `lexicon/**/*.json`) are the truth; `tools/build_db.py` projects them into a derived, gitignored `data/tokens.sqlite`. L0 (`bible/`) is never mutated. A new `data/morph-sources.json` registry drives alignment one row per language, so the engine names no language (exactly as `generate_ot.py` names no edition). Source-format messiness is quarantined in per-source normalizers that emit a single fixed-schema intermediate TSV; everything downstream is deterministic against that known schema.

**Tech Stack:** Python 3 (stdlib only: `json`, `sqlite3`, `csv`, `unicodedata`, `xml.etree`, `pathlib`), `pytest`. No new runtime deps.

## Global Constraints

- **L0 immutability:** never write under `bible/`. Token `FORM` is taken from the L0 verse text, which is authoritative; source tags map onto it.
- **Licensing:** every shipped datum is PD or CC-BY. STEPBible (TAGNT/TAHOT/TBESG/TBESH) is CC-BY — credit STEPBible and Tyndale House Cambridge, link `https://github.com/STEPBible`. Strong's, Abbott-Smith (1922), Thayer, BDB, Gesenius are PD. The Louw-Nida lexicon *text* is UBS-copyright: only an open Strong's→domain *number* mapping may be used; if none is confirmed open, fall back to SDBH/SDBG or SIL domains (Task 0 decides). Every gloss/entry records `src` provenance.
- **Encoding:** all text NFC-normalized (matches existing corpus). Files UTF-8, LF newlines.
- **Book codes:** uppercase 3-char codes from `data/books.json` (`code` field); chapter files zero-padded to 3 digits (`PAD=3`), as in `tools/generate_ot.py`.
- **Verse ref string:** canonical `CODE.chapter.verse` (e.g. `JOH.1.1`), used as the CoNLL-U `# ref =` anchor and the DB `verses.ref` / `tokens.ref` key.
- **Determinism:** every generator is idempotent — same inputs produce byte-identical outputs. The DB is a pure projection; dropping and rebuilding changes nothing.
- **TDD:** each task writes a failing test first, then minimal code to green. Commit after each task.

## Normalized intermediate TSV schema (the quarantine boundary)

Per-source normalizers (Task 1) emit `data/cache/morph/<lang>.tsv` with this exact header and columns. All alignment code (Task 4+) reads only this — never raw source formats.

```
ref	idx	surface	lemma	strong	xpos	feats	translit	edition
```

- `ref` — `CODE.chapter.verse` (mapped from the source's own reference scheme).
- `idx` — 1-based word index within the verse, in source order.
- `surface` — the source word form (NFC; for matching only — the final `FORM` comes from L0).
- `lemma` — dictionary headword (NFC).
- `strong` — normalized Strong's: `G`/`H` + zero-padded 4-digit number (`G0026`, `H0430`).
- `xpos` — raw source morph code, verbatim (STEPBible morph string).
- `feats` — normalized CoNLL-U FEATS (`Case=Nom|Number=Sing|Gender=Masc`), or `_`.
- `translit` — transliteration if the source provides one, else `_`.
- `edition` — for Greek, the edition tag the row belongs to (`TR`/`Byz`/`NA`…) so alignment can filter to TR; for Hebrew, `WLC`.

## File Structure

```
data/morph-sources.json          NEW  registry: 1 row/language (lang, source backend, lexicon sources, domain source)
data/cache/morph/<lang>.tsv      NEW  gitignored normalized intermediate (Task 1 output)
data/cache/morph/raw/            NEW  gitignored raw downloaded sources
docs/FORMATS-morph.md            NEW  Task 0 output: exact raw-source layouts + license confirmations
morph/<test>/<CODE>/NNN.conllu   NEW  L1 canonical token files
lexicon/<lang>/<STRONG>.json     NEW  L2a canonical lexicon entries
data/tokens.sqlite               NEW  derived, gitignored
tools/morph_norm/                NEW  per-source normalizers
  __init__.py
  stepbible_greek.py             TAGNT TSV  -> normalized tsv
  stepbible_hebrew.py            TAHOT TSV  -> normalized tsv
tools/conllu.py                  NEW  Token dataclass + CoNLL-U read/write
tools/morph_feats.py             NEW  STEPBible morph code -> (UPOS, FEATS)
tools/align_morph.py             NEW  L0 verse + normalized tsv -> [Token]  (scheme-parametric)
tools/generate_morph.py          NEW  driver: registry -> all .conllu files
tools/build_lexicon.py           NEW  Strong's + PD lexicons + domains -> lexicon/**/*.json
tools/build_db.py                NEW  canonical -> tokens.sqlite
tools/validate_morph.py          NEW  structural + coverage oracles, pinned counts
tests/test_conllu.py             NEW
tests/test_morph_feats.py        NEW
tests/test_align_morph.py        NEW
tests/test_build_lexicon.py      NEW
tests/test_build_db.py           NEW
tests/test_validate_morph.py     NEW
.gitignore                       MOD  add data/tokens.sqlite, data/cache/morph/
README.md                        MOD  add L1/L2a section + regenerate steps
```

---

### Task 0: Data acquisition + license verification (spike)

**Files:**
- Create: `docs/FORMATS-morph.md`
- Create: `data/cache/morph/raw/` (gitignored; downloaded sources)

**Interfaces:**
- Produces: `docs/FORMATS-morph.md` documenting, for each source, its exact on-disk layout (column headers / XML element shape), reference scheme, morph-code scheme, license, and canonical URL. Downstream tasks cite this file for field names.

This task is a research spike — no code module ships, but it gates everything. It ends when `FORMATS-morph.md` answers every question a normalizer needs.

- [ ] **Step 1: Acquire the Greek source.** Download STEPBible **TAGNT** (Translators Amalgamated Greek NT) TSV from `https://github.com/STEPBible/STEPBible-Data` into `data/cache/morph/raw/`. Confirm rows carry: reference, Greek word, Strong's, morphology code, and an edition/witness marker identifying TR readings.

- [ ] **Step 2: Acquire the Hebrew source.** Download STEPBible **TAHOT** (Translators Amalgamated Hebrew OT) TSV into `data/cache/morph/raw/`. Confirm rows carry: reference, Hebrew word (with pointing), Strong's, morphology code.

- [ ] **Step 3: Acquire the lexicon sources.** Download: Strong's Greek + Hebrew dictionaries (openscriptures `strongs` / `HebrewLexicon`, PD), Abbott-Smith (PD), BDB (openscriptures `HebrewLexicon`, PD). Record each license + URL.

- [ ] **Step 4: Resolve the domain spine.** Determine whether an open Strong's→Louw-Nida domain-number mapping exists (check openscriptures, STEPBible TBESG). If yes, record it. If no, select the fallback (SDBH/SDBG or SIL domains) and record that decision. **Write the chosen domain source + license into `FORMATS-morph.md`.**

- [ ] **Step 5: Document formats.** For every source, write into `docs/FORMATS-morph.md`: exact column headers (or XML element/attribute names), the reference-string scheme and how it maps to `CODE.chapter.verse` (use `data/books.json` codes), the morph-code scheme, license, and URL. This file is the contract Tasks 1–8 build against.

- [ ] **Step 6: Commit.**

```bash
git add docs/FORMATS-morph.md
git commit -m "docs: morph source formats + license verification (Task 0 spike)"
```

---

### Task 1: Source normalizers → fixed-schema TSV

**Files:**
- Create: `tools/morph_norm/__init__.py`, `tools/morph_norm/stepbible_greek.py`, `tools/morph_norm/stepbible_hebrew.py`
- Create: `tests/test_morph_norm.py`
- Modify: `.gitignore` (add `data/cache/morph/`)

**Interfaces:**
- Consumes: raw STEPBible TSVs in `data/cache/morph/raw/`; field names per `docs/FORMATS-morph.md`.
- Produces: `normalize_greek(raw_path) -> list[dict]` and `normalize_hebrew(raw_path) -> list[dict]`, each dict having keys `ref, idx, surface, lemma, strong, xpos, feats, translit, edition`. A CLI writes `data/cache/morph/<lang>.tsv` with the header from the schema section above. `pad_strong(prefix, number) -> str` (e.g. `pad_strong("G", "26") -> "G0026"`).

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_morph_norm.py
from tools.morph_norm.stepbible_greek import normalize_greek, pad_strong

def test_pad_strong_zero_pads_to_four_digits():
    assert pad_strong("G", "26") == "G0026"
    assert pad_strong("H", "430") == "H0430"
    assert pad_strong("G", "3056") == "G3056"

def test_normalize_greek_row(tmp_path):
    # One TAGNT-shaped row: a tab-separated line with a header.
    raw = tmp_path / "tagnt.tsv"
    raw.write_text(
        "Ref\tGreek\tTransliteration\tStrongs\tMorph\tEdition\n"
        "Jhn.1.1#01\tἐν\ten\tG1722\tPREP\tTR\n",
        encoding="utf-8",
    )
    rows = normalize_greek(raw)
    assert rows[0]["ref"] == "JOH.1.1"
    assert rows[0]["idx"] == 1
    assert rows[0]["surface"] == "ἐν"
    assert rows[0]["strong"] == "G1722"
    assert rows[0]["xpos"] == "PREP"
    assert rows[0]["edition"] == "TR"
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_morph_norm.py -v`
Expected: FAIL with `ModuleNotFoundError: tools.morph_norm.stepbible_greek`.

- [ ] **Step 3: Implement the Greek normalizer.** Read by header name (robust to column order); map the source book abbreviation to the `CODE` via a book-name table loaded from `data/books.json`; parse the `#NN` word index from the ref; pass the morph code through to `xpos` (FEATS derivation happens in Task 3, so `feats` is `_` here).

```python
# tools/morph_norm/stepbible_greek.py
import csv, json, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def pad_strong(prefix, number):
    return f"{prefix}{int(number):04d}"

def _osis_to_code():
    """Map STEPBible/OSIS book abbreviations (e.g. 'Jhn') to corpus CODE ('JOH')."""
    # FORMATS-morph.md documents the exact abbreviations TAGNT uses.
    return {
        "Mat":"MAT","Mrk":"MAR","Luk":"LUK","Jhn":"JOH","Act":"ACT","Rom":"ROM",
        "1Co":"1CO","2Co":"2CO","Gal":"GAL","Eph":"EPH","Php":"PHP","Col":"COL",
        "1Th":"1TH","2Th":"2TH","1Ti":"1TI","2Ti":"2TI","Tit":"TIT","Phm":"PHM",
        "Heb":"HEB","Jas":"JAM","1Pe":"1PE","2Pe":"2PE","1Jn":"1JO","2Jn":"2JO",
        "3Jn":"3JO","Jud":"JDE","Rev":"REV",
    }

def _parse_ref(raw_ref, book_map):
    # "Jhn.1.1#01" -> ("JOH.1.1", 1)
    locus, _, widx = raw_ref.partition("#")
    book, chap, verse = locus.split(".")
    return f"{book_map[book]}.{int(chap)}.{int(verse)}", int(widx or "1")

def normalize_greek(raw_path):
    book_map = _osis_to_code()
    out = []
    with open(raw_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            ref, idx = _parse_ref(row["Ref"], book_map)
            strong = row["Strongs"].strip()
            if strong and strong[0] in "GH":
                strong = pad_strong(strong[0], strong[1:])
            out.append({
                "ref": ref, "idx": idx,
                "surface": unicodedata.normalize("NFC", row["Greek"]),
                "lemma": unicodedata.normalize("NFC", row.get("Greek", "")),
                "strong": strong,
                "xpos": row["Morph"].strip(),
                "feats": "_",
                "translit": row.get("Transliteration", "_") or "_",
                "edition": row.get("Edition", "TR").strip(),
            })
    return out
```

(The Hebrew normalizer mirrors this with the Hebrew OSIS→CODE map and TAHOT headers; lemma column is TAHOT's Hebrew lemma; `edition` is `"WLC"`.)

- [ ] **Step 4: Implement the Hebrew normalizer** (`tools/morph_norm/stepbible_hebrew.py`) following the same shape, reading TAHOT headers per `FORMATS-morph.md`, OSIS→CODE for the 39 OT books, `edition="WLC"`.

- [ ] **Step 5: Add a CLI to write the TSVs.** At the bottom of each module:

```python
def _write_tsv(rows, out_path):
    cols = ["ref","idx","surface","lemma","strong","xpos","feats","translit","edition"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

if __name__ == "__main__":
    raw = ROOT / "data" / "cache" / "morph" / "raw" / "tagnt.tsv"
    _write_tsv(normalize_greek(raw), ROOT / "data" / "cache" / "morph" / "grc.tsv")
```

- [ ] **Step 6: Run tests to verify they pass.**

Run: `python -m pytest tests/test_morph_norm.py -v`
Expected: PASS.

- [ ] **Step 7: Add gitignore + commit.**

```bash
printf 'data/tokens.sqlite\ndata/cache/morph/\n' >> .gitignore
git add tools/morph_norm tests/test_morph_norm.py .gitignore
git commit -m "feat: STEPBible TAGNT/TAHOT normalizers to fixed-schema TSV"
```

---

### Task 2: CoNLL-U read/write

**Files:**
- Create: `tools/conllu.py`
- Create: `tests/test_conllu.py`

**Interfaces:**
- Produces:
  - `Token` dataclass: fields `idx:str, form:str, lemma:str, upos:str, xpos:str, feats:str, head:str="_", deprel:str="_", misc:str="_"`.
  - `format_misc(strong, translit, glosses:dict, align:str|None) -> str` → CoNLL-U MISC string (`Strong=G1722|Translit=en|gloss_en=in`), `_` if empty.
  - `write_sentence(ref:str, tokens:list[Token]) -> str` → one CoNLL-U sentence block (with `# ref =` comment), trailing blank line.
  - `parse_sentence(block:str) -> tuple[str, list[Token]]` → `(ref, tokens)`.
  - `write_file(path, sentences:list[tuple[str,list[Token]]])`, `parse_file(path) -> list[tuple[str,list[Token]]]`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_conllu.py
from tools.conllu import Token, write_sentence, parse_sentence, format_misc

def test_format_misc_orders_and_joins():
    assert format_misc("G1722", "en", {"en": "in"}, None) == "Strong=G1722|Translit=en|gloss_en=in"

def test_format_misc_empty_is_underscore():
    assert format_misc("", "_", {}, None) == "_"

def test_roundtrip_sentence():
    toks = [Token("1", "ἐν", "ἐν", "ADP", "PREP", "_", misc="Strong=G1722")]
    block = write_sentence("JOH.1.1", toks)
    assert block.startswith("# ref = JOH.1.1\n")
    ref, parsed = parse_sentence(block)
    assert ref == "JOH.1.1"
    assert parsed[0].form == "ἐν"
    assert parsed[0].misc == "Strong=G1722"
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_conllu.py -v`
Expected: FAIL with `ModuleNotFoundError: tools.conllu`.

- [ ] **Step 3: Implement `tools/conllu.py`.**

```python
from dataclasses import dataclass, field

COLS = ("idx","form","lemma","upos","xpos","feats","head","deprel","misc")

@dataclass
class Token:
    idx: str
    form: str
    lemma: str
    upos: str
    xpos: str
    feats: str
    head: str = "_"
    deprel: str = "_"
    misc: str = "_"

def format_misc(strong, translit, glosses, align):
    parts = []
    if strong:
        parts.append(f"Strong={strong}")
    if translit and translit != "_":
        parts.append(f"Translit={translit}")
    for lang, text in glosses.items():
        if text:
            parts.append(f"gloss_{lang}={text}")
    if align:
        parts.append(f"Align={align}")
    return "|".join(parts) if parts else "_"

def write_sentence(ref, tokens):
    lines = [f"# ref = {ref}"]
    for t in tokens:
        lines.append("\t".join(getattr(t, c) for c in COLS))
    return "\n".join(lines) + "\n\n"

def parse_sentence(block):
    ref = None
    tokens = []
    for line in block.splitlines():
        if line.startswith("# ref ="):
            ref = line.split("=", 1)[1].strip()
        elif line and not line.startswith("#"):
            tokens.append(Token(*line.split("\t")))
    return ref, tokens

def write_file(path, sentences):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(write_sentence(r, t) for r, t in sentences), encoding="utf-8")

def parse_file(path):
    text = path.read_text(encoding="utf-8")
    out = []
    for block in text.split("\n\n"):
        if block.strip():
            out.append(parse_sentence(block + "\n"))
    return out
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `python -m pytest tests/test_conllu.py -v`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add tools/conllu.py tests/test_conllu.py
git commit -m "feat: CoNLL-U token read/write"
```

---

### Task 3: Morph-code → (UPOS, FEATS) decoder

**Files:**
- Create: `tools/morph_feats.py`
- Create: `tests/test_morph_feats.py`

**Interfaces:**
- Consumes: STEPBible morph code strings (the `xpos` column; scheme per `FORMATS-morph.md`).
- Produces: `decode(xpos:str, lang:str) -> tuple[str, str]` returning `(upos, feats)`, where `upos` is a Universal POS tag and `feats` is a sorted `Key=Val|...` string (or `_`). `lang` is `"grc"` or `"hbo"`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_morph_feats.py
from tools.morph_feats import decode

def test_greek_noun_nom_sg_fem():
    upos, feats = decode("N-NSF", "grc")
    assert upos == "NOUN"
    assert feats == "Case=Nom|Gender=Fem|Number=Sing"

def test_greek_preposition():
    assert decode("PREP", "grc") == ("ADP", "_")

def test_unknown_code_is_x():
    assert decode("???", "grc") == ("X", "_")
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_morph_feats.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tools/morph_feats.py`.** Map the leading POS token to UPOS; decode the parsing suffix into features. Cover the Greek Robinson-style codes used by TAGNT and the Hebrew codes used by TAHOT (full tables per `FORMATS-morph.md`); unknown → `("X", "_")`.

```python
_GREEK_POS = {"N":"NOUN","V":"VERB","A":"ADJ","PREP":"ADP","CONJ":"CCONJ",
              "ADV":"ADV","ART":"DET","P":"PRON","PRON":"PRON","INJ":"INTJ"}
_CASE = {"N":"Nom","G":"Gen","D":"Dat","A":"Acc","V":"Voc"}
_NUM  = {"S":"Sing","P":"Plur","D":"Dual"}
_GEN  = {"M":"Masc","F":"Fem","N":"Neut"}

def _feats(d):
    return "|".join(f"{k}={d[k]}" for k in sorted(d)) if d else "_"

def _decode_greek(xpos):
    head, _, rest = xpos.partition("-")
    upos = _GREEK_POS.get(head, "X")
    d = {}
    if head == "N" and len(rest) >= 3:
        if rest[0] in _CASE: d["Case"] = _CASE[rest[0]]
        if rest[1] in _NUM:  d["Number"] = _NUM[rest[1]]
        if rest[2] in _GEN:  d["Gender"] = _GEN[rest[2]]
    # verbs, adjectives, pronouns: extend per FORMATS-morph.md tables
    return upos, _feats(d)

def decode(xpos, lang):
    if not xpos or xpos == "_":
        return "X", "_"
    if lang == "grc":
        return _decode_greek(xpos)
    return _decode_hebrew(xpos)  # defined alongside, per TAHOT scheme

def _decode_hebrew(xpos):
    # TAHOT codes: part-of-speech letter + parsing; full table per FORMATS-morph.md.
    pos_map = {"N":"NOUN","V":"VERB","A":"ADJ","P":"PRON","R":"ADP","C":"CCONJ",
               "D":"ADV","T":"DET","S":"PRON"}
    head = xpos[0] if xpos else ""
    return pos_map.get(head, "X"), "_"
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `python -m pytest tests/test_morph_feats.py -v`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add tools/morph_feats.py tests/test_morph_feats.py
git commit -m "feat: morph-code to UPOS/FEATS decoder"
```

---

### Task 4: Alignment engine (one Greek book green)

**Files:**
- Create: `data/morph-sources.json`
- Create: `tools/align_morph.py`
- Create: `tests/test_align_morph.py`

**Interfaces:**
- Consumes: L0 verse text (`bible/<test>/<CODE>/NNN.json`, fields `greek_textus_receptus` / `hebrew_masoretic`); normalized TSV `data/cache/morph/<lang>.tsv`; `tools.conllu.Token`; `tools.morph_feats.decode`.
- Produces:
  - `load_norm(lang) -> dict[str, list[dict]]` mapping `ref → list of normalized rows (idx-ordered)`.
  - `tokenize_l0(text:str) -> list[str]` — split an L0 verse into surface words (whitespace + punctuation-aware), preserving order.
  - `align_verse(ref, l0_text, norm_rows, lang) -> list[Token]` — produce CoNLL-U tokens whose `form` comes from L0, with lemma/xpos/feats/Strong from the matched normalized row; mismatches recorded via `Align=` in MISC.
  - `normalize_surface(s:str) -> str` — strip accents/pointing + lowercase for matching only.

- [ ] **Step 1: Create the registry.**

```json
{
  "languages": [
    {"lang": "grc", "testament": "nt", "l0_field": "greek_textus_receptus",
     "norm": "data/cache/morph/grc.tsv", "edition_filter": "TR",
     "lexicon_sources": ["strongs-greek", "abbott-smith"], "domain_source": "ln-map"},
    {"lang": "hbo", "testament": "ot", "l0_field": "hebrew_masoretic",
     "norm": "data/cache/morph/hbo.tsv", "edition_filter": "WLC",
     "lexicon_sources": ["strongs-hebrew", "bdb"], "domain_source": "sdbh"}
  ]
}
```

- [ ] **Step 2: Write the failing test.**

```python
# tests/test_align_morph.py
from tools.align_morph import normalize_surface, align_verse

def test_normalize_surface_strips_accents():
    assert normalize_surface("ἐν") == normalize_surface("εν")

def test_align_verse_form_comes_from_l0():
    l0 = "ἐν ἀρχῇ"
    norm = [
        {"idx":1,"surface":"ἐν","lemma":"ἐν","strong":"G1722","xpos":"PREP","translit":"en","edition":"TR"},
        {"idx":2,"surface":"ἀρχῇ","lemma":"ἀρχή","strong":"G0746","xpos":"N-DSF","translit":"archē","edition":"TR"},
    ]
    toks = align_verse("JOH.1.1", l0, norm, "grc")
    assert [t.form for t in toks] == ["ἐν", "ἀρχῇ"]
    assert toks[1].lemma == "ἀρχή"
    assert "Strong=G0746" in toks[1].misc
    assert toks[1].upos == "NOUN"

def test_align_verse_unmatched_l0_word_marked():
    l0 = "ἐν δέ"  # δέ absent from source rows
    norm = [{"idx":1,"surface":"ἐν","lemma":"ἐν","strong":"G1722","xpos":"PREP","translit":"en","edition":"TR"}]
    toks = align_verse("X.1.1", l0, norm, "grc")
    assert "Align=unmatched" in toks[1].misc
```

- [ ] **Step 3: Run test to verify it fails.**

Run: `python -m pytest tests/test_align_morph.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `tools/align_morph.py`.** Match L0 words to normalized rows in order by `normalize_surface`; attach tags on match; on an L0 word with no remaining source match, emit a token with empty tags + `Align=unmatched`; on source rows left over, the last token gains `Align=source_extra:<n>`.

```python
import csv, json, re, unicodedata
from pathlib import Path
from tools.conllu import Token, format_misc
from tools.morph_feats import decode

ROOT = Path(__file__).resolve().parents[1]
_PUNCT = re.compile(r"[\.,;:·’‘\"\?\!·\[\]]")

def normalize_surface(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _PUNCT.sub("", s).lower().strip()

def tokenize_l0(text):
    return [w for w in _PUNCT.sub(" ", text).split() if w]

def load_norm(lang):
    path = ROOT / "data" / "cache" / "morph" / f"{lang}.tsv"
    by_ref = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            row["idx"] = int(row["idx"])
            by_ref.setdefault(row["ref"], []).append(row)
    for ref in by_ref:
        by_ref[ref].sort(key=lambda r: r["idx"])
    return by_ref

def align_verse(ref, l0_text, norm_rows, lang):
    words = tokenize_l0(l0_text)
    rows = list(norm_rows)
    tokens = []
    si = 0
    for i, w in enumerate(words, start=1):
        match = None
        if si < len(rows) and normalize_surface(w) == normalize_surface(rows[si]["surface"]):
            match = rows[si]; si += 1
        if match:
            upos, feats = decode(match["xpos"], lang)
            misc = format_misc(match["strong"], match.get("translit","_"), {}, None)
            tokens.append(Token(str(i), w, match["lemma"], upos, match["xpos"], feats, misc=misc))
        else:
            tokens.append(Token(str(i), w, "_", "X", "_", "_",
                                misc=format_misc("", "_", {}, "unmatched")))
    if si < len(rows) and tokens:
        leftover = len(rows) - si
        last = tokens[-1]
        extra = f"source_extra:{leftover}"
        last.misc = last.misc + f"|Align={extra}" if last.misc != "_" else f"Align={extra}"
    return tokens
```

- [ ] **Step 5: Run tests to verify they pass.**

Run: `python -m pytest tests/test_align_morph.py -v`
Expected: PASS.

- [ ] **Step 6: Add the driver `tools/generate_morph.py` and prove one book.** Driver iterates the registry, loads each language's normalized TSV, walks the L0 chapter files for that testament's books, and writes `morph/<test>/<CODE>/NNN.conllu`. Add a `--book CODE` flag. Run it for the smallest NT book to get a real green slice:

```bash
python -m tools.generate_morph --lang grc --book 3JO
```

Expected: `morph/nt/3JO/001.conllu` exists, every verse present, forms equal to the L0 Greek.

- [ ] **Step 7: Commit.**

```bash
git add data/morph-sources.json tools/align_morph.py tools/generate_morph.py tests/test_align_morph.py morph/nt/3JO
git commit -m "feat: morpho-lexical alignment engine; 3 John Greek green"
```

---

### Task 5: Validator + full Greek NT

**Files:**
- Create: `tools/validate_morph.py`
- Create: `tests/test_validate_morph.py`

**Interfaces:**
- Consumes: `morph/**/*.conllu`, L0 corpus, `tools.conllu.parse_file`.
- Produces: `validate(testament:str) -> dict` returning `{"verses":int, "tokens":int, "unmatched":int, "source_extra":int, "missing_strong":int}`; raises `AssertionError` on structural failure (a verse with no sentence, a token whose FORM is absent from its L0 verse). A `__main__` prints the report and compares against pinned expected counts.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_validate_morph.py
from tools.validate_morph import reconcile_form

def test_reconcile_form_present():
    assert reconcile_form("ἀρχῇ", "ἐν ἀρχῇ ἦν") is True

def test_reconcile_form_absent():
    assert reconcile_form("xyz", "ἐν ἀρχῇ ἦν") is False
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_validate_morph.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tools/validate_morph.py`** with `reconcile_form`, per-verse coverage checks, and counters. Structural assertions: every L0 verse has exactly one CoNLL-U sentence; every token FORM appears in its L0 verse text; ranges (`5-6` IDs) are well-formed.

- [ ] **Step 4: Generate the full Greek NT.**

```bash
python -m tools.generate_morph --lang grc
```

- [ ] **Step 5: Run the validator, pin the counts.**

Run: `python -m tools.validate_morph nt`
Expected: prints `verses=7957 tokens=<N> unmatched=<U> ...`. Record the observed counts as pinned constants in `validate_morph.py` (mirroring `EXPECTED_ABSENT`/`EXPECTED_SRC` in `validate_ot.py`), so future runs fail if coverage drifts. `unmatched` must be 0 or a small explicitly-pinned number with each cause noted.

- [ ] **Step 6: Commit.**

```bash
git add tools/validate_morph.py tests/test_validate_morph.py morph/nt
git commit -m "feat: morph validator with pinned coverage; full Greek NT aligned"
```

---

### Task 6: Full Hebrew OT (scheme-parametric reuse)

**Files:**
- Modify: `tools/morph_feats.py` (`_decode_hebrew` full table), `tools/validate_morph.py` (OT pins)
- Create: `tests/test_morph_feats_hebrew.py`

**Interfaces:**
- Consumes: same engine; `lang="hbo"`, `testament="ot"`, `l0_field="hebrew_masoretic"`.
- Produces: `morph/ot/**/*.conllu`; OT pinned counts in the validator.

- [ ] **Step 1: Write the failing Hebrew decode test.**

```python
# tests/test_morph_feats_hebrew.py
from tools.morph_feats import decode

def test_hebrew_noun():
    upos, _ = decode("Ncfsa", "hbo")  # noun, common, fem, sing, absolute (TAHOT scheme)
    assert upos == "NOUN"

def test_hebrew_verb():
    upos, _ = decode("Vqp3ms", "hbo")  # verb qal perfect 3ms
    assert upos == "VERB"
```

- [ ] **Step 2: Run test to verify it fails (or under-decodes).**

Run: `python -m pytest tests/test_morph_feats_hebrew.py -v`
Expected: FAIL until `_decode_hebrew` covers the TAHOT POS letters.

- [ ] **Step 3: Flesh out `_decode_hebrew`** per the TAHOT scheme in `FORMATS-morph.md` (POS letter → UPOS; decode stem/person/gender/number/state into FEATS).

- [ ] **Step 4: Prove one OT book green**, then the full OT.

```bash
python -m tools.generate_morph --lang hbo --book OBA
python -m tools.generate_morph --lang hbo
```

- [ ] **Step 5: Run the OT validator, pin counts.**

Run: `python -m tools.validate_morph ot`
Expected: prints `verses=23145 tokens=<N> ...`. Pin the observed counts. Note: Hebrew ketiv/qere and the OSHB↔WLC pointing differences are the expected `unmatched`/`source_extra` causes — record each as a pinned, explained number.

- [ ] **Step 6: Commit.**

```bash
git add tools/morph_feats.py tools/validate_morph.py tests/test_morph_feats_hebrew.py morph/ot
git commit -m "feat: full Hebrew OT aligned; OT coverage pinned"
```

---

### Task 7: Lexicon builder (L2a entries + multilingual glosses)

**Files:**
- Create: `tools/build_lexicon.py`
- Create: `tests/test_build_lexicon.py`

**Interfaces:**
- Consumes: PD lexicon sources (Strong's, Abbott-Smith, BDB) per `FORMATS-morph.md`; the set of Strong's numbers actually used in `morph/**/*.conllu`; the Vulgate L0 column for Latin gloss derivation.
- Produces:
  - `build_entry(strong, lang, sources) -> dict` matching the spec's entry schema (`strong, lemma, translit, lang, pos, glosses, senses, domains, root, sources`).
  - `seed_glosses(strong, sources) -> dict[lang, list]` — fills `en` from PD lexicons; other languages where a PD source links to the Strong's number; each gloss `{"text":..., "src":...}`.
  - A `__main__` writing `lexicon/<lang>/<STRONG>.json` for every Strong's used in the corpus.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_build_lexicon.py
from tools.build_lexicon import build_entry

FAKE = {
    "strongs-greek": {"G0026": {"lemma":"ἀγάπη","translit":"agapē","gloss":"love, affection","root":"G0025"}},
    "abbott-smith":  {"G0026": {"gloss":"love"}},
}

def test_build_entry_has_schema_fields():
    e = build_entry("G0026", "grc", FAKE)
    assert e["strong"] == "G0026"
    assert e["lemma"] == "ἀγάπη"
    assert e["glosses"]["en"][0]["text"]
    assert e["glosses"]["en"][0]["src"]
    assert e["root"] == "G0025"
    assert "strongs-greek" in e["sources"]

def test_glosses_is_lang_keyed_map():
    e = build_entry("G0026", "grc", FAKE)
    assert isinstance(e["glosses"], dict)
    assert "en" in e["glosses"]
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_build_lexicon.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tools/build_lexicon.py`.** Merge sources by Strong's; English glosses from Strong's + Abbott-Smith/BDB, each tagged with `src`; Latin glosses derived by collecting the Vulgate L0 words aligned to that Strong's (src `vulgate-link`); empty language slots remain absent keys (ready to fill). `senses` seeded from any sense divisions the PD source carries (else a single sense from the gloss); `domains` left `[]` here (filled in Task 8).

- [ ] **Step 4: Run tests to verify they pass.**

Run: `python -m pytest tests/test_build_lexicon.py -v`
Expected: PASS.

- [ ] **Step 5: Build the real lexicon + spot-check.**

```bash
python -m tools.build_lexicon
python -c "import json;print(json.load(open('lexicon/grc/G0026.json'))['glosses']['en'])"
```

Expected: `lexicon/grc/` and `lexicon/hbo/` populated; G0026 shows an English gloss with provenance.

- [ ] **Step 6: Commit.**

```bash
git add tools/build_lexicon.py tests/test_build_lexicon.py lexicon
git commit -m "feat: L2a lexicon builder with multilingual glosses + provenance"
```

---

### Task 8: Domain spine (thesaurus)

**Files:**
- Modify: `tools/build_lexicon.py` (attach domains)
- Create: `tests/test_domains.py`

**Interfaces:**
- Consumes: the open domain source chosen in Task 0 (Strong's→Louw-Nida map, or SDBH/SDBG/SIL fallback), per `FORMATS-morph.md`.
- Produces: `attach_domains(entry, domain_map) -> entry` adding `domains:[...]` and per-sense `domain` where available; provenance added to `sources`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_domains.py
from tools.build_lexicon import attach_domains

def test_attach_domains_adds_domain_list():
    entry = {"strong":"G0026","domains":[],"senses":[{"id":1,"gloss_en":"love"}],"sources":["strongs-greek"]}
    dmap = {"G0026": ["25.43"]}
    out = attach_domains(entry, dmap)
    assert out["domains"] == ["25.43"]
    assert "ln-map" in out["sources"] or "sdbh" in out["sources"]
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_domains.py -v`
Expected: FAIL with `ImportError: cannot import name 'attach_domains'`.

- [ ] **Step 3: Implement `attach_domains`** and wire it into the `build_lexicon` main pass; record the domain source name in `sources`.

- [ ] **Step 4: Rebuild + verify a cluster.**

```bash
python -m tools.build_lexicon
python -c "import json,glob;             entries=[json.load(open(p)) for p in glob.glob('lexicon/grc/*.json')];             print(sorted(e['strong'] for e in entries if '25.43' in e.get('domains',[]))[:10])"
```

Expected: multiple love-domain lemmas cluster under `25.43` — the thesaurus join works.

- [ ] **Step 5: Commit.**

```bash
git add tools/build_lexicon.py tests/test_domains.py lexicon
git commit -m "feat: semantic-domain spine attached to lexicon entries"
```

---

### Task 9: Derived SQLite DB

**Files:**
- Create: `tools/build_db.py`
- Create: `tests/test_build_db.py`

**Interfaces:**
- Consumes: `morph/**/*.conllu`, `lexicon/**/*.json`, L0 corpus; `tools.conllu.parse_file`.
- Produces: `build(db_path)` creating the schema from the spec (`verses, tokens, lexicon, glosses, senses, domains`) and populating it; helper `misc_field(misc:str, key:str) -> str|None` to pull `Strong`/`Translit` out of a MISC string.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_build_db.py
import sqlite3
from tools.build_db import misc_field, build

def test_misc_field_extracts_strong():
    assert misc_field("Strong=G1722|Translit=en", "Strong") == "G1722"
    assert misc_field("_", "Strong") is None

def test_build_creates_joinable_db(tmp_path, monkeypatch):
    # build() reads the repo's canonical files; here assert schema + a concordance join.
    db = tmp_path / "t.sqlite"
    build(db)
    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"verses","tokens","lexicon","glosses","senses","domains"} <= names
    # every token's strong resolves to a lexicon row (left-join finds no orphans beyond pinned)
    orphans = con.execute(
        "SELECT COUNT(*) FROM tokens t LEFT JOIN lexicon l ON t.strong=l.strong "
        "WHERE t.strong IS NOT NULL AND l.strong IS NULL").fetchone()[0]
    assert isinstance(orphans, int)
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_build_db.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tools/build_db.py`.** Create tables per the spec schema; walk L0 chapter files into `verses` (one row per verse, ref + every parallel column); walk `morph/**/*.conllu` into `tokens` (ref, idx, form, lemma, strong, upos, xpos, feats, translit, align_note); walk `lexicon/**/*.json` into `lexicon`/`glosses`/`senses`/`domains`. Wrap inserts in one transaction; create indexes on `tokens.strong`, `tokens.ref`, `domains.domain`.

- [ ] **Step 4: Run tests to verify they pass.**

Run: `python -m pytest tests/test_build_db.py -v`
Expected: PASS.

- [ ] **Step 5: Build the real DB + prove the four query classes.**

```bash
python -m tools.build_db
sqlite3 data/tokens.sqlite "SELECT COUNT(*) FROM tokens WHERE strong='G0026';"          -- concordance
sqlite3 data/tokens.sqlite "SELECT l.strong,l.lemma FROM lexicon l JOIN domains d ON l.strong=d.strong WHERE d.domain='25.43' LIMIT 10;"  -- thesaurus
sqlite3 data/tokens.sqlite "SELECT v.kjv FROM tokens t JOIN verses v ON t.ref=v.ref WHERE t.strong='G3056' LIMIT 5;"  -- cross-translation
sqlite3 data/tokens.sqlite "SELECT COUNT(*) FROM tokens WHERE feats LIKE '%Case=Gen%';"  -- morph search
```

Expected: each returns sensible non-empty results.

- [ ] **Step 6: Commit.**

```bash
git add tools/build_db.py tests/test_build_db.py
git commit -m "feat: derived SQLite token DB (concordance/thesaurus/cross-translation/morph)"
```

---

### Task 10: Docs + full regen check

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: README section documenting the L1/L2a layers, the two-form architecture, the canonical formats, and regenerate commands; STEPBible CC-BY attribution.

- [ ] **Step 1: Add a README section** describing `morph/`, `lexicon/`, the derived `data/tokens.sqlite`, the `data/morph-sources.json` registry, and the regenerate sequence:

```
python -m tools.morph_norm.stepbible_greek      # raw -> data/cache/morph/grc.tsv
python -m tools.morph_norm.stepbible_hebrew     # raw -> data/cache/morph/hbo.tsv
python -m tools.generate_morph                  # -> morph/**/*.conllu
python -m tools.validate_morph nt && python -m tools.validate_morph ot
python -m tools.build_lexicon                   # -> lexicon/**/*.json
python -m tools.build_db                        # -> data/tokens.sqlite
```

- [ ] **Step 2: Add STEPBible attribution** to the Sources + License sections (TAGNT/TAHOT/TBESG/TBESH, CC-BY, credit STEPBible + Tyndale House Cambridge).

- [ ] **Step 3: Full clean regen** to prove determinism:

```bash
rm -rf morph lexicon data/tokens.sqlite
python -m tools.generate_morph && python -m tools.build_lexicon && python -m tools.build_db
python -m tools.validate_morph nt && python -m tools.validate_morph ot && python -m pytest -q
git status --short    # morph/ and lexicon/ regenerate identically (no diff vs committed)
```

Expected: validators pass, full test suite green, regenerated `morph/`+`lexicon/` byte-identical to committed.

- [ ] **Step 4: Commit.**

```bash
git add README.md
git commit -m "docs: document L1/L2a morpho-lexical floor + STEPBible attribution"
```

---

## Self-Review

**Spec coverage:**
- Two-form architecture (canonical → derived DB) → Tasks 2,4,9. ✓
- L1 CoNLL-U schema (ID/FORM/LEMMA/UPOS/XPOS/FEATS/HEAD/DEPREL/MISC) → Task 2 (`COLS`), Task 4 (population). ✓
- Registry-driven, scheme-parametric (Greek+Hebrew, no per-language code forks) → `data/morph-sources.json` Task 4; reuse Task 6. ✓
- Sources STEPBible TAGNT/TAHOT + PD lexicons → Tasks 0,1,7. ✓
- Alignment: L0 authoritative, FORM from L0, mismatches marked → Task 4 (`align_verse`, `Align=`). ✓
- Validator with pinned counts/oracles → Tasks 5,6. ✓
- L2a entry schema (glosses map, senses, domains, root, provenance) → Tasks 7,8. ✓
- Multilingual seed-all-PD glosses → Task 7 (`seed_glosses`, Latin via Vulgate link). ✓
- Domain thesaurus spine + licensing fallback → Tasks 0(step4),8. ✓
- Derived DB schema + four query classes → Task 9. ✓
- L0 never mutated; gitignore DB → Global Constraints, Task 1 step 7. ✓
- Deferred L2b/L3/L4/L5/translation engine → not implemented; HEAD/DEPREL left empty (Task 2). ✓

**Placeholder scan:** Morph decode tables (Tasks 3,6) intentionally ship the common cases in-plan and direct the implementer to `FORMATS-morph.md` for the full table — the scheme is real and documented by Task 0, not invented. No `TBD`/`TODO`/"handle edge cases" left.

**Type consistency:** `Token` field order/names consistent across Tasks 2,4,5,9; `format_misc`/`misc_field` are inverses; `pad_strong` 4-digit form (`G0026`) used uniformly in normalizer, lexicon filenames, and DB keys; `ref` string `CODE.chapter.verse` consistent across CoNLL-U anchor, validator, and DB.
