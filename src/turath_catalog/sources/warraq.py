"""Adapter for a Warraq library workspace (the curated tables a Warraq library keeps beside its scans).

It reads only the curated tables of the workspace and never the books:

    data/catalog.json                 one entry per book (title, author, label, category, volume sizes)
    data/editions/edition-info.json   per-edition facts, each with its source (title page, imprint page,
                                      size-linked Waqfeya record, same-edition Shamela card, file label)
    data/editions/groups.json         editions grouped by work
    data/editions/edition-review.tsv  editions whose sources disagree  -> excluded ("needs review")
    data/names/plan-held.tsv          names held for a question         -> excluded ("needs review")
    data/names/read-status.tsv        which title pages were read by eye -> confidence "high"
    data/names/author-death-review.tsv  authors whose death year is in doubt -> no death year
    data/names/manuscripts.tsv        holding library of each manuscript copy
    data/compare/shamela-matches.tsv  work-level links to Shamela books
    data/shamela/books.tsv, authors.jsonl   Shamela facts: author id, death year, full name

Free-text notes (Waqfeya descriptions, Shamela biographies and blurbs, the curator's review notes and
comments, OCR text) are never read into a record. File paths stay inside the adapter: a record's
`key` is used for joins only and is dropped on export.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..hijri import ah_to_ce_range, century_ah
from ..record import EditionRecord, Editor, Volume
from ..textnorm import WAW_NAMES, arabic_digits_to_ascii, author_key, nfc, norm, tokens

SOURCE_MAP = {
    "قراءة صفحة العنوان": "title_page",
    "صفحة الحقوق": "imprint_page",
    "صفحة الحقوق (نص)": "imprint_page",
    "الوقفية": "catalog_record",
    "الشاملة": "shamela_card",
    "اسم المجلد": "file_label",
}
DEATH_SOURCE_MAP = {"الشاملة": "shamela_book", "الشاملة (المؤلف)": "author_table"}
GOOD_SHAMELA = {"exact", "exact (card title)", "prefix+author", "prefix+author (card title)", "smart-tokens", "prefix"}

ORDINALS = {
    "الأولى": 1,
    "الاولى": 1,
    "الثانية": 2,
    "الثالثة": 3,
    "الرابعة": 4,
    "الخامسة": 5,
    "السادسة": 6,
    "السابعة": 7,
    "الثامنة": 8,
    "التاسعة": 9,
    "العاشرة": 10,
    "first": 1,
    "second": 2,
    "third": 3,
}
ROLE_WORDS = [  # (regex on the words before the name, role, Arabic role as written)
    (r"ترجم", "translator", "ترجمة"),
    (r"شرح", "commentator", "شرح"),
    (r"جمع|إعداد|اعداد|رتب", "compiler", "جمع"),
    (r"ضبط|صحح|راجع|مراجعة", "corrector", "ضبط وتصحيح"),
    (r"إشراف|اشراف", "supervisor", "إشراف"),
    (r"قدم|تقديم", "introducer", "تقديم"),
    (r"تحقيق|حقق|^ت$|ت-|اعتنى|عني|بعناية|علق|خرج|تخريج", "editor", "تحقيق"),
]
NOT_A_PERSON = re.compile(r"^(ط\.?|طبعة|مخطوط|رسالة|أطروحة|اطروحة|بدون|مستل|مجلة|تصوير)(\s|$)")
BODY = re.compile(r"^(?:مركز|مكتب|المكتب|لجنة|اللجنة|قسم|مؤسسة|هيئة|وزارة|جامعة|مجموعة|جماعة|شركة|مجمع|إدارة|دار|فريق|نخبة)\s")
PERSON_PREFIX = re.compile(r"^(?:(?:الدكتور|الأستاذ|الشيخ|د\.|د/|د|أ\.د\.|ا\.د\.)\s*(?<=\s|\.|/))+")
HONORIFICS = re.compile(r"^(?:(?:الإمام|الامام|الحافظ|الشيخ|العلامة|شيخ الإسلام|القاضي)\s+)+")
GROUP_AUTHORS = {norm(x) for x in ("مجموعة من المؤلفين", "مجموعة مؤلفين", "مجهول", "غير معروف", "مؤلف مجهول")}
EXTRA_CITIES = [
    "القاهرة",
    "بيروت",
    "دمشق",
    "الرياض",
    "الكويت",
    "الرباط",
    "الجزائر",
    "جدة",
    "تونس",
    "عمان",
    "طنطا",
    "بغداد",
    "صنعاء",
    "الإسكندرية",
    "دبي",
    "ليدن",
    "الشارقة",
    "الجيزة",
    "مدريد",
    "طنجة",
    "بولاق",
    "الدمام",
    "المنصورة",
    "باريس",
    "الموصل",
    "فاس",
    "تطوان",
    "طرابلس",
    "حلب",
    "مراكش",
    "القسطنطينية",
    "إستانبول",
    "استانبول",
    "لندن",
    "بنغازي",
    "الطائف",
    "حيدرآباد",
    "لكنو",
    "دلهي",
    "كراتشي",
    "لاهور",
    "بيشاور",
    "نواكشوط",
    "قازان",
    "المدينة",
    "مكة",
    "مصر",
    "لبنان",
    "سوريا",
    "الأردن",
    "المغرب",
    "السعودية",
]
EXTRA_CITIES += ["المدينة المنورة", "مكة المكرمة", "الدار البيضاء", "أبو ظبي"]


def _tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = [ln for ln in path.open(encoding="utf-8") if not ln.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE))


def _int(v) -> int | None:
    if v is None:
        return None
    m = re.search(r"\d+", arabic_digits_to_ascii(str(v)))
    return int(m.group()) if m else None


@dataclass
class Report:
    """What the adapter left out, and why (printed by the build and written to the release)."""

    excluded: Counter = field(default_factory=Counter)
    dropped_values: Counter = field(default_factory=Counter)

    def as_dict(self) -> dict:
        return {"excluded_rows": dict(self.excluded), "dropped_values": dict(self.dropped_values)}


class WarraqWorkspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser()
        self.data = self.root / "data"
        if not (self.data / "catalog.json").exists():
            raise FileNotFoundError(f"{self.data / 'catalog.json'} not found: is {self.root} a Warraq workspace?")
        self.report = Report()
        self._cities = self._city_vocabulary()

    # ---- helpers -------------------------------------------------------------------------
    def _city_vocabulary(self) -> list[str]:
        names = set(EXTRA_CITIES)
        for r in _tsv(self.data / "names/title-read.tsv"):
            for c in re.split(r"[،,\-]|\sو", r.get("city") or ""):
                c = c.strip()
                if 1 < len(c) <= 20:
                    names.add(c)
        return sorted(names, key=len, reverse=True)

    def split_place(self, publisher: str) -> tuple[str, str]:
        """«دار الفكر دمشق» → («دار الفكر», «دمشق»); «المطبعة السلفية بمصر» → («المطبعة السلفية», «مصر»)."""
        publisher = " - ".join(x.strip(" -") for x in re.split(r"/", publisher) if x.strip(" -"))
        # «دار المعارف 1958 - طبعة ملونة»: printing details are not part of the publisher's name
        segs = [re.sub(r"^ط\.?\s+", "", x) for x in re.split(r"\s+-\s+", publisher)]
        segs = [x for x in segs if x and not re.match(r"^(طبعة|ط$)", x)]
        publisher = re.sub(r"\s*\b\d{4}\s*(هـ|م)?$", "", " - ".join(segs)).strip(" -،")
        pub, places = publisher.strip(), []
        for _ in range(2):
            for c in self._cities:
                m = re.search(rf"(?:\s+-\s+|\s+|،\s*)(?:ب)?{re.escape(c)}$", pub)
                if m and m.start() > 0 and len(pub[: m.start()].split()) >= 1:
                    places.insert(0, c)
                    pub = pub[: m.start()].strip(" -،")
                    break
            else:
                break
        if publisher.strip() in self._cities:  # the whole value is a place
            return "", publisher.strip()
        return pub, " - ".join(places)

    @staticmethod
    def parse_editors(value: str, edition_text: str) -> list[Editor]:
        out = []
        parts = []
        for part in re.split(r"\s*-\s+|\s+-\s*|؛|(?<!^د)/", value):
            part = part.strip(" .،-")
            if BODY.match(part):  # «مركز البحوث وتقنية المعلومات»: one body, whatever «و» it holds
                parts.append(part)
                continue
            joined = part.split("-")  # «فؤاد سزكين-علاء الدين جوخوشا»: full names joined by a bare dash
            if len(joined) > 1 and all(len(p.split()) >= 2 for p in joined):
                parts += joined
                continue
            # «عادل أحمد عبد الموجود وعلي محمد معوض»: two people, when both sides are full names
            pieces = re.split(r"\s+و(?=\S)", part)
            if (
                len(pieces) > 1
                and all(len(p.split()) >= 2 for p in pieces[:1] + ["و" + p for p in pieces[1:]])
                and not any(("و" + p).split()[0] in WAW_NAMES for p in pieces[1:])
                and all(len(p.split()) >= 2 for p in pieces[1:])
            ):
                parts += [pieces[0]] + pieces[1:]
            else:
                parts.append(part)
        for part in parts:
            name = PERSON_PREFIX.sub("", part.strip(" .،-"))
            if len(name) < 3 or NOT_A_PERSON.match(name) or re.search(r"\d", name) or name.count("(") != name.count(")"):
                continue
            if name.count("،") == 1:  # catalog form «معروف، بشار عواد» → «بشار عواد معروف»
                family, given = (x.strip() for x in name.split("،"))
                if given and len(family.split()) <= 2:
                    name = f"{given} {family}"
            if "،" in name or len(name) > (120 if BODY.match(name) else 80):
                continue
            role, role_ar = "editor", "تحقيق"
            first = name.split()[0]
            seg = next((s for s in re.split(r"\s+-\s+", edition_text.strip("()")) if first in s), "")
            before = seg.split(first)[0].strip() if seg else ""
            for pat, r, ar in ROLE_WORDS:
                if before and re.search(pat, before):
                    role, role_ar = r, ar
                    break
            out.append(Editor(name=name, role=role, role_ar=role_ar))
        return out

    @staticmethod
    def kind_of(text: str) -> str:
        if re.search(r"(^|\s)مخطوط", text):
            return "manuscript"
        if "حجرية" in text:
            return "lithograph"
        if re.search(r"رسالة (ماجستير|دكتوراه|جامعية|علمية)|أطروحة", text):
            return "thesis"
        if re.search(r"(^|\s)مستل", text):
            return "offprint"
        return "printed"

    # ---- main --------------------------------------------------------------------------------
    def records(self) -> list[EditionRecord]:
        d = self.data
        cat = json.loads((d / "catalog.json").read_text(encoding="utf-8"))
        info = {nfc(k): v for k, v in json.loads((d / "editions/edition-info.json").read_text(encoding="utf-8")).items()}
        groups = {}
        gpath = d / "editions/groups.json"
        if gpath.exists():
            for g in json.loads(gpath.read_text(encoding="utf-8")):
                for e in g["editions"]:
                    groups[nfc(e["cat"] + "/" + e["folder"])] = "g:" + g["work"]
        review = {nfc(r["book"]) for r in _tsv(d / "editions/edition-review.tsv")}
        held = {nfc(r["book"]) for r in _tsv(d / "names/plan-held.tsv")}
        read = {nfc(r["book"]) for r in _tsv(d / "names/read-status.tsv") if r.get("status") == "read"}
        doubtful_death = {r["author_key"] for r in _tsv(d / "names/author-death-review.tsv")}

        # Shamela: work links, author ids, full names (names only; biographies are never read)
        sham_books = {r["book_id"]: r for r in _tsv(d / "shamela/books.tsv")}
        sham_auth: dict[int, str] = {}
        apath = d / "shamela/authors.jsonl"
        if apath.exists():
            for ln in apath.open(encoding="utf-8"):
                a = json.loads(ln)
                full = (a.get("full") or "").split("\n")[0]
                if a.get("life") and " بن " in full and not re.search(r"[0-9٠-٩A-Za-z@*«»:]", full):
                    full = full.split(")")[0] if ")" in full else full
                    full = " ".join(re.sub(r"[()]", " ", re.sub(r"[ً-ْ]", "", full)).split()).strip(" ،")
                    if 5 < len(full) <= 160:
                        sham_auth[int(a["id"])] = full
        work_links: dict[str, list[tuple[int, str, str]]] = defaultdict(list)  # book id -> (shamela id, match, author)
        for r in _tsv(d / "compare/shamela-matches.tsv"):
            if r["match"] in GOOD_SHAMELA:
                for bid in (r.get("phone_book_ids") or "").split():
                    work_links[bid].append((int(r["shamela_id"]), r["match"], r.get("author") or ""))

        manuscripts = self._manuscripts(cat)
        out: list[EditionRecord] = []
        for b in cat["books"]:
            key = nfc(b["cat"] + "/" + b["folder"])
            if key in review and key not in read:
                self.report.excluded["sources disagree on the edition (held for review)"] += 1
                continue
            if key in held:
                self.report.excluded["title or author under review"] += 1
                continue
            ei = info.get(key, {})
            rec = EditionRecord(
                key=key,
                title=b["title"].strip(),
                category_ar=b["cat"],
                author=(b.get("author") or "").strip(),
                label=" - ".join(x.strip() for x in b["folder"].split("/")),
                work_group=groups.get(key, ""),
                title_page_read=key in read,
            )
            if not re.search(r"[\u0621-\u064A]", rec.title):
                self.report.excluded["title not in Arabic script (out of scope)"] += 1
                continue
            short, _, full = rec.author.partition("؛")
            rec.author = HONORIFICS.sub("", short.strip())
            if " بن " in full and len(full) <= 160:
                rec.author_full_name, rec.sources["author_full_name"] = " ".join(full.split()), "catalog_record"
            if norm(rec.author) in GROUP_AUTHORS:
                rec.author = ""
            for f in ("editor", "publisher", "hijri", "gregorian", "edition_no", "pages", "volumes", "death"):
                if f in ei and ei[f].get("s") not in SOURCE_MAP and f != "death":
                    self.report.dropped_values[f"{f}: unknown source {ei[f].get('s')}"] += 1
                    ei = {k: v for k, v in ei.items() if k != f}
            src = lambda f, ei=ei: SOURCE_MAP[ei[f]["s"]]
            if "editor" in ei:
                rec.editors = self.parse_editors(str(ei["editor"]["v"]), b.get("edition") or "")
                if rec.editors:
                    rec.sources["editors"] = src("editor")
                else:
                    self.report.dropped_values["editor: not a person's name"] += 1
            if "publisher" in ei:
                rec.publisher, rec.place = self.split_place(str(ei["publisher"]["v"]))
                if src("publisher") == "file_label" and rec.author and norm(rec.publisher) == norm(rec.author):
                    self.report.dropped_values["publisher: the author's name, read from a file label"] += 1
                    rec.publisher = rec.place = ""
                if rec.publisher or rec.place:
                    rec.sources["publisher"] = src("publisher")
                if rec.place:
                    rec.sources["place"] = src("publisher")
            h, g = _int(ei.get("hijri", {}).get("v")), _int(ei.get("gregorian", {}).get("v"))
            if h is not None and not 1100 <= h <= 1460:
                self.report.dropped_values["year_ah outside 1100-1460"] += 1
                h = None
            if g is not None and not 1700 <= g <= 2026:
                self.report.dropped_values["year_ce outside 1700-2026"] += 1
                g = None
            if h and g:
                lo, hi = ah_to_ce_range(h)
                if not lo - 1 <= g <= hi + 1:
                    self.report.dropped_values["year_ah and year_ce disagree (both dropped)"] += 1
                    h = g = None
            if h:
                rec.year_ah, rec.sources["year_ah"] = h, src("hijri")
            if g:
                rec.year_ce, rec.sources["year_ce"] = g, src("gregorian")
            if "edition_no" in ei:
                raw = str(ei["edition_no"]["v"]).strip()
                n = int(raw) if raw.isdigit() else ORDINALS.get(raw)
                if n and 1 <= n <= 50:
                    rec.edition_number = n
                    rec.sources["edition_number"] = src("edition_no")
                elif raw and raw != "بدون":
                    rec.edition_statement = raw
                    rec.sources["edition_statement"] = src("edition_no")
            if "pages" in ei and (p := _int(ei["pages"]["v"])) and 1 <= p <= 100000:
                rec.pages, rec.sources["pages"] = p, src("pages")
            vols = _int(ei.get("volumes", {}).get("v")) if "volumes" in ei else None
            if vols:
                rec.sources["volumes"] = src("volumes")
            elif (v := _int(b.get("numberOfVolumes"))) and b.get("waqfeya"):
                vols = v
                rec.sources["volumes"] = "catalog_record"
            if vols and 1 <= vols <= 500:
                rec.volumes = vols
            for i, (name, size) in enumerate(b["files"], 1):
                m = re.match(r"^(\d{1,3})\s+-\s+", name)
                rec.files.append(Volume(label=m.group(1) if m else f"{i:02d}", size_bytes=int(size)))
            # death year, century
            akey = author_key(rec.author)
            c = _int(b.get("century"))
            rec.century_ah = c if c and 1 <= c <= 15 else None
            in_doubt = akey in doubtful_death and ei.get("death", {}).get("s") != "الشاملة"
            if "death" in ei and not in_doubt:
                dy = _int(ei["death"]["v"])
                if dy and 1 <= dy <= 1450:
                    if rec.century_ah and century_ah(dy) != rec.century_ah:
                        self.report.dropped_values["death year outside the record's century"] += 1
                    else:
                        rec.death_ah, rec.death_source = dy, DEATH_SOURCE_MAP.get(ei["death"]["s"], "author_table")
            elif "death" in ei:
                self.report.dropped_values["death year in doubt (two people may share the name)"] += 1
            # Shamela links: the work, its author, and the same edition when the card supplied values
            ours = tokens(rec.author)
            name_agrees = False
            for sid, how, sauthor in work_links.get(str(b["id"]), []):
                agree = bool(ours & tokens(sauthor)) if ours else False
                name_agrees = name_agrees or agree
                rec.shamela_work_ids.append((sid, "high" if agree and how.startswith("exact") else "medium"))
                sb = sham_books.get(str(sid))
                if agree and sb and sb.get("author_id", "").isdigit():
                    rec.shamela_author_id = rec.shamela_author_id or int(sb["author_id"])
            if rec.death_source == "shamela_book" and not name_agrees:
                rec.death_name_matched = False  # the year is the Shamela book's author's; is he this author?
            if rec.shamela_author_id in sham_auth and not rec.author_full_name:
                rec.author_full_name, rec.sources["author_full_name"] = sham_auth[rec.shamela_author_id], "shamela_author"
            if "shamela_card" in rec.sources.values() and len({s for s, _ in rec.shamela_work_ids}) == 1:
                rec.shamela_edition_id = rec.shamela_work_ids[0][0]
            rec.waqfeya_ids = [w["id"] for w in b.get("waqfeya") or [] if re.fullmatch(r"[0-9a-f]{24}", w.get("id", ""))]
            rec.kind = self.kind_of(b.get("edition") or "")
            if key in manuscripts:
                rec.kind = "manuscript"
                rec.holding_library, rec.shelfmark, rec.holding_confidence, rec.printed_key = manuscripts[key]
            out.append(rec)
        return out

    def _manuscripts(self, cat: dict) -> dict[str, tuple[str, str, str, str]]:
        """catalog key -> (holding library, shelfmark, confidence, key of a printed edition)."""
        by_file = {}
        for b in cat["books"]:
            for name, _ in b["files"]:
                by_file[nfc(b["cat"] + "/" + name)] = nfc(b["cat"] + "/" + b["folder"])
                by_file[nfc(b["cat"] + "/" + b["folder"] + "/" + name)] = nfc(b["cat"] + "/" + b["folder"])
        out = {}
        for r in _tsv(self.data / "names/manuscripts.tsv"):
            key = by_file.get(nfc(r.get("path", "")))
            if not key:
                continue
            holding = (r.get("holding") or "").strip()
            conf = "high"
            if re.search(r"\(.*\)", holding):
                conf = "medium"  # read from the upload's file name or description, not from the book
                holding = re.sub(r"\s*\([^)]*\)", "", holding)
            if "فيما يبدو" in holding:
                conf = "low"
                holding = holding.replace("فيما يبدو", "")
            lib, _, mark = holding.partition("،")
            lib, mark = " ".join(lib.split()), re.sub(r"^\s*رقم\s*", "", mark).strip()
            if mark and not re.search(r"\d", mark):  # «مؤسسة الملك عبد العزيز، الدار البيضاء»: a place, not a shelfmark
                lib, mark = f"{lib} - {mark}", ""
            printed = by_file.get(nfc(r.get("printed", "")), "")
            if key in out and not lib:
                continue
            out[key] = (lib, mark, conf if lib else "", printed)
        return out
