---
license: cc-by-4.0
language:
- ar
- en
pretty_name: turath-catalog — classical Arabic works and their printed editions
size_categories:
- 10K<n<100K
source_datasets:
- original
annotations_creators:
- expert-generated
language_creators:
- found
multilinguality:
- monolingual
task_categories:
- other
tags:
- bibliography
- library-science
- digital-humanities
- islamic-studies
- arabic
- turath
- manuscripts
- hijri
- openiti
- wikidata
- linked-data
configs:
- config_name: editions
  default: true
  data_files: parquet/editions.parquet
- config_name: works
  data_files: parquet/works.parquet
- config_name: authors
  data_files: parquet/authors.parquet
- config_name: editors
  data_files: parquet/editors.parquet
- config_name: edition_editors
  data_files: parquet/edition_editors.parquet
- config_name: manuscripts
  data_files: parquet/manuscripts.parquet
- config_name: edition_files
  data_files: parquet/edition_files.parquet
- config_name: categories
  data_files: parquet/categories.parquet
---

# turath-catalog

An open bibliographic dataset of **classical Arabic works and their printed editions**: 5,134 works,
5,626 editions (editor, publisher, place, year, edition number, volumes, pages), 2,451 authors under 2,643 name forms
(1,239 with a sourced death year in Hijri, with its Gregorian range), 2,265 editors with 3,999 credits, and 31
manuscript copies with their holding library. Works link to OpenITI (1,683) and Shamela (2,313);
authors to Wikidata (842) and OpenITI (875). Every value names its source and every edition carries a
confidence level. **Metadata only**: no scans and no text.

- **Curated by:** Khalid Benjelloun
- **Language(s):** Arabic (values), English (column names, category names, documentation)
- **License:** CC BY 4.0 (data); the build and validation code is MIT
- **Repository:** https://github.com/kmbenjel/turath-catalog
- **Arabic documentation:** https://warraq.benjelloun.dev/turath-catalog/

## Uses

```python
from datasets import load_dataset

editions = load_dataset("kmbenjel/turath-catalog", "editions", split="train")
works = load_dataset("kmbenjel/turath-catalog", "works", split="train")
```

**Direct uses.** Citing and choosing printed editions; telling two printings of a text apart;
authority work on editors and publishers; matching a library's holdings or scans against a known
edition (exact file sizes in `edition_files`); entity linking between Shamela, OpenITI and Wikidata;
Arabic NLP tasks around bibliographic text: name normalisation, Hijri date handling, title and
author matching, edition statement parsing; collection analysis by century, subject and editor.

**Out-of-scope uses.** It is not a census of Arabic printing: it covers one large private library,
whose choices shape it (see *Bias*). It holds no text, so it cannot serve text mining of the works.
Absence of an edition here says nothing about its existence.

## Dataset structure

Eight tables, joined by stable ids. Full column documentation: `docs/data-dictionary.md` in the
repository; a JSON Schema per table in `schema/`.

| config | rows | key | one row per |
|---|---:|---|---|
| `editions` | 5,626 | `edition_id` | printing, lithograph, thesis, offprint or manuscript copy |
| `works` | 5,134 | `work_id` | text by an author |
| `authors` | 2,643 | `author_id` | name form of an author (one name with two death years is two people; the forms of one person share `canonical_author_id`: 2,451 people) |
| `editors` | 2,265 | `person_id` | person or body credited on an edition |
| `edition_editors` | 3,999 | — | credit: edition × person × role |
| `manuscripts` | 31 | `manuscript_id` | manuscript copy, with holding library |
| `edition_files` | 15,079 | — | scan file of an edition: volume label, exact byte size |
| `categories` | 40 | `category_ar` | subject category (al-Maktaba al-Shamila's 40), with English name |

Ids: `work_id = "w_" + sha1(title_key|author_key)[:10]` (the recipe shared with the
`turath-match` and `arabic-bib` tools); editions, authors, editors and manuscripts use the same
`<letter>_<10 hex>` form. A release only appends columns, at the end of a table, and keeps the id recipes.
Multi-valued cells are `;`-separated; `ext_ids` are `scheme:id` pairs
(`shamela`, `shamela_author`, `waqfeya`); `field_sources` is a JSON object from column to source.

Example row (`editions`, abridged):

```json
{"edition_id": "e_f5c4f8c472", "work_id": "w_92c7dcdccd", "title_ar": "آداب الفتوى والمفتي والمستفتي",
 "title_clean_ar": "آداب الفتوى والمفتي والمستفتي", "alt_titles_ar": null, "title_note_ar": null,
 "kind": "printed", "editors_ar": "بسام عبد الوهاب الجابي", "publisher_ar": "دار الفكر", "place_ar": "دمشق",
 "year_ah": 1408, "year_ce": 1988, "edition_number": 1, "volumes": 1, "pages": 96, "title_page_read": true,
 "ext_ids": "waqfeya:66a88e0187c55ca3e12f3acb", "confidence": "high",
 "field_sources": "{\"editors_ar\": \"title_page\", \"publisher_ar\": \"title_page\", \"year_ah\": \"catalog_record\", ...}"}
```

**Titles.** `title_ar` keeps the title cell as the library gives it; `title_clean_ar` is the title alone.
What else the cell carried has its own column: another title of the work in `alt_titles_ar`
(«الجامع لأحكام القرآن = تفسير القرطبي»), a remark in `title_note_ar` («(من النحل إلى الصافات)»), and an
edition mark («ط. الخانجي», «ت - الميمني») is checked against the row: dropped when `publisher_ar` or
`editors_ar` already says it, used to fill an empty `publisher_ar` (source `file_label`), kept as a remark
when the row says otherwise. 103 edition titles carry such a part; ids hash the title as given.

**People.** `authors` has one row per name form. Forms that carry the same Shamela author id and no
conflicting death year share a `canonical_author_id` (192 forms folded, 2,451 people); group by it to
count people.

## Dataset creation

### Curation rationale

Open catalogs of Arabic heritage describe digital texts (OpenITI), linked entities (Wikidata) or a
single digitised edition per book (Shamela). The printed edition, the unit a scholar cites, is rarely a
row anywhere open. This dataset makes it one, with the evidence for each value.

### Source data

The editions are those of a 16,700-volume library of Arabic PDF scans assembled and checked by the
curator. For each edition, values come from, in order of strength:

| source (`field_sources`) | what it is | editions using it |
|---|---|---|
| `title_page` | the title page of the scan, read by eye | 2,230 read in full |
| `imprint_page` | the imprint or copyright page of the scan | |
| `catalog_record` | a [Waqfeya](https://waqfeya.net) record for the same file, linked by its exact byte size | |
| `shamela_card` | the [al-Maktaba al-Shamila](https://shamela.ws) card of the same edition (same editor, or same publisher) | 446 |
| `shamela_author` | names from the Shamela author record of a matched work | |
| `file_label` | the library's own label, composed from the above | |

Death years come from the Shamela author record of a Shamela book matched to the work
(`shamela_book`, 1,173 authors) or from agreeing witnesses for the same name (`author_table`, 66).
Only facts were taken from outside catalogs (names, titles, years, counts, identifiers); their
descriptions, biographies and blurbs were not.

**Links.** OpenITI book URIs (release 2025.1.9) need the same death year, the same folded title
(`high`) or a 3-word title prefix (`medium`), an agreeing author name and a single candidate. Wikidata
authors come through Wikidata's Shamela author id (P12435) with the item's death year inside the Hijri
year's Gregorian range (86 candidates were rejected by that check); editions through Shamela book ids
(P12239) and works through their "edition of" (P629). OpenITI is used as a link target only; its
metadata (CC BY-NC-SA 4.0) is not copied.

### Annotations and confidence

`editions.confidence` is `high` when the title page was read by eye (2,230), `medium` when the values come
from a size-linked catalog record or the same-edition Shamela card (3,021), `low` when only the library
label supports them (375). `authors.death_confidence` is `high` when two witnesses agree or the year
falls in the century a catalog record gives (932), `medium` for a single witness (263), `low` when the year
is that of the author of a matched Shamela book whose name could not be matched to the row's name, so
that the row may name that book's commentator, transmitter or editor (44).

### What was excluded

151 editions whose sources disagree and 116 whose title or author is under review; 125 titles not in
Arabic script. Values that fail a check are dropped rather than kept: 166 death years where two people
may share a name, 48 death years outside the century given by a catalog record, 32 Hijri/Gregorian
year pairs that disagree, 85 "editor" values that are not a person's name, 3 publisher values from a file
label that repeat the author's name. File names, paths, download
links, OCR text, notes and comments are never part of a record. The counts of each build are in
`build-report.json`.

## Personal and sensitive information

The persons named are authors, editors, translators and other contributors as printed on published
books, i.e. public bibliographic data; many are historical. The dataset holds no contact details, no
data about readers or owners, and no information about the library itself beyond its edition list.
A validator rejects any release containing paths, e-mail addresses, URLs, IP addresses or credential
words.

## Bias, risks and limitations

- **Collection bias.** One library's choices: classical works first (2,725 of the 3,228 works with a
  dated author are by authors who died by 1300 AH), with major modern studies. Subjects follow the 40
  categories of al-Maktaba al-Shamila, which name the four Sunni schools of law and no other tradition.
  Most editions with a Gregorian year were printed 1975–2024 (3,472 of 3,818); 344 are older.
- **Edition coverage.** 63% of editions name an editor, 79% a publisher, 75% a year, 31% a place.
- **Name variants.** Editors are merged only when one form is contained in a unique fuller form with the
  same first and last name; some persons still appear under two forms. Authors are folded only by a shared
  catalog identifier (`canonical_author_id`); an author without one may appear under two forms.
- **Copies.** A row of `editions` is a scanned copy: two scans of one printing are two rows with the same
  editor, publisher and year (16 such pairs).
- **Links are lower bounds.** A work not linked to OpenITI or Wikidata may exist there under another
  title or without the identifiers used here.
- **Dates.** Hijri→Gregorian ranges use the tabular Islamic calendar, which can differ from observed
  dates by a day or two at year boundaries.

## Citation

```bibtex
@dataset{benjelloun_turath_catalog_2026,
  author    = {Benjelloun, Khalid},
  title     = {turath-catalog: classical Arabic works and their printed editions},
  year      = {2026},
  version   = {0.2.0},
  license   = {CC-BY-4.0},
  url       = {https://github.com/kmbenjel/turath-catalog}
}
```

## Dataset card contact

Issues and corrections: https://github.com/kmbenjel/turath-catalog/issues
