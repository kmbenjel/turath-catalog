import copy

import pytest

from turath_catalog import load
from turath_catalog.validate import check


@pytest.fixture
def t(sample_dir):
    return load(sample_dir)


def test_sample_is_clean(t):
    assert check(t) == []


def _first(t, table):
    return t[table][0]


def test_duplicate_id(t):
    t["works"].append(copy.deepcopy(t["works"][0]))
    assert any("duplicate keys" in e for e in check(t))


def test_orphan_edition(t):
    _first(t, "editions")["work_id"] = "w_0000000000"
    errs = check(t)
    assert any("editions.work_id" in e and "missing from works" in e for e in errs)


def test_work_without_edition(t):
    w = copy.deepcopy(t["works"][0])
    w["work_id"] = "w_ffffffffff"
    t["works"].append(w)
    assert any("has no edition" in e for e in check(t))


def test_death_year_sanity(t):
    a = next(a for a in t["authors"] if a["death_ah"])
    a["death_ce_from"] += 5
    assert any("death_ce" in e for e in check(t))
    a["death_ah"] = 2000
    assert any("outside" in e for e in check(t))


def test_century_mismatch(t):
    a = next(a for a in t["authors"] if a["death_ah"])
    a["century_ah"] = 1 if a["century_ah"] != 1 else 2
    assert any("century" in e for e in check(t))


def test_printed_before_death(t):
    w = next(w for w in t["works"] if w["author_id"])
    a = next(a for a in t["authors"] if a["author_id"] == w["author_id"])
    if not a["death_ah"]:
        pytest.skip("sample author without death year")
    e = next(e for e in t["editions"] if e["work_id"] == w["work_id"] and e["kind"] != "manuscript")
    a.update(death_ah=1100, death_ce_from=1688, death_ce_to=1689, century_ah=11)
    e.update(year_ah=1050, year_ce=None)
    errs = check(t)
    assert any("before its author died" in x for x in errs) or any("outside" in x for x in errs)


@pytest.mark.parametrize(
    "value, what",
    [
        ("Books/التفسير/جامع البيان.pdf", "file path"),
        ("/home/someone/books", "file path"),
        ("someone@example.com", "e-mail"),
        ("192.168.1.10", "IP address"),
        ("https://example.org/x", "URL"),
        ("owner: ask", "workspace word"),
        ("password=x", "credential"),
        ("التفسير/جامع البيان", "a path?"),
    ],
)
def test_leaks_are_caught(t, value, what):
    _first(t, "editions")["publisher_ar"] = value
    assert any(what in e for e in check(t))


def test_personal_name_is_caught(t):
    _first(t, "editions")["publisher_ar"] = "دار فلان الفلاني"
    assert any("personal name" in e for e in check(t, ("فلان الفلاني",)))


def test_schema_errors(t):
    e = _first(t, "editions")
    e["kind"] = "ebook"
    e["year_ah"] = "1420"
    e["ext_ids"] = "goodreads:1"
    e["field_sources"] = "{bad"
    e["surprise"] = 1
    errs = "\n".join(check(t))
    for needle in ("not in", "is not integer", "unknown schemes", "not JSON", "unknown columns"):
        assert needle in errs


def test_counts_must_agree(t):
    _first(t, "works")["n_editions"] += 1
    _first(t, "authors")["n_works"] += 1
    _first(t, "editions")["size_bytes"] += 1
    errs = "\n".join(check(t))
    assert "n_editions" in errs and "n_works" in errs and "size_bytes" in errs


def test_a_release_built_before_a_column_existed_is_still_valid(t):
    old = {
        "works": ("title_clean_ar",),
        "editions": ("title_clean_ar", "alt_titles_ar", "title_note_ar"),
        "authors": ("canonical_author_id",),
    }
    for table, cols in old.items():
        for r in t[table]:
            for c in cols:
                r.pop(c)
    assert check(t) == []
    t["works"][0]["title_clean_ar"] = None  # once a column is there, a required value must be too
    t["works"][1]["title_clean_ar"] = t["works"][1]["title_ar"]
    assert any("works[0].title_clean_ar: required value missing" in e for e in check(t))


def test_clean_title_must_be_the_title_alone(t):
    _first(t, "editions")["title_clean_ar"] = "الجامع لأحكام القرآن = تفسير القرطبي"
    t["works"][0]["title_clean_ar"] = "الحماسة البصرية (ط. الخانجي)"
    t["works"][1]["alt_titles_ar"] = t["works"][1]["title_clean_ar"]
    errs = check(t)
    assert sum("still carries «=» or a bracket" in e for e in errs) == 2
    assert any("lists its own title among alt_titles_ar" in e for e in errs)


def test_canonical_author_must_exist_and_be_its_own_canonical(t):
    a, b, c = t["authors"][:3]
    a["canonical_author_id"] = "a_0000000000"
    b["canonical_author_id"] = c["author_id"]
    c["canonical_author_id"] = t["authors"][3]["author_id"]
    errs = check(t)
    assert any("authors.canonical_author_id" in e and "missing from authors" in e for e in errs)
    assert any(f"{b['author_id']} points to {c['author_id']}, which is not its own canonical row" in e for e in errs)
