"""Adapter for a user's own catalog: one CSV row per edition, so any library can be normalised into the
same tables (works, editions, authors, editors…) with the same stable ids.

Columns (only `title` is required; unknown columns are ignored):
    title, author, author_death_ah, category, editors (";"-separated, optionally "role:name"),
    publisher, place, year_ah, year_ce, edition_number, volumes, pages, kind, work, sizes (";"-separated bytes)
Every value is recorded with source `user`.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from ..hijri import century_ah
from ..model import CATEGORY_EN, KINDS, ROLE_AR, ROLES
from ..record import EditionRecord, Editor, Volume
from ..textnorm import arabic_digits_to_ascii, nfc


def _int(v: str | None) -> int | None:
    m = re.search(r"\d+", arabic_digits_to_ascii(v or ""))
    return int(m.group()) if m else None


def read_user_csv(path: str | Path) -> tuple[list[EditionRecord], dict]:
    path = Path(path)
    recs, skipped = [], 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "title" not in reader.fieldnames:
            raise SystemExit(f"{path}: needs a header row with at least a 'title' column")
        for n, row in enumerate(reader, 2):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("title"):
                skipped += 1
                continue
            cat = row.get("category") or "كتب عامة"
            if cat not in CATEGORY_EN:
                cat = "كتب عامة"
            r = EditionRecord(
                key=f"{path.name}:{n}:{nfc(row['title'])}",
                title=row["title"],
                category_ar=cat,
                author=row.get("author", ""),
                work_group=row.get("work", ""),
                title_source="user",
            )
            r.label = " - ".join(x for x in (r.title, r.author, row.get("publisher", "")) if x)
            for part in filter(None, (p.strip() for p in row.get("editors", "").split(";"))):
                role, _, name = part.partition(":") if ":" in part else ("editor", "", part)
                role = role if role in ROLES else "editor"
                r.editors.append(Editor(name=name.strip(), role=role, role_ar=ROLE_AR[role]))
            r.publisher, r.place = row.get("publisher", ""), row.get("place", "")
            r.year_ah, r.year_ce = _int(row.get("year_ah")), _int(row.get("year_ce"))
            r.edition_number, r.volumes, r.pages = _int(row.get("edition_number")), _int(row.get("volumes")), _int(row.get("pages"))
            r.kind = row.get("kind") if row.get("kind") in KINDS else "printed"
            d = _int(row.get("author_death_ah"))
            if d and 1 <= d <= 1450:
                r.death_ah, r.death_source, r.century_ah = d, "user", century_ah(d)
            sizes = [_int(s) for s in row.get("sizes", "").split(";") if _int(s)]
            r.files = [Volume(label=f"{i:02d}", size_bytes=s) for i, s in enumerate(sizes, 1)] or [Volume("01", 1)]
            r.title_page_read = row.get("verified", "").lower() in ("1", "true", "yes")
            for col, fld in (
                ("editors", "editors"),
                ("publisher", "publisher"),
                ("place", "place"),
                ("year_ah", "year_ah"),
                ("year_ce", "year_ce"),
                ("edition_number", "edition_number"),
                ("volumes", "volumes"),
                ("pages", "pages"),
            ):
                if row.get(col):
                    r.sources[fld] = "user"
            recs.append(r)
    return recs, {"excluded_rows": {"no title": skipped} if skipped else {}, "dropped_values": {}}
