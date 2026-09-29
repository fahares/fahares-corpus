#!/usr/bin/env python3
"""
Comprehensive audit and report generator for shelfmark metadata leaks across 34 volumes of Fahares.
Features:
1. Contextual verification: inspects subsequent lines in the text file to distinguish:
   - TRUE STRUCTURAL LEAKS: Lines where the line break was missed and codicology/content notes were swallowed.
   - SHELFMARK TYPOS (False Positives): Headers that already broke cleanly, but have an internal OCR semicolon or library tag (e.g. '24؛ مشهد' or '443/1؛ کر').
2. Non-backtracking, strict extraction:
   - Supports attached letters including الف, ج, ی, etc. (e.g. 54الف, 312/6ج, 67ی, 16315/4ی, 45ض/6).
   - Long collection names (طباطبائی, فیروز, عکسی, حکمت, ...) precede short single-letter codes (-ط, -ف, -عکس).
   - Single-letter suffixes ([گضفطعمشکنرصایجودب]) must NOT be followed by another Persian letter ((?![آ-ی])) so they never clip words like بی‌کا, کا:, شامل, بیاض, جنگ, مشهد.
   - Attached collection tags (عکسی, مشهد, بخش\\d+, حاشیه) are recognized as integral parts of the shelfmark.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

CORPUS_DIR = Path("/home/tabib/projects/apps/fahares-corpus")
TEXT_DIR = CORPUS_DIR / "text"
REPORTS_DIR = CORPUS_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PAGE_TAG_PATTERN = re.compile(r'<!--\s*page:\s*(\d+)\s*-->')

# Known donor collection names that form part of a compound shelfmark (e.g. 250-فیروز, 139 سرود)
COLLECTION_NAMES = [
    'طباطبائی', 'فیروز', 'عکسی', 'حکمت', 'خوئی', 'فیاض', 'مفتاح', 'بهار', 'مشکوة',
    'دهخدا', 'اصغر مهدوی', 'مهدوی', 'سنا', 'حسینی', 'کر', 'مشهد', 'فرخ',
    'معزی', 'سروری', 'درحاشیه', 'سرود', 'صدر', 'معیری'
]

# Exclude 'و' from attached single letters to avoid conflicting with conjunction 'و'
ATTACHED_LETTERS = r'(?:الف|[بجدهزحطیکلمنسعفصقرشتثخذضظغگچپژ])(?![آ-ی\d])'
HYPHEN_LETTERS = r'[-ـ]\s*[آ-ی](?![آ-ی\d])'

PIECE = (
    r'-?\d+(?:[/\-]\d+)*'
    r'(?:\s*\([آ-ی]\))?'
    r'(?:-(?:' + '|'.join(COLLECTION_NAMES) + r'|عکس|[آ-ی]))?'
    r'(?:[/\-][آ-ی](?![آ-ی]))?'
    r'(?:\s*(?:' + '|'.join(COLLECTION_NAMES) + r'))?'
    r'(?:[/\-]\d+)*'
    r'(?:\s*\([آ-ی]\))?'
    r'(?:عکسی|مشهد|بخش\s*\d+|حاشیه|' + ATTACHED_LETTERS + r')?'
    r'(?:[/\-]\d+)*'
    r'(?:\s*\([آ-ی]\))?'
    r'(?:\s*' + HYPHEN_LETTERS + r')*'
    r'(?:\s+[آ-ی](?![آ-ی\d]))?'
)

SHELFMARK_STRICT_PREFIX = re.compile(
    r'^('
    r'عکسی\s+بدون\s+شماره(?:\s*/\s*\d+)?'
    r'|\d*مجموعه\s+بدون\s+شماره(?:\s*/\s*\d+)?'
    r'|بدون\s+شماره(?:\s*/\s*\d+)?'
    r'|نامعلوم(?:\s*/\s*\d+)?'
    r'|ندارد'
    r'|جنگ\s*\d+(?:/\d+)?'
    r'|مجموعه\s*\d+(?:/\d+)?'
    r'|[A-Za-z\.]+\s*[\d\w\.\-]+'
    r'|' + PIECE + r'(?:\s*(?:و|تا|-)\s*' + PIECE + r')*'
    r'|[ضفطعشكمگ]\s*\d+(?:[/\-]\d+)*(?:[گضفطعمشک]|عکسی)?'
    r')'
    r'(?:\s*[-ـ؛]?\s*(?:' + '|'.join(COLLECTION_NAMES) + r'|[آ-ی](?![آ-ی\d]))\b)?'
)

# Standard codicology keywords
CODICOLOGY_KEYWORDS = [
    r'خط\s*:', r'کا\s*:', r'بی‌کا\b', r'بی\s+کا\b', r'بى‌كا\b', r'بى\s+كا\b',
    r'تا\s*:', r'بی‌تا\b', r'بی\s+تا\b', r'بى‌تا\b', r'بى\s+تا\b',
    r'نسخه\s+اصل\s*:', r'نسخه\s+اصلی\s*:', r'اصل\s+نسخه\s*:', r'افتادگی\s*:', r'آغاز\s*:', r'انجام\s*:',
    r'اندازه\s*:', r'قطع\s*:', r'کاغذ\s*:', r'جلد\s*:', r'تملک\s*:', r'واقف\s*:', r'وقف\s*:',
    r'مصحح\b', r'محشی\b', r'مجدول\b', r'رکابه\b', r'بلاغ\b', r'چاپ\s*:', r'چاپی\s+است\b',
    r'\[ف\s*:', r'\[نشریه\s*:', r'\[مؤید\s*:', r'\[دلیل\s+المخطوطات\s*:', r'\[رایانه\]', r'\[د\.ث\b',
    r'همان\s+نسخه(?:\s+بالا|\s+اصل)?\b'
]
CODICOLOGY_REGEX = re.compile('|'.join(CODICOLOGY_KEYWORDS))

def extract_clean_shelfmark_and_remainder(raw_shelfmark):
    cleaned = raw_shelfmark.strip()
    m = SHELFMARK_STRICT_PREFIX.match(cleaned)
    if m:
        extracted = m.group(0).strip().rstrip('؛').strip()
        rem = cleaned[m.end():].strip().lstrip('؛').strip()
        return extracted, rem, True
    
    # Fallback if no strict prefix matched
    if cleaned.endswith('؛'):
        return cleaned[:-1].strip(), "", False
        
    return cleaned, "", False

def classify_remainder(rem_text):
    if not rem_text:
        return "خطای نگارشی (نقطه‌ویرگول زاید یا علامت اختصاری)"
    if CODICOLOGY_REGEX.search(rem_text):
        if re.match(r'^(?:خط:|کا:|بی‌کا|تا:|بی‌تا|نسخه اصل)', rem_text):
            return "الگوی الف: اتصال مستقیم به مشخصات کالبدشناسی (خط، کاتب، تاریخ...)"
        else:
            return "الگوی ب: اتصال به یادداشت محتوا/نسخه + مشخصات کالبدشناسی"
    if rem_text.startswith('[') and rem_text.endswith(']'):
        return "الگوی ج: اتصال مستقیم به ارجاع فهرستگان [ف: ...]"
    return "الگوی د: یادداشت محتوایی یا توضیحی کوتاه بدون مشخصات کالبدشناسی"

def audit_all():
    vol_files = list(TEXT_DIR.glob("fankha/fankha_vol_*.txt")) or list(TEXT_DIR.glob("fankha_vol_*.txt")) or list(TEXT_DIR.glob("fahares_vol_*.txt"))
    vol_files = sorted(vol_files, key=lambda p: int(re.search(r'\d+', p.name).group()))
    
    true_leaks = []
    shelfmark_typos = []
    
    vol_stats = defaultdict(int)
    category_stats = defaultdict(int)
    
    for vol_path in vol_files:
        vol_num = int(re.search(r'\d+', vol_path.name).group())
        current_page = None
        
        with open(vol_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line_no, raw_line in enumerate(lines, start=1):
            p_tags = PAGE_TAG_PATTERN.findall(raw_line)
            if p_tags:
                current_page = int(p_tags[-1])
            
            clean_l = PAGE_TAG_PATTERN.sub('', raw_line).strip()
            if 'شماره نسخه:' not in clean_l and 'شماره نسخه :' not in clean_l:
                continue
            
            header_match = re.match(r'^(\d+[\.\s]\s*)?([^؛]+)؛\s*([^؛]+)؛\s*شماره نسخه:\s*(.*)', clean_l)
            if not header_match:
                continue
            
            seq_str = header_match.group(1)
            seq = int(re.search(r'\d+', seq_str).group()) if seq_str and re.search(r'\d+', seq_str) else None
            city = header_match.group(2).strip()
            lib = header_match.group(3).strip()
            raw_sm = header_match.group(4).strip()
            
            # Check context: inspect next lines skipping blank lines and page tags
            next_lines = []
            for l in lines[line_no:line_no+25]:
                sl = PAGE_TAG_PATTERN.sub('', l).strip()
                if not sl:
                    continue
                if re.match(r'^\d+[\.\s]', sl) or re.match(r'^[●■▪◆]', sl):
                    break
                next_lines.append(sl)
            
            has_cod_in_next = any(CODICOLOGY_REGEX.search(nl) for nl in next_lines)
            has_cod_in_header = bool(CODICOLOGY_REGEX.search(raw_sm) or re.search(r'\[[^\]]+\]', raw_sm))
            
            # Extract shelfmark and remainder
            clean_sm, rem_text, split_ok = extract_clean_shelfmark_and_remainder(raw_sm)
            
            # Case 1: The next line ALREADY has the full codicology and header has no codicology
            if has_cod_in_next and not has_cod_in_header:
                if '؛' in raw_sm.rstrip('؛ '):
                    shelfmark_typos.append({
                        "volume": vol_num,
                        "file": vol_path.name,
                        "line_number": line_no,
                        "page": current_page,
                        "city": city,
                        "library": lib,
                        "raw_shelfmark": raw_sm,
                        "clean_shelfmark": clean_sm,
                        "issue": "وجود نقطه‌ویرگول زاید در دل شماره نسخه (مانند '24؛ مشهد' یا '443/1؛ کر')"
                    })
                # No leak happened here! Next line has the manuscript entry!
                continue
            
            # Case 2: Remainder is completely empty (no leak)
            if not rem_text:
                continue
            
            # Case 3: Remainder has NO codicology keywords and is very short (1-2 words)
            # This is a shelfmark suffix or collection tag, NOT a leak of codicological description.
            if not CODICOLOGY_REGEX.search(rem_text) and len(rem_text.split()) <= 2:
                continue
            
            category = classify_remainder(rem_text)
            
            rec = {
                "volume": vol_num,
                "file": vol_path.name,
                "line_number": line_no,
                "page": current_page,
                "sequence_number": seq,
                "city": city,
                "library": lib,
                "raw_shelfmark": raw_sm,
                "clean_shelfmark": clean_sm,
                "clean_shelfmark_length": len(clean_sm),
                "leaked_remainder": rem_text,
                "category": category,
                "split_successful": split_ok,
                "original_line": raw_line.strip()
            }
            true_leaks.append(rec)
            vol_stats[vol_num] += 1
            category_stats[category] += 1

    # Save JSON report of TRUE leaks
    json_path = REPORTS_DIR / "shelfmark_leaks.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(true_leaks, jf, ensure_ascii=False, indent=2)

    # Save JSON report of shelfmark typos
    typos_json_path = REPORTS_DIR / "shelfmark_typos.json"
    with open(typos_json_path, "w", encoding="utf-8") as tf:
        json.dump(shelfmark_typos, tf, ensure_ascii=False, indent=2)
        
    # Generate Markdown report
    md_path = REPORTS_DIR / "shelfmark_leakage_audit_report.md"
    with open(md_path, "w", encoding="utf-8") as mf:
        mf.write("# گزارش جامع و پالایش‌شده نشت اطلاعات به شماره نسخه (۳۴ جلد فنخا)\n\n")
        mf.write(f"- **تاریخ به‌روزرسانی گزارش**: ۲۹ سپتامبر ۲۰۲۶ (نسخه نهایی با پشتیبانی کامل از پسوندهای الف، ج، ی و ارقام پیوسته)\n")
        mf.write(f"- **تعداد کل نشت‌های واقعی ساختاری (نیاز به شکست سطر)**: {len(true_leaks):,} رکورد\n")
        mf.write(f"- **تعداد موارد خطای جزئی املایی در شماره نسخه (بدون نشت کالبدشناسی)**: {len(shelfmark_typos):,} رکورد\n")
        mf.write(f"- **تعداد مجلدات بررسی‌شده**: ۳۴ جلد کامل\n\n")
        
        mf.write("## ۱. توزیع آماری بر اساس دسته‌بندی الگوهای نشت واقعی\n\n")
        mf.write("| دسته‌بندی الگو | تعداد رکورد | درصد |\n")
        mf.write("| :--- | :---: | :---: |\n")
        for cat, cnt in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            pct = (cnt / len(true_leaks)) * 100
            mf.write(f"| {cat} | {cnt:,} | {pct:.1f}% |\n")
            
        mf.write("\n## ۲. توزیع آماری بر اساس مجلدات (جلد ۱ تا ۳۴)\n\n")
        mf.write("| جلد | تعداد رکوردهای نشت‌کرده | فایل منبع |\n")
        mf.write("| :---: | :---: | :--- |\n")
        for v in range(1, 35):
            cnt = vol_stats[v]
            mf.write(f"| جلد {v:02d} | {cnt:,} | `fahares_vol_{v:02d}.txt` |\n")

        mf.write("\n## ۳. جدول خطاهای املایی شماره نسخه (موارد مشابه ردیف ۷۳ - بدون نشت کالبدشناسی)\n\n")
        mf.write("این موارد نیاز به شکستن سطر ندارند، زیرا سطر بعدی آن‌ها دارای مشخصات کالبدشناسی است؛ تنها یک نقطه ویرگول تصادفی بین عدد و شناسه مجموعه قرار گرفته یا پسوند متصل به نسخه است:\n\n")
        mf.write("| # | جلد | سطر | کتابخانه | شماره نسخه خام | شرح اشکال |\n")
        mf.write("| :---: | :---: | :---: | :---: | :--- | :--- |\n")
        for i, t in enumerate(shelfmark_typos, start=1):
            mf.write(f"| {i} | {t['volume']} | {t['line_number']} | {t['library']} | `{t['raw_shelfmark']}` | {t['issue']} |\n")

        mf.write("\n## ۴. جدول جامع تمام رکوردهای نشت واقعی (نیازمند شکست سطر)\n\n")
        mf.write("| # | جلد | سطر | صفحه | کتابخانه | شماره نسخه خالص | طول | خلاصه متن تفکیک‌شده |\n")
        mf.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |\n")
        for i, r in enumerate(true_leaks, start=1):
            short_rem = r['leaked_remainder'].replace('|', '/')[:60]
            clean_sm = r['clean_shelfmark'].replace('|', '/')
            mf.write(f"| {i} | {r['volume']} | {r['line_number']} | {r['page']} | {r['library']} | `{clean_sm}` | {r['clean_shelfmark_length']} | {short_rem}... |\n")

    print(f"Audit completed successfully!")
    print(f"True structural leaks: {len(true_leaks)}")
    print(f"Shelfmark typos: {len(shelfmark_typos)}")
    print(f"Saved JSON data: {json_path}")
    print(f"Saved Markdown report: {md_path}")

if __name__ == "__main__":
    audit_all()
