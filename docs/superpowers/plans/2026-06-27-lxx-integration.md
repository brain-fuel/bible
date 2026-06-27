# LXX Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Septuagint (full Greek OT) as a tagged corpus with morphology and an MT↔LXX word-alignment artifact, reusing the morpho-lexical floor's engine, so the next sub-project (L2b) has an attested Greek↔Hebrew bridge.

**Architecture:** Two-form, additive, maximal reuse. The LXX is a new corpus tree `bible/lxx/` driven by a registry row; the existing Greek morph decoder + alignment engine + `lexicon/grc/` are reused unchanged where possible. Source-format messiness is quarantined in a per-source normalizer that emits the floor's fixed-schema TSV; everything downstream is deterministic. A Task-0 spike verifies all sources/licenses first.

**Tech Stack:** Python 3 stdlib only (`json`, `sqlite3`, `csv`, `unicodedata`, `xml.etree`, `urllib`, `pathlib`), `pytest`. No new runtime deps.

## Global Constraints

- **L0 immutability:** never write under `bible/ot/`, `bible/nt/`, or `bible/apo/`. The LXX is a NEW tree `bible/lxx/`. Token `FORM` comes from `bible/lxx/` text (authoritative); source tags map onto it.
- **Licensing:** every shipped datum is PD or CC-BY. STEPBible (CC-BY), MACULA/Clear Bible (CC-BY), Strong's/Swete/BDB (PD) are allowed. Restricted sources (e.g. CATSS/CCAT if redistribution-limited) are rejected and the fallback recorded. Provenance (`src`/`sources`) on every datum.
- **Encoding:** NFC, UTF-8, LF.
- **Book codes:** uppercase 3-char from `data/books.json`. Protocanon LXX reuses the OT codes (GEN…MAL). Deuterocanon reuses the apo codes already present (1ES, 2ES, TOB, JDT, ADE, WIS, SIR, BAR, PAZ, SUS, BEL, MAN, 1MA, 2MA); LXX-only books (e.g. 3 Maccabees, 4 Maccabees, Psalm 151, Odes, Psalms of Solomon) get new codes finalized in Task 1 per the chosen edition. Chapter files zero-padded to 3 digits.
- **Ref string:** `CODE.chapter.verse` (LXX versification for `bible/lxx/`).
- **Versification:** `bible/lxx/` is self-spined on LXX numbering; an LXX↔MT map records correspondence/divergence in `refs` (same shape as the OT corpus: `refs[<edition>] = {"src": "c:v", "absent": true}`).
- **Determinism:** every generator is idempotent; the DB and all canonical artifacts rebuild byte-identical.
- **Concurrency:** another agent works `bible/apo/` in this repo. Work in an isolated worktree; touch only new paths plus additive edits to `data/books.json` / `data/morph-sources.json` / `README.md` / `tools/`. Reuse existing apo book codes rather than renaming.
- **TDD:** failing test first, minimal code to green, commit per task.

## Normalized intermediate TSV schema (reused from the floor — the quarantine boundary)

The LXX normalizer (Task 3) emits `data/cache/morph/lxx.tsv` with the SAME header/columns the floor uses, so the existing alignment engine consumes it unchanged:

```
ref	idx	surface	lemma	strong	xpos	feats	translit	edition
```

- `ref` = `CODE.chapter.verse` (LXX versification). `idx` = 1-based word index in verse.
- `surface` = LXX word form (NFC, for matching). `lemma` = dictionary headword (NFC).
- `strong` = `G` + 4-digit Strong's where the lemma resolves to a Greek Strong's via `lexicon/grc/`, else empty.
- `xpos` = raw LXX morph code verbatim. `feats` = `_` (FEATS derived at decode time).
- `translit` = if provided, else `_`. `edition` = `LXX`.

## File Structure

```
docs/FORMATS-lxx.md                NEW  Task-0 output: LXX source layouts + licenses
data/cache/morph/raw/lxx/          NEW  gitignored raw LXX downloads
data/cache/morph/lxx.tsv           NEW  gitignored normalized LXX tokens (Task 3)
data/books.json                    MOD  add LXX book set/order + lxx_name field
data/versification/lxx-versification.json  NEW  LXX↔MT verse map (Task 1)
data/morph-sources.json            MOD  +1 row: lxx
bible/lxx/<CODE>/NNN.json          NEW  LXX Greek text (Task 2)
morph/lxx/<CODE>/NNN.conllu        NEW  LXX morphology (Task 5)
align/mt-lxx/<CODE>/NNN.json       NEW  MT↔LXX word alignment, protocanon (Task 7)
lexicon/grc/*.json                 MOD  extend with LXX-only lemmas (Task 6)
data/tokens.sqlite                 (derived, gitignored) +lxx tokens +mt_lxx table (Task 8)
tools/sources/lxx_source.py        NEW  backend for the chosen tagged-LXX source
tools/morph_norm/lxx.py            NEW  normalize tagged-LXX -> lxx.tsv
tools/generate_lxx.py              NEW  emit bible/lxx/ from the source
tools/lxx_versification.py         NEW  build/apply LXX<->MT verse map
tools/align_mt_lxx.py              NEW  build align/mt-lxx/ artifact
tools/validate_lxx.py              NEW  LXX corpus structural + versification oracles
tools/morph_feats.py               MOD  LXX morph-code scheme (if != Robinson)
tools/align_morph.py               MOD  load_norm keyed by entry/norm-path (de-collide grc)
tools/generate_morph.py            MOD  pass norm path per entry
tools/validate_morph.py            MOD  LXX morph coverage pins
tools/build_lexicon.py             MOD  ingest LXX-only lemmas
tools/build_db.py                  MOD  load lxx tokens + mt_lxx table
tests/                             NEW  per-tool tests
```

---

### Task 0: Data acquisition + license verification (spike)

**Files:**
- Create: `docs/FORMATS-lxx.md`
- Create: `data/cache/morph/raw/lxx/` (gitignored)

**Interfaces:**
- Produces: `docs/FORMATS-lxx.md` documenting, for each LXX source, its exact layout, reference scheme, morph-code scheme, license, URL — the contract Tasks 1–8 build against.

This is a research spike; no code module ships. It ends when `FORMATS-lxx.md` answers every question the downstream tasks need.

- [ ] **Step 1: LXX text + morphology source.** Evaluate, in order: **MACULA Septuagint** (Clear-Bible, CC-BY) — check `github.com/Clear-Bible` for an LXX dataset with text+lemma+morph; **STEPBible** tagged LXX (CC-BY) if present; **CATSS/CCAT** Rahlfs morphology (verify redistribution license — REJECT if restricted); **Swete** (PD, text only). Download the best OPEN one into `data/cache/morph/raw/lxx/`. Record real sample rows.

- [ ] **Step 2: MT↔LXX alignment source.** Look for an open word-level Hebrew↔Greek alignment: a MACULA MT↔LXX alignment, or other CC-BY/PD set. Verify CATSS/Tov license (REJECT if restricted). If none is open, record the fallback decision: verse-level lemma co-occurrence (lower confidence). Document the exact format + how it keys (by ref / Strong's / lemma).

- [ ] **Step 3: LXX↔MT versification.** Determine whether the STEPBible **TVTMS** already cached (`data/cache/` / `data/versification/`) carries an LXX tradition. If yes, document how to extract LXX↔MT. If no, document the known divergences to hand-map (Psalms numbering, Jeremiah chapter reorder, Greek-Esther/Daniel additions) for a CC0 supplement.

- [ ] **Step 4: LXX book list + codes.** From the chosen edition, list every LXX book, its order, chapter counts, and the CODE to use (protocanon → OT codes GEN…MAL; deuterocanon → existing apo codes; LXX-only → new codes). Record any book whose LXX name/segmentation differs from the apo agent's.

- [ ] **Step 5: Strong's linkage feasibility.** Confirm the tagged-LXX provides a Greek **lemma** per word (needed to join `lexicon/grc/` by lemma→Strong's). Record the lemma field and its normalization (accents/NFC) vs the existing `lexicon/grc/` lemmas.

- [ ] **Step 6: Document + commit.** Write all of the above into `docs/FORMATS-lxx.md` (exact headers/elements, ref scheme, morph scheme, license, URL per source). Commit only the doc.

```bash
git add docs/FORMATS-lxx.md
git commit -m "docs: LXX source formats + license verification (Task 0 spike)"
```

---

### Task 1: Book registry + LXX↔MT versification map

**Files:**
- Modify: `data/books.json`
- Create: `data/versification/lxx-versification.json`, `tools/lxx_versification.py`
- Create: `tests/test_lxx_versification.py`

**Interfaces:**
- Consumes: `docs/FORMATS-lxx.md` (book list + versification findings).
- Produces:
  - `data/books.json` rows for every LXX book with `testament:"lxx"`, `code`, `lxx_name`, `chapters`, and a `lxx_order` index.
  - `lxx_books() -> list[dict]` in `tools/lxx_versification.py` returning the LXX book rows.
  - `mt_ref(lxx_code, lxx_chapter, lxx_verse) -> str|None` returning the MT `"chapter:verse"` for a protocanon LXX position, or `None` if no MT counterpart (deuterocanon or genuinely absent).
  - `load_lxx_vmap() -> dict` loading `data/versification/lxx-versification.json`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_lxx_versification.py
from tools.lxx_versification import mt_ref, lxx_books

def test_psalms_offset_known_case():
    # LXX Psalm numbering diverges from MT; a documented mapped case from FORMATS-lxx.md.
    # (Use the exact pair recorded in docs/FORMATS-lxx.md Step 3.)
    assert mt_ref("PSA", 9, 22) == "10:1"

def test_deuterocanon_has_no_mt():
    assert mt_ref("1MA", 1, 1) is None

def test_lxx_books_nonempty_and_have_codes():
    books = lxx_books()
    assert len(books) >= 39
    assert all(b.get("code") and b.get("testament") == "lxx" for b in books)
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_lxx_versification.py -v`
Expected: FAIL with `ModuleNotFoundError: tools.lxx_versification`.

- [ ] **Step 3: Add LXX book rows to `data/books.json`** per `FORMATS-lxx.md` Step 4 (testament `lxx`, codes, `lxx_name`, `chapters`, `lxx_order`). Protocanon reuses GEN…MAL codes; deuterocanon reuses apo codes; LXX-only books get the new codes recorded in Task 0.

- [ ] **Step 4: Build the versification map.** Implement `tools/lxx_versification.py` (`lxx_books`, `load_lxx_vmap`, `mt_ref`) and produce `data/versification/lxx-versification.json` from TVTMS (if it carries LXX, per Task 0 Step 3) plus a CC0 supplement for the documented divergences. The map keys LXX `CODE.chapter.verse` → MT `chapter:verse` (or marks no-counterpart).

- [ ] **Step 5: Run tests to verify they pass.**

Run: `python -m pytest tests/test_lxx_versification.py -v`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add data/books.json data/versification/lxx-versification.json tools/lxx_versification.py tests/test_lxx_versification.py
git commit -m "feat: LXX book registry + LXX<->MT versification map"
```

---

### Task 2: LXX corpus generator

**Files:**
- Create: `tools/sources/lxx_source.py`, `tools/generate_lxx.py`, `tools/validate_lxx.py`
- Create: `tests/test_generate_lxx.py`
- Modify: `.gitignore` (add `data/cache/morph/raw/lxx/` if not covered by `data/cache/`)

**Interfaces:**
- Consumes: the cached LXX source (per `FORMATS-lxx.md`); `tools.lxx_versification.mt_ref`/`lxx_books`.
- Produces:
  - `LxxSource` in `tools/sources/lxx_source.py` exposing `chapter(book_meta, chapter) -> {verse:int -> greek_text:str}` and `chapters(book_meta) -> [int]`, mirroring the existing `tools/sources/registry.py` source interface.
  - `tools/generate_lxx.py` writing `bible/lxx/<CODE>/NNN.json`: each verse `{"verse":int, "greek_lxx":str, "refs":{...}}` where `refs.mt = {"src": "<c:v>"}` for protocanon positions whose MT ref differs, or `{"absent": true}` where no MT counterpart. `--book CODE` flag.
  - `validate(testament="lxx") -> dict` in `tools/validate_lxx.py`: asserts contiguous verses, non-empty `greek_lxx`, book/chapter coverage vs `data/books.json`; pins total LXX verse count.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_generate_lxx.py
from tools.generate_lxx import build_chapter

def test_build_chapter_shapes_verses():
    # Fake source chapter: {verse: greek_text}
    src = {1: "ἐν ἀρχῇ ἐποίησεν ὁ θεὸς", 2: "ἡ δὲ γῆ ἦν ἀόρατος"}
    ch = build_chapter("GEN", 1, src)
    assert ch["book_id"] == "GEN"
    assert ch["chapter"] == 1
    assert ch["verses"][0] == {"verse": 1, "greek_lxx": "ἐν ἀρχῇ ἐποίησεν ὁ θεὸς"}
    assert ch["verses"][1]["verse"] == 2
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_generate_lxx.py -v`
Expected: FAIL with `ModuleNotFoundError: tools.generate_lxx`.

- [ ] **Step 3: Implement the source backend + `build_chapter` + driver.** `build_chapter(code, chapter, src_verses)` returns the chapter dict (verses sorted, `greek_lxx` NFC). The driver walks `lxx_books()`, pulls each chapter from `LxxSource`, attaches `refs.mt` via `mt_ref`, writes `bible/lxx/<CODE>/NNN.json`. Implement `validate_lxx.py` structural checks.

- [ ] **Step 4: Run the unit test + generate one book.**

Run: `python -m pytest tests/test_generate_lxx.py -v` → PASS.
Run: `python -m tools.generate_lxx --book RUT`
Expected: `bible/lxx/RUT/001.json`… exist, every verse has non-empty `greek_lxx`.

- [ ] **Step 5: Commit.**

```bash
git add tools/sources/lxx_source.py tools/generate_lxx.py tools/validate_lxx.py tests/test_generate_lxx.py bible/lxx/RUT
git commit -m "feat: LXX corpus generator; Ruth green"
```

---

### Task 3: LXX normalizer → fixed-schema TSV

**Files:**
- Create: `tools/morph_norm/lxx.py`
- Create: `tests/test_morph_norm_lxx.py`

**Interfaces:**
- Consumes: the cached tagged-LXX source (per `FORMATS-lxx.md`); `lexicon/grc/*.json` for the lemma→Strong's index.
- Produces:
  - `lemma_strong_index() -> dict[str,str]` mapping NFC Greek lemma → `G####` from `lexicon/grc/`.
  - `normalize_lxx(raw_path) -> list[dict]` with keys `ref, idx, surface, lemma, strong, xpos, feats, translit, edition` (edition `"LXX"`; `strong` filled via the lemma index, else `""`; `feats` `"_"`). `ref` mapped to `CODE.chapter.verse` (LXX versification), CODE via the book-abbrev→CODE map in `FORMATS-lxx.md`.
  - A CLI writing `data/cache/morph/lxx.tsv` (same header as the floor's normalizers, via a shared `_write_tsv`).

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_morph_norm_lxx.py
from tools.morph_norm.lxx import normalize_lxx

def test_normalize_lxx_row(tmp_path):
    # One source row in the format documented in FORMATS-lxx.md (adjust the fixture
    # to the real layout; here a simple tab form with a header).
    raw = tmp_path / "lxx.txt"
    raw.write_text(
        "ref\tword\tlemma\tmorph\n"
        "Gen.1.1#01\tἐν\tἐν\tP\n",
        encoding="utf-8",
    )
    rows = normalize_lxx(raw)
    assert rows[0]["ref"] == "GEN.1.1"
    assert rows[0]["idx"] == 1
    assert rows[0]["surface"] == "ἐν"
    assert rows[0]["lemma"] == "ἐν"
    assert rows[0]["xpos"] == "P"
    assert rows[0]["edition"] == "LXX"
    assert rows[0]["feats"] == "_"
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_morph_norm_lxx.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tools/morph_norm/lxx.py`** per the real format (handle whatever block/flat structure `FORMATS-lxx.md` documents, mirroring the patterns in `tools/morph_norm/stepbible_greek.py`). Build `lemma_strong_index()` by reading `lexicon/grc/*.json` (`lemma` → `strong`); fill `strong` when the LXX lemma matches, else `""`. NFC everywhere. Add the `_write_tsv` CLI.

- [ ] **Step 4: Run tests + generate the real TSV.**

Run: `python -m pytest tests/test_morph_norm_lxx.py -v` → PASS.
Run: `python -m tools.morph_norm.lxx` → writes `data/cache/morph/lxx.tsv`. Spot-check Genesis 1:1 rows and report the Strong's-link rate (how many LXX tokens resolved a `G####`).

- [ ] **Step 5: Commit.**

```bash
git add tools/morph_norm/lxx.py tests/test_morph_norm_lxx.py
git commit -m "feat: LXX normalizer to fixed-schema TSV with lemma->Strong's linkage"
```

---

### Task 4: Generalize the morph engine for LXX (de-collide grc) + decoder scheme

**Files:**
- Modify: `tools/align_morph.py`, `tools/generate_morph.py`, `data/morph-sources.json`
- Modify: `tools/morph_feats.py` (only if LXX codes differ from Robinson)
- Create: `tests/test_align_morph_lxx.py`

**Interfaces:**
- Consumes: `data/cache/morph/lxx.tsv`; `bible/lxx/` text; existing `align_verse`, `decode`.
- Produces:
  - `load_norm(norm_path: str) -> dict` — CHANGED to take the explicit norm-file path from the registry entry (so two `grc` entries — `nt` and `lxx` — no longer collide on a lang-derived path). Update `generate_morph.py` to pass `entry["norm"]`.
  - Registry row appended to `data/morph-sources.json`: `{"lang":"grc","testament":"lxx","l0_field":"greek_lxx","norm":"data/cache/morph/lxx.tsv","edition_filter":"LXX","morph_scheme":"<robinson|lxx>","lexicon_sources":["strongs-greek"],"domain_source":"ln-map"}`.
  - If LXX morph codes differ from Robinson: `decode(code, lang, scheme="robinson")` gains an `lxx` scheme branch (per `FORMATS-lxx.md`); `generate_morph` passes `entry.get("morph_scheme","robinson")`. If LXX uses Robinson-style codes, no decoder change — document that.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_align_morph_lxx.py
from tools.align_morph import load_norm

def test_load_norm_takes_explicit_path(tmp_path):
    p = tmp_path / "lxx.tsv"
    p.write_text(
        "ref\tidx\tsurface\tlemma\tstrong\txpos\tfeats\ttranslit\tedition\n"
        "GEN.1.1\t1\tἐν\tἐν\tG1722\tP\t_\ten\tLXX\n",
        encoding="utf-8",
    )
    by_ref = load_norm(str(p))
    assert by_ref["GEN.1.1"][0]["strong"] == "G1722"
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_align_morph_lxx.py -v`
Expected: FAIL (current `load_norm` takes a lang, not a path).

- [ ] **Step 3: Refactor `load_norm` to take the norm path; update `generate_morph` callers.** Confirm the existing NT/OT registry rows still resolve (their `norm` paths are already in the registry — pass `entry["norm"]`). Add the `lxx` registry row. Add the decoder `lxx` scheme branch only if `FORMATS-lxx.md` shows non-Robinson codes.

- [ ] **Step 4: Run tests + regression + one LXX book green.**

Run: `python -m pytest tests/test_align_morph_lxx.py tests/test_align_morph.py -v` → PASS.
Run: `python -m tools.generate_morph --lang grc --book 3JO` (NT regression — still works) then `python -m tools.morph_norm.lxx && python -m tools.generate_morph --testament lxx --book RUT`.
Expected: `morph/lxx/RUT/001.conllu` exists; FORM from `bible/lxx/RUT`; tokens carry lemma/xpos/feats and `Strong=` where linked. Report Ruth unmatched %.

(If `generate_morph` lacks a `--testament` filter, add one alongside `--lang`/`--book` in this step — small additive flag.)

- [ ] **Step 5: Commit.**

```bash
git add tools/align_morph.py tools/generate_morph.py tools/morph_feats.py data/morph-sources.json tests/test_align_morph_lxx.py morph/lxx/RUT
git commit -m "feat: generalize morph engine for LXX (path-keyed load_norm); Ruth LXX morph green"
```

---

### Task 5: Full LXX morph + validator pins

**Files:**
- Modify: `tools/validate_morph.py`
- Create: `tests/test_validate_morph_lxx.py`

**Interfaces:**
- Consumes: `morph/lxx/**`, `bible/lxx/**`.
- Produces: `validate("lxx")` returning `{"verses","tokens","unmatched","source_extra","missing_strong"}`; structural asserts (every `bible/lxx/` verse has one CoNLL-U sentence; every FORM reconciles to its LXX verse text); pinned LXX constants; exits nonzero on drift.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_validate_morph_lxx.py
from tools.validate_morph import reconcile_form

def test_reconcile_form_lxx_present():
    assert reconcile_form("ἀρχῇ", "ἐν ἀρχῇ ἐποίησεν") is True
```

- [ ] **Step 2: Run test to verify it fails (or add the lxx branch).**

Run: `python -m pytest tests/test_validate_morph_lxx.py -v`
Expected: PASS for `reconcile_form` reuse; the new work is the `"lxx"` branch + pins (added next).

- [ ] **Step 3: Add the `"lxx"` branch to `validate()`** (mirror the `ot` branch: load `lxx_books()`, walk `bible/lxx/` + `morph/lxx/`), generate the full LXX morph (`python -m tools.generate_morph --testament lxx`), run `python -m tools.validate_morph lxx`, observe counts, PIN them (`EXPECTED_LXX_*`). The LXX Strong's-link rate will be lower than the NT (LXX-only vocabulary) — pin the real `missing_strong` with a comment naming the cause. Re-run to confirm exit zero.

- [ ] **Step 4: Run validator + full suite.**

Run: `python -m tools.validate_morph lxx` → prints + exits 0 against pins.
Run: `python -m pytest -q` → green.

- [ ] **Step 5: Commit.**

```bash
git add tools/validate_morph.py tests/test_validate_morph_lxx.py morph/lxx
git commit -m "feat: full LXX morphology aligned + pinned coverage"
```

---

### Task 6: Extend lexicon with LXX-only lemmas

**Files:**
- Modify: `tools/build_lexicon.py`
- Create: `tests/test_build_lexicon_lxx.py`

**Interfaces:**
- Consumes: `data/cache/morph/lxx.tsv` (the lemma set, incl. lemmas with empty `strong`); existing Greek gloss sources.
- Produces: `lxx_only_lemmas() -> list[str]` (LXX lemmas not resolvable to an existing `lexicon/grc/` Strong's). `build_lexicon` extended to emit lemma-keyed entries for them: `lexicon/grc/lemma-<slug>.json` with `{"strong": null, "lemma": ..., "lang":"grc", "glosses":{...}, "sources":[...], "domains":[], "senses":[...]}` — NO fabricated Strong's. Gloss from a PD/CC-BY Greek source if the lemma resolves there, else empty glosses (slot ready).

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_build_lexicon_lxx.py
from tools.build_lexicon import build_lemma_entry

def test_lemma_entry_has_null_strong_and_lemma_key():
    e = build_lemma_entry("διαθήκη", {"glosses": {"en": [{"text": "covenant", "src": "x"}]}})
    assert e["strong"] is None
    assert e["lemma"] == "διαθήκη"
    assert e["lang"] == "grc"
    assert e["glosses"]["en"][0]["text"] == "covenant"
    assert e["domains"] == []
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_build_lexicon_lxx.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_lemma_entry'`.

- [ ] **Step 3: Implement `build_lemma_entry` + `lxx_only_lemmas`** and wire into the `build_lexicon` main pass (additive: existing Strong's-keyed entries unchanged; new lemma-keyed entries appended). Use a filesystem-safe slug for the filename (e.g. transliteration or a hash of the NFC lemma) — document the slug rule.

- [ ] **Step 4: Run tests + rebuild + report.**

Run: `python -m pytest tests/test_build_lexicon_lxx.py -v` → PASS.
Run: `python -m tools.build_lexicon` → report how many LXX-only lemma entries were added and the Strong's-link rate of LXX tokens.

- [ ] **Step 5: Commit.**

```bash
git add tools/build_lexicon.py tests/test_build_lexicon_lxx.py lexicon/grc
git commit -m "feat: extend lexicon with LXX-only lemma-keyed entries"
```

---

### Task 7: MT↔LXX alignment artifact

**Files:**
- Create: `tools/align_mt_lxx.py`, `tests/test_align_mt_lxx.py`

**Interfaces:**
- Consumes: the Task-0 alignment source (word-level if open, else verse-level lemma co-occurrence); `tools.lxx_versification.mt_ref`; `morph/ot/**` (MT tokens) and `morph/lxx/**` (LXX tokens).
- Produces:
  - `align_verse_pair(mt_ref:str, mt_tokens:list, lxx_tokens:list, source) -> list[dict]` producing edges `{"mt_ref","lxx_ref","mt_strong","lxx_strong","lxx_lemma","confidence","src"}`.
  - A driver writing `align/mt-lxx/<CODE>/NNN.json` for protocanon books (keyed by LXX ref, listing the MT correspondences per LXX word). `confidence` ∈ {high (word-level source), low (verse-level fallback)}; `src` records provenance.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_align_mt_lxx.py
from tools.align_mt_lxx import align_verse_pair

def test_word_level_edge_carries_provenance():
    mt = [{"strong": "H7225", "lemma": "רֵאשִׁית"}]
    lxx = [{"strong": "G0746", "lemma": "ἀρχή"}]
    # word-level source says MT word 0 <-> LXX word 0
    src = {"pairs": [(0, 0)], "kind": "word"}
    edges = align_verse_pair("GEN.1.1", "GEN.1.1", mt, lxx, src)
    assert edges[0]["mt_strong"] == "H7225"
    assert edges[0]["lxx_strong"] == "G0746"
    assert edges[0]["confidence"] == "high"
    assert edges[0]["src"]
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_align_mt_lxx.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `align_mt_lxx.py`.** For a word-level source, emit one edge per aligned pair (`confidence="high"`). For the verse-level fallback, emit the cross-product of content lemmas in the corresponding MT/LXX verse (`confidence="low"`), flagged. Use `mt_ref` to pair LXX verses to MT verses; skip deuterocanon (no MT). Driver writes `align/mt-lxx/<CODE>/NNN.json`.

- [ ] **Step 4: Run tests + build + report.**

Run: `python -m pytest tests/test_align_mt_lxx.py -v` → PASS.
Run: `python -m tools.align_mt_lxx` → report protocanon alignment coverage (edges, % of LXX protocanon tokens with an MT edge, high vs low confidence split). Spot-check GEN.1.1 (רֵאשִׁית↔ἀρχή).

- [ ] **Step 5: Commit.**

```bash
git add tools/align_mt_lxx.py tests/test_align_mt_lxx.py align/mt-lxx
git commit -m "feat: MT<->LXX word alignment artifact (protocanon, provenance+confidence)"
```

---

### Task 8: DB extension (LXX tokens + mt_lxx table)

**Files:**
- Modify: `tools/build_db.py`
- Create: `tests/test_build_db_lxx.py`

**Interfaces:**
- Consumes: `bible/lxx/**`, `morph/lxx/**`, `align/mt-lxx/**`, extended `lexicon/grc/`.
- Produces: `verses` gains LXX rows (`testament="lxx"`, `greek` column = `greek_lxx`); `tokens` gains LXX rows (`testament="lxx"`); new table `mt_lxx(mt_ref, lxx_ref, mt_strong, lxx_strong, lxx_lemma, confidence, src)` with indexes on `mt_strong`, `lxx_strong`. `lexicon`/`glosses` include the LXX-only lemma entries (strong nullable).

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_build_db_lxx.py
import sqlite3
from tools.build_db import build

def test_mt_lxx_table_and_lxx_tokens(tmp_path):
    db = tmp_path / "t.sqlite"
    build(db)
    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "mt_lxx" in names
    lxx_tokens = con.execute("SELECT COUNT(*) FROM tokens WHERE testament='lxx'").fetchone()[0]
    assert lxx_tokens > 0
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_build_db_lxx.py -v`
Expected: FAIL (no `mt_lxx` table / no lxx tokens yet).

- [ ] **Step 3: Extend `build_db.py`** to load `bible/lxx/` into `verses`, `morph/lxx/` into `tokens` (testament `lxx`), and `align/mt-lxx/` into a new `mt_lxx` table; create its indexes; keep the build one transaction + idempotent. Handle nullable `strong` in `lexicon` for LXX-only lemma rows.

- [ ] **Step 4: Run tests + build + prove the cross-language query.**

Run: `python -m pytest tests/test_build_db_lxx.py -v` → PASS.
Run: `python -m tools.build_db` then prove the bridge:
```
sqlite3 data/tokens.sqlite "SELECT DISTINCT lxx_strong FROM mt_lxx WHERE mt_strong='H7225';"   -- Hebrew rēʾšît -> Greek renderings
sqlite3 data/tokens.sqlite "SELECT COUNT(*) FROM tokens WHERE testament='lxx';"
```
Report row counts (verses/tokens incl lxx; mt_lxx edges).

- [ ] **Step 5: Commit.**

```bash
git add tools/build_db.py tests/test_build_db_lxx.py
git commit -m "feat: DB loads LXX tokens + mt_lxx alignment table (cross-language bridge)"
```

---

### Task 9: Docs + full regen determinism check

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: README section documenting the LXX corpus, morph, MT↔LXX alignment, and the regenerate sequence; attributions for the chosen LXX source + alignment source + versification.

- [ ] **Step 1: Add a README section** describing `bible/lxx/`, `morph/lxx/`, `align/mt-lxx/`, the LXX↔MT versification map, and the regenerate sequence:

```
python -m tools.generate_lxx              # -> bible/lxx/
python -m tools.morph_norm.lxx            # -> data/cache/morph/lxx.tsv
python -m tools.generate_morph --testament lxx   # -> morph/lxx/
python -m tools.validate_morph lxx
python -m tools.build_lexicon             # + LXX-only lemmas
python -m tools.align_mt_lxx              # -> align/mt-lxx/
python -m tools.build_db                  # + lxx tokens + mt_lxx table
```
(verify these module paths/flags match what was built; correct any that differ.)

- [ ] **Step 2: Add attributions** to the Sources + License sections for the chosen LXX text/morph source, the MT↔LXX alignment source, and the versification source (PD/CC-BY, with the exact credit each license requires — STEPBible, Clear Bible/MACULA, etc.).

- [ ] **Step 3: Full clean regen determinism check.**

```bash
git status --short    # clean
rm -rf bible/lxx morph/lxx align/mt-lxx data/tokens.sqlite
python -m tools.generate_lxx && python -m tools.morph_norm.lxx && python -m tools.generate_morph --testament lxx
python -m tools.build_lexicon && python -m tools.align_mt_lxx && python -m tools.build_db
python -m tools.validate_lxx && python -m tools.validate_morph lxx && python -m pytest -q
git status --short    # bible/lxx, morph/lxx, align/mt-lxx, lexicon/grc regenerate byte-identical (no diff)
```
Expected: validators pass, suite green, regenerated artifacts byte-identical to committed. If any diff appears, that is a determinism bug — investigate, don't re-commit blindly.

- [ ] **Step 4: Commit.**

```bash
git add README.md
git commit -m "docs: document LXX integration + source attributions"
```

---

## Self-Review

**Spec coverage:**
- Full LXX (protocanon + deuterocanon) corpus → Tasks 1,2. ✓
- Morphology via reused Greek decoder + alignment engine → Tasks 4,5. ✓
- Strong's linkage (lemma → lexicon/grc) + LXX-only lemma entries → Tasks 3,6. ✓
- MT↔LXX alignment artifact (protocanon, provenance+confidence) → Task 7. ✓
- LXX↔MT versification (TVTMS reuse + supplement) → Task 1. ✓
- DB extension (lxx tokens + mt_lxx table) → Task 8. ✓
- Two-form/additive/registry-driven; L0 untouched; bible/lxx own tree → Global Constraints, Tasks 2,4. ✓
- Apocrypha coexistence (reuse apo codes, own tree) → Global Constraints, Task 1. ✓
- Task-0 data/license gate; PD/CC-BY only; provenance → Task 0. ✓
- Boundary: no relation edges (that's L2b) → not implemented; alignment artifact is the handoff. ✓

**Placeholder scan:** Task fixtures intentionally say "adjust to the real layout per FORMATS-lxx.md" for the source-parsing tests because the exact source format is resolved by the Task-0 spike (same proven pattern as the floor plan) — the normalized-TSV quarantine boundary keeps all downstream tasks deterministic against a known schema. No `TBD`/`TODO`/"handle edge cases" left.

**Type consistency:** `mt_ref`/`load_lxx_vmap` (Task 1) used in Tasks 2,7; `load_norm(norm_path)` signature change (Task 4) consumed by `generate_morph`; normalized-TSV columns identical to the floor's schema; `align/mt-lxx` edge keys (`mt_strong`/`lxx_strong`/`confidence`/`src`) consistent between Task 7 producer and Task 8 `mt_lxx` table; `greek_lxx` field name consistent across Tasks 2,4,8; Strong's `G####` 4-digit padding consistent with the floor.
