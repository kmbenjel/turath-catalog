# Contributing

Thank you for helping. Two kinds of contribution are welcome.

## Corrections to the data

Open an issue with the **Correction** template and give:

1. the `edition_id` (or `work_id`, `author_id`);
2. the column and the value you propose;
3. the evidence: what the title page or the imprint page says (a photo of the page is best), or a
   catalog record of the **same** edition.

A correction is applied when the evidence shows the same edition. Values from another printing of the
work are added as that printing, not as a correction. Every accepted correction appears in the
CHANGELOG of the next release.

## Code

```bash
git clone https://github.com/kmbenjel/turath-catalog
cd turath-catalog
uv venv && uv pip install -e ".[dev]"
make check          # ruff + pytest with coverage
```

- Python 3.10+, stdlib in the core; Parquet, pandas and matplotlib stay optional.
- Every table and column lives in `src/turath_catalog/model.py`; after changing it run
  `turath-catalog schema` and commit the regenerated `schema/` and `docs/data-dictionary.md`
  (a test fails when they are stale).
- The id recipe (`textnorm.title_key`, `textnorm.author_key`, `build.work_id_for`) is shared with
  turath-match and arabic-bib. Changing it is a major version.
- New source adapters go in `src/turath_catalog/sources/` and return `EditionRecord`s, with the source
  of each value in `sources`. Never read free-text descriptions into a record.
- Tests: add a case for each rule you add; keep the sample (`src/turath_catalog/sample/`) valid.
