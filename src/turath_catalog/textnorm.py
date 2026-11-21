"""Arabic normalisation and the matching keys that every Warraq tool shares.

`title_key` and `author_key` are the recipe behind the stable ids (`work_id` = sha1 of
``title_key|author_key``). turath-match computes its cluster ids with the same recipe, so a
work clustered there and a work in this dataset carry the same id.
"""

from __future__ import annotations

import re
import unicodedata

_DIACRITICS = re.compile(r"[ً-ْٰـ]")  # harakat, superscript alif, tatweel
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي", "ء": None})
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NON_WORD = re.compile(r"[^ء-ي0-9 ]")
_HONORIFICS = re.compile(r"^(?:(?:الإمام|الامام|الحافظ|الشيخ|العلامة|العلامه|شيخ الإسلام|شيخ الاسلام|القاضي|الأستاذ|الدكتور|د)\.?\s+)+")


def nfc(s: str | None) -> str:
    return unicodedata.normalize("NFC", s or "")


def arabic_digits_to_ascii(s: str) -> str:
    return (s or "").translate(_DIGITS)


def norm(s: str | None) -> str:
    """Fold an Arabic string for comparison: no diacritics, one alif/ya/ha form, no punctuation."""
    s = _DIACRITICS.sub("", nfc(s))
    s = s.translate(_FOLD).translate(_DIGITS)
    s = _NON_WORD.sub(" ", s)
    return " ".join(s.split())


def title_key(title: str | None) -> str:
    """The work part of a title: brackets, edition and editor tails and a leading «كتاب» dropped, folded."""
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", title or "")
    t = re.split(r"\s+-\s+|\s+ط\s|\s+ت\s", " " + t + " ")[0]
    words = norm(t).split()
    if len(words) > 1 and words[0] == "كتاب":
        words = words[1:]
    return " ".join(words)


def author_key(author: str | None) -> str:
    """The first name form of an author («الشاشي؛ إسحاق بن …» → «الشاشي»), honorifics dropped, folded."""
    a = re.split(r"[؛;]", author or "")[0].strip()
    return norm(_HONORIFICS.sub("", a))


STOP_TOKENS = frozenset(
    norm(w)
    for w in [
        "بن",
        "ابن",
        "ابي",
        "ابو",
        "أبي",
        "أبو",
        "ابا",
        "عبد",
        "الله",
        "محمد",
        "احمد",
        "أحمد",
        "علي",
        "الامام",
        "الحافظ",
        "الشيخ",
        "العلامه",
        "القاضي",
        "الدين",
    ]
)


def tokens(s: str | None, min_len: int = 3) -> set[str]:
    """Distinctive folded words of a name (common name parts and short words dropped)."""
    return {w for w in norm(s).split() if len(w) >= min_len and w not in STOP_TOKENS}


# Given names that open with «و»: in «أحمد ووهبة الزحيلي» the «و…» word is a name, not "and"
WAW_NAMES = frozenset(
    [
        "ولد",
        "وليد",
        "وهبة",
        "وهبه",
        "وصي",
        "وائل",
        "وداد",
        "وفاء",
        "وحيد",
        "ولي",
        "وجيه",
        "وسيم",
        "وضاح",
        "ورقة",
        "وهب",
        "وكيع",
        "وجدي",
        "وفيق",
        "واصل",
        "واثق",
        "وديع",
    ]
)
