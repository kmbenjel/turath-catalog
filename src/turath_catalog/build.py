"""Edition records → normalised tables (works, editions, authors, editors, edition_editors, manuscripts,
edition_files, categories). Deterministic: the same records give the same tables, ids and order."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass

from .hijri import ah_to_ce_range, century_ah
from .model import CATEGORY_EN, ROLE_AR
from .record import EditionRecord
from .textnorm import WAW_NAMES, author_key, nfc, norm, title_key
from .titles import mark_agrees, split_title

Tables = dict[str, list[dict]]
_RANK = {"high": 0, "medium": 1, "low": 2}


def h10(prefix: str, text: str) -> str:
    return f"{prefix}_{hashlib.sha1(nfc(text).encode('utf-8')).hexdigest()[:10]}"


def work_id_for(title: str, author: str) -> str:
    """The shared recipe (turath-match uses it for its cluster ids)."""
    return h10("w", f"{title_key(title)}|{author_key(author)}")


_ROLE_MARK = {"editor": "ت", "translator": "ترجمة"}


def main_title(title: str) -> str:
    """«A = B» → «A»: the part of a title that names the work (and that its id hashes)."""
    return title.split(" = ")[0].strip()


@dataclass(frozen=True)
class ResolvedTitle:
    """A record's title, split (`titles.split_title`) and checked against the record's own edition fields."""

    clean: str
    alts: tuple[str, ...]
    notes: tuple[str, ...]
    publisher: str  # the record's publisher, or the title's «ط X» mark when the record names none
    publisher_from_mark: bool


def resolve_title(r: EditionRecord) -> ResolvedTitle:
    """An edition mark written in the title («ط. الخانجي», «ت - الميمني») says nothing new when the row already
    names that publisher or editor: it is dropped from the clean title. When the row names no publisher, the
    mark gives it. A mark that disagrees with the row is kept as a remark, so no source is silently overruled."""
    p = split_title(r.title, r.author)
    notes = list(p.notes)
    publisher, from_mark = r.publisher, False
    for m in p.publisher_marks:
        if mark_agrees(m, f"{r.publisher} {r.place}"):
            continue
        if not publisher and not r.place and len(p.publisher_marks) == 1:
            publisher, from_mark = m, True
        else:
            notes.append(f"ط {m}")
    for m in p.editor_marks:
        if not any(mark_agrees(m, e.name) for e in r.editors):
            notes.append(f"ت {m}")
    return ResolvedTitle(p.clean, p.alts, tuple(notes), publisher, from_mark)


def compose_label(r: EditionRecord) -> str:
    """The edition's citation form, composed from its own fields only, so it can never disagree with them:
    «title - author - ت editor وeditor - publisher place» (a role other than editing is written out: «شرح فلان»).
    The title is the clean one: other titles, remarks and edition marks have their own columns."""
    rt = resolve_title(r)
    parts = [rt.clean]
    if r.author:
        parts.append(r.author)
    by_role: dict[str, list[str]] = {}
    for e in r.editors:
        by_role.setdefault(e.role, []).append(e.name)
    for role, names in by_role.items():
        mark = _ROLE_MARK.get(role) or ROLE_AR.get(role, "ت")
        parts.append(f"{mark} " + " و".join(names))
    imprint = " ".join(x for x in (rt.publisher, r.place.replace(" - ", " ")) if x)
    if imprint:
        parts.append(imprint)
    return " - ".join(p for p in parts if p)


def edition_confidence(r: EditionRecord) -> str:
    if r.title_page_read:
        return "high"
    if {"catalog_record", "shamela_card", "imprint_page", "title_page"} & set(r.sources.values()):
        return "medium"
    return "low"


class _UF:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


def _people(recs: list[EditionRecord]) -> dict[int, str]:
    """record index -> author_id. One name form with two death years is two people; a record with only a
    century (or nothing) joins the single person of that name in that century, if there is exactly one."""
    by_key: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(recs):
        if author_key(r.author):
            by_key[author_key(r.author)].append(i)
    out = {}
    for k, idx in by_key.items():
        deaths = sorted({recs[i].death_ah for i in idx if recs[i].death_ah})
        for i in idx:
            r = recs[i]
            if r.death_ah:
                d = r.death_ah
            else:
                fit = [d for d in deaths if not r.century_ah or century_ah(d) == r.century_ah]
                d = fit[0] if len(fit) == 1 else None
            if len(deaths) <= 1 and (d is None or d in deaths):
                out[i] = h10("a", k)  # the usual case: one person of that name
            else:
                out[i] = h10("a", f"{k}|{d}" if d else f"{k}|c{r.century_ah or ''}")
    return out


def _names_two_people(name: str) -> bool:
    """«الطبراني وابن مردويه»: a later word opens with «و» and is not itself a name («وهبة», «ولي»)."""
    return any(w.startswith("و") and len(w) > 2 and w not in WAW_NAMES for w in name.split()[1:])


def _canonical_authors(rows: dict[str, dict]) -> None:
    """Rows that one catalog identifier shows to be one person («ابن الجوزي», «أبو الفرج ابن الجوزي») point to a
    single row, the dated one with the most works. Decided by identifier and death year, never by name alone."""
    by_ext: dict[str, list[dict]] = defaultdict(list)
    for a in rows.values():
        if a["ext_ids"] and not _names_two_people(a["name_ar"]):
            by_ext[a["ext_ids"]].append(a)
    for group in by_ext.values():
        if len(group) < 2 or len({a["death_ah"] for a in group if a["death_ah"]}) > 1:
            continue
        head = min(group, key=lambda a: (a["death_ah"] is None, -a["n_works"], len(a["name_ar"]), a["author_id"]))
        for a in group:
            a["canonical_author_id"] = head["author_id"]


def build_tables(recs: list[EditionRecord]) -> Tables:
    recs = sorted(recs, key=lambda r: nfc(r.key))
    n = len(recs)
    person_of = _people(recs)

    # ---- works: union editions of one adapter group, or of the same title key and author ------------------
    uf = _UF(n)
    first: dict[tuple, int] = {}
    for i, r in enumerate(recs):
        keys = [("t", title_key(main_title(r.title)), person_of.get(i, ""))]  # «A = B» is the work «A»
        if r.work_group:
            keys.append(("g", r.work_group))
        for k in keys:
            if k in first:
                uf.union(first[k], i)
            else:
                first[k] = i
    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[uf.find(i)].append(i)

    resolved = [resolve_title(r) for r in recs]
    works, editions, files, ed_eds, manuscripts = [], [], [], [], []
    work_of: dict[int, str] = {}
    edition_of: dict[str, str] = {}
    seen_wid: dict[str, int] = {}
    author_rows: dict[str, dict] = {}
    for root in sorted(clusters):
        idx = clusters[root]
        best = min(idx, key=lambda i: (_RANK[edition_confidence(recs[i])], len(recs[i].title), nfc(recs[i].key)))
        titles = Counter(main_title(recs[i].title) for i in idx)
        title = main_title(recs[best].title)
        if titles.most_common(1)[0][1] > titles[title]:
            title = titles.most_common(1)[0][0]
        author = recs[best].author
        title_clean = split_title(title, author).clean
        alts = sorted({t for i in idx for t in resolved[i].alts} - {title, title_clean})
        wid = work_id_for(title, author)
        if wid in seen_wid:  # same title key and author name, different people or groups: disambiguate
            wid = h10("w", f"{title_key(title)}|{author_key(author)}|{person_of.get(best, '')}|{recs[best].category_ar}")
        seen_wid[wid] = root
        cat = Counter(recs[i].category_ar for i in idx).most_common(1)[0][0]
        sham = Counter()
        for i in idx:
            for sid, conf in recs[i].shamela_work_ids:
                sham[sid] += 2 if conf == "high" else 1
        aid = person_of.get(best)
        works.append(
            {
                "work_id": wid,
                "title_ar": title,
                "alt_titles_ar": ";".join(alts) or None,
                "author_id": aid,
                "author_name_ar": author or None,
                "category_ar": cat,
                "category_en": CATEGORY_EN.get(cat, cat),
                "openiti_uri": None,
                "openiti_confidence": None,
                "wikidata_qid": None,
                "ext_ids": ";".join(f"shamela:{s}" for s, _ in sorted(sham.items(), key=lambda kv: (-kv[1], kv[0]))) or None,
                "n_editions": len(idx),
                "confidence": min((edition_confidence(recs[i]) for i in idx), key=_RANK.get),
                "title_clean_ar": title_clean,
            }
        )
        for i in idx:
            work_of[i] = wid

    # ---- editions, files, editors ----------------------------------------------------------------------------
    people_names: dict[str, Counter] = defaultdict(Counter)  # folded name -> spellings
    raw_people: list[tuple[int, int, str, str, str]] = []
    for i, r in enumerate(recs):
        eid = h10("e", r.key)
        edition_of[r.key] = eid
        ext = [f"waqfeya:{w}" for w in r.waqfeya_ids]
        if r.shamela_edition_id:
            ext.append(f"shamela:{r.shamela_edition_id}")
        sources = {
            {"editors": "editors_ar", "publisher": "publisher_ar", "place": "place_ar", "edition_statement": "edition_statement_ar"}.get(
                k, k
            ): v
            for k, v in sorted(r.sources.items())
            if k != "author_full_name"
        }
        rt = resolved[i]
        if rt.publisher_from_mark:
            sources["publisher_ar"] = r.title_source
        editions.append(
            {
                "edition_id": eid,
                "work_id": work_of[i],
                "title_ar": r.title,
                "label_ar": compose_label(r),
                "kind": r.kind,
                "editors_ar": ";".join(e.name for e in r.editors) or None,
                "publisher_ar": rt.publisher or None,
                "place_ar": r.place or None,
                "year_ah": r.year_ah,
                "year_ce": r.year_ce,
                "edition_number": r.edition_number,
                "edition_statement_ar": r.edition_statement or None,
                "volumes": r.volumes,
                "pages": r.pages,
                "n_files": max(1, len(r.files)),
                "size_bytes": sum(f.size_bytes for f in r.files) or 1,
                "title_page_read": r.title_page_read,
                "wikidata_qid": None,
                "ext_ids": ";".join(ext) or None,
                "field_sources": json.dumps(sources, ensure_ascii=False, sort_keys=True) if sources else None,
                "confidence": edition_confidence(r),
                "title_clean_ar": rt.clean,
                "alt_titles_ar": ";".join(rt.alts) or None,
                "title_note_ar": ";".join(rt.notes) or None,
            }
        )
        for s, f in enumerate(r.files, 1):
            files.append({"edition_id": eid, "seq": s, "volume_label": f.label, "size_bytes": f.size_bytes})
        for s, e in enumerate(r.editors, 1):
            people_names[norm(e.name)][e.name] += 1
            raw_people.append((i, s, norm(e.name), e.role, e.role_ar or ROLE_AR.get(e.role, "تحقيق")))

    # merge shorter name forms into a unique longer one: same first and last word, all words contained
    canon: dict[str, str] = {}
    folded = sorted(people_names, key=lambda k: (-len(k.split()), k))
    for k in folded:
        w = k.split()
        if len(w) >= 2:
            longer = [
                o
                for o in folded
                if len(o.split()) > len(w) and o.split()[0] == w[0] and o.split()[-1] == w[-1] and set(w) <= set(o.split())
            ]
            roots = {canon.get(o, o) for o in longer}
            if len(roots) == 1:
                canon[k] = roots.pop()
                continue
        canon[k] = k
    editors: dict[str, dict] = {}
    seen_pair = set()
    for i, s, k, role, role_ar in raw_people:
        root = canon[k]
        pid = h10("p", root)
        row = editors.setdefault(
            pid, {"person_id": pid, "name_ar": people_names[root].most_common(1)[0][0], "_variants": set(), "_eds": set()}
        )
        if k != root:
            row["_variants"].add(people_names[k].most_common(1)[0][0])
        eid = editions[i]["edition_id"]
        row["_eds"].add(eid)
        if (eid, pid, role) in seen_pair:
            continue
        seen_pair.add((eid, pid, role))
        ed_eds.append({"edition_id": eid, "person_id": pid, "role": role, "role_ar": role_ar, "seq": s})
    editor_rows = [
        {
            "person_id": r["person_id"],
            "name_ar": r["name_ar"],
            "name_variants_ar": ";".join(sorted(r["_variants"])) or None,
            "n_editions": len(r["_eds"]),
        }
        for r in sorted(editors.values(), key=lambda r: r["person_id"])
    ]

    # ---- authors -------------------------------------------------------------------------------------------
    by_author: dict[str, list[int]] = defaultdict(list)
    for i, aid in person_of.items():
        by_author[aid].append(i)
    work_authors = Counter(w["author_id"] for w in works if w["author_id"])
    for aid, idx in by_author.items():
        if aid not in work_authors:
            continue
        rs = [recs[i] for i in idx]
        deaths = Counter(r.death_ah for r in rs if r.death_ah)
        cents = Counter(r.century_ah for r in rs if r.century_ah)
        death = deaths.most_common(1)[0][0] if len(deaths) == 1 else None
        dsrc = None
        if death:
            srcs = {r.death_source for r in rs if r.death_ah == death}
            dsrc = "shamela_book" if "shamela_book" in srcs else sorted(srcs)[0]
        cent = century_ah(death) if death else (cents.most_common(1)[0][0] if len(cents) == 1 else None)
        full = Counter((r.author_full_name, r.sources.get("author_full_name")) for r in rs if r.author_full_name)
        fname, fsrc = full.most_common(1)[0][0] if full else (None, None)
        sids = Counter(r.shamela_author_id for r in rs if r.shamela_author_id)
        sid = sids.most_common(1)[0][0] if len(sids) == 1 else None
        if not death:
            dconf = None
        elif not any(r.death_name_matched for r in rs if r.death_ah == death):
            dconf = "low"  # the year of a matched catalog book's author, whose name does not match this one
        else:
            dconf = "high" if deaths[death] >= 2 or (cents and century_ah(death) in cents) else "medium"
        lo, hi = ah_to_ce_range(death) if death else (None, None)
        names = Counter(r.author for r in rs)
        author_rows[aid] = {
            "author_id": aid,
            "name_ar": names.most_common(1)[0][0],
            "full_name_ar": fname,
            "full_name_source": fsrc,
            "death_ah": death,
            "death_ce_from": lo,
            "death_ce_to": hi,
            "century_ah": cent,
            "death_source": dsrc,
            "death_confidence": dconf,
            "n_works": work_authors[aid],
            "openiti_author_uri": None,
            "wikidata_qid": None,
            "ext_ids": f"shamela_author:{sid}" if sid else None,
            "canonical_author_id": aid,
        }
    _canonical_authors(author_rows)

    # ---- manuscripts ---------------------------------------------------------------------------------------
    for i, r in enumerate(recs):
        if r.kind != "manuscript":
            continue
        eid = edition_of[r.key]
        manuscripts.append(
            {
                "manuscript_id": h10("m", eid),
                "edition_id": eid,
                "work_id": work_of[i],
                "title_ar": r.title,
                "author_id": person_of.get(i) if person_of.get(i) in author_rows else None,
                "holding_library_ar": r.holding_library or None,
                "shelfmark": r.shelfmark or None,
                "holding_confidence": r.holding_confidence or None,
                "printed_edition_id": edition_of.get(r.printed_key) if r.printed_key else None,
            }
        )
    # printed editions of the same work, when the input named none
    printed_by_work = defaultdict(list)
    for e in editions:
        if e["kind"] != "manuscript":
            printed_by_work[e["work_id"]].append(e["edition_id"])
    for m in manuscripts:
        if not m["printed_edition_id"] and printed_by_work.get(m["work_id"]):
            m["printed_edition_id"] = sorted(printed_by_work[m["work_id"]])[0]

    cats = []
    for ar, en in CATEGORY_EN.items():
        cats.append(
            {
                "category_ar": ar,
                "category_en": en,
                "n_works": sum(1 for w in works if w["category_ar"] == ar),
                "n_editions": sum(1 for e, r in zip(editions, recs) if r.category_ar == ar),
            }
        )
    for w in works:  # authors' work counts per final work rows
        if w["author_id"] and w["author_id"] not in author_rows:
            w["author_id"] = None

    return {
        "works": sorted(works, key=lambda r: r["work_id"]),
        "editions": sorted(editions, key=lambda r: r["edition_id"]),
        "authors": sorted(author_rows.values(), key=lambda r: r["author_id"]),
        "editors": editor_rows,
        "edition_editors": sorted(ed_eds, key=lambda r: (r["edition_id"], r["seq"], r["person_id"])),
        "manuscripts": sorted(manuscripts, key=lambda r: r["manuscript_id"]),
        "edition_files": sorted(files, key=lambda r: (r["edition_id"], r["seq"])),
        "categories": cats,
    }
