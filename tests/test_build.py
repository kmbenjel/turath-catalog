import json
import re

from turath_catalog.build import build_tables, compose_label, h10, work_id_for
from turath_catalog.model import ID
from turath_catalog.record import EditionRecord, Editor
from turath_catalog.textnorm import author_key, title_key
from turath_catalog.validate import check


def rec(key, title, author="", **kw) -> EditionRecord:
    return EditionRecord(key=key, title=title, author=author, category_ar="الفقه العام", **kw)


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


def test_label_is_composed_from_the_fields_not_the_input_label():
    r = rec(
        "k",
        "كتاب المجروحين من المحدثين = المجروحين",
        "ابن حبان البستي",
        label="كتاب المجروحين من المحدثين - ابن حبان البستي (ت حمدي السلفي - دار الوعي)",
        editors=[Editor("حمدي السلفي"), Editor("محمد علي", role="translator")],
        publisher="دار الصميعي",
        place="الرياض - السعودية",
    )
    assert compose_label(r) == "كتاب المجروحين من المحدثين - ابن حبان البستي - ت حمدي السلفي - ترجمة محمد علي - دار الصميعي الرياض السعودية"
    e = build_tables([r])["editions"][0]
    assert e["label_ar"] == compose_label(r)
    assert "دار الوعي" not in e["label_ar"] and "(" not in e["label_ar"]
    assert compose_label(rec("t", "الرسالة")) == "الرسالة"
    two = rec("u", "الأم", "الشافعي", editors=[Editor("رفعت فوزي"), Editor("علي محمد")])
    assert compose_label(two) == "الأم - الشافعي - ت رفعت فوزي وعلي محمد"


def test_a_title_with_a_second_name_groups_with_the_plain_title():
    t = build_tables(
        [
            rec("a", "السيرة النبوية = سيرة ابن هشام", "ابن هشام", publisher="دار الكتاب العربي"),
            rec("b", "السيرة النبوية", "ابن هشام", publisher="دار المعرفة"),
            rec("c", "السيرة النبوية", "ابن كثير"),
        ]
    )
    assert check(t) == []
    (w,) = [w for w in t["works"] if w["author_name_ar"] == "ابن هشام"]
    assert (w["title_ar"], w["title_clean_ar"], w["alt_titles_ar"], w["n_editions"]) == (
        "السيرة النبوية",
        "السيرة النبوية",
        "سيرة ابن هشام",
        2,
    )
    assert w["work_id"] == work_id_for("السيرة النبوية", "ابن هشام")  # the recipe id, not a disambiguated one
    assert len(t["works"]) == 2


def test_edition_keeps_the_title_as_given_and_offers_the_parts():
    t = build_tables(
        [
            rec("a", "الجامع لأحكام القرآن = تفسير القرطبي", "القرطبي"),
            rec("b", "تفسير يحيى بن سلام (من النحل إلى الصافات)", "يحيى بن سلام"),
            rec("c", "آداب الفتوى", "النووي"),
        ]
    )
    e = {e["title_ar"]: e for e in t["editions"]}
    a, b, c = e["الجامع لأحكام القرآن = تفسير القرطبي"], e["تفسير يحيى بن سلام (من النحل إلى الصافات)"], e["آداب الفتوى"]
    assert (a["title_clean_ar"], a["alt_titles_ar"], a["title_note_ar"]) == ("الجامع لأحكام القرآن", "تفسير القرطبي", None)
    assert (b["title_clean_ar"], b["alt_titles_ar"], b["title_note_ar"]) == ("تفسير يحيى بن سلام", None, "من النحل إلى الصافات")
    assert (c["title_clean_ar"], c["alt_titles_ar"], c["title_note_ar"]) == ("آداب الفتوى", None, None)
    assert b["label_ar"] == "تفسير يحيى بن سلام - يحيى بن سلام"
    w = {w["title_clean_ar"]: w for w in t["works"]}
    assert w["تفسير يحيى بن سلام"]["title_ar"] == "تفسير يحيى بن سلام (من النحل إلى الصافات)"
    assert w["تفسير يحيى بن سلام"]["work_id"] == work_id_for("تفسير يحيى بن سلام", "يحيى بن سلام")


def test_an_edition_mark_the_row_confirms_is_dropped():
    r = rec("a", "الحماسة البصرية (ط. الخانجي)", "البصري", editors=[Editor("عادل سليمان جمال")], publisher="مكتبة الخانجي")
    e = build_tables([r])["editions"][0]
    assert (e["title_clean_ar"], e["title_note_ar"], e["publisher_ar"]) == ("الحماسة البصرية", None, "مكتبة الخانجي")
    assert e["label_ar"] == "الحماسة البصرية - البصري - ت عادل سليمان جمال - مكتبة الخانجي"
    r = rec("b", "سمط اللآلي (ت - الميمني)", "البكري", editors=[Editor("عبد العزيز الميمني")])
    e = build_tables([r])["editions"][0]
    assert (e["title_clean_ar"], e["title_note_ar"]) == ("سمط اللآلي", None)


def test_a_publisher_mark_fills_an_empty_publisher_with_its_source():
    r = rec("a", "النفح الشذي شرح جامع الترمذي ط الصميعي", "ابن سيد الناس", sources={"year_ah": "catalog_record"}, year_ah=1428)
    e = build_tables([r])["editions"][0]
    assert (e["title_clean_ar"], e["publisher_ar"], e["title_note_ar"]) == ("النفح الشذي شرح جامع الترمذي", "الصميعي", None)
    assert json.loads(e["field_sources"]) == {"publisher_ar": "file_label", "year_ah": "catalog_record"}
    assert e["label_ar"] == "النفح الشذي شرح جامع الترمذي - ابن سيد الناس - الصميعي"
    r.title_source = "user"
    assert json.loads(build_tables([r])["editions"][0]["field_sources"])["publisher_ar"] == "user"


def test_a_mark_that_disagrees_with_the_row_is_kept_as_a_remark():
    r = rec(
        "a",
        "صحيح سنن أبي داود ط غراس (الأم)",
        "الألباني",
        publisher="مكتبة المعارف",
        editors=[Editor("زهير الشاويش")],
        sources={"publisher": "catalog_record"},
    )
    e = build_tables([r])["editions"][0]
    assert (e["title_clean_ar"], e["publisher_ar"], e["title_note_ar"]) == ("صحيح سنن أبي داود", "مكتبة المعارف", "الأم;ط غراس")
    assert json.loads(e["field_sources"]) == {"publisher_ar": "catalog_record"}
    r = rec("b", "الإخنائية ت زهوي", "ابن تيمية", editors=[Editor("أحمد بن مونس العنزي")])
    assert build_tables([r])["editions"][0]["title_note_ar"] == "ت زهوي"
    r = rec("c", "الإخنائية ت زهوي", "ابن تيمية")  # a surname alone is not an editor's name: a remark, not a credit
    e = build_tables([r])["editions"][0]
    assert (e["editors_ar"], e["title_note_ar"]) == (None, "ت زهوي")


def test_marks_never_change_an_id():
    plain = build_tables([rec("k", "الحماسة البصرية", "البصري", publisher="مكتبة الخانجي")])
    marked = build_tables([rec("k", "الحماسة البصرية (ط. الخانجي)", "البصري", publisher="مكتبة الخانجي")])
    for table, col in [("works", "work_id"), ("editions", "edition_id"), ("authors", "author_id")]:
        assert plain[table][0][col] == marked[table][0][col]


def test_name_forms_of_one_person_share_a_canonical_author():
    t = build_tables(
        [
            rec("a", "صيد الخاطر", "ابن الجوزي", death_ah=597, death_source="shamela_book", shamela_author_id=51),
            rec("b", "تلبيس إبليس", "ابن الجوزي", death_ah=597, death_source="shamela_book", shamela_author_id=51),
            rec("c", "المنتظم", "أبو الفرج ابن الجوزي", shamela_author_id=51),
            rec("d", "زاد المعاد", "ابن قيم الجوزية", death_ah=751, death_source="shamela_book", shamela_author_id=9),
            rec("e", "المعجم الصغير", "الطبراني", death_ah=360, death_source="shamela_book", shamela_author_id=232),
            rec("f", "جزء فيه أحاديث", "الطبراني وابن مردويه", death_ah=360, death_source="shamela_book", shamela_author_id=232),
            rec("g", "الفتاوى", "ولي الله الدهلوي", death_ah=1176, death_source="shamela_book", shamela_author_id=1349),
            rec("h", "حجة الله البالغة", "شاه ولي الله الدهلوي", death_ah=1176, death_source="shamela_book", shamela_author_id=1349),
        ]
    )
    assert check(t) == []
    a = {a["name_ar"]: a for a in t["authors"]}
    head = a["ابن الجوزي"]
    assert head["canonical_author_id"] == head["author_id"]  # dated, most works
    assert a["أبو الفرج ابن الجوزي"]["canonical_author_id"] == head["author_id"]
    assert a["أبو الفرج ابن الجوزي"]["author_id"] != head["author_id"]  # the row and its id stay
    assert a["ابن قيم الجوزية"]["canonical_author_id"] == a["ابن قيم الجوزية"]["author_id"]
    # «الطبراني وابن مردويه» names two people: the identifier of the first does not make them one
    assert a["الطبراني وابن مردويه"]["canonical_author_id"] == a["الطبراني وابن مردويه"]["author_id"]
    # «ولي» is a name, not «و» + a second person
    assert a["شاه ولي الله الدهلوي"]["canonical_author_id"] == a["ولي الله الدهلوي"]["canonical_author_id"]
    assert len({x["canonical_author_id"] for x in t["authors"]}) == 5


def test_one_identifier_with_two_death_years_is_left_apart():
    t = build_tables(
        [
            rec("a", "كتاب أ", "السخاوي", death_ah=902, death_source="shamela_book", shamela_author_id=34),
            rec("b", "كتاب ب", "شمس الدين السخاوي", death_ah=903, death_source="shamela_book", shamela_author_id=34),
        ]
    )
    assert all(a["canonical_author_id"] == a["author_id"] for a in t["authors"])


def test_a_death_year_whose_source_names_another_author_is_low():
    t = build_tables(
        [
            rec("a", "طبقات الفقهاء الشافعية", "النووي", death_ah=643, death_source="shamela_book", death_name_matched=False),
            rec("b", "الأذكار", "الآجري", death_ah=360, death_source="shamela_book"),
            rec("c", "الشريعة", "الآجري", death_ah=360, death_source="shamela_book", death_name_matched=False),
        ]
    )
    a = {a["name_ar"]: a for a in t["authors"]}
    assert a["النووي"]["death_confidence"] == "low"
    assert a["الآجري"]["death_confidence"] == "high"  # one witness whose name matches is enough
    assert check(t) == []
