"""How much of a release is absent from, or thinner in, the open sources it links to.

Numbers are computed from data anyone can download: the OpenITI 2025.1.9 metadata TSV and three
Wikidata SPARQL results (cached by `turath-catalog build`). Shamela figures come from the links the
release itself carries (ext_ids). Every figure is a lower bound for coverage elsewhere: a work we could
not link may still be in the other source under a title we did not recognise.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from . import link
from .textnorm import tokens


def coverage(t: dict, cache: Path) -> dict:
    works, eds, authors = t["works"], t["editions"], t["authors"]
    A = {a["author_id"]: a for a in authors}
    dated = [w for w in works if A.get(w["author_id"] or "", {}).get("death_ah")]
    classical = [w for w in dated if A[w["author_id"]]["death_ah"] <= 1300]
    eds_by_work = defaultdict(list)
    for e in eds:
        eds_by_work[e["work_id"]].append(e)
    res: dict = {
        "release": {
            "works": len(works),
            "editions": len(eds),
            "authors": len(authors),
            "works_with_dated_author": len(dated),
            "works_by_authors_died_by_1300_ah": len(classical),
            "editions_with_editor": sum(1 for e in eds if e["editors_ar"]),
            "editions_with_publisher": sum(1 for e in eds if e["publisher_ar"]),
            "editions_with_year": sum(1 for e in eds if e["year_ah"] or e["year_ce"]),
            "editions_with_volumes": sum(1 for e in eds if e["volumes"]),
            "authors_with_death_year": sum(1 for a in authors if a["death_ah"]),
            "works_with_2plus_editions": sum(1 for w in works if w["n_editions"] > 1),
        }
    }
    # ---- OpenITI ---------------------------------------------------------------------------------------
    meta = link.openiti_metadata(cache, offline=True)
    if meta:
        ara = [r for r in meta if r.get("language") == "ara"]
        ed_info = defaultdict(str)
        for r in ara:
            ed_info[r["book"]] += " " + (r.get("ed_info") or "")
        linked = [w for w in dated if w["openiti_uri"]]
        linked_classical = [w for w in classical if w["openiti_uri"]]
        named = total = 0
        for w in linked:
            info = tokens(ed_info.get(w["openiti_uri"], ""))
            for e in eds_by_work[w["work_id"]]:
                if e["editors_ar"]:
                    total += 1
                    fam = {sorted(tokens(n))[-1] for n in e["editors_ar"].split(";") if tokens(n)}
                    named += bool(fam & info)
        res["openiti"] = {
            "release": link.OPENITI_RELEASE,
            "books": len({r["book"] for r in ara}),
            "versions": len(ara),
            "versions_with_any_edition_statement": sum(1 for r in ara if (r.get("ed_info") or "").strip()),
            "has_columns_for_publisher_editor_volumes": False,
            "dated_works_found": len(linked),
            "dated_works_not_found": len(dated) - len(linked),
            "classical_works_found": len(linked_classical),
            "classical_works_not_found": len(classical) - len(linked_classical),
            "our_editions_of_found_works_with_editor": total,
            "of_which_editor_named_in_openiti_ed_info": named,
            "extra_editions_for_found_works": sum(len(eds_by_work[w["work_id"]]) for w in linked),
        }
    # ---- Wikidata (identifier crosswalk; a lower bound) --------------------------------------------------
    wd = {n: link.wikidata(cache, n, offline=True) for n in link.QUERIES}
    if any(wd.values()):
        da = [a for a in authors if a["death_ah"]]
        res["wikidata"] = {
            "items_with_shamela_author_id": len({r["qid"] for r in wd["shamela_author"]}),
            "items_with_shamela_book_id": len({r["qid"] for r in wd["shamela_book"]}),
            "items_with_openiti_author_id": len({r["qid"] for r in wd["openiti_author"]}),
            "dated_authors_linked": sum(1 for a in da if a["wikidata_qid"]),
            "dated_authors_not_linked": sum(1 for a in da if not a["wikidata_qid"]),
            "works_linked": sum(1 for w in works if w["wikidata_qid"]),
            "editions_linked": sum(1 for e in eds if e["wikidata_qid"]),
            "editions_not_linked": sum(1 for e in eds if not e["wikidata_qid"]),
        }
    # ---- Shamela (links carried by the release) ------------------------------------------------------------
    in_sh = {w["work_id"] for w in works if "shamela:" in (w["ext_ids"] or "")}
    same_ed = sum(1 for e in eds if "shamela:" in (e["ext_ids"] or ""))
    res["shamela"] = {
        "works_linked": len(in_sh),
        "works_not_linked": len(works) - len(in_sh),
        "editions_same_edition_in_shamela": same_ed,
        "editions_of_linked_works_in_another_edition": sum(
            1 for e in eds if e["work_id"] in in_sh and "shamela:" not in (e["ext_ids"] or "")
        ),
        "editions_of_works_not_in_shamela": sum(1 for e in eds if e["work_id"] not in in_sh),
    }
    return res
