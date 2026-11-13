# releases/

Built releases land here (`make release`) and are published as GitHub release assets and on Hugging Face;
they are not committed, to keep the repository small. The repository carries a 149-work sample in
`src/turath_catalog/sample/` that passes the same validation.

A release folder holds:

| path | what |
|---|---|
| `csv/<table>.csv` | UTF-8, header row, empty cell = null |
| `jsonl/<table>.jsonl` | one JSON object per row, nulls explicit |
| `parquet/<table>.parquet` | zstd, typed columns, column descriptions in the schema metadata |
| `pocketshelf.csv` | one row per edition in the catalog format of [pocketshelf](https://github.com/kmbenjel/pocketshelf) |
| `schema/<table>.schema.json` | JSON Schema of one row |
| `build-report.json` | row counts, what was excluded and why, link counts, confidence counts |
| `SHA256SUMS` | checksums of every file; two builds from the same inputs give the same sums |
