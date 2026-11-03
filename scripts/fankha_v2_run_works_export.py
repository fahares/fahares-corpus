#!/usr/bin/env python3
"""Works of a run of one title that the OCR lost and the site lacks, for `fahares:add-corpus-works` (fahares step 14.23).

Inside a run of same-titled works («ساقی نامه», vol 17; «شرح زبدة الاصول», vol 19) the title alignment of the
v1-v2 comparison pairs by position, so a work the site lacks shows as the run's last one. The works are named here
by their v2 key, each checked on its page image. A copy the site holds under another work (the old text gave the
copies after the lost lines to the work before them) is moved: found in the volume by city, library and shelfmark on
the copy's page ±1, under a work of another author; the rest are made from v2. The slug suffix is the volume's next
free ordinal, from --next (read on production: local and production slugs differ after works were added there).

Usage: fankha_v2_run_works_export.py --out FILE --next 17:1755 --next 19:2128 v17-1301 v17-1302 … [--db fahares_prod]
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_v2_db_compare import ROOT, load_json, norm, query  # noqa: E402
from fankha_v2_new_works_export import copy_record, people, seq, work_columns  # noqa: E402


def site_copies(db, vol):
    return list(query(db, "SELECT JSON_OBJECT('id', m.id, 'slug', w.slug, 'author', w.author_name, 'city', m.city, "
                          "'library', m.library, 'shelfmark', ifnull(m.shelfmark, ''), 'page', ifnull(m.page_start, 0)) "
                          f"FROM manuscripts m JOIN works w ON w.id = m.work_id WHERE m.volume_number = {vol}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--next', action='append', required=True, help='VOLUME:ORDINAL, the first free slug ordinal')
    ap.add_argument('keys', nargs='+')
    args = ap.parse_args()
    nxt = {int(v): int(o) for v, o in (x.split(':') for x in args.next)}

    works, cache = [], {}
    for key in args.keys:
        vol, ordinal = (int(x) for x in key[1:].split('-'))
        if vol not in cache:
            cache[vol] = ({w['key']['ordinal']: w for w in load_json('fankha_v2', vol)},
                          open(os.path.join(ROOT, 'text', 'fankha', f'fankha_vol_{vol:02d}.txt'), encoding='utf-8').read().split('\n'),
                          site_copies(args.db, vol))
        v2, lines, site = cache[vol]
        w = v2[ordinal]
        author = norm((w['author'] or {}).get('name') or '')
        copies = []
        for c in w['copies']:
            page = (c.get('provenance') or {}).get('page_start') or 0
            hits = [r for r in site if norm(r['shelfmark']) == norm(c['shelfmark']) and abs(int(r['page']) - page) <= 1
                    and norm(r['author'] or '') != author]
            if len(hits) == 1:
                r = hits[0]
                copies.append({'move': {'id': r['id'], 'from_slug': r['slug'], 'city': r['city'], 'library': r['library'],
                                        'shelfmark': r['shelfmark']}, 'sequence_number': seq(c)})
            elif hits:
                raise SystemExit(f'{key}: {len(hits)} site copies for {c["shelfmark"]}')
            else:
                copies.append({'make': copy_record(c)})
        works.append({'v2': key, 'slug_suffix': f'-v{vol}-{nxt[vol]}', 'columns': work_columns(w, lines), **people(w),
                      'subjects': w['subjects'], 'languages': w['languages'], 'copies': copies})
        nxt[vol] += 1

    out = {'source': f'works of a same-titled run the site lacks, checked on the page images, {date.today()}; '
                     f'fahares step 14.23', 'works': works, 'fills': [], 'work_updates': []}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    cs = [c for w in works for c in w['copies']]
    print(f"{len(works)} works; copies: {sum('move' in c for c in cs)} moved, {sum('make' in c for c in cs)} made",
          file=sys.stderr)


if __name__ == '__main__':
    main()
