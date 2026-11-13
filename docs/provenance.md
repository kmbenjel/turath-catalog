# Provenance, confidence and exclusions

This page explains where every value in turath-catalog comes from, how confident it is, and what was
left out. The numbers are those of release 0.1.0 (`build-report.json`).

## The editions

The editions are the printed books (and a few manuscript copies, lithographs, theses and offprints) of
a 16,700-volume library of Arabic PDF scans, checked one by one in 2025–2026. A scan file is never part of
the dataset; only its byte size is kept (`edition_files`), so that anyone holding a copy can recognise it.

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

## Confidence

- **Editions.** `high`: the title page was read by eye and the label made from it (2,230). `medium`: at
  least one value comes from the title or imprint page, a size-linked catalog record or the same-edition
  Shamela card (3,021). `low`: only the library's label supports the values (375).
- **Works.** The best confidence among the work's editions.
- **Death years.** `shamela_book`: the Shamela author record of a Shamela book matched to one of the
  author's works (1,173 authors). `author_table`: the same name carries that year on another of the
  author's books, or Shamela's author table has exactly one author of that name whose death falls in the
  century a catalog record gives (66). `death_confidence` is `high` when two witnesses agree or the year
  falls in the recorded century (962), `medium` for a single witness (277).
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
| "editor" values that are not a person | 80 values | e.g. an edition statement or a thesis note in the editor field |
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
