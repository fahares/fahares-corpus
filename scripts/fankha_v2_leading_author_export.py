#!/usr/bin/env python3
"""Works with no author on the site whose description begins with the author line v1 did not read (fahares item 87,
step 14.61).

v1 dropped an author line that begins with «از» or «در» («ازهری»، «درازی»، «دربندی») and others, and kept it, with
its transliteration, at the head of the description. Step 14.8 took only descriptions that were that name and
nothing more; step 14.11 compared the whole line, dates included, with v2's name. Here the first line of the
description, without its dates («، 282 - 370 قمری», «(-1216ق)», «، ق 12 قمری») and a transliteration on the same line, must be the name v2 reads for the work; the name
goes to author_name and that line and its transliteration leave the description, the rest of which stays as the
site has it. A hedged author («؟») is left to fahares:mark-hedged-authors. A person is linked only with v2's century.
For `fahares:add-corpus-works`.

--hedged (step 14.65): only the authors the line hedges («؟ …», «؟علی …», «احتمالا …»), as items for
fahares:mark-hedged-authors --file, which gives the name with its certainty and takes the line out of the description.

Usage: fankha_v2_leading_author_export.py --diffs reports/fankha_v2_db_review8/diffs.jsonl --out FILE [--db fahares_prod] [--hedged]
"""
import argparse
import json
import re
import sys
from datetime import date

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from fankha_v2_author_from_description_export import LATIN, by_title_and_author, norm, site_rows, v2_works  # noqa: E402

HEDGE = re.compile(r'^\s*(؟|محتملا|ظاهرا|گویا|شاید|احتمالا)(?:\s+|(?=[^\s]))')
DATES = re.compile(r'[\s،,]*\(?\s*-?\s*\d[\d\s\-–/؟?]*\s*(?:قمری|هجری|شمسی|میلادی|ق|ه|م|ش)?\s*\)?\s*$')
CENTURY = re.compile(r'[\s،,]*(?:ق|قرن)?\s*\d*\s*(?:قمری|هجری|شمسی|میلادی)\s*$')
PERSIAN = re.compile('[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]')  # letters, not the «،» a transliteration carries
TRANSLIT = re.compile(r'\s+[a-zA-Zāīūšḥṣṭẓžčğḏṯġẖ‘’\'\s,.()\-]+$')


def bare(head):
    """The name of an author line without its dates, century («، ق 12 قمری») and transliteration («سعید sa‘īd»)."""
    prev = None
    while prev != head:
        prev, head = head, DATES.sub('', CENTURY.sub('', TRANSLIT.sub('', head))).strip()
    return head


def key(t):
    return re.sub(r'\s*،\s*', '، ', norm(t)).replace(' ', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diffs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--v2', default='json/fankha_v2')
    ap.add_argument('--hedged', action='store_true', help='only hedged author lines, for fahares:mark-hedged-authors (step 14.65)')
    args = ap.parse_args()
    ids = [int(d['id']) for d in map(json.loads, open(args.diffs, encoding='utf-8'))
           if d['table'] == 'Work' and d['field'] == 'author_name' and d['category'] == 'filled'
           and not d['protected']]
    site, v2 = site_rows(args.db, ids), v2_works(args.v2)
    updates, skipped, items = [], {}, []
    for rid in ids:
        slug, desc, author, title, vol = site[rid]
        lines = desc.split('\n')
        first = next((i for i, x in enumerate(lines) if x.strip()), None)
        head = lines[first].strip() if first is not None else ''
        hedge = HEDGE.match(head)
        if args.hedged:
            head = HEDGE.sub('', head) if hedge else ''
        name = bare(head)
        m = re.search(r'-v\d+-\d+$', slug)
        w = v2.get(m.group(0)) if m else None
        a = (w or {}).get('author') or {}
        if head and key(name) not in (key(a.get('name')), key(a.get('name_raw'))):
            w = by_title_and_author(v2, vol, title, name) or w
            a = (w or {}).get('author') or {}
        if author:
            skipped[rid] = 'the site has an author'
        elif not head or not a.get('name'):
            skipped[rid] = 'no description, or v2 reads no author'
        elif not args.hedged and (a.get('hedge') or hedge):
            skipped[rid] = 'the author is hedged («؟»): fahares:mark-hedged-authors'
        elif '؟' in head:
            skipped[rid] = 'a «؟» inside the name (a date or a nisba), not on the attribution'
        elif key(name) not in (key(a.get('name')), key(a.get('name_raw'))):
            skipped[rid] = 'the description does not begin with the author v2 reads'
        else:
            rest = lines[first + 1:]
            nxt = next((i for i, x in enumerate(rest) if x.strip()), None)
            if nxt is not None and LATIN.search(rest[nxt]) and not PERSIAN.search(rest[nxt]):
                rest = rest[nxt + 1:]
            body = '\n'.join(rest).strip() or None
            if args.hedged:
                items.append({'work_slug': slug, 'id': rid, 'name': a['name'], 'hedge': hedge.group(1),
                              'description_from': desc, 'description_to': body})
                continue
            death = a.get('death') or {}
            updates.append({'work_slug': slug, 'v2': m.group(0).lstrip('-') if m else None, 'id': rid,
                            'changes': {'author_name': {'from': None, 'to': a['name']},
                                        'description': {'from': desc, 'to': body}},
                            'author': {'name': a['name'], 'century': death['century']} if death.get('century') else None})
    if args.hedged:
        json.dump({'source': f'hedged author lines at the head of the description ({args.diffs}), {date.today()}; step 14.65',
                   'items': items, 'skipped': [{'id': k, 'why': v} for k, v in skipped.items()]},
                  open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{len(items)} hedged authors, {len(skipped)} skipped', file=sys.stderr)
        return
    out = {'source': f'fankha parser v2 against the site ({args.diffs}), {date.today()}; step 14.61',
           'category': 'leading_author', 'works': [], 'fills': [], 'work_updates': updates,
           'skipped': [{'id': k, 'why': v} for k, v in skipped.items()]}
    json.dump(out, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(updates)} works, {len(skipped)} skipped', file=sys.stderr)


if __name__ == '__main__':
    main()
