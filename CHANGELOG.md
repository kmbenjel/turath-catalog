# Changelog

All notable changes to the dataset and its tools. The project follows [Semantic Versioning](https://semver.org):
for the data, a MAJOR version changes or removes columns or id recipes, a MINOR version adds rows,
columns or links, a PATCH version corrects values.

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

[0.1.0]: https://github.com/kmbenjel/turath-catalog/releases/tag/v0.1.0
