"""The parts of a title as catalogs and file labels write it.

A title cell often carries more than the title: another name of the work after «=», a remark in
brackets, the mark of an edition («ط. الخانجي») or of an editor («ت - الميمني»). `split_title` separates
them without losing any, so the dataset can keep the title as given and offer a clean one beside it:

    «الجامع لأحكام القرآن = تفسير القرطبي»   → clean «الجامع لأحكام القرآن», other title «تفسير القرطبي»
    «الحماسة البصرية (ط. الخانجي)»           → clean «الحماسة البصرية», publisher mark «الخانجي»
    «تفسير يحيى بن سلام (من النحل إلى الصافات)» → clean «تفسير يحيى بن سلام», remark «من النحل إلى الصافات»

The ids never depend on this module: `work_id` hashes `textnorm.title_key` of the title as given.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .textnorm import norm

__all__ = ["TitleParts", "mark_agrees", "split_title"]

_BRACKET = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")
_SEP = r"(?:\s*[.\-]\s*|\s+)"  # between a mark's letter and its name: «ط. », «ط - », «ط »
_PUB_MARK = re.compile(rf"^ط{_SEP}(\S.*)$")
_ED_MARK = re.compile(rf"^(?:ت{_SEP}|تحقيق\s+)(\S.*)$")
_TAIL_MARK = re.compile(rf"^(.*)(?:\s*[-،.]\s*|\s+)(ط|ت){_SEP}(\S.*)$")  # the last mark of the title
_JOINERS = "ويليه|ويليها|ومعه|ومعها|وبهامشه|وبهامشها|وبذيله|وبذيلها"
_JOINED = re.compile(rf"\s*،?\s+(?:{_JOINERS})(?:\s|$)")
_DANGLING = re.compile(rf"\s*،?\s*(?:{_JOINERS})-?$")
_ORDINAL = re.compile(r"^(?:ال)?(?:أولى|اولى|ثانية|ثالثة|رابعة|خامسة|سادسة|سابعة|ثامنة|تاسعة|عاشرة|جديدة|مصورة|ملونة|منقحة|مزيدة)(?:\s|$)")
# A bracket that opens with one of these (and has a second word) names the work another way: «(تفسير ابن عادل)»
_GENRE = frozenset(
    norm(w)
    for w in [
        "تفسير",
        "حاشية",
        "حماسة",
        "ديوان",
        "سنن",
        "سيرة",
        "شرح",
        "صحيح",
        "طبقات",
        "كتاب",
        "متن",
        "مختصر",
        "مسند",
        "مستخرج",
        "مصنف",
        "معجم",
        "مغازي",
        "مقدمة",
        "منظومة",
        "موطأ",
        "تاريخ",
    ]
)
_GENERIC = frozenset(norm(w) for w in ["دار", "مكتبة", "المكتبة", "مطبعة", "المطبعة", "مؤسسة", "طبعة", "نشر", "للنشر"])
_MAX_MARK_WORDS = 6


@dataclass(frozen=True)
class TitleParts:
    """What `split_title` found. Nothing of the input is dropped: every piece lands in one field."""

    clean: str  # the title itself
    alts: tuple[str, ...] = ()  # other titles of the same work
    notes: tuple[str, ...] = ()  # remarks: the part covered, a disambiguator, a series
    publisher_marks: tuple[str, ...] = ()  # «ط. X» / «ط X»: the edition, named by its publisher
    editor_marks: tuple[str, ...] = ()  # «ت - X» / «تحقيق X»: the edition, named by its editor


def _tidy(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([،.])", r"\1", s).strip(" -،.:")
    return _DANGLING.sub("", s).strip(" -،.:")


def _is_mark_name(x: str) -> bool:
    return not re.search(r"[0-9٠-٩=]", x) and len(x.split()) <= _MAX_MARK_WORDS and not _ORDINAL.match(x)


def split_title(title: str | None, author: str = "") -> TitleParts:
    """Separate a title from the other titles, remarks and edition marks written with it.

    >>> split_title("الجامع لأحكام القرآن = تفسير القرطبي").alts
    ('تفسير القرطبي',)
    >>> split_title("الحماسة البصرية (ط. الخانجي)")
    TitleParts(clean='الحماسة البصرية', alts=(), notes=(), publisher_marks=('الخانجي',), editor_marks=())
    """
    raw = " ".join((title or "").split())
    alts: list[str] = []
    notes: list[str] = []
    pubs: list[str] = []
    eds: list[str] = []

    def bracket(m: re.Match[str]) -> str:
        x = _tidy(m.group(1) if m.group(1) is not None else m.group(2))
        if not x:
            return " "
        pm, em = _PUB_MARK.match(x), _ED_MARK.match(x)
        words = norm(x).split()
        if pm and _is_mark_name(pm.group(1)):
            pubs.append(_tidy(pm.group(1)))
        elif em and _is_mark_name(em.group(1)):
            eds.append(_tidy(em.group(1)))
        elif x.startswith("أو ") and len(words) > 1:
            alts.append(_tidy(x[3:]))
        elif len(words) > 1 and words[0] in _GENRE and not re.search(r"[0-9٠-٩]", x):
            alts.append(x)
        else:
            notes.append(x)
        return " "

    t = re.sub(r"[()\[\]]", " ", _BRACKET.sub(bracket, raw))  # an unpaired bracket is not part of a title
    for _ in range(2):  # «… ط القلم», «…. ت- مشهور» at the end of the title
        m = _TAIL_MARK.match(t)
        if not m or not _is_mark_name(m.group(3)) or not _tidy(m.group(1)):
            break
        (pubs if m.group(2) == "ط" else eds).append(_tidy(m.group(3)))
        t = m.group(1)

    main, *others = re.split(r"\s*=\s*", t)
    for o in others:
        j = _JOINED.search(o)
        if j:  # «A = B، ويليه C»: C comes with the book, not with its second name
            main, o = main + o[j.start() :], o[: j.start()]
        if _tidy(o):
            alts.append(_tidy(o))
    main = _tidy(main)
    if author:  # «أخبار مكة -الأزرقي»: the author's name is not part of the title
        m = re.search(r"\s*-\s*(\S.*)$", main)
        if m and norm(m.group(1)) == norm(author) and _tidy(main[: m.start()]):
            main = _tidy(main[: m.start()])
    if not main:  # nothing but brackets: the title is what they hold
        return TitleParts(clean=_tidy(re.sub(r"[()\[\]=]", " ", raw)) or raw)
    uniq = lambda xs, drop=(): tuple(dict.fromkeys(x for x in xs if x and x not in drop))
    return TitleParts(main, uniq(alts, (main,)), uniq(notes), uniq(pubs), uniq(eds))


def mark_agrees(mark: str, value: str) -> bool:
    """Does an edition mark name what the row already says? «الخانجي» agrees with «مكتبة الخانجي», «العراق»
    with «المجمع العلمي العراقي»; «غراس» does not agree with «مكتبة المعارف»."""
    want = [w for w in norm(mark).split() if w not in _GENERIC]
    have = norm(value).split()
    return bool(want) and all(any(h == w or (len(w) >= 4 and h.startswith(w)) for h in have) for w in want)
