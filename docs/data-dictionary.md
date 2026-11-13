# Data dictionary

Generated from `src/turath_catalog/model.py` (`turath-catalog schema`); do not edit by hand.
Every table ships as CSV (UTF-8, header row, empty cell = null), JSON Lines and Parquet (zstd),
with the same columns in the same order. JSON Schemas for one row of each table are in `schema/`.

Conventions: ids are stable hashes (see each `*_id`); multi-valued text cells are `;`-separated;
`ext_ids` cells are `scheme:id` pairs; years are integers; `confidence` is `high`, `medium` or `low`.

## `works`

One row per work (a text by an author), whatever the number of its editions in the dataset.

| column | type | required | description |
|---|---|---|---|
| `work_id` | string | yes | Stable id: `w_` + first 10 hex digits of sha1(`title_key/author_key`). (e.g. `w_5c1f0e2b9a`) |
| `title_ar` | string | yes | Title of the work in Arabic, as on the best-attested edition. (e.g. `آداب الفتوى والمفتي والمستفتي`) |
| `alt_titles_ar` | string |  | Other titles of the work, `;`-separated (titles written «A = B» are split). |
| `author_id` | string |  | The work's author (authors.author_id). Empty for anonymous works and collections. |
| `author_name_ar` | string |  | The author's name as cited (denormalised from authors.name_ar for convenience). |
| `category_ar` | string | yes | Subject category, one of the 40 categories of al-Maktaba al-Shamila. (e.g. `أصول الفقه`) |
| `category_en` | string | yes | English name of the category. (e.g. `Principles of jurisprudence`) |
| `openiti_uri` | string |  | OpenITI book URI (2025.1.9 release) of the same work. (e.g. `0676Nawawi.AdabFatwa`) |
| `openiti_confidence` | string |  | How the OpenITI link was made: `high` = same death year, same title, author name agrees; `medium` = same death year, one title is a prefix of the other (3+ words), author agrees. (one of `high`, `medium`, `low`) |
| `wikidata_qid` | string |  | Wikidata item of the work, through the Wikidata item of a Shamela edition (P12239 → P629). |
| `ext_ids` | string |  | Other catalogs' ids for the work, `;`-separated `scheme:id` (scheme `shamela` = al-Maktaba al-Shamila book id). (e.g. `shamela:1094`) |
| `n_editions` | integer | yes | Number of editions of this work in the dataset. (range 1..) |
| `confidence` | string | yes | Confidence of the work's identity (title and author): the best confidence among its editions. (one of `high`, `medium`, `low`) |

## `editions`

One row per edition (a printing, lithograph, thesis or manuscript copy) of a work.

| column | type | required | description |
|---|---|---|---|
| `edition_id` | string | yes | Stable id: `e_` + first 10 hex digits of sha1 of the edition's label within its category. |
| `work_id` | string | yes | The work (works.work_id). |
| `title_ar` | string | yes | Title as given on this edition. |
| `label_ar` | string | yes | Composed label «title - author - editor - publisher place», the library's citation form. |
| `kind` | string | yes | printed, lithograph, manuscript (a copy of a manuscript), thesis (university thesis) or offprint (a journal article). (one of `printed`, `lithograph`, `manuscript`, `thesis`, `offprint`) |
| `editors_ar` | string |  | Editors and other contributors, `;`-separated, in order (details in edition_editors). |
| `publisher_ar` | string |  | Publisher or printing house. |
| `place_ar` | string |  | Place of publication (cities `-`-separated). |
| `year_ah` | integer |  | Year of this printing, Hijri. (range 1100..1460) |
| `year_ce` | integer |  | Year of this printing, Gregorian. (range 1700..2026) |
| `edition_number` | integer |  | Edition number (الطبعة الأولى = 1). (range 1..50) |
| `edition_statement_ar` | string |  | Edition statement when it is not a plain number (e.g. «طبعة خاصة»). |
| `volumes` | integer |  | Number of volumes of the printed set, as the edition or its catalog record gives it. (range 1..500) |
| `pages` | integer |  | Number of printed pages, as the edition's catalog record gives it. (range 1..) |
| `n_files` | integer | yes | Number of scan files (volumes as scanned) in the library. (range 1..) |
| `size_bytes` | integer | yes | Total size of the scan files in bytes (exact sizes per file in edition_files). (range 1..) |
| `title_page_read` | boolean | yes | True when the title page of this scan was read by eye and the label made from it. |
| `wikidata_qid` | string |  | Wikidata item of the same edition (the item that carries this Shamela book id, P12239). |
| `ext_ids` | string |  | `;`-separated `scheme:id`: `waqfeya` = waqfeya.net book id of a record for this very scan (linked by exact file size); `shamela` = Shamela book whose card describes this same edition. |
| `field_sources` | string |  | JSON object: column → source of its value (title_page, imprint_page, catalog_record, shamela_card, shamela_author, file_label, user). |
| `confidence` | string | yes | `high`: title page read by eye; `medium`: values from a size-linked catalog record or the same-edition Shamela card; `low`: from the library's label only. (one of `high`, `medium`, `low`) |

## `authors`

One row per author. Two people who share a name form are two rows when their death years differ.

| column | type | required | description |
|---|---|---|---|
| `author_id` | string | yes | Stable id: `a_` + first 10 hex digits of sha1(`author_key` or `author_key/death_ah`). |
| `name_ar` | string | yes | The name by which the author is cited (shuhra), as on the editions. (e.g. `النووي`) |
| `full_name_ar` | string |  | Full name (ism, nasab, kunya, nisba) when a source gives it. |
| `full_name_source` | string |  | Source of full_name_ar. (one of `title_page`, `imprint_page`, `catalog_record`, `shamela_card`, `shamela_author`, `file_label`, `user`) |
| `death_ah` | integer |  | Death year, Hijri. (range 1..1450) |
| `death_ce_from` | integer |  | First Gregorian year that the Hijri death year overlaps. (range 600..2030) |
| `death_ce_to` | integer |  | Last Gregorian year that the Hijri death year overlaps (equal to or one more than death_ce_from). (range 600..2030) |
| `century_ah` | integer |  | Hijri century of death (from death_ah, else from a catalog record). (range 1..15) |
| `death_source` | string |  | `shamela_book`: the Shamela author record of a Shamela book matched to one of the author's works; `author_table`: the same name's year on another of the author's books, or Shamela's author table when name and century agree. (one of `shamela_book`, `author_table`, `user`) |
| `death_confidence` | string |  | `high`: every edition that gives a year agrees and the year is in the recorded century; `medium`: a single witness. (one of `high`, `medium`, `low`) |
| `n_works` | integer | yes | Number of the author's works in the dataset. (range 1..) |
| `openiti_author_uri` | string |  | OpenITI author URI. (e.g. `0676Nawawi`) |
| `wikidata_qid` | string |  | Wikidata item of the author, through Wikidata's Shamela author id (P12435), with the death year checked. |
| `ext_ids` | string |  | `;`-separated `scheme:id` (`shamela_author` = al-Maktaba al-Shamila author id). |

## `editors`

One row per person named as editor or contributor of an edition.

| column | type | required | description |
|---|---|---|---|
| `person_id` | string | yes | Stable id: `p_` + first 10 hex digits of sha1 of the folded name. |
| `name_ar` | string | yes | The fullest form of the name found. |
| `name_variants_ar` | string |  | Shorter forms merged into this person, `;`-separated. |
| `n_editions` | integer | yes | Number of editions the person contributed to. (range 1..) |

## `edition_editors`

Who did what for each edition (many-to-many between editions and editors).

| column | type | required | description |
|---|---|---|---|
| `edition_id` | string | yes | editions.edition_id |
| `person_id` | string | yes | editors.person_id |
| `role` | string | yes | Contribution: editor, compiler, commentator, corrector, introducer, translator, supervisor. (one of `editor`, `compiler`, `commentator`, `corrector`, `introducer`, `translator`, `supervisor`) |
| `role_ar` | string | yes | Contribution in Arabic (تحقيق، شرح، جمع، ضبط وتصحيح، تقديم، ترجمة، إشراف). |
| `seq` | integer | yes | Order of the person on the edition. (range 1..) |

## `manuscripts`

Manuscript copies in the library: where the manuscript itself is kept, as the copy shows it.

| column | type | required | description |
|---|---|---|---|
| `manuscript_id` | string | yes | Stable id: `m_` + first 10 hex digits of sha1 of the edition id. |
| `edition_id` | string | yes | The copy as an edition row (kind = manuscript). |
| `work_id` | string | yes | works.work_id |
| `title_ar` | string | yes | Title. |
| `author_id` | string |  | authors.author_id |
| `holding_library_ar` | string |  | Library that holds the manuscript (as its stamp, card or ownership note shows). Empty when the copy does not show it. |
| `shelfmark` | string |  | Shelfmark or number in that library. |
| `holding_confidence` | string |  | `high`: read in the copy itself; `medium`: from the upload's own description; `low`: probable (the copy suggests it). (one of `high`, `medium`, `low`) |
| `printed_edition_id` | string |  | A printed edition of the same work in the dataset, when there is one. |

## `edition_files`

One row per scan file (volume) of an edition: its order and exact size, for matching copies by size. No file names or paths.

| column | type | required | description |
|---|---|---|---|
| `edition_id` | string | yes | editions.edition_id |
| `seq` | integer | yes | Order of the file in the edition. (range 1..) |
| `volume_label` | string | yes | Volume number as labelled (`00` = front matter). |
| `size_bytes` | integer | yes | Exact size of the file in bytes. (range 1..) |

## `categories`

The 40 subject categories (those of al-Maktaba al-Shamila) with English names.

| column | type | required | description |
|---|---|---|---|
| `category_ar` | string | yes | Category in Arabic. |
| `category_en` | string | yes | Category in English. |
| `n_works` | integer | yes | Works in the category. (range 0..) |
| `n_editions` | integer | yes | Editions in the category. (range 0..) |

