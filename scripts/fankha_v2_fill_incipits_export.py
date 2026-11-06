#!/usr/bin/env python3
"""Incipits and explicits the site's own entry text has and its columns lack (fahares item 87, step 14.67).

v1 left incipit_text or explicit_text empty where the entry numbers them («آغاز 1:», «برابر2») or writes them in a way
it did not read; parser v2 read them. A value is taken only where the site's column is empty and the whole of v2's
value (letters only: spaces, punctuation and digits aside) is in the record's own raw text on the site, so nothing
comes from a neighbouring entry. Works go to `fahares:add-corpus-works` (work_updates), copies to
`fahares:rebuild-copies` (records); both write only where the site still holds the empty value.

Usage: fankha_v2_fill_incipits_export.py --diffs reports/fankha_v2_db_review8/diffs.jsonl --works FILE --copies FILE [--db fahares_prod]
"""
import argparse
import base64
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date

FIELDS = ('incipit_text', 'explicit_text')


def letters(s):
    s = (s or '').replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('ى', 'ی')
    return re.sub(r'[\s‌\W_0-9]+', '', s)


def site(db, table, ids):
    cols = 'id, slug' if table == 'works' else 'id, shelfmark'
    out = {}
    for i in range(0, len(ids), 1000):
        sql = (f"select {cols}, replace(to_base64(ifnull(raw_text, '')), '\\n', ''), "
               + ', '.join(f"ifnull(replace(to_base64({f}), '\\n', ''), 'NULL')" for f in FIELDS)
               + f" from {table} where id in ({','.join(map(str, ids[i:i + 1000]))})")
        res = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        for line in filter(None, res.split('\n')):
            rid, key, raw, *vals = line.split('\t')
            out[int(rid)] = {'key': key, 'raw': base64.b64decode(raw).decode(),
                             **{f: None if v == 'NULL' else base64.b64decode(v).decode() for f, v in zip(FIELDS, vals)}}
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
        if d['field'] in FIELDS and d['category'] == 'filled' and not d['protected'] and d.get('v2'):
            wanted[(d['table'], d['id'])][d['field']] = d['v2']
    skipped = defaultdict(int)
    updates, records = [], []
    for table, name in (('Work', 'works'), ('Manuscript', 'manuscripts')):
        ids = sorted(i for t, i in wanted if t == table)
        rows = site(args.db, name, ids)
        for rid in ids:
            row = rows.get(rid)
            if not row:
                skipped['gone'] += 1
                continue
            raw = letters(row['raw'])
            changes = {}
            for field, value in wanted[(table, rid)].items():
                if (row[field] or '').strip():
                    skipped['the site has a value'] += 1
                elif not letters(value) or letters(value) not in raw:
                    skipped["v2's value is not in the record's own text"] += 1
                else:
                    changes[field] = {'from': row[field], 'to': value.strip()}
            if not changes:
                continue
            if table == 'Work':
                m = re.search(r'-(v\d+-\d+)$', row['key'])
                updates.append({'work_slug': row['key'], 'v2': m.group(1) if m else None, 'id': rid, 'changes': changes, 'author': None})
            else:
                records.append({'table': 'manuscripts', 'id': rid, 'shelfmark': row['key'], 'category': 'incipits',
                                'v2': 'filled', 'changes': changes})
    src = f'incipits and explicits of the record\'s own text ({args.diffs}), {date.today()}; fahares step 14.67'
    json.dump({'source': src, 'category': 'incipits', 'works': [], 'fills': [], 'work_updates': updates},
              open(args.works, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({'source': src, 'records': records}, open(args.copies, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n = lambda xs: sum(len(x['changes']) for x in xs)
    print(f'{len(updates)} works ({n(updates)} values), {len(records)} copies ({n(records)} values); skipped {dict(skipped)}', file=sys.stderr)


if __name__ == '__main__':
    main()
