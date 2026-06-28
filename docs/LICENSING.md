# Licensing

This project mixes three license regimes by artifact type. The goal: **software
under AGPL-3.0, content under CC0 wherever possible**, with CC-BY retained only
where a dataset is derived from a CC-BY source whose attribution we are bound to
preserve.

## Quick map

| Artifact | License | File |
|----------|---------|------|
| All software (everything under `tools/`, build scripts, test code) | **AGPL-3.0-or-later** | [`LICENSE`](../LICENSE), [`licenses/AGPL-3.0.txt`](../licenses/AGPL-3.0.txt) |
| Original content + content derived solely from public-domain sources | **CC0-1.0** (public-domain dedication) | [`licenses/CC0-1.0.txt`](../licenses/CC0-1.0.txt) |
| Content derived from a CC-BY source (attribution required) | **CC-BY-4.0** | [`licenses/CC-BY-4.0.txt`](../licenses/CC-BY-4.0.txt) |

When a file mixes regimes (e.g. a token record carrying both a PD surface form
and a CC-BY morphology tag), the **most restrictive applicable** license governs
that datum, and the CC-BY attribution below is required.

## Software — AGPL-3.0-or-later

Every line of code in this repository (the `tools/` package, generators,
validators, build and test scripts) is licensed **GNU Affero General Public
License, version 3 or any later version**. If you run a modified version of this
software to provide a network service, the AGPL requires you to offer the
modified source to users of that service.

## Content — CC0-1.0 (default)

The following are dedicated to the public domain under **CC0-1.0**. To the
extent we hold any copyright or database right in them, we waive it:

- The repository's original compilation, schema, and file structure.
- Hand-authored data we created: the CC0 versification supplements
  (`data/versification/*-supplement.json`).
- The verse-aligned biblical **text** corpora, which are themselves public
  domain by age and carry no new copyright from mechanical transcription
  (Westminster Leningrad Codex; Clementine Vulgate; King James Version; **Swete,
  _The Old Testament in Greek_, 1909, sourced as public-domain text, not from
  any later GPL/other-licensed repackaging**).
- The Strong's dictionary spine (James Strong, 1890, public domain).
- Any derived data computed **solely** from public-domain inputs.

## Content — CC-BY-4.0 (attribution required)

These datasets are derived from CC-BY sources. The derived data in this
repository remains **CC-BY-4.0** and the attributions below MUST be preserved by
anyone redistributing it:

- **Versification mapping** derived from **STEPBible TVTMS** (Translators
  Versification Traditions Mapping System), Tyndale House Cambridge — CC-BY 4.0.
  (Our `*-supplement.json` additions are CC0; the TVTMS-derived map is CC-BY.)
- **Morpho-lexical tags** (NT/OT, and any future LXX morphology) derived from
  **STEPBible TAGNT / TAHOT / TBESG / TAGOT** — STEPBible.org, Tyndale House
  Cambridge — CC-BY 4.0.
- **Semantic-domain data** (Louw-Nida / SDBH) from the **MACULA Greek and Hebrew
  Linguistic Datasets, Clear Bible Inc.** — CC-BY 4.0.
- **LXX lemmas** from **openscriptures GreekResources `LxxLemmas`** (Open
  Scriptures Septuagint Project, David Troidl) — CC-BY 4.0. (Bare lemma strings
  are uncopyrightable lexical facts; we attribute regardless to honor the
  source.)

### Required attribution strings

- STEPBible (TVTMS, TAGNT, TAHOT, TBESG, TAGOT): "Data from STEPBible.org,
  Tyndale House Cambridge, CC-BY 4.0."
- MACULA: "MACULA Greek/Hebrew Linguistic Datasets, Clear Bible Inc., CC-BY 4.0.
  https://github.com/Clear-Bible/macula-greek and macula-hebrew"
- openscriptures LxxLemmas: "Open Scriptures Septuagint lemmas (David Troidl),
  CC-BY 4.0. https://github.com/openscriptures/GreekResources"

## Excluded / not redistributed

Sources whose licenses are incompatible with the above are **not** included in
this repository and are never shipped:

- CATSS / CCAT LXX morphology and the CATSS/Tov MT↔LXX alignment (CC-BY-NC +
  user declaration) — rejected.
- eliranwong LXX repackagings (GPL-3.0, CATSS-derived) — not redistributed; the
  PD Swete text is sourced as public-domain text, not copied from those repos.

## Per-datum provenance

Every generated datum carries `src` / `sources` provenance fields, so the
governing license of any value is mechanically traceable to the table above.
