from turath_catalog.build import build_tables
from turath_catalog.link import link_openiti, link_wikidata


def meta(uri, date, author, title):
    return {
        "version_uri": uri + ".X-ara1",
        "book": uri,
        "date": date,
        "author_ar": author,
        "title_ar": title,
        "language": "ara",
        "ed_info": "",
    }


def test_openiti_needs_year_title_and_author(records):
    t = build_tables(records)
    m = [
        meta("0676Nawawi.MajmucSharhMuhadhdhab", "0676", "يحيى بن شرف النووي", "المجموع شرح المهذب :: المجموع"),
        meta("0676Nawawi.Arbacun", "0676", "النووي", "الأربعون النووية"),  # not equal and too short for a prefix
        meta("0851IbnQadiShuhba.Tabaqat", "0851", "ابن قاضي شهبة", "طبقات الشافعية"),
        meta("0851Other.Tabaqat", "0851", "ابن قاضي شهبة", "طبقات الشافعية"),  # two candidates: ambiguous, no link
        meta("0335Shashi.Shamil", "0336", "الشاشي", "الشامل"),  # wrong year
        meta("0325Shashi.Usul", "0325", "الشاشي", "أصول الشاشي"),
    ]
    n = link_openiti(t, m)
    works = {w["title_ar"]: w for w in t["works"]}
    assert works["المجموع شرح المهذب"]["openiti_uri"] == "0676Nawawi.MajmucSharhMuhadhdhab"
    assert works["المجموع شرح المهذب"]["openiti_confidence"] == "high"
    assert works["طبقات الشافعية"]["openiti_uri"] is None
    assert works["الشامل"]["openiti_uri"] is None
    assert works["أصول الشاشي"]["openiti_uri"] == "0325Shashi.Usul"
    assert n["ambiguous"] == 1
    authors = {a["author_id"]: a for a in t["authors"]}
    assert authors[works["المجموع شرح المهذب"]["author_id"]]["openiti_author_uri"] == "0676Nawawi"


def test_openiti_prefix_match_is_medium(records):
    t = build_tables(records)
    link_openiti(t, [meta("0676Nawawi.Majmuc", "0676", "النووي", "المجموع شرح المهذب للشيرازي")])
    w = next(w for w in t["works"] if w["title_ar"] == "المجموع شرح المهذب")
    assert (w["openiti_uri"], w["openiti_confidence"]) == ("0676Nawawi.Majmuc", "medium")


def test_wikidata_crosswalk_checks_death_year(records):
    t = build_tables(records)
    nawawi = next(a for a in t["authors"] if a["name_ar"] == "النووي")
    ajurri = next(a for a in t["authors"] if a["name_ar"] == "الآجري")
    nawawi["ext_ids"], ajurri["ext_ids"] = "shamela_author:35", "shamela_author:99"
    sh_auth = [
        {"qid": "Q295394", "v": "35", "year": 1277},
        {"qid": "Q1", "v": "99", "year": 1500},  # death year far from 360 AH: rejected
    ]
    ed = next(e for e in t["editions"] if e["title_ar"] == "المجموع شرح المهذب" and e["ext_ids"] is None)
    ed["ext_ids"] = "shamela:2186"
    sh_book = [{"qid": "Q200", "v": "2186", "work": "Q300"}]
    oi = [{"qid": "Q295394", "v": "0676Nawawi", "year": 1277}]
    n = link_wikidata(t, sh_auth, sh_book, oi)
    assert nawawi["wikidata_qid"] == "Q295394" and nawawi["openiti_author_uri"] == "0676Nawawi"
    assert ajurri["wikidata_qid"] is None and n["authors_rejected_by_death_year"] == 1
    assert ed["wikidata_qid"] == "Q200"
    assert next(w for w in t["works"] if w["work_id"] == ed["work_id"])["wikidata_qid"] == "Q300"
