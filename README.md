# پیکره‌ی فنخا

**متن پیراسته و داده‌ی ساختاریافته‌ی «فهرستگان نسخه‌های خطی ایران» (فنخا، ۳۴ جلد، به کوشش مصطفی درایتی)**

این مخزن داده‌ی پایه‌ی سایت [فهارس](https://fahares.net) ([کد سایت](https://github.com/fahares/fahares)) را نگه می‌دارد:
متن ۳۴ جلد فنخا، پارسری که آن را به JSON ساختاریافته تبدیل می‌کند، و آزمون‌های پارسر. خود فایل‌های JSON در git نیستند و
در [Releases](https://github.com/fahares/fahares-corpus/releases) منتشر می‌شوند.

## محتوا

| | شمار |
| :--- | ---: |
| جلد | ۳۴ |
| اثر | ۷۱٬۵۵۰ |
| نسخه | ۳۲۳٬۸۸۴ |
| مدخل ارجاعی | ۱۴٬۸۰۵ |

شمارها از خروجی نگارش v1.1.6 است. حجم متن حدود ۲۰۰ مگابایت، JSON باز حدود ۱٫۱ گیگابایت و آرشیو فشرده حدود ۱۰۵ مگابایت است.

پوشش فیلدهای اصلی نسخه در همین نگارش:

| فیلد | نسخه | درصد |
| :--- | ---: | ---: |
| ارجاع به فهرست کتابخانه (`catalog_citation`) | ۳۲۳٬۷۶۲ | ۹۹٫۹ |
| کاتب یا «بی‌کا» | ۳۱۳٬۱۶۱ | ۹۶٫۷ |
| تاریخ کتابت یا «بی‌تا» | ۳۱۲٬۵۷۱ | ۹۶٫۵ |
| خط | ۲۷۲٬۶۷۷ | ۸۴٫۲ |
| شمار برگ | ۲۴۵٬۷۸۱ | ۷۵٫۹ |
| اندازه | ۲۳۴٬۴۹۰ | ۷۲٫۴ |
| شمار سطر | ۲۰۳٬۳۷۰ | ۶۲٫۸ |
| آغاز | ۱۹۷٬۱۷۳ | ۶۰٫۹ |
| جلد و صحافی | ۱۸۹٬۶۵۷ | ۵۸٫۶ |
| انجام | ۱۷۴٬۹۸۰ | ۵۴٫۰ |
| تملک، وقف و مهر | ۵۹٬۶۴۹ | ۱۸٫۴ |

## ساختار مخزن

| مسیر | محتوا |
| :--- | :--- |
| `text/fankha/` | متن پیراسته‌ی جلدها، `fankha_vol_01.txt` تا `fankha_vol_34.txt` |
| `scripts/fankha_parser.py` | پارسر یک جلد (پایتون، بی وابستگی بیرونی) |
| `scripts/parse_all_volumes.py` | اجرای موازی پارسر روی همه‌ی جلدها |
| `scripts/fankha_parser_v2.py` | نگارش دوم پارسر، در دست کار (پایین را ببینید) |
| `scripts/` (دیگر فایل‌ها) | ممیزی متن، و اسکریپت‌هایی که فایل تصمیم برای اصلاح داده‌ی سایت می‌سازند |
| `tests/` | آزمون‌های پارسر و نمونه‌های طلایی (`tests/gold/`) |
| `catalogs/` | فهرست منابع مقدمه‌ی جلد اول فنخا و راهنمای رموز آن ([راهنما](catalogs/README.md)) |
| `reconciliations/` | تصمیم‌های نسخه‌شناسانه درباره‌ی استدراک‌ها و نام‌های مرکب ([راهنما](reconciliations/README.md)) |
| `json/` | جای فایل‌های JSON (بیرون از git) |

## دریافت JSON

```bash
./scripts/download_json.sh
```

یا مستقیم:

```bash
mkdir -p json
curl -L https://github.com/fahares/fahares-corpus/releases/download/v1.1.6/fankha_json_v1.1.6.tar.gz | tar -xz -C json/
```

خروجی در `json/fankha/fankha_vol_NN.json` است.

## ساختن JSON از متن

```bash
python3 scripts/parse_all_volumes.py
```

همه‌ی جلدها را در چند دقیقه می‌سازد و آمار کل را چاپ می‌کند. آزمون‌ها:

```bash
python3 -m unittest discover tests
```

### نگارش دوم پارسر

`fankha_parser_v2.py` بازنویسی پارسر بر پایه‌ی دسته‌بندی سطرهاست و مرز فیلدها را دقیق‌تر تعیین می‌کند. خروجی آن در
`json/fankha_v2/` نوشته می‌شود و هنوز ریلیز نشده است. فعلاً از آن برای یافتن و اصلاح خطاهای داده‌ی سایت استفاده می‌شود
(اسکریپت‌های `fankha_v2_*_export.py`). طرح آن در
[`docs/plans/fankha-parser-v2.md`](https://github.com/fahares/fahares/blob/main/docs/plans/fankha-parser-v2.md) مخزن
فهارس آمده است.

## ساختار JSON

هر فایل یک جلد است:

```json
{
  "volume_number": 18,
  "total_works": 2496,
  "total_referrals": 605,
  "total_manuscripts": 8460,
  "referrals": [
    { "source_title": "…", "target_title": "…", "volume_number": 18, "page": 12 }
  ],
  "works": [
    {
      "primary_title": "…",
      "alternative_titles": [],
      "subjects": ["…"],
      "languages": ["عربی"],
      "author_name": "…",
      "author_death_date_hijri": null,
      "description": null,
      "incipit": null,
      "bibliography": [],
      "page_start": 15,
      "page_end": 15,
      "raw_text": "…",
      "manuscripts": [
        {
          "sequence_number": 1,
          "city": "تهران",
          "library": "مفتاح",
          "shelfmark": "1207/1",
          "scribe_name": null,
          "is_bika": true,
          "copy_date_raw": "قرن 13",
          "scripts": ["نستعلیق"],
          "folios": null,
          "incipit_text": null,
          "catalog_citation": "[ف: …]",
          "ownership_and_seals": [],
          "is_autograph": false,
          "residual_notes": null,
          "raw_text": "…"
        }
      ]
    }
  ]
}
```

این نمونه فقط فیلدهای اصلی را نشان می‌دهد. هر اثر ۴۵ و هر نسخه ۵۷ فیلد دارد، از جمله شکل خام مقدارها (`*_raw`)،
پرچم‌های نسخه‌شناسی (`is_collated`، `is_ruled`، `is_illuminated`، `is_illustrated`، `has_author_marginalia` و …) و
یادداشت‌ها (`editorial_notes`، `annex_notes`). `raw_text` متن خود مدخل در فنخاست.

## تاریخچه‌ی نسخه‌ها

تغییرهای هر ریلیز در [CHANGELOG.md](CHANGELOG.md) است.

## سپاس

«فهرستگان نسخه‌های خطی ایران» حاصل سال‌ها کار مصطفی درایتی و همکارانش است. این مخزن متن آن را برای جست‌وجو و پژوهش
ساختاریافته می‌کند.

## مجوز

- **متن و داده** (`text/`، `catalogs/`، `reconciliations/`، `tests/gold/` و فایل‌های JSON ریلیزها): [CC BY-SA 4.0](LICENSE-DATA).
  استفاده و بازنشر، تجاری یا غیرتجاری، آزاد است، به این شرط که نام «فهارس» و «فهرستگان نسخه‌های خطی ایران» ذکر شود و داده‌ی
  برگرفته با همین مجوز منتشر شود.
- **کد** (`scripts/` و آزمون‌ها): [GNU AGPL-3.0](LICENSE) (نگارش ۳ یا بالاتر).
