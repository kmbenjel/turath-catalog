"""Checks that run on a full local release (built with `make release`); skipped when there is none."""

import json
from pathlib import Path

import pytest

from turath_catalog import __version__, load
from turath_catalog.validate import check

ROOT = Path(__file__).resolve().parents[1]
RELEASES = sorted((ROOT / "releases").glob("turath-catalog-*/jsonl"))
CURATOR = ("Benjelloun", "بن جلون", "بنجلون")


def test_sample_has_no_personal_data():
    assert check(load("sample"), CURATOR) == []


@pytest.mark.skipif(not RELEASES, reason="no local release")
def test_full_release_is_clean():
    t = load(RELEASES[-1].parent)
    assert check(t, CURATOR) == []
    assert len(t["works"]) > 1000 and len(t["editions"]) >= len(t["works"])
    sums = (RELEASES[-1].parent / "SHA256SUMS").read_text()
    assert "parquet/editions.parquet" in sums and "csv/works.csv" in sums


@pytest.mark.skipif(not RELEASES, reason="no local release")
def test_docs_quote_the_numbers_of_the_release():
    """Every headline figure in the README, the dataset card and the Arabic docs is re-measured here from the
    release itself and from the two audit files (`make bench quality`), so the prose cannot drift from the data."""
    rel = RELEASES[-1].parent
    if rel.name != f"turath-catalog-{__version__}":
        pytest.skip("the local release is not the version the docs describe")
    t = load(rel)
    report = json.loads((rel / "build-report.json").read_text(encoding="utf-8"))
    bench = json.loads((ROOT / "bench/results.json").read_text(encoding="utf-8"))
    quality = json.loads((ROOT / "bench/quality.json").read_text(encoding="utf-8"))
    assert quality["release"] == rel.name and bench["release"]["works"] == len(t["works"])
    eds, authors, works = t["editions"], t["authors"], t["works"]
    dropped = report["adapter"]["dropped_values"]
    oi, dq, dy = bench["openiti"], quality["duplicates"], quality["death_years"]
    everywhere = ("README.md", "hf/README.md", "docs/ar/index.md")
    figures = {
        "works": (len(works), everywhere),
        "editions": (len(eds), everywhere),
        "author name forms": (len(authors), everywhere),
        "people": (dq["people_by_canonical_author_id"], everywhere + ("docs/provenance.md", "docs/ar/guides/sources.md")),
        "name forms folded": (
            dq["author_rows_folded_into_another"],
            ("README.md", "hf/README.md", "docs/provenance.md", "docs/ar/guides/sources.md"),
        ),
        "dated authors": (sum(1 for a in authors if a["death_ah"]), everywhere),
        "editors": (len(t["editors"]), everywhere),
        "credits": (len(t["edition_editors"]), ("README.md", "hf/README.md")),
        "files": (len(t["edition_files"]), everywhere),
        "OpenITI works": (sum(1 for w in works if w["openiti_uri"]), ("README.md", "hf/README.md")),
        "Wikidata authors": (sum(1 for a in authors if a["wikidata_qid"]), ("README.md", "hf/README.md", "docs/ar/why.md")),
        "Shamela works": (sum(1 for w in works if "shamela:" in (w["ext_ids"] or "")), ("README.md", "hf/README.md")),
        "works with several editions": (sum(1 for w in works if w["n_editions"] > 1), ("README.md", "docs/ar/why.md")),
        "title pages read": (
            sum(1 for e in eds if e["confidence"] == "high"),
            ("README.md", "hf/README.md", "docs/provenance.md", "docs/ar/why.md"),
        ),
        "medium editions": (sum(1 for e in eds if e["confidence"] == "medium"), ("README.md", "hf/README.md", "docs/provenance.md")),
        "low editions": (sum(1 for e in eds if e["confidence"] == "low"), ("README.md", "hf/README.md", "docs/provenance.md")),
        "titles with a part": (
            quality["titles"]["editions_title_differs_from_clean"],
            ("README.md", "hf/README.md", "docs/provenance.md", "docs/ar/guides/sources.md"),
        ),
        "death high": (dy["by_confidence"]["high"], ("hf/README.md", "docs/provenance.md", "docs/ar/guides/sources.md")),
        "death medium": (dy["by_confidence"]["medium"], ("hf/README.md", "docs/provenance.md", "docs/ar/guides/sources.md")),
        "death low": (dy["by_confidence"]["low"], ("hf/README.md", "docs/provenance.md", "docs/ar/guides/sources.md")),
        "editor values dropped": (
            dropped["editor: not a person's name"],
            ("README.md", "hf/README.md", "docs/provenance.md", "docs/ar/guides/sources.md"),
        ),
        "classical works": (bench["release"]["works_by_authors_died_by_1300_ah"], ("README.md", "hf/README.md", "docs/ar/why.md")),
        "classical works not in OpenITI": (oi["classical_works_not_found"], ("README.md", "docs/ar/why.md")),
        "editor-credited editions of OpenITI works": (oi["our_editions_of_found_works_with_editor"], ("README.md", "docs/ar/why.md")),
        "of which editor absent from OpenITI": (
            oi["our_editions_of_found_works_with_editor"] - oi["of_which_editor_named_in_openiti_ed_info"],
            ("README.md", "docs/ar/why.md"),
        ),
        "works not in Shamela": (bench["shamela"]["works_not_linked"], ("README.md", "docs/ar/why.md")),
        "editions not in Wikidata": (bench["wikidata"]["editions_not_linked"], ("README.md", "docs/ar/why.md")),
    }
    missing = []
    for what, (n, files) in figures.items():
        for f in files:
            if f"{n:,}" not in (ROOT / f).read_text(encoding="utf-8"):
                missing.append(f"{f}: {what} = {n:,}")
    assert not missing, missing
    pct = lambda col: f"{round(100 * sum(1 for e in eds if e[col]) / len(eds))}%"
    for f, cols in {
        "README.md": ("editors_ar", "publisher_ar", "volumes"),
        "hf/README.md": ("editors_ar", "publisher_ar", "place_ar"),
    }.items():
        text = (ROOT / f).read_text(encoding="utf-8")
        assert all(pct(c) in text for c in cols), f
    assert f"turath-catalog-{__version__}/parquet" in (ROOT / "README.md").read_text(encoding="utf-8")
