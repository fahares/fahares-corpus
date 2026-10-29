#!/usr/bin/env python3
"""
Fankha parser v2 (fahares item 87).

Line-classifying rewrite of fankha_parser.py. It reuses v1's title/subject/language and author-date helpers
(they score 100% on the gold set) and replaces everything that decides which piece of text belongs to which
field. Design and JSON shape: fahares/docs/plans/fankha-parser-v2.md, sections 4 and 8.

Main differences from v1:
- page tags are removed from every line before parsing; each line keeps its line number and pages;
- an incipit/explicit ends at the end of its line (or where a physical-description group starts on it);
- text before the first physical label of the physical line is a leading segment, split into contents scope,
  copy description («غیر همانند»), original-copy reference and notes;
- the physical line is tokenised into «؛» groups and «،» chunks, each chunk read by its leading label;
- hedge words are split off structural values into `hedge`;
- an author line is recognised by the Latin line that follows it, with or without dates.

Usage: fankha_parser_v2.py [VOL ...]   (default: all 34 volumes; writes json/fankha_v2/)
"""
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_parser import (  # noqa: E402
    parse_header_line, extract_title_form_and_clean, parse_subjects, parse_languages, parse_date_triad,
    extract_author_and_date, is_author_line, is_bib_citation, split_bib_citations, is_catalog_citation,
)

PARSER_VERSION = '2.0.0'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = re.compile(r'<!--\s*page:\s*(\d+)\s*-->')
INVISIBLE = re.compile(r'[‎‏‪-‮﻿]')
LATIN = re.compile(r'[A-Za-zāīūḥṣṭẓḍčšžġḡ‘’]')
PERSIAN = re.compile(r'[؀-ۿ]')

# ---------------------------------------------------------------- text preparation

class Line:
    __slots__ = ('no', 'text', 'page_start', 'page_end', 'tag_at')

    def __init__(self, no, text, page_start, page_end, tag_at):
        self.no, self.text, self.page_start, self.page_end, self.tag_at = no, text, page_start, page_end, tag_at


def prepare(text: str) -> List[Line]:
    """Strip page tags. `tag_at` is the offset in the cleaned text where the last mid-line tag stood."""
    out, page = [], 1
    for i, raw in enumerate(text.split('\n'), 1):
        start = page
        tag_at = None
        pieces, pos = [], 0
        for m in PAGE.finditer(raw):
            pieces.append(raw[pos:m.start()])
            before = ' '.join(''.join(pieces).split())
            if before and raw[m.end():].strip():
                tag_at = len(before)
            page = int(m.group(1))
            pos = m.end()
        pieces.append(raw[pos:])
        clean = re.sub(r'\s+', ' ', INVISIBLE.sub('', ''.join(pieces))).strip()
        if start != page and not ''.join(pieces[:1]).strip():
            start = page          # tag at the start of the line: the line belongs to the new page
        out.append(Line(i, clean, start, page, tag_at))
    return out

# ---------------------------------------------------------------- hedges

HEDGE_LEAD = re.compile(r'^(?P<h>[؟?]|منسوب\s+به|گویا|ظاهراً|ظاهرا|احتمالاً|احتمالا|محتملاً|محتملا|شاید|به\s+احتمال\s+قوی)'
                        r'(?:\s+از)?(?:\s+|$)')
HEDGE_TAIL = re.compile(r'\s*(?P<h>\((?:؟|\?|احتمالاً|احتمالا|ظاهراً|ظاهرا|گویا)\)|[؟?])$')


def split_hedge(v: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not v:
        return v, None
    hedges = []
    m = HEDGE_LEAD.match(v)
    if m:
        hedges.append(m.group('h'))
        v = v[m.end():]
    m = HEDGE_TAIL.search(v)
    if m:
        hedges.append(m.group('h').strip('()'))
        v = v[:m.start()]
    v = v.strip(' ،؛.:')
    return (v or None), (' '.join(hedges) or None)

# ---------------------------------------------------------------- scripts (rulings of question 2)

SCRIPT_TYPES = ['شکسته نستعلیق', 'نستعلیق شکسته', 'نستعلیق', 'نسخ', 'شکسته', 'تعلیق', 'رقاع', 'رقعه', 'رقعی', 'ثلث',
                'کوفی', 'ریحان', 'محقق', 'توقیع', 'غبار', 'دیوانی', 'سیاق', 'مغربی', 'بهار', 'تحریری', 'تایپی',
                'لاتین', 'پهلوی', 'ارمنی', 'عبری', 'سریانی', 'گرجی', 'اویغوری', 'دیونا گری', 'دیوناگری', 'اوستایی',
                'مسند', 'عربی', 'ترکی', 'سنسکریت', 'چاپی', 'سنگی']
SCRIPT_TYPE_RE = re.compile('|'.join(sorted(map(re.escape, SCRIPT_TYPES), key=len, reverse=True)))


def parse_script_item(item: str) -> Dict[str, Any]:
    item = ' '.join(item.split())
    quals = []
    m = re.search(r'مایل\s+به\s+\S+', item)          # «نسخ مایل به رقعه»: one script, qualified
    if m:
        quals.append(m.group(0))
        item = (item[:m.start()] + item[m.end():]).strip()
    types = SCRIPT_TYPE_RE.findall(item)
    if 'شکسته نستعلیق' in types or 'نستعلیق شکسته' in types:
        types = [t for t in types if t not in ('شکسته', 'نستعلیق', 'نستعلیق شکسته')]
        types = ['شکسته نستعلیق'] + [t for t in types if t != 'شکسته نستعلیق']
    base = [t for t in types if t != 'تحریری'] or types
    typ = base[0] if base else None
    rest = SCRIPT_TYPE_RE.sub(' ', item)
    if 'تحریری' in types and typ != 'تحریری':
        quals.append('تحریری')
    quals += [w for w in re.split(r'\s+و\s+|\s+', rest.strip()) if w and w != 'و']
    return {'type': typ, 'qualifiers': quals}


def parse_scripts(raw: Optional[str]) -> List[Dict[str, Any]]:
    """«نسخ و نستعلیق تحریری» → two scripts; «نستعلیق راسته و چلیپا» → one script with two qualifiers."""
    if not raw:
        return []
    items: List[Dict[str, Any]] = []
    for part in re.split(r'\s*،\s*', raw):
        words = re.split(r'\s+و\s+', part)
        for w in words:
            w = w.strip()
            if not w:
                continue
            it = parse_script_item(w)
            if it['type'] is None and items:          # «… راسته و چلیپا»: qualifiers of the previous script
                items[-1]['qualifiers'] += it['qualifiers']
            else:
                items.append(it)
    return items

# ---------------------------------------------------------------- shared splitting helpers

def split_outside(s: str, sep: str) -> List[str]:
    """Split on sep outside (), [] and «»."""
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in '([«':
            depth += 1
        elif ch in ')]»' and depth:
            depth -= 1
        if ch == sep and depth == 0:
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append(''.join(cur))
    return [x.strip() for x in out]


TRAILING_CITATION = re.compile(r'(\[[^\[\]]*\](?:\s*و\s*\[[^\[\]]*\])*)\s*$')


def take_trailing_citation(s: str) -> Tuple[str, Optional[str]]:
    m = TRAILING_CITATION.search(s)
    if not m:
        return s, None
    inner = re.findall(r'\[([^\[\]]*)\]', m.group(1))
    if not inner or not all(is_bib_citation(x.strip()) or is_catalog_citation(x.strip()) for x in inner):
        return s, None
    return s[:m.start()].rstrip(' ؛،'), m.group(1).strip()

# ---------------------------------------------------------------- work header

LABEL_LINE = re.compile(r'^(?P<l>وابسته به|تاریخ تألیف|تاریخ تالیف|تألیف|تاریخ اجازه|اجازه|اهداء به|اهدا به|اهدایی به|'
                        r'به درخواست|به دستور|به فرمایش|به خواهش|به نام|چاپ|آغاز(?: کتاب| متن)?|انجام(?: کتاب| متن)?|شرح و حواشی|شروح و حواشی|مترجم|اسم مترجم|اصل از)\s*:\s*(?P<v>.*)$')
HETERO_LINE = re.compile(r'^(?P<q>ظاهراً|ظاهرا|بعضاً|بعضا|احتمالاً|احتمالا|گویا)?\s*غیر\s?همانند\s*:?\s*$')
HETERO_QUAL = {'بعضاً': 'partial', 'بعضا': 'partial'}
EPITHET_TAIL = re.compile(r'،\s*(?P<e>(?:امام|پیامبر|خلیفه)\s+\S+(?:\s+\S+)?)$')


def is_latin_line(s: str) -> bool:
    return bool(s) and len(LATIN.findall(s)) > len(PERSIAN.findall(s))


def parse_author(line: str, latin: Optional[str]) -> Dict[str, Any]:
    name_raw, date = extract_author_and_date(line)
    name, hedge = split_hedge(name_raw)
    if name and name.startswith('(؟)'):
        name, hedge = name[3:].strip(), (hedge or '؟')
    epithet = None
    if name:
        m = EPITHET_TAIL.search(name)
        if m:
            epithet, name = m.group('e'), name[:m.start()].strip()
    death = None
    if date:
        d_hedge = '؟' if re.search(r'[؟?]', date) else None
        cent, sort_y, _ = parse_date_triad(date)
        death = {'raw': date, 'hedge': d_hedge, 'century': cent, 'sort_year': sort_y}
    translit = latin
    if latin:
        translit = re.sub(r'\s*\([^)]*\)\s*$', '', latin).strip()
    return {'name': name, 'name_raw': name_raw, 'epithet': epithet, 'hedge': hedge,
            'transliteration': translit, 'death': death}


def parse_work_header(lines: List[Line], vol: int, ordinal: int) -> Dict[str, Any]:
    head = lines[0].text.lstrip('●').strip()
    titles, subject_raw, language_raw = parse_header_line(head)
    title, work_form = extract_title_form_and_clean(titles[0] if titles else head)
    languages, src_lang, tgt_lang, lang_unc = parse_languages(language_raw)
    w: Dict[str, Any] = {
        'key': {'vol': vol, 'ordinal': ordinal},
        'provenance': {'page_start': lines[0].page_start, 'page_end': lines[-1].page_end,
                       'line_start': lines[0].no, 'line_end': lines[-1].no},
        'title': title, 'title_line': titles[0] if titles else head, 'work_form': work_form,
        'alt_titles': titles[1:], 'subjects': parse_subjects(subject_raw), 'subject_raw': subject_raw,
        'languages': languages, 'language_raw': language_raw, 'source_language': src_lang,
        'target_language': tgt_lang, 'language_uncertain': lang_unc,
        'transliteration': None, 'alt_transliterations': [], 'author': None, 'author_unknown': False, 'translator': None,
        'original_author': None, 'heterogeneous': None, 'identification_uncertain': False,
        'composition': None, 'dedication': None, 'related_work': None, 'print_info': None,
        'description': None, 'incipit': None, 'explicit': None, 'commentaries': [], 'bibliography': [],
    }
    body = [l for l in lines[1:] if l.text]
    i = 0
    if i < len(body) and is_latin_line(body[i].text):
        parts = [p.strip() for p in body[i].text.split('=') if p.strip()]
        w['transliteration'], w['alt_transliterations'] = (parts[0] if parts else None), parts[1:]
        i += 1
    # author: a Persian line followed by a Latin line (dates optional), else v1's author-line test
    if i < len(body) and not LABEL_LINE.match(body[i].text) and not HETERO_LINE.match(body[i].text):
        cand = body[i].text
        nxt = body[i + 1].text if i + 1 < len(body) else None
        if nxt and is_latin_line(nxt) and len(cand) <= 150 and not cand.startswith('['):
            w['author'] = parse_author(cand, nxt)
            i += 2
        elif is_author_line(cand, nxt):
            w['author'] = parse_author(cand, None)
            i += 1
    desc: List[str] = []
    bib: List[str] = []
    comm_mode = False
    for l in body[i:]:
        t = l.text
        if re.match(r'^(?:مؤلف\s+|پدیدآور\s+)?(?:ناشناخته|ناشناس|نامعلوم)\s*:?$', t):
            w['author_unknown'] = True
            continue
        hm = HETERO_LINE.match(t)
        if hm:
            q = hm.group('q')
            w['heterogeneous'] = {'qualifier': HETERO_QUAL.get(q, 'doubtful') if q else None, 'hedge': q}
            continue
        if re.search(r'همانندی\s+(?:نامعلوم|غیر معلوم|نامشخص)', t) and len(t) < 40:
            w['identification_uncertain'] = True
            continue
        if comm_mode:
            item = re.sub(r'^\d+[\.\-]\s*', '', t)
            item, _ = take_trailing_citation(item)
            if item:
                w['commentaries'].append(item)
            continue
        if t.startswith('[') and t.endswith(']'):
            inner = t[1:-1].strip()
            if is_bib_citation(inner):
                bib += split_bib_citations(inner)
                continue
        m = LABEL_LINE.match(t)
        if m:
            lab, v = m.group('l').split()[0] if m.group('l').startswith(('آغاز', 'انجام')) else m.group('l'), m.group('v').strip()
            v, cit = take_trailing_citation(v)
            if cit:
                for x in re.findall(r'\[([^\[\]]*)\]', cit):
                    bib += split_bib_citations(x.strip())
            if lab in ('آغاز', 'انجام'):
                parts = IE_SPLIT.split(v)
                w['incipit' if lab == 'آغاز' else 'explicit'] = parts[0].strip()
                for part in parts[1:]:
                    pm = IE_START.match(part)
                    if pm and pm.group('l').startswith('انجام') and not w['explicit']:
                        w['explicit'] = part[pm.end():].strip()
            elif lab == 'وابسته به':
                w['related_work'] = v
            elif lab in ('تاریخ تألیف', 'تاریخ تالیف', 'تألیف', 'تاریخ اجازه', 'اجازه'):
                pm = re.search(r'[؛،]\s*(?:محل\s*:?\s*تألیف|محل تألیف|محل تالیف|محل صدور|محل نگارش)\s*:?\s*(.+)$', v)
                w['composition'] = {'date': (v[:pm.start()] if pm else v).strip(' ؛،'),
                                    'place': pm.group(1).strip() if pm else None}
            elif lab in ('اهداء به', 'اهدا به', 'اهدایی به', 'به درخواست', 'به دستور', 'به فرمایش', 'به خواهش', 'به نام'):
                w['dedication'] = v
            elif lab == 'چاپ':
                w['print_info'] = v
            elif lab in ('مترجم', 'اسم مترجم'):
                w['translator'] = parse_author(v, None)
            elif lab == 'اصل از':
                w['original_author'] = parse_author(v, None)
            elif lab in ('شرح و حواشی', 'شروح و حواشی'):
                comm_mode = True
                if v:
                    w['commentaries'].append(v)
            continue
        if not desc and not w['author'] and is_latin_line(t):
            continue
        desc.append(t)
    if desc:
        text = '\n'.join(desc)
        text, cit = take_trailing_citation(text)
        if cit:
            for x in re.findall(r'\[([^\[\]]*)\]', cit):
                bib += split_bib_citations(x.strip())
        w['description'] = text or None
    w['bibliography'] = bib
    return w

# ---------------------------------------------------------------- copies

COPY_HEAD = re.compile(r'^(?:(?P<seq>\d+)\s*[\.\-]\s*)?(?P<loc>.+?)\s*؛\s*شماره\s*نسخه\s*:\s*(?P<shelf>.*)$')
IE_START = re.compile(r'^(?P<l>(?:آغاز|انجام)[^:؛]{0,25}?)\s*:\s*')
IE_SPLIT = re.compile(r'\s*؛\s*(?=(?:آغاز|انجام)[^:؛]{0,25}?:)')
# an explicit label after the incipit with no «؛», as printed («آغاز: برابر انجام: …», «برابرانجام:»)
BARE_EXPLICIT = re.compile(r'(?:\s*،?\s+|(?<=برابر)|(?<=برابر\d))(?=انجام(?:\s+(?:نسخه|کتاب|متن))?\s*:)')
PHYS_LABEL = (r'(?:خط\s*:|کا\s*:|بی[‌ ]?کا\b|تا\s*:|بی[‌ ]?تا\b|کاغذ\s*:|جلد\s*:|اندازه\s*:|افتادگی\s*:|'
              r'جا\s*:|\d+\s*گ\b|\d+\s*برگ\b|\d+\s*ص\s*\(|کاتب\s*=)')
PHYS_GROUP_START = re.compile(r'(?:^|؛\s*)(?=' + PHYS_LABEL + r')')
ORIG_RE = re.compile(r'^(?:نسخه\s+اصل[یی]?|اصل\s+نسخه)\s*:\s*(?P<v>.*)$')
SCOPE_RE = re.compile(r'^(?:جلد|ج\s*\d|مجلد|دفتر|کتاب|باب|فصل|مقاله|مقالت|جزء|جزو|بخش|قسمت|فن|مقصد|مطلب|مجلس|'
                      r'از\s+(?:باب|فصل|کتاب|جلد|ابتدا|آغاز|اول|اواسط|اواخر|برگ|مقاله|جزء|جزو|بخش|\S+\s+تا\s)|تا\s+|شامل\s*:|(?:شامل|دارای|مشتمل\s+بر)\s+(?:ابواب|باب|کتب|کتاب|جلد|مجلد|فصول|بخش|مقالات)|فقط|نیمه|نیمی|حدود\s+(?:یک|دو|سه|نیمی)|مقدمه|خاتمه|دیباچه|'
                      r'تمام|کامل|ناقص|طهارت|صلاة|صلات)'
                      r'|را\s+دارد|را\s+ندارد|آمده\s+است\s*$|کتاب\s+\S+\s+تا|،\s*تا\s+\S')
SCOPE_NOT = re.compile(r'^(?:از\s+روی|از\s+نسخه|کتابی|کتاب\s+در\s|تذکر|نام\s+مؤلف)')
AUTOGRAPH_RE = re.compile(r'^(?:کاتب\s*=\s*)?(?:مؤلف|مولف|مصنف|ناظم|شارح|مترجم|جامع)(?:\s|$|\()')
FLAG_WORDS = {'مصحح': 'corrected', 'تصحیح شده': 'corrected', 'محشی': 'marginal_notes', 'مذهب': 'illuminated',
              'مجدول': 'ruled', 'مصور': 'illustrated', 'مقابله شده': 'collated', 'عکسی': 'facsimile',
              'رکابه دار': 'catchwords', 'با رکابه': 'catchwords'}
# v1's flag rules (scripts/fankha_parser.py), which v2 had narrowed: the phase 3 comparison found 21k flags
# v1 set correctly and v2 did not. «مجدول» in the binding describes the binding, not ruled leaves; a gilt binding
# («جلد: تیماج مذهب») does count as «مذهب» (gold set), and «در حاشیه آمده» is not a glossed copy.
FLAG_RULES = [
    ('corrected', re.compile(r'مصحح|تصحیح\s+شده|تصحیح\s+دارد|تصحیح\s+و\s+مقابله')),
    ('marginal_notes', re.compile(r'محشی|حاشیه\s+دارد|(?:با|دارای)\s+حواشی|حواشی\s+(?:مختصر|فراوان|بسیار)')),
    ('ruled', re.compile(r'مجدول|(?:دارای\s+|با\s+)?کمند(?:[‌\s]کشی)?|جدول[‌\s]کشی|با\s+جدول|جدول\s+[^\s؛،]+\s+خطی')),
    ('catchwords', re.compile(r'رکابه[‌\s]?دار|با\s+رکابه|دارای\s+رکابه')),
    ('collated', re.compile(r'مقابله\s+(?:شده|گردیده|نموده|کردم)|تصحیح\s+و\s+مقابله|مقابل\s+کرده|(?:با|دارای)\s+(?:علامت|نشان(?:ی)?|امضای|امضا)?\s*(?:بلاغ|بلغ)|'
                            r'با\s+(?:نشان|عبارت)\s*«بلغ|(?:سه\s+بار|دو\s+مرتبه)\s+مقابله')),
    ('illuminated', re.compile(r'(?:(?:سرلوح|کتیبه|شمسه)\s+)?(?:مذهب|مرصع|زرین)(?!\s+(?:شیعه|حنفی|شافعی|مالکی|امامیه|جعفری|اهل\s+سنت))|'
                               r'تذهیب|طلاپوش|زرنگار|زرافشان|اکلیل|سر[‌\s]?لوح|طلااندازی|طلا\s+اندازی')),
    ('illustrated', re.compile(r'مصور|دارای\s+(?:تصاویر|عکس‌های\s+فتوگرافیک|نقاشی|نگاره)|با\s+(?:اشکال\s+هندسی|تصاویر)|مجلس\s+تصویر')),
    ('author_marginalia', re.compile(r'محشی\s+با\s+(?:نشان|علامت|رمز|امضاء|امضای)\s*«?منه|محشی\s+(?:از|به\s+خط)\s+(?:مؤلف|مولف)|'
                                     r'حاشیه(?:[‌\s]+های[ی‌]?)?\s+از\s+(?:مؤلف|مولف)|منه\s+(?:سلمه\s+الله|مد\s*ظله|دام\s*ظله|عفی\s+عنه|رحمه\s+الله|'
                                     r'قدس\s+سره|ایده\s+الله|حفظه\s+الله|دام\s+علوه|مد\s+عزه)|محشی\s+با\s+(?:نشان|رمز)[^؛]{0,40}«منه')),
]
BINDING_TEXT = re.compile(r'جلد\s*:[^؛\[]*')
COMMISSION_RE = re.compile(r'^(?:جهت|به\s+دستور|حسب\s*الامر|حسب‌الامر|به\s+امر|به\s+فرمایش|به\s+خواهش|به\s+درخواست|برای)\s+(?P<v>.+)$')
PORTION_RE = re.compile(r'^(?P<n>.*?)\s*\((?P<p>[^()]*(?:ورق|برگ|صفحه|جلد|بخش|دفتر|جزء|جزو)[^()]*)\)$')
SIMPLE_LABELS = [('paper', r'کاغذ'), ('binding', r'جلد'), ('dimensions', r'اندازه'),
                 ('text_dimensions', r'(?:ابعاد|اندازه)\s*متن'), ('defects', r'افتادگی'), ('format', r'قطع'),
                 ('donor', r'(?:واقف|وقف|تاریخ\s+وقف)'), ('ownership', r'(?:تملک|تملکات)'), ('seals', r'(?:مهر|مهرها)')]
LIST_FIELDS = ('ownership', 'seals', 'acquisition')
ACQ_RE = re.compile(r'^(?P<k>اهدایی|اهدائی|خریداری|انتقالی|واگذاری|امانی)(?:\s+از)?\s*:?\s*(?P<v>.*)$')
DATE_FRAG = re.compile(r'^(?:\d{1,2}\s+)?(?:فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند|محرم|صفر|'
                       r'ربیع\S*|جمادی\S*|رجب|شعبان|رمضان|شوال|ذی\S*|ذو\S*)(?:\s+\S+)?(?:\s+\d{3,4})?\s*[قشم]?$'
                       r'|^(?:به\s+تاریخ\s+)?\d{3,4}\s*[قشم]?$|^\d{4}/\d{1,2}/\d{1,2}$')
SIMPLE_RE = [(f, re.compile(r'^' + p + r'\s*:\s*(?P<v>.*)$')) for f, p in SIMPLE_LABELS]


def new_copy() -> Dict[str, Any]:
    return {'key': {'seq': None, 'ordinal': None}, 'provenance': None, 'city': None, 'library': None,
            'shelfmark': None, 'incipit': None, 'explicit': None, 'extra_incipits': [], 'contents_scope': None,
            'copy_description': None, 'notes': [], 'script_raw': None, 'scripts': [], 'scribes': [],
            'is_autograph': False, 'autograph_hedge': None, 'no_scribe': False, 'copy_date': None,
            'undated': False, 'copy_place': None, 'commissioned_by': None, 'folios': None, 'lines': None,
            'lines_note': None, 'text_dimensions': None, 'dimensions': None, 'paper': None, 'binding': None,
            'defects': None, 'format': None, 'donor': None, 'ownership': [], 'seals': [], 'acquisition': [],
            'flags': [], 'original_copy': None,
            'other_listings': [], 'catalog_citation': None, 'unparsed': [], 'raw_text': None}


def add_flag(c, f):
    if f not in c['flags']:
        c['flags'].append(f)


def flag_chunk(c, chunk) -> bool:
    """Chunks that are only flag words («مصحح»، «مذهب و مجدول») set flags and are consumed."""
    words = [w for w in re.split(r'\s*(?:،|\s+و\s+)\s*', chunk) if w]
    hits = [FLAG_WORDS.get(w) for w in words]
    if words and all(hits):
        for h in hits:
            add_flag(c, h)
        return True
    for k, f in FLAG_WORDS.items():
        if re.search(r'(?:^|\s)' + k + r'(?:\s|$|،)', chunk):
            add_flag(c, f)
    return False


def parse_ie_line(c, text: str, tag_at: Optional[int] = None) -> Optional[str]:
    """Parse an incipit/explicit line. Returns the physical tail if one is glued on the same line.

    When a page tag stood between the explicit and that tail, the text after the tag is a lost line of
    its own (copy description or note), not part of the explicit."""
    tail = None
    m = re.search(r'\s*؛?\s*(?=(?:خط\s*:\s*[^،؛]+[،؛]\s*(?:کا\s*:|کاتب\s*=|بی[‌ ]?کا|بی[‌ ]?تا|تا\s*:)|'
                  r'کا\s*:\s*[^،؛:]{2,80}،\s*(?:تا\s*:|بی[‌ ]?تا)|'
                  r'بی[‌ ]?کا\s*،\s*(?:تا|بی)))', text)
    if m and m.start() > 0:
        text, tail = text[:m.start()], text[m.end():]
        if tag_at and 0 < tag_at < len(text) and not IE_SPLIT.search(text[tag_at:]):
            text, tail = text[:tag_at], text[tag_at:].strip() + '؛ ' + tail
    parts = []
    for part in IE_SPLIT.split(text):
        if re.match(r'^آغاز(?:\s+(?:نسخه|کتاب|متن))?\s*:', part):
            parts += BARE_EXPLICIT.split(part, maxsplit=1)
        else:
            parts.append(part)
    for part in parts:
        pm = IE_START.match(part)
        if not pm:
            continue
        lab, val = ' '.join(pm.group('l').split()), part[pm.end():].strip()
        sm = re.match(r'^برابر\s*(\d)?$', val)
        same = bool(sm)
        rec = {'text': None if same else val, 'same_as_work': same}
        if sm and sm.group(1):
            rec['same_as_work_n'] = int(sm.group(1))     # «برابر2»: the work's second incipit/explicit
        if lab in ('آغاز', 'آغاز نسخه'):
            if c['incipit'] is None:
                c['incipit'] = rec
            else:
                c['extra_incipits'].append({'label': lab, **rec})
        elif lab in ('انجام', 'انجام نسخه'):
            if c['explicit'] is None:
                c['explicit'] = rec
            else:
                c['extra_incipits'].append({'label': lab, **rec})
        elif lab == 'آغاز و انجام':
            c['incipit'] = c['incipit'] or dict(rec)
            c['explicit'] = c['explicit'] or dict(rec)
        else:
            c['extra_incipits'].append({'label': lab, **rec})
            if lab.startswith('آغاز') and c['incipit'] is None:
                c['incipit'] = {'text': val, 'same_as_work': same}
    return tail


def fa(s: str) -> str:
    """Persian letter forms, for matching only (values keep the printed form)."""
    return s.replace('ك', 'ک').replace('ي', 'ی').replace('ى', 'ی')


def classify_leading(c, seg: str, hetero: bool):
    for part in [p for p in split_outside(seg, '؛') if p]:
        om = ORIG_RE.match(part)
        if om:
            set_original(c, om.group('v'))
        elif part.startswith('همان نسخه') and not c['notes'] and len(part) < 30:
            c['notes'].append({'type': 'same_as_previous', 'text': part, 'hedge': None})
        elif SCOPE_RE.search(fa(part)) and not SCOPE_NOT.match(fa(part)) and c['contents_scope'] is None:
            head, sep, rest = part.partition('، ')
            if sep and re.search(r'(?:^|\s)(?:که|است|می‌|نمی‌)', rest) and not re.match(r'^\d+\.', rest) \
                    and not SCOPE_RE.search(rest):
                c['contents_scope'] = head
                c['notes'].append({'type': 'remark', 'text': rest, 'hedge': None})
            else:
                c['contents_scope'] = part
        elif hetero and c['copy_description'] is None:
            c['copy_description'] = part
        elif not flag_chunk(c, part):
            v, h = split_hedge(part)
            c['notes'].append({'type': 'remark', 'text': part, 'hedge': h})


def set_original(c, v: str):
    v = v.strip()
    if v.startswith('همان نسخه'):
        c['original_copy'] = {'kind': 'previous', 'raw': v, 'previous_seq': None}
    else:
        c['original_copy'] = {'kind': 'external', 'raw': v, 'previous_seq': None}
    add_flag(c, 'facsimile')          # in Fankha «نسخه اصل:» is how a photo copy names its original (ruling 8)


def parse_scribe(c, v: str):
    v = v.strip()
    name, hedge = split_hedge(v)
    if name and AUTOGRAPH_RE.match(name):
        c['is_autograph'], c['autograph_hedge'] = True, hedge
        return
    if not name:
        return
    portion = None
    pm = PORTION_RE.match(name)
    if pm:
        name, portion = pm.group('n').strip(), pm.group('p').strip()
    c['scribes'].append({'name': name, 'hedge': hedge, 'portion': portion})


NOTE_VERB = re.compile(r'(?:^|\s)(?:است|شده|دارد|کرده|نوشته|آمده|می[‌ ]?\S+|که|را)(?:\s|$)')


def is_fragment(ch: str) -> bool:
    """A date, a name, a seal legend or a seal shape continuing the provenance field before it."""
    if DATE_FRAG.match(ch) or re.match(r'^«[^»]+»(?:\s*\([^)]*\))?$', ch) or re.match(r'^\((?:مربع|بیضی|دایره|مستطیل|\S+)\)$', ch):
        return True
    return len(ch.split()) <= 7 and ':' not in ch and not NOTE_VERB.search(ch) and not re.search(r'\d{3,4}\s*گ', ch)


def parse_physical(c, text: str):
    last = None                      # the field an unlabelled chunk may continue
    for gi, group in enumerate(split_outside(text, '؛')):
        last = None
        for chunk in split_outside(group, '،'):
            if not chunk:
                continue
            ch = chunk.strip(' .')
            if re.match(r'^(?:كا|بى|تاريخ)', ch):          # labels printed with Arabic letter forms
                ch = fa(ch[:6]) + ch[6:]
            m = re.match(r'^خط\s*:\s*(?P<v>.*)$', ch)
            if m:
                c['script_raw'] = m.group('v').strip()
                c['scripts'] = parse_scripts(c['script_raw'])
                last = 'script'
                continue
            m = re.match(r'^کا\s*:\s*(?P<v>.*)$', ch) or re.match(r'^(?P<v>کاتب\s*=\s*.*)$', ch)
            if m:
                parse_scribe(c, m.group('v'))
                last = 'scribe'
                continue
            if re.match(r'^بی[‌ ]?کا$', ch):
                c['no_scribe'], last = True, 'bika'
                continue
            m = re.match(r'^تا\s*:\s*(?P<v>.*)$', ch)
            if m:
                v, h = split_hedge(m.group('v'))
                cent, sort_y, _ = parse_date_triad(v)
                c['copy_date'] = {'raw': v, 'hedge': h, 'century': cent, 'sort_year': sort_y}
                last = 'date'
                continue
            m = re.match(r'^بی[‌ ]?تا\s*(?:\((?P<g>[^)]*)\))?$', ch)
            if m:
                c['undated'], last = True, 'bita'
                if m.group('g'):
                    c['notes'].append({'type': 'date_guess', 'text': m.group('g'), 'hedge': None})
                continue
            m = re.match(r'^جا\s*:\s*(?P<v>.*)$', ch)
            if m:
                v, h = split_hedge(m.group('v'))
                c['copy_place'] = {'v': v, 'hedge': h}
                last = 'place'
                continue
            m = re.match(r'^(?P<v>\d[\d/]*\s*(?:گ|برگ|ص)(?=\s|\(|$).*)$', ch)
            if m:
                c['folios'], last = m.group('v'), 'folios'
                continue
            if last == 'folios' and re.match(r'^\([^()]*\d[^()]*\)$', ch):
                c['folios'] += ' ' + ch
                continue
            m = re.match(r'^(?P<n>\d+(?:\s*(?:[-–]|و)\s*\d+)*\s*سطر)\s*(?:\((?P<d>[^)]*)\))?\s*(?P<r>.*)$', ch)
            if m:
                c['lines'] = m.group('n')
                if m.group('d'):
                    c['text_dimensions'] = m.group('d')
                r = m.group('r').strip()
                dm = re.search(r'\s*\(([\d/\s×x*]+)\)$', r)
                if dm and not c['text_dimensions']:
                    c['text_dimensions'], r = dm.group(1).strip(), r[:dm.start()].strip()
                if r.strip(' سطر'):
                    c['lines_note'] = r
                last = None
                continue
            if re.search(r'سطور\s+چلیپا|چلیپایی|مختلف\s*السطر|مختلف\s*السطور', ch):
                dm = re.search(r'\s*\(([\d/\s×x*]+)\)$', ch)
                if dm:
                    c['text_dimensions'], ch = c['text_dimensions'] or dm.group(1).strip(), ch[:dm.start()].strip()
                c['lines_note'], last = ch, None
                continue
            hit = False
            for f, rx in SIMPLE_RE:
                m = rx.match(ch)
                if m:
                    if f in LIST_FIELDS:
                        c[f].append(m.group('v').strip())
                    else:
                        c[f] = m.group('v').strip()
                    last, hit = f, True
                    break
            if hit:
                continue
            m = ACQ_RE.match(ch)
            if m:
                c['acquisition'].append(ch)
                last = 'acquisition'
                continue
            m = COMMISSION_RE.match(ch)
            if m and last in ('place', 'date', 'scribe'):
                c['commissioned_by'], last = m.group('v').strip(), None
                continue
            # «جلد: تیماج سرخ، مجدول، ترنج و سرترنج»: an unlabelled chunk after the binding describes the binding
            # (a flag word there is the binding's, not the leaves')
            if last == 'binding' and not re.search(r'[:\d]', ch) and len(ch.split()) <= 8:
                c['binding'] += '، ' + ch
                continue
            if flag_chunk(c, ch):
                continue
            # unlabelled chunk: continuation of the previous field, or a note
            v, h = split_hedge(ch)
            if last == 'scribe' and c['scribes'] and not re.search(r'[\d:]', ch) and not h and (
                    len(ch.split()) <= 4 or ('،' not in c['scribes'][-1]['name'] and len(ch.split()) <= 7)):
                c['scribes'][-1]['name'] += '، ' + ch
                continue
            if last == 'script' and parse_scripts(ch) and all(s['type'] for s in parse_scripts(ch)) \
                    and len(ch.split()) <= 3:
                c['script_raw'] += '، ' + ch
                c['scripts'] = parse_scripts(c['script_raw'])
                continue
            if last in ('bika', 'bita') and h:
                c['notes'].append({'type': 'scribe_guess' if last == 'bika' else 'date_guess', 'text': v, 'hedge': h})
                continue
            if last in ('paper', 'binding') and not re.search(r':', ch) and len(ch.split()) <= 4:
                c[last] += '، ' + ch
                continue
            if last == 'folios' and re.match(r'^\d+\s*[-–]\s*\d+$', ch):
                c['folios'] += ' (' + ch + ')'
                continue
            if last == 'place' and c['copy_place'] and len(ch.split()) <= 5 and not re.search(r'[\d:]', ch):
                c['copy_place']['v'] += '، ' + ch
                continue
            if re.match(r'^کاغذ\s+\S', ch) and not c['paper']:
                c['paper'], last = ch[4:].strip(), 'paper'
                continue
            if re.match(r'^جلد\s+(?!\d)\S', ch) and not c['binding']:
                c['binding'], last = ch[3:].strip(), 'binding'
                continue
            if last in ('ownership', 'donor') and (re.match(r'^(?:با\s+مهر|با\s+تولیت|\d{3,4}\s)', ch)
                                                    or re.match(r'^\S+(?:\s+\S+)?\s+بن\s', ch)):
                if last == 'donor':
                    c['donor'] += '، ' + ch
                else:
                    c['ownership'][-1] += '، ' + ch
                continue
            if last in LIST_FIELDS + ('donor',) and is_fragment(ch):
                if last == 'donor':
                    c['donor'] += '، ' + ch
                elif c[last]:
                    c[last][-1] += '، ' + ch
                continue
            c['notes'].append({'type': 'remark', 'text': ch, 'hedge': h})
            last = None


def parse_copy(lines: List[Line], ordinal: int, hetero: bool) -> Dict[str, Any]:
    c = new_copy()
    c['key']['ordinal'] = ordinal
    c['provenance'] = {'page_start': lines[0].page_start, 'page_end': lines[-1].page_end,
                       'line_start': lines[0].no, 'line_end': lines[-1].no}
    c['raw_text'] = '\n'.join(l.text for l in lines if l.text)
    content = [l for l in lines if l.text]
    hm = COPY_HEAD.match(content[0].text)
    if hm:
        if hm.group('seq'):
            c['key']['seq'] = int(hm.group('seq'))
        loc = [p.strip() for p in hm.group('loc').split('؛')]
        c['city'], c['library'] = loc[0], '؛ '.join(loc[1:]) or None
        c['shelfmark'] = hm.group('shelf').strip() or None
    rest = content[1:]
    if rest:                                      # the closing bracket(s) are the catalogue citation
        last_text, cit = take_trailing_citation(rest[-1].text)
        if cit:
            c['catalog_citation'] = cit
            rest[-1] = Line(rest[-1].no, last_text, rest[-1].page_start, rest[-1].page_end, rest[-1].tag_at)
    merged: List[Line] = []
    for l in rest:
        if not l.text:
            continue
        if merged and re.match(r'^(?:آغاز|انجام)[^:؛]{0,25}:\s*$', merged[-1].text) and not IE_START.match(l.text):
            p = merged[-1]
            merged[-1] = Line(p.no, p.text + ' ' + l.text, p.page_start, l.page_end, None)
            continue
        merged.append(l)
    rest = merged
    for l in rest:
        t = l.text
        if not t:
            continue
        if IE_START.match(t):
            tail = parse_ie_line(c, t, l.tag_at)
            if tail:
                parse_line_body(c, tail, hetero, None)
            continue
        parse_line_body(c, t, hetero, l.tag_at)
    body = ' '.join(l.text for l in rest if l.text and not IE_START.match(l.text))
    leaves = BINDING_TEXT.sub(' ', body)
    for f, rx in FLAG_RULES:
        if rx.search(leaves if f == 'ruled' else body):
            add_flag(c, f)
    if 'author_marginalia' in c['flags']:
        add_flag(c, 'marginal_notes')
    if c['shelfmark'] and 'عکسی' in c['shelfmark']:
        add_flag(c, 'facsimile')
    kept = []
    for n in c['notes']:
        if n['type'] == 'remark':
            t = fa(n['text'])
            am = ACQ_RE.match(t)
            if am:
                c['acquisition'].append(n['text'])
                continue
            hit = False
            for f, rx in SIMPLE_RE:
                m = rx.match(t)
                if m and f in LIST_FIELDS + ('donor',):
                    if f == 'donor':
                        c['donor'] = (c['donor'] + '، ' if c['donor'] else '') + n['text']
                    else:
                        c[f].append(m.group('v').strip())
                    hit = True
                    break
            if hit:
                continue
            n.update(classify_note(n['text']))
        kept.append(n)
    c['notes'] = kept
    if any(n.get('by_author') and n['type'] == 'marginalia' or n.get('by_author') and 'marginalia' in n.get('also', [])
           for n in c['notes']):
        add_flag(c, 'author_marginalia')
    if c['scribes'] or c['is_autograph']:
        c['no_scribe'] = c['no_scribe'] and not c['scribes']
    return c


def parse_line_body(c, t: str, hetero: bool, tag_at: Optional[int]):
    m = None
    for gm in PHYS_GROUP_START.finditer(t):
        m = gm
        break
    if m is None:
        om = ORIG_RE.match(t)
        if om:
            set_original(c, om.group('v'))
        else:
            classify_leading(c, t, hetero)
        return
    lead, phys = t[:m.start()].strip(' ؛'), t[m.end():]
    if lead:
        classify_leading(c, lead, hetero)
    parse_physical(c, phys)

# ---------------------------------------------------------------- note types (user's approval, 6 Aban 1405; plan section 10)

NOTE_RULES = [   # order = precedence of the main type; every other matching type goes to `also`
    ('contents', r'^\d+\s*[\.\-)]\s'),   # an item of a numbered list of texts in a collection
    ('cataloguer', r'^(?:در\s+فهرست|تذکر|مکرر|ضمیمه|ر\.\s*ک|نک\.|نیز\s+ن)|^\(\d+\)$|به\s+خطا|دانسته\s+شده'),
    ('acquisition', r'^(?:اهدایی|اهدائی|خریداری|انتقالی|واگذاری|امانی)|به\s+کتابخانه\s+\S+\s+(?:اهدا|واگذار)|به\s+کتابخانه(?:\s+\S+){0,3}\s+(?:رسید|آمد|داده)'),
    ('endowment', r'وقف|واقف|موقوف'),
    ('certificate', r'اجازه|سماع|قرائت|انهاء|انهای|بلاغ|بلغ\s'),
    ('ownership', r'تملک|از\s+آن\s+\S+(?:\s+\S+){0,2}\s+بوده|ملکیت|تملّک|مالک|در\s+نزد|اهدای\s+کتاب|اهدا\s+به|هدیه|ابتیاع|انتقال\s+به\s+ملک'),
    ('seal', r'مهر\s|مهری|مهرها|^مهر|سجع|«عبده|«الراجی|نقش\s+مهر|^«[^»]+»\s*\((?:مربع|بیضی|بیضوی|دایره|مدور|مستطیل|کتابی|لوزی)\)$'),
    ('collation', r'مقابله|تصحیح|مصحح|نسخه[‌ ]?بدل|«خ\s*ل»|کاستی|افتاده‌ها|بدل\s'),
    ('marginalia', r'حاشیه|حواشی|محشی|هامش|تعلیقه|تعلیقات|حاشیه‌نویسی'),
    ('transcription', r'مسوده|مسودّه|مبیضه|منشی|به\s+خط\s+(?!مؤلف)|از\s+روی|نقل\s+از|منقول\s+از|استنساخ|کاتب|کتابت|به\s+خواهش|به\s+جهت|به\s+دستور|نگارش\s+یافته|به\s+دست\s+چند'),
    ('diagram', r'اشکال|جداول|دایره|دوایر|نقشه|تشریح|هندسی|نجومی|زایچه|شکل\s|اسطرلاب'),
    ('illustration', r'نگاره|نقاشی|مصور|تصویر|تصاویر|مینیاتور|مجلس\s+(?:تصویر|نقاشی)|صورت\s+\S+\s+کشیده'),
    ('decoration', r'عناوین|سرنج|سرخی|شنگرفی|پیشانی|مذهب|سرلوح|کمند|ترنج|شنگرف|لاجورد|زرین|طلا|زر\s|زر$|کتیبه|مرصع|افشان|گل\s+و\s+بوته|مجدول|جدول|حل[‌ ]?کاری|تشعیر|شمسه'),
    ('codicology', r'قلم\s*خوردگی|خط\s*خوردگی|صفحه\s*شمار|شماره\s*گذاری|رکابه|عطف|لبه|صحافی|صحاف|آب[‌ ]?دیدگی|موریانه|وصالی|رطوبت|پارگی|کرم[‌ ]?خوردگی|آشفته|جابجا|نونویس|'
                   r'ستون|سطور|مورب|کیفیت\s+تصویر|بیاض|سفینه|کاغذ|اوراق|برگ‌ها|ورق‌ها|بی[‌ ]?نقطه|نقطه'),
    ('annex', r'(?:^|\s)(?:در|پشت|بر|روی)\s+(?:پایان|آخر|آغاز|ابتدا|اول|انتها|پشت|برگ|صفحه|جلد)|فوائد|فائده|فایده|یادداشت|'
              r'اضافه\s+دارد|افزوده|نوشته‌ای|صورت\s+(?:اجازه|وقفنامه|نامه)|سپس|همراه\s+است'),
    ('cataloguer', r'فهرست|تذکر|نام\s+(?:مؤلف|کتاب|کاتب)|به\s+قرینه|به\s+استناد|تعیین\s+شد|شناخته\s+نشد|ناشناخته|مجلدات|'
                   r'شماره\s+\d|غیر\s+از\s+رساله|با\s+نسخه\s+\S+\s+(?:یکی|مقایسه)'),
    ('contents', r'^کتب\s|^از\s.+\sتا\s|تا\s*(?:کتاب|پایان|آخر)|حدیث|تفسیر|قواعد|نامه|مطالب|^فی\s|پاسخ|شامل|مشتمل|دارای|اشعار|شعر|شاعر|قصیده|قصاید|غزل|مثنوی|رباعی|مراثی|مدایح|جنگ|منتخب|ترجمه|بیت|باب|فصل|'
                 r'رساله|در\s+(?:بیان|ذکر|شرح|فضیلت|احوال)|درباره|مقدمه'),
]
NOTE_RULES = [(t, re.compile(p)) for t, p in NOTE_RULES]
BY_AUTHOR = re.compile(r'(?:به\s+خط|از|توسط|خود|دست)\s+(?:خود\s+)?(?:مؤلف|مصنف|ناظم|شارح)|(?:حواشی|تصحیح|مقابله|اجازه|تعلیقات|'
                       r'تعلیقه|یادداشت)(?:\s+و\s+\S+)?\s+(?:از\s+)?(?:مؤلف|مصنف|ناظم|شارح)|شده[‌ ]?ی?\s+(?:مؤلف|مصنف)|(?:مؤلف|مصنف)$')
SEAL_SHAPE = re.compile(r'\((مربع|بیضی|بیضوی|دایره|دایره‌ای|مدور|گرد|مستطیل|کتابی|لوزی|هشت\s*ضلعی|شش\s*ضلعی|چهارگوش)\)|'
                        r'(?:مهر\s+)?(مربع|بیضی|بیضوی|مدور|مستطیل|کتابی|لوزی|هشت\s*ضلعی)(?:\s|$)')
HEDGE_ANY = re.compile(r'(?:^|\s)(گویا|ظاهراً|ظاهرا|احتمالاً|احتمالا|شاید|محتملاً)(?:\s|$)')


def classify_note(text: str) -> Dict[str, Any]:
    t = fa(text)
    hits = [typ for typ, rx in NOTE_RULES if rx.search(t)]
    if 'seal' in hits and re.search(r'^مهر\s+صحاف|مهر\s+صحاف', t):
        hits = ['seal'] + [h for h in hits if h != 'seal'] + ['codicology']        # binder's seal (ruling, 6 Aban)
    if re.search(r'زر|طلا|لاجورد|سرخ|تحریر|منقش|گل\s|نقاشی|زمینه|الوان|تذهیب', t):
        for h in ('diagram', 'marginalia'):
            if h in hits and 'decoration' in hits and hits.index(h) < hits.index('decoration'):
                hits.remove(h)
                hits.insert(hits.index('decoration') + 1, h)
    if 'illustration' in hits and 'diagram' in hits:
        hits.remove('illustration')            # scientific figures (anatomy, astronomy) are diagrams
    if 'certificate' in hits and re.search(r'صورت\s+اجازه|متن\s+اجازه', t):
        hits.remove('certificate')
        hits = ['annex'] + [h for h in hits if h != 'annex'] + ['certificate']   # an ijaza copied as a text
    main = hits[0] if hits else 'other'
    also = [h for h in dict.fromkeys(hits[1:]) if h != main]
    out: Dict[str, Any] = {'type': main, 'also': also, 'by_author': False, 'by_author_hedge': None,
                           'seal': None, 'hedge': None}
    hm = HEDGE_ANY.search(t)
    if hm:
        out['hedge'] = hm.group(1)
    if BY_AUTHOR.search(t) and (main in ('marginalia', 'collation', 'certificate', 'annex', 'transcription')
                                or set(also) & {'marginalia', 'collation', 'certificate'}):
        out['by_author'] = True
        out['by_author_hedge'] = out['hedge']
    if main == 'seal' or 'seal' in also:
        lm = re.search(r'«([^»]+)»', text)
        sm = SEAL_SHAPE.search(t)
        out['seal'] = {'legend': lm.group(1) if lm else None,
                       'shape': (sm.group(1) or sm.group(2)) if sm else None}
    return out


# ---------------------------------------------------------------- volume

def split_entries(lines: List[Line]) -> List[Tuple[str, List[Line]]]:
    entries: List[Tuple[str, List[Line]]] = []
    cur: List[Line] = []
    kind = None
    for l in lines:
        t = l.text
        is_work = t.startswith('●')
        is_ref = ('←' in t and not is_work and not t.startswith(('آغاز', 'انجام'))
                  and 'شماره نسخه' not in t and len(t) < 200)
        if is_work or is_ref:
            if cur and kind:
                entries.append((kind, cur))
            cur, kind = [l], ('work' if is_work else 'ref')
            if is_ref:
                entries.append((kind, cur))
                cur, kind = [], None
            continue
        if kind:
            cur.append(l)
    if cur and kind:
        entries.append((kind, cur))
    return entries


def parse_work(lines: List[Line], vol: int, ordinal: int) -> Dict[str, Any]:
    first_copy = next((i for i, l in enumerate(lines) if 'شماره نسخه' in l.text and i > 0), len(lines))
    w = parse_work_header(lines[:first_copy], vol, ordinal)
    hetero = w['heterogeneous'] is not None
    blocks: List[List[Line]] = []
    for l in lines[first_copy:]:
        if 'شماره نسخه' in l.text and COPY_HEAD.match(l.text):
            blocks.append([l])
        elif blocks:
            blocks[-1].append(l)
    copies: List[Dict[str, Any]] = []
    for b in blocks:
        c = parse_copy(b, len(copies) + 1, hetero)
        body = c['raw_text'].split('\n', 1)[1] if '\n' in c['raw_text'] else ''
        body_wo_cit, _ = take_trailing_citation(body)
        if copies and re.fullmatch(r'همان\s+نسخه(?:\s+بالا)?', body_wo_cit.strip(' .')):
            # same physical copy listed again from another catalogue: merge (ruling of section 7)
            copies[-1]['other_listings'].append({'city': c['city'], 'library': c['library'],
                                                 'shelfmark': c['shelfmark'],
                                                 'catalog_citation': c['catalog_citation'],
                                                 'line': c['provenance']['line_start']})
            continue
        if c['original_copy'] and c['original_copy']['kind'] == 'previous' and copies:
            c['original_copy']['previous_seq'] = copies[-1]['key']['seq'] or copies[-1]['key']['ordinal']
        c['key']['ordinal'] = len(copies) + 1
        copies.append(c)
    if w['provenance']:
        w['provenance']['line_end'] = lines[-1].no
        w['provenance']['page_end'] = lines[-1].page_end
    w['copies'] = copies
    return w


def parse_volume(vol: int, text: str) -> Dict[str, Any]:
    lines = prepare(text)
    works, refs = [], []
    for kind, ls in split_entries(lines):
        if kind == 'ref':
            src, _, tgt = ls[0].text.partition('←')
            refs.append({'source': src.strip(), 'target': tgt.strip(), 'vol': vol,
                         'page': ls[0].page_start, 'line': ls[0].no})
        else:
            works.append(parse_work(ls, vol, len(works) + 1))
    return {'works': works, 'referrals': refs}


def text_commit() -> Optional[str]:
    try:
        return subprocess.check_output(['git', '-C', ROOT, 'log', '-1', '--format=%H', '--', 'text/fankha'],
                                       text=True).strip() or None
    except Exception:
        return None


def main(argv: List[str]):
    vols = [int(a) for a in argv] or list(range(1, 35))
    out_dir = os.path.join(ROOT, 'json', 'fankha_v2')
    os.makedirs(out_dir, exist_ok=True)
    commit = text_commit()
    for v in vols:
        with open(os.path.join(ROOT, 'text', 'fankha', f'fankha_vol_{v:02d}.txt'), encoding='utf-8') as fh:
            data = parse_volume(v, fh.read())
        doc = {'schema': 'fankha/v2', 'parser_version': PARSER_VERSION, 'text_commit': commit, 'volume': v,
               'total_works': len(data['works']),
               'total_copies': sum(len(w['copies']) for w in data['works']), **data}
        with open(os.path.join(out_dir, f'fankha_vol_{v:02d}.json'), 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
        print(f'vol {v:2d}: {doc["total_works"]} works, {doc["total_copies"]} copies')


if __name__ == '__main__':
    main(sys.argv[1:])
