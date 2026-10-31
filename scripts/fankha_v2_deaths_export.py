#!/usr/bin/env python3
"""Export the life dates of a work's author and translator from parser v2 (fahares item 96) for fahares:fill-death-ranges.

Usage: fankha_v2_deaths_export.py --v2 json/fankha_v2 --out FILE

For each work whose author or translator has a death text (author.death.raw, «1040 - 1124 ؟ قمری», «ق13 قمری»): its key,
title and page (the site finds its work by title and page, FankhaWorkLocator) and each person's name and that text as
written. Works of the same title in the same volume come too, with only their key, title and page, so the site can tell
same-titled works on one page apart in their order.
"""
import argparse
import glob
import json
import re
import sys
from datetime import date


def title_key(t):
    t = (t or '').translate(str.maketrans({'ي': 'ی', 'ك': 'ک', 'ة': 'ه', 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ی'}))
    t = re.sub(r'\s*\([^()]*\)\s*$', '', t)
    t = re.sub(r'[\s‌ـ«»()\[\]،.:؛\-]', '', t)
    return re.sub(r'^ال', '', t)


def person(p):
    raw = ((p or {}).get('death') or {}).get('raw') if isinstance(p, dict) else None
    return {'name': p.get('name'), 'death_raw': raw.strip()} if raw and raw.strip() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--v2', default='json/fankha_v2')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    works, wanted, allw = [], set(), []
    for f in sorted(glob.glob(f'{args.v2}/fankha_vol_*.json')):
        for w in json.load(open(f, encoding='utf-8'))['works']:
            base = {'key': w['key'], 'title': w.get('title') or '', 'provenance': {'page_start': (w.get('provenance') or {}).get('page_start')}}
            allw.append(base)
            people = {role: person(w.get(role)) for role in ('author', 'translator')}
            if any(people.values()):
                works.append(base | {role: p for role, p in people.items() if p})
                wanted.add((w['key']['vol'], title_key(base['title'])))
    have = {(w['key']['vol'], w['key']['ordinal']) for w in works}
    peers = [w for w in allw if (w['key']['vol'], title_key(w['title'])) in wanted and (w['key']['vol'], w['key']['ordinal']) not in have]
    out = {'source': f'fankha parser v2 ({args.v2}), {date.today()}', 'works': works, 'peers': peers}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(works)} works, {len(peers)} same-titled peers', file=sys.stderr)


if __name__ == '__main__':
    main()
