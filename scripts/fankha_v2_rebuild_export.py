#!/usr/bin/env python3
"""Export copies whose content on the site belongs to another copy, rebuilt from parser v2, as a decision file for
`fahares:rebuild-copies`.

Usage: fankha_v2_rebuild_export.py --ids FILE --out FILE [--db fahares_prod]

FILE lists site manuscript ids, one per line, each with the v2 copy found for it (tab separated: id, vol, ordinal,
copy index). These are copies whose city, library and shelfmark are right but whose raw text, date, scribe and size
came from a neighbouring copy (item 87, step 13.70). For each, every content column the site keeps is taken from
the v2 copy at the same place; the record keeps its identity (work, sequence, city, library, shelfmark, pages).
Each change carries the value the site has in --db, so the command writes only where nothing changed since.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_v2_db_compare import FLAGS, ie_text, lead_int, load_json  # noqa: E402

COLUMNS = ['raw_text', 'scribe_name', 'has_other_scribes', 'is_bika', 'is_bita', 'is_autograph', 'copy_date_raw',
           'copy_date_hijri_year', 'copy_place', 'commissioned_by', 'folios', 'lines', 'dimensions', 'paper', 'binding',
           'incipit_text', 'explicit_text', *FLAGS, 'metadata']


def values(c):
    """The site's columns for a v2 copy."""
    date_raw = (c['copy_date'] or {}).get('raw')
    year = (c['copy_date'] or {}).get('sort_year') if date_raw and re.search(r'\d{3,4}', date_raw) else None
    notes = [n['text'] for n in c['notes'] if n['type'] not in ('seal', 'ownership')]
    owned = [n['text'] for n in c['notes'] if n['type'] in ('seal', 'ownership')] + list(c['ownership'])
    v = {
        'raw_text': c['raw_text'],
        'scribe_name': c['scribes'][0]['name'] if c['scribes'] else None,
        'has_other_scribes': int(len(c['scribes']) > 1),
        'is_bika': int(c['no_scribe']),
        'is_bita': int(c['undated']),
        'is_autograph': int(c['is_autograph']),
        'copy_date_raw': date_raw,
        'copy_date_hijri_year': year,
        'copy_place': (c['copy_place'] or {}).get('v'),
        'commissioned_by': c['commissioned_by'],
        'folios': lead_int(c['folios']) if 'گ' in (c['folios'] or '') else None,   # «2ص» is pages, not leaves
        'lines': lead_int(c['lines']),
        'dimensions': c['dimensions'],
        'paper': c['paper'],
        'binding': c['binding'],
        'incipit_text': ie_text(c['incipit']),
        'explicit_text': ie_text(c['explicit']),
        **{col: int(f in c['flags']) for col, f in FLAGS.items()},
        'metadata': {'incipits': [], 'explicits': [], 'editorial_notes': notes, 'ownership_and_seals': owned,
                     'catalog_citation': c['catalog_citation'], 'residual_notes': None},
    }
    return v


def site_rows(db, ids):
    cols = ', '.join(f'`{c}`' for c in COLUMNS)
    sql = f"select json_object('id', id, 'shelfmark', shelfmark, {', '.join(f'{q!r}, `{c}`' for q, c in zip(COLUMNS, COLUMNS))}) " \
          f"from manuscripts where id in ({','.join(map(str, ids))})"
    out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                          f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    rows = {}
    for line in out.strip().split('\n'):
        r = json.loads(line)
        if isinstance(r.get('metadata'), str):
            r['metadata'] = json.loads(r['metadata'] or 'null')
        rows[r['id']] = r
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()

    wanted = [line.split('\t') for line in open(args.ids, encoding='utf-8') if line.strip()]
    site = site_rows(args.db, [int(w[0]) for w in wanted])
    vols = {}
    records = []
    for mid, vol, ordinal, index in wanted:
        vol, ordinal, index = int(vol), int(ordinal), int(index)
        if vol not in vols:
            vols[vol] = {w['key']['ordinal']: w for w in load_json('fankha_v2', vol)}
        c = vols[vol][ordinal]['copies'][index]
        row = site[int(mid)]
        new = values(c)
        changes = {k: {'from': row.get(k), 'to': v} for k, v in new.items() if row.get(k) != v}
        records.append({'table': 'manuscripts', 'id': int(mid), 'shelfmark': row['shelfmark'], 'category': 'rebuild',
                        'v2': f'v{vol}-{ordinal}#{index}', 'changes': changes})
    out = {'source': f'site copies rebuilt from fankha parser v2 ({args.ids}), {date.today()}', 'records': records}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f'{len(records)} records', file=sys.stderr)


if __name__ == '__main__':
    main()
