import pytest

from turath_catalog.hijri import ah_to_ce_range, ce_to_ah_range, century_ah
from turath_catalog.textnorm import author_key, norm, title_key, tokens


@pytest.mark.parametrize(
    "raw, folded",
    [
        ("إِحْيَاءُ عُلُومِ الدِّين", "احيا علوم الدين"),  # hamza dropped, as in every Warraq key
        ("مُقَدِّمَة ابن خلدون", "مقدمه ابن خلدون"),
        ("فتاوى «ابن تيمية» ٧٢٨", "فتاوي ابن تيميه 728"),
        ("الـــنووي", "النووي"),
        ("", ""),
        (None, ""),
    ],
)
def test_norm(raw, folded):
    assert norm(raw) == folded


def test_title_key_drops_tails_and_kitab():
    assert title_key("كتاب الأم (ط دار الوفاء)") == "الام"
    assert title_key("المجموع شرح المهذب - النووي - ت المطيعي") == "المجموع شرح المهذب"
    assert title_key("كتاب") == "كتاب"


def test_author_key_takes_first_form_without_honorifics():
    assert author_key("الإمام الحافظ النووي") == "النووي"
    assert author_key("الشاشي؛ إسحاق بن إبراهيم") == "الشاشي"
    assert author_key("") == ""


def test_tokens_drop_common_name_parts():
    assert tokens("محمد بن أحمد الذهبي") == {"الذهبي"}


@pytest.mark.parametrize(
    "ah, ce",
    [
        (1, (622, 623)),
        (11, (632, 633)),
        (676, (1277, 1278)),
        (728, (1327, 1328)),
        (808, (1405, 1406)),
        (1420, (1999, 2000)),
        (1446, (2024, 2025)),
    ],
)
def test_ah_to_ce(ah, ce):
    assert ah_to_ce_range(ah) == ce


def test_ce_to_ah_is_the_inverse():
    for ah in (1, 100, 505, 676, 1000, 1300, 1445):
        lo, hi = ah_to_ce_range(ah)
        assert ce_to_ah_range(lo)[0] <= ah <= ce_to_ah_range(hi)[1]


def test_invalid_years():
    with pytest.raises(ValueError):
        ah_to_ce_range(0)
    with pytest.raises(ValueError):
        ce_to_ah_range(100)


def test_century():
    assert [century_ah(y) for y in (1, 100, 101, 676, 1400, 1401)] == [1, 1, 2, 7, 14, 15]
