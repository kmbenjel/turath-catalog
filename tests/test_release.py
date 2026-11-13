"""Checks that run on a full local release (built with `make release`); skipped when there is none."""

from pathlib import Path

import pytest

from turath_catalog import load
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
