"""The id recipe is shared with arabic-bib and turath-match ("keys v1"). When arabic-bib is installed,
its keys must equal ours byte for byte, or the work ids of the three projects would drift apart."""

import pytest

from turath_catalog.build import work_id_for
from turath_catalog.textnorm import author_key, norm, title_key

arabic_bib = pytest.importorskip("arabic_bib")

CASES = [
    ("إِحْيَاءُ عُلُومِ الدِّين", "الغزالي"),
    ("كتاب الأم (ط دار الوفاء)", "الإمام الشافعي"),
    ("المجموع شرح المهذب - النووي - ت المطيعي", "النووي؛ يحيى بن شرف"),
    ("فتاوى «ابن تيمية» ٧٢٨", "شيخ الإسلام ابن تيمية"),
]


@pytest.mark.parametrize("title, author", CASES)
def test_keys_match_arabic_bib(title, author):
    assert arabic_bib.key_norm(title) == norm(title)
    assert arabic_bib.title_key(title) == title_key(title)
    assert arabic_bib.author_key(author) == author_key(author)
    assert work_id_for(title, author).startswith("w_")
