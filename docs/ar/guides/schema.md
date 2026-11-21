---
title: بنية الجداول
description: الجداول الثمانية وحقولها وكيف يرتبط بعضها ببعض.
order: 1
---

# بنية الجداول

البيانات ثمانية جداول يربط بينها معرّفات ثابتة. الوصف الكامل لكل حقل في
[قاموس البيانات](https://github.com/kmbenjel/turath-catalog/blob/main/docs/data-dictionary.md)، ومخطط JSON
Schema لكل جدول في مجلد `schema/`.

| الجدول | المعرّف | أهم الحقول |
|---|---|---|
| `works` الكتب | `work_id` | العنوان كما ورد، والعنوان مجرّدًا (`title_clean_ar`)، والعناوين الأخرى (`alt_titles_ar`)، المؤلف، القسم بالعربية والإنجليزية، `openiti_uri`، `wikidata_qid`، أرقام الشاملة، عدد الطبعات |
| `editions` الطبعات | `edition_id` | الكتاب، العنوان كما ورد ومجرّدًا وعناوينه الأخرى وملاحظته (`title_ar`، `title_clean_ar`، `alt_titles_ar`، `title_note_ar`)، نوع الطبعة، المحققون، الناشر، المكان، السنة الهجرية والميلادية، رقم الطبعة، المجلدات، الصفحات، مصادر الحقول، درجة الثقة |
| `authors` المؤلفون | `author_id` | الاسم المشهور، الاسم الكامل، سنة الوفاة الهجرية ومقابلها الميلادي، القرن، مصدر السنة ودرجة الثقة فيها، والصف الجامع لصيغ اسم المؤلف الواحد (`canonical_author_id`) |
| `editors` المحققون | `person_id` | الاسم بأتم صيغه، والصيغ الأقصر المدمجة فيه |
| `edition_editors` الإسهامات | — | الطبعة، الشخص، الدور (تحقيق، شرح، جمع، ضبط وتصحيح، تقديم، ترجمة، إشراف)، الترتيب |
| `manuscripts` المخطوطات | `manuscript_id` | الخزانة، رقم الحفظ، درجة الثقة، طبعة مطبوعة للكتاب نفسه |
| `edition_files` ملفات الطبعات | — | ترتيب المجلد، رقمه، حجمه بالبايت |
| `categories` الأقسام | `category_ar` | أقسام الشاملة الأربعون مع أسمائها الإنجليزية |

## المعرّفات

المعرّف بصمة ثابتة لا رقم صف: `work_id` هو `w_` متبوعة بأول عشرة أحرف من بصمة SHA-1 لمفتاح العنوان ومفتاح
المؤلف بعد التطبيع (حذف الحركات والتطويل، وتوحيد الألف والياء والتاء المربوطة، وحذف الألقاب مثل «الإمام»
و«الحافظ»). والوصفة نفسها في أداتي [turath-match](/turath-match/) و[arabic-bib](/arabic-bib/)، فتلتقي
الأدوات الثلاث على المعرّف نفسه دون جدول وسيط.

## قواعد عامة

- الخانة الفارغة في CSV تعني: لا قيمة.
- الحقول المتعددة القيم مفصولة بفاصلة منقوطة `;`.
- حقل `ext_ids` أزواج `نظام:معرّف`، مثل `shamela:6345;waqfeya:66a88e01…`.
- حقل `field_sources` كائن JSON يربط كل حقل بمصدره.
- الإصدار الجديد يزيد أعمدة في آخر الجدول ولا يغيّر عمودًا قائمًا ولا طريقة حساب المعرّفات؛ فما كُتب
  لقراءة الإصدار 0.1.0 يقرأ 0.2.0 كما هو.

## العنوان والمؤلف: كما وردا، وموحَّدَين

- `title_ar` العنوان كما كتبته المكتبة، وقد يحمل عنوانًا آخر بعد «=» أو ملاحظة بين قوسين أو علامة طبعة.
  و`title_clean_ar` العنوان وحده، وهو ما يُعرض ويُطابَق به.
- `author_id` صيغة اسم، و`canonical_author_id` الشخص: اجمع به لتعدّ المؤلفين لا صيغ أسمائهم.

```python
import pandas as pd
authors = pd.read_parquet("turath-catalog-0.2.0/parquet/authors.parquet")
works = pd.read_parquet("turath-catalog-0.2.0/parquet/works.parquet")
person = authors.set_index("author_id").canonical_author_id
print(works.assign(person=works.author_id.map(person)).groupby("person").size().sort_values().tail(5))
```

التفصيل والقواعد في [المصادر والثقة](sources.md).

## مثال

```python
import pandas as pd
eds = pd.read_parquet("turath-catalog-0.2.0/parquet/editions.parquet")
print(eds[eds.confidence == "high"].groupby("publisher_ar").size().sort_values().tail(10))
```
