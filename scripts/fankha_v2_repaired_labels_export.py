#!/usr/bin/env python3
"""Columns parser v2.4.0 newly reads from labels printed without their mark or misprinted (fahares item 87, step 14.282).

The copies whose v2 fields changed between two parser outputs (--before DIR, and json/fankha_v2 now) are matched to the
site's copies by their text. For those copies only, the comparison's «filled» differences (the site's column is empty,
v2 has a value) of the content columns are taken, where no reviewed correction protects the column and the record's
own text on the site shows the value: letters for text columns, digits and «×» for a size or a date, «N سطر» and «N گ»
for the counts. «بی‌کا» and «بی‌تا» are turned on where v2 now reads them and the column they speak of is empty.
Output: a decision file for `fahares:rebuild-copies` (records with `changes: {column: {from, to}}`).

Usage: fankha_v2_repaired_labels_export.py --before scratch/fankha_v2_before --diffs reports/fankha_v2_db_review10/diffs.jsonl --copies FILE [--db fahares_prod]
"""
import argparse
import re
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
from fankha_v2_fill_columns_export import shown, letters, tight, site, norm  # noqa: E402

V2_FIELDS = ('script_raw', 'scribes', 'no_scribe', 'copy_date', 'undated', 'copy_place', 'folios', 'lines', 'dimensions',
             'paper', 'binding', 'incipit', 'explicit', 'commissioned_by')
# a scribe or a patron read this way is too often a remark («نونویس», «… با پنج سرلوح مذهب»): those stay for a reviewer
COLUMNS = ('copy_date_raw', 'binding', 'lines', 'dimensions', 'explicit_text', 'incipit_text', 'paper', 'folios', 'copy_place')
FLAGS = {'is_bika': 'scribe_name', 'is_bita': 'copy_date_raw'}


def is_shown(field, value, raw):
    if field == 'lines':            # «23س (9/5×16/5)», «29سط»: the count as the misprinted label has it
        return bool(re.search(r'(?<![\d/])' + str(int(value)) + r'\s*(?:سطری|سطر|سط|س)(?![\u0600-\u06FF])', norm(raw)))
    if field == 'copy_date_raw':
        return len(tight(value)) >= 3 and tight(value) in tight(raw)
    if field in ('binding', 'scribe_name', 'incipit_text', 'explicit_text'):
        return len(letters(value)) >= 3 and letters(value) in letters(raw)
    return shown(field, value, raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--diffs', required=True)
    ap.add_argument('--copies', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    changed = set()
    for f in sorted(glob.glob(str(ROOT / 'json/fankha_v2/*.json'))):
        now = json.load(open(f, encoding='utf-8'))['works']
        was = json.load(open(os.path.join(args.before, os.path.basename(f)), encoding='utf-8'))['works']
        for wn, wb in zip(now, was):
            for cn, cb in zip(wn['copies'], wb['copies']):
                if any(cn[k] != cb[k] for k in V2_FIELDS):
                    changed.add(rkey(cn['raw_text']))
    by_text = defaultdict(list)
    for r in query(args.db, "select json_object('id', id, 'raw', raw_text) from manuscripts where catalog_id = 1"):
        by_text[rkey(r['raw'])].append(r['id'])
    ids = {v[0] for k, v in by_text.items() if k in changed and len(v) == 1}
    wanted, skipped = defaultdict(dict), Counter()
    for d in map(json.loads, open(args.diffs, encoding='utf-8')):
        if d['table'] != 'Manuscript' or d['id'] not in ids:
            continue
        if (d['field'] in COLUMNS and d['category'] == 'filled') or (d['field'] in FLAGS and d['category'] == 'flag_on'):
            if d['protected']:
                skipped[f"{d['field']}: a reviewed correction"] += 1
            elif d.get('v2') not in (None, ''):
                wanted[d['id']][d['field']] = d['v2']
    fields = list(dict.fromkeys(list(COLUMNS) + list(FLAGS) + list(FLAGS.values())))
    rows = site(args.db, 'manuscripts', sorted(wanted), fields) if wanted else {}
    records, per = [], Counter()
    for rid in sorted(wanted):
        row, changes = rows[rid], {}
        for field, value in wanted[rid].items():
            if field in ('paper', 'binding'):
                # «کاغذ سپاهانی جلد تیماج مشکی», «جلد تیماج 3گ (60پ-62ر)»: the next field ran on with no mark
                value = re.split(r'\s+(?:جلد\s|\d[\d/]*\s*(?:گ|برگ|ص)(?![\u0600-\u06FF]))', str(value))[0].strip(' :،,')
                if not value or len(value.split()) > 8:
                    skipped[f'{field}: not a {field}'] += 1
                    continue
            if field in FLAGS:
                if str(row[field] or '0') != '0' or str(row[FLAGS[field]] or '').strip():
                    skipped[f'{field}: the site has the flag or the value'] += 1
                else:
                    changes[field] = {'from': 0, 'to': 1}
            elif field == 'scribe_name' and str(value).strip().startswith('='):
                skipped['scribe_name: the author, not a name'] += 1
            elif str(row[field] or '').strip() not in ('', '0'):
                skipped[f'{field}: the site has a value'] += 1
            elif not is_shown(field, value, row['raw']):
                skipped[f"{field}: not in the record's own text"] += 1
            else:
                to = int(value) if field in ('lines', 'folios') else str(value).strip()
                changes[field] = {'from': None if row[field] in (None, '') else (int(row[field]) if field in ('lines', 'folios') else row[field]), 'to': to}
        # a copy that gets a scribe or a date is no longer «بی‌کا» or «بی‌تا»
        for flag, column in FLAGS.items():
            if column in changes and str(row[flag] or '0') != '0':
                changes[flag] = {'from': 1, 'to': 0}
        if changes:
            records.append({'table': 'manuscripts', 'id': rid, 'shelfmark': row['key'], 'category': 'columns', 'v2': 'filled', 'changes': changes})
            per.update(changes.keys())
    src = f"columns parser v2.4.0 newly reads ({args.diffs}), {date.today()}; fahares step 14.282"
    json.dump({'source': src, 'records': records}, open(args.copies, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(changed)} v2 copies changed, {len(ids)} on the site; {len(records)} copies; values {dict(per)}; skipped {dict(skipped)}', file=sys.stderr)


if __name__ == '__main__':
    main()
