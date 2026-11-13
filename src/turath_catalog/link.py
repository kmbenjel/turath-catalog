"""Links to OpenITI and Wikidata, made only where they can be checked.

OpenITI (release 2025.1.9 metadata, one TSV): a work gets an OpenITI book URI when the OpenITI author's
death year (the 4 digits of the URI) equals the author's death year here, the titles agree (folded and
equal: `high`; one a prefix of the other with 3+ words: `medium`), the author names share a distinctive
word, and exactly one OpenITI book fits. The author then takes that book's author URI.

Wikidata: by identifier crosswalk, never by name search.
  * authors: Wikidata items that carry a Shamela author id (P12435) equal to the author's Shamela id,
    kept only when the item's death year (P570) falls within the Hijri death year's Gregorian range ±1;
  * editions: the item that carries the Shamela book id (P12239) of the same edition;
  * works: that edition item's "edition or translation of" (P629);
  * OpenITI author ids on Wikidata (P13870) fill openiti_author_uri when the death years agree.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from .textnorm import norm, title_key, tokens

OPENITI_URL = "https://raw.githubusercontent.com/OpenITI/RELEASE/master/metadata/OpenITI_metadata_2025-1-9.tsv"
OPENITI_RELEASE = "2025.1.9"
SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "turath-catalog/0.1 (open bibliographic dataset; https://github.com/kmbenjel/turath-catalog)"
QUERIES = {
    "shamela_author": "SELECT ?item ?v ?d WHERE { ?item wdt:P12435 ?v . OPTIONAL { ?item wdt:P570 ?d } }",
    "shamela_book": "SELECT ?item ?v ?work WHERE { ?item wdt:P12239 ?v . OPTIONAL { ?item wdt:P629 ?work } }",
    "openiti_author": "SELECT ?item ?v ?d WHERE { ?item wdt:P13870 ?v . OPTIONAL { ?item wdt:P570 ?d } }",
}


def _fetch(url: str, dest: Path, data: bytes | None = None, accept: str = "*/*") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Accept": accept})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                tmp = dest.with_suffix(dest.suffix + ".part")
                tmp.write_bytes(r.read())
                tmp.replace(dest)
                return dest
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    return dest


def openiti_metadata(cache: Path, offline: bool = False) -> list[dict]:
    path = cache / "OpenITI_metadata_2025-1-9.tsv"
    if not path.exists():
        if offline:
            return []
        _fetch(OPENITI_URL, path)
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def wikidata(cache: Path, name: str, offline: bool = False) -> list[dict]:
    path = cache / f"wikidata-{name}.csv"
    if not path.exists():
        if offline:
            return []
        q = urllib.parse.urlencode({"query": QUERIES[name]}).encode()
        _fetch(SPARQL, path, data=q, accept="text/csv")
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["qid"] = r["item"].rsplit("/", 1)[-1]
        if r.get("work"):
            r["work"] = r["work"].rsplit("/", 1)[-1]
        m = re.match(r"^(-?\d{1,4})-", r.get("d") or "")
        r["year"] = int(m.group(1)) if m else None
    return rows


def _ext(row: dict, scheme: str) -> list[str]:
    return [x.split(":", 1)[1] for x in (row.get("ext_ids") or "").split(";") if x.startswith(scheme + ":")]


def _add_ext(row: dict, item: str) -> None:
    parts = [x for x in (row.get("ext_ids") or "").split(";") if x]
    if item not in parts:
        parts.append(item)
    row["ext_ids"] = ";".join(parts) or None


def link_openiti(tables: dict, meta: list[dict]) -> dict:
    """Fill works.openiti_uri / openiti_confidence and authors.openiti_author_uri. Returns counts."""
    books: dict[int, dict[str, dict]] = defaultdict(dict)  # death year -> book uri -> info
    for r in meta:
        if r.get("language") != "ara" or not (r.get("date") or "").isdigit():
            continue
        b = books[int(r["date"])].setdefault(r["book"], {"titles": set(), "author": set()})
        for t in (r.get("title_ar") or "").split("::"):
            if title_key(t):
                b["titles"].add(title_key(t))
        b["author"] |= tokens(r.get("author_ar", "").replace("::", " "))
    authors = {a["author_id"]: a for a in tables["authors"]}
    n = {"high": 0, "medium": 0, "ambiguous": 0}
    for w in tables["works"]:
        a = authors.get(w["author_id"] or "")
        if not a or not a["death_ah"] or a["death_ah"] not in books:
            continue
        ours = {title_key(w["title_ar"])} | {title_key(t) for t in (w["alt_titles_ar"] or "").split(";") if t}
        ours.discard("")
        atok = tokens(a["name_ar"]) | tokens(a["full_name_ar"])
        hits = {"high": [], "medium": []}
        for uri, b in books[a["death_ah"]].items():
            if not (atok & b["author"]):
                continue
            if ours & b["titles"]:
                hits["high"].append(uri)
            elif any(_prefix(x, y) for x in ours for y in b["titles"]):
                hits["medium"].append(uri)
        for level in ("high", "medium"):
            if len(hits[level]) == 1:
                w["openiti_uri"], w["openiti_confidence"] = hits[level][0], level
                n[level] += 1
                break
            if len(hits[level]) > 1:
                n["ambiguous"] += 1
                break
    # author URIs from the works they wrote
    by_author: dict[str, set] = defaultdict(set)
    for w in tables["works"]:
        if w["openiti_uri"] and w["author_id"]:
            by_author[w["author_id"]].add(w["openiti_uri"].split(".")[0])
    for aid, uris in by_author.items():
        if len(uris) == 1:
            authors[aid]["openiti_author_uri"] = uris.pop()
    n["authors"] = sum(1 for a in tables["authors"] if a["openiti_author_uri"])
    return n


def _prefix(a: str, b: str) -> bool:
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(short.split()) >= 3 and (long_ + " ").startswith(short + " ")


def link_wikidata(tables: dict, sh_auth: list[dict], sh_book: list[dict], oi_auth: list[dict]) -> dict:
    def fits(a: dict, year: int | None) -> bool:
        return bool(a["death_ah"]) and year is not None and a["death_ce_from"] - 1 <= year <= a["death_ce_to"] + 1

    by_sid = defaultdict(list)
    for r in sh_auth:
        by_sid[r["v"]].append(r)
    n = {"authors": 0, "authors_rejected_by_death_year": 0, "editions": 0, "works": 0, "openiti_authors_from_wikidata": 0}
    for a in tables["authors"]:
        sids = _ext(a, "shamela_author")
        if len(sids) != 1:
            continue
        items = {r["qid"]: r for r in by_sid.get(sids[0], [])}
        good = [q for q, r in items.items() if fits(a, r["year"])]
        if len(good) == 1:
            a["wikidata_qid"] = good[0]
            n["authors"] += 1
        elif items:
            n["authors_rejected_by_death_year"] += 1
    oi_by_qid = defaultdict(set)
    for r in oi_auth:
        oi_by_qid[r["qid"]].add(r["v"])
    for a in tables["authors"]:
        if a["wikidata_qid"] and not a["openiti_author_uri"] and len(oi_by_qid.get(a["wikidata_qid"], ())) == 1:
            uri = next(iter(oi_by_qid[a["wikidata_qid"]]))
            if re.match(r"^\d{4}", uri) and a["death_ah"] == int(uri[:4]):
                a["openiti_author_uri"] = uri
                n["openiti_authors_from_wikidata"] += 1
    ed_item = defaultdict(set)
    work_item = defaultdict(set)
    for r in sh_book:
        ed_item[r["v"]].add(r["qid"])
        if r.get("work"):
            work_item[r["v"]].add(r["work"])
    works = {w["work_id"]: w for w in tables["works"]}
    per_work = defaultdict(set)
    for e in tables["editions"]:
        sids = _ext(e, "shamela")
        if len(sids) == 1 and len(ed_item.get(sids[0], ())) == 1:
            e["wikidata_qid"] = next(iter(ed_item[sids[0]]))
            n["editions"] += 1
            per_work[e["work_id"]] |= work_item.get(sids[0], set())
    for wid, qs in per_work.items():
        if len(qs) == 1:
            works[wid]["wikidata_qid"] = qs.pop()
            n["works"] += 1
    for w in tables["works"]:  # a work linked to Shamela books whose Wikidata editions point at one work item
        if not w["wikidata_qid"]:
            qs = set().union(*(work_item.get(s, set()) for s in _ext(w, "shamela"))) if _ext(w, "shamela") else set()
            if len(qs) == 1:
                w["wikidata_qid"] = qs.pop()
                n["works"] += 1
    return n


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = ["link_openiti", "link_wikidata", "openiti_metadata", "wikidata", "norm"]
