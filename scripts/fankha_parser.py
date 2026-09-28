#!/usr/bin/env python3
"""
Fankha Production Parser & Structured JSON Generator (v2 - Phase 1 Refactored).
Extracts work headers, referral links, and granular manuscript metadata from
the Fankha text corpus into rich, relational-ready JSON with multi-subject/language,
date triad sorting, volume/page ranges, and granular citations.
"""

import re
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple

PAGE_TAG_PATTERN = re.compile(r'<!--\s*page:\s*(\d+)\s*-->')
KNOWN_SCRIPTS = r'(?:نستعلیق|نسخ|شکسته|تعلیق|رقعه|کوفی|ثلث|ریحان|محقق|طومار|لاتین)'
DATE_MARKERS = r'(?:\d+|قرن|با تاریخ|اوایل|اواخر|نیمه|بی‌تا|بی تا|غره|سلخ|جمادی|ربیع|شوال|رمضان|صفر|محرم|شعبان|ذوالقعده|ذیقعده|ذوالحجه|ذیحجه|سنه)'
CONTENT_WORDS_RE = re.compile(r'(?:فصل|باب|مقاله|میمر|جزء|قسم|مطلب|کتاب|مقصد|حدیث|ثمره|شعبه|پایان|شعر|بیت)')

KNOWN_LANGUAGES = {
    'فارسی', 'عربی', 'ترکی', 'اردو', 'عبری', 'سریانی', 'پهلوی',
    'اوستایی', 'کردی', 'پشتو', 'فرانسوی', 'فرانسه', 'انگلیسی', 'لاتین', 'لری',
    'ارمنی', 'هندی', 'پنجابی'
}

COMPOUND_SUBJECTS_WHITELIST = [
    'کلام و اعتقادات', 'کلام و عقاید', 'عرفان و تصوف', 'آداب و سنن',
    'تفسیر و علوم قرآن', 'علوم قرآن', 'حکومت و سیاست', 'فضایل و مناقب',
    'عروض و قافیه', 'ادیان و مذاهب'
]

@dataclass
class Manuscript:
    sequence_number: Optional[int] = None
    city: Optional[str] = None
    library: Optional[str] = None
    shelfmark: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    scribe: Optional[str] = None
    scribe_name: Optional[str] = None
    is_bika: bool = False
    is_bita: bool = False
    is_autograph: bool = False
    copy_date_raw: Optional[str] = None
    copy_place: Optional[str] = None
    script: Optional[str] = None
    scripts: List[str] = field(default_factory=list)
    script_styles: List[str] = field(default_factory=list)
    folios: Optional[str] = None
    lines: Optional[str] = None
    dimensions: Optional[str] = None
    text_dimensions: Optional[str] = None
    commissioned_by: Optional[str] = None
    identification_notes: Optional[str] = None
    is_identification_uncertain: bool = False
    paper: Optional[str] = None
    binding: Optional[str] = None
    format: Optional[str] = None
    incipit_text: Optional[str] = None
    explicit_text: Optional[str] = None
    incipits: List[Dict[str, Optional[str]]] = field(default_factory=list)
    explicits: List[Dict[str, Optional[str]]] = field(default_factory=list)
    incipit_matches_work: bool = False
    explicit_matches_work: bool = False
    defects: Optional[str] = None
    print_info: Optional[str] = None
    contents_note: Optional[str] = None
    donor: Optional[str] = None
    colophon: Optional[str] = None
    composition_date: Optional[str] = None
    original_copy_ref: Optional[str] = None
    parent_manuscript_seq: Optional[int] = None
    catalog_citation: Optional[str] = None
    editorial_notes: List[str] = field(default_factory=list)
    annex_notes: List[str] = field(default_factory=list)
    ownership_and_seals: List[str] = field(default_factory=list)
    seals: List[Dict[str, Optional[str]]] = field(default_factory=list)
    residual_notes: Optional[str] = None
    is_corrected: bool = False
    has_marginal_notes: bool = False
    is_ruled: bool = False
    has_catchwords: bool = False
    is_facsimile: bool = False
    is_distinct_work: bool = False
    is_collated: bool = False
    is_illuminated: bool = False
    is_illustrated: bool = False
    has_author_marginalia: bool = False
    raw_text: str = ""

@dataclass
class WorkEntry:
    primary_title: str
    clean_title: Optional[str] = None
    work_form: Optional[str] = None
    alternative_titles: List[str] = field(default_factory=list)
    is_heterogeneous: bool = False
    is_identification_uncertain: bool = False
    identification_notes: Optional[str] = None
    subject: Optional[str] = None
    subject_raw: Optional[str] = None
    subjects: List[str] = field(default_factory=list)
    language: Optional[str] = None
    language_raw: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    is_language_uncertain: bool = False
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    transliteration: Optional[str] = None
    alternative_transliterations: List[str] = field(default_factory=list)
    author_name: Optional[str] = None
    author_name_raw: Optional[str] = None
    authorship_status: str = "certain"
    translator_name: Optional[str] = None
    original_author_name: Optional[str] = None
    author_transliteration: Optional[str] = None
    author_death_date_raw: Optional[str] = None
    author_death_date_hijri: Optional[str] = None
    author_death_date_century: Optional[int] = None
    author_death_date_sort_year: Optional[int] = None
    author_death_date_gregorian: Optional[str] = None
    author_death_date_gregorian_calculated: Optional[int] = None
    composition_date: Optional[str] = None
    composition_place: Optional[str] = None
    dedication: Optional[str] = None
    related_work: Optional[str] = None
    description: Optional[str] = None
    print_info: Optional[str] = None
    incipit: Optional[str] = None
    explicit: Optional[str] = None
    commentaries_and_glosses: List[str] = field(default_factory=list)
    bibliography: List[str] = field(default_factory=list)
    volume_number: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    manuscripts: List[Manuscript] = field(default_factory=list)

@dataclass
class ReferralEntry:
    source_title: str
    target_title: str
    volume_number: Optional[int] = None
    page: Optional[int] = None

AUTHOR_DATE_PATTERN = re.compile(
    r'(?:'
    r'\d{3,4}[?؟]?\s*[\-–]\s*\d{3,4}\s*[?؟]?\s*(?:ق(?:مر[یی])?|ش(?:مسی)?|م(?:یلادی)?)?'
    r'|[\-–]\s*\d{3,4}\s*[?؟]?\s*(?:ق(?:مر[یی])?|ش(?:مسی)?|م(?:یلادی)?)?'
    r'|ق\s*\d{1,2}\s*ق?'
    r'|قرن\s*\d{1,2}\s*(?:ق(?:مر[یی])?|ش(?:مسی)?|م(?:یلادی)?)?'
    r'|زنده در\s*\d{3,4}'
    r'|متوفای\s*\d{3,4}'
    r'|\d{3,4}\s*[?؟]?\s*(?:ق(?:مر[یی])?|ش(?:مسی)?|م(?:یلادی)?)?'
    r'|\((?:(?:قرن|سده)\s*\d{1,2}|[\d\?؟\s\-–\.\/]+(?:ق(?:مر[یی])?|ش(?:مسی)?|م(?:یلادی)?|قبل میلاد)?)\)'
    r')[\.\s]*$'
)

DESC_WORDS = [
    'است', 'بود', 'می‌شود', 'میگردد', 'می‌باشد', 'میباشد', 'گردیده', 'آمده',
    'دارد', 'شامل', 'مشتمل', 'مجموعه', 'رساله', 'کتاب', 'منظومه', 'گزارش',
    'بندی', 'سرگذشت', 'مطالب', 'عبارتند', 'یکی از', 'چند ', 'درباره', 'پیرامون',
    '«باب»', '«فصل»', '«اصل»', '«مقدمه»', '«مقصد»', 'باشد', 'محتملاً', 'احتمالاً'
]

DESC_WORDS_PATTERN = re.compile(
    r'(?:^|[؛،\s\(\)\[\]«»])(?:' +
    '|'.join(re.escape(w.strip()) for w in DESC_WORDS) +
    r')(?:[؛،\s\(\)\[\]«»]|$|[!؟\.])'
)

HONORIFICS = {'ص', 'ع', 'عج', 'ره', 'س', 'قس', 'رض'}

def is_language_str(s: str) -> bool:
    if not s:
        return False
    clean = PAGE_TAG_PATTERN.sub('', s).strip()
    clean = re.sub(r'[a-zA-Z\'].*', '', clean).strip()
    clean = clean.replace('عربى', 'عربی')
    words = re.split(r'[\s،,و/\-]+', clean)
    words = [w for w in words if w and w not in ('و', 'به', 'یا', 'زبان')]
    if not words:
        return False
    return all(w in KNOWN_LANGUAGES for w in words)

def parse_languages(lang_str: Optional[str]) -> Tuple[List[str], Optional[str], Optional[str], bool]:
    if not lang_str:
        return [], None, None, False
    s = PAGE_TAG_PATTERN.sub('', lang_str).strip()
    s = re.sub(r'[a-zA-Z\'].*', '', s).strip()
    s = s.replace('عربى', 'عربی')
    
    is_uncertain = False
    source_lang = None
    target_lang = None

    if re.search(r'یا|یا اینکه|مردد|شاید', s):
        is_uncertain = True

    # Check translation pattern: e.g. "عربی به فارسی", "فارسی به ترکی", "فارسی به فارسی"
    m_trans = re.search(r'([^\s]+)\s+به\s+([^\s]+)', s)
    if m_trans:
        src = m_trans.group(1).strip()
        tgt = m_trans.group(2).strip()
        if src in KNOWN_LANGUAGES or tgt in KNOWN_LANGUAGES:
            source_lang = src if src in KNOWN_LANGUAGES else None
            target_lang = tgt if tgt in KNOWN_LANGUAGES else None
            langs = []
            for l in [src, tgt]:
                if l in KNOWN_LANGUAGES and l not in langs:
                    langs.append(l)
            return langs if langs else [tgt], source_lang, target_lang, False

    words = re.split(r'[\s،,و/\-]+', s)
    res = []
    for w in words:
        if w in KNOWN_LANGUAGES and w not in res:
            res.append(w)
    return (res if res else [s]), source_lang, target_lang, is_uncertain

def extract_title_form_and_clean(primary_title: str) -> Tuple[str, Optional[str]]:
    m = re.search(r'\(([^)]+)\)\s*$', primary_title)
    if not m:
        return primary_title, None

    qualifier = m.group(1).strip()
    if qualifier in HONORIFICS:
        return primary_title, None

    clean = primary_title[:m.start()].strip()

    form = None
    if re.search(r'ترجمه|با ترجمه', qualifier):
        form = "translation"
    elif re.search(r'منتخب|مختصر|برگزیده|خلاصه|ملخص', qualifier):
        form = "selection"
    elif re.search(r'منظوم|منظومه|ارجوزة|أرجوزة|شعر|قصیده|قصيدة', qualifier):
        form = "verse"
    elif re.search(r'گردآوری|جوامع|مجموعه|مجموعة', qualifier):
        form = "compilation"
    elif re.search(r'جدول|جداول', qualifier):
        form = "table"
    elif re.search(r'فائده|فوائد|فایده|مطالب|مطالبی', qualifier):
        form = "notes"
    elif re.search(r'تقریر|تقرير|تقریرات|تقريرات', qualifier):
        form = "lecture_notes"
    elif re.search(r'شرح|حاشیه|تعلیقه|حواشی', qualifier):
        form = "commentary"
    elif re.search(r'رساله|رسالة|کتاب', qualifier):
        form = "treatise"

    return (clean if clean else primary_title), form

def clean_author(raw_author: str) -> Tuple[str, str]:
    status = "certain"
    s = raw_author.strip()

    if re.search(r'منسوب به|شاید از', s):
        status = "attributed"
    elif re.search(r'[؟\?]|ظاهراً|ظاهرا|احتمالاً|احتمالا|گویا', s):
        status = "probable"

    clean = s
    clean = re.sub(r'^(?:[؟\?\s\:]|منسوب به|شاید از|ظاهراً از|ظاهرا از|ظاهراً|ظاهرا|احتمالاً از|احتمالا از|احتمالاً|احتمالا|گویا از|گویا)+', '', clean).strip(' :؟?')
    clean = re.sub(r'\s*\([؟\?]\)', '', clean).strip()
    clean = re.sub(r'[؟\?]', '', clean).strip()

    return (clean if clean else s), status

def parse_subjects(subj_str: Optional[str]) -> List[str]:
    if not subj_str:
        return []
    s = subj_str.strip()
    for cs in COMPOUND_SUBJECTS_WHITELIST:
        if s == cs:
            return [cs]
    
    parts = re.split(r'[،,]+', s)
    res = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        found_wl = False
        for cs in COMPOUND_SUBJECTS_WHITELIST:
            if p == cs:
                res.append(cs)
                found_wl = True
                break
        if not found_wl:
            res.append(p)
    return res

KNOWN_SCRIPTS_LIST = [
    'شکسته نستعلیق', 'نستعلیق', 'شکسته', 'تعلیق', 'رقعه', 'کوفی', 'ثلث',
    'ریحان', 'محقق', 'طومار', 'مغربی', 'لاتین', 'تایپی', 'نسخ'
]

KNOWN_SCRIPT_STYLES = [
    'زیبا', 'خوش', 'خوانا', 'ممتاز', 'پخته', 'جلی', 'خفی',
    'تحریری', 'درشت', 'معرب', 'چلیپا', 'کتابتی', 'متوسط', 'عالی',
    'ریز', 'ریزه', 'کهن', 'قدیم', 'شیرین', 'خشن'
]

def parse_scripts_and_styles(script_str: Optional[str]) -> Tuple[List[str], List[str]]:
    if not script_str:
        return [], []
    s = script_str

    scripts = []
    for sc in KNOWN_SCRIPTS_LIST:
        if sc in s:
            scripts.append(sc)
            s = s.replace(sc, ' ')

    styles = []
    for st in KNOWN_SCRIPT_STYLES:
        if re.search(r'(?:^|[،\sو/\-])' + re.escape(st) + r'(?:[،\sو/\-]|$)', s):
            styles.append(st)
            s = re.sub(r'(?:^|[،\sو/\-])' + re.escape(st) + r'(?:[،\sو/\-]|$)', ' ', s)

    return (scripts if scripts else [script_str.strip()]), styles

def parse_scripts(script_str: Optional[str]) -> List[str]:
    scripts, _ = parse_scripts_and_styles(script_str)
    return scripts

def parse_incipits_and_explicits(text: str) -> Tuple[List[Dict[str, Optional[str]]], List[Dict[str, Optional[str]]], bool, bool, List[str]]:
    incipit_matches_work = False
    explicit_matches_work = False
    extracted_spans = []

    # Check matches work
    if re.search(r'آغاز\s*(?:و\s*)?انجام[:\s]\s*برابر', text):
        incipit_matches_work = True
        explicit_matches_work = True
        for b_span in ['آغاز و انجام: برابر', 'آغاز و انجام برابر', 'آغاز انجام: برابر', 'آغاز انجام برابر']:
            if b_span in text:
                extracted_spans.append(b_span)
    else:
        if 'آغاز: برابر' in text or 'آغاز برابر' in text:
            incipit_matches_work = True
            extracted_spans.extend(['آغاز: برابر', 'آغاز برابر'])
        if 'انجام: برابر' in text or 'انجام برابر' in text:
            explicit_matches_work = True
            extracted_spans.extend(['انجام: برابر', 'انجام برابر'])

    # Incipit and explicit headers
    pattern = re.compile(
        r'(?:^|[؛\n]|(?<!و)\s+)\b((?:آغاز\s+(?:و\s+)?انجام|آغاز|انجام)(?:[ \t]*:[ \t]*(?:آغاز|انجام))?(?:\s+(?:جلد|قسمت|بخش|دفتر|باب|فصل|دیباچه|متن|فهرست|تعلیق|تعلیقات|نسخه|رساله|خطبه)?(?:\s+(?:اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|\d+))?)?)\s*:\s*',
        re.MULTILINE
    )

    matches = list(pattern.finditer(text))
    incipits = []
    explicits = []

    TERMINAL_RE = re.compile(
        r'(?:(?:[؛\n]|\.\s*)\s*(?:خط:|کا:|کاتب:|تا:|جا:|کاغذ:|جلد:|قطع:|ابعاد|اندازه|مصحح|مجدول|مذهب|تملک:|مهر:|اهدایی:|اهدا:|افتادگی:|نسخه اصل:|اصل نسخه:|چاپ:|شامل:|مشتمل بر:|مجموعه\s*ای\s+است|مجموعه‌ای\s+است|توضیح:|تذکر:|ترقیمه:|انجامه:|خاتمه:|از\s+فص\s+|بی‌کا|بی کا|بی‌تا|بی تا|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)))|(?:\s*\[\s*(?:ف|سنا|تراثنا|دارالکتب|فهرست|نشریه|عکسی|میراث|آستانه|مخ|کتابخانه|نسخ|طبسی|سپهسالار|مجلس|مرعشی|ملی|ملک|دانشگاه|مشهد|قم|تهران|مؤید|دنا)[^\]]*\]|\s*\[[^\]]*\d+\s*[\-–]\s*\d+[^\]]*\])'
    )

    for i, m in enumerate(matches):
        raw_header = m.group(1).strip()
        start_content = m.end()
        sub_text = text[start_content:]

        barabar_m = re.match(r'^\s*(برابر(?:\s+است)?(?:\s+\d+)?)(?=[؛\n]|$)', sub_text)
        if barabar_m:
            end_content = start_content + barabar_m.end()
        elif i + 1 < len(matches):
            next_start = matches[i + 1].start()
            sub_next = text[start_content:next_start]
            term_m = TERMINAL_RE.search(sub_next)
            if term_m:
                end_content = start_content + term_m.start()
            else:
                end_content = next_start
        else:
            term_m = TERMINAL_RE.search(sub_text)
            if term_m:
                end_content = start_content + term_m.start()
            else:
                end_content = len(text)

        content = text[start_content:end_content].strip(' ؛،\n')
        span_str = text[m.start():end_content].strip()
        extracted_spans.append(span_str)

        if 'آغاز' in raw_header and 'انجام' in raw_header:
            if 'برابر' in content:
                incipit_matches_work = True
                explicit_matches_work = True
            elif content:
                incipits.append({'label': None, 'text': content})
                explicits.append({'label': None, 'text': content})
            continue

        is_incipit = raw_header.startswith('آغاز')
        clean_lbl = re.sub(r'^(?:آغاز|انجام)[:\s]+(?:آغاز|انجام)?', '', raw_header).strip(' :')
        if not clean_lbl or clean_lbl in ('آغاز', 'انجام'):
            label = None
        else:
            label = clean_lbl

        if content in ('برابر', 'برابر است', 'برابر؛', 'برابر.'):
            if is_incipit:
                incipit_matches_work = True
            else:
                explicit_matches_work = True
            continue

        item = {'label': label, 'text': content}
        if is_incipit:
            incipits.append(item)
        else:
            explicits.append(item)

    return incipits, explicits, incipit_matches_work, explicit_matches_work, extracted_spans

def parse_seals(seal_texts: List[str]) -> List[Dict[str, Optional[str]]]:
    res = []
    for st in seal_texts:
        clean = re.sub(r'^(?:دارای\s*)?مهر(?:ها)?:\s*', '', st).strip()
        items = re.split(r'[,،؛]\s*|\s+و\s+', clean)
        for it in items:
            it = re.sub(r'^(?:و\s+)', '', it).strip(' «»')
            if not it:
                continue
            shape_m = re.search(r'\((مربع|بیضی|بادامی|مدور|دایره|هشت\s*ضلعی|مستطیل)\)', it)
            shape = shape_m.group(1).strip() if shape_m else None
            insc = re.sub(r'\([^)]+\)', '', it).strip(' «»')
            if insc:
                res.append({'inscription': insc, 'shape': shape})
    return res

def is_bib_citation(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    has_vol_page = bool(re.search(r'\d+\s*[\/\-:]\s*\d+', s))
    has_catalog_keyword = bool(re.search(r'(?:فهرست|فهرستواره|منزوی|الذریعة|الذریعه|مشار|الفهرس|کشف الظنون|هدية العارفين|معجم|طبقات|نسخه‌های|نسخه های|دنا|ف:|ف\s*\d)', s))
    has_semicolon = '؛' in s
    has_page_word = bool(re.search(r'(?:ص|ج|جلد|صفحه|شماره)\s*\d+', s))
    return has_vol_page or has_catalog_keyword or has_semicolon or has_page_word

def parse_header_line(clean_header: str) -> Tuple[List[str], Optional[str], Optional[str]]:
    parts = [p.strip() for p in clean_header.split('/') if p.strip()]
    if not parts:
        return [clean_header], None, None
    
    titles_part = parts[0]
    titles = [t.strip() for t in titles_part.split('=') if t.strip()]
    
    if len(parts) == 1:
        return titles, None, None
    elif len(parts) == 2:
        part2 = parts[1].strip()
        # Handle leading hyphen indicating missing subject (e.g. /- فارسی)
        if (part2.startswith('-') or part2.startswith('–')) and is_language_str(part2.lstrip('-– ')):
            return titles, None, part2.lstrip('-– ').strip()

        if '-' in part2:
            sub_parts = [sp.strip() for sp in part2.split('-') if sp.strip()]
            if len(sub_parts) == 2 and is_language_str(sub_parts[1]):
                return titles, sub_parts[0], sub_parts[1]
        
        if is_language_str(part2):
            return titles, None, part2
        else:
            return titles, part2, None
    else:
        subject = parts[1].strip()
        language = parts[2].strip()
        if subject in ('-', '–'):
            subject = None
        if language.startswith('-') or language.startswith('–'):
            language = language.lstrip('-– ').strip()
        if subject and '-' in subject and not language:
            sub_parts = [sp.strip() for sp in subject.split('-') if sp.strip()]
            if len(sub_parts) == 2 and is_language_str(sub_parts[1]):
                subject = sub_parts[0]
                language = sub_parts[1]
        return titles, subject, language

def parse_date_triad(date_raw: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    if not date_raw:
        return None, None, None
    
    s = date_raw.strip()
    century = None
    sort_year = None
    
    # 1. Century textual patterns: e.g. "قرن 7", "قرن 11", "سده 8", "ق 11", "اواخر قرن 7", "اوایل قرن 10"
    m_cent = re.search(r'(?:(اوایل|اواخر|نیمه\s*اول|نیمه\s*دوم)\s+)?(?:قرن|سده|ق\s*)\s*(\d{1,2})', s)
    if m_cent:
        mod = m_cent.group(1) or ''
        c_num = int(m_cent.group(2))
        if 1 <= c_num <= 15:
            century = c_num
            base = (c_num - 1) * 100
            if 'اوایل' in mod:
                sort_year = base + 20
            elif 'اواخر' in mod:
                sort_year = base + 80
            elif 'نیمه دوم' in mod:
                sort_year = base + 75
            elif 'نیمه اول' in mod:
                sort_year = base + 25
            else:
                sort_year = base + 50
    
    # 2. Number extraction (Hijri years 100..1450)
    nums = [int(n) for n in re.findall(r'(?<!\d)(\d{3,4})(?!\d)', s) if 100 <= int(n) <= 1450]
    if nums:
        death_y = nums[-1]
        sort_year = death_y
        century = (death_y - 1) // 100 + 1
    
    # 3. Gregorian calculated equivalent from Hijri
    greg_calc = None
    if sort_year and 100 <= sort_year <= 1450:
        greg_calc = round(sort_year * 0.970229 + 621.57)
        
    return century, sort_year, greg_calc

def is_author_line(line: str, next_line: Optional[str] = None) -> bool:
    line = line.strip()
    if not line or len(line) > 120:
        return False
    clean_l = re.sub(r'^(?:[؟\?\s\:]|منسوب به|شاید از|ظاهراً از|ظاهرا از|ظاهراً|ظاهرا|احتمالاً از|احتمالا از|احتمالاً|احتمالا|گویا از|گویا)+', '', line).strip(' :؟?')
    if not clean_l:
        return False
    first_word = clean_l.split()[0] if clean_l.split() else ''
    if any(first_word.startswith(w) for w in ['رساله', 'کتاب', 'منظومه', 'شرح', 'ترجمه', 'تفسیر', 'یکی', 'این', 'در', 'از', 'سرگذشت', 'مجموعه', 'مطالب', 'گزارش', 'آمار', 'وابسته']):
        return False
    if DESC_WORDS_PATTERN.search(clean_l):
        return False
    if any(clean_l.startswith(w) for w in ['آغاز:', 'انجام:', 'چاپ:', 'وابسته به:', 'تاریخ تألیف:', 'تألیف:', 'تاریخ اجازه:', 'اجازه:', 'اهداء به:', 'اهدا به:', 'اهدایی به:', 'موضوع:']):
        return False

    if next_line:
        nl = next_line.strip()
        if any(c.isascii() and c.isalpha() for c in nl) and re.search(r'\([0-9\?؟\-–CDc\s\.]+\)', nl):
            return True

    if AUTHOR_DATE_PATTERN.search(clean_l):
        return True

    if '،' in clean_l:
        parts = [p.strip() for p in clean_l.split('،')]
        last = parts[-1]
        if re.search(r'(?:\d|[\?؟]|قرن|ق\s*\d|\bق\b|قمری|شمسی|میلادی|قبل میلاد)', last):
            return True

    if '،' in clean_l and any(w in clean_l for w in ['بن', 'ابن', 'ابو', 'محمد', 'احمد', 'علی', 'حسن', 'حسین', 'میرزا', 'سید', 'شیخ', 'ملا']):
        return True

    if len(clean_l.split()) <= 4 and any(w in clean_l for w in ['میرزا', 'سید', 'شیخ', 'ملا', 'خان', 'شاه', 'پاشا', 'افندی']):
        return True

    return False

def extract_author_and_date(cand: str) -> Tuple[str, Optional[str]]:
    cand = cand.strip().rstrip('. :،')

    m_paren = re.search(r'\s*\(((?:(?:قرن|سده)\s+)?[\d\?؟\s\-–\.\/]*(?:ق(?:مر[یی])?|م(?:یلادی)?|ش(?:مسی)?|قبل میلاد)?)\)$', cand)
    if m_paren and (any(c.isdigit() for c in m_paren.group(1)) or 'قرن' in m_paren.group(1) or 'سده' in m_paren.group(1)):
        return cand[:m_paren.start()].rstrip('، '), m_paren.group(1).strip()

    if '،' in cand:
        parts = [p.strip() for p in cand.split('،')]
        last = parts[-1]
        has_digit = bool(re.search(r'\d', last))
        has_era = bool(re.search(r'(?:قرن|قبل میلاد|متوف[یای]|زنده در|\bق\b|قمری|قمرى|شمسی|شمسى|میلادی|ميلادي|\bم\b)', last))

        if (has_digit or has_era) and not re.search(r'(?:بن|ابن|بنت)\s+[\u0600-\u06FF]', last):
            author_part = '، '.join(parts[:-1]).strip()
            if author_part:
                return author_part, last

    m = re.search(r'[\s،]+((?:(?:ق|قرن|سده|متوفای|زنده در)\s*)?[\-–\s]*[\d\?؟]+[\d\?؟\s\-–\.\/]*(?:یا\s+[\d\?؟]+[\d\?؟\s\-–\.\/]*)?(?:ق(?:مر[یی])?|م(?:یلادی)?|ش(?:مسی)?|قبل میلاد)?)$', cand)
    if m and any(c.isdigit() for c in m.group(1)):
        author_part = cand[:m.start()].rstrip('، ')
        if author_part:
            return author_part, m.group(1).strip()

    return cand, None

class FankhaParser:
    def __init__(self, volume_number: int):
        self.volume_number = volume_number
        self.works: List[WorkEntry] = []
        self.referrals: List[ReferralEntry] = []

    def parse_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        raw_entries = self._split_entries(text)
        for entry_lines, start_page, end_page in raw_entries:
            entry_text = "\n".join(entry_lines).strip()
            if not entry_text:
                continue

            first_line = entry_lines[0].strip()
            if '←' in first_line and not first_line.startswith('●'):
                self._parse_referral(first_line, start_page)
            elif first_line.startswith('●'):
                work = self._parse_work(entry_lines, start_page, end_page)
                if work:
                    self.works.append(work)

    def _split_entries(self, text: str) -> List[Tuple[List[str], int, int]]:
        lines = text.split('\n')
        entries = []
        curr_entry_lines = []
        curr_page = 1
        entry_start_page = 1

        for line in lines:
            page_matches = PAGE_TAG_PATTERN.findall(line)
            if page_matches:
                curr_page = int(page_matches[-1])

            stripped = line.strip()
            is_work_header = stripped.startswith('● ')
            is_referral = '←' in stripped and not is_work_header and not stripped.startswith('آغاز') and not stripped.startswith('انجام')

            if (is_work_header or is_referral) and curr_entry_lines:
                entries.append((curr_entry_lines, entry_start_page, curr_page))
                curr_entry_lines = []
                entry_start_page = curr_page

            curr_entry_lines.append(line)

        if curr_entry_lines:
            entries.append((curr_entry_lines, entry_start_page, curr_page))

        return entries

    def _parse_referral(self, line: str, page: int):
        clean = PAGE_TAG_PATTERN.sub('', line).strip()
        parts = clean.split('←')
        if len(parts) >= 2:
            src = parts[0].strip()
            tgt = parts[1].strip()
            self.referrals.append(ReferralEntry(
                source_title=src,
                target_title=tgt,
                volume_number=self.volume_number,
                page=page
            ))

    def _parse_work(self, lines: List[str], start_page: int, end_page: int) -> Optional[WorkEntry]:
        header_line = lines[0]
        raw_header = header_line.lstrip('● ').strip()
        clean_header = PAGE_TAG_PATTERN.sub('', raw_header).strip()

        titles, subject_part, language_part = parse_header_line(clean_header)
        primary_title = titles[0] if titles else clean_header
        alternative_titles = titles[1:] if len(titles) > 1 else []

        clean_title, work_form = extract_title_form_and_clean(primary_title)

        subject_raw = subject_part
        subjects = parse_subjects(subject_part)
        language_raw = language_part
        languages, source_lang, target_lang, is_lang_uncertain = parse_languages(language_part)

        if source_lang and not work_form:
            work_form = "translation"

        is_hetero = any(('غیر همانند' in l or 'غیرهمانند' in l) for l in lines)
        is_id_uncertain = any(('همانندی نامعلوم' in l or 'همانندی غیر معلوم' in l or 'همانندی نامشخص' in l) for l in lines)

        work = WorkEntry(
            primary_title=primary_title,
            clean_title=clean_title,
            work_form=work_form,
            alternative_titles=alternative_titles,
            is_heterogeneous=is_hetero,
            is_identification_uncertain=is_id_uncertain,
            identification_notes=("همانندی نامعلوم" if is_id_uncertain else None),
            subject=subject_raw,
            subject_raw=subject_raw,
            subjects=subjects,
            language=language_raw,
            language_raw=language_raw,
            languages=languages,
            is_language_uncertain=is_lang_uncertain,
            source_language=source_lang,
            target_language=target_lang,
            volume_number=self.volume_number,
            page_start=start_page,
            page_end=end_page
        )

        preamble_lines = []
        ms_blocks: List[List[str]] = []
        curr_ms_lines: List[str] = []
        in_ms_section = False

        for line in lines[1:]:
            clean_l = PAGE_TAG_PATTERN.sub('', line).strip()
            if ('شماره نسخه:' in clean_l or 'شماره نسخه :' in clean_l) and not in_ms_section:
                in_ms_section = True
                if curr_ms_lines:
                    ms_blocks.append(curr_ms_lines)
                    curr_ms_lines = []
            elif in_ms_section and ('شماره نسخه:' in clean_l or 'شماره نسخه :' in clean_l):
                if curr_ms_lines:
                    ms_blocks.append(curr_ms_lines)
                    curr_ms_lines = []

            if not in_ms_section:
                preamble_lines.append(line)
            else:
                curr_ms_lines.append(line)

        if curr_ms_lines:
            ms_blocks.append(curr_ms_lines)

        self._parse_work_preamble(work, preamble_lines)

        for seq, ms_lines in enumerate(ms_blocks, 1):
            ms = self._parse_manuscript(ms_lines, start_page, seq, is_hetero, is_id_uncertain)
            if ms:
                work.manuscripts.append(ms)

        return work

    def _parse_work_preamble(self, work: WorkEntry, preamble_lines: List[str]):
        if not preamble_lines:
            return

        idx = 0
        total_p = len(preamble_lines)

        # 1. Transliteration (line 1 after header if ASCII/Latin letters)
        while idx < total_p and not PAGE_TAG_PATTERN.sub('', preamble_lines[idx]).strip():
            idx += 1
        if idx < total_p:
            cand = PAGE_TAG_PATTERN.sub('', preamble_lines[idx]).strip()
            if cand and any(c.isascii() and c.isalpha() for c in cand):
                trans_parts = [tp.strip() for tp in cand.split('=') if tp.strip()]
                if trans_parts:
                    work.transliteration = trans_parts[0]
                    work.alternative_transliterations = trans_parts[1:]
                idx += 1

        # 2. Author info
        while idx < total_p and not PAGE_TAG_PATTERN.sub('', preamble_lines[idx]).strip():
            idx += 1
        if idx < total_p:
            cand = PAGE_TAG_PATTERN.sub('', preamble_lines[idx]).strip()
            next_idx = idx + 1
            while next_idx < total_p and not PAGE_TAG_PATTERN.sub('', preamble_lines[next_idx]).strip():
                next_idx += 1
            next_cand = PAGE_TAG_PATTERN.sub('', preamble_lines[next_idx]).strip() if next_idx < total_p else None

            cand_trans = None
            if re.search(r'[a-zA-Z\']', cand) and re.search(r'[\u0600-\u06FF]', cand):
                m_lat = re.search(r'([a-zA-Z\'].*)', cand)
                if m_lat:
                    cand_trans = m_lat.group(1).strip()
                    cand = cand[:m_lat.start()].strip()

            # Check if this line is an explicit translator / original author line
            if 'مترجم:' in cand or cand.startswith('اصل از') or re.match(r'^(?:اصل\s+)?از:\s*', cand):
                orig_m = re.search(r'(?:^|[؛،\n])\s*(?:اصل\s+از|از):\s*([^؛،\n]+)', cand)
                if not orig_m:
                    orig_m = re.search(r'(?:^|[؛،\n])\s*اصل\s+از\s+([^،؛\n]+)', cand)
                if orig_m:
                    work.original_author_name = orig_m.group(1).strip()
                    work.author_name = work.original_author_name

                trans_m = re.search(r'(?:^|[؛،\n])\s*(?:مترجم|اسم مترجم):\s*([^؛\n]+)', cand)
                if trans_m:
                    raw_trans = trans_m.group(1).strip()
                    clean_t, trans_date = extract_author_and_date(raw_trans)
                    work.translator_name = clean_t
                    if trans_date:
                        work.author_death_date_raw = trans_date
                        cent, sort_y, greg_calc = parse_date_triad(trans_date)
                        work.author_death_date_century = cent
                        work.author_death_date_sort_year = sort_y
                        if greg_calc:
                            work.author_death_date_gregorian_calculated = greg_calc
                    work.work_form = "translation"

                idx += 1
            elif is_author_line(cand, next_cand or cand_trans):
                raw_author_name, date_part = extract_author_and_date(cand)
                clean_name, auth_status = clean_author(raw_author_name)
                work.author_name = clean_name
                work.author_name_raw = raw_author_name
                work.authorship_status = auth_status
                if date_part:
                    work.author_death_date_raw = date_part
                    if re.search(r'(?:م\b|میلادی|قبل میلاد)', date_part) and not re.search(r'(?:ق\b|قمری)', date_part):
                        work.author_death_date_gregorian = date_part
                    else:
                        work.author_death_date_hijri = date_part
                    
                    cent, sort_y, greg_calc = parse_date_triad(date_part)
                    work.author_death_date_century = cent
                    work.author_death_date_sort_year = sort_y
                    if greg_calc:
                        work.author_death_date_gregorian_calculated = greg_calc
                idx += 1

                if not cand_trans and idx < total_p:
                    while idx < total_p and not PAGE_TAG_PATTERN.sub('', preamble_lines[idx]).strip():
                        idx += 1
                    if idx < total_p:
                        next_l = PAGE_TAG_PATTERN.sub('', preamble_lines[idx]).strip()
                        if next_l and any(c.isascii() and c.isalpha() for c in next_l):
                            cand_trans = next_l
                            idx += 1

                if cand_trans:
                    gm = re.search(r'\(([^)]+)\)$', cand_trans)
                    if gm:
                        work.author_transliteration = cand_trans[:gm.start()].strip()
                        work.author_death_date_gregorian = gm.group(1).strip()
                    else:
                        work.author_transliteration = cand_trans

        # 3. Remaining preamble: description, related_work, print, composition_date, dedication, incipit/explicit, bibliography
        rem_text = "\n".join(preamble_lines[idx:]).strip()
        if not rem_text:
            return

        # Translator (مترجم: ...)
        trans_m = re.search(r'(?:^|[؛،\n])\s*(?:مترجم|اسم مترجم):\s*([^؛\n]+)', rem_text)
        if trans_m:
            work.translator_name = trans_m.group(1).strip()
            rem_text = rem_text.replace(trans_m.group(0), ' ').strip()
            if not work.work_form:
                work.work_form = "translation"

        # Original author (اصل از: ... / اصل از ... / از: ...)
        orig_auth_m = re.search(r'(?:^|[؛،\n])\s*(?:اصل از|از):\s*([^؛\n]+)', rem_text)
        if not orig_auth_m:
            orig_auth_m = re.search(r'(?:^|[؛،\n])\s*اصل از\s+([^،؛\n]+?)(?=(?:[،؛]|\s+و\s+(?:ترجمه|شرح)|\n|$))', rem_text)
        if orig_auth_m:
            work.original_author_name = orig_auth_m.group(1).strip()
            rem_text = rem_text.replace(orig_auth_m.group(0), ' ').strip()

        # Composition date (تاریخ تألیف / تألیف / تاریخ اجازه / اجازه)
        comp_m = re.search(r'(?:^|\n)\s*(?:تاریخ تألیف|تألیف|تاریخ اجازه|اجازه):\s*([^\n]+)', rem_text)
        if comp_m:
            comp_val = comp_m.group(1).strip()
            place_m = re.search(r'(?:[؛،]\s*)?(?:محل تألیف|محل تالیف|محل صدور|محل نگارش):\s*([^؛،\n]+)', comp_val)
            if place_m:
                work.composition_date = comp_val[:place_m.start()].strip(' ؛،')
                work.composition_place = place_m.group(1).strip()
            else:
                work.composition_date = comp_val
            rem_text = rem_text.replace(comp_m.group(0), '\n').strip()

        # Dedication / Commissioned by (اهداء به / اهدا به / اهدایی به / به درخواست / به دستور / ...)
        ded_m = re.search(r'(?:^|\n)\s*(?:اهداء به|اهدا به|اهدایی به|به درخواست|به دستور|به فرمایش|به امر|به خواهش|به التماس|به فرموده|به نام):\s*([^\n]+)', rem_text)
        if ded_m:
            work.dedication = ded_m.group(1).strip()
            rem_text = rem_text.replace(ded_m.group(0), '\n').strip()

        # Related work (وابسته به: ...)
        rel_m = re.search(r'(?:^|\n)\s*وابسته به:\s*([^\n]+)', rem_text)
        if rel_m:
            work.related_work = rel_m.group(1).strip()
            rem_text = rem_text.replace(rel_m.group(0), ' ').strip()

        # Print info at work level: چاپ: ...
        work_print_m = re.search(r'(?:^|\n)\s*چاپ:\s*([^\n]+)', rem_text)
        if work_print_m:
            work.print_info = work_print_m.group(1).strip()

        # Work level incipit / explicit
        inc_m = re.search(r'(?:^|\n)\s*آغاز:\s*([^\n]+)', rem_text)
        if inc_m:
            work.incipit = inc_m.group(1).strip()
        exp_m = re.search(r'(?:^|\n)\s*انجام:\s*([^\n]+)', rem_text)
        if exp_m:
            work.explicit = exp_m.group(1).strip()

        # Commentaries and glosses: شرح و حواشی: / شروح و حواشی:
        comm_section_m = re.search(r'(?:^|\n)\s*(?:شرح و حواشی|شروح و حواشی):\s*(.+)', rem_text, re.DOTALL)
        if comm_section_m:
            comm_text = comm_section_m.group(1).strip()
            raw_comm_items = re.split(r'(?:^|\n)\s*\d+[\.\-]\s*', comm_text)
            comm_items = []
            for ci in raw_comm_items:
                ci_clean = re.sub(r'\[[^\]]+\]', '', ci).strip()
                ci_clean = PAGE_TAG_PATTERN.sub('', ci_clean).strip(' \n؛،-')
                if ci_clean:
                    comm_items.append(ci_clean)
            if comm_items:
                work.commentaries_and_glosses = comm_items

        # Bibliography citations [ ... ] - split each by semicolon (؛)
        bib_items = []
        bib_spans = []
        for m in re.finditer(r'\[([^\]]+)\]', rem_text):
            content = m.group(1).strip()
            if is_bib_citation(content):
                citations = [c.strip() for c in content.split('؛') if c.strip()]
                bib_items.extend(citations)
                bib_spans.append(m.group(0))

        if bib_items:
            work.bibliography = bib_items

        # Description is everything before incipit, print, commentaries, or bibliography
        desc_text = rem_text
        if comm_section_m:
            desc_text = desc_text.split(comm_section_m.group(0))[0]
        if work_print_m:
            desc_text = desc_text.split(work_print_m.group(0))[0]
        if inc_m:
            desc_text = desc_text.split(inc_m.group(0))[0]
        if exp_m:
            desc_text = desc_text.split(exp_m.group(0))[0]

        for b_span in bib_spans:
            desc_text = desc_text.replace(b_span, ' ')

        clean_desc = PAGE_TAG_PATTERN.sub('', desc_text).strip()
        if clean_desc:
            work.description = clean_desc

    def _parse_manuscript(self, ms_lines: List[str], current_page: int, fallback_seq: int, is_work_heterogeneous: bool = False, is_work_identification_uncertain: bool = False) -> Optional[Manuscript]:
        raw_text = "\n".join(ms_lines).strip()
        if not raw_text:
            return None

        ms = Manuscript(
            sequence_number=fallback_seq,
            page_start=current_page,
            page_end=current_page,
            is_distinct_work=is_work_heterogeneous,
            is_identification_uncertain=is_work_identification_uncertain,
            raw_text=raw_text
        )

        header_line = ms_lines[0].strip()
        clean_header = PAGE_TAG_PATTERN.sub('', header_line).strip()
        seq_m = re.match(r'^(\d+)[\.\s]\s*', clean_header)
        if seq_m:
            ms.sequence_number = int(seq_m.group(1))
            clean_header = clean_header[seq_m.end():].strip()

        header_match = re.match(r'([^؛]+)؛\s*([^؛]+)؛\s*شماره نسخه:\s*(.*)', clean_header)
        if header_match:
            ms.city = header_match.group(1).strip()
            ms.library = header_match.group(2).strip()
            ms.shelfmark = header_match.group(3).strip()

        rem_text = "\n".join(ms_lines[1:]).strip() if len(ms_lines) > 1 else ""

        ms_pages = [int(p) for p in PAGE_TAG_PATTERN.findall(raw_text)]
        if ms_pages:
            ms.page_start = ms_pages[0]
            ms.page_end = ms_pages[-1]

        extracted_spans: List[str] = []

        # 1. Bracketed notes: catalog citation vs editorial notes
        for cm in re.finditer(r'\[([^\]]+)\]', rem_text):
            b_content = cm.group(1).strip()
            if is_bib_citation(b_content):
                ms.catalog_citation = f"[{b_content}]"
            else:
                ms.editorial_notes.append(b_content)
            extracted_spans.append(cm.group(0))

        # 2. Original copy reference: نسخه اصل: ... / اصل نسخه: ... or همان نسخه بالا / همان نسخه
        orig_m = re.search(r'(?:^|[؛،\n]\s*)(?:نسخه\s+اصل|اصل\s+نسخه):\s*([^؛\n]+)', rem_text)
        if not orig_m:
            orig_m = re.search(r'(?:^|[؛،\n]\s*)(همان\s+نسخه(?:\s+اصل)?(?:\s+بالا|\s+شماره\s*\d+)?)', rem_text)
        if orig_m:
            orig_val = orig_m.group(1).strip() if orig_m.lastindex else orig_m.group(0).strip()
            ms.original_copy_ref = orig_val
            extracted_spans.append(orig_m.group(0).strip())
            if 'همان نسخه' in ms.original_copy_ref:
                m_num = re.search(r'شماره\s*(\d+)', ms.original_copy_ref)
                if m_num:
                    ms.parent_manuscript_seq = int(m_num.group(1))
                elif fallback_seq > 1:
                    ms.parent_manuscript_seq = fallback_seq - 1

        # 3. Print info: چاپ: ... / رساله چاپی است
        print_m = re.search(r'(?:^|[؛،\n])\s*(?:چاپ:\s*([^؛\n]+)|([^؛\n]*?(?:چاپی\s+است|رساله\s+چاپی|کتاب\s+چاپی|نسخه\s+چاپی)[^؛\n]*?))(?=[؛\n]|$)', rem_text)
        if print_m:
            ms.print_info = (print_m.group(1) or print_m.group(2)).strip()
            extracted_spans.append(print_m.group(0).strip())

        # 4. Contents / Included works: شامل: ... / حاوی: ... / مشتمل بر: ... / بخش ... است / در ... باب / از باب ... تا آخر / رسائل ...؛
        coll_title_m = re.search(r'(?:^|\n)\s*(رسائل\s+[^؛\n]+|مجموعه\s+رسائل\s+[^؛\n]+|مجموعه\s+[^؛\n]+?)(?=[؛\n])', rem_text)
        if coll_title_m:
            c_title = coll_title_m.group(1).strip()
            if not any(c_title.startswith(p) for p in ['در این مجموعه', 'از این مجموعه']):
                ms.contents_note = c_title
                extracted_spans.append(coll_title_m.group(0).strip(' ؛\n'))

        contents_m = re.search(r'(?:^|[؛،\n])\s*(?:شامل|حاوی|مشتمل بر)[:\s]\s*([^؛\n]+)', rem_text)
        if contents_m:
            c_val = contents_m.group(1).strip()
            if ms.contents_note:
                ms.contents_note += f"؛ {c_val}"
            else:
                ms.contents_note = c_val
            extracted_spans.append(contents_m.group(0))
        else:
            sec_m = re.search(r'(?:^|[؛،\n])\s*([^؛،\n]*?(?:بخش[^\n؛،]*است|بندی\s+از\s+آن\s+است|گزیده‌ای\s+است\s+از\s+آن|\d+\s+تعلیق\s+از\s+تعلیقات|در\s+(?:[^\s،؛]+\s+)?باب(?:[^\n؛،]*فصل)?|از\s+باب\s+\d+\s+تا\s+(?:آخر|پایان)|(?:مثنوی|دفتر|جلد|مجلد|قسمت|بخش)\s+(?:اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|\d+)(?:\s+(?:از|شامل|تا)[^؛\n]*|\s+را\s+دارد)?)[^؛\n]*?)(?=[؛\n]|،\s*(?:خط:|کا:|کاتب:|محرر:|تا:|جا:|کاغذ:|جلد:|$))', rem_text)
            if sec_m:
                s_val = sec_m.group(1).strip()
                if ms.contents_note:
                    ms.contents_note += f"؛ {s_val}"
                else:
                    ms.contents_note = s_val
                extracted_spans.append(sec_m.group(1).strip())

        lead_contents_m = re.search(r'(?:^|\n|^(?:[^\n؛]+[؛،]\s*))\s*([^؛\n]*?(?:گردآوری\s+شده|در\s+این\s+مجموعه|مجموعه\s*ای\s+است|بیاضی\s+است|بیاض|جنگ|نوحه\s+و\s+سوگواری|چند\s+مجلس\s+روضه|مراثی|مرثیه|روضه|درباره\s+|در\s+موضوع\s+)[^؛\n]*?)(?=[؛\n]|،\s*خط:)', rem_text)
        if lead_contents_m:
            l_val = lead_contents_m.group(1).strip()
            if not ms.contents_note:
                ms.contents_note = l_val
            elif l_val not in ms.contents_note:
                ms.contents_note += f"؛ {l_val}"
            extracted_spans.append(l_val)

        lead_pre_script_m = re.search(r'(?:^|\n)\s*([^؛\n]+?)(?:[؛\n]|،)\s*(?:خط:|بی‌کا|بی کا)', rem_text)
        if lead_pre_script_m:
            cand = lead_pre_script_m.group(1).strip()
            if not re.search(r'آغاز|انجام|نسخه اصل|اصل نسخه|چاپ:|افتادگی:', cand):
                if re.match(r'^(?:از|سروده)\s+', cand) and not ms.editorial_notes:
                    ms.editorial_notes.append(cand)
                else:
                    if not ms.contents_note:
                        ms.contents_note = cand
                    elif cand not in ms.contents_note:
                        ms.contents_note += f"؛ {cand}"
                extracted_spans.append(lead_pre_script_m.group(1).strip(' ؛،\n'))

        # 5. Editorial notes: توضیح: / تذکر: / نقد فهرست / در پایان اجازه ... است / در پایان نسخه ... / در این مجموعه ... / این نسخه ...
        for ep in [r'(?:^|[؛،\n])\s*توضیح:\s*([^؛\n]+)', r'(?:^|[؛،\n])\s*تذکر:\s*([^؛\n]+)']:
            for em in re.finditer(ep, rem_text):
                ed_text = PAGE_TAG_PATTERN.sub('', em.group(1)).strip()
                ms.editorial_notes.append(ed_text)
                extracted_spans.append(em.group(0))
        ijaza_m = re.search(r'(?:^|[؛،\n])\s*((?:در\s+پایان\s+)?اجازه\s+[^؛\n]+?(?:است)?)(?=[؛\n]|$)', rem_text)
        if ijaza_m:
            ms.editorial_notes.append(ijaza_m.group(1).strip())
            extracted_spans.append(ijaza_m.group(1).strip())
        col_end_m = re.search(r'(?:^|[؛،\n])\s*(در\s+پایان\s+نسخه\s+[^؛\n]+?(?:شده|است))(?=[؛\n]|$)', rem_text)
        if col_end_m:
            ms.editorial_notes.append(col_end_m.group(1).strip())
            extracted_spans.append(col_end_m.group(1).strip())
        maj_notes_m = re.search(r'(?:^|[؛،\n])\s*(در\s+این\s+مجموعه\s+[^؛\n]+?)(?=[؛\n]|$)', rem_text)
        if maj_notes_m:
            ms.editorial_notes.append(maj_notes_m.group(1).strip())
            extracted_spans.append(maj_notes_m.group(1).strip())
        ed_this_ms = re.search(r'(?:^|[؛،\n])\s*(این\s+(?:نسخه|کتاب|رساله|مجموعه)\s+[^؛\n]+?)(?=[؛\n]|$)', rem_text)
        if ed_this_ms:
            ed_text = PAGE_TAG_PATTERN.sub('', ed_this_ms.group(1)).strip()
            ms.editorial_notes.append(ed_text)
            extracted_spans.append(ed_this_ms.group(0))
        ed_auth_m = re.search(r'(?:^|[؛،\n])\s*([^؛،\n]*?(?:نام\s+(?:مؤلف|کتاب|رساله)|در\s+فهرست\s+(?:نام|از))[^؛\n]+?(?:شد|شده|است|ذکر شد|آمده))(?=[؛\n]|$)', rem_text)
        if ed_auth_m:
            ms.editorial_notes.append(ed_auth_m.group(1).strip())
            extracted_spans.append(ed_auth_m.group(1).strip())
        handwriting_diff_m = re.search(r'(?:^|[؛،\n])\s*((?:بعضی|برخی|چند)\s+(?:صفحه|صفحات|برگ)\s+(?:ظاهراً\s+)?[^؛\n]*?به\s+خط\s+[^؛\n]+?(?:است)?)(?=[؛\n]|$)', rem_text)
        if handwriting_diff_m:
            ms.editorial_notes.append(handwriting_diff_m.group(1).strip())
            extracted_spans.append(handwriting_diff_m.group(1).strip())
        scribe_note_m = re.search(r'(?:^|[؛،\n])\s*(کاتب\s+(?:می‌نویسد|گوید|ذکر\s+می‌کند|در\s+پایان\s+می‌نویسد)\s+که\s+[^؛\n]+)(?=[؛\n]|$)', rem_text)
        if scribe_note_m:
            ms.editorial_notes.append(scribe_note_m.group(1).strip())
            extracted_spans.append(scribe_note_m.group(1).strip())
        lead_intro_m = re.search(r'(?:^|[؛،\n])\s*(در\s+(?:ابتدا|اول|آغاز)\s+[^؛\n]+?(?:نوشته|آمده|دارد|است|دیده می‌شود))(?=[؛\n]|$)', rem_text)
        if lead_intro_m:
            ms.editorial_notes.append(lead_intro_m.group(1).strip())
            extracted_spans.append(lead_intro_m.group(1).strip())
        charm_m = re.search(r'(?:^|[؛،\n])\s*(در\s+(?:اول|آخر|پایان|ابتدا|آغاز|حاشیه|هامش|متن)[^؛\n]*?عبارت\s+«[^»]+»\s+دیده\s+می‌شود|عبارت\s+«یا\s+کبیکج»[^؛\n]*?(?:دیده\s+می‌شود|آمده|دارد|است))(?=[؛\n]|$)', rem_text)
        if charm_m:
            ms.editorial_notes.append(charm_m.group(1).strip())
            extracted_spans.append(charm_m.group(1).strip())
        from_orig_m = re.search(r'(?:^|[؛،\n])\s*((?:گویا\s+)?از\s+روی\s+(?:نسخه|جامع|کتاب|خط(?:\s+مصنف|\s+مؤلف)?)[^؛،\n]+?)(?=[؛،\n]|$)', rem_text)
        if from_orig_m:
            ms.editorial_notes.append(from_orig_m.group(1).strip())
            extracted_spans.append(from_orig_m.group(0).strip(' ؛،\n'))
        ed_comp_m = re.search(r'(?:^|[؛،\n])\s*([^؛،\n]*?(?:خلاصه\s*تر|مفصل\s*تر|متفاوت\s+با|مختصرتر)[^؛\n]+?است)(?=[؛\n]|$)', rem_text)
        if ed_comp_m:
            ms.editorial_notes.append(ed_comp_m.group(1).strip())
            extracted_spans.append(ed_comp_m.group(1).strip())
        auth_lead_m = re.search(r'(?:^|\n)\s*(از\s+[^؛\n]+?)(?=[؛\n]|،\s*خط:)', rem_text)
        if auth_lead_m:
            ms.editorial_notes.append(auth_lead_m.group(1).strip())
            extracted_spans.append(auth_lead_m.group(1).strip())
        ed_date_m = re.search(r'(?:^|[؛،\n])\s*(یک\s+جا\s+تاریخ\s+[^؛\n]+?)(?=[؛\n]|$)', rem_text)
        if ed_date_m:
            ms.editorial_notes.append(ed_date_m.group(1).strip())
            extracted_spans.append(ed_date_m.group(1).strip())
        ed_pkt_m = re.search(r'(?:^|[؛،\n])\s*(مجموعه\s+بخش‌های\s+پراکنده‌ای\s+[^؛\n]+?است)(?=[؛\n]|$)', rem_text)
        if ed_pkt_m:
            ms.editorial_notes.append(ed_pkt_m.group(1).strip())
            extracted_spans.append(ed_pkt_m.group(1).strip())

        # 6. Colophon extract: ترقیمه: / انجامه: / خاتمه:
        colophon_m = re.search(r'(?:^|[؛،\n]|\.\s*)\s*(?:ترقیمه|انجامه|خاتمه):\s*([^؛\n]+)', rem_text)
        if colophon_m:
            ms.colophon = colophon_m.group(1).strip()
            extracted_spans.append(colophon_m.group(0))

        # 7. Composition date: تاریخ تألیف / تألیف / تاریخ اجازه / اجازه
        comp_m = re.search(r'(?:^|[؛،\n])\s*(?:تاریخ تألیف|تألیف|تاریخ اجازه|اجازه):\s*(.+?)(?=(?:[؛،\n]\s*(?:محل تألیف|محل صدور)|(?:\s+این\s+(?:کتاب|رساله))|[؛\n]|$))', rem_text)
        if comp_m:
            ms.composition_date = comp_m.group(1).strip()
            extracted_spans.append(comp_m.group(0))

        # 8. Donor: اهدایی: / اهدا:
        donor_m = re.search(r'(?:^|[؛،\n])\s*(?:اهدایی|اهدا):\s*([^؛\n]+)', rem_text)
        if donor_m:
            ms.donor = donor_m.group(1).strip()
            extracted_spans.append(donor_m.group(0))

        # 9. Incipit / Explicit (multi-incipit and explicit extraction)
        incipits, explicits, m_inc, m_exp, inc_exp_spans = parse_incipits_and_explicits(rem_text)
        ms.incipits = incipits
        ms.explicits = explicits
        ms.incipit_matches_work = m_inc
        ms.explicit_matches_work = m_exp
        if incipits:
            ms.incipit_text = "\n".join(item['text'] for item in incipits if item.get('text'))
        if explicits:
            ms.explicit_text = "\n".join(item['text'] for item in explicits if item.get('text'))
        extracted_spans.extend(inc_exp_spans)

        # 10. Defects (افتادگی: ... / فاقد خطبه / دیباچه آن نیست / ناقص است / ...)
        defects_m = re.search(r'(?:^|[؛،\n])\s*افتادگی[؛:\.]\s*([^؛\n]+)', rem_text)
        if defects_m:
            ms.defects = defects_m.group(1).strip()
            extracted_spans.append(defects_m.group(0))

        def_extra_m = re.search(r'(?:^|[؛،\n])\s*([^؛،\n]*?(?:فاقد\s+(?:خطبه|دیباچه|سرلوح|مقدمه(?:[‌\s]+منثوره)?)|دیباچه\s+آن\s+نیست|بی\s+دیباچه|ناقص\s+است|نقص(?:‌| )?هایی\s+دارد|نقصان\s+دارد|ناتمام(?:\s+است)?|فقط\s+مقداری\s+از|نونویس|نو نویس|بخشی\s+از(?:\s+آن)?|قسمتی\s+از(?:\s+آن)?|(?:در\s+نسخه\s+ما\s+)?تنها\s+(?:دیباچه|مقدمه|آغاز|پایان|بخش|فصل)\s+آن\s+آمده)[^؛،\n]*?)(?=[؛،\n]|$)', rem_text)
        if def_extra_m:
            d_val = def_extra_m.group(1).strip()
            if ms.defects:
                ms.defects += f"؛ {d_val}"
            else:
                ms.defects = d_val
            extracted_spans.append(def_extra_m.group(1).strip())

        # 11. Identification uncertainty
        id_m = re.search(r'(?:^|[؛،\n])\s*(?:کتاب ناشناخته|همانندی نامعلوم|همانندی غیر معلوم|همانندی نامشخص)[:\.]?\s*([^؛\n]+)', rem_text)
        if id_m:
            ms.is_identification_uncertain = True
            ms.identification_notes = id_m.group(0).strip(' ؛،\n')
            extracted_spans.append(id_m.group(0))
        elif 'همانندی نامعلوم' in rem_text or 'همانندی غیر معلوم' in rem_text or 'کتاب ناشناخته' in rem_text:
            ms.is_identification_uncertain = True
            extracted_spans.extend(['همانندی نامعلوم', 'همانندی غیر معلوم', 'کتاب ناشناخته'])

        # 12. Commissioned by (به دستور / به فرمایش / به امر / به خواهش / به التماس / به فرموده / برای / به نام)
        comm_m = re.search(r'(?:^|[؛،\n])\s*([^؛،\n]*?(?:به دستور|به فرمایش|به امر|به خواهش|به التماس|به فرموده|به نام|برای)[:\s]\s*[^؛\n\[]+)', rem_text)
        if comm_m:
            full_comm_span = comm_m.group(1).strip()
            inner_m = re.search(r'(?:به دستور|به فرمایش|به امر|به خواهش|به التماس|به فرموده|به نام|برای)[:\s]\s*([^؛\n\[]+)', full_comm_span)
            if inner_m:
                c_val = inner_m.group(1).strip()
                c_val = re.sub(r'\s*(?:کتابت شده|نوشته شده|تحریر شده|نگاشته شده|انجام شده).*$', '', c_val).strip()
                if c_val:
                    ms.commissioned_by = c_val
                    extracted_spans.append(full_comm_span)

        # 13. Codicological labels
        SCRIPT_STOP = r'(?:[؛\n\[]|،\s*(?:کا:|کاتب:|محرر:|تا:|جا:|کاغذ:|جلد:|قطع:|ابعاد|اندازه|مصحح|مجدول|مذهب|مصور|رکابه‌دار|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)|مختلف(?:[‌\s]السطور|[‌\s]السطر)))'
        script_m = re.search(r'(?:^|[؛،\.\n])\s*(خط:\s*[^؛\n\[]+?)(?=' + SCRIPT_STOP + r'|$)', rem_text)
        if script_m:
            full_script_span = script_m.group(1).strip()
            ms.script = re.sub(r'^خط:\s*', '', full_script_span).strip()
            ms.scripts, ms.script_styles = parse_scripts_and_styles(ms.script)
            extracted_spans.append(full_script_span)
        else:
            script_no_colon_m = re.search(r'(?:^|[؛،\n\s])(?:و\s+)?(خط\s+(?:زیبا|خوش|عالی|نازیبا|متوسط|روان|خوانا|ناخوانا|جلی|خفی|معرب|شکسته|نستعلیق|نسخ|ثلث|رقاع|ریحان|توقیع|کوفی|مغربی|دیوانی))', rem_text)
            if script_no_colon_m:
                ms.script = script_no_colon_m.group(1).strip()
                ms.scripts, ms.script_styles = parse_scripts_and_styles(ms.script)
                extracted_spans.append(script_no_colon_m.group(0).strip(' ؛،\n'))

        if 'بی‌کا' in rem_text or 'بی کا' in rem_text:
            ms.is_bika = True
            ms.scribe = None
            ms.scribe_name = None
            extracted_spans.extend(['بی‌کا', 'بی کا'])
        else:
            SCRIBE_STOP = r'(?:[؛\n\[]|،\s*(?:تا:|جا:|خط:|بی‌تا|بی تا|بی‌کا|بی کا|برای:|برای\s+|به دستور|به نام|کاغذ:|جلد:|قطع:|ابعاد|اندازه|مصحح|مجدول|مذهب|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)))'
            scribe_m = re.search(r'(?:^|[؛،\n])\s*(?:کا:|کاتب:|محرر:)\s*([^؛\n\[]+?)(?=' + SCRIBE_STOP + r'|$)', rem_text)
            if scribe_m:
                s_val = scribe_m.group(1).strip()
                extracted_spans.append(scribe_m.group(0))
                if re.search(r'^=?\s*مؤلف(?:\s*\(گویا\))?$', s_val):
                    ms.is_autograph = True
                    ms.scribe = None
                    ms.scribe_name = None
                else:
                    ms.scribe = s_val
                    ms.scribe_name = s_val

        if any(w in rem_text for w in ['کاتب = مؤلف', 'کاتب=مؤلف', 'محرر = مؤلف', 'محرر=مؤلف', 'به خط مؤلف', 'بخط مؤلف', 'به خط خود مؤلف', 'به خط خود شاعر']):
            ms.is_autograph = True
            if ms.scribe and re.search(r'^=?\s*مؤلف(?:\s*\(گویا\))?$', ms.scribe.strip()):
                ms.scribe = None
                ms.scribe_name = None
            extracted_spans.extend(['کاتب = مؤلف', 'کاتب=مؤلف', 'محرر = مؤلف', 'محرر=مؤلف', 'به خط مؤلف', 'بخط مؤلف', 'به خط خود مؤلف', 'به خط خود شاعر'])

        if re.search(r'(?:^|[؛،\s])(?:بی‌تا|بی تا)(?:[؛،\s]|$)', rem_text):
            ms.is_bita = True
            extracted_spans.extend(['بی‌تا', 'بی تا'])

        DATE_STOP = r'(?:[؛\n\[]|،\s*(?:جا:|خط:|کا:|کاتب:|محرر:|کاغذ:|جلد:|قطع:|ابعاد|اندازه|مصحح|مجدول|مذهب|مصور|رکابه‌دار|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)|مختلف(?:[‌\s]السطور|[‌\s]السطر)))'
        date_m = re.search(r'(?:^|[؛،\n])\s*تا:\s*([^؛\n\[]+?)(?=' + DATE_STOP + r'|$)', rem_text)
        if date_m:
            ms.copy_date_raw = re.sub(r'\[[^\]]*\]?', '', date_m.group(1)).strip()
            extracted_spans.append(date_m.group(0))

        PLACE_STOP = r'(?:[؛\n\[]|،\s*(?:تا:|خط:|کا:|کاتب:|محرر:|کاغذ:|جلد:|قطع:|ابعاد|اندازه|مصحح|مجدول|مذهب|مصور|رکابه‌دار|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)|مختلف(?:[‌\s]السطور|[‌\s]السطر)))'
        place_m = re.search(r'(?:^|[؛،\n])\s*جا:\s*([^؛\n\[]+?)(?=' + PLACE_STOP + r'|$)', rem_text)
        if place_m:
            ms.copy_place = re.sub(r'\[[^\]]*\]?', '', place_m.group(1)).strip()
            extracted_spans.append(place_m.group(0))

        # Folios extraction: robust multi-candidate scoring to avoid capturing defects/partial page notes (e.g. 21صفحه آغاز نونویس)
        folio_candidates = []
        rem_len = len(rem_text)
        folio_pat = re.compile(r'(?:^|[؛،\s])(?<!\bدر\s)(?<!\bاز\s)(?<!\bبه\s)(?<!\bتا\s)(\d+[\d\s\/\-–\.]*(?:صص|ص|گ|برگ|ورق|صفحه)(?!\w)(?:\s*\([^)]+\))?)')
        for fm in folio_pat.finditer(rem_text):
            f_val = fm.group(1).strip()
            num_m = re.search(r'^\d+', f_val)
            if not num_m:
                continue
            f_num = int(num_m.group(0))
            if f_num <= 0 or f_num > 6000:
                continue

            span_start = fm.start()
            span_end = fm.end()
            post_ctx = rem_text[span_end:min(rem_len, span_end + 60)]
            pre_ctx = rem_text[max(0, span_start - 30):span_start]

            score = 0
            # Negative context: defects, partial copies, notes
            if re.search(r'(?:نونویس|نو نویس|افتادگی|افتاده|ناقص|نانوشته|سفید|الحاق|اضافی|برگ\s*شمار)', post_ctx):
                score -= 100
            if re.search(r'(?:از|تا|در|حدود|فقط|شامل|دارای)\s*$', pre_ctx):
                score -= 50

            # Positive context: proximity to standard physical codicological elements
            if re.search(r'سطر|سطور', post_ctx):
                score += 45
            if re.search(r'اندازه|سم|\[ف:', post_ctx):
                score += 35
            if re.search(r'(?:کاغذ|جلد):', pre_ctx):
                score += 30
            if 'گ' in f_val:
                score += 15

            # Positional score: physical characteristics appear at the end of the entry
            ratio = span_start / max(1, rem_len)
            score += int(ratio * 30)

            folio_candidates.append({
                'val': f_val,
                'score': score,
                'span': fm.group(0).strip(' ؛،\n'),
            })

        if folio_candidates:
            folio_candidates.sort(key=lambda x: x['score'], reverse=True)
            best_folio = folio_candidates[0]
            if best_folio['score'] >= 0 or len(folio_candidates) == 1:
                ms.folios = best_folio['val']
                extracted_spans.append(best_folio['span'])
                if any(w in ms.folios for w in ['هامش', 'حاشیه']):
                    ms.has_marginal_notes = True

        # Explicit text dimensions: ابعاد متن: / اندازه متن: / سطح نوشته:
        text_dim_m = re.search(r'(?:^|[؛،\n])\s*(?:ابعاد متن|اندازه متن|سطح نوشته):\s*([^؛،\n\[]+)', rem_text)
        if text_dim_m:
            ms.text_dimensions = text_dim_m.group(1).strip()
            extracted_spans.append(text_dim_m.group(0))

        # Lines count, column layouts and parenthesized text dimensions (e.g. 21 سطر دوستونی, 25 سطر چهار ستونی, 10 تا 20 بیت)
        all_lines = list(re.finditer(r'((?:(?:\d+[\d\s\/\-–\.]*(?:تا|الی|–|-)?\s*\d*[\d\s\/\-–\.]*(?:سطور|سطر|بیت)|مختلف(?:[‌\s]السطور|[‌\s]السطر)|سطور چلیپایی)(?:\s+(?:راسته\s+و\s+چلیپا|راسته\s*چلیپا|چلیپایی|چلیپا|راسته|(?:دو|سه|چهار|چند)\s*ستونی))?|(?:هر\s+صفحه\s+)?\d+\s+تا\s+\d+\s+بیت))(?:\s*\(([0-9\/\,\.\-–\s]+[×xX\*][0-9\/\,\.\-–\s]+(?:\s*سم)?)\)(?:\s*سطر)?)?', rem_text))
        valid_lines = [m for m in all_lines if not re.search(r'(?:افزودن|کسر|کمبود|زیادتی|افتادن)\s*$', rem_text[:m.start()])]
        best_m = None
        for m in valid_lines:
            if m.group(2):
                best_m = m
                break
        if not best_m and valid_lines:
            best_m = valid_lines[-1]
        if best_m:
            ms.lines = best_m.group(1).strip()
            if best_m.group(2) and not ms.text_dimensions:
                ms.text_dimensions = best_m.group(2).strip()
            extracted_spans.append(best_m.group(0))

        cols_m = re.search(r'(?:^|[؛،\s])((?:دو|سه|چهار|چند)\s*ستونی)(?=[؛،\s]|$)', rem_text)
        if cols_m:
            extracted_spans.append(cols_m.group(1).strip())
            if ms.lines and 'ستونی' not in ms.lines:
                ms.lines += f" {cols_m.group(1).strip()}"

        # Text placement: در متن و هامش / در هامش / در متن / در حاشیه
        placement_m = re.search(r'(?:^|[؛،\n])\s*(در\s+(?:متن\s+و\s+هامش|متن\s+و\s+حاشیه|هامش|حاشیه|متن))(?=[؛،\n]|$)', rem_text)
        if placement_m:
            p_val = placement_m.group(1).strip()
            extracted_spans.append(placement_m.group(0).strip(' ؛،\n'))
            if any(w in p_val for w in ['هامش', 'حاشیه']):
                ms.has_marginal_notes = True

        # Overall dimensions (negative lookahead for متن)
        dim_m = re.search(r'(?:^|[؛،\n])\s*(?:اندازه|ابعاد)(?!\s*متن):\s*([^؛،\n\[]+)', rem_text)
        if dim_m:
            ms.dimensions = dim_m.group(1).strip()
            extracted_spans.append(dim_m.group(0))

        CODICOLOGY_STOP = r'(?:[؛\n\[]|،\s*(?:جلد:|کاغذ:|قطع:|ابعاد|اندازه|خط:|کا:|تا:|جا:|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)|مختلف السطر))'

        paper_m = re.search(r'(?:^|[؛،\n])\s*کاغذ:\s*([^؛\n\[]+?)(?=' + CODICOLOGY_STOP + r'|$)', rem_text)
        if paper_m:
            ms.paper = paper_m.group(1).strip()
            extracted_spans.append(paper_m.group(0))

        binding_m = re.search(r'(?:^|[؛،\n])\s*جلد:\s*([^؛\n\[]+?)(?=' + CODICOLOGY_STOP + r'|$)', rem_text)
        if binding_m:
            ms.binding = binding_m.group(1).strip()
            extracted_spans.append(binding_m.group(0))

        format_m = re.search(r'(?:^|[؛،\n])\s*قطع:\s*([^؛\n\[]+?)(?=' + CODICOLOGY_STOP + r'|$)', rem_text)
        if format_m:
            ms.format = format_m.group(1).strip()
            extracted_spans.append(format_m.group(0))

        # Ownership & Seals
        raw_seals = []
        for sp in [
            r'(?:دارای\s*)?مهر(?:[‌\s]+(?:وقف|بیضی|مربع|مدور|چهارگوش|هشت\s*ضلعی|بادامی))?[:\s]\s*([^؛\n]+)',
            r'تملک[ی:\s]\s*([^؛\n]+)',
            r'(?:تاریخ\s+)?(?:وقف|واقف)[:\s]\s*([^؛\n]+)',
            r'(?:از\s+موقوفات|وقف[‌\s]?نامه(?:\s+نسخه)?|موقوفه)\s+([^؛\n]+)',
            r'(?:انتقالی\s+از|خریداری(?:\s+از|\s+شده\s+از|\s+در|\s+به\s+سال)?|اهدایی\s+از|از\s+کتابخانه)\s+([^؛\n]+)',
            r'(?:روی\s+جلد\s+نوشته|در\s+پشت\s+جلد|در\s+عطف\s+جلد|در\s+برگ\s+اول|در\s+پشت\s+صفحه\s+بدرقه)\s*([^؛\n]+)'
        ]:
            for sm in re.finditer(sp, rem_text):
                full_match = sm.group(0).strip()
                ms.ownership_and_seals.append(full_match)
                extracted_spans.append(full_match)
                if re.match(r'^(?:دارای\s*)?مهر', full_match):
                    raw_seals.append(full_match)
                else:
                    m_inner_seal = re.findall(r'با مهر\s*«([^»]+)»(?:\s*\(([^)]+)\))?', full_match)
                    for is_text, is_shape in m_inner_seal:
                        shape_str = f" ({is_shape})" if is_shape else ""
                        raw_seals.append(f"مهر: {is_text}{shape_str}")

        if raw_seals:
            ms.seals = parse_seals(raw_seals)

        ANNEX_STOP = r'(?:[؛\n\[]|،\s*(?:خط:|کا:|کاتب:|محرر:|تا:|جا:|کاغذ:|جلد:|قطع:|ابعاد|اندازه|مصحح|مجدول|مذهب|مصور|رکابه‌دار|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)|مختلف(?:[‌\s]السطور|[‌\s]السطر)))'
        annex_pat = re.compile(r'(?:^|[؛\n])\s*([^؛\n]*?(?:ضمیمه|الحاق|دنباله\s+(?:رساله|کتاب)|رساله\s+ضمیمه|یادداشت|سپس\s+«|پس\s+از\s+این|مطالب\s+پراکنده|عبارت[ی‌]?(?:\s+ترکی|\s+فارسی|\s+عربی)?\s+به\s+تاریخ|در\s+\d+\s*[پرو]\s+عبارت|در\s+پایان\s+[^؛\n]+?(?:است|دارد)|(?:چند\s+تاریخ|تاریخ|ثبت|یادداشت)\s+(?:تولد|ولادت|وفات))[^؛\n]*?)(?=' + ANNEX_STOP + r'|$)')
        for am in annex_pat.finditer(rem_text):
            ms.annex_notes.append(am.group(1).strip())
            extracted_spans.append(am.group(1).strip())

        # Colophon: Check if there is colophon text starting with "تمام شد" or "تمت" or "پایان یافت" or autograph certificate "با دستخط ... در پایان نسخه"
        if not ms.colophon:
            colo_cert_m = re.search(r'(?:^|[؛،\n])\s*(با\s+دستخط\s+[^؛\n]+?:\s*«[^»]+»)', rem_text)
            if colo_cert_m:
                ms.colophon = colo_cert_m.group(1).strip()
                extracted_spans.append(colo_cert_m.group(1).strip())
            else:
                colo_start_m = re.search(r'(?:^|[؛\n])\s*(تمام شد\s+[^؛\n]+|تمت\s+[^؛\n]+|پایان یافت\s+[^؛\n]+|(?:در\s+)?(?:آخر|پایان)\s+(?:آن\s+|نسخه\s+)?آمده\s+«[^»]+»|قبل\s+العصر\s+[^؛\n]+?\.(?=[؛\n\s]*(?:خط:|$)))', rem_text)
                if colo_start_m:
                    ms.colophon = colo_start_m.group(1).strip()
                    extracted_spans.append(colo_start_m.group(0))

        # Boolean flags
        if 'مصحح' in rem_text:
            ms.is_corrected = True
            extracted_spans.append('مصحح')
        if 'محشی' in rem_text or 'در حواشی' in rem_text or 'در حاشیه' in rem_text:
            ms.has_marginal_notes = True
            extracted_spans.extend(['محشی', 'در حواشی', 'در حاشیه'])
        ruled_m = re.search(r'(?:صفحات\s+)?مجدول(?:\s*(?:و\s*)?(?:زرین|به\s+زر(?:\s+و\s+[^؛،\n]+)?|الوان|کمند|ساده|محرر|مذهب|مرصع))*|(?:دارای\s+|با\s+)?کمند(?:[‌\s]کشی(?:\s+شده)?)?(?:\s+به\s+زر(?:\s+و\s+مشکی)?)?|(?:صفحات\s+)?جدول\s+[^\s؛،\n]+\s+خطی|(?:دارای\s+)?جدول[‌\s]کشی|با\s+جدول', rem_text)
        if ruled_m:
            ms.is_ruled = True
            r_str = ruled_m.group(0).strip()
            if any(gold in r_str for gold in ['زرین', 'زر', 'مذهب', 'طلا']):
                ms.is_illuminated = True
            extracted_spans.append(r_str)
        elif 'مجدول' in rem_text or 'با جدول' in rem_text:
            ms.is_ruled = True
            extracted_spans.extend(['مجدول', 'با جدول'])
        if 'رکابه‌دار' in rem_text:
            ms.has_catchwords = True
            extracted_spans.append('رکابه‌دار')
        if 'عکسی' in rem_text or 'عکس' in clean_header or (ms.original_copy_ref and 'عکسی' in ms.original_copy_ref):
            ms.is_facsimile = True
            ms.sequence_number = None
            extracted_spans.append('عکسی')
        if 'غیر همانند' in rem_text or 'غیرهمانند' in rem_text:
            ms.is_distinct_work = True
            extracted_spans.extend(['غیر همانند', 'غیرهمانند'])

        # is_collated: مقابله شده / مقابله گردیده / تصحیح و مقابله / مقابل کرده / با بلاغ ... / دارای بلاغ / با نشانی بلاغ
        if re.search(r'(?:مقابله\s+(?:شده|گردیده|نموده|کردم)|تصحیح\s+و\s+مقابله|مقابل\s+کرده|(?:با|دارای)\s+(?:علامت|نشان(?:ی)?|امضای|امضا)?\s*(?:بلاغ|بلغ)|با\s+بلاغ|با\s+(?:نشان|عبارت)\s*«بلغ[»\s]|سه\s+بار\s+مقابله|دو\s+مرتبه\s+مقابله)', rem_text):
            ms.is_collated = True
            m_coll = re.search(r'(?:[؛،\n]\s*)?(?:[^\n؛،]*مقابله[^\n؛،]*|(?:با|دارای)\s+(?:علامت|نشان(?:ی)?|امضای|امضا)?\s*(?:بلاغ|بلغ)[^\n؛،]*|با\s+(?:نشان|عبارت)\s*«بلغ[^»]+»[^\n؛،]*)', rem_text)
            if m_coll:
                extracted_spans.append(m_coll.group(0).strip(' ؛،\n'))
            for coll_s in ['دارای بلاغ', 'با نشانی بلاغ', 'با امضای بلاغ', 'با بلاغ']:
                if coll_s in rem_text:
                    extracted_spans.append(coll_s)

        # is_illuminated: مذهب / تذهیب / زرین / طلاپوش / سرلوح مذهب / سرلوح مرصع / شمسه مذهب / کتیبه مرصع / زرنگار / زرافشان / اکلیل
        illum_m = re.search(r'(?:دارای\s+)?(?:(?:سرلوح|کتیبه|شمسه)\s+)?(?:مذهب|مرصع|زرین)(?:\s+و\s+(?:مذهب|مرصع|زرین))?|تذهیب|طلاپوش|زرنگار|زرافشان|اکلیل(?:[‌\s]اندازی)?', rem_text)
        if illum_m and not re.search(r'مذهب\s+(?:شیعه|حنفی|شافعی|مالکی|امامیه|جعفری|اهل\s+سنت)', illum_m.group(0)):
            ms.is_illuminated = True
            extracted_spans.append(illum_m.group(0).strip())
        if 'اکلیل' in rem_text:
            ms.is_illuminated = True
            extracted_spans.append('اکلیل')

        # is_illustrated: مصور / دارای تصاویر / با تصاویر / با اشکال هندسی / دارای عکس‌های فتوگرافیک
        if re.search(r'(?:نسخه\s+)?مصور(?:\s+است)?|دارای\s+(?:تصاویر|عکس‌های\s+فتوگرافیک|نقاشی|نگاره)|با\s+(?:اشکال\s+هندسی|تصاویر)', rem_text):
            ms.is_illustrated = True
            m_ill = re.search(r'(?:[؛،\n]\s*)?(?:(?:نسخه\s+)?مصور(?:\s+است)?(?:\s+به\s+[^؛،\n]+)?|دارای\s+(?:تصاویر|عکس‌های\s+فتوگرافیک|نقاشی|نگاره)[^؛،\n]*|با\s+(?:اشکال\s+هندسی|تصاویر)[^؛،\n]*)', rem_text)
            if m_ill:
                extracted_spans.append(m_ill.group(0).strip(' ؛،\n'))
            for ill_s in ['مصور', 'نسخه مصور است', 'با اشکال هندسی', 'دارای عکس‌های فتوگرافیک']:
                if ill_s in rem_text:
                    extracted_spans.append(ill_s)

        MARG_STOP = r'(?:[؛\n\[]|،\s*(?:مصحح|مجدول|مذهب|مصور|رکابه‌دار|خط:|کا:|کاتب:|محرر:|تا:|جا:|کاغذ:|جلد:|قطع:|ابعاد|اندازه|\d+[\d\s\/\-–\.]*(?:ص|صص|گ|برگ|ورق|صفحه|سطر)|مختلف(?:[‌\s]السطور|[‌\s]السطر)))'
        marg_m = re.search(r'(?:^|[؛،\n])\s*((?:محشی|(?:[^\n؛،]*\s+)?حاشیه‌نویسی)\s+(?:(?:لغوی\s+)?با\s+(?:نشان(?:[‌\s]?های)?|علامت|رموز|رمز)|(?:لغوی\s+)?از|به\s+خط|به\s+نقل\s+از)\s+[^؛\n]+?)(?=' + MARG_STOP + r'|$)', rem_text)
        if marg_m:
            ms.has_marginal_notes = True
            extracted_spans.append(marg_m.group(1).strip())
            if re.search(r'(?:منه|مؤلف|مد\s*ظله|سلمه\s+الله|دام\s*ظله|عفی\s+عنه|رحمه\s+الله)', marg_m.group(1)):
                ms.has_author_marginalia = True

        if re.search(r'(?:صورت\s+چلیپا|به\s+صورت\s+چلیپا|چلیپا\s+نویس)', rem_text):
            if 'چلیپا' not in ms.script_styles:
                ms.script_styles.append('چلیپا')
            extracted_spans.extend(['صورت چلیپا', 'به صورت چلیپا', 'چلیپا نویس'])

        if re.search(r'(?:حمایلی|به صورت حمایلی)', rem_text):
            if 'حمایلی' not in ms.script_styles:
                ms.script_styles.append('حمایلی')
            m_hm = re.search(r'[^؛\n]*?(?:حمایلی|به\s+صورت\s+حمایلی)[^؛\n]*', rem_text)
            if m_hm:
                extracted_spans.append(m_hm.group(0).strip(' ؛،\n'))

        if re.search(r'(?:^|[؛،\n])\s*(با\s+حواشی\s+[^؛\n]*?)(?=[؛\n]|$)', rem_text):
            ms.has_marginal_notes = True
            m_bh = re.search(r'(?:^|[؛،\n])\s*(با\s+حواشی\s+[^؛\n]*?)(?=[؛\n]|$)', rem_text)
            if m_bh:
                extracted_spans.append(m_bh.group(1).strip())

        if re.search(r'(?:سرلوح|سر لوح)', rem_text):
            ms.is_illuminated = True
            m_sl = re.search(r'(?:دارای|با)?\s*(?:یک|دو|سه|چهار|\d+)?\s*سر[‌\s]?لوح(?:[‌\s]+های)?[^\n؛،]*', rem_text)
            if m_sl:
                extracted_spans.append(m_sl.group(0).strip())
            for sl_span in ['دارای سرلوح', 'دارای سر لوح', 'با سرلوح', 'با سر لوح', 'با سر لوح‌های زرین', 'سرلوح‌های زرین', 'سر لوح‌های زرین', 'با دو سرلوح زرین', 'با یک سرلوح']:
                if sl_span in rem_text:
                    extracted_spans.append(sl_span)

        # has_author_marginalia: محشی با نشان منه / محشی از مؤلف / منه سلمه الله / منه مد ظله ...
        if re.search(r'(?:محشی\s+با\s+(?:نشان|علامت|امضاء|امضای)\s*«?منه|محشی\s+(?:از|به\s+خط)\s+مؤلف|حاشیه(?:[‌\s]+های[ی‌]?)?\s+از\s+مؤلف|منه\s+(?:سلمه\s+الله|مد\s*ظله|دام\s*ظله|عفی\s+عنه|رحمه\s+الله|قدس\s+سره|ایده\s+الله|حفظه\s+الله|دام\s+علوه|مد\s+عزه))', rem_text):
            ms.has_author_marginalia = True
            ms.has_marginal_notes = True

        # Misbound / disordered leaves notes
        if re.search(r'(?:آغاز\s+در\s+پایان|در\s+صحافی\s+در\s+پایان|آشفته\s+و\s+پس\s+و\s+پیش|جابجایی\s+اوراق|برگ‌های\s+آشفته)', rem_text):
            disorder_m = re.search(r'[^؛\n]*(?:آغاز\s+در\s+پایان|در\s+صحافی\s+در\s+پایان|آشفته\s+و\s+پس\s+و\s+پیش|جابجایی\s+اوراق|برگ‌های\s+آشفته)[^؛\n]*', rem_text)
            if disorder_m:
                d_text = disorder_m.group(0).strip()
                if ms.identification_notes:
                    ms.identification_notes += f"؛ {d_text}"
                else:
                    ms.identification_notes = d_text
                extracted_spans.append(d_text)

        # Residual notes calculation
        res_clean = rem_text
        for span in sorted(list(set(extracted_spans)), key=len, reverse=True):
            if span:
                res_clean = res_clean.replace(span, ' ')

        labels = [
            'اندازه:', 'ابعاد:', 'ابعاد متن:', 'اندازه متن:', 'سطح نوشته:',
            'کاغذ:', 'جلد:', 'قطع:', 'آغاز:', 'انجام:', 'نسخه اصل:',
            'خط:', 'کا:', 'تا:', 'جا:', 'افتادگی:', 'چاپ:', 'شامل:',
            'اهدایی:', 'اهدا:', 'ترقیمه:', 'انجامه:', 'خاتمه:',
            'تاریخ تألیف:', 'تألیف:', 'تاریخ اجازه:', 'اجازه:',
            'توضیح:', 'تذکر:', 'به دستور:', 'به دستور',
            'به فرمایش:', 'به فرمایش', 'به امر:', 'به امر',
            'به فرموده:', 'به فرموده', 'برای:', 'برای', 'به نام:', 'به نام',
            'کاتب:', 'محرر:', 'کاتب = مؤلف', 'کاتب=مؤلف', 'محرر = مؤلف', 'محرر=مؤلف',
            'بی‌تا', 'بی تا', 'بی‌کا', 'بی کا', 'مصحح', 'محشی', 'مجدول', 'مذهب', 'زرین', 'مرصع', 'مذهب و مرصع',
            'مقابله شده', 'واقف:', 'واقف', 'تاریخ وقف:', 'تاریخ وقف', 'افتادگی؛', 'افتادگی.',
            'نسخه اصل:', 'اصل نسخه:'
        ]
        for lb in labels:
            res_clean = res_clean.replace(lb, ' ')

        res_clean = re.sub(r'<!--[^>]+-->', ' ', res_clean)
        res_clean = re.sub(r'(?:^|[؛،\s])و(?=[؛،\s]|$)', ' ', res_clean)
        res_clean = re.sub(r'^[؛،\s\n\-\.]+|[؛،\s\n\-\.]+$', ' ', res_clean)
        res_clean = re.sub(r'[؛،\n\-\.]{2,}', ' ', res_clean)
        res_clean = re.sub(r'\s+', ' ', res_clean).strip(' ؛،-.')

        if len(re.findall(r'[\u0600-\u06FF]', res_clean)) >= 3 and res_clean.strip() not in ['تاریخ', 'آغاز', 'انجام', 'سطر', 'سطور', 'برابر', 'محرر', 'کاتب']:
            ms.residual_notes = res_clean

        return ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            'volume_number': self.volume_number,
            'total_works': len(self.works),
            'total_referrals': len(self.referrals),
            'total_manuscripts': sum(len(w.manuscripts) for w in self.works),
            'referrals': [asdict(r) for r in self.referrals],
            'works': [asdict(w) for w in self.works]
        }

    def export_json(self, output_file: str, indent: int = 2):
        data = self.to_dict()
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        print(f"Exported volume {self.volume_number} to {output_file}")
        print(f"  - Works: {data['total_works']}")
        print(f"  - Referrals: {data['total_referrals']}")
        print(f"  - Manuscripts: {data['total_manuscripts']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fankha_parser.py <volume_num | input_file> [output_json_path]")
        sys.exit(1)

    arg1 = sys.argv[1]
    if arg1.isdigit():
        vol_num = int(arg1)
        input_file = f"sources/text/fahares_vol_{vol_num:02d}.txt"
        output_file = sys.argv[2] if len(sys.argv) > 2 else f"sources/json/fahares_vol_{vol_num:02d}.json"
    else:
        input_file = arg1
        m = re.search(r'vol_(\d+)', input_file)
        vol_num = int(m.group(1)) if m else 18
        output_file = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    parser = FankhaParser(vol_num)
    parser.parse_file(input_file)
    parser.export_json(output_file)

if __name__ == '__main__':
    main()
