#!/usr/bin/env python3
"""Corpus-wide comparison of parser v1 (json/fankha) and v2 (json/fankha_v2) on the error classes of
fahares/docs/plans/fankha-parser-v2.md section 3. Prints one JSON object."""
import glob
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = re.compile(r'<!--\s*page:')
HEDGE = re.compile(r'^(?:گویا|ظاهرا|ظاهراً|احتمالا|احتمالاً|شاید)\s')


def n(s): return re.sub(r'\s+', ' ', re.sub(r'<!--\s*page:\s*\d+\s*-->', ' ', s or '')).strip().replace('‌', '')


def leaks(x):
    if isinstance(x, dict): return any(leaks(v) for k, v in x.items() if k != 'raw_text')
    if isinstance(x, list): return any(leaks(v) for v in x)
    return isinstance(x, str) and bool(PAGE.search(x))


def glued(text, raw, label):
    """the value's end is not on the raw line that carries its label"""
    e = n(text)
    if not e: return None
    segs = [l.split(label, 1)[1] for l in (n(x) for x in raw.split('\n')) if label in l]
    return bool(segs) and not any(e[-30:] in s for s in segs)


c1, c2 = Counter(), Counter()
for f in sorted(glob.glob(os.path.join(ROOT, 'json', 'fankha', 'fankha_vol_*.json'))):
    for w in json.load(open(f))['works']:
        c1['works'] += 1
        d = w['description'] or ''
        c1['desc_is_hetero_marker'] += bool(re.fullmatch(r'(?:بعضاً |ظاهرا |ظاهراً )?غیر ?همانند:?', d.strip()))
        c1['no_author'] += not w['author_name']
        for m in w['manuscripts']:
            c1['copies'] += 1
            c1['contents_note_khatt'] += (m['contents_note'] or '').startswith('خط:')
            c1['hedge_in_date'] += bool(HEDGE.match(m['copy_date_raw'] or ''))
            c1['hedge_in_scribe'] += bool(HEDGE.match(m['scribe_name'] or ''))
            c1['page_tag_leak'] += leaks(m)
            g = glued(m['explicit_text'], m['raw_text'], 'انجام:')
            if g is not None: c1['explicits'] += 1; c1['explicit_glued'] += g
for f in sorted(glob.glob(os.path.join(ROOT, 'json', 'fankha_v2', 'fankha_vol_*.json'))):
    for w in json.load(open(f))['works']:
        c2['works'] += 1
        d = w['description'] or ''
        c2['desc_is_hetero_marker'] += bool(re.fullmatch(r'(?:بعضاً |ظاهرا |ظاهراً )?غیر ?همانند:?', d.strip()))
        c2['no_author'] += not w['author']
        c2['author_hedged'] += bool((w['author'] or {}).get('hedge'))
        c2['heterogeneous'] += w['heterogeneous'] is not None
        for cp in w['copies']:
            c2['copies'] += 1
            c2['page_tag_leak'] += leaks(cp)
            c2['hedge_in_date'] += bool(HEDGE.match((cp['copy_date'] or {}).get('raw') or ''))
            c2['hedge_in_scribe'] += any(HEDGE.match(s['name']) for s in cp['scribes'])
            c2['date_hedged'] += bool((cp['copy_date'] or {}).get('hedge'))
            c2['scribe_hedged'] += any(s['hedge'] for s in cp['scribes'])
            c2['contents_scope'] += bool(cp['contents_scope'])
            c2['copy_description'] += bool(cp['copy_description'])
            c2['original_copy'] += bool(cp['original_copy'])
            c2['other_listings'] += len(cp['other_listings'])
            c2['copies_with_remark_notes'] += any(x['type'] == 'remark' for x in cp['notes'])
            ex = cp['explicit']
            if ex and ex['text']:
                g = glued(ex['text'], cp['raw_text'], 'انجام:')
                if g is not None: c2['explicits'] += 1; c2['explicit_glued'] += g
print(json.dumps({'v1': c1, 'v2': c2}, ensure_ascii=False, indent=1))
