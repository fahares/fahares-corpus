#!/usr/bin/env python3
"""Export the works parser v2 has and the site lacks as a decision file for `fahares:add-corpus-works` (item 87).

Usage: fankha_v2_new_works_export.py --report reports/fankha_v2_db_review3 --out FILE [--db fahares_prod]

Reads the plan of `fankha_v2_new_works_plan.py` (`new_works_plan.json`) and the page-image check of every new work
(`new_works_check/`, step 13.71), and writes:

- works: each new work's site columns from v2, its author and other people, subjects and languages, and its copies:
  a copy the site already holds under another work is moved (site id and the from-work's slug), the rest are made.
  The title is the printed heading line («ذخیرة الاسکندر (ترجمه)»), as the site keeps it; the slug suffix is the
  plan's next free ordinal of the volume. Works the check found on the site already (SAME_ON_SITE) are left out.
- fills: site works the moves leave without copies, because the old parser gave them the next entry's copies and
  dropped their own (EMPTIED_IDS, local ids read only for their slugs): their own copies from v2, moved when the site holds them elsewhere, else made.
- work_updates: site works whose columns came from a neighbouring entry (WORK_FIXES), each change with the value
  the site has, so the command writes only where nothing changed since.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_v2_db_compare import ROOT, load_json  # noqa: E402
from fankha_v2_new_works_plan import n, query  # noqa: E402
from fankha_v2_rebuild_export import values as copy_values  # noqa: E402

PAGE_TAG = re.compile(r'^\s*<!--\s*page:\s*\d+\s*-->\s*$')
# found on the site under a variant spelling or without the author (step 13.71)
SAME_ON_SITE = {'v11-1263', 'v17-1347', 'v23-858'}
# site works the moves leave empty (local id, for the slug) -> the v2 entry they are (title and author agree)
EMPTIED_IDS = {9389: 'v5-1003', 14218: 'v7-1648', 24545: 'v13-506', 30211: 'v15-1113', 35749: 'v18-227',
               35859: 'v18-340', 35935: 'v18-420', 47767: 'v23-850', 47835: 'v23-924', 47951: 'v23-1042'}
# site works whose author is a neighbour's: local id -> v2 entry («اصول العقائد» ج 4 holds Feyz's copies under
# Abdolwahhab's heading; «ساقی نامه» of Reza Forugh has no author)
WORK_FIXES = {6505: 'v4-473', 35113: 'v17-1347'}
FIX_COLUMNS = ('author_name', 'raw_text', 'description', 'bibliography', 'transliteration', 'composition_date_raw',
               'incipit_text', 'explicit_text', 'alternative_titles')


def entry_text(lines, w):
    end = w['copies'][0]['provenance']['line_start'] - 1 if w['copies'] else w['provenance']['line_end']
    text = '\n'.join(l for l in lines[w['provenance']['line_start'] - 1:end] if not PAGE_TAG.match(l))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def work_columns(w, lines):
    a = w['author'] or {}
    alts = [{'title': t, 'transliteration': (w['alt_transliterations'][i] if i < len(w['alt_transliterations']) else None)}
            for i, t in enumerate(w['alt_titles'])]
    return {
        'primary_title': w['title_line'],
        'clean_title': w['title'],
        'alternative_titles': alts or None,
        'transliteration': w['transliteration'],
        'author_name': a.get('name'),
        'composition_date_raw': (w['composition'] or {}).get('date'),
        'composition_place': (w['composition'] or {}).get('place'),
        'work_form': w['work_form'],
        'subject_summary': w['subject_raw'],
        'language_summary': w['language_raw'],
        'incipit_text': w['incipit'],
        'explicit_text': w['explicit'],
        'description': w['description'],
        'bibliography': w['bibliography'] or None,
        'print_info': w['print_info'],
        'dedication': w['dedication'],
        'related_work': w['related_work'],
        'commentaries_and_glosses': w['commentaries'] or None,
        'raw_text': entry_text(lines, w),
        'volume_number': w['key']['vol'],
        'page_start': w['provenance']['page_start'],
        'page_end': w['provenance']['page_end'],
    }


def people(w):
    a = w['author'] or {}
    death = a.get('death') or {}
    out = {'author': {'name': a.get('name'), 'hedge': a.get('hedge'), 'century': death.get('century'),
                      'death_year': death.get('sort_year')} if a.get('name') else None, 'roles': []}
    for role, field in (('translator', 'translator'), ('original_author', 'original_author')):
        p = w.get(field)
        if p and p.get('name'):
            out['roles'].append({'role': role, 'name': p['name'], 'hedge': p.get('hedge'),
                                 'century': ((p.get('death') or {}).get('century'))})
    return out


def copy_record(c):
    v = copy_values(c)
    pr = c.get('provenance') or {}
    v.update({'sequence_number': c['key']['seq'], 'page_start': pr.get('page_start'), 'page_end': pr.get('page_end'),
              'city': c['city'], 'library': c['library'], 'shelfmark': c['shelfmark']})
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()

    plan = json.load(open(os.path.join(args.report, 'new_works_plan.json')))['works']
    vols, texts = {}, {}

    def v2(key):
        vol, ordinal = (int(x) for x in key[1:].split('-'))
        if vol not in vols:
            vols[vol] = {w['key']['ordinal']: w for w in load_json('fankha_v2', vol)}
            texts[vol] = open(os.path.join(ROOT, 'text', 'fankha', f'fankha_vol_{vol:02d}.txt'), encoding='utf-8').read().split('\n')
        return vols[vol][ordinal], texts[vol]

    ids = {c['site_id'] for w in plan for c in w['copies'] if c['site_id']}
    site = {int(r[0]): r[1:] for r in query(args.db, "select m.id, w.slug, m.city, m.library, ifnull(m.shelfmark, '') from manuscripts m "
                                              f"join works w on w.id = m.work_id where m.id in ({','.join(map(str, ids))})")}
    moved = set()
    works = []
    for p in plan:
        if p['v2'] in SAME_ON_SITE:
            continue
        w, lines = v2(p['v2'])
        copies = []
        for pc, c in zip(p['copies'], w['copies']):
            if pc['site_id']:
                slug, city, library, shelf = site[pc['site_id']]
                copies.append({'move': {'id': pc['site_id'], 'from_slug': slug, 'city': city, 'library': library, 'shelfmark': shelf},
                               'sequence_number': c['key']['seq']})
                moved.add(pc['site_id'])
            else:
                copies.append({'make': copy_record(c)})
        works.append({'v2': p['v2'], 'slug_suffix': p['slug_suffix'], 'columns': work_columns(w, lines), **people(w),
                      'subjects': w['subjects'], 'languages': w['languages'], 'copies': copies})

    # the emptied works' own copies: on the site elsewhere (full text, then shelfmark on the page ±1) or made
    fills = []
    slugs = {int(r[0]): r[1] for r in query(args.db, f"select id, slug from works where id in ({','.join(map(str, EMPTIED_IDS))})")}
    for wid, key in EMPTIED_IDS.items():
        w, _ = v2(key)
        vol = w['key']['vol']
        rows = query(args.db, f"select m.id, w.slug, m.city, m.library, ifnull(m.shelfmark, ''), ifnull(m.page_start, 0), "
                              f"substring_index(m.raw_text, '\\n', 1) from manuscripts m join works w on w.id = m.work_id where m.volume_number = {vol}")
        copies = []
        for c in w['copies']:
            head = n(re.sub(r'^\d+\.\s*', '', c['raw_text'].split('\n')[0]))
            page = (c.get('provenance') or {}).get('page_start') or 0
            hits = [r for r in rows if int(r[0]) not in moved and r[1] != slugs[wid]
                    and (n(re.sub(r'^\d+\.\s*', '', r[6])) == head or (n(r[4]) == n(c['shelfmark']) and abs(int(r[5]) - page) <= 1))]
            if len(hits) == 1:
                r = hits[0]
                copies.append({'move': {'id': int(r[0]), 'from_slug': r[1], 'city': r[2], 'library': r[3], 'shelfmark': r[4]},
                               'sequence_number': c['key']['seq']})
                moved.add(int(r[0]))
            else:
                copies.append({'make': copy_record(c)})
        fills.append({'v2': key, 'work_slug': slugs[wid], 'copies': copies})

    # works whose columns are a neighbour's
    updates = []
    for wid, key in WORK_FIXES.items():
        w, lines = v2(key)
        cols = work_columns(w, lines)
        row = json.loads(query(args.db, "select json_object(" + ', '.join(f"'{c}', `{c}`" for c in ('slug',) + FIX_COLUMNS) +
                               f") from works where id = {wid}")[0][0])
        for c in ('bibliography', 'alternative_titles'):
            if isinstance(row[c], str):
                row[c] = json.loads(row[c])
        changes = {c: {'from': row[c], 'to': cols[c]} for c in FIX_COLUMNS if row[c] != cols[c]}
        updates.append({'v2': key, 'work_slug': row['slug'], **people(w), 'changes': changes})

    out = {'source': f'works parser v2 has and the site lacks ({args.report}), {date.today()}',
           'works': works, 'fills': fills, 'work_updates': updates}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    cs = [c for w in works for c in w['copies']] + [c for f in fills for c in f['copies']]
    print(f"{len(works)} works, {len(fills)} fills, {len(updates)} work updates; copies: "
          f"{sum('move' in c for c in cs)} moved, {sum('make' in c for c in cs)} made", file=sys.stderr)


if __name__ == '__main__':
    main()
