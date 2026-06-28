# LXX Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Septuagint (full Greek OT) as a lemma- and Strong's-tagged corpus with LXX↔MT versification and a verse-level MT↔LXX translational bridge, reusing the morpho-lexical floor's engine, so the next sub-project (L2b) has an attested Greek↔Hebrew bridge.

**Architecture:** Two-form, additive, maximal reuse. The LXX is a new corpus tree `bible/lxx/` driven by a registry row; the existing alignment engine + `lexicon/grc/` are reused. **Open-subset build (decided after the Task-0 spike):** full morphology (UPOS/XPOS/FEATS) has no shippable open source today — STEPBible TAGOT (CC-BY) is announced but unreleased, and every ready-made morph LXX is CC-BY-**NC**. So this plan ships LXX **text + lemma + Strong's** now (Swete PD text + openscriptures LxxLemmas CC-BY), leaves the morph columns empty as ready slots, and backfills morphology additively when TAGOT releases. No open word-level MT↔LXX alignment exists either, so the bridge is **verse-level co-occurrence** (flagged confidence), not word-level. Source-format messiness is quarantined in a per-source normalizer that emits the floor's fixed-schema TSV; everything downstream is deterministic.

**Tech Stack:** Python 3 stdlib only (`json`, `sqlite3`, `csv`, `unicodedata`, `xml.etree`, `urllib`, `pathlib`), `pytest`. No new runtime deps.

## Global Constraints

- **L0 immutability:** never write under `bible/ot/`, `bible/nt/`, or `bible/apo/`. The LXX is a NEW tree `bible/lxx/`. Token `FORM` comes from `bible/lxx/` text (authoritative); source tags map onto it.
- **Licensing (all shipped data PD or CC-BY; verified in Task 0, see `docs/FORMATS-lxx.md`):** LXX text = **Swete 1909, Public Domain** — extract the PD text (word sequence + versification) from the cached source and emit our OWN `bible/lxx/` format; do NOT redistribute the GPL-3.0 CSV file. Lemmas = **openscriptures GreekResources `LxxLemmas`, CC-BY 4.0**. Versification = **STEPBible TVTMS, CC-BY 4.0** + a **CC0** hand-authored supplement. Strong's/lexicon = existing repo `lexicon/grc/` (PD spine). REJECTED (do not use): CATSS/CCAT, eliranwong RLXX, CenterBLC morph, CATSS/Tov alignment — all CC-BY-NC or restricted. Provenance (`src`/`sources`) on every datum.
- **Repo license policy (see `docs/LICENSING.md`):** software (all code in `tools/`, tests) = **AGPL-3.0-or-later**; content = **CC0-1.0** by default (our originals, the CC0 supplement, the PD Swete corpus text, the Strong's spine); content **derived from a CC-BY source stays CC-BY-4.0 with attribution** (TVTMS versification, STEPBible morpho-lexical tags, MACULA domains, openscriptures LxxLemmas). For the LXX work this means: `bible/lxx/` (Swete PD text) = CC0; the lemma + Strong's tags carried in `morph/lxx/` and any LxxLemmas-derived data = CC-BY (attribute openscriptures); the TVTMS-derived versification map = CC-BY, its `-supplement.json` = CC0. Most-restrictive-applicable license governs a mixed datum.
- **Morphology deferred:** no open morph source today. CoNLL-U `UPOS`/`XPOS`/`FEATS` ship EMPTY (`_`) for LXX; `LEMMA` + `MISC Strong=` are populated. This is intentional and pinned, NOT a bug. Backfill when STEPBible TAGOT (CC-BY) releases — same decoder/normalizer as TAGNT will then fill the columns additively. `HEAD`/`DEPREL` stay empty (L3, as in the floor).
- **Greek normalization — DO NOT NFC the join key.** Task 0 verified `lexicon/grc/` lemmas are precomposed polytonic with **oxia** (e.g. U+1F79), NOT NFC (NFC would fold oxia→tonos U+03CC and BREAK the lemma→Strong's join). LxxLemmas lemmas are byte-identical to `lexicon/grc/`. So: store and match LXX `lemma` as the **raw source string**; join `lemma→strong` by exact raw-string equality. Do not call `unicodedata.normalize("NFC", …)` on the lemma or the lexicon key.
- **Book codes:** uppercase 3-char from `data/books.json`. Protocanon LXX reuses the OT codes (GEN…MAL). Deuterocanon reuses the apo codes already present (1ES, TOB, JDT, ADE, WIS, SIR, BAR, PAZ, SUS, BEL, MAN, 1MA, 2MA). LXX-only NEW codes: `3MA` (3 Maccabees), `4MA` (4 Maccabees), `ODE` (Odes), `PSS` (Psalms of Solomon). Decisions baked: Epistle of Jeremiah = `BAR` chapter 6 (NOT a separate code); Psalm 151 = `PSA` chapter 151. **`2ES` in books.json is 4 Ezra (Latin apocalypse), NOT a Greek LXX book — never reuse it for LXX; LXX "Esdras B" maps to `EZR`+`NEH`.** Text-form doublets (Joshua/Judges A/B, Daniel/Susanna/Bel OG vs Theodotion, Tobit BA/S) are ONE book each with a `text_form` tag, NOT new codes. Chapter files zero-padded to 3 digits.
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
- `surface` = LxxLemmas word form (used only for accent-stripped matching to the Swete `FORM`; may be unaccented). `lemma` = dictionary headword, **raw source string, NOT NFC** (see Global Constraints).
- `strong` = `G` + 4-digit Strong's where the lemma resolves via the raw-string `lexicon/grc/` index, else empty.
- `xpos` = `_` (no open morph source — deferred to TAGOT). `feats` = `_` (deferred).
- `translit` = `_` (none in source). `edition` = `LXX`.

## File Structure

```
docs/FORMATS-lxx.md                DONE (Task 0)  LXX source layouts + licenses
data/cache/morph/raw/lxx/          gitignored raw LXX downloads (Swete text, LxxLemmas)
data/cache/morph/lxx.tsv           NEW  gitignored normalized LXX tokens (Task 3)
data/books.json                    MOD  add LXX book set/order + lxx_name + text_form
data/versification/lxx-versification.json  NEW  LXX↔MT verse map (Task 1)
data/morph-sources.json            MOD  +1 row: lxx
bible/lxx/<CODE>/NNN.json          NEW  LXX Greek text, Swete (Task 2)
morph/lxx/<CODE>/NNN.conllu        NEW  LXX lemma+Strong's tags, morph cols empty (Task 5)
align/mt-lxx/<CODE>/NNN.json       NEW  verse-level MT↔LXX bridge, protocanon (Task 7)
lexicon/grc/*.json                 MOD  extend with LXX-only lemmas (Task 6)
data/tokens.sqlite                 (derived, gitignored) +lxx tokens +mt_lxx table (Task 8)
tools/sources/lxx_source.py        NEW  Swete PD text backend
tools/morph_norm/lxx.py            NEW  normalize LxxLemmas -> lxx.tsv (+ raw-string Strong's join)
tools/generate_lxx.py              NEW  emit bible/lxx/ from the Swete backend
tools/lxx_versification.py         NEW  build/apply LXX<->MT verse map
tools/tvtms.py                     MOD  emit the already-parsed Greek/LXX column (Task 1)
tools/align_mt_lxx.py              NEW  build align/mt-lxx/ verse-level bridge
tools/validate_lxx.py              NEW  LXX corpus structural + versification oracles
tools/align_morph.py               MOD  load_norm keyed by norm-path (de-collide grc nt vs lxx)
tools/generate_morph.py            MOD  pass norm path per entry; --testament filter
tools/validate_morph.py            MOD  LXX lemma/Strong's coverage pins (morph cols empty)
tools/build_lexicon.py             MOD  ingest LXX-only lemmas
tools/build_db.py                  MOD  load lxx tokens + mt_lxx table
tests/                             NEW  per-tool tests
```

---

### Task 0: Data acquisition + license verification (spike) — DONE

**Status:** COMPLETE. Commit `47195c4`. Deliverable `docs/FORMATS-lxx.md`; full findings in `.superpowers/sdd/task-0-report.md`.

**Outcome (drives every task below):** open-subset build. LXX text = Swete PD; lemmas = openscriptures LxxLemmas CC-BY; versification = TVTMS Greek column (already parsed-past by `tools/tvtms.py`) + CC0 supplement; Strong's join by raw-oxia string match (no NFC); morphology + word-level alignment have no open source → deferred / verse-level fallback. All ready-made morph/alignment LXX sources are CC-BY-NC → rejected.

No further work in this task. Read `docs/FORMATS-lxx.md` before each downstream task for the exact source layouts, the LxxLemmas record format, the Swete edition, and the book list.

---

### Task 1: Book registry + LXX↔MT versification map

**Files:**
- Modify: `data/books.json`, `tools/tvtms.py`
- Create: `data/versification/lxx-versification.json`, `tools/lxx_versification.py`
- Create: `tests/test_lxx_versification.py`

**Interfaces:**
- Consumes: `docs/FORMATS-lxx.md` (book list + versification findings); the TVTMS file already cached/fetched by `tools/tvtms.py`.
- Produces:
  - `data/books.json` rows for every LXX book with `testament:"lxx"`, `code`, `lxx_name`, `chapters`, `lxx_order`, and (for doublets) `text_form`.
  - `lxx_books() -> list[dict]` in `tools/lxx_versification.py` returning the LXX book rows (testament `lxx`).
  - `mt_ref(lxx_code, lxx_chapter, lxx_verse) -> str|None` — MT `"chapter:verse"` for a protocanon LXX position, or `None` if no MT counterpart (deuterocanon or genuinely absent).
  - `load_lxx_vmap() -> dict` loading `data/versification/lxx-versification.json`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_lxx_versification.py
from tools.lxx_versification import mt_ref, lxx_books

def test_psalms_offset_known_case():
    # LXX Psalm numbering diverges from MT. Use the exact pair recorded in
    # docs/FORMATS-lxx.md (TVTMS Psalms offset) — adjust c:v to that documented case.
    assert mt_ref("PSA", 9, 22) == "10:1"

def test_deuterocanon_has_no_mt():
    assert mt_ref("1MA", 1, 1) is None

def test_lxx_books_present_with_codes():
    books = lxx_books()
    assert len(books) >= 39
    codes = {b["code"] for b in books}
    assert {"GEN", "PSA", "1MA", "3MA", "4MA", "ODE", "PSS"} <= codes
    assert all(b.get("testament") == "lxx" for b in books)
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_lxx_versification.py -v`
Expected: FAIL with `ModuleNotFoundError: tools.lxx_versification`.

- [ ] **Step 3: Add LXX book rows to `data/books.json`** per `docs/FORMATS-lxx.md` and the Global Constraints book-code rules: protocanon GEN…MAL (LXX Minor-Prophets order, `lxx_name` e.g. "Kingdoms"/"Paralipomenon"/"Asma"); deuterocanon reusing existing apo codes; new codes `3MA`/`4MA`/`ODE`/`PSS`; Epistle of Jeremiah folded as `BAR` ch.6; Psalm 151 as `PSA` ch.151; doublets get a `text_form` field, not new codes. Do NOT touch `2ES`.

- [ ] **Step 4: Build the versification map.** Extend `tools/tvtms.py` to emit its already-parsed Greek/LXX column (additive — do not change existing Hebrew/Latin output), then implement `tools/lxx_versification.py` (`lxx_books`, `load_lxx_vmap`, `mt_ref`) producing `data/versification/lxx-versification.json` from the TVTMS LXX rows plus a CC0 supplement (`data/versification/lxx-versification-supplement.json`, mirroring the existing `ot-versification-supplement.json`) for what TVTMS does not model: Jeremiah chapter reorder, integrated Greek-Esther/Greek-Daniel additions, book-level chapter-count gaps. Map keys LXX `CODE.chapter.verse` → MT `chapter:verse` (or no-counterpart).

- [ ] **Step 5: Run tests to verify they pass.**

Run: `python -m pytest tests/test_lxx_versification.py -v`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add data/books.json data/versification/lxx-versification.json data/versification/lxx-versification-supplement.json tools/tvtms.py tools/lxx_versification.py tests/test_lxx_versification.py
git commit -m "feat: LXX book registry + LXX<->MT versification map"
```

---

### Task 2: LXX corpus generator (Swete text)

**Files:**
- Create: `tools/sources/lxx_source.py`, `tools/generate_lxx.py`, `tools/validate_lxx.py`
- Create: `tests/test_generate_lxx.py`
- Modify: `.gitignore` (only if `data/cache/morph/raw/lxx/` is not already covered by `data/cache/`)

**Interfaces:**
- Consumes: the cached Swete PD text (per `docs/FORMATS-lxx.md`); `tools.lxx_versification.mt_ref`/`lxx_books`.
- Produces:
  - `LxxSource` in `tools/sources/lxx_source.py` exposing `chapter(book_meta, chapter) -> {verse:int -> greek_text:str}` and `chapters(book_meta) -> [int]`, mirroring the existing `tools/sources/` backends.
  - `tools/generate_lxx.py` with `build_chapter(code, chapter, src_verses) -> dict` and a driver writing `bible/lxx/<CODE>/NNN.json`: each verse `{"verse":int, "greek_lxx":str, "refs":{...}}` where `refs.mt = {"src": "<c:v>"}` for protocanon positions whose MT ref differs and `{"absent": true}` where no MT counterpart. `--book CODE` flag.
  - `validate(testament="lxx") -> dict` in `tools/validate_lxx.py`: asserts contiguous verses, non-empty `greek_lxx`, book/chapter coverage vs `data/books.json`; pins total LXX verse count.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_generate_lxx.py
from tools.generate_lxx import build_chapter

def test_build_chapter_shapes_verses():
    src = {1: "εν αρχη εποιησεν ο θεος", 2: "η δε γη ην αορατος"}
    ch = build_chapter("GEN", 1, src)
    assert ch["book_id"] == "GEN"
    assert ch["chapter"] == 1
    assert ch["verses"][0] == {"verse": 1, "greek_lxx": "εν αρχη εποιησεν ο θεος"}
    assert ch["verses"][1]["verse"] == 2
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_generate_lxx.py -v`
Expected: FAIL with `ModuleNotFoundError: tools.generate_lxx`.

- [ ] **Step 3: Implement the Swete source backend + `build_chapter` + driver.** `build_chapter(code, chapter, src_verses)` returns the chapter dict (verses sorted ascending, `greek_lxx` the Swete text verbatim). The driver walks `lxx_books()`, pulls each chapter from `LxxSource`, attaches `refs.mt` via `mt_ref` (protocanon only; deuterocanon gets no `mt` ref), writes `bible/lxx/<CODE>/NNN.json`. Implement `validate_lxx.py` structural checks. Confirm `data/cache/morph/raw/lxx/` is gitignored.

- [ ] **Step 4: Run the unit test + generate one book.**

Run: `python -m pytest tests/test_generate_lxx.py -v` → PASS.
Run: `python -m tools.generate_lxx --book RUT`
Expected: `bible/lxx/RUT/001.json`… exist, every verse has non-empty `greek_lxx`.

- [ ] **Step 5: Commit.**

```bash
git add tools/sources/lxx_source.py tools/generate_lxx.py tools/validate_lxx.py tests/test_generate_lxx.py bible/lxx/RUT
git commit -m "feat: LXX corpus generator (Swete PD); Ruth green"
```

---

### Task 3: LXX normalizer → fixed-schema TSV (lemma + Strong's, morph empty)

**Files:**
- Create: `tools/morph_norm/lxx.py`
- Create: `tests/test_morph_norm_lxx.py`

**Interfaces:**
- Consumes: the cached LxxLemmas source (per `docs/FORMATS-lxx.md`); `lexicon/grc/*.json` for the raw-string lemma→Strong's index.
- Produces:
  - `lemma_strong_index() -> dict[str,str]` mapping **raw** Greek lemma → `G####` from `lexicon/grc/` (no NFC — see Global Constraints).
  - `normalize_lxx(raw_path) -> list[dict]` with keys `ref, idx, surface, lemma, strong, xpos, feats, translit, edition`: `edition` `"LXX"`; `strong` filled via the raw-string index, else `""`; `xpos`/`feats`/`translit` all `"_"` (no morph source); `ref` mapped to `CODE.chapter.verse` (LXX versification) via the book-abbrev→CODE map from `docs/FORMATS-lxx.md` + the Global Constraints code rules.
  - A CLI writing `data/cache/morph/lxx.tsv` (same header as the floor's normalizers, via a shared `_write_tsv`).

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_morph_norm_lxx.py
from tools.morph_norm.lxx import normalize_lxx

def test_normalize_lxx_row(tmp_path):
    # One record in the LxxLemmas format documented in docs/FORMATS-lxx.md
    # (adjust the fixture to the real layout). Morph columns must be "_".
    raw = tmp_path / "lxx.txt"
    raw.write_text(
        "ref\tword\tlemma\n"
        "Gen.1.1#01\tεν\tἐν\n",
        encoding="utf-8",
    )
    rows = normalize_lxx(raw)
    assert rows[0]["ref"] == "GEN.1.1"
    assert rows[0]["idx"] == 1
    assert rows[0]["lemma"] == "ἐν"     # raw, not NFC
    assert rows[0]["xpos"] == "_"        # no open morph source
    assert rows[0]["feats"] == "_"
    assert rows[0]["edition"] == "LXX"
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_morph_norm_lxx.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tools/morph_norm/lxx.py`** per the real LxxLemmas layout (mirror the structure of `tools/morph_norm/stepbible_greek.py` where useful). Build `lemma_strong_index()` by reading `lexicon/grc/*.json` (`lemma` → `strong`) using the raw lemma string as the key (do NOT NFC). Fill `strong` when the LXX lemma matches, else `""`. Set `xpos`/`feats`/`translit` to `"_"`. Add the `_write_tsv` CLI.

- [ ] **Step 4: Run tests + generate the real TSV.**

Run: `python -m pytest tests/test_morph_norm_lxx.py -v` → PASS.
Run: `python -m tools.morph_norm.lxx` → writes `data/cache/morph/lxx.tsv`. Spot-check Genesis 1:1 rows and report the Strong's-link rate (LXX tokens that resolved a `G####`).

- [ ] **Step 5: Commit.**

```bash
git add tools/morph_norm/lxx.py tests/test_morph_norm_lxx.py
git commit -m "feat: LXX normalizer to fixed-schema TSV (lemma + raw-string Strong's link, morph deferred)"
```

---

### Task 4: Generalize the morph engine for LXX (de-collide grc nt vs lxx)

**Files:**
- Modify: `tools/align_morph.py`, `tools/generate_morph.py`, `data/morph-sources.json`
- Create: `tests/test_align_morph_lxx.py`

**Interfaces:**
- Consumes: `data/cache/morph/lxx.tsv`; `bible/lxx/` text; existing `align_verse`.
- Produces:
  - `load_norm(norm_path: str) -> dict` — CHANGED to take the explicit norm-file path from the registry entry (so two `grc` entries — `nt` and `lxx` — no longer collide on a lang-derived path). Update `generate_morph.py` to pass `entry["norm"]` at each call site.
  - Registry row appended to `data/morph-sources.json`: `{"lang":"grc","testament":"lxx","l0_field":"greek_lxx","norm":"data/cache/morph/lxx.tsv","edition_filter":"LXX","morph_scheme":"none","lexicon_sources":["strongs-greek"],"domain_source":"ln-map"}`. `morph_scheme:"none"` tells `generate_morph` to skip morph decoding (XPOS/UPOS/FEATS stay empty); only LEMMA + `Strong=` are written. (When TAGOT lands, flip this to the TAGNT scheme and morph fills additively.)
  - `--testament <t>` filter on `generate_morph` (additive, alongside `--lang`/`--book`).

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_align_morph_lxx.py
from tools.align_morph import load_norm

def test_load_norm_takes_explicit_path(tmp_path):
    p = tmp_path / "lxx.tsv"
    p.write_text(
        "ref\tidx\tsurface\tlemma\tstrong\txpos\tfeats\ttranslit\tedition\n"
        "GEN.1.1\t1\tεν\tἐν\tG1722\t_\t_\t_\tLXX\n",
        encoding="utf-8",
    )
    by_ref = load_norm(str(p))
    assert by_ref["GEN.1.1"][0]["strong"] == "G1722"
    assert by_ref["GEN.1.1"][0]["lemma"] == "ἐν"
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_align_morph_lxx.py -v`
Expected: FAIL (current `load_norm` takes a lang, not a path).

- [ ] **Step 3: Refactor `load_norm` to take the norm path; update `generate_morph` callers** to pass `entry["norm"]`. Confirm the existing NT/OT registry rows still resolve (their `norm` paths are already in the registry). Add the `lxx` registry row with `morph_scheme:"none"`; in `generate_morph`, when `morph_scheme=="none"` skip the `decode(...)` call and leave UPOS/XPOS/FEATS empty. Add the `--testament` filter.

- [ ] **Step 4: Run tests + regression + one LXX book green.**

Run: `python -m pytest tests/test_align_morph_lxx.py tests/test_align_morph.py -v` → PASS.
Run: `python -m tools.generate_morph --lang grc --book 3JO` (NT regression — still fully tagged with morph) then `python -m tools.morph_norm.lxx && python -m tools.generate_morph --testament lxx --book RUT`.
Expected: `morph/lxx/RUT/001.conllu` exists; `FORM` from `bible/lxx/RUT` (Swete); each token carries `LEMMA` + `MISC Strong=` where linked; UPOS/XPOS/FEATS columns are `_`. Report Ruth unmatched % (Swete-text ↔ LxxLemmas surface divergence — pin honestly).

- [ ] **Step 5: Commit.**

```bash
git add tools/align_morph.py tools/generate_morph.py data/morph-sources.json tests/test_align_morph_lxx.py morph/lxx/RUT
git commit -m "feat: generalize morph engine for LXX (path-keyed load_norm, morph_scheme=none); Ruth LXX green"
```

---

### Task 5: Full LXX lemma-tagging + validator pins

**Files:**
- Modify: `tools/validate_morph.py`
- Create: `tests/test_validate_morph_lxx.py`

**Interfaces:**
- Consumes: `morph/lxx/**`, `bible/lxx/**`.
- Produces: `validate("lxx")` returning `{"verses","tokens","unmatched","source_extra","missing_strong","with_morph"}`; structural asserts (every `bible/lxx/` verse has one CoNLL-U sentence; every `FORM` reconciles to its LXX verse text; `with_morph == 0` — morph columns intentionally empty); pinned LXX constants; exits nonzero on drift.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_validate_morph_lxx.py
from tools.validate_morph import reconcile_form

def test_reconcile_form_lxx_present():
    assert reconcile_form("αρχη", "εν αρχη εποιησεν") is True
```

- [ ] **Step 2: Run test to verify it passes (reuse) — the new work is the lxx branch + pins.**

Run: `python -m pytest tests/test_validate_morph_lxx.py -v`
Expected: PASS for `reconcile_form` reuse.

- [ ] **Step 3: Add the `"lxx"` branch to `validate()`** (mirror the `ot` branch: load `lxx_books()`, walk `bible/lxx/` + `morph/lxx/`). Generate the full LXX tagging (`python -m tools.generate_morph --testament lxx`), run `python -m tools.validate_morph lxx`, observe counts, PIN them (`EXPECTED_LXX_VERSES`, `EXPECTED_LXX_TOKENS`, `EXPECTED_LXX_UNMATCHED`, `EXPECTED_LXX_MISSING_STRONG`). Assert `with_morph == 0` with a comment: "morph deferred to TAGOT; lemma+Strong's only." LXX Strong's-link rate is lower than NT (LXX-only vocabulary) — pin the real `missing_strong` and name the cause. Re-run to confirm exit zero.

- [ ] **Step 4: Run validator + full suite.**

Run: `python -m tools.validate_morph lxx` → prints + exits 0 against pins.
Run: `python -m pytest -q` → green.

- [ ] **Step 5: Commit.**

```bash
git add tools/validate_morph.py tests/test_validate_morph_lxx.py morph/lxx
git commit -m "feat: full LXX lemma+Strong's tagging aligned + pinned coverage (morph deferred)"
```

---

### Task 6: Extend lexicon with LXX-only lemmas

**Files:**
- Modify: `tools/build_lexicon.py`
- Create: `tests/test_build_lexicon_lxx.py`

**Interfaces:**
- Consumes: `data/cache/morph/lxx.tsv` (the lemma set, incl. lemmas with empty `strong`); existing Greek gloss sources.
- Produces: `lxx_only_lemmas() -> list[str]` (LXX lemmas not resolvable to an existing `lexicon/grc/` Strong's). `build_lexicon` extended to emit lemma-keyed entries for them: `lexicon/grc/lemma-<slug>.json` with `{"strong": null, "lemma": ..., "lang":"grc", "glosses":{...}, "sources":[...], "domains":[], "senses":[]}` — NO fabricated Strong's. Gloss from a PD/CC-BY Greek source if the lemma resolves there, else empty glosses (slot ready).

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

- [ ] **Step 3: Implement `build_lemma_entry` + `lxx_only_lemmas`** and wire into the `build_lexicon` main pass (additive: existing Strong's-keyed entries unchanged; new lemma-keyed entries appended). Use a deterministic filesystem-safe slug for the filename (transliteration or a stable hash of the raw lemma) — document the slug rule.

- [ ] **Step 4: Run tests + rebuild + report.**

Run: `python -m pytest tests/test_build_lexicon_lxx.py -v` → PASS.
Run: `python -m tools.build_lexicon` → report how many LXX-only lemma entries were added and the overall LXX-token Strong's-link rate.

- [ ] **Step 5: Commit.**

```bash
git add tools/build_lexicon.py tests/test_build_lexicon_lxx.py lexicon/grc
git commit -m "feat: extend lexicon with LXX-only lemma-keyed entries"
```

---

### Task 7: MT↔LXX bridge artifact (verse-level co-occurrence)

**Files:**
- Create: `tools/align_mt_lxx.py`, `tests/test_align_mt_lxx.py`

**Interfaces:**
- Consumes: `tools.lxx_versification.mt_ref`; `morph/ot/**` (MT Hebrew tokens, with Strong's) and `morph/lxx/**` (LXX Greek tokens, with Strong's).
- Produces:
  - `align_verse_pair(lxx_ref:str, mt_ref:str, mt_tokens:list, lxx_tokens:list) -> list[dict]` producing edges `{"lxx_ref","mt_ref","mt_strong","lxx_strong","lxx_lemma","confidence","src"}`. Verse-level co-occurrence: the content-word cross-product of the corresponding MT and LXX verse; every edge `confidence="verse-cooccurrence"`, `src="derived:verse-cooccurrence"`.
  - A driver writing `align/mt-lxx/<CODE>/NNN.json` for protocanon books (keyed by LXX ref), using `mt_ref` to pair each LXX verse to its MT verse; deuterocanon skipped (no MT). Coverage pinned.

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_align_mt_lxx.py
from tools.align_mt_lxx import align_verse_pair

def test_verse_level_edges_carry_provenance():
    mt = [{"strong": "H7225", "lemma": "רֵאשִׁית"}]
    lxx = [{"strong": "G0746", "lemma": "ἀρχή"}]
    edges = align_verse_pair("GEN.1.1", "GEN.1.1", mt, lxx)
    assert edges[0]["mt_strong"] == "H7225"
    assert edges[0]["lxx_strong"] == "G0746"
    assert edges[0]["lxx_lemma"] == "ἀρχή"
    assert edges[0]["confidence"] == "verse-cooccurrence"
    assert edges[0]["src"]
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `python -m pytest tests/test_align_mt_lxx.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `align_mt_lxx.py`.** Emit the content-word cross-product of each corresponding MT/LXX verse (skip tokens with empty `strong`), every edge flagged `confidence="verse-cooccurrence"`. Use `mt_ref` to pair LXX verses to MT verses; skip deuterocanon. Driver writes `align/mt-lxx/<CODE>/NNN.json`. (The schema carries a `confidence` field so a future word-level source can add `confidence="word"` edges additively without a migration.)

- [ ] **Step 4: Run tests + build + report.**

Run: `python -m pytest tests/test_align_mt_lxx.py -v` → PASS.
Run: `python -m tools.align_mt_lxx` → report protocanon coverage (edge count, % of LXX protocanon verses with ≥1 edge). Spot-check GEN.1.1 (H7225 רֵאשִׁית co-occurs with G0746 ἀρχή).

- [ ] **Step 5: Commit.**

```bash
git add tools/align_mt_lxx.py tests/test_align_mt_lxx.py align/mt-lxx
git commit -m "feat: MT<->LXX verse-level co-occurrence bridge (protocanon, confidence-flagged)"
```

---

### Task 8: DB extension (LXX tokens + mt_lxx table)

**Files:**
- Modify: `tools/build_db.py`
- Create: `tests/test_build_db_lxx.py`

**Interfaces:**
- Consumes: `bible/lxx/**`, `morph/lxx/**`, `align/mt-lxx/**`, extended `lexicon/grc/`.
- Produces: `verses` gains LXX rows (`testament="lxx"`, `greek` column = `greek_lxx`); `tokens` gains LXX rows (`testament="lxx"`); new table `mt_lxx(lxx_ref, mt_ref, mt_strong, lxx_strong, lxx_lemma, confidence, src)` with indexes on `mt_strong`, `lxx_strong`. `lexicon`/`glosses` include the LXX-only lemma entries (strong nullable).

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

- [ ] **Step 3: Extend `build_db.py`** to load `bible/lxx/` into `verses`, `morph/lxx/` into `tokens` (testament `lxx`; empty UPOS/XPOS/FEATS stored as NULL/empty consistently with how the floor stores absent fields), and `align/mt-lxx/` into a new `mt_lxx` table; create its indexes; keep the build one transaction + idempotent. Handle nullable `strong` in `lexicon` for LXX-only lemma rows.

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
git commit -m "feat: DB loads LXX tokens + mt_lxx bridge table (cross-language join)"
```

---

### Task 9: Docs + full regen determinism check

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: README section documenting the LXX corpus, lemma+Strong's tagging, the verse-level MT↔LXX bridge, the deferred-morph status, the regenerate sequence, and attributions.

- [ ] **Step 1: Add a README section** describing `bible/lxx/`, `morph/lxx/` (lemma+Strong's; morph columns empty pending TAGOT), `align/mt-lxx/` (verse-level co-occurrence), the LXX↔MT versification map, and the regenerate sequence:

```
python -m tools.generate_lxx              # -> bible/lxx/   (Swete PD)
python -m tools.morph_norm.lxx            # -> data/cache/morph/lxx.tsv  (LxxLemmas + Strong's)
python -m tools.generate_morph --testament lxx   # -> morph/lxx/ (lemma+Strong's, morph empty)
python -m tools.validate_morph lxx
python -m tools.build_lexicon             # + LXX-only lemmas
python -m tools.align_mt_lxx              # -> align/mt-lxx/ (verse-level bridge)
python -m tools.build_db                  # + lxx tokens + mt_lxx table
```
(verify these module paths/flags match what was built; correct any that differ.)

- [ ] **Step 2: Add attributions + a "Deferred" note.** Sources/License sections credit: Swete 1909 (PD), openscriptures GreekResources LxxLemmas (CC-BY 4.0), STEPBible TVTMS (CC-BY 4.0), CC0 versification supplement. Add a short "Deferred (open-source gated)" note: full LXX morphology awaits STEPBible TAGOT (CC-BY) release — backfills the empty UPOS/XPOS/FEATS via the existing TAGNT decoder by flipping the registry `morph_scheme`; a word-level MT↔LXX alignment would upgrade the bridge from verse-level co-occurrence when an open source appears.

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
git commit -m "docs: document LXX integration (open subset) + source attributions"
```

---

## Self-Review

**Spec coverage (against the approved design spec, as amended by the Task-0 open-subset decision):**
- Full LXX (protocanon + deuterocanon) corpus → Tasks 1,2 (Swete PD). ✓
- Lemma + Strong's tagging (raw-string join, no NFC) → Tasks 3,4,5. ✓
- Morphology → DEFERRED (no open source; TAGOT backfill). Columns ship empty, pinned `with_morph==0`. ✓ (scope change, user-approved)
- LXX-only lemma lexicon entries → Task 6. ✓
- MT↔LXX bridge → Task 7, verse-level co-occurrence (word-level has no open source). ✓ (degraded, user-approved)
- LXX↔MT versification (TVTMS Greek column + CC0 supplement) → Task 1. ✓
- DB extension (lxx tokens + mt_lxx table) → Task 8. ✓
- Two-form/additive/registry-driven; L0 untouched; bible/lxx own tree → Global Constraints, Tasks 2,4. ✓
- Apocrypha coexistence (reuse apo codes, own tree, doublets as text_form) → Global Constraints, Task 1. ✓
- PD/CC-BY only; provenance; rejected NC sources → Global Constraints, Task 0. ✓
- Boundary: no relation edges (that's L2b) → not implemented; the mt_lxx table is the handoff. ✓

**Placeholder scan:** Task fixtures say "adjust to the real layout per FORMATS-lxx.md" for the two source-parsing tests (LxxLemmas record format, Swete edition) — the exact byte layout is documented in the committed `docs/FORMATS-lxx.md`, and the normalized-TSV quarantine boundary keeps every downstream task deterministic. No `TBD`/`TODO`/"handle edge cases" left.

**Type consistency:** `mt_ref`/`lxx_books`/`load_lxx_vmap` (Task 1) used in Tasks 2,7; `load_norm(norm_path)` signature change (Task 4) consumed by `generate_morph`; `morph_scheme:"none"` (Task 4) honored by `generate_morph` and asserted by `validate` `with_morph==0` (Task 5); normalized-TSV columns identical to the floor's schema (Task 3) and consumed by `load_norm` (Task 4); `align/mt-lxx` edge keys (`lxx_ref`/`mt_ref`/`mt_strong`/`lxx_strong`/`lxx_lemma`/`confidence`/`src`) consistent between Task 7 producer and Task 8 `mt_lxx` table; `greek_lxx` field name consistent across Tasks 2,4,8; Strong's `G####` 4-digit padding and raw-oxia (non-NFC) join key consistent across Tasks 3,4,6.
