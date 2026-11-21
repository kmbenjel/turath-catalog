"""turath-catalog command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__

EPILOG = """examples:
  turath-catalog info sample                              what is in a release (here: the bundled sample)
  turath-catalog validate releases/turath-catalog-0.2.0   check ids, references, dates, leaks
  turath-catalog build --csv my-library.csv --out out/     normalise your own catalog into the same tables
  turath-catalog build --warraq ~/library --out releases/turath-catalog-0.2.0
  turath-catalog charts releases/turath-catalog-0.2.0 --out docs/media
  turath-catalog schema --out schema --dictionary docs/data-dictionary.md
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="turath-catalog",
        description="Build, check and explore an open bibliographic dataset of classical Arabic works and editions.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--version", action="version", version=f"turath-catalog {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="inputs -> normalised tables (CSV, JSON Lines, Parquet) + pocketshelf.csv")
    src = b.add_mutually_exclusive_group(required=True)
    src.add_argument("--warraq", type=Path, metavar="DIR", help="a Warraq library workspace (data/catalog.json …)")
    src.add_argument("--csv", type=Path, metavar="FILE", help="your own catalog, one row per edition (see docs)")
    b.add_argument("--out", type=Path, required=True, help="release folder to write")
    b.add_argument("--cache", type=Path, default=Path("cache"), help="downloads of OpenITI / Wikidata (default ./cache)")
    b.add_argument("--offline", action="store_true", help="no downloads: link only from what is already cached")
    b.add_argument("--formats", default="csv,jsonl,parquet", help="comma list of csv,jsonl,parquet")
    b.add_argument(
        "--include", action="append", default=[], metavar="SRC[:NAME]", help="copy a file into the release (dataset card, licence)"
    )

    v = sub.add_parser("validate", help="check a release: schema, unique ids, references, dates, leaks")
    v.add_argument("path", type=Path)
    v.add_argument("--personal-name", action="append", default=[], help="a name that must not appear (repeatable)")

    i = sub.add_parser("info", help="row counts and coverage of a release")
    i.add_argument("path", type=Path)

    c = sub.add_parser("charts", help="draw the README charts from a release")
    c.add_argument("path", type=Path)
    c.add_argument("--out", type=Path, default=Path("docs/media"))

    s = sub.add_parser("schema", help="write JSON Schemas and the data dictionary from the model")
    s.add_argument("--out", type=Path, default=Path("schema"))
    s.add_argument("--dictionary", type=Path, default=Path("docs/data-dictionary.md"))

    sm = sub.add_parser("sample", help="cut a small, self-consistent sample out of a release")
    sm.add_argument("path", type=Path)
    sm.add_argument("--out", type=Path, default=Path("src/turath_catalog/sample"))
    sm.add_argument("--works", type=int, default=150)

    cmp_ = sub.add_parser("compare", help="coverage of the release in OpenITI, Wikidata and Shamela (cached data)")
    cmp_.add_argument("path", type=Path)
    cmp_.add_argument("--cache", type=Path, default=Path("cache"))
    cmp_.add_argument("--out", type=Path, help="write the numbers as JSON")

    a = ap.parse_args(argv)
    if a.cmd == "build":
        from .pipeline import build_release

        path = a.warraq or a.csv
        inc = tuple((Path(x.split(":", 1)[0]), x.split(":", 1)[1] if ":" in x else Path(x).name) for x in a.include)
        rep = build_release("warraq" if a.warraq else "csv", path, a.out, a.cache, a.offline, tuple(a.formats.split(",")), inc)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    if a.cmd in ("validate", "info", "charts", "sample", "compare"):
        from . import load

        if not (a.path.exists() or str(a.path) == "sample"):
            print(f"turath-catalog: {a.path} does not exist", file=sys.stderr)
            return 2
        tables = load(a.path)
    if a.cmd == "validate":
        from .validate import check

        errs = check(tables, tuple(a.personal_name))
        for e in errs[:200]:
            print(e)
        n = sum(len(v) for v in tables.values())
        print(f"{'FAIL' if errs else 'OK'}: {n:,} rows in {len(tables)} tables, {len(errs)} problems")
        return 1 if errs else 0
    if a.cmd == "info":
        from .stats import summary

        print(summary(tables))
        return 0
    if a.cmd == "charts":
        from .charts import draw_all

        for p in draw_all(tables, a.out):
            print(p)
        return 0
    if a.cmd == "schema":
        from .export import data_dictionary, write_schemas

        for p in write_schemas(a.out):
            print(p)
        a.dictionary.parent.mkdir(parents=True, exist_ok=True)
        a.dictionary.write_text(data_dictionary() + "\n", encoding="utf-8")
        print(a.dictionary)
        return 0
    if a.cmd == "sample":
        from .export import write_tables
        from .stats import cut_sample

        write_tables(cut_sample(tables, a.works), a.out, ("csv",))
        print(a.out)
        return 0
    if a.cmd == "compare":
        from .compare import coverage

        res = coverage(tables, a.cache)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if a.out:
            a.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
