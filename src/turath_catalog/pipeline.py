"""inputs → records → tables → links → files: the whole build, as one function the CLI calls."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from . import __version__, link
from .build import build_tables
from .export import write_pocketshelf, write_schemas, write_tables
from .validate import check


def load_records(source: str, path: Path):
    if source == "warraq":
        from .sources.warraq import WarraqWorkspace

        ws = WarraqWorkspace(path)
        return ws.records(), ws.report.as_dict()
    if source == "csv":
        from .sources.usercsv import read_user_csv

        return read_user_csv(path)
    raise SystemExit(f"unknown source {source!r} (warraq | csv)")


def build_release(
    source: str,
    path: Path,
    out: Path,
    cache: Path,
    offline: bool = False,
    formats=("csv", "jsonl", "parquet"),
    include: tuple[tuple[Path, str], ...] = (),
) -> dict:
    """Build, link, validate and write a release. `include` copies extra files (dataset card, licence) in."""
    recs, adapter_report = load_records(source, path)
    tables = build_tables(recs)
    links = {}
    meta = link.openiti_metadata(cache, offline=offline)
    if meta:
        links["openiti"] = link.link_openiti(tables, meta)
    wd = {n: link.wikidata(cache, n, offline=offline) for n in link.QUERIES}
    if any(wd.values()):
        links["wikidata"] = link.link_wikidata(tables, wd["shamela_author"], wd["shamela_book"], wd["openiti_author"])
    errors = check(tables)
    if errors:
        raise SystemExit("validation failed:\n  " + "\n  ".join(errors[:40]) + (f"\n  … {len(errors)} errors" if len(errors) > 40 else ""))
    write_tables(tables, out, formats)
    write_pocketshelf(tables, out / "pocketshelf.csv")
    write_schemas(out / "schema")
    for src, name in include:
        (out / name).write_bytes(Path(src).read_bytes())
    report = {
        "version": __version__,
        "source": source,
        "rows": {k: len(v) for k, v in tables.items()},
        "adapter": adapter_report,
        "links": links,
        "link_sources": {"openiti": link.OPENITI_RELEASE, "wikidata": "query.wikidata.org SPARQL, cached on first build"},
        "confidence": {
            "editions": dict(Counter(e["confidence"] for e in tables["editions"])),
            "works": dict(Counter(w["confidence"] for w in tables["works"])),
        },
    }
    (out / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sums = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return report
