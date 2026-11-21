"""Write the tables as CSV, JSON Lines and Parquet, plus the pocketshelf catalog, and read them back."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .model import TABLES, columns, json_schema

FORMATS = ("csv", "jsonl", "parquet")


def write_tables(tables: dict, out: Path, formats=FORMATS) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name in TABLES:
        rows = tables[name]
        cols = [c.name for c in columns(name)]
        if "csv" in formats:
            p = out / "csv" / f"{name}.csv"
            p.parent.mkdir(exist_ok=True)
            with p.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(cols)
                for r in rows:
                    w.writerow(["" if r.get(c) is None else _csv_val(r[c]) for c in cols])
            written.append(p)
        if "jsonl" in formats:
            p = out / "jsonl" / f"{name}.jsonl"
            p.parent.mkdir(exist_ok=True)
            with p.open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps({c: r.get(c) for c in cols}, ensure_ascii=False) + "\n")
            written.append(p)
        if "parquet" in formats:
            written.append(_parquet(name, rows, out / "parquet" / f"{name}.parquet"))
    return written


def _csv_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def _parquet(name: str, rows: list[dict], path: Path) -> Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as e:  # pragma: no cover - optional dependency
        raise SystemExit("Parquet output needs pyarrow: pip install 'turath-catalog[parquet]'") from e
    types = {"string": pa.string(), "integer": pa.int32(), "boolean": pa.bool_()}
    cols = columns(name)
    fields = []
    for c in cols:
        t = pa.int64() if c.name == "size_bytes" else types[c.type]
        fields.append(pa.field(c.name, t, nullable=not c.required, metadata={"description": c.doc}))
    schema = pa.schema(fields, metadata={"description": TABLES[name]["doc"], "license": "CC-BY-4.0"})
    table = pa.Table.from_pylist([{c.name: r.get(c.name) for c in cols} for r in rows], schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd")
    return path


def read_tables(root: Path) -> dict[str, list[dict]]:
    """Read a release (or the sample) back: JSON Lines when present, else CSV with typed columns."""
    root = Path(root)
    out = {}
    for name in TABLES:
        jl, cs = root / "jsonl" / f"{name}.jsonl", root / "csv" / f"{name}.csv"
        if jl.exists():
            out[name] = [json.loads(ln) for ln in jl.open(encoding="utf-8") if ln.strip()]
        elif cs.exists():
            out[name] = read_csv(cs, name)
        else:
            out[name] = []
    return out


def read_csv(path: Path, name: str) -> list[dict]:
    types = {c.name: c.type for c in columns(name)}
    rows = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            row = {}
            for k, v in r.items():
                t = types.get(k, "string")
                if v == "":
                    row[k] = None
                elif t == "integer":
                    row[k] = int(v)
                elif t == "boolean":
                    row[k] = v == "true"
                else:
                    row[k] = v
            rows.append(row)
    return rows


POCKETSHELF_COLS = [
    "title",
    "author",
    "author_death",
    "author_calendar",
    "category",
    "path",
    "volumes",
    "size",
    "pages",
    "lang",
    "work",
    "edition",
    "editor",
    "publisher",
    "place",
    "year",
    "tags",
    "ext_ids",
    "century",
    "alt_titles",
    "note",
]
KIND_TAGS = {"printed": "", "lithograph": "طبعة حجرية", "manuscript": "مخطوط", "thesis": "رسالة جامعية", "offprint": "مستل"}


def pocketshelf_rows(tables: dict) -> list[dict]:
    """One row per edition in pocketshelf's catalog input format (docs/catalog-schema.md of pocketshelf)."""
    works = {w["work_id"]: w for w in tables["works"]}
    authors = {a["author_id"]: a for a in tables["authors"]}
    files: dict[str, list] = {}
    for f in tables["edition_files"]:
        files.setdefault(f["edition_id"], []).append(f)
    out = []
    for e in sorted(tables["editions"], key=lambda e: (works[e["work_id"]]["category_ar"], e["label_ar"])):
        w = works[e["work_id"]]
        a = authors.get(w["author_id"] or "", {})
        ed = []
        if e["edition_number"]:
            ed.append(f"ط {e['edition_number']}")
        if e["edition_statement_ar"]:
            ed.append(e["edition_statement_ar"])
        tags = [t for t in (KIND_TAGS[e["kind"]], "تحقيق" if e["editors_ar"] else "") if t]
        ext = ";".join(x for x in (w["ext_ids"], e["ext_ids"]) if x)
        if w["openiti_uri"]:
            ext += (";" if ext else "") + f"openiti:{w['openiti_uri']}"
        if w["wikidata_qid"]:
            ext += (";" if ext else "") + f"wikidata:{w['wikidata_qid']}"
        vols = files.get(e["edition_id"], [])
        out.append(
            {
                "title": e["title_clean_ar"],
                "author": w["author_name_ar"] or "",
                "author_death": a.get("death_ah") or "",
                "author_calendar": "ah",
                "category": w["category_ar"],
                "path": "",
                "volumes": ";".join(f"{v['volume_label']}||{v['size_bytes']}" for v in vols) if len(vols) > 1 else "",
                "size": e["size_bytes"],
                "pages": e["pages"] or "",
                "lang": "ar",
                "work": e["work_id"],
                "edition": " ".join(ed),
                "editor": e["editors_ar"] or "",
                "publisher": e["publisher_ar"] or "",
                "place": e["place_ar"] or "",
                "year": e["year_ce"] or "",
                "tags": ";".join(tags),
                "ext_ids": ext,
                "century": a.get("century_ah") or "",
                "alt_titles": e["alt_titles_ar"] or "",
                "note": e["title_note_ar"] or "",
            }
        )
    return out


def write_pocketshelf(tables: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=POCKETSHELF_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(pocketshelf_rows(tables))
    return path


def write_schemas(dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for name in TABLES:
        p = dest / f"{name}.schema.json"
        p.write_text(json.dumps(json_schema(name), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out.append(p)
    return out


def data_dictionary() -> str:
    lines = [
        "# Data dictionary",
        "",
        "Generated from `src/turath_catalog/model.py` (`turath-catalog schema`); do not edit by hand.",
        "Every table ships as CSV (UTF-8, header row, empty cell = null), JSON Lines and Parquet (zstd),",
        "with the same columns in the same order. JSON Schemas for one row of each table are in `schema/`.",
        "",
        "Conventions: ids are stable hashes (see each `*_id`); multi-valued text cells are `;`-separated;",
        "`ext_ids` cells are `scheme:id` pairs; years are integers; `confidence` is `high`, `medium` or `low`.",
        "",
    ]
    for name, t in TABLES.items():
        lines += [f"## `{name}`", "", t["doc"], "", "| column | type | required | description |", "|---|---|---|---|"]
        for c in t["cols"]:
            extra = []
            if c.enum:
                extra.append("one of " + ", ".join(f"`{x}`" for x in c.enum))
            if c.minimum is not None or c.maximum is not None:
                extra.append(f"range {c.minimum if c.minimum is not None else ''}..{c.maximum if c.maximum is not None else ''}")
            if c.example:
                extra.append(f"e.g. `{c.example}`")
            doc = c.doc + (" (" + "; ".join(extra) + ")" if extra else "")
            lines.append(f"| `{c.name}` | {c.type} | {'yes' if c.required else ''} | {doc.replace('|', '/')} |")
        lines.append("")
    return "\n".join(lines)
