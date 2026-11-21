import pytest

from turath_catalog.build import work_id_for
from turath_catalog.textnorm import title_key
from turath_catalog.titles import TitleParts, mark_agrees, split_title


@pytest.mark.parametrize(
    "title, clean, alts",
    [
        ("الجامع لأحكام القرآن = تفسير القرطبي", "الجامع لأحكام القرآن", ("تفسير القرطبي",)),
        ("الطبقات الكبير = الطبقات الكبرى = طبقات ابن سعد", "الطبقات الكبير", ("الطبقات الكبرى", "طبقات ابن سعد")),
        ("مفاتيح الغيب=التفسير الكبير=تفسير الرازي", "مفاتيح الغيب", ("التفسير الكبير", "تفسير الرازي")),
        ("نقد النثر (أو كتاب البيان)", "نقد النثر", ("كتاب البيان",)),
        ("اللباب في علوم الكتاب (تفسير ابن عادل)", "اللباب في علوم الكتاب", ("تفسير ابن عادل",)),
        ("الكتاب (كتاب سيبويه)", "الكتاب", ("كتاب سيبويه",)),
        ("المسند = المسند", "المسند", ()),  # a title is not its own other title
    ],
)
def test_other_titles(title, clean, alts):
    p = split_title(title)
    assert (p.clean, p.alts) == (clean, alts)
    assert not p.notes and not p.publisher_marks and not p.editor_marks


def test_what_comes_with_the_book_stays_with_the_title_not_with_its_second_name():
    p = split_title("رد المحتار على الدر المختار = حاشية ابن عابدين، ويليه قرة عيون الأخيار وتقريرات الرافعي")
    assert p.clean == "رد المحتار على الدر المختار، ويليه قرة عيون الأخيار وتقريرات الرافعي"
    assert p.alts == ("حاشية ابن عابدين",)


@pytest.mark.parametrize(
    "title, clean, note",
    [
        ("تفسير يحيى بن سلام (من النحل إلى الصافات)", "تفسير يحيى بن سلام", "من النحل إلى الصافات"),
        ("مجموعة الرسائل والمسائل النجدية (الجزء الأول)", "مجموعة الرسائل والمسائل النجدية", "الجزء الأول"),
        ("الأحكام ( الشعبي )", "الأحكام", "الشعبي"),
        ("رحمة للعالمين (مترجم)", "رحمة للعالمين", "مترجم"),
        ("فهرس المخطوطات [القسم الثاني]", "فهرس المخطوطات", "القسم الثاني"),
        ("الفتاوى (رسالة ماجستير)", "الفتاوى", "رسالة ماجستير"),  # a thesis note, not another title
        ("الوفيات (تاريخ 1300)", "الوفيات", "تاريخ 1300"),  # a genre word with a number is a remark
        ("الأم (ط 2)", "الأم", "ط 2"),  # an edition number is not a publisher
        ("الأم (ط. الثانية)", "الأم", "ط. الثانية"),
        ("الرسالة (ت 204 هـ)", "الرسالة", "ت 204 هـ"),  # a death date is not an editor
        ("الحماسة البصرية (ط. قديمة)", "الحماسة البصرية", "ط. قديمة"),  # the kind of edition is not a publisher
        ("تفسير الطبري (ط حجرية)", "تفسير الطبري", "ط حجرية"),
        ("صحيح البخاري (كتاب الإيمان)", "صحيح البخاري", "كتاب الإيمان"),  # a part of the book, not another title
        ("شرح صحيح مسلم (مقدمة المحقق)", "شرح صحيح مسلم", "مقدمة المحقق"),
        ("مسند أحمد (مسند المكثرين من الصحابة)", "مسند أحمد", "مسند المكثرين من الصحابة"),  # same genre word: a part
    ],
)
def test_remarks(title, clean, note):
    p = split_title(title)
    assert (p.clean, p.notes) == (clean, (note,))
    assert not p.alts and not p.publisher_marks and not p.editor_marks


@pytest.mark.parametrize(
    "title, clean, mark",
    [
        ("الحماسة البصرية (ط. الخانجي)", "الحماسة البصرية", "الخانجي"),
        ("إعجاز القرآن والبلاغة النبوية (ط - الكتاب)", "إعجاز القرآن والبلاغة النبوية", "الكتاب"),
        ("قرى الضيف (ط أضواء السلف)", "قرى الضيف", "أضواء السلف"),
        ("الاقتراح في أصول النحو ط القلم", "الاقتراح في أصول النحو", "القلم"),
        ("الفصل في الملل والأهواء والنحل، وبهامشه الملل والنحل- ط. صبيح", "الفصل في الملل والأهواء والنحل، وبهامشه الملل والنحل", "صبيح"),
    ],
)
def test_publisher_marks(title, clean, mark):
    assert split_title(title) == TitleParts(clean=clean, publisher_marks=(mark,))


@pytest.mark.parametrize(
    "title, clean, mark",
    [
        ("الورع (ت - السعدني)", "الورع", "السعدني"),
        ("سنن ابن ماجه مع أحكام الألباني. ت- مشهور", "سنن ابن ماجه مع أحكام الألباني", "مشهور"),
        ("البدر التمام شرح بلوغ المرام ت الزبن", "البدر التمام شرح بلوغ المرام", "الزبن"),
        ("الأربعون (تحقيق بدر البدر)", "الأربعون", "بدر البدر"),
    ],
)
def test_editor_marks(title, clean, mark):
    assert split_title(title) == TitleParts(clean=clean, editor_marks=(mark,))


def test_both_marks_and_a_second_title_at_once():
    p = split_title("السنن = سنن أبي داود (ط. الرسالة) ت الأرناؤوط")
    assert p == TitleParts("السنن", alts=("سنن أبي داود",), publisher_marks=("الرسالة",), editor_marks=("الأرناؤوط",))


@pytest.mark.parametrize(
    "title",
    [
        "آداب الفتوى والمفتي والمستفتي",
        "المثل السائر في أدب الكاتب والشاعر، ويليه الفلك الدائر على الأدب الثائر",
        "تاريخ ابن حجي حوادث ووفيات 796-815 هـ",
        "«لكن» في القرآن الكريم دراسة تركيبية دلالية",
        "شرح الوسيط في خط ابن مقلة",  # «ط» and «ت» inside words are not marks
        "هل انتشر الإسلام بالسيف؟",
        "المنتقى ط 2",  # no publisher's name after «ط»: left alone
    ],
)
def test_plain_titles_are_untouched(title):
    assert split_title(title) == TitleParts(clean=title)


@pytest.mark.parametrize(
    "title, author, clean",
    [
        ("تصحيح التنبيه، ويليه", "", "تصحيح التنبيه"),  # a joiner with nothing after it
        ("إعلام الأريب بحدوث بدعة المحاريب ويليها", "", "إعلام الأريب بحدوث بدعة المحاريب"),
        ("الإمام الباقلاني وآراؤه الاعتقادية.", "", "الإمام الباقلاني وآراؤه الاعتقادية"),
        ("أخبار مكة وما جاء فيها من الآثار -الأزرقي", "الأزرقي", "أخبار مكة وما جاء فيها من الآثار"),
        ("أخبار مكة - الأزرقي", "الفاكهي", "أخبار مكة - الأزرقي"),  # not this row's author: kept
        ("  الرسالة   القشيرية  ", "", "الرسالة القشيرية"),
        ("الأم (الجزء", "", "الأم الجزء"),  # an unpaired bracket
        ("(مخطوط)", "", "مخطوط"),  # nothing but a bracket: the title is what it holds
        ("", "", ""),
        (None, "", ""),
    ],
)
def test_tidying(title, author, clean):
    assert split_title(title, author).clean == clean


@pytest.mark.parametrize(
    "mark, value, agrees",
    [
        ("الخانجي", "مكتبة الخانجي", True),
        ("المكتب الإسلامي", "المكتب الإسلامي بيروت", True),
        ("العراق", "المجمع العلمي العراقي", True),
        ("دار الفاروق", "الفاروق الحديثة للطباعة والنشر", True),  # «دار» alone decides nothing
        ("غراس", "مكتبة المعارف", False),
        ("القلم", "دار البيروتي دمشق", False),
        ("الميمني", "عبد العزيز الميمني", True),
        ("زهوي", "أحمد بن مونس العنزي", False),
        ("دار", "دار الفكر", False),
        ("الخانجي", "", False),
    ],
)
def test_mark_agrees(mark, value, agrees):
    assert mark_agrees(mark, value) is agrees


@pytest.mark.parametrize(
    "title",
    ["الحماسة البصرية (ط. الخانجي)", "الورع (ت - السعدني)", "تفسير يحيى بن سلام (من النحل إلى الصافات)", "الاقتراح في أصول النحو ط القلم"],
)
def test_the_clean_title_has_the_key_of_the_title_as_given(title):
    """Ids hash the title as given; for these forms the clean title gives the same key, so matching on it is safe."""
    clean = split_title(title).clean
    assert title_key(clean) == title_key(title)
    assert work_id_for(clean, "مؤلف") == work_id_for(title, "مؤلف")
