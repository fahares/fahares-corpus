#!/usr/bin/env python3
"""The columns of the site's copies that a new parser output reads otherwise than the one before (fahares item 87, step
14.302: parser v2.7.0 after the shifted commas and the run-on paper and binding were put right in the text).

The copies whose v2 value differs between two parser outputs (--before DIR, and json/fankha_v2 now) are matched to the
site's copies by their text before the change. A column is written where the site holds what v2 held before (letters,
digits and «×» alike; empty where v2 had none): the paper cut where the binding ran on («اصفهانی جلد تیماج مشکی» →
«اصفهانی»), the binding, the date, the place, the size, the leaves and the lines it now reads, and «بی‌کا» where the
copy has no scribe's name. A scribe's name is left for its own step: a fuller name is another person's record.
Output: a decision file for `fahares:rebuild-copies`, which leaves a column a reviewed correction protects.

Usage: fankha_v2_changed_columns_export.py --before scratch/fankha_v2_260 --copies FILE --step 14.302 [--db fahares_prod]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fankha_v2_db_compare import query, rkey, count_of, lead_int  # noqa: E402
from fankha_v2_fill_columns_export import site, tight  # noqa: E402

TEXT = {
    'copy_date_raw': lambda c: (c['copy_date'] or {}).get('raw'),
    'copy_place': lambda c: (c['copy_place'] or {}).get('v'),
    'paper': lambda c: c['paper'],
    'binding': lambda c: c['binding'],
    'dimensions': lambda c: c['dimensions'],
}
COUNTS = {
    'folios': lambda c: count_of(c['folios'], '(?:گ|برگ)'),
    'pages': lambda c: count_of(c['folios'], 'ص'),
    'lines': lambda c: lead_int(c['lines']),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--copies', required=True)
    ap.add_argument('--step', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    changed, texts = defaultdict(list), Counter()
    for f in sorted(glob.glob(str(ROOT / 'json/fankha_v2/*.json'))):
        now = json.load(open(f, encoding='utf-8'))['works']
        was = json.load(open(os.path.join(args.before, os.path.basename(f)), encoding='utf-8'))['works']
        for wn, wb in zip(now, was):
            for cn, cb in zip(wn['copies'], wb['copies']):
                texts[rkey(cb['raw_text'])] += 1
                diff = {col: (get(cb), get(cn)) for col, get in {**TEXT, **COUNTS}.items() if get(cb) != get(cn)}
                if cn['no_scribe'] and not cb['no_scribe'] and not cn['scribes']:
                    diff['is_bika'] = (0, 1)
                if diff:
                    # the site may hold the text before the fixes or after them
                    for key in {rkey(cb['raw_text']), rkey(cn['raw_text'])}:
                        changed[key].append(diff)
    by_text = defaultdict(list)
    for r in query(args.db, "select json_object('id', id, 'raw', raw_text) from manuscripts where catalog_id = 1"):
        k = rkey(r['raw'])
        if k in changed:
            by_text[k].append(r['id'])
    want, skipped = {}, Counter()
    for k, diffs in changed.items():
        if not by_text[k]:
            continue
        if len(by_text[k]) != 1 or len(diffs) != 1:
            skipped['copy: not one copy with this text on the site'] += 1
            continue
        want[by_text[k][0]] = diffs[0]
    rows = site(args.db, 'manuscripts', sorted(want), list(TEXT) + list(COUNTS) + ['is_bika', 'scribe_name']) if want else {}
    records, per = [], Counter()
    for rid in sorted(want):
        row, changes = rows[rid], {}
        for col, (a, b) in want[rid].items():
            have = (row[col] or '').strip()
            if col == 'is_bika':
                if have in ('', '0') and not (row['scribe_name'] or '').strip():
                    changes[col] = {'from': 0, 'to': 1}
                else:
                    skipped['is_bika: the site has the flag or a scribe'] += 1
            elif col in COUNTS:
                if b is None or a is not None:
                    skipped[f'{col}: v2 no longer reads it, or read another'] += 1
                elif have not in ('', '0'):
                    skipped[f'{col}: the site has a value'] += 1
                else:
                    changes[col] = {'from': None if row[col] in (None, '') else int(row[col]), 'to': int(b)}
            elif b is None:
                skipped[f'{col}: v2 no longer reads it'] += 1
            elif tight(have) == tight(b):
                skipped[f'{col}: the site has it'] += 1
            elif tight(have) != tight(a or ''):
                skipped[f'{col}: the site holds another value'] += 1
            elif col in ('paper', 'binding') and (re.search(r'\d\s*(?:گ|ص|برگ|سطر)', b) or len(b.split()) > 12):
                skipped[f'{col}: the value still runs on'] += 1
            else:
                changes[col] = {'from': row[col] if have else None, 'to': b}
        if changes:
            records.append({'table': 'manuscripts', 'id': rid, 'shelfmark': row['key'], 'category': 'columns', 'v2': 'changed', 'changes': changes})
            per.update(changes.keys())
    src = f"columns a new parser output reads otherwise (before: {args.before}), {date.today()}; fahares step {args.step}"
    json.dump({'source': src, 'records': records}, open(args.copies, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(records)} copies; values {dict(per)}; skipped {dict(skipped)}', file=sys.stderr)


if __name__ == '__main__':
    main()
