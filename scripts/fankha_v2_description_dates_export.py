#!/usr/bin/env python3
"""A date of composition or a dedication left as a line of a work's description on the site (fahares backlog item 148):
parser v2 from 2.3.1 reads the labels «سال تألیف:», «زمان تألیف:», «تاریخ ترجمه:», «به امر:», «اهداء:», «اهداءبه:» and
the date with no mark («تاریخ تألیف 1209ق», volume 22), which v1 and v2 up to 2.3.0 left in the description.

A line is taken out of the site's description, and its column filled with v2's value, where the column is empty, the
line's value is v2's (digits and letters alike; a place after the date, «…؛ محل تألیف: …», goes to its own column the
same way), and what is left of the description is v2's description, letter for letter. «تاریخ ترجمه» is the work's
date only where v2 made it so: the work has no other date (the user's decision, step 14.235); elsewhere v2 keeps the
line in the description, and so it stays here.

A site work is v2's work of its slug's number where the titles agree, and else the one work of its title on its page in
its volume (v2 found more works in volume 22 than v1, so the numbers there no longer agree).

Output: work_updates for `fahares:add-corpus-works`.
Usage: fankha_v2_description_dates_export.py --out FILE --step 14.N [--db fahares_prod] [--v2 json/fankha_v2]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fankha_v2_db_compare import query  # noqa: E402
from fankha_v2_fill_columns_export import letters, site, tight  # noqa: E402
from fankha_v2_author_from_description_export import v2_works  # noqa: E402

DATE = re.compile(r'^(?P<l>تاریخ ت[اأ]لیف|سال ت[اأ]لیف|زمان ت[اأ]لیف|تاریخ ترجمه)\s*:?\s*(?P<v>[^؛]*?)\s*'
                  r'(?:[؛،]\s*(?:محل|مکان|جای) ت[اأ]لیف\s*:\s*(?P<p>.*?))?\s*؛?\s*$')
DEDICATION = re.compile(r'^(?:به امر|به دستور|به نام|به درخواست|اهداء\s*به|اهدا\s*به|اهداءبه|اهداء|اهدا|تقدیم به)\s*:\s*(?P<v>.+?)\s*$')
FIELDS = ['description', 'composition_date_raw', 'composition_place', 'dedication']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--step', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--v2', default=str(ROOT / 'json/fankha_v2'))
    args = ap.parse_args()
    v2 = v2_works(args.v2)
    # where v2 found more works in a volume than v1 (volume 22), a site work's slug no longer names v2's work of that
    # number: the work is then the one of its title on its page in that volume
    placed = defaultdict(list)
    for k, w in v2.items():
        placed[(w['key']['vol'], w['provenance']['page_start'], letters(w['title']))].append(k)
    ids, how = {}, Counter()
    for r in query(args.db, "select json_object('id', id, 'slug', slug, 'title', clean_title, 'vol', volume_number, 'page', page_start) "
                            "from works where catalog_id = 1 and description is not null "
                            "and description regexp 'ت[اأ]لیف|تاریخ ترجمه|به امر|به دستور|به نام|به درخواست|اهدا|تقدیم به'"):
        m = re.search(r'-v\d+-\d+$', r['slug'])
        if m and m.group(0) in v2 and letters(v2[m.group(0)]['title']) == letters(r['title']):
            ids[r['id']] = m.group(0)
            how['by the slug'] += 1
            continue
        there = placed.get((r['vol'], r['page'], letters(r['title'])), [])
        if len(there) == 1:
            ids[r['id']] = there[0]
            how['by title and page'] += 1
        else:
            how['no v2 work'] += 1
    rows = site(args.db, 'works', sorted(ids), FIELDS)
    updates, counts, kinds = [], Counter(), Counter()
    for rid in sorted(ids):
        w, f = rows[rid], v2[ids[rid]]
        comp = f.get('composition') or {}
        keep, fill, taken = [], {}, []
        for line in (w['description'] or '').split('\n'):
            s = line.strip()
            m = DATE.match(s)
            if m and m.group('v') and not (w['composition_date_raw'] or '').strip() and comp.get('date') \
                    and tight(m.group('v')) == tight(comp['date']):
                place = m.group('p')
                if place and ((w['composition_place'] or '').strip() or tight(place) != tight(comp.get('place') or '')):
                    keep.append(line)                     # the place has nowhere to go: the line stays whole
                    continue
                fill['composition_date_raw'] = comp['date']
                if place:
                    fill['composition_place'] = comp['place']
                taken.append('translation date' if m.group('l') == 'تاریخ ترجمه' else 'date')
                continue
            m = DEDICATION.match(s)
            if m and not (w['dedication'] or '').strip() and f.get('dedication') and letters(m.group('v')) \
                    and letters(m.group('v')) in letters(f['dedication']):
                fill['dedication'] = f['dedication']
                taken.append('dedication')
                continue
            keep.append(line)
        if not taken:
            continue
        rest = '\n'.join(keep).strip('\n')
        if letters(rest) != letters(f.get('description') or ''):
            counts["left: what stays is not v2's description"] += 1
            continue
        counts['works'] += 1
        kinds.update(taken)
        changes = {'description': {'from': w['description'], 'to': rest or None}}
        for field, value in fill.items():
            changes[field] = {'from': w[field], 'to': value}
        updates.append({'work_slug': w['key'], 'v2': ids[rid].lstrip('-'), 'id': rid, 'changes': changes, 'author': None})
    out = {
        'source': ("a date of composition or a dedication left as a line of a work's description, taken out where its "
                   "column is empty and takes v2's value, and only where what is left is v2's description, "
                   f"{date.today()}; fahares step {args.step}"),
        'category': 'description_dates', 'works': [], 'fills': [], 'work_updates': updates,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(ids), 'works looked at', dict(how), ';', dict(counts), dict(kinds), file=sys.stderr)


if __name__ == '__main__':
    main()
