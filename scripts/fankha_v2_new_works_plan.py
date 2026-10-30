#!/usr/bin/env python3
"""Plan the works parser v2 has and the site lacks (item 87): for each, the slug suffix it gets and, for each of its
copies, the site copy that already holds it (under another work) or nothing (to be made).

Usage: fankha_v2_new_works_plan.py --report reports/fankha_v2_db_review3 --out FILE [--db fahares_prod]

A v2 work is new when the title alignment leaves it unmatched and no site work of the same title and author holds
its copies (`new_works.json`, step 13.71). A copy is found on the site by its full text (`other_work.jsonl`, the
comparison's raw-text match) or else by shelfmark on the same page (±1). A new work's slug ends with the next
free ordinal of its volume («-v16-2501»): the site's ordinals are the old parser's, so v2's cannot be used.
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_v2_db_compare import load_json  # noqa: E402


def n(s):
    return re.sub(r'[\s‌\-_.]', '', (s or '').replace('ي', 'ی').replace('ى', 'ی').replace('ك', 'ک')
                  .replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا'))


def query(db, sql):
    out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                          f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    return [line.split('\t') for line in out.split('\n') if line]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()

    new = [x for x in json.load(open(os.path.join(args.report, 'new_works.json'))) if x['cls'] == 'new']
    by_raw = collections.defaultdict(dict)
    for line in open(os.path.join(args.report, 'other_work.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        by_raw[r['v2_work'].split(' ')[0]][n(r['raw_text'].split('\n')[0])] = r['id']
    top = {int(v): int(m) for v, m in query(args.db, "select volume_number, max(cast(substring_index(slug, '-', -1) as unsigned)) from works group by volume_number")}

    works, used = [], set()
    for vol in sorted({x['vol'] for x in new}):
        v2 = {w['key']['ordinal']: w for w in load_json('fankha_v2', vol)}
        site = collections.defaultdict(list)
        info = {}
        for mid, wid, shelf, page, slug, title in query(args.db, f"select m.id, m.work_id, ifnull(m.shelfmark, '-'), ifnull(m.page_start, 0), w.slug, w.primary_title from manuscripts m join works w on w.id = m.work_id where m.volume_number = {vol}"):
            site[n(shelf)].append((int(mid), int(page)))
            info[int(mid)] = (int(wid), slug, title)
        for x in sorted((x for x in new if x['vol'] == vol), key=lambda x: x['ordinal']):
            w = v2[x['ordinal']]
            top[vol] += 1
            copies = []
            for i, c in enumerate(w['copies']):
                mid = by_raw[x['key']].get(n(c['raw_text'].split('\n')[0]))
                if mid is None:
                    page = (c.get('provenance') or {}).get('page_start') or 0
                    hits = [h for h in site.get(n(c['shelfmark']), []) if abs(h[1] - page) <= 1 and h[0] not in used]
                    mid = hits[0][0] if len(hits) == 1 else None
                if mid in used:
                    mid = None
                if mid:
                    used.add(mid)
                wid, slug, title = info.get(mid, (None, None, None))
                copies.append({'index': i, 'head': c['raw_text'].split('\n')[0], 'page': (c.get('provenance') or {}).get('page_start'),
                               'site_id': mid, 'site_work_id': wid, 'site_work_slug': slug, 'site_work_title': title})
            works.append({'v2': x['key'], 'vol': vol, 'ordinal': x['ordinal'], 'slug_suffix': f'-v{vol}-{top[vol]}',
                          'title': w['title'], 'author': (w['author'] or {}).get('name'),
                          'pages': [w['provenance']['page_start'], w['provenance']['page_end']], 'copies': copies})
    out = {'source': f'works parser v2 has and the site lacks ({args.report}), {date.today()}', 'works': works}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    held = sum(1 for w in works for c in w['copies'] if c['site_id'])
    print(f"{len(works)} works, {sum(len(w['copies']) for w in works)} copies: {held} on the site, "
          f"{sum(len(w['copies']) for w in works) - held} to make", file=sys.stderr)


if __name__ == '__main__':
    main()
