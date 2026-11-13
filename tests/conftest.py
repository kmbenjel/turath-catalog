from __future__ import annotations

import json
from pathlib import Path

import pytest

from turath_catalog.record import EditionRecord, Editor, Volume

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_dir() -> Path:
    return ROOT / "src" / "turath_catalog" / "sample"


def rec(key, title, author="", **kw) -> EditionRecord:
    files = kw.pop("files", [Volume("01", 1000)])
    r = EditionRecord(
        key=key,
        title=title,
        author=author,
        category_ar=kw.pop("category_ar", "الفقه العام"),
        label=kw.pop("label", title),
        files=files,
        **kw,
    )
    return r


@pytest.fixture
def records() -> list[EditionRecord]:
    return [
        rec(
            "a",
            "المجموع شرح المهذب",
            "النووي",
            death_ah=676,
            death_source="shamela_book",
            century_ah=7,
            editors=[Editor("محمد نجيب المطيعي")],
            publisher="دار الفكر",
            place="بيروت",
            year_ah=1417,
            year_ce=1996,
            title_page_read=True,
            sources={"editors": "title_page", "publisher": "title_page"},
            shamela_work_ids=[(2186, "high")],
            files=[Volume("01", 500), Volume("02", 700)],
        ),
        rec(
            "b",
            "المجموع شرح المهذب",
            "النووي",
            century_ah=7,
            editors=[Editor("محمد المطيعي")],
            sources={"editors": "catalog_record"},
            waqfeya_ids=["66a88e0187c55ca3e12f3acb"],
        ),
        rec("c", "الأربعون", "النووي", death_ah=676, death_source="author_table"),
        rec("d", "الأربعون", "الآجري", death_ah=360, death_source="shamela_book"),
        rec("e", "طبقات الشافعية", "ابن قاضي شهبة", death_ah=851, death_source="shamela_book"),
        rec(
            "f",
            "طبقات الشافعية",
            "ابن قاضي شهبة",
            death_ah=851,
            death_source="shamela_book",
            kind="manuscript",
            holding_library="مكتبة الأزهر",
            shelfmark="267",
            holding_confidence="high",
        ),
        rec("g", "الشامل", "الشاشي", death_ah=335, death_source="shamela_book"),
        rec("h", "أصول الشاشي", "الشاشي", death_ah=325, death_source="shamela_book"),
        rec("i", "ديوان مجهول", ""),
    ]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A miniature Warraq workspace with every input the adapter reads."""
    d = tmp_path / "ws" / "data"
    for sub in ("editions", "names", "compare", "shamela"):
        (d / sub).mkdir(parents=True)
    books = [
        {
            "id": 1,
            "cat": "أصول الفقه",
            "folder": "آداب الفتوى - النووي - ت بسام الجابي - دار الفكر دمشق",
            "title": "آداب الفتوى",
            "author": "النووي",
            "edition": "ت بسام الجابي - دار الفكر دمشق",
            "files": [["آداب الفتوى - النووي.pdf", 1263747]],
            "waqfeya": [{"id": "66a88e0187c55ca3e12f3acb", "name": "x", "url": "https://waqfeya.net/books/x"}],
            "century": "القرن 07 هـ",
            "numberOfVolumes": "1",
        },
        {
            "id": 2,
            "cat": "أصول الفقه",
            "folder": "كتاب في نزاع - مؤلف",
            "title": "كتاب في نزاع",
            "author": "مؤلف",
            "edition": "",
            "files": [["كتاب في نزاع - مؤلف.pdf", 10]],
        },
        {
            "id": 3,
            "cat": "أصول الفقه",
            "folder": "كتاب معلق - مؤلف",
            "title": "كتاب معلق",
            "author": "مؤلف",
            "edition": "",
            "files": [["كتاب معلق - مؤلف.pdf", 11]],
        },
        {
            "id": 4,
            "cat": "علوم أخرى",
            "folder": "Frankenstein - Mary Shelley",
            "title": "Frankenstein",
            "author": "Mary Shelley",
            "edition": "",
            "files": [["Frankenstein - Mary Shelley.pdf", 12]],
        },
        {
            "id": 5,
            "cat": "التاريخ",
            "folder": "رحلة العبدري - محمد العبدري - مخطوط",
            "title": "رحلة العبدري",
            "author": "محمد العبدري",
            "edition": "مخطوط",
            "files": [["01 - رحلة العبدري.pdf", 100], ["02 - رحلة العبدري.pdf", 200]],
        },
        {
            "id": 6,
            "cat": "التاريخ",
            "folder": "الرحلة المغربية - محمد العبدري - دار ابن حزم",
            "title": "الرحلة المغربية",
            "author": "محمد العبدري؛ محمد بن محمد بن علي العبدري البلنسي",
            "edition": "دراسة وتحقيق علي إبراهيم كردي - دار سعد الدين / دمشق",
            "files": [["الرحلة المغربية.pdf", 300]],
        },
        {
            "id": 7,
            "cat": "الفقه العام",
            "folder": "مسائل - ابن أبي شيبة",
            "title": "مسائل",
            "author": "ابن أبي شيبة",
            "edition": "",
            "files": [["مسائل.pdf", 400]],
            "century": "القرن 3 هـ",
        },
    ]
    (d / "catalog.json").write_text(json.dumps({"generated": "x", "books": books}, ensure_ascii=False), encoding="utf-8")
    info = {
        "أصول الفقه/آداب الفتوى - النووي - ت بسام الجابي - دار الفكر دمشق": {
            "editor": {"v": "الجابي، بسام عبد الوهاب", "s": "الوقفية"},
            "publisher": {"v": "دار الفكر دمشق", "s": "قراءة صفحة العنوان"},
            "edition_no": {"v": "الأولى", "s": "الوقفية"},
            "hijri": {"v": 1408, "s": "الوقفية"},
            "gregorian": {"v": 1988, "s": "الوقفية"},
            "pages": {"v": 96, "s": "الوقفية"},
            "death": {"v": 676, "s": "الشاملة"},
            "note": {"v": "وصف نثري من الوقفية لا ينشر", "s": "الوقفية"},
        },
        "التاريخ/الرحلة المغربية - محمد العبدري - دار ابن حزم": {
            "editor": {"v": "علي إبراهيم كردي", "s": "اسم المجلد"},
            "publisher": {"v": "دار سعد الدين / دمشق", "s": "اسم المجلد"},
            "hijri": {"v": 1420, "s": "صفحة الحقوق"},
            "gregorian": {"v": 1950, "s": "صفحة الحقوق"},
        },
        "الفقه العام/مسائل - ابن أبي شيبة": {"death": {"v": 235, "s": "الشاملة (المؤلف)"}},
    }
    (d / "editions/edition-info.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    (d / "editions/groups.json").write_text("[]", encoding="utf-8")
    (d / "editions/edition-review.tsv").write_text("book\tsource\tconflict\nأصول الفقه/كتاب في نزاع - مؤلف\twaqfeya\tx\n", encoding="utf-8")
    (d / "names/plan-held.tsv").write_text("n\tbook\twhy held\n0\tأصول الفقه/كتاب معلق - مؤلف\towner: ask\n", encoding="utf-8")
    (d / "names/read-status.tsv").write_text(
        "book\tstatus\tsources\twhat was read\nأصول الفقه/آداب الفتوى - النووي - ت بسام الجابي - دار الفكر دمشق\tread\trename\tx\n",
        encoding="utf-8",
    )
    (d / "names/author-death-review.tsv").write_text(
        "author_key\tyears\twhy\tcentury\texample\nابن ابي شيبه\t235 297\tseveral\t\tx\n", encoding="utf-8"
    )
    (d / "names/title-read.tsv").write_text(
        "n\tbook\tverdict\ttitle\tauthor\teditor\tpublisher\tcity\tyear\tkind\tsection\tnote\n", encoding="utf-8"
    )
    (d / "names/manuscripts.tsv").write_text(
        "# comment line\nn\tpath\ttitle\tauthor\tholding\tprinted\tnote\n"
        "1\tالتاريخ/رحلة العبدري - محمد العبدري - مخطوط/01 - رحلة العبدري.pdf\tرحلة العبدري\tمحمد العبدري\tوقف رواق المغاربة بالأزهر، رقم 12\t"
        "التاريخ/الرحلة المغربية.pdf\tملاحظة خاصة لا تنشر\n",
        encoding="utf-8",
    )
    (d / "compare/shamela-matches.tsv").write_text(
        "shamela_id\ttitle\tauthor\tdeath\tcategory\tshamela_pdf\tmatch\tphone_book_ids\n"
        "7\tآداب الفتوى والمفتي والمستفتي\tالنووي\t676\tأصول الفقه\t1\texact\t1\n"
        "8\tشيء آخر\tغيره\t\tأصول الفقه\t1\tcover\t1\n",
        encoding="utf-8",
    )
    (d / "shamela/books.tsv").write_text(
        "book_id\ttitle\tcategory\tauthor\tdeath\tprinted\thas_pdf\tpdf_size\tauthor_id\n7\tآداب الفتوى\tأصول الفقه\tالنووي\t676\t1\t1\t1\t35\n",
        encoding="utf-8",
    )
    (d / "shamela/authors.jsonl").write_text(
        json.dumps(
            {
                "id": 35,
                "name": "النووي",
                "life": "٦٣١ - ٦٧٦ هـ",
                "full": "يحيى بن شرف بن مري النووي (أبو زكريا) فقيه",
                "bio": "سيرة طويلة لا تنشر",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path / "ws"
