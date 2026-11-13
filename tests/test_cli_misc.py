import json

from turath_catalog import load
from turath_catalog.charts import draw_all
from turath_catalog.cli import main
from turath_catalog.compare import coverage
from turath_catalog.sources.usercsv import read_user_csv
from turath_catalog.stats import cut_sample, summary
from turath_catalog.validate import check

USER_CSV = """title,author,author_death_ah,category,editors,publisher,place,year_ah,year_ce,edition_number,volumes,pages,kind,sizes,verified
الرسالة,الشافعي,204,أصول الفقه,editor:أحمد محمد شاكر,مصطفى البابي الحلبي,القاهرة,1358,1940,1,1,600,printed,1000;2000,yes
الرسالة,الشافعي,204,أصول الفقه,,دار الكتب العلمية,بيروت,,,,,,,,
,بلا عنوان,,,,,,,,,,,,,
مسند الشافعي,الشافعي,204,تصنيف غير معروف,commentator:فلان,,,,,,,,manuscript,,
"""


def test_user_csv_builds_the_same_tables(tmp_path, capsys):
    p = tmp_path / "mine.csv"
    p.write_text(USER_CSV, encoding="utf-8")
    recs, rep = read_user_csv(p)
    assert len(recs) == 3 and rep["excluded_rows"] == {"no title": 1}
    out = tmp_path / "out"
    card = tmp_path / "card.md"
    card.write_text("# card", encoding="utf-8")
    args = ["build", "--csv", str(p), "--out", str(out), "--offline", "--cache", str(tmp_path / "cache"), "--include", f"{card}:README.md"]
    assert main(args) == 0
    assert (out / "README.md").read_text(encoding="utf-8") == "# card"
    t = load(out)
    assert check(t) == []
    risala = [w for w in t["works"] if w["title_ar"] == "الرسالة"]
    assert len(risala) == 1 and risala[0]["n_editions"] == 2
    (a,) = [a for a in t["authors"] if a["name_ar"] == "الشافعي"]
    assert (a["death_ah"], a["death_ce_from"], a["death_ce_to"], a["death_source"]) == (204, 819, 820, "user")
    roles = {x["role"] for x in t["edition_editors"]}
    assert roles == {"editor", "commentator"}
    assert {w["category_ar"] for w in t["works"]} == {"أصول الفقه", "كتب عامة"}
    report = json.loads((out / "build-report.json").read_text(encoding="utf-8"))
    assert report["rows"]["editions"] == 3
    assert (out / "SHA256SUMS").read_text().count("\n") >= 20
    assert main(["validate", str(out)]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_info_validate_schema_sample(sample_dir, tmp_path, capsys):
    assert main(["info", str(sample_dir)]) == 0
    assert "works" in capsys.readouterr().out
    assert main(["validate", "sample"]) == 0
    assert main(["validate", str(tmp_path / "nope")]) == 2
    assert main(["schema", "--out", str(tmp_path / "s"), "--dictionary", str(tmp_path / "dd.md")]) == 0
    assert (tmp_path / "s" / "works.schema.json").exists() and "## `works`" in (tmp_path / "dd.md").read_text()
    assert main(["sample", str(sample_dir), "--out", str(tmp_path / "smp"), "--works", "20"]) == 0
    assert main(["validate", str(tmp_path / "smp")]) == 0


def test_validate_reports_failure(sample_dir, tmp_path, capsys):
    t = load(sample_dir)
    t["editions"][0]["publisher_ar"] = "x@y.org"
    from turath_catalog.export import write_tables

    write_tables(t, tmp_path, ("jsonl",))
    assert main(["validate", str(tmp_path)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_sample_cut_and_summary(sample_dir):
    t = load(sample_dir)
    small = cut_sample(t, 30)
    assert check(small) == []
    assert "editions" in summary(small)


def test_charts(sample_dir, tmp_path):
    paths = draw_all(load(sample_dir), tmp_path)
    assert [p.name for p in paths] == [
        "works-by-century.png",
        "works-by-category.png",
        "editions-per-work.png",
        "completeness.png",
        "card.webp",
    ]
    from PIL import Image

    assert Image.open(tmp_path / "card.webp").size == (1200, 750)


def test_compare_without_cache(sample_dir, tmp_path, capsys):
    res = coverage(load(sample_dir), tmp_path)
    assert set(res) == {"release", "shamela"}
    assert res["shamela"]["works_linked"] + res["shamela"]["works_not_linked"] == res["release"]["works"]
    assert main(["compare", str(sample_dir), "--cache", str(tmp_path), "--out", str(tmp_path / "c.json")]) == 0


def test_compare_with_cached_sources(sample_dir, tmp_path):
    (tmp_path / "OpenITI_metadata_2025-1-9.tsv").write_text(
        "version_uri\tlanguage\tdate\tauthor_ar\tbook\ttitle_ar\ted_info\nX.Y.Z-ara1\tara\t0676\tالنووي\t0676Nawawi.X\tX\tت فلان\n",
        encoding="utf-8",
    )
    (tmp_path / "wikidata-shamela_author.csv").write_text(
        "item,v,d\nhttp://www.wikidata.org/entity/Q1,35,1277-01-01T00:00:00Z\n", encoding="utf-8"
    )
    (tmp_path / "wikidata-shamela_book.csv").write_text(
        "item,v,work\nhttp://www.wikidata.org/entity/Q2,7,http://www.wikidata.org/entity/Q3\n", encoding="utf-8"
    )
    (tmp_path / "wikidata-openiti_author.csv").write_text("item,v,d\n", encoding="utf-8")
    res = coverage(load(sample_dir), tmp_path)
    assert res["openiti"]["books"] == 1 and res["wikidata"]["items_with_shamela_book_id"] == 1
