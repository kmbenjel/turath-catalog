import csv
import json
from pathlib import Path

import jsonschema
import pytest

from turath_catalog import load
from turath_catalog.export import POCKETSHELF_COLS, data_dictionary, pocketshelf_rows, read_tables, write_pocketshelf, write_tables
from turath_catalog.model import TABLES, json_schema

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def t(sample_dir):
    return load(sample_dir)


def test_every_sample_row_matches_its_json_schema(t):
    for name in TABLES:
        validator = jsonschema.Draft202012Validator(json_schema(name))
        for row in t[name]:
            validator.validate(row)


def test_committed_schemas_and_dictionary_are_current():
    for name in TABLES:
        on_disk = json.loads((ROOT / "schema" / f"{name}.schema.json").read_text(encoding="utf-8"))
        assert on_disk == json_schema(name), f"schema/{name}.schema.json is stale: run `turath-catalog schema`"
    assert (ROOT / "docs/data-dictionary.md").read_text(encoding="utf-8") == data_dictionary() + "\n"


@pytest.mark.parametrize("fmt", ["csv", "jsonl", "parquet"])
def test_round_trip(t, tmp_path, fmt):
    write_tables(t, tmp_path, (fmt,))
    if fmt == "parquet":
        import pyarrow.parquet as pq

        back = {n: pq.read_table(tmp_path / "parquet" / f"{n}.parquet").to_pylist() for n in TABLES}
        meta = pq.read_schema(tmp_path / "parquet" / "works.parquet")
        assert meta.metadata[b"license"] == b"CC-BY-4.0"
        assert meta.field("work_id").metadata[b"description"]
    else:
        back = read_tables(tmp_path)
    for n in TABLES:
        assert back[n] == [{c.name: r.get(c.name) for c in TABLES[n]["cols"]} for r in t[n]], n


def test_pocketshelf_export(t, tmp_path):
    p = write_pocketshelf(t, tmp_path / "pocketshelf.csv")
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == POCKETSHELF_COLS
    assert len(rows) == len(t["editions"])
    assert {r["author_calendar"] for r in rows} == {"ah"}
    assert all(r["path"] == "" for r in rows)
    multi = [r for r in rows if r["volumes"]]
    assert multi and all("||" in v for r in multi for v in r["volumes"].split(";"))
    works = {w["work_id"] for w in t["works"]}
    assert {r["work"] for r in rows} <= works
    linked = [r for r in pocketshelf_rows(t) if "openiti:" in r["ext_ids"]]
    assert linked
