#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remediate subject headers across 34 volumes in fahares-corpus.
Standardizes headers into slash format: ● عنوان / موضوع / زبان
Fixes typos, trailing hyphens, pure dashes, half-spaces, and Prophet biography titles.
"""

import os
import re
import sys
import glob

TEXT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../text/fankha'))

TYPO_MAP = {
    'داریه': 'درایه',
    'علوم غریبیه': 'علوم غریبه',
    'اخترینی': 'اختربینی',
    'كيمياء': 'کیمیا',
    'صناعت': 'صنعت',
    'اصطرلاب': 'اسطرلاب',
    'اسطر لاب': 'اسطرلاب',
    'پیشگوئی': 'پیشگویی',
    'فضائل و مناقب': 'فضایل و مناقب',
    'هیأت': 'هیئت'
}

SPACING_MAP = {
    'نامه نگاری': 'نامه‌نگاری',
    'حیوان شناسی': 'حیوان‌شناسی',
    'طالع بینی': 'طالع‌بینی',
    'قیافه شناسی': 'قیافه‌شناسی',
    'روان شناسی': 'روان‌شناسی',
    'گیاه شناسی': 'گیاه‌شناسی',
    'ستاره شناسی': 'ستاره‌شناسی',
    'چند دانشی': 'چنددانشی',
    'اختر بینی': 'اختربینی',
    'پاسخ پرسشها': 'پاسخ پرسش‌ها',
    'پاسخ پرسش ها': 'پاسخ پرسش‌ها',
    'دندان پزشکی': 'دندان‌پزشکی',
    'طالع نامه': 'طالع‌نامه',
    'فال نامه': 'فالنامه',
    'فال گیری': 'فالگیری',
}

PROPHET_PATTERNS = [
    (re.compile(r'تاریخ\s+پیامبراکرم\s*\(ص\)'), 'تاریخ پیامبر اکرم (ص)'),
    (re.compile(r'تاریخ\s+پیامبر\s+اکرم\s*\(ص\)'), 'تاریخ پیامبر اکرم (ص)'),
    (re.compile(r'تاریخ\s+پیامبراکرم\s*\(ع\)'), 'تاریخ پیامبر اکرم (ص)'),
    (re.compile(r'تاریخ\s+پیامبر\s+اکرم(?!\s*\()'), 'تاریخ پیامبر اکرم (ص)'),
    (re.compile(r'تاریخ\s+پیامبراکرم(?!\s*\()'), 'تاریخ پیامبر اکرم (ص)')
]

LANGS_LIST = ['فارسی', 'عربی', 'اردو', 'ترکی', 'پهلوی', 'اوستایی', 'فرانسوی', 'فرانسه', 'سریانی', 'عبری', 'ارمنی', 'هندی', 'پنجابی', 'عرب', 'فارسى']
LANGS_PATTERN = r'(' + '|'.join(LANGS_LIST) + r')'

def clean_header_line(orig_line: str) -> str:
    clean = orig_line
    
    # 0. Dangling trailing slash
    clean = re.sub(r'\s*/\s*$', '', clean)
    
    # 1. Pure dash removal: e.g. '● پراکنده ... / -' or '/-' or '/ —' or '/ ـ'
    clean = re.sub(r'\s*/\s*[-–—ـ]+\s*$', '', clean)
    
    # 2. Leading dash on language: e.g. '/ـ عربی' -> '/ عربی' or '/ - فارسی' -> '/ فارسی'
    clean = re.sub(r'/\s*[-–—ـ]+\s*(?=' + LANGS_PATTERN + r')', r'/ ', clean)
    
    # 3. Trailing dash on subject: e.g. ' / فقه - ' -> ' / فقه '
    clean = re.sub(r'/\s*([^/]+?)\s*[-–—ـ]\s*$', r'/ \1', clean)
    
    # 4. Multi-language with dashes: e.g. ' / عربی - فارسی' -> ' / عربی و فارسی'
    clean = re.sub(r'/\s*(' + LANGS_PATTERN + r')\s*[-–—]\s*(' + LANGS_PATTERN + r')\s*$', r'/ \1 و \2', clean)
    
    # 5. Subject + Lang separated by dash/colon/dot/comma -> separate by slash
    clean = re.sub(r'/\s*([^/]+?)\s*[-–—.:،]\s*(' + LANGS_PATTERN + r'(?:\s+(?:و|-)\s+' + LANGS_PATTERN + r')?)\s*$', r'/ \1 / \2', clean)
    
    # 6. Missing separator between specific subjects and language
    clean = re.sub(r'/\s*(حکومت و سیاست|طب|اسناد|نامه‌نگاری|نامه نگاری|فقه|تجوید|تاریخ ترکی|تاریخ ایران|مواعظ|ادبیات)\s+(' + LANGS_PATTERN + r')\s*$', r'/ \1 / \2', clean)
    
    # 7. Typos
    for typo, fix in TYPO_MAP.items():
        if typo in clean:
            clean = clean.replace(typo, fix)
            
    # 8. Spacing
    for sp, fix in SPACING_MAP.items():
        if sp in clean:
            clean = clean.replace(sp, fix)
            
    # 9. Prophet standardization
    if 'تاریخ پیامبر' in clean or 'تاریخ پیامبراکرم' in clean:
        for pat, repl in PROPHET_PATTERNS:
            clean = pat.sub(repl, clean)
            
    # 10. Clean up multiple spaces
    clean = re.sub(r'[ \t]{2,}', ' ', clean)
    
    # 11. Final strip of any trailing slash created or leftover
    clean = re.sub(r'\s*/\s*$', '', clean)
    
    return clean.rstrip()

def remediate_volumes(dry_run: bool = True):
    files = sorted(glob.glob(os.path.join(TEXT_DIR, 'fankha_vol_*.txt')))
    print(f"Targeting {len(files)} files in {TEXT_DIR} (dry_run={dry_run})")
    
    total_lines = 0
    total_headers = 0
    modified_headers = 0
    
    for filepath in files:
        vol_name = os.path.basename(filepath)
        vol_mods = 0
        new_lines = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                total_lines += 1
                raw = line.rstrip('\r\n')
                if raw.strip().startswith('●'):
                    total_headers += 1
                    cleaned = clean_header_line(raw)
                    if cleaned != raw:
                        vol_mods += 1
                        modified_headers += 1
                        new_lines.append(cleaned + '\n')
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
                    
        print(f"  {vol_name}: {vol_mods} headers modified.")
        
        if not dry_run and vol_mods > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
    print("\nSummary:")
    print(f"  Total lines processed: {total_lines}")
    print(f"  Total work headers: {total_headers}")
    print(f"  Total modified headers: {modified_headers}")

if __name__ == '__main__':
    dry_run = '--apply' not in sys.argv
    remediate_volumes(dry_run=dry_run)
