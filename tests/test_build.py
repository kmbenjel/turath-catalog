import re

from turath_catalog.build import build_tables, h10, work_id_for
from turath_catalog.model import ID
from turath_catalog.textnorm import author_key, title_key
from turath_catalog.validate import check


def test_tables_validate_and_ids_have_their_form(records):
    t = build_tables(records)
    assert check(t) == []
    for table, col, kind in [
        ("works", "work_id", "work"),
        ("editions", "edition_id", "edition"),
        ("authors", "author_id", "author"),
        ("editors", "person_id", "person"),
    ]:
        assert all(re.match(ID[kind], r[col]) for r in t[table])


def test_editions_of_one_work_are_grouped(records):
    t = build_tables(records)
    majmu = [w for w in t["works"] if w["title_ar"] == "المجموع شرح المهذب"]
    assert len(majmu) == 1 and majmu[0]["n_editions"] == 2
    assert majmu[0]["work_id"] == work_id_for("المجموع شرح المهذب", "النووي")
    assert majmu[0]["work_id"] == h10("w", f"{title_key('المجموع شرح المهذب')}|{author_key('النووي')}")
    assert majmu[0]["ext_ids"] == "shamela:2186"
    assert majmu[0]["confidence"] == "high"


def test_same_title_by_different_authors_are_different_works(records):
    t = build_tables(records)
    arbaun = [w for w in t["works"] if w["title_ar"] == "الأربعون"]
    assert len(arbaun) == 2 and len({w["author_id"] for w in arbaun}) == 2


def test_one_name_two_death_years_is_two_people(records):
    t = build_tables(records)
    shashi = [a for a in t["authors"] if a["name_ar"] == "الشاشي"]
    assert sorted(a["death_ah"] for a in shashi) == [325, 335]
    assert len({a["author_id"] for a in shashi}) == 2


def test_century_only_record_joins_the_dated_person(records):
    t = build_tables(records)
    nawawi = [a for a in t["authors"] if a["name_ar"] == "النووي"]
    assert len(nawawi) == 1
    a = nawawi[0]
    assert (a["death_ah"], a["death_ce_from"], a["death_ce_to"], a["century_ah"]) == (676, 1277, 1278, 7)
    assert a["death_source"] == "shamela_book" and a["death_confidence"] == "high"
    assert a["n_works"] == 2


def test_shorter_editor_name_merges_into_the_fuller_one(records):
    t = build_tables(records)
    mutii = [p for p in t["editors"] if "المطيعي" in p["name_ar"]]
    assert len(mutii) == 1
    assert mutii[0]["name_ar"] == "محمد نجيب المطيعي"
    assert mutii[0]["name_variants_ar"] == "محمد المطيعي"
    assert mutii[0]["n_editions"] == 2


def test_manuscript_points_to_a_printed_edition_of_the_work(records):
    t = build_tables(records)
    (m,) = t["manuscripts"]
    eds = {e["edition_id"]: e for e in t["editions"]}
    assert m["holding_library_ar"] == "مكتبة الأزهر" and m["shelfmark"] == "267"
    assert eds[m["printed_edition_id"]]["kind"] == "printed"
    assert eds[m["printed_edition_id"]]["work_id"] == m["work_id"]


def test_anonymous_work_has_no_author(records):
    t = build_tables(records)
    (w,) = [w for w in t["works"] if w["title_ar"] == "ديوان مجهول"]
    assert w["author_id"] is None and w["author_name_ar"] is None


def test_confidence_levels(records):
    t = build_tables(records)
    conf = {e["title_ar"] + e["edition_id"]: e["confidence"] for e in t["editions"]}
    assert set(conf.values()) == {"high", "medium", "low"}


def test_files_and_sizes(records):
    t = build_tables(records)
    e = next(e for e in t["editions"] if e["n_files"] == 2)
    assert e["size_bytes"] == 1200
    assert [f["volume_label"] for f in t["edition_files"] if f["edition_id"] == e["edition_id"]] == ["01", "02"]


def test_build_is_deterministic(records):
    assert build_tables(records) == build_tables(list(reversed(records)))
