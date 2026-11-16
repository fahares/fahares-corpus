#!/usr/bin/env python3
"""A work's description the old import lost (fahares items 87 and 15; "filled" Work/description rows of the
comparison report, the site's column being empty):
  - the description read as the author's name, «از: ملاجعفر (ق13 و 14هـ) در مقدمه گوید: …», «از: صالح. منظومه‌ای است
    در دویست و نه بیت …»: the name alone stays in author_name (with «(؟)» where the catalogue doubts it), the rest
    becomes the description. Where the text names no author («اصل از شیخ صدوق …», «ناشناخته، حاوی …», «یکی از علمای
    شیخیه گویا …») author_name is emptied and the whole text is the description;
  - the description set on the transliteration's line, «māhūzī, hoseyn ebn-e mohammad ( - 1768) اجازه مبسوطی است …»,
    or after no author line («اصل از علی شاه خوارزمی است که …»): the description is v2's, without the Latin head.
Left out: a v2 description that is only a label («همانند:», «به امر: …» the dedication column holds), print
information («چاپ: …», the print_info column's), a line of sources in brackets, names of several people, and the
cases listed in SKIP with their reason.
The name is cut by rule and, where the rule does not fit, by the hand-made NAMES table below (read from the text).
The work is unlinked from the person whose "name" was the sentence (add-corpus-works links a person only on a
confident match); those person records stay, without works, for a later clean-up.

Input: a fankha_v2_db_compare.py report. Output: work_updates for fahares:add-corpus-works.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_v2_fill_columns_export import letters, site  # noqa: E402

LABEL_ONLY = re.compile(r'^(?:(?:ظاهرا|ظاهراً|احتمالاً|احتمالا|بعضاً)?\s*(?:غیر\s*)?همانند(?:ی\s+نامعلوم)?|نامعلوم|ناشناس)\s*:?$')
COLUMN_LINE = re.compile(r'^(?:به امر|به دستور|به نام|به درخواست|اهداء به|تقدیم به|وابسته به|تاریخ ت[اأ]لیف|محل ت[اأ]لیف|تاریخ ترجمه)\s*:')
LATIN_HEAD = re.compile(r'^[^؀-ۿ]*[a-zA-Zāīūšḥṣṭẓ‘][^؀-ۿ]*(?=[؀-ۿ])')
NAME = re.compile(r'^(.{2,40}?)(\s*\(\s*؟\s*\)|؟)?(?:\.\s*|؛\s*)(?=\S)')

# work id -> (author_name or None, description); read from the text where the rule does not fit
NAMES = {
    46244: ('محمد بن یوسف', None),            # «محمد بن یوسف کتابی است در علم رمل …»
    65297: ('ابن المعاد', None),              # «ابن المعاد حکم شصت و شش چیز نجس را …»
    316: ('ملاجعفر', None),                   # «ملاجعفر (ق13 و 14هـ) در مقدمه گوید: …»
    14804: ('طوسی', None),                    # «طوسی (ق 14ق). ترجیع‌بندی است …»
    54220: ('سید مرتضی', None),               # «سید مرتضی و از احوال و آثار او نشانی نیافتیم. …»
    47568: ('عبدالله طاهر', None),            # «عبدالله طاهر، در 5 بیت»
    43501: ('امینای بری (؟)', None),          # «امینای بری؟ در آغاز آمده: …»
    68524: ('خادمی', None),                   # «خادمی.مختصری است …»
    5087: (None, 'whole'), 11613: (None, 'whole'), 36228: (None, 'whole'), 46305: (None, 'whole'),
}
SKIP = {
    52792: 'three authors', 33603: 'two authors and a note', 28843: 'the site holds another text', 25931: 'no «از:»',
    35831: 'a name alone', 67295: 'a name alone', 64246: 'a name alone', 28472: 'a name alone', 35653: 'a name alone',
    63110: 'a name alone', 47565: 'a name alone', 70103: 'a name alone',
    46391: 'v2 reads a copy as the description', 29340: 'an incipit', 29485: 'an incipit', 30828: 'an incipit',
}


def clean(v2):
    """v2's description without label lines, the Latin head and print information; None when nothing is left."""
    lines = []
    for line in v2.split('\n'):
        s = LATIN_HEAD.sub('', line.strip()).strip()
        if not s or LABEL_ONLY.match(s) or COLUMN_LINE.match(s) or re.match(r'^چاپ\s*:', s) or re.fullmatch(r'\[[^\[\]]+\]\.?', s):
            continue
        lines.append(s)
    text = '\n'.join(lines).strip()
    return text if len(letters(text)) >= 12 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', required=True)
    args = ap.parse_args()
    by_work = {}
    for d in map(json.loads, open(Path(args.report) / 'diffs.jsonl', encoding='utf-8')):
        if d['table'] == 'Work' and not d['protected']:
            by_work.setdefault(int(d['id']), {})[d['field']] = d
    rows = {i: f for i, f in by_work.items() if 'description' in f and f['description']['category'] == 'filled'}
    works = site(args.db, 'works', list(rows), ['description', 'author_name', 'author_id', 'print_info', 'dedication'])
    updates, counts = [], Counter()
    for rid, f in sorted(rows.items()):
        w, v2 = works[rid], f['description']['v2'].strip()
        if w['description']:
            counts['changed since the report'] += 1
            continue
        if rid in SKIP:
            counts['skipped: ' + SKIP[rid]] += 1
            continue
        changes = {}
        as_name = f.get('author_name', {}).get('category') == 'emptied'
        m = re.match(r'^از\s*:\s*', v2)
        if as_name:
            body = v2[m.end():] if m else v2
            if letters(body)[:150] != letters(w['author_name'] or '')[:150] and rid not in NAMES:
                counts['skipped: the name column holds another text'] += 1
                continue
            if rid in NAMES:
                name, desc = NAMES[rid]
                if desc == 'whole':
                    desc = body
                else:
                    bare = name.replace(' (؟)', '')
                    desc = body[body.index(bare) + len(bare):].lstrip(' ؟.،؛') if bare in body else None
            else:
                n = NAME.match(body)
                if not n or ' و ' in n.group(1) or '،' in n.group(1):
                    counts['skipped: no clear name'] += 1
                    continue
                name = n.group(1).strip() + (' (؟)' if n.group(2) else '')
                desc = body[n.end():].strip()
            if not desc or len(letters(desc)) < 8:
                counts['skipped: a name alone'] += 1
                continue
            changes['author_name'] = {'from': w['author_name'], 'to': name}
            changes['description'] = {'from': None, 'to': desc}
            counts['name and description parted'] += 1
        else:
            if m:
                counts['skipped: «از:» with the author kept'] += 1
                continue
            desc = clean(v2)
            if not desc:
                counts['skipped: label, print or citation only'] += 1
                continue
            changes['description'] = {'from': None, 'to': desc}
            counts['description filled'] += 1
        updates.append({'work_slug': w['key'], 'v2': f['description']['label'].split(' ')[0], 'id': rid, 'changes': changes})
    out = {'source': ("a work's description the old import lost: read as the author's name (the name parted from it), or set on the "
                      f"transliteration's line; from v2 ({args.report}), {date.today()}; fahares step {args.step}"),
           'category': 'corpus_fix', 'works': [], 'fills': [], 'work_updates': updates}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(updates), dict(sorted(counts.items())))


if __name__ == '__main__':
    main()
