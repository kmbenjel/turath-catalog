"""The dataset's tables and columns: the single source for the JSON Schemas, the data dictionary,
the Parquet types and the validator."""

from __future__ import annotations

from dataclasses import dataclass

CONF = ["high", "medium", "low"]
ROLES = ["editor", "compiler", "commentator", "corrector", "introducer", "translator", "supervisor"]
ROLE_AR = {
    "editor": "تحقيق",
    "compiler": "جمع",
    "commentator": "شرح",
    "corrector": "ضبط وتصحيح",
    "introducer": "تقديم",
    "translator": "ترجمة",
    "supervisor": "إشراف",
}
KINDS = ["printed", "lithograph", "manuscript", "thesis", "offprint"]
DEATH_SOURCES = ["shamela_book", "author_table", "user"]
FIELD_SOURCES = ["title_page", "imprint_page", "catalog_record", "shamela_card", "shamela_author", "file_label", "user"]


@dataclass(frozen=True)
class Col:
    name: str
    type: str  # string | integer | boolean
    doc: str
    required: bool = False
    enum: tuple[str, ...] | None = None
    pattern: str | None = None
    minimum: int | None = None
    maximum: int | None = None
    example: str = ""


def C(name, type_, doc, **kw):
    if "enum" in kw and kw["enum"] is not None:
        kw["enum"] = tuple(kw["enum"])
    return Col(name, type_, doc, **kw)


ID = {
    "work": r"^w_[0-9a-f]{10}$",
    "edition": r"^e_[0-9a-f]{10}$",
    "author": r"^a_[0-9a-f]{10}$",
    "person": r"^p_[0-9a-f]{10}$",
    "manuscript": r"^m_[0-9a-f]{10}$",
}
EXT_IDS = r"^([a-z_]+:[^;:\s]+)(;[a-z_]+:[^;:\s]+)*$"
OPENITI_BOOK = r"^\d{4}[A-Za-z]+\.[A-Za-z0-9]+$"
OPENITI_AUTHOR = r"^\d{4}[A-Za-z]+$"
QID = r"^Q\d+$"

TABLES: dict[str, dict] = {
    "works": {
        "doc": "One row per work (a text by an author), whatever the number of its editions in the dataset.",
        "key": "work_id",
        "cols": [
            C(
                "work_id",
                "string",
                "Stable id: `w_` + first 10 hex digits of sha1(`title_key|author_key`).",
                required=True,
                pattern=ID["work"],
                example="w_5c1f0e2b9a",
            ),
            C(
                "title_ar",
                "string",
                "Title of the work in Arabic, as on the best-attested edition.",
                required=True,
                example="آداب الفتوى والمفتي والمستفتي",
            ),
            C("alt_titles_ar", "string", "Other titles of the work, `;`-separated (titles written «A = B» are split)."),
            C(
                "author_id",
                "string",
                "The work's author (authors.author_id). Empty for anonymous works and collections.",
                pattern=ID["author"],
            ),
            C("author_name_ar", "string", "The author's name as cited (denormalised from authors.name_ar for convenience)."),
            C(
                "category_ar",
                "string",
                "Subject category, one of the 40 categories of al-Maktaba al-Shamila.",
                required=True,
                example="أصول الفقه",
            ),
            C("category_en", "string", "English name of the category.", required=True, example="Principles of jurisprudence"),
            C(
                "openiti_uri",
                "string",
                "OpenITI book URI (2025.1.9 release) of the same work.",
                pattern=OPENITI_BOOK,
                example="0676Nawawi.AdabFatwa",
            ),
            C(
                "openiti_confidence",
                "string",
                "How the OpenITI link was made: `high` = same death year, same title, author name agrees; `medium` = same death year, one title is a prefix of the other (3+ words), author agrees.",
                enum=CONF,
            ),
            C(
                "wikidata_qid",
                "string",
                "Wikidata item of the work, through the Wikidata item of a Shamela edition (P12239 → P629).",
                pattern=QID,
            ),
            C(
                "ext_ids",
                "string",
                "Other catalogs' ids for the work, `;`-separated `scheme:id` (scheme `shamela` = al-Maktaba al-Shamila book id).",
                pattern=EXT_IDS,
                example="shamela:1094",
            ),
            C("n_editions", "integer", "Number of editions of this work in the dataset.", required=True, minimum=1),
            C(
                "confidence",
                "string",
                "Confidence of the work's identity (title and author): the best confidence among its editions.",
                required=True,
                enum=CONF,
            ),
        ],
    },
    "editions": {
        "doc": "One row per edition (a printing, lithograph, thesis or manuscript copy) of a work.",
        "key": "edition_id",
        "cols": [
            C(
                "edition_id",
                "string",
                "Stable id: `e_` + first 10 hex digits of sha1 of the edition's label within its category.",
                required=True,
                pattern=ID["edition"],
            ),
            C("work_id", "string", "The work (works.work_id).", required=True, pattern=ID["work"]),
            C("title_ar", "string", "Title as given on this edition.", required=True),
            C(
                "label_ar",
                "string",
                "Citation form composed from this row's fields: «title - author - ت editors - publisher place» (title_ar without alternative titles, the author's name, editors_ar with their role, publisher_ar, place_ar).",
                required=True,
            ),
            C(
                "kind",
                "string",
                "printed, lithograph, manuscript (a copy of a manuscript), thesis (university thesis) or offprint (a journal article).",
                required=True,
                enum=KINDS,
            ),
            C("editors_ar", "string", "Editors and other contributors, `;`-separated, in order (details in edition_editors)."),
            C("publisher_ar", "string", "Publisher or printing house."),
            C("place_ar", "string", "Place of publication (cities `-`-separated)."),
            C("year_ah", "integer", "Year of this printing, Hijri.", minimum=1100, maximum=1460),
            C("year_ce", "integer", "Year of this printing, Gregorian.", minimum=1700, maximum=2026),
            C("edition_number", "integer", "Edition number (الطبعة الأولى = 1).", minimum=1, maximum=50),
            C("edition_statement_ar", "string", "Edition statement when it is not a plain number (e.g. «طبعة خاصة»)."),
            C(
                "volumes",
                "integer",
                "Number of volumes of the printed set, as the edition or its catalog record gives it.",
                minimum=1,
                maximum=500,
            ),
            C("pages", "integer", "Number of printed pages, as the edition's catalog record gives it.", minimum=1),
            C("n_files", "integer", "Number of scan files (volumes as scanned) in the library.", required=True, minimum=1),
            C(
                "size_bytes",
                "integer",
                "Total size of the scan files in bytes (exact sizes per file in edition_files).",
                required=True,
                minimum=1,
            ),
            C(
                "title_page_read",
                "boolean",
                "True when the title page of this scan was read by eye and the label made from it.",
                required=True,
            ),
            C(
                "wikidata_qid",
                "string",
                "Wikidata item of the same edition (the item that carries this Shamela book id, P12239).",
                pattern=QID,
            ),
            C(
                "ext_ids",
                "string",
                "`;`-separated `scheme:id`: `waqfeya` = waqfeya.net book id of a record for this very scan (linked by exact file size); `shamela` = Shamela book whose card describes this same edition.",
                pattern=EXT_IDS,
            ),
            C("field_sources", "string", "JSON object: column → source of its value (" + ", ".join(FIELD_SOURCES) + ")."),
            C(
                "confidence",
                "string",
                "`high`: title page read by eye; `medium`: values from a size-linked catalog record or the same-edition Shamela card; `low`: from the library's label only.",
                required=True,
                enum=CONF,
            ),
        ],
    },
    "authors": {
        "doc": "One row per author. Two people who share a name form are two rows when their death years differ.",
        "key": "author_id",
        "cols": [
            C(
                "author_id",
                "string",
                "Stable id: `a_` + first 10 hex digits of sha1(`author_key` or `author_key|death_ah`).",
                required=True,
                pattern=ID["author"],
            ),
            C("name_ar", "string", "The name by which the author is cited (shuhra), as on the editions.", required=True, example="النووي"),
            C("full_name_ar", "string", "Full name (ism, nasab, kunya, nisba) when a source gives it."),
            C("full_name_source", "string", "Source of full_name_ar.", enum=FIELD_SOURCES),
            C("death_ah", "integer", "Death year, Hijri.", minimum=1, maximum=1450),
            C("death_ce_from", "integer", "First Gregorian year that the Hijri death year overlaps.", minimum=600, maximum=2030),
            C(
                "death_ce_to",
                "integer",
                "Last Gregorian year that the Hijri death year overlaps (equal to or one more than death_ce_from).",
                minimum=600,
                maximum=2030,
            ),
            C("century_ah", "integer", "Hijri century of death (from death_ah, else from a catalog record).", minimum=1, maximum=15),
            C(
                "death_source",
                "string",
                "`shamela_book`: the Shamela author record of a Shamela book matched to one of the author's works; `author_table`: the same name's year on another of the author's books, or Shamela's author table when name and century agree.",
                enum=DEATH_SOURCES,
            ),
            C(
                "death_confidence",
                "string",
                "`high`: every edition that gives a year agrees and the year is in the recorded century; `medium`: a single witness.",
                enum=CONF,
            ),
            C("n_works", "integer", "Number of the author's works in the dataset.", required=True, minimum=1),
            C("openiti_author_uri", "string", "OpenITI author URI.", pattern=OPENITI_AUTHOR, example="0676Nawawi"),
            C(
                "wikidata_qid",
                "string",
                "Wikidata item of the author, through Wikidata's Shamela author id (P12435), with the death year checked.",
                pattern=QID,
            ),
            C("ext_ids", "string", "`;`-separated `scheme:id` (`shamela_author` = al-Maktaba al-Shamila author id).", pattern=EXT_IDS),
        ],
    },
    "editors": {
        "doc": "One row per person named as editor or contributor of an edition.",
        "key": "person_id",
        "cols": [
            C(
                "person_id",
                "string",
                "Stable id: `p_` + first 10 hex digits of sha1 of the folded name.",
                required=True,
                pattern=ID["person"],
            ),
            C("name_ar", "string", "The fullest form of the name found.", required=True),
            C("name_variants_ar", "string", "Shorter forms merged into this person, `;`-separated."),
            C("n_editions", "integer", "Number of editions the person contributed to.", required=True, minimum=1),
        ],
    },
    "edition_editors": {
        "doc": "Who did what for each edition (many-to-many between editions and editors).",
        "key": None,
        "cols": [
            C("edition_id", "string", "editions.edition_id", required=True, pattern=ID["edition"]),
            C("person_id", "string", "editors.person_id", required=True, pattern=ID["person"]),
            C("role", "string", "Contribution: " + ", ".join(ROLES) + ".", required=True, enum=ROLES),
            C("role_ar", "string", "Contribution in Arabic (تحقيق، شرح، جمع، ضبط وتصحيح، تقديم، ترجمة، إشراف).", required=True),
            C("seq", "integer", "Order of the person on the edition.", required=True, minimum=1),
        ],
    },
    "manuscripts": {
        "doc": "Manuscript copies in the library: where the manuscript itself is kept, as the copy shows it.",
        "key": "manuscript_id",
        "cols": [
            C(
                "manuscript_id",
                "string",
                "Stable id: `m_` + first 10 hex digits of sha1 of the edition id.",
                required=True,
                pattern=ID["manuscript"],
            ),
            C("edition_id", "string", "The copy as an edition row (kind = manuscript).", required=True, pattern=ID["edition"]),
            C("work_id", "string", "works.work_id", required=True, pattern=ID["work"]),
            C("title_ar", "string", "Title.", required=True),
            C("author_id", "string", "authors.author_id", pattern=ID["author"]),
            C(
                "holding_library_ar",
                "string",
                "Library that holds the manuscript (as its stamp, card or ownership note shows). Empty when the copy does not show it.",
            ),
            C("shelfmark", "string", "Shelfmark or number in that library."),
            C(
                "holding_confidence",
                "string",
                "`high`: read in the copy itself; `medium`: from the upload's own description; `low`: probable (the copy suggests it).",
                enum=CONF,
            ),
            C(
                "printed_edition_id",
                "string",
                "A printed edition of the same work in the dataset, when there is one.",
                pattern=ID["edition"],
            ),
        ],
    },
    "edition_files": {
        "doc": "One row per scan file (volume) of an edition: its order and exact size, for matching copies by size. No file names or paths.",
        "key": None,
        "cols": [
            C("edition_id", "string", "editions.edition_id", required=True, pattern=ID["edition"]),
            C("seq", "integer", "Order of the file in the edition.", required=True, minimum=1),
            C("volume_label", "string", "Volume number as labelled (`00` = front matter).", required=True),
            C("size_bytes", "integer", "Exact size of the file in bytes.", required=True, minimum=1),
        ],
    },
    "categories": {
        "doc": "The 40 subject categories (those of al-Maktaba al-Shamila) with English names.",
        "key": "category_ar",
        "cols": [
            C("category_ar", "string", "Category in Arabic.", required=True),
            C("category_en", "string", "Category in English.", required=True),
            C("n_works", "integer", "Works in the category.", required=True, minimum=0),
            C("n_editions", "integer", "Editions in the category.", required=True, minimum=0),
        ],
    },
}

CATEGORY_EN = {
    "أصول الفقه": "Principles of jurisprudence",
    "الأدب": "Literature",
    "الأنساب": "Genealogy",
    "البلاغة": "Rhetoric",
    "البلدان والرحلات": "Geography and travel",
    "التاريخ": "History",
    "التجويد والقراءات": "Quranic recitation and readings",
    "التخريج والأطراف": "Hadith source-tracing and indexes",
    "التراجم والطبقات": "Biographies and generations",
    "التفسير": "Quranic exegesis",
    "الجوامع": "Hadith compendia",
    "الرقائق والآداب والأذكار": "Piety, manners and devotions",
    "السياسة الشرعية والقضاء": "Governance and the judiciary",
    "السيرة النبوية": "Life of the Prophet",
    "الشعر ودواوينه": "Poetry and diwans",
    "الطب": "Medicine",
    "العروض والقوافي": "Prosody and rhyme",
    "العقيدة": "Creed",
    "العلل والسؤلات الحديثية": "Hadith defects and questions",
    "الغريب والمعاجم": "Rare words and dictionaries",
    "الفتاوى": "Fatwas",
    "الفرائض والوصايا": "Inheritance and bequests",
    "الفرق والردود": "Sects and refutations",
    "الفقه الحنبلي": "Hanbali law",
    "الفقه الحنفي": "Hanafi law",
    "الفقه الشافعي": "Shafi'i law",
    "الفقه العام": "Comparative law",
    "الفقه المالكي": "Maliki law",
    "المنطق": "Logic",
    "النحو والصرف": "Grammar and morphology",
    "شروح الحديث": "Hadith commentaries",
    "علوم أخرى": "Other sciences",
    "علوم الحديث": "Hadith sciences",
    "علوم الفقه والقواعد الفقهية": "Legal maxims and theory",
    "علوم القرآن وأصول التفسير": "Quranic sciences",
    "فهارس الكتب والأدلة": "Bibliographies and guides",
    "كتب السنة": "Hadith collections",
    "كتب اللغة": "Arabic language",
    "كتب عامة": "General works",
    "مسائل فقهية": "Legal questions",
}


def columns(table: str) -> list[Col]:
    return TABLES[table]["cols"]


def json_schema(table: str) -> dict:
    """JSON Schema (draft 2020-12) of one row of `table`."""
    props, req = {}, []
    for c in columns(table):
        p: dict = {"description": c.doc}
        p["type"] = c.type if c.required else [c.type, "null"]
        if c.enum:
            p["enum"] = list(c.enum) + ([] if c.required else [None])
        if c.pattern:
            p["pattern"] = c.pattern
        if c.minimum is not None:
            p["minimum"] = c.minimum
        if c.maximum is not None:
            p["maximum"] = c.maximum
        props[c.name] = p
        if c.required:
            req.append(c.name)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://github.com/kmbenjel/turath-catalog/schema/{table}.schema.json",
        "title": f"turath-catalog {table}",
        "description": TABLES[table]["doc"],
        "type": "object",
        "properties": props,
        "required": req,
        "additionalProperties": False,
    }
