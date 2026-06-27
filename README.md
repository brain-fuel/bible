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
        "hebrew_masoretic": "1:1",
        "latin_vulgate": "absent"
      }
    }

#### Schema notes

- The OT `verse` field uses KJV versification for all traditions.
- The `refs` field is present only when a tradition diverges from KJV numbering.
  - `refs.hebrew_masoretic` gives the Hebrew "chapter:verse" where it differs from KJV numbering.
  - `refs.latin_vulgate: "absent"` marks the ten KJV verses the Clementine Vulgate merges into the previous verse (so `latin_vulgate` is empty in those cases).
  - `refs.hebrew_masoretic_absent: true` would mark a missing Hebrew verse (none currently present).
- Hebrew text includes full Masoretic pointing (vowels and cantillation marks), normalized to NFC form.

## Edition System

Each parallel text is registered in `data/editions.json` with metadata: id, language, source type, versification system, and license. New side-by-side texts can be added by appending a registry row and rerunning generation, without schema change.

## Sources

All underlying texts are in the public domain:

- **King James Version** (1611): Sourced from Scrollmapper's bible_databases datasets.
- **Clementine Vulgate** (Latin, 1592): Sourced from Scrollmapper's bible_databases datasets. Ten OT verses are merged into the preceding verse in the Vulgate tradition (recorded in `refs.latin_vulgate`).
- **Hebrew Masoretic Text** (Westminster Leningrad Codex): Sourced via the Sefaria API. Includes full Masoretic pointing with vowels and cantillation marks.
- **Greek Textus Receptus** (NT only): Sourced from the Logos Apostolic interlinear (https://www.logosapostolic.org/bibles/latin_vulgate_textus_receptus_king_james/).

## Versification Mapping and Attribution

The OT cross-tradition verse alignment is derived from **STEPBible's TVTMS** (Translators Versification Traditions Mapping System), produced by Tyndale House Cambridge. This data is licensed CC BY 4.0. A small hand-authored CC0 supplement (`data/versification/ot-versification-supplement.json`) aligns the Decalogue chapters (Exodus 20, Deuteronomy 5) to the Sefaria verse division.

**Credit STEPBible and link to** https://github.com/STEPBible when using this compilation.

## License

This repository is licensed CC BY 4.0 (see LICENSE file). The underlying biblical texts (Westminster Leningrad Codex, Clementine Vulgate, King James Version) are in the public domain. CC BY 4.0 applies to the compilation, code, and derived data in this repository. Attribution to STEPBible and Tyndale House Cambridge is required for the TVTMS-derived versification mapping.

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

Raw sources are cached in `data/cache/` (gitignored).
