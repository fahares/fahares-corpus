#!/usr/bin/env python3
"""Export reviewed categories of the v2-vs-site comparison as a decision file for `fahares:apply-corpus-categories`.

Usage: fankha_v2_apply_export.py --diffs reports/fankha_v2_db_review2/diffs.jsonl --out FILE CATEGORY ...

Categories (item 87, sample review step 13.65):
  facsimile  manuscripts with «نسخه اصل: …» get is_facsimile = 1 (site still has the v1 value 0)
  print_bib  the bracket of citations glued to the end of «چاپ» leaves print_info, when every citation in it is
             already in the work's bibliography; the command checks that again before writing

Each record names the row by id and by natural key (its work's slug suffix and, for a copy, its shelfmark, as
the site has them in --db, a copy of production: the command then finds a record merged, moved or renumbered since), and each change
by the value the site had in the comparison, so the command writes only where nothing changed since.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date


def site_keys(db, table, ids):
    """The natural key (slug suffix «-v2-856») of each record's work as the site has it: a work's ordinal in v2 can
    differ from the site's after restored works, so the comparison's label is not used."""
    keys = {}
    for i in range(0, len(ids), 2000):
        chunk = ','.join(map(str, ids[i:i + 2000]))
        sql = (f'select m.id, w.slug, m.shelfmark from manuscripts m join works w on w.id = m.work_id where m.id in ({chunk})'
               if table == 'manuscripts' else f'select id, slug, null from works where id in ({chunk})')
        out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        for line in out.strip().split('\n'):
            rid, slug, shelfmark = line.split('\t')
            m = re.search(r'-v\d+-\d+$', slug)
            keys[int(rid)] = (m.group(0) if m else None, shelfmark)
    return keys


def citations(bracket):
    return [t.strip() for t in re.split(r'[؛;]', bracket.strip(' ،.[]')) if t.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diffs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('categories', nargs='+', choices=['facsimile', 'print_bib'])
    args = ap.parse_args()

    records, skipped = [], {}
    for line in open(args.diffs, encoding='utf-8'):
        x = json.loads(line)
        if x['protected'] or x['site'] == 'unknown':
            continue
        if 'facsimile' in args.categories and x['field'] == 'is_facsimile' and x['category'] == 'flag_on':
            records.append({'table': 'manuscripts', 'id': x['id'],
                            'category': 'facsimile', 'changes': {'is_facsimile': {'from': 0, 'to': 1}}})
        elif 'print_bib' in args.categories and x['table'] == 'Work' and x['field'] == 'print_info' \
                and x['category'] == 'trimmed':
            db, v2 = x['db'], x['v2'] or ''
            tail = db[len(v2):] if db.startswith(v2) else None
            if not tail or not re.match(r'^[\s،.]*\[[^\[\]]*\][\s.]*$', tail):
                skipped[x['id']] = 'the cut is not one trailing bracket'
                continue
            records.append({'table': 'works', 'id': x['id'], 'category': 'print_bib',
                            'changes': {'print_info': {'from': db, 'to': v2 or None}},
                            'require_in_bibliography': citations(tail)})

    for table in ('manuscripts', 'works'):
        keys = site_keys(args.db, table, [r['id'] for r in records if r['table'] == table])
        for r in records:
            if r['table'] == table:
                r['work_key'], shelfmark = keys.get(r['id'], (None, None))
                if table == 'manuscripts':
                    r['shelfmark'] = shelfmark
    lost = [r for r in records if not r['work_key']]
    records = [r for r in records if r['work_key']]
    out = {'source': f'fankha parser v2 against the site ({args.diffs}), {date.today()}',
           'categories': args.categories, 'records': records,
           'skipped': [{'id': k, 'why': v} for k, v in skipped.items()]
           + [{'id': r['id'], 'why': 'not on the site'} for r in lost]}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f'{len(records)} records, {len(skipped)} skipped', file=sys.stderr)


if __name__ == '__main__':
    main()
