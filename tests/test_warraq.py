import json

import pytest

from turath_catalog.build import build_tables
from turath_catalog.sources.warraq import WarraqWorkspace
from turath_catalog.validate import check


@pytest.fixture
def ws(workspace):
    return WarraqWorkspace(workspace)


def by_title(recs):
    return {r.title: r for r in recs}


def test_review_held_and_non_arabic_rows_are_excluded(ws):
    recs = by_title(ws.records())
    assert "كتاب في نزاع" not in recs
    assert "كتاب معلق" not in recs
    assert "Frankenstein" not in recs
    ex = ws.report.excluded
    assert ex["sources disagree on the edition (held for review)"] == 1
    assert ex["title or author under review"] == 1
    assert ex["title not in Arabic script (out of scope)"] == 1


def test_values_carry_their_sources(ws):
    r = by_title(ws.records())["آداب الفتوى"]
    assert r.title_page_read
    assert [e.name for e in r.editors] == ["بسام عبد الوهاب الجابي"]  # «الجابي، بسام عبد الوهاب» turned round
    assert (r.publisher, r.place) == ("دار الفكر", "دمشق")
    assert (r.year_ah, r.year_ce, r.edition_number, r.pages) == (1408, 1988, 1, 96)
    assert r.sources["editors"] == "catalog_record" and r.sources["publisher"] == "title_page"
    assert r.volumes == 1 and r.sources["volumes"] == "catalog_record"
    assert r.death_ah == 676 and r.death_source == "shamela_book"
    assert r.shamela_work_ids == [(7, "high")]  # «cover» relation is not identity
    assert r.shamela_author_id == 35
    assert r.author_full_name == "يحيى بن شرف بن مري النووي أبو زكريا"  # cut before the occupations
    assert r.waqfeya_ids == ["66a88e0187c55ca3e12f3acb"]


def test_prose_is_never_read(ws):
    blob = json.dumps([r.__dict__ for r in ws.records()], ensure_ascii=False, default=lambda o: o.__dict__)
    for private in ("وصف نثري", "سيرة طويلة", "ملاحظة خاصة", "owner: ask", "فقيه"):
        assert private not in blob


def test_disagreeing_years_are_dropped_and_slashes_become_places(ws):
    r = by_title(ws.records())["الرحلة المغربية"]
    assert r.year_ah is None and r.year_ce is None
    assert ws.report.dropped_values["year_ah and year_ce disagree (both dropped)"] == 1
    assert (r.publisher, r.place) == ("دار سعد الدين", "دمشق")
    assert r.editors[0].role == "editor" and r.editors[0].role_ar == "تحقيق"
    assert r.author == "محمد العبدري"
    assert r.author_full_name == "محمد بن محمد بن علي العبدري البلنسي"


def test_death_year_in_doubt_is_dropped(ws):
    r = by_title(ws.records())["مسائل"]
    assert r.death_ah is None and r.century_ah == 3


def test_manuscript_holding_and_printed_edition(ws):
    recs = ws.records()
    m = by_title(recs)["رحلة العبدري"]
    assert m.kind == "manuscript"
    assert (m.holding_library, m.shelfmark, m.holding_confidence) == ("وقف رواق المغاربة بالأزهر", "12", "high")
    t = build_tables(recs)
    (row,) = t["manuscripts"]
    printed = next(e for e in t["editions"] if e["edition_id"] == row["printed_edition_id"])
    assert printed["title_ar"] == "الرحلة المغربية"
    assert check(t) == []


def test_not_a_workspace(tmp_path):
    with pytest.raises(FileNotFoundError):
        WarraqWorkspace(tmp_path)


@pytest.mark.parametrize(
    "value, edition, expected",
    [
        ("د/ وداد القاضي", "", [("وداد القاضي", "editor")]),
        ("إحسان ذنون الثامري / د. محمد عبد الله القدحات", "", [("إحسان ذنون الثامري", "editor"), ("محمد عبد الله القدحات", "editor")]),
        ("ط. دبي", "", []),
        ("رسالة ماجستير", "", []),
        ("محمد حامد الفقي", "صححه وعلق عليه محمد حامد الفقي - مطبعة السنة", [("محمد حامد الفقي", "corrector")]),
        ("عبد الله التركي", "شرح عبد الله التركي - هجر", [("عبد الله التركي", "commentator")]),
        ("سعيد", "قدم له سعيد - دار", [("سعيد", "introducer")]),
    ],
)
def test_parse_editors(value, edition, expected):
    assert [(e.name, e.role) for e in WarraqWorkspace.parse_editors(value, edition)] == expected


@pytest.mark.parametrize(
    "text, kind",
    [
        ("مخطوط", "manuscript"),
        ("طبعة حجرية فاس", "lithograph"),
        ("رسالة ماجستير - جامعة أم القرى", "thesis"),
        ("مستل من مجلة", "offprint"),
        ("ت فلان - دار", "printed"),
    ],
)
def test_kind_of(text, kind):
    assert WarraqWorkspace.kind_of(text) == kind


@pytest.mark.parametrize(
    "value, expected",
    [
        ("دار المعارف 1958 - طبعة ملونة", ("دار المعارف", "")),
        ("المطبعة السلفية بمصر", ("المطبعة السلفية", "مصر")),
        ("ط. دار الفكر", ("دار الفكر", "")),
        ("مكتبة الخانجي - القاهرة 1997", ("مكتبة الخانجي", "القاهرة")),
        ("القاهرة", ("", "القاهرة")),
        ("دار سعد الدين / دمشق", ("دار سعد الدين", "دمشق")),
    ],
)
def test_split_place(ws, value, expected):
    assert ws.split_place(value) == expected


@pytest.mark.parametrize(
    "value, names",
    [
        ("أحمد محمد شاكر وعبد السلام هارون", ["أحمد محمد شاكر", "عبد السلام هارون"]),
        ("محمود وأحمد شاكر", ["محمود وأحمد شاكر"]),  # cannot be split into two full names
        ("عبد الله ولد إسلم", ["عبد الله ولد إسلم"]),  # «ولد» is part of the name
        ("محمد بن علي ووليد قصاب", ["محمد بن علي", "وليد قصاب"]),
    ],
)
def test_joint_editors(value, names):
    assert [e.name for e in WarraqWorkspace.parse_editors(value, "")] == names
