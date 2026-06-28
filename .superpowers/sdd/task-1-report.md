# Task 1 Report: LXX Book Registry + LXX<->MT Versification Map

## Status

DONE

## Commits

Base: `9ca1b980` (HEAD before this task)
After commit: see `git log --oneline` for the new commit hash (feat: LXX book registry + LXX<->MT versification map)

## Test Summary

- Task tests: 3/3 pass (test_psalms_offset_known_case, test_deuterocanon_has_no_mt, test_lxx_books_present_with_codes)
- Full suite: 252 green (249 pre-existing + 3 new)

## books.json LXX Row Structure

**Design decision:** The existing `test_codes_unique_and_three_chars` test enforces that all book codes are unique across the entire `books.json`. Adding duplicate-code rows with `testament:"lxx"` would break it. The minimal additive choice was chosen:

1. **OT protocanon rows (GEN..MAL):** Added `lxx_name`, `lxx_order` fields to existing `testament:"ot"` rows. Two doublet rows also received `text_form` (JOS: "B", JDG: "A", DAN: "Th"). PSA got `chapters_lxx: 151`. No `testament` field changed.

2. **Apo rows (1ES, TOB, JDT, ADE, WIS, SIR, BAR, PAZ, SUS, BEL, MAN, 1MA, 2MA):** Added `lxx_name`, `lxx_order` fields. SUS, BEL also got `text_form: "Th"`. TOB got `text_form: "BA"`. `2ES` is untouched (it is 4 Ezra, not an LXX book).

3. **New LXX-only rows** (4 total, all new codes): `3MA`, `4MA`, `ODE`, `PSS` with `testament:"lxx"`. These are the only rows with `testament:"lxx"` in books.json.

**Apo coexistence:** Apo rows retain `testament:"apo"` in books.json. `lxx_books()` synthesizes the LXX view at runtime by copying any row with `lxx_order` set and overriding `testament` to `"lxx"`. This preserves both traditions without structural conflict.

The consequence: `books.json` does NOT have explicit LXX rows for GEN..MAL or the deuterocanon codes. The `lxx_books()` function builds them dynamically. All returned dicts have `testament:"lxx"` (test assertion satisfied).

## Versification Map Coverage

**lxx-versification.json:** 3,730 Greek divergences extracted from the TVTMS Greek/LXX column (STEPBible CC BY 4.0). Format: key = LXX `"CODE C:V"` (e.g., `"PSA 9:22"`), value = MT `"chapter:verse"` (e.g., `"10:1"`). Covers:
- **Psalms numbering offset:** All 18 merged-Psalm-9/10 pairs (PSA 9:22-9:39 -> 10:1-10:18) plus the full Psalter offset cascade (LXX runs one psalm behind MT from ch.10 onwards).
- **Exodus verse shifts** (Exo 8, 20, 21, 22, 25, 28, 35, 36, 37, 38, 39, 40 etc.)
- **Numbers verse shifts** (Num 1, 6, 10, 26 etc.)
- **Genesis, Leviticus, Deuteronomy, Joshua, Judges, Samuel/Kings** divergences.
- **Esther additions** (Est.A-F in Greek column; skipped because "Esg" not in ABBR -- see concerns).
- **Daniel additions** (S3Y/Sus/Bel skipped -- see concerns).
- General verse-boundary shifts across the protocanon.

**lxx-versification-supplement.json:** CC0 hand-authored supplement covering:
- Psalm 151 verses 1-7 -> null (no MT counterpart)
- Notes (as top-level string fields) on Jeremiah chapter reorder and the structural nature of Greek Esther/Daniel additions (not enumerable as simple verse pairs)

**mt_ref logic:**
- Deuterocanon codes (hardcoded frozenset) -> None
- Lookup `"CODE C:V"` in merged TVTMS+supplement map
- If explicit null value (PSA 151) -> None
- If found -> return MT "c:v"
- If not found (identity) -> return `"chapter:verse"`

## Real Psalms Pair Used

`mt_ref("PSA", 9, 22) == "10:1"` -- verified directly from TVTMS data:
- TVTMS block `$Psa.9:1-10:18`, BIBLES header, row `OneToOne Psa.10:1-18 [Hebrew] Psa.9:22-39 [Latin] Psa.9:22-39 [Greek]`
- LXX Psalm 9 superscription = verse 1, shifting content so LXX 9:22 = first verse of MT Psalm 10.

## Concerns / Risks for Downstream Tasks

1. **TVTMS "unmapped OT abbreviations" warning:** The Greek column of TVTMS references deuterocanon book abbreviations (`1Es, 1Ma, 2Ma, Bar, Bel, Esg, Jdt, Man, Ps2, S3Y, Sir, Sus, Tob, Wis`) that are not in the ABBR map. These are skipped. This is correct behaviour for `mt_ref` (deuterocanon has no MT counterpart anyway), but it means the LXX versification for Greek Esther (`Esg`) additions and Greek Daniel additions (`S3Y`/Susanna/Bel) is not captured as verse-level entries. The supplement notes this but does not enumerate them fully. Downstream tasks (generate_lxx, align_mt_lxx) that need to know the LXX position of these additions should consult the supplement note and implement book-specific logic.

2. **lxx_books() synthesizes testament:"lxx" at runtime:** The LXX view of protocanon and deuterocanon books is not stored persistently with `testament:"lxx"` in books.json -- it is synthesized by `lxx_books()`. Downstream tasks that load books.json directly (e.g., `generate_lxx.py`) must call `lxx_books()` rather than filtering books.json by `testament=="lxx"`.

3. **lxx_order for doublets:** JOS/JDG/DAN/SUS/BEL each have one `lxx_order` value covering the "standard" text-form (JOS=B, JDG=A, DAN=Th). The alternate text-forms (JOS A, JDG B, DAN OG, SUS OG, BEL OG, TOB S) share the same code and lxx_order. When Task 3 (normalizer) and Task 4 (morph engine) handle doublet editions, they should use the `text_form` field to distinguish editions within a code.

4. **Jeremiah chapter reorder:** The TVTMS captures some Jer verse-level divergences but NOT the chapter reorder (LXX OAN position mid-book vs MT end-of-book). The supplement notes this without enumerating it. Task 2 (generate_lxx) and Task 7 (align) will need custom logic for Jeremiah's structural rearrangement.

5. **`lxx_versification.json` is generated from live TVTMS fetch:** The file is committed to the repo (like `ot-versification.json`) so downstream tasks can load it without network access. But it was generated in this task by fetching the live TVTMS file. If the TVTMS upstream changes materially, regeneration requires `python -m tools.tvtms` (extended to emit the Greek section -- currently `main()` still writes only `ot-versification.json`). A TODO: extend `main()` to also write `lxx-versification.json`. **RESOLVED in fix pass below.**

---

## Fix Pass (review findings)

Commit: `11117cef`

### FIX 1 -- mt_ref footgun: returns None for non-protocanon codes

**Problem:** `mt_ref("2ES", 1, 1)` returned `"1:1"` (identity fallthrough) because 2ES was absent from `_DEUTEROCANON` and absent from the vmap, so the function fell through to the identity path.

**Root cause:** The exclusion logic was a hardcoded `_DEUTEROCANON` frozenset. 2ES is not an LXX book at all (4 Ezra / Latin apocalypse), not merely a deuterocanon book, so it was not listed.

**Fix:** Removed `_DEUTEROCANON` entirely. Replaced with a data-driven helper `_lxx_protocanon_codes()` (cached) that reads `data/books.json` and returns only codes where `testament == "ot"` and `lxx_order is not None`. These are exactly the LXX-participating OT books that have Hebrew (MT) counterparts. `mt_ref` now returns `None` immediately for any code not in this set, including:
- 2ES: `testament="apo"`, no `lxx_order` -- not in set
- 1MA, 1ES, TOB, etc.: `testament="apo"` -- not in set
- 3MA, 4MA, ODE, PSS: `testament="lxx"` -- not in set
- GEN, PSA, etc.: `testament="ot"` with `lxx_order` -- in set, proceed to vmap lookup

**Files changed:** `tools/lxx_versification.py` (removed `_DEUTEROCANON`, added `_protocanon_cache` + `_lxx_protocanon_codes()`, updated `mt_ref` docstring + guard).

**New test:** `tests/test_lxx_versification.py::test_non_lxx_code_has_no_mt`
```
assert mt_ref("2ES", 1, 1) is None
```

**Test run:**
```
$ python -m pytest tests/test_lxx_versification.py -v
tests/test_lxx_versification.py::test_psalms_offset_known_case PASSED
tests/test_lxx_versification.py::test_deuterocanon_has_no_mt PASSED
tests/test_lxx_versification.py::test_non_lxx_code_has_no_mt PASSED
tests/test_lxx_versification.py::test_lxx_books_present_with_codes PASSED
4 passed in 0.23s
```

### FIX 2 -- tvtms main() regenerates lxx-versification.json

**Problem:** `main()` (i.e. `python -m tools.tvtms`) wrote only `ot-versification.json`. The committed `lxx-versification.json` was generated ad-hoc during the task and could not be regenerated, violating Task 9's byte-identical determinism check.

**Structure of committed file:** TVTMS-only (no supplement); top-level keys `_attribution` + `greek`; 3,730 entries; `json.dumps(indent=2, ensure_ascii=False) + "\n"`. The supplement is merged at load time by `load_lxx_vmap()`. No reformatting needed.

**Fix:** Added `LXX_OUT_PATH` constant to `tools/tvtms.py` pointing at `data/versification/lxx-versification.json`. Extended `main()` to write a second output after the OT file, using the same format and containing only `{"_attribution": "...", "greek": m["greek"]}`. The attribution string matches the committed file exactly.

**Files changed:** `tools/tvtms.py` (added `LXX_OUT_PATH`, extended `main()`).

**Verification -- byte-identical regen:**
```
$ python -m tools.tvtms
WARNING: unmapped OT abbreviations: ['1Es', '1Ma', '2Es', '2Ma', '4Es', 'Bar', 'Bel', 'Esg', 'Jdt', 'Man', 'Ps2', 'S3Y', 'Sir', 'Sus', 'Tob', 'Wis']
Hebrew divergences: 1965
Latin divergences:  2835
Greek divergences:  3730
Written: .../data/versification/ot-versification.json
Written: .../data/versification/lxx-versification.json

$ git diff --stat data/versification/lxx-versification.json
(no output -- byte-identical)

$ git diff --stat data/versification/ot-versification.json
(no output -- byte-identical)
```

### Full suite after both fixes

```
$ python -m pytest -q
253 passed in 11.22s
```

252 pre-existing + 1 new (`test_non_lxx_code_has_no_mt`) = 253 green.
