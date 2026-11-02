#!/usr/bin/env python3
"""Works whose description on the site is their author's name and its transliteration (fahares item 87, step 14.8).

v1 read the author line of these entries into the description, so the site has no author for them. The decision
file names each work by slug and moves the name to author_name (the command links it to a person only where
PersonNameMatcher is confident, else the name stays text) and empties the description, only where v2 reads the same
author from the entry and the description is that name and nothing else of substance. A person is linked only when
v2 gives the author's century. For `fahares:add-corpus-works`.

Usage: fankha_v2_author_from_description_export.py --diffs reports/fankha_v2_db_review7/diffs.jsonl --out FILE
"""
import argparse
import base64
import glob
import json
import re
import subprocess
import sys
from datetime import date

LATIN = re.compile(r'[a-zāīūšḥṣṭẓžčğ‘’]', re.I)


def norm(t):
    return re.sub(r'\s+', ' ', (t or '').replace('ي', 'ی').replace('ك', 'ک')).strip(' .،؛:')


def site_rows(db, ids):
    rows = {}
    for i in range(0, len(ids), 2000):
        sql = (f"select id, slug, replace(to_base64(description), '\\n', ''), ifnull(author_name, ''), "
               f"replace(to_base64(primary_title), '\\n', ''), volume_number from works "
               f"where id in ({','.join(map(str, ids[i:i + 2000]))})")
        out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        for line in out.rstrip('\n').split('\n'):
            rid, slug, desc, author, title, vol = line.split('\t')
            rows[int(rid)] = (slug, base64.b64decode(desc).decode() if desc != 'NULL' else '', author,
                              base64.b64decode(title).decode() if title != 'NULL' else '', int(vol))
    return rows


def v2_works(v2dir):
    works = {}
    for f in sorted(glob.glob(f'{v2dir}/fankha_vol_*.json')):
        for w in json.load(open(f, encoding='utf-8'))['works']:
            works[f"-v{w['key']['vol']}-{w['key']['ordinal']}"] = w
    return works


def by_title_and_author(works, vol, title, name):
    """The one v2 work of the volume with this title and this author, when the ordinal points elsewhere (a work
    restored from a page image shifts the ordinals after it; a run of works of one title is in another order)."""
    hits = [w for k, w in works.items() if k.startswith(f'-v{vol}-') and norm(w.get('title_line') or '') == norm(title)
            and norm((w.get('author') or {}).get('name')) == norm(name)]
    return hits[0] if len(hits) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diffs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--v2', default='json/fankha_v2')
    args = ap.parse_args()

    ids = [int(d['id']) for d in map(json.loads, open(args.diffs, encoding='utf-8'))
           if d['table'] == 'Work' and d['field'] == 'description' and d['category'] == 'emptied'
           and d['site'] == 'v1' and not d['protected']]
    site, v2 = site_rows(args.db, ids), v2_works(args.v2)
    updates, skipped = [], {}
    for rid in ids:
        slug, desc, author, title, vol = site[rid]
        lines = [x.strip() for x in desc.strip().split('\n') if x.strip()]
        m = re.search(r'-v\d+-\d+$', slug)
        w = v2.get(m.group(0)) if m else None
        a = (w or {}).get('author') or {}
        if lines and norm(lines[0]) not in (norm(a.get('name')), norm(a.get('name_raw'))):
            w = by_title_and_author(v2, vol, title, lines[0]) or w
            a = (w or {}).get('author') or {}
        if author:
            skipped[rid] = 'the site has an author'
        elif a.get('hedge') or (lines and lines[0].startswith('؟')):
            skipped[rid] = 'the author is hedged («؟»), which the update would not keep'
        elif not lines or not a.get('name') or len(lines) > 2 or (len(lines) == 2 and not LATIN.search(lines[1])):
            skipped[rid] = 'the description is more than a name and its transliteration'
        elif norm(lines[0]) not in (norm(a.get('name')), norm(a.get('name_raw'))) \
                and norm(re.sub(r'،?\s*-?\s*\d+.*$', '', lines[0])) != norm(a.get('name')):
            skipped[rid] = 'v2 reads another author'
        else:
            death = a.get('death') or {}
            updates.append({'work_slug': slug, 'v2': m.group(0).lstrip('-'), 'id': rid,
                            'changes': {'author_name': {'from': None, 'to': a['name']},
                                        'description': {'from': desc, 'to': w.get('description')}},
                            # a person is linked only with the author's century: these names are mostly bare
                            # («احمد بن ابراهیم»), and without a date the match is a guess
                            'author': {'name': a['name'], 'century': death['century']} if death.get('century') else None})
    out = {'source': f'fankha parser v2 against the site ({args.diffs}), {date.today()}; steps 14.8 and 14.10',
           'works': [], 'fills': [], 'work_updates': updates,
           'skipped': [{'id': k, 'why': v} for k, v in skipped.items()]}
    json.dump(out, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(updates)} works, {len(skipped)} skipped', file=sys.stderr)


if __name__ == '__main__':
    main()
