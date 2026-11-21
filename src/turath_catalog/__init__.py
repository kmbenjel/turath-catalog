"""turath-catalog: an open bibliographic dataset of classical Arabic works and their printed editions,
and the tools that build, validate and load it."""

from __future__ import annotations

from pathlib import Path

__version__ = "0.2.0"
__all__ = ["__version__", "load"]


def load(path: str | Path, table: str | None = None, as_pandas: bool = False):
    """Load a release folder, or the sample shipped inside the package with ``path="sample"``.

    >>> tables = load("releases/turath-catalog-0.2.0")      # dict of table name -> list of rows
    >>> works = load("releases/turath-catalog-0.2.0", "works", as_pandas=True)
    """
    from .export import read_tables

    p = Path(path)
    if str(path) == "sample":
        p = Path(__file__).resolve().parent / "sample"
    tables = read_tables(p)
    if as_pandas:
        import pandas as pd

        tables = {k: pd.DataFrame(v) for k, v in tables.items()}
    return tables[table] if table else tables
