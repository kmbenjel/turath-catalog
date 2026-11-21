"""The intermediate record every source adapter produces: one printed edition (or manuscript copy)
of one work, with the source of each value. `build.normalise` turns a list of these into tables."""

from __future__ import annotations

from dataclasses import dataclass, field

# Where a value came from. Ordered from strongest to weakest evidence.
SOURCES = {
    "title_page": "read by eye from the title page of the scan",
    "imprint_page": "read from the imprint (colophon / copyright) page of the scan",
    "catalog_record": "a library catalog record linked to the scan by its exact file size (Waqfeya)",
    "shamela_card": "the Shamela book card of the same edition (same editor, or same publisher when no editor)",
    "shamela_author": "the Shamela author record of a Shamela book matched to this work (names only)",
    "file_label": "the library's own label for the file, composed from the evidence above",
    "user": "supplied in the user's own catalog file",
}

CONFIDENCE = ("high", "medium", "low")


@dataclass
class Editor:
    name: str
    role: str = "editor"  # editor | compiler | commentator | corrector | introducer | translator | supervisor
    role_ar: str = ""


@dataclass
class Volume:
    label: str
    size_bytes: int


@dataclass
class EditionRecord:
    """One edition as a source adapter sees it. Only `key`, `title` and `category_ar` are required."""

    key: str  # adapter-private, never exported (may be a path)
    title: str
    category_ar: str
    author: str = ""
    label: str = ""
    work_group: str = ""  # adapter's own grouping key for editions of one work, if any
    editors: list[Editor] = field(default_factory=list)
    publisher: str = ""
    place: str = ""
    year_ah: int | None = None
    year_ce: int | None = None
    edition_number: int | None = None
    edition_statement: str = ""
    kind: str = "printed"  # printed | lithograph | manuscript | thesis | offprint
    volumes: int | None = None
    pages: int | None = None
    files: list[Volume] = field(default_factory=list)
    death_ah: int | None = None
    death_source: str = ""
    death_name_matched: bool = True  # False: the year's source names its author differently from `author`
    century_ah: int | None = None  # the author's century when no death year is known
    author_full_name: str = ""
    shamela_author_id: int | None = None
    shamela_work_ids: list[tuple[int, str]] = field(default_factory=list)  # (book id, confidence)
    shamela_edition_id: int | None = None  # the Shamela book whose card describes THIS edition
    waqfeya_ids: list[str] = field(default_factory=list)
    title_page_read: bool = False
    sources: dict[str, str] = field(default_factory=dict)  # field -> SOURCES key
    title_source: str = "file_label"  # SOURCES key of the title cell (an edition mark in it may fill the publisher)
    holding_library: str = ""  # manuscripts only
    shelfmark: str = ""
    holding_confidence: str = ""
    printed_key: str = ""  # manuscripts: key of a printed edition of the same work in the same input
