---
title: البدء السريع
description: أول استعلام في أقل من دقيقة.
order: 3
---

# البدء السريع

## 1. نظرة عامة على العيّنة

```bash
pip install "turath-catalog[pandas]"
turath-catalog info sample
```

يطبع البرنامج عدد الكتب والطبعات والمؤلفين، ونسبة الطبعات التي عُرف محققها وناشرها وسنتها، وعدد الروابط.

## 2. طبعات كتاب واحد

```python
import pandas as pd
works = pd.read_parquet("turath-catalog-0.1.0/parquet/works.parquet")
eds = pd.read_parquet("turath-catalog-0.1.0/parquet/editions.parquet")
tabari = works.loc[works.title_ar == "جامع البيان عن تأويل آي القرآن", "work_id"]
print(eds[eds.work_id.isin(tabari)][["editors_ar", "publisher_ar", "year_ah", "volumes"]])
```

فتظهر طبعات تفسير الطبري الثلاث: طبعة محمود وأحمد شاكر، وطبعة عبد الله التركي في 25 مجلدًا، مع ناشر كل منها وسنته.

## 3. كل ما حققه محقق

```python
editors = pd.read_parquet("turath-catalog-0.1.0/parquet/editors.parquet")
credits = pd.read_parquet("turath-catalog-0.1.0/parquet/edition_editors.parquet")
harun = editors[editors.name_ar.str.contains("عبد السلام") & editors.name_ar.str.contains("هارون")]
print(credits.merge(harun, on="person_id").merge(eds, on="edition_id")[["title_ar", "publisher_ar", "year_ce"]])
```

## 4. المؤلفون حسب القرن

```python
authors = pd.read_parquet("turath-catalog-0.1.0/parquet/authors.parquet")
print(authors.groupby("century_ah").size())
```

## 5. التحقق من سلامة الجداول

```bash
turath-catalog validate turath-catalog-0.1.0
```

يفحص الأمر أنواع الحقول، وتفرّد المعرّفات، وأن لكل طبعة كتابًا، واتساق السنة الهجرية مع الميلادية، وأن لا
مسار ملف ولا بريد ولا رابط تسرّب إلى البيانات.
