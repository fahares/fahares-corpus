#!/usr/bin/env python3
"""Copies whose heading the OCR bent (fahares item 87, step 14.146): «2. قم،فرهاد معتمد شماره نسخه: …», «4 شیراز
علامه طباطبائی؛ شماره نسخه 68/3», «6. قم؛ مرکز احیاء؛ برابرشماره نسخه: 4010». Parser v2.2.0 reads them; v1 did not.
- A copy the site holds on its own with no city, library and shelfmark gets them, and its library's id.
- A copy v1 merged into the copy above it: the copy above is rebuilt from v2 with its own text and columns, and the
  merged one is made.
Output: a rebuild-copies file (records) and an add-corpus-works file (fills).
"""
import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fankha_parser_v2 as p  # noqa: E402
from fankha_v2_author_from_description_export import v2_works  # noqa: E402
from fankha_v2_new_works_export import copy_record  # noqa: E402
from fankha_v2_rebuild_export import values as copy_values  # noqa: E402

WORKS = ['v4-1880', 'v7-172', 'v7-1324', 'v7-1332', 'v7-1550', 'v10-1781', 'v12-1055', 'v22-211']


def q(db, sql):
    out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c', f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -N -B {db}'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    return [json.loads(l.replace('\\\\', '\\')) for l in out.splitlines() if l.strip()]


def esc(s):
    return s.replace("'", "''")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--rebuild', required=True)
    ap.add_argument('--fills', required=True)
    ap.add_argument('--step', default='14.146')
    args = ap.parse_args()
    v2 = v2_works('json/fankha_v2')
    records, fills, log = [], [], []
    for key in WORKS:
        w = v2['-' + key]
        vol = key.split('-')[0][1:]
        for i, c in enumerate(w['copies']):
            head = c['raw_text'].split('\n')[0]
            if p.COPY_HEAD.match(head):
                continue
            # the site's work by the copy's own text: its slug ordinal may differ from v2's (v4-1880 is the site's v4-1879)
            hit = q(args.db, "select json_object('id', m.id, 'work_id', m.work_id, 'shelfmark', m.shelfmark, 'raw', m.raw_text, 'slug', w.slug) "
                             "from manuscripts m join works w on w.id = m.work_id "
                             f"where w.slug like '%-v{vol}-%' and m.raw_text like '%{esc(head[:40])}%'")
            if len(hit) != 1:
                log.append((key, i, 'site copy not found'))
                continue
            row = hit[0]
            slug = {'s': row['slug'], 'id': row['work_id']}
            lib = q(args.db, "select json_object('id', library_id) from manuscripts where library_id is not null and "
                             f"city = '{esc(c['city'])}' and library = '{esc(c['library'])}' group by library_id order by count(*) desc limit 1")
            if not lib:   # «قم، فرهاد معتمد»: the site has the library once, in another city
                lib = q(args.db, f"select json_object('id', id) from libraries where name = '{esc(c['library'])}'")
                lib = lib if len(lib) == 1 else []
            lib_id = lib[0]['id'] if lib else None
            if row['raw'].startswith(head):            # its own copy: only the heading's columns
                records.append({'table': 'manuscripts', 'id': row['id'], 'shelfmark': row['shelfmark'], 'category': 'rebuild',
                                'v2': f'{key}#{i}', 'changes': {
                                    'city': {'from': None, 'to': c['city']}, 'library': {'from': None, 'to': c['library']},
                                    'library_id': {'from': None, 'to': lib_id}, 'shelfmark': {'from': None, 'to': c['shelfmark']}}})
                log.append((key, i, 'heading', row['id'], lib_id))
                continue
            # merged into the copy above: that copy's own text and columns, and the merged one made
            above = w['copies'][i - 1]
            cur = q(args.db, "select json_object('raw_text', raw_text, 'scribe_name', scribe_name, 'copy_date_raw', copy_date_raw, "
                             "'copy_date_hijri_year', copy_date_hijri_year, 'folios', folios, 'lines', `lines`, 'dimensions', dimensions, "
                             "'paper', paper, 'binding', binding, 'metadata', metadata) from manuscripts where id = " + str(row['id']))[0]
            cur['metadata'] = json.loads(cur['metadata']) if isinstance(cur['metadata'], str) else cur['metadata']
            new = copy_values(above)
            changes = {f: {'from': cur[f], 'to': new[f]} for f in cur if f in new and cur[f] != new[f]}
            records.append({'table': 'manuscripts', 'id': row['id'], 'shelfmark': row['shelfmark'], 'category': 'rebuild',
                            'v2': f'{key}#{i - 1}', 'changes': changes})
            make = copy_record(c)
            fills.append({'v2': key, 'work_slug': slug['s'], 'copies': [{'make': make}]})
            log.append((key, i, 'split', row['id'], sorted(changes)))
    src = (f"copies whose heading the OCR bent, which parser v2.2.0 reads; {date.today()}; fahares step {args.step}")
    Path(args.rebuild).write_text(json.dumps({'source': src, 'records': records}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    Path(args.fills).write_text(json.dumps({'source': src, 'category': 'bent_heading', 'works': [], 'fills': fills, 'work_updates': []},
                                           ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for l in log:
        print(l)


if __name__ == '__main__':
    main()
