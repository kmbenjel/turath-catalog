# Changelog

All notable changes to the dataset and its tools. The project follows [Semantic Versioning](https://semver.org):
for the data, a MAJOR version changes or removes columns or id recipes, a MINOR version adds rows,
columns or links, a PATCH version corrects values.

## [0.2.0] - unreleased

Columns are only added, each at the end of its table, and the id recipes are those of 0.1.0: every
edition, author, manuscript and file id of 0.1.0 is in 0.2.0 (`bench/quality.json`, section `against`).

### Data
- **Titles as given and clean.** `editions.title_ar` and `works.title_ar` keep the library's title cell;
  the new `title_clean_ar` is the title alone. New `editions.alt_titles_ar` holds the other titles of the
  work («الجامع لأحكام القرآن = تفسير القرطبي», «(تفسير ابن عادل)») and `editions.title_note_ar` the
  remarks («(من النحل إلى الصافات)»). 103 edition titles and 45 work titles carry such a part.
- **Edition marks checked against the edition.** «ط. الخانجي» or «ت - الميمني» in a title is dropped from
  the clean title when `publisher_ar` or `editors_ar` already says it, fills `publisher_ar` when the row
  named no publisher (2 editions, source `file_label`), and stays in `title_note_ar` when the row says
  otherwise (3 editions). `label_ar` is composed from the clean title.
- **Works.** A title written «A = B» is the work «A»: it groups with the editions titled «A» (5,134
  works; 371 with several editions; each merged work's OpenITI link stays on the work it joins).
  `works.alt_titles_ar` also takes the other titles given in brackets, which links 2 more works to
  OpenITI (1,683 OpenITI URIs in all).
- **People.** New `authors.canonical_author_id`: name forms that carry the same Shamela author id and no
  conflicting death year point to one row (192 forms folded, 2,451 people). Author rows and their ids
  are unchanged.
- **Death years.** `death_confidence` is `low` (44 authors) when the year is that of the author of a
  matched Shamela book whose name could not be matched to the row's name.
- **Contributors.** A body keeps its whole name («مركز البحوث وتقنية المعلومات»), full names joined by a
  dash are separate people, and what is left of a mark is not a name (2,265 contributors, 3,999 credits).
- `pocketshelf.csv`: `title` is the clean title; new last columns `alt_titles` and `note`.

### Tools
- `turath_catalog.titles.split_title` and `mark_agrees`: the title split as a function.
- `validate` checks the clean titles and the canonical author references, and still accepts a release
  built before these columns existed.
- `bench/quality.py` (`make quality`): audit of title parts, duplicates, death years and id recipes, and
  of the ids and values that differ from an earlier release.

## [0.1.0] - 2026-11-13

### Data
- 5,139 works, 5,626 editions, 2,643 authors (1,239 with a death year), 2,265 editors (4,012 credits),
  31 manuscript copies, 15,079 scan files with exact sizes, 40 categories.
- Every edition value carries its source (`field_sources`); every edition a confidence.
- Links: 1,685 OpenITI book URIs (release 2025.1.9), 875 OpenITI author URIs, 842 Wikidata authors,
  460 Wikidata works, 109 Wikidata editions, 2,313 works with Shamela book ids.
- CSV, JSON Lines and Parquet; `pocketshelf.csv` for the pocketshelf catalog; `SHA256SUMS`.

### Tools
- `turath-catalog build` from a Warraq library workspace or from any CSV catalog (one row per edition).
- `validate` (schema, unique ids, references, counts, Hijri/Gregorian consistency, leak checks),
  `info`, `charts`, `schema` (JSON Schemas + data dictionary), `sample`, `compare` (coverage against
  OpenITI, Wikidata and Shamela).
- Stable ids shared with turath-match and arabic-bib ("keys v1").

[0.2.0]: https://github.com/kmbenjel/turath-catalog/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kmbenjel/turath-catalog/releases/tag/v0.1.0
