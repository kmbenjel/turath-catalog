# Provenance, confidence and exclusions

This page explains where every value in turath-catalog comes from, how confident it is, and what was
left out. The numbers are those of release 0.2.0 (`build-report.json`).

## The editions

The editions are the printed books (and a few manuscript copies, lithographs, theses and offprints) of
a 16,700-volume library of Arabic PDF scans. Each edition's values come from its own scan (the title page,
read by eye for 2,230 editions, or the imprint page), from a catalog record tied to the scan by its exact byte
size, or from the Shamela card of the same edition; the stronger source gives the value (the table below
gives the order), and editions whose sources were found to disagree are held out until the title page settles
them. A scan file is never part of the dataset; only its byte size is kept (`edition_files`), so that anyone
holding a copy can recognise it.

## Sources of values

| `field_sources` value | meaning | strength |
|---|---|---|
| `title_page` | read by eye on the title page of the scan | strongest |
| `imprint_page` | read on the imprint or copyright page of the scan | strong |
| `catalog_record` | a Waqfeya record whose file has exactly the same byte size as the scan | strong for the same file |
| `shamela_card` | the al-Maktaba al-Shamila card of the same edition: the editor named on the scan matches the card's editor, or, when neither names one, the publisher matches | medium |
| `shamela_author` | the full name from the Shamela author record of a Shamela book matched to the work | medium |
| `file_label` | the library's label for the scan, itself composed from the sources above | weakest |
| `user` | your own catalog file (`turath-catalog build --csv`) | as good as your file |

A catalog record that contradicts the scan's own label (a different editor or publisher) is not used
for that edition. Only facts are taken from catalogs: names, titles, years, counts and identifiers.
Their prose (descriptions, biographies, blurbs) is never read into a record.

## Titles

`title_ar` is the title cell as the library gives it, kept verbatim. `title_clean_ar` is the title alone;
`turath_catalog.titles.split_title` separates the rest, and nothing is dropped unless the row already says it:

| in the title cell | goes to | rule |
|---|---|---|
| «A = B» | `alt_titles_ar` | B is another title of the same work; what follows «ويليه», «ومعه», «وبهامشه» stays with A |
| a bracket that names the work another way | `alt_titles_ar` | it opens with «أو» or with a genre word (تفسير, شرح, كتاب, صحيح, مختصر …) and has a second word |
| any other bracket | `title_note_ar` | the part covered («(كتاب الإيمان)», «(مقدمة المحقق)», a bracket that opens with the title's own first word), a disambiguator, a series |
| «ط. X», «ط X» (a publisher) | checked against `publisher_ar` and `place_ar` | the row confirms it: dropped; the row has no publisher: `publisher_ar` = X with source `file_label`; the row says otherwise: kept in `title_note_ar` as «ط X» |
| «ت - X», «ت X» (an editor) | checked against `editors_ar` | confirmed: dropped; otherwise kept in `title_note_ar` as «ت X» (a surname alone is not entered as an editor) |

In release 0.2.0, 103 edition titles carry such a part: 59 another title, 19 a remark; 2 publisher marks
filled an empty `publisher_ar` and 3 marks that the row does not confirm are kept as remarks. `work_id`
hashes the title as given, so the clean title never moves an id; a title written «A = B» is the work «A».

## People

`authors` has one row per name form: «ابن الجوزي» and «أبو الفرج ابن الجوزي» are two rows. Rows that carry
the same Shamela author id and no conflicting death year share a `canonical_author_id`, the dated row with
the most works. A name that joins two people («الطبراني وابن مردويه») is left on its own. 192 of the 2,643
rows are folded this way, which leaves 2,451 people; no row is merged on a name alone.

## Confidence

- **Editions.** `high`: the title page was read by eye and the label made from it (2,230). `medium`: at
  least one value comes from the title or imprint page, a size-linked catalog record or the same-edition
  Shamela card (3,021). `low`: only the library's label supports the values (375).
- **Works.** The best confidence among the work's editions.
- **Death years.** `shamela_book`: the Shamela author record of a Shamela book matched to one of the
  author's works (1,173 authors). `author_table`: the same name carries that year on another of the
  author's books, or Shamela's author table has exactly one author of that name whose death falls in the
  century a catalog record gives (66). `death_confidence` is `high` when two witnesses agree or the year
  falls in the recorded century (932), `medium` for a single witness (263), `low` when the year is that of
  the author of a matched Shamela book whose name could not be matched to the row's name, so that the row may
  name that book's commentator, transmitter or editor (44).
- **Manuscript holdings.** `high`: read in the copy itself (stamp, card, ownership note); `medium`: from
  the description of the upload; `low`: probable from the copy.
- **Links.** `openiti_confidence` `high` (same death year, same folded title, agreeing author) or
  `medium` (same year, a title prefix of 3+ words, agreeing author). Wikidata links have a single rule:
  an identifier crosswalk plus a death-year check, so they carry no separate level.

## What was excluded, and why

| left out | count | why |
|---|---:|---|
| editions whose sources disagree | 151 | the scan and its catalog records name different editors or publishers and the title page has not settled it |
| editions whose title or author is under review | 116 | a reading is in question |
| titles not in Arabic script | 125 | outside the dataset's scope (modern foreign-language books in the library) |
| death years where two people may share a name | 166 values | the same name form carries two years |
| death years outside the recorded century | 48 values | the year and the catalog's century disagree |
| Hijri/Gregorian year pairs that disagree | 32 pairs | both dropped rather than guessing which is right |
| "editor" values that are not a person | 85 values | e.g. an edition statement or a thesis note in the editor field |
| publisher values that repeat the author's name | 3 values | read from a file label, where the author's name had taken the publisher's place |
| file names, paths, download links, OCR text, notes, comments | all | never part of a record; the validator rejects paths, URLs, e-mails, IPs and credential words |

## Identifier schemes

| scheme | where | meaning |
|---|---|---|
| `shamela` | works, editions | al-Maktaba al-Shamila book id (`https://shamela.ws/book/<id>`) |
| `shamela_author` | authors | al-Maktaba al-Shamila author id (`https://shamela.ws/author/<id>`) |
| `waqfeya` | editions | waqfeya.net record id of the same scan file |
| `openiti_uri` | works | OpenITI book URI, release 2025.1.9 |
| `openiti_author_uri` | authors | OpenITI author URI |
| `wikidata_qid` | works, editions, authors | Wikidata item |

OpenITI metadata is CC BY-NC-SA 4.0; this dataset carries only its identifiers, not its titles or notes.
