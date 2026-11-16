#!/usr/bin/env python3
"""A copy's scribe whose name the old import read wrong (fahares item 87, step 14.224; scribe_name rows of the
comparison report):
  - the date of the copy glued to the name, «محمد علی بن عباس تویسرکانی، تا سه شنبه 16 ذیقعده 1085ق» ("trimmed"): the
    name is cut where v2's ends, and the date goes to the empty date column («بی‌تا» sets is_bita);
  - the part of the name the catalogue completes in brackets, lost with all after it, «محمد» for «محمد [اسماعیل]
    سبزواری» ("extended"): the name is v2's, when it stands so in the copy's text.
A bracket that is no part of the name stays out («[بخش اول]», «[؟]», «[که می‌تواند مؤلف نیز باشد]»), and so does a
copy whose date column holds another date.
Each record carries "scribe": "rename": fahares:rebuild-copies then renames the linked person instead of unlinking
the copy, where that person has only these copies.
Input: a fankha_v2_db_compare.py report. Output: a fahares:rebuild-copies file.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_v2_fill_columns_export import letters  # noqa: E402
from fankha_v2_ie_tail_export import q  # noqa: E402

DATE_TAIL = re.compile(r'^[\s،؛]*(?:تا\s*:?\s*(\S.*)|(بی\s*‌?تا|بیتا))\s*$')
NOT_NAME = re.compile(r'افتاده|رفته|شاید|چنین|^\s*ظ\s*$|كذا|کذ|دست|شده|درگذشته|بخش|جلد|؟|که\s|برگ|پایان|قسمت|نسخه|مؤلف|کذا|\.\.\.|ظاهرا|گویا|احتمال|رساله|کتاب|جزء|\d')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.224')
    args = ap.parse_args()
    rows = [d for d in map(json.loads, open(Path(args.report) / 'diffs.jsonl', encoding='utf-8'))
            if d['table'] == 'Manuscript' and d['field'] == 'scribe_name' and d['category'] in ('trimmed', 'extended') and not d['protected']]
    ids = sorted({int(d['id']) for d in rows})
    site = {}
    for i in range(0, len(ids), 500):
        for r in q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'scribe_name', scribe_name, 'copy_date_raw', copy_date_raw, "
                            f"'is_bita', is_bita, 'raw', raw_text) from manuscripts where id in ({','.join(map(str, ids[i:i + 500]))})"):
            site[r['id']] = r
    out, counts = [], Counter()
    for d in rows:
        s, v2 = site.get(int(d['id'])), (d['v2'] or '').strip()
        if not s or s['scribe_name'] != d['db']:
            counts['changed since the report'] += 1
            continue
        old, changes = s['scribe_name'], {}
        if d['category'] == 'trimmed':
            m = DATE_TAIL.match(old[len(v2):]) if old.startswith(v2) and v2 else None
            if not m:
                continue
            if s['copy_date_raw']:
                counts['date: the column holds a date'] += 1
                continue
            changes['scribe_name'] = {'from': old, 'to': v2}
            if m.group(1):
                changes['copy_date_raw'] = {'from': None, 'to': m.group(1).strip(' .،؛')}
                counts['date moved'] += 1
            elif not s['is_bita']:
                changes['is_bita'] = {'from': s['is_bita'], 'to': 1}
                counts['bita set'] += 1
        else:
            parts = re.findall(r'\[([^\[\]]*)\]', v2)
            if not parts or not v2.startswith(old.rstrip()):
                continue
            if any(NOT_NAME.search(p) or len(p) > 40 or not p.strip() for p in parts) or 'درگذشته' in v2:
                counts['bracket: no part of the name'] += 1
                continue
            if letters(v2) not in letters(s['raw'] or ''):
                counts['bracket: not so in the text'] += 1
                continue
            changes['scribe_name'] = {'from': old, 'to': v2}
            counts['bracket restored'] += 1
        out.append({'table': 'manuscripts', 'id': s['id'], 'shelfmark': s['shelfmark'], 'category': 'rebuild', 'v2': d['label'].split(' ')[0],
                    'scribe': 'rename', 'changes': changes})
    Path(args.out).write_text(json.dumps({'source': f"a scribe's name cut before the glued date, or completed with its bracketed part, from v2 ({args.report}), {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(sorted(counts.items())))


if __name__ == '__main__':
    main()
