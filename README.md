# پیکرۀ فنخا

**متن پیراسته و دادۀ ساختاریافتۀ «فهرستگان نسخه‌های خطی ایران» (فنخا، ۳۴ جلد، به کوشش مصطفی درایتی)**

این مخزن دادۀ پایۀ سایت [فهارس](https://fahares.net) ([کد سایت](https://github.com/fahares/fahares)) را نگه می‌دارد:
متن ۳۴ جلد فنخا، پارسری که آن را به JSON ساختاریافته تبدیل می‌کند، و آزمون‌های پارسر. خود فایل‌های JSON در git نیستند و
در [Releases](https://github.com/fahares/fahares-corpus/releases) منتشر می‌شوند.

## محتوا

| | شمار |
| :--- | ---: |
| جلد | ۳۴ |
| اثر | ۷۱٬۵۵۰ |
| نسخه | ۳۲۳٬۸۸۴ |
| مدخل ارجاعی | ۱۴٬۸۰۵ |

شمارها از خروجی نگارش v1.1.6 (پارسر یکم) است؛ شمارهای نگارش دوم پایین‌تر آمده. حجم متن حدود ۲۰۰ مگابایت، JSON باز حدود ۱٫۱ گیگابایت و آرشیو فشرده حدود ۱۰۵ مگابایت است.

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
| `text/fankha/` | متن پیراستۀ جلدها، `fankha_vol_01.txt` تا `fankha_vol_34.txt` |
| `scripts/fankha_parser.py` | پارسر یک جلد (پایتون، بی وابستگی بیرونی) |
| `scripts/parse_all_volumes.py` | اجرای موازی پارسر روی همۀ جلدها |
| `scripts/fankha_parser_v2.py` | نگارش دوم پارسر، که خروجی ریلیزهای v2 را می‌سازد (پایین را ببینید) |
| `scripts/` (دیگر فایل‌ها) | ممیزی متن، و اسکریپت‌هایی که فایل تصمیم برای اصلاح دادۀ سایت می‌سازند |
| `tests/` | آزمون‌های پارسر و نمونه‌های طلایی (`tests/gold/`) |
| `catalogs/` | فهرست منابع مقدمۀ جلد اول فنخا و راهنمای رموز آن ([راهنما](catalogs/README.md)) |
| `reconciliations/` | تصمیم‌های نسخه‌شناسانه دربارۀ استدراک‌ها و نام‌های مرکب ([راهنما](reconciliations/README.md)) |
| `json/` | جای فایل‌های JSON (بیرون از git) |

## دریافت JSON (نگارش یکم)

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

همۀ جلدها را در چند دقیقه می‌سازد و آمار کل را چاپ می‌کند. آزمون‌ها:

```bash
python3 -m unittest discover tests
```

### نگارش دوم پارسر

`fankha_parser_v2.py` بازنویسی پارسر بر پایۀ دسته‌بندی سطرهاست و مرز فیلدها را دقیق‌تر تعیین می‌کند. خروجی آن در
`json/fankha_v2/` نوشته می‌شود و از نگارش v2.9.0 در ریلیزها منتشر می‌شود (پایین را ببینید). ساختار آن با ساختار
نگارش یکم فرق دارد و جایگزین سرراست آن نیست. اسکریپت‌های `fankha_v2_*_export.py` از همین خروجی فایل تصمیم برای اصلاح
دادۀ سایت می‌سازند. طرح پارسر در
[`docs/plans/fankha-parser-v2.md`](https://github.com/fahares/fahares/blob/main/docs/plans/fankha-parser-v2.md) مخزن
فهارس آمده است.

```bash
python3 scripts/fankha_parser_v2.py        # همۀ جلدها، حدود سه دقیقه
```

## دادۀ نگارش دوم (`fankha/v2`)

```bash
./scripts/download_json.sh v2
```

یا مستقیم:

```bash
mkdir -p json
curl -L https://github.com/fahares/fahares-corpus/releases/download/v2.9.0/fankha_json_v2.9.0.tar.gz | tar -xz -C json/
```

خروجی در `json/fankha_v2/fankha_vol_NN.json` است. متن جلدها در git ممکن است از متن آخرین ریلیز تازه‌تر باشد؛
`text_commit` هر فایل نشان می‌دهد از کدام کامیت متن ساخته شده است. شمارها در نگارش v2.9.0:

| | شمار |
| :--- | ---: |
| اثر | ۷۱٬۷۲۰ |
| نسخه | ۳۲۲٬۰۸۶ |
| مدخل ارجاعی | ۱۴٬۸۳۳ |
| یادداشت نسخه | ۱۸۲٬۰۶۰ |

شمار نسخه از نگارش یکم کمتر است، چون سطرهای «همان نسخه بالا» به نسخۀ خودشان پیوسته‌اند؛ شمار اثر بیشتر است، چون مرز
مدخل‌ها دقیق‌تر خوانده می‌شود.

| فیلد | نسخه | درصد |
| :--- | ---: | ---: |
| ارجاع به فهرست کتابخانه (`catalog_citation`) | ۳۲۱٬۹۷۸ | ۱۰۰٫۰ |
| کاتب، «بی‌کا» یا خط مؤلف | ۳۱۵٬۳۷۸ | ۹۷٫۹ |
| تاریخ کتابت یا «بی‌تا» | ۳۱۵٬۳۳۹ | ۹۷٫۹ |
| خط | ۲۷۵٬۱۰۳ | ۸۵٫۴ |
| شمار برگ یا صفحه | ۲۴۶٬۸۳۳ | ۷۶٫۶ |
| اندازه | ۲۳۶٬۱۷۱ | ۷۳٫۳ |
| شمار سطر | ۱۹۹٬۸۹۱ | ۶۲٫۱ |
| آغاز | ۱۹۷٬۵۹۵ | ۶۱٫۳ |
| جلد و صحافی | ۱۹۱٬۲۸۴ | ۵۹٫۴ |
| انجام | ۱۷۵٬۰۶۸ | ۵۴٫۴ |
| تملک، وقف، مهر و ورود | ۶۲٬۵۰۱ | ۱۹٫۴ |

هر فایل یک جلد است، با `schema: "fankha/v2"`، `parser_version` و `text_commit` (کامیت متنی که از آن ساخته شده):

```json
{
  "schema": "fankha/v2",
  "parser_version": "2.9.0",
  "text_commit": "a38c82060d54eb35180ee69597a9821e0234bb0e",
  "volume": 18,
  "total_works": 2519,
  "total_copies": 8458,
  "referrals": [{"source": "سر الاسرار", "target": "سر الابرار", "vol": 18, "page": 19, "line": 261}],
  "works": [
    {
      "key": {"vol": 18, "ordinal": 56},
      "provenance": {"page_start": 36, "page_end": 43, "line_start": 1118, "line_end": 1461},
      "title": "السرائر الحاوى لتحریر الفتاوی",
      "subjects": ["فقه"],
      "languages": ["عربی"],
      "author": {"name": "ابن ادریس، محمد بن احمد", "name_raw": "ابن ادریس، محمد بن احمد", "epithet": null, "hedge": null, "transliteration": "ebn-e edrīs, mohammad ebn-e ahmad", "death": {"raw": "543 - 598 قمری", "hedge": null, "century": 6, "sort_year": 598}},
      "composition": {"date": "588ق", "place": null},
      "description": "مشتمل است بر یک دوره کامل فقهی از (طهارت تا دیات) که ارزش و …",
      "incipit": "بسمله الحمدلله الذی خلق الانسان فعدله وعلمه البیان ففضله و …",
      "explicit": "و العفو عمن ظلمک تمت الاحادیث المنتزعة من کتاب العیون و …",
      "bibliography": ["الذریعة 155/12", "ریحانة الأدب 377/7 و 378/7"],
      "copies": [
        {
          "key": {"seq": 26, "ordinal": 27},
          "provenance": {"page_start": 38, "page_end": 38, "line_start": 1224, "line_end": 1227},
          "city": "تهران",
          "library": "دائرة المعارف",
          "shelfmark": "784",
          "incipit": {"text": null, "same_as_work": true},
          "explicit": {"text": null, "same_as_work": true},
          "script_raw": "نسخ پخته",
          "scripts": [{"type": "نسخ", "qualifiers": ["پخته"]}],
          "scribes": [{"name": "ابراهیم بن محمد بن علی بن احمد حرفوش عاملی اصلا امامی …", "hedge": null, "portion": null}],
          "no_scribe": false,
          "is_autograph": false,
          "copy_date": {"raw": "چهارشنبه 16 ذیقعده 1064ق", "hedge": null, "century": 11, "sort_year": 1064},
          "undated": false,
          "copy_place": null,
          "folios": "256گ",
          "lines": "27 سطر",
          "text_dimensions": "11×20",
          "dimensions": "18×29سم",
          "paper": "نخودی",
          "binding": "مقوایی تیماج سرخ پوشانده",
          "ownership": ["علی بن محمد بن الحسن بن زین الدین عاملی مورخ 1073ق"],
          "seals": ["«... طباطبائی» (چهارگوش)"],
          "notes": [{"type": "endowment", "text": "با وقف‌نامه مبنی بر اینکه این مجلد و یکصد و هشتاد و سه جلد …", "hedge": null, "also": ["contents"], "by_author": false, "by_author_hedge": null, "seal": null}, {"type": "endowment", "text": "وقف 14 معصوم در شهر اصفهان باشد. به تاریخ 1225ق", "hedge": null, "also": [], "by_author": false, "by_author_hedge": null, "seal": null}],
          "flags": [],
          "catalog_citation": "[ف: 2 - 139]",
          "raw_text": "26. تهران؛ دائرة المعارف؛ شماره نسخه: 784\nآغاز و انجام: …"
        }
      ]
    }
  ]
}
```

این نمونه (اثر ۵۶ جلد ۱۸ و نسخۀ ۲۷ آن، با متن‌های کوتاه‌شده) فیلدهای اصلی را نشان می‌دهد؛ هر اثر ۳۶ و هر نسخه ۴۰ فیلد دارد. چند نکته:

- **شمارۀ اثر:** `key.ordinal` شمارۀ اثر در جلد در همین نگارش است و با شمارۀ نگارش یکم (که در نشانی آثار سایت فهارس
  آمده) یکی نیست، چون شمار مدخل‌ها فرق دارد.
- **کاتبان:** `scribes` فهرست است؛ کاتب هر جزء و دست‌های یک مرقع هر کدام یک عضو آن‌اند، با `portion` و `note`.
- **تاریخ:** `copy_date.raw` متن چاپی است؛ تاریخ دوم یا توضیح تاریخ در `copy_date.note` می‌آید.
- **یادداشت‌ها:** هر تکۀ بی برچسب شرح نسخه یک عضو `notes` است، با نوعی که قاعدۀ پارسر داده. نوع دقیق‌ترِ داوری‌شده
  در `reconciliations/fankha_note_types.jsonl` است (کلید: دوازده نویسۀ نخست `sha1` متن یادداشت).
- **آنچه خوانده نشده:** `unparsed` باید تهی باشد؛ در این نگارش در همۀ نسخه‌ها تهی است.

دقت: روی نمونۀ طلایی (۱۱۰ اثر) ۹۹٫۴ درصد وارسی‌ها درست است. این عدد خوش‌بینانه است، چون پارسر با همین نمونه تنظیم شده؛
حدود دو هزار تکه از شرح نسخه‌ها هنوز یادداشت مانده‌اند در حالی که ادامۀ یک فیلدند.

## ساختار JSON نگارش یکم

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

## تاریخچۀ نسخه‌ها

تغییرهای هر ریلیز در [CHANGELOG.md](CHANGELOG.md) است.

## سپاس

«فهرستگان نسخه‌های خطی ایران» حاصل سال‌ها کار مصطفی درایتی و همکارانش است. این مخزن متن آن را برای جست‌وجو و پژوهش
ساختاریافته می‌کند.

## مجوز

- **متن و داده** (`text/`، `catalogs/`، `reconciliations/`، `tests/gold/` و فایل‌های JSON ریلیزها): [CC BY-SA 4.0](LICENSE-DATA).
  استفاده و بازنشر، تجاری یا غیرتجاری، آزاد است، به این شرط که نام «فهارس» و «فهرستگان نسخه‌های خطی ایران» ذکر شود و دادۀ
  برگرفته با همین مجوز منتشر شود.
- **کد** (`scripts/` و آزمون‌ها): [GNU AGPL-3.0](LICENSE) (نگارش ۳ یا بالاتر).
