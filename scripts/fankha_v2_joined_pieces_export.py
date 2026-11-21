#!/usr/bin/env python3
"""The pieces parser v2.5.0 joins to the field they stand right after (fahares item 87): a second date or a remark on
the date, more of the binding, the paper or the place of copying. A piece joins where a model read it as the rest of
that field (reconciliations/fankha_note_types.jsonl, «c») and it follows the field's value in the record's own text.

The copies whose v2 value grew between two parser outputs (--before DIR, and json/fankha_v2 now) are matched to the
site's copies by their text. The site's column gets the same tail, keeping its own spelling of the part it has, where
it holds what v2 held before (letters and digits alike). A date's remark («تا: قرن 12، در عصر مؤلف») goes to
copy_date_note where that is empty. Left alone: a column that holds another value, or the piece already.
Output: a decision file for `fahares:rebuild-copies` (records with `changes: {column: {from, to}}`); the command
itself leaves a column a reviewed correction protects.

Usage: fankha_v2_joined_pieces_export.py --before scratch/fankha_v2_241_before --copies FILE [--db fahares_prod] [--step 14.N]
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fankha_v2_db_compare import query, rkey  # noqa: E402
from fankha_v2_fill_columns_export import site, tight  # noqa: E402

V2 = {
    'copy_date_raw': lambda c: (c['copy_date'] or {}).get('raw'),
    'copy_date_note': lambda c: (c['copy_date'] or {}).get('note'),
    'copy_place': lambda c: (c['copy_place'] or {}).get('v'),
    'paper': lambda c: c['paper'],
    'binding': lambda c: c['binding'],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--copies', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='')
    args = ap.parse_args()
    grown = defaultdict(list)            # text key → [{column: (before, now)}]
    for f in sorted(glob.glob(str(ROOT / 'json/fankha_v2/*.json'))):
        now = json.load(open(f, encoding='utf-8'))['works']
        was = json.load(open(os.path.join(args.before, os.path.basename(f)), encoding='utf-8'))['works']
        for wn, wb in zip(now, was):
            for cn, cb in zip(wn['copies'], wb['copies']):
                diff = {}
                for col, get in V2.items():
                    a, b = get(cb), get(cn)
                    if a != b and b and (col == 'copy_date_note' or (a and b.startswith(a + '، '))):
                        diff[col] = (a, b)
                if diff:
                    grown[rkey(cn['raw_text'])].append(diff)
    by_text = defaultdict(list)
    for r in query(args.db, "select json_object('id', id, 'raw', raw_text) from manuscripts where catalog_id = 1"):
        k = rkey(r['raw'])
        if k in grown:
            by_text[k].append(r['id'])
    skipped = Counter()
    want = {}
    for k, diffs in grown.items():
        if len(by_text[k]) != 1 or len(diffs) != 1:
            skipped['copy: not one copy with this text on the site'] += 1
            continue
        want[by_text[k][0]] = diffs[0]
    rows = site(args.db, 'manuscripts', sorted(want), list(V2)) if want else {}
    records, per = [], Counter()
    for rid in sorted(want):
        row, changes = rows[rid], {}
        for col, (a, b) in want[rid].items():
            have = (row[col] or '').strip()
            if col == 'copy_date_note':
                piece = b[len(a) + 2:] if a and b.startswith(a + '، ') else b
                if tight(piece) in tight(have):
                    skipped[f'{col}: the site has it'] += 1
                elif have:
                    skipped[f'{col}: the site holds another note'] += 1
                else:
                    changes[col] = {'from': None, 'to': b}
            elif tight(have) == tight(b):
                skipped[f'{col}: the site has it'] += 1
            elif tight(have) != tight(a):
                skipped[f'{col}: the site holds another value'] += 1
            else:
                changes[col] = {'from': row[col], 'to': have + b[len(a):]}
        if changes:
            records.append({'table': 'manuscripts', 'id': rid, 'shelfmark': row['key'], 'category': 'columns', 'v2': 'joined', 'changes': changes})
            per.update(changes.keys())
    src = f"pieces parser v2.5.0 joins to the field they follow (before: {args.before}), {date.today()}" + (f'; fahares step {args.step}' if args.step else '')
    json.dump({'source': src, 'records': records}, open(args.copies, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{sum(map(len, grown.values()))} v2 copies grew; {len(records)} copies; values {dict(per)}; skipped {dict(skipped)}', file=sys.stderr)


if __name__ == '__main__':
    main()
