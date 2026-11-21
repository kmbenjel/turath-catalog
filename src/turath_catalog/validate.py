"""Checks a built dataset: schema, unique ids, references, dates, and that nothing private leaked."""

from __future__ import annotations

import json
import re
from collections import Counter

from .hijri import ah_to_ce_range, century_ah
from .model import FIELD_SOURCES, TABLES, columns

EXT_SCHEMES = {"shamela", "shamela_author", "waqfeya", "openiti", "wikidata"}
LEAK_PATTERNS = {
    "file path": re.compile(r"(/home/|/sdcard|/storage/|[A-Za-z]:\\\\|\\.pdf\b|\\.epub\b|\bBooks/|\.\./)", re.I),
    "e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "IP address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "URL": re.compile(r"https?://|www\.", re.I),
    "phone number": re.compile(r"\+\d[\d ]{8,}"),
    "credential word": re.compile(r"password|passwd|token|secret|ftp\.env|phone_ssh", re.I),
    "workspace word": re.compile(r"\bowner\b|المالك:|plan-\d|review-comments|changes\.tsv|HANDOFF|WORKLOG", re.I),
}
# Text fields that may legitimately hold a slash: none of ours do once paths are gone, except shelfmarks
SLASH_OK = {"shelfmark"}


def check(tables: dict, personal_names: tuple[str, ...] = ()) -> list[str]:
    errs: list[str] = []
    errs += _schema(tables)
    errs += _keys(tables)
    errs += _references(tables)
    errs += _dates(tables)
    errs += _titles(tables)
    errs += _leaks(tables, personal_names)
    return errs


def _schema(tables: dict) -> list[str]:
    errs = []
    for name in TABLES:
        rows = tables.get(name, [])
        # a column that no row carries was added after this release was built: an older release stays valid
        cols = {c.name: c for c in columns(name) if not rows or any(c.name in r for r in rows)}
        for i, r in enumerate(rows):
            extra = set(r) - set(cols)
            if extra:
                errs.append(f"{name}[{i}]: unknown columns {sorted(extra)}")
            for c in cols.values():
                v = r.get(c.name)
                if v is None or v == "":
                    if c.required:
                        errs.append(f"{name}[{i}].{c.name}: required value missing")
                    continue
                ok = {
                    "string": isinstance(v, str),
                    "integer": isinstance(v, int) and not isinstance(v, bool),
                    "boolean": isinstance(v, bool),
                }[c.type]
                if not ok:
                    errs.append(f"{name}[{i}].{c.name}: {v!r} is not {c.type}")
                    continue
                if c.enum and v not in c.enum:
                    errs.append(f"{name}[{i}].{c.name}: {v!r} not in {list(c.enum)}")
                if c.pattern and not re.search(c.pattern, v):
                    errs.append(f"{name}[{i}].{c.name}: {v!r} does not match {c.pattern}")
                if c.minimum is not None and v < c.minimum or c.maximum is not None and v > c.maximum:
                    errs.append(f"{name}[{i}].{c.name}: {v} outside {c.minimum}..{c.maximum}")
                if c.name == "ext_ids":
                    bad = {x.split(":", 1)[0] for x in v.split(";")} - EXT_SCHEMES
                    if bad:
                        errs.append(f"{name}[{i}].ext_ids: unknown schemes {sorted(bad)}")
                if c.name == "field_sources":
                    try:
                        fs = json.loads(v)
                        known = {c.name for c in columns(name)}
                        if set(fs) - known or set(fs.values()) - set(FIELD_SOURCES):
                            errs.append(f"{name}[{i}].field_sources: unknown keys or sources {fs}")
                    except json.JSONDecodeError:
                        errs.append(f"{name}[{i}].field_sources: not JSON")
    return errs


def _keys(tables: dict) -> list[str]:
    errs = []
    for name, t in TABLES.items():
        rows = tables.get(name, [])
        keys = {
            "edition_files": ("edition_id", "seq"),
            "edition_editors": ("edition_id", "person_id", "role"),
        }.get(name, (t["key"],) if t["key"] else None)
        if not keys:
            continue
        dup = [k for k, n in Counter(tuple(r.get(k) for k in keys) for r in rows).items() if n > 1]
        if dup:
            errs.append(f"{name}: {len(dup)} duplicate keys {keys}, e.g. {dup[0]}")
    return errs


def _references(tables: dict) -> list[str]:
    errs = []
    ids = {n: {r[TABLES[n]["key"]] for r in tables.get(n, [])} for n in ("works", "editions", "authors", "editors")}
    refs = [
        ("editions", "work_id", "works"),
        ("works", "author_id", "authors"),
        ("edition_editors", "edition_id", "editions"),
        ("edition_editors", "person_id", "editors"),
        ("manuscripts", "edition_id", "editions"),
        ("manuscripts", "work_id", "works"),
        ("manuscripts", "author_id", "authors"),
        ("manuscripts", "printed_edition_id", "editions"),
        ("edition_files", "edition_id", "editions"),
        ("authors", "canonical_author_id", "authors"),
    ]
    for table, col, target in refs:
        bad = [r[col] for r in tables.get(table, []) if r.get(col) and r[col] not in ids[target]]
        if bad:
            errs.append(f"{table}.{col}: {len(bad)} ids missing from {target}, e.g. {bad[0]}")
    canonical = {a["author_id"]: a.get("canonical_author_id") for a in tables.get("authors", [])}
    for aid, cid in canonical.items():
        if cid and canonical.get(cid, cid) != cid:
            errs.append(f"authors: {aid} points to {cid}, which is not its own canonical row")
    per_work = Counter(e["work_id"] for e in tables.get("editions", []))
    for w in tables.get("works", []):
        if per_work[w["work_id"]] == 0:
            errs.append(f"works: {w['work_id']} has no edition")
        elif per_work[w["work_id"]] != w["n_editions"]:
            errs.append(f"works: {w['work_id']} n_editions {w['n_editions']} != {per_work[w['work_id']]}")
    per_author = Counter(w["author_id"] for w in tables.get("works", []) if w.get("author_id"))
    for a in tables.get("authors", []):
        if per_author[a["author_id"]] != a["n_works"]:
            errs.append(f"authors: {a['author_id']} n_works {a['n_works']} != {per_author[a['author_id']]}")
    files = Counter(f["edition_id"] for f in tables.get("edition_files", []))
    for e in tables.get("editions", []):
        if files and files[e["edition_id"]] != e["n_files"]:
            errs.append(f"editions: {e['edition_id']} n_files {e['n_files']} != {files[e['edition_id']]} file rows")
    sizes = Counter()
    for f in tables.get("edition_files", []):
        sizes[f["edition_id"]] += f["size_bytes"]
    for e in tables.get("editions", []):
        if sizes and sizes[e["edition_id"]] != e["size_bytes"]:
            errs.append(f"editions: {e['edition_id']} size_bytes != sum of its files")
    return errs


def _dates(tables: dict) -> list[str]:
    errs = []
    deaths = {}
    for a in tables.get("authors", []):
        d = a.get("death_ah")
        if not isinstance(d, int) or isinstance(d, bool):
            if a.get("death_ce_from") or a.get("death_ce_to") or a.get("death_source"):
                errs.append(f"authors: {a['author_id']} has CE years or a source but no death_ah")
            continue
        deaths[a["author_id"]] = d
        if not 1 <= d <= 1450:
            continue  # reported by the schema check
        if (a.get("death_ce_from"), a.get("death_ce_to")) != ah_to_ce_range(d):
            errs.append(f"authors: {a['author_id']} death_ce {a.get('death_ce_from')}-{a.get('death_ce_to')} != {ah_to_ce_range(d)}")
        if a.get("century_ah") != century_ah(d):
            errs.append(f"authors: {a['author_id']} century {a.get('century_ah')} != century of {d}")
        if not a.get("death_source") or not a.get("death_confidence"):
            errs.append(f"authors: {a['author_id']} death year without source or confidence")
    works = {w["work_id"]: w for w in tables.get("works", [])}
    for e in tables.get("editions", []):
        h, g = e.get("year_ah"), e.get("year_ce")
        h = h if isinstance(h, int) and h > 0 else None
        g = g if isinstance(g, int) else None
        if h and g:
            lo, hi = ah_to_ce_range(h)
            if not lo - 1 <= g <= hi + 1:
                errs.append(f"editions: {e['edition_id']} year_ah {h} and year_ce {g} disagree")
        d = deaths.get(works.get(e["work_id"], {}).get("author_id"))
        if h and d and d < 1200 and h < d and e["kind"] != "manuscript":
            errs.append(f"editions: {e['edition_id']} printed {h} AH before its author died ({d} AH)")
    return errs


def _titles(tables: dict) -> list[str]:
    """A clean title is the title alone: no second title, no bracket; and it is not listed as its own other title."""
    errs = []
    for name in ("works", "editions"):
        for r in tables.get(name, []):
            clean = r.get("title_clean_ar")
            if not clean:
                continue  # an older release, or reported by the schema check
            key = r[TABLES[name]["key"]]
            if re.search(r"[=()\[\]]", clean):
                errs.append(f"{name}: {key} title_clean_ar still carries «=» or a bracket: {clean[:80]!r}")
            if clean in (r.get("alt_titles_ar") or "").split(";"):
                errs.append(f"{name}: {key} lists its own title among alt_titles_ar")
    return errs


def _leaks(tables: dict, personal_names: tuple[str, ...]) -> list[str]:
    errs = []
    names = [n.lower() for n in personal_names if n]
    for name in TABLES:
        for i, r in enumerate(tables.get(name, [])):
            for k, v in r.items():
                if not isinstance(v, str):
                    continue
                for what, pat in LEAK_PATTERNS.items():
                    if pat.search(v):
                        errs.append(f"{name}[{i}].{k}: looks like a {what}: {v[:80]!r}")
                if "/" in v and k not in SLASH_OK and k != "field_sources":
                    errs.append(f"{name}[{i}].{k}: contains '/', a path? {v[:80]!r}")
                low = v.lower()
                for n in names:
                    if n in low:
                        errs.append(f"{name}[{i}].{k}: contains a listed personal name")
    return errs
