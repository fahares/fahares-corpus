#!/usr/bin/env python3
"""Columns the record's own Fankha text has and the site leaves empty, from parser v2 (fahares item 87, step 14.91).

Like fankha_v2_fill_incipits_export.py (step 14.67), for copies' paper, dimensions, lines, folios, copy_place and
commissioned_by, and works' composition_date_raw. A value is taken only where the site's column is empty and the
record's own raw text shows it: letters for text columns, «13×20سم» with its digits for dimensions, «N سطر» and «N گ»
for the counts, the date without spaces for a date of composition. Works go to `fahares:add-corpus-works`
(work_updates), copies to `fahares:rebuild-copies` (records). Export before any run: afterwards the columns are full.

Usage: fankha_v2_fill_columns_export.py --diffs reports/fankha_v2_db_review9/diffs.jsonl --works FILE --copies FILE [--db fahares_prod]
"""
import argparse
import base64
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date

COPY = ('paper', 'dimensions', 'lines', 'folios', 'copy_place', 'commissioned_by')
WORK = ('composition_date_raw',)
LABELS = {'paper': r'کاغذ\s*:?', 'copy_place': r'(?:جا|محل کتابت)\s*:', 'commissioned_by': r'(?:به امر|به سفارش|سفارش|برای|به خواهش)'}
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def norm(s):
    return (s or '').translate(DIGITS).replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('ى', 'ی')


def letters(s):
    return re.sub(r'[\s‌\W_0-9]+', '', norm(s))


def tight(s):
    return re.sub(r'[\s‌]+', '', norm(s)).replace('x', '×').replace('X', '×').replace('*', '×')


def shown(field, value, raw):
    if field in ('lines', 'folios'):
        unit = r'سطر' if field == 'lines' else r'(?:گ|برگ)'
        return bool(re.search(r'(?<![\d/])' + str(int(value)) + r'\s*' + unit, norm(raw)))
    if field in ('dimensions', 'composition_date_raw'):
        return len(tight(value)) >= 3 and tight(value) in tight(raw)
    if len(letters(value)) < 3 or letters(value) not in letters(raw):
        return False
    # a text column only where its own label prints it: «کاغذ: نخودی», «جا: نجف», «به امر …»
    label = LABELS.get(field)
    first = re.escape(norm(value).split()[0])
    return not label or bool(re.search(label + r'[^؛\n]{0,40}?' + first, norm(raw)))


def site(db, table, ids, fields):
    key = 'slug' if table == 'works' else 'shelfmark'
    out = {}
    for i in range(0, len(ids), 1000):
        sql = (f"select id, {key}, replace(to_base64(ifnull(raw_text, '')), '\\n', ''), "
               + ', '.join(f"ifnull(replace(to_base64(`{f}`), '\\n', ''), 'NULL')" for f in fields)
               + f" from {table} where id in ({','.join(map(str, ids[i:i + 1000]))})")
        res = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        for line in filter(None, res.split('\n')):
            rid, k, raw, *vals = line.split('\t')
            out[int(rid)] = {'key': k, 'raw': base64.b64decode(raw).decode(),
                             **{f: None if v == 'NULL' else base64.b64decode(v).decode() for f, v in zip(fields, vals)}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diffs', required=True)
    ap.add_argument('--works', required=True)
    ap.add_argument('--copies', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    wanted = defaultdict(dict)
    for d in map(json.loads, open(args.diffs, encoding='utf-8')):
        fields = COPY if d['table'] == 'Manuscript' else WORK
        if d['field'] in fields and d['category'] == 'filled' and not d['protected'] and d.get('v2') not in (None, ''):
            wanted[(d['table'], d['id'])][d['field']] = d['v2']
    skipped = defaultdict(int)
    updates, records = [], []
    for table, name, fields in (('Work', 'works', WORK), ('Manuscript', 'manuscripts', COPY)):
        ids = sorted(i for t, i in wanted if t == table)
        rows = site(args.db, name, ids, fields) if ids else {}
        for rid in ids:
            row = rows.get(rid)
            if not row:
                skipped['gone'] += 1
                continue
            changes = {}
            for field, value in wanted[(table, rid)].items():
                if field == 'paper':
                    # «کاغذ نخودی، جلد مقوا …» without its colon: v2 ran on into the binding and the extent
                    value = re.split(r'\s*[:،,]?\s*(?:جلد|\d|اندازه)', str(value))[0].strip(' :،,')
                if field == 'paper' and (len(value.split()) > 6 or re.match(r'(?:و|این)\s', value)):
                    skipped['paper: a sentence, not a paper'] += 1
                elif str(row[field] or '').strip() not in ('', '0'):
                    skipped[f'{field}: the site has a value'] += 1
                elif not shown(field, value, row['raw']):
                    skipped[f"{field}: not in the record's own text"] += 1
                else:
                    to = int(value) if field in ('lines', 'folios') else str(value).strip()
                    changes[field] = {'from': None if row[field] in (None, '') else (int(row[field]) if field in ('lines', 'folios') else row[field]), 'to': to}
            if not changes:
                continue
            if table == 'Work':
                m = re.search(r'-(v\d+-\d+)$', row['key'])
                updates.append({'work_slug': row['key'], 'v2': m.group(1) if m else None, 'id': rid, 'changes': changes, 'author': None})
            else:
                records.append({'table': 'manuscripts', 'id': rid, 'shelfmark': row['key'], 'category': 'columns',
                                'v2': 'filled', 'changes': changes})
    src = f"columns of the record's own text ({args.diffs}), {date.today()}; fahares step 14.91"
    json.dump({'source': src, 'category': 'columns', 'works': [], 'fills': [], 'work_updates': updates},
              open(args.works, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({'source': src, 'records': records}, open(args.copies, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    per = defaultdict(int)
    for r in updates + records:
        for f in r['changes']:
            per[f] += 1
    print(f'{len(updates)} works, {len(records)} copies; values {dict(per)}; skipped {dict(skipped)}', file=sys.stderr)


if __name__ == '__main__':
    main()
