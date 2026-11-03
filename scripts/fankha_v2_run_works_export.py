#!/usr/bin/env python3
"""Works of a run of one title that the OCR lost and the site lacks, for `fahares:add-corpus-works` (fahares step 14.23).

Inside a run of same-titled works («ساقی نامه», vol 17; «شرح زبدة الاصول», vol 19) the title alignment of the
v1-v2 comparison pairs by position, so a work the site lacks shows as the run's last one. The works are named here
by their v2 key, each checked on its page image. A copy the site holds under another work (the old text gave the
copies after the lost lines to the work before them) is moved: found in the volume by city, library and shelfmark on
the copy's page ±2 (v1's pages run a page off), under a work of another author; the rest are made from v2. The slug suffix is the volume's next
free ordinal, from --next (read on production: local and production slugs differ after works were added there).
A shelfmark the site holds twice under the work («رضوی 7141», vol 11) moves by its sequence (`from_sequence`); a
«همان نسخه بالا» row the site keeps apart and v2 keeps on the copy (`other_listings`) moves with it.

--fill V2KEY:SLUG gives a site work the copies v2 lists for it, all made (a work the lost text left without its own).

Usage: fankha_v2_run_works_export.py --out FILE --next 17:1755 --next 19:2128 [--fill v22-1594:SLUG] v17-1301 …
       [--db fahares_prod]
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
                          "'library', m.library, 'shelfmark', ifnull(m.shelfmark, ''), 'page', ifnull(m.page_start, 0), "
                          "'seq', ifnull(m.sequence_number, 0)) "
                          f"FROM manuscripts m JOIN works w ON w.id = m.work_id WHERE m.volume_number = {vol}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--next', action='append', required=True, help='VOLUME:ORDINAL, the first free slug ordinal')
    ap.add_argument('--fill', action='append', default=[], help='V2KEY:SLUG, a site work whose own copies the site lacks')
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
        copies, used = [], set()

        def found(shelfmark, library, page):
            hits = [r for r in site if norm(r['shelfmark']) == norm(shelfmark) and abs(int(r['page']) - page) <= 2
                    and norm(r['library'] or '')[:4] == norm(library or '')[:4] and norm(r['author'] or '') != author
                    and r['id'] not in used]
            return sorted(hits, key=lambda r: r['seq'])

        def move(r, s, twins):
            used.add(r['id'])
            m = {'id': r['id'], 'from_slug': r['slug'], 'city': r['city'], 'library': r['library'], 'shelfmark': r['shelfmark']}
            if twins:
                m['from_sequence'] = r['seq']        # the site holds this shelfmark twice under the work
            return {'move': m, 'sequence_number': s}

        for c in w['copies']:
            page = (c.get('provenance') or {}).get('page_start') or 0
            hits = found(c['shelfmark'], c['library'], page)
            twins = sum(norm(x['shelfmark']) == norm(c['shelfmark']) and x['library'] == c['library'] for x in w['copies'])
            if len(hits) == 1 or (hits and twins > 1 and len(hits) <= twins):
                copies.append(move(hits[0], seq(c), twins > 1))     # twins: in the order of the site's sequence
            elif hits:
                raise SystemExit(f'{key}: {len(hits)} site copies for {c["shelfmark"]}')
            else:
                copies.append({'make': copy_record(c)})
            # «همان نسخه بالا» rows v2 keeps on the copy (other_listings) are rows of their own on the site
            for o in c.get('other_listings') or []:
                hits = found(o['shelfmark'], o['library'], page)
                if len(hits) == 1:
                    copies.append(move(hits[0], seq(c), False))
        works.append({'v2': key, 'slug_suffix': f'-v{vol}-{nxt[vol]}', 'columns': work_columns(w, lines), **people(w),
                      'subjects': w['subjects'], 'languages': w['languages'], 'copies': copies})
        nxt[vol] += 1

    # site works left without their own copies (vol 22 «عشق» of Alamuti Taleqani holds only Jaberi's copy)
    fills = []
    for spec in args.fill:
        key, slug = spec.split(':')
        vol, ordinal = (int(x) for x in key[1:].split('-'))
        w = {x['key']['ordinal']: x for x in load_json('fankha_v2', vol)}[ordinal]
        fills.append({'v2': key, 'work_slug': slug, 'copies': [{'make': copy_record(c)} for c in w['copies']]})

    out = {'source': f'works of a same-titled run the site lacks, checked on the page images, {date.today()}; '
                     f'fahares step 14.23', 'works': works, 'fills': fills, 'work_updates': []}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    cs = [c for w in works for c in w['copies']]
    print(f"{len(works)} works; copies: {sum('move' in c for c in cs)} moved, {sum('make' in c for c in cs)} made",
          file=sys.stderr)


if __name__ == '__main__':
    main()
