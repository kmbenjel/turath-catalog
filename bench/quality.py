#!/usr/bin/env python3
"""Data-quality audit of a release: title marks, duplicates, death years, id recipes and, against an earlier
release, which ids and values changed. Every number the docs give about data quality comes from here.

    python bench/quality.py releases/turath-catalog-0.2.0 --previous releases/turath-catalog-0.1.0 \
        --out bench/quality.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from turath_catalog import load
from turath_catalog.build import h10, work_id_for
from turath_catalog.model import TABLES
from turath_catalog.textnorm import author_key, title_key

KEYS = {"edition_files": ("edition_id", "seq"), "edition_editors": ("edition_id", "person_id", "role")}


def key_of(table: str, row: dict):
    k = KEYS.get(table) or (TABLES[table]["key"],)
    return tuple(row[c] for c in k)


def titles(t: dict) -> dict:
    eds, works = t["editions"], t["works"]
    marked = re.compile(r"[=()\[\]]")
    return {
        "editions_title_differs_from_clean": sum(1 for e in eds if e["title_ar"] != e["title_clean_ar"]),
        "editions_with_alt_titles": sum(1 for e in eds if e["alt_titles_ar"]),
        "editions_with_title_note": sum(1 for e in eds if e["title_note_ar"]),
        "edition_marks_kept_as_note": sum(1 for e in eds if re.search(r"(^|;)[طت] ", e["title_note_ar"] or "")),
        "works_title_differs_from_clean": sum(1 for w in works if w["title_ar"] != w["title_clean_ar"]),
        "works_with_alt_titles": sum(1 for w in works if w["alt_titles_ar"]),
        "clean_titles_with_equals_or_bracket": sum(1 for r in eds + works if marked.search(r["title_clean_ar"])),
    }


def duplicates(t: dict) -> dict:
    authors, works, eds = t["authors"], t["works"], t["editions"]
    person = {a["author_id"]: a["canonical_author_id"] for a in authors}
    by_ext = Counter(a["ext_ids"] for a in authors if a["ext_ids"])
    by_work = defaultdict(list)
    for w in works:
        if w["author_id"]:
            by_work[(title_key(w["title_ar"].split(" = ")[0]), person[w["author_id"]])].append(w["work_id"])
    same_ed = Counter(
        (e["work_id"], e["editors_ar"], e["publisher_ar"], e["year_ah"], e["year_ce"], e["edition_number"], e["kind"])
        for e in eds
        if e["editors_ar"] or e["publisher_ar"]
    )
    return {
        "author_rows": len(authors),
        "people_by_canonical_author_id": len(set(person.values())),
        "author_rows_folded_into_another": sum(1 for a, c in person.items() if a != c),
        "catalog_author_ids_on_several_rows": sum(1 for n in by_ext.values() if n > 1),
        "of_which_left_apart": sum(
            1 for x, n in by_ext.items() if n > 1 and len({a["canonical_author_id"] for a in authors if a["ext_ids"] == x}) > 1
        ),
        "work_groups_same_title_key_same_person": sum(1 for v in by_work.values() if len(v) > 1),
        "edition_groups_same_work_editors_publisher_year": sum(1 for n in same_ed.values() if n > 1),
    }


def deaths(t: dict) -> dict:
    authors = {a["author_id"]: a for a in t["authors"]}
    works = {w["work_id"]: w for w in t["works"]}
    groups = defaultdict(set)
    for a in authors.values():
        if a["death_ah"]:
            groups[a["canonical_author_id"]].add(a["death_ah"])
    early = 0
    for e in t["editions"]:
        a = authors.get(works[e["work_id"]]["author_id"] or "")
        if a and a["death_ah"] and e["year_ah"] and e["kind"] != "manuscript" and e["year_ah"] < a["death_ah"] - 80:
            early += 1
    names = defaultdict(set)
    for a in authors.values():
        names[author_key(a["name_ar"])].add(a["author_id"])
    return {
        "authors_with_death_year": sum(1 for a in authors.values() if a["death_ah"]),
        "by_confidence": dict(sorted(Counter(a["death_confidence"] for a in authors.values() if a["death_ah"]).items())),
        "by_source": dict(sorted(Counter(a["death_source"] for a in authors.values() if a["death_ah"]).items())),
        "people_with_two_death_years": sum(1 for v in groups.values() if len(v) > 1),
        "openiti_uri_year_differs": sum(
            1 for a in authors.values() if a["openiti_author_uri"] and a["death_ah"] and int(a["openiti_author_uri"][:4]) != a["death_ah"]
        ),
        "editions_printed_80_years_before_author_death": early,
        "name_forms_on_several_rows": sum(1 for v in names.values() if len(v) > 1),
    }


def recipes(t: dict) -> dict:
    works, authors = t["works"], t["authors"]
    w_ok = sum(1 for w in works if work_id_for(w["title_ar"], w["author_name_ar"] or "") == w["work_id"])
    a_plain = sum(1 for a in authors if h10("a", author_key(a["name_ar"])) == a["author_id"])
    return {
        "work_ids_equal_to_sha1_of_title_key_author_key": w_ok,
        "work_ids_disambiguated": len(works) - w_ok,
        "author_ids_equal_to_sha1_of_author_key": a_plain,
        "author_ids_with_death_year_or_century_in_the_hash": len(authors) - a_plain,
    }


def against(t: dict, old: dict) -> dict:
    out = {}
    for name in TABLES:
        new_rows = {key_of(name, r): r for r in t[name]}
        old_rows = {key_of(name, r): r for r in old[name]}
        kept = new_rows.keys() & old_rows.keys()
        changed = Counter()
        for k in kept:
            for col, v in old_rows[k].items():
                if new_rows[k].get(col) != v:
                    changed[col] += 1
        out[name] = {
            "rows_before": len(old_rows),
            "rows_now": len(new_rows),
            "ids_kept": len(kept),
            "ids_gone": len(old_rows.keys() - new_rows.keys()),
            "ids_new": len(new_rows.keys() - old_rows.keys()),
            "columns_added": [c for c in (t[name][0] if t[name] else {}) if old[name] and c not in old[name][0]],
            "values_changed_in_kept_rows": dict(sorted(changed.items())),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("release", type=Path)
    ap.add_argument("--previous", type=Path, help="an earlier release to compare ids and values with")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    t = load(a.release)
    res = {"release": a.release.name, "titles": titles(t), "duplicates": duplicates(t), "death_years": deaths(t), "ids": recipes(t)}
    if a.previous:
        res["against"] = {"release": a.previous.name, "tables": against(t, load(a.previous))}
    text = json.dumps(res, ensure_ascii=False, indent=2) + "\n"
    print(text, end="")
    if a.out:
        a.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
