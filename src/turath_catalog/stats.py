"""Summaries of a release and a self-consistent sample cut."""

from __future__ import annotations

from collections import Counter


def summary(t: dict) -> str:
    w, e, a = t["works"], t["editions"], t["authors"]
    pct = lambda n, d: f"{n:,} ({100 * n / d:.0f}%)" if d else "0"
    lines = [
        f"works            {len(w):,}",
        f"editions         {len(e):,}  (files {len(t['edition_files']):,})",
        f"authors          {len(a):,}  with death year {pct(sum(1 for x in a if x['death_ah']), len(a))}",
        f"editors          {len(t['editors']):,}  (credits {len(t['edition_editors']):,})",
        f"manuscripts      {len(t['manuscripts']):,}",
        "",
        "editions with    editor "
        + pct(sum(1 for x in e if x["editors_ar"]), len(e))
        + " · publisher "
        + pct(sum(1 for x in e if x["publisher_ar"]), len(e))
        + " · year "
        + pct(sum(1 for x in e if x["year_ah"] or x["year_ce"]), len(e))
        + " · volumes "
        + pct(sum(1 for x in e if x["volumes"]), len(e)),
        "edition confidence " + ", ".join(f"{k} {v:,}" for k, v in sorted(Counter(x["confidence"] for x in e).items())),
        "links            OpenITI works "
        + pct(sum(1 for x in w if x["openiti_uri"]), len(w))
        + " · Wikidata authors "
        + pct(sum(1 for x in a if x["wikidata_qid"]), len(a))
        + " · Shamela works "
        + pct(sum(1 for x in w if "shamela:" in (x["ext_ids"] or "")), len(w)),
    ]
    return "\n".join(lines)


def cut_sample(t: dict, n_works: int = 150) -> dict:
    """The first `n_works` works that have an author with a death year, a known editor and a link, plus
    everything they reference, so the sample passes the same validation as a full release."""
    authors = {x["author_id"]: x for x in t["authors"]}
    eds_by_work: dict[str, list] = {}
    for e in t["editions"]:
        eds_by_work.setdefault(e["work_id"], []).append(e)

    def score(w):
        a = authors.get(w["author_id"] or "", {})
        es = eds_by_work[w["work_id"]]
        return (
            -(len(es) > 1),
            -bool(w["openiti_uri"]),
            -bool(a.get("wikidata_qid")),
            -any(e["editors_ar"] for e in es),
            -bool(a.get("death_ah")),
            w["work_id"],
        )

    picked = sorted(t["works"], key=score)[: n_works - 10]
    picked += [w for w in t["works"] if any(e["kind"] == "manuscript" for e in eds_by_work[w["work_id"]])][:10]
    works = {w["work_id"]: w for w in picked}
    eds = [e for e in t["editions"] if e["work_id"] in works]
    eids = {e["edition_id"] for e in eds}
    aids = {w["author_id"] for w in works.values() if w["author_id"]}
    ee = [x for x in t["edition_editors"] if x["edition_id"] in eids]
    pids = {x["person_id"] for x in ee}
    ms = [dict(m) for m in t["manuscripts"] if m["edition_id"] in eids]
    for m in ms:
        if m["printed_edition_id"] not in eids:
            m["printed_edition_id"] = None
    au = []
    for a in t["authors"]:
        if a["author_id"] in aids:
            a = dict(a)
            a["n_works"] = sum(1 for w in works.values() if w["author_id"] == a["author_id"])
            au.append(a)
    editors = []
    for p in t["editors"]:
        if p["person_id"] in pids:
            p = dict(p)
            p["n_editions"] = len({x["edition_id"] for x in ee if x["person_id"] == p["person_id"]})
            editors.append(p)
    cats = []
    for c in t["categories"]:
        c = dict(c)
        c["n_works"] = sum(1 for w in works.values() if w["category_ar"] == c["category_ar"])
        c["n_editions"] = sum(1 for e in eds if works[e["work_id"]]["category_ar"] == c["category_ar"])
        cats.append(c)
    return {
        "works": sorted(works.values(), key=lambda r: r["work_id"]),
        "editions": eds,
        "authors": au,
        "editors": editors,
        "edition_editors": ee,
        "manuscripts": ms,
        "edition_files": [f for f in t["edition_files"] if f["edition_id"] in eids],
        "categories": cats,
    }
