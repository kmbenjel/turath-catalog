---
title: التثبيت
description: طرق الحصول على بيانات فهرس التراث وأدواته.
order: 2
---

# التثبيت والحصول على البيانات

## الطريق الأيسر: ملفات جاهزة

الجداول كاملة منشورة بثلاث صيغ في صفحة الإصدارات على GitHub وفي Hugging Face:

| الصيغة | تصلح لـ |
|---|---|
| CSV | جداول البيانات (Excel وLibreOffice) وأي لغة برمجة |
| Parquet | pandas وR وDuckDB، وهي أصغر حجمًا وأسرع قراءة |
| JSON Lines | البرامج التي تقرأ JSON سطرًا سطرًا |

!!! tip "ملاحظة"
    ملفات CSV بترميز UTF-8. إن ظهرت الحروف العربية مشوّهة في Excel فافتح الملف من «بيانات ← من نص/CSV» واختر الترميز UTF-8.

## من Hugging Face

```bash
pip install datasets
```

```python
from datasets import load_dataset
editions = load_dataset("kmbenjel/turath-catalog", "editions", split="train")
```

## الأداة نفسها (Python 3.10 فما فوق)

```bash
pip install turath-catalog
```

ومعها pandas لمن يريد الجداول في DataFrame:

```bash
pip install "turath-catalog[pandas]"
```

وفي الحزمة عيّنة من 149 كتابًا تكفي للتجربة دون تنزيل شيء آخر:

```bash
turath-catalog info sample
```

ولمن يستعمل `uv` دون تثبيت:

```bash
uvx turath-catalog info sample
```
