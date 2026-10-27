#!/usr/bin/env python3
"""Stratified gold-set sampler for Fankha parser audit (fahares item 87, phase 1).

Writes units.jsonl (raw text only, for blind annotation) and parsed.jsonl
(the current parser's output for the same units)."""
import glob, json, random, re, sys

CORPUS = sys.argv[1]
OUT = sys.argv[2]
rnd = random.Random(87)
PAGE = re.compile(r'<!--\s*page:\s*\d+\s*-->')
HEDGE = re.compile(r'گویا|ظاهرا|ظاهراً|احتمالا|احتمالاً|شاید|\(؟\)|منسوب')

works, mss = [], []
for f in sorted(glob.glob(f'{CORPUS}/json/fankha/fankha_vol_*.json')):
    d = json.load(open(f))
    v = d['volume_number']
    for wi, w in enumerate(d['works']):
        wid = f'v{v:02d}w{wi:05d}'
        works.append((wid, v, w))
        for m in w['manuscripts']:
            mss.append((f"{wid}m{m['sequence_number']}", v, w, m))

def header(w):
    return w.get('raw_text') or ''

def head_area(w):
    # title line + author block (before the description)
    return '\n'.join(header(w).split('\n')[:6])

def mid_tag(t):
    return any(PAGE.search(l) and PAGE.sub('', l).strip() for l in t.split('\n'))

W = {
    'rand': (40, lambda v, w: True),
    'nodate_author': (10, lambda v, w: w['author_name'] and not w['author_death_date_raw']),
    'no_author_latin2': (10, lambda v, w: not w['author_name'] and len([l for l in header(w).split('\n')[:6] if re.search(r'[a-zāīū]{3}', l)]) >= 2),
    'hedge_author': (10, lambda v, w: bool(HEDGE.search('\n'.join(head_area(w).split('\n')[2:])))),
    'heterogeneous': (10, lambda v, w: 'غیر همانند' in header(w) or w['is_heterogeneous']),
    'vol34': (10, lambda v, w: v == 34),
    'pagetag_header': (10, lambda v, w: mid_tag(header(w))),
    'collection': (10, lambda v, w: re.match(r'(?:مجموعه|جنگ|بیاض|سفینه)', w['primary_title'] or '')),
}
M = {
    'rand': (55, lambda v, w, m: True),
    'autograph': (15, lambda v, w, m: re.search(r'مؤلف|مصنف', m['raw_text']) and re.search(r'کا:|کاتب|خط مؤلف', m['raw_text'])),
    'hedge': (15, lambda v, w, m: re.search(r'(?:کا|تا|جا):\s*(?:گویا|ظاهرا|ظاهراً|احتمالا|احتمالاً|شاید)|\(؟\)', m['raw_text'])),
    'pagetag_mid': (15, lambda v, w, m: mid_tag(m['raw_text'])),
    'vol34': (10, lambda v, w, m: v == 34),
    'heterogeneous': (10, lambda v, w, m: w['is_heterogeneous']),
    'scope_prefix': (15, lambda v, w, m: re.search(r'^(?!آغاز|خط:|کا:|بی‌کا)[^\n؛]{3,80}؛\s*خط:', m['raw_text'], re.M)),
    'vol23': (5, lambda v, w, m: v == 23),
    'typed': (5, lambda v, w, m: 'تایپی' in m['raw_text']),
    'multi_incipit': (5, lambda v, w, m: m['raw_text'].count('آغاز') >= 2),
}

units, parsed, seen = [], [], set()
for name, (n, pred) in W.items():
    pool = [x for x in works if x[0] not in seen and pred(x[1], x[2])]
    for wid, v, w in rnd.sample(pool, min(n, len(pool))):
        seen.add(wid)
        units.append({'uid': wid, 'kind': 'work', 'stratum': name, 'vol': v, 'raw': header(w)})
        parsed.append({'uid': wid, 'kind': 'work', **{k: x for k, x in w.items() if k not in ('manuscripts', 'raw_text')}})
for name, (n, pred) in M.items():
    pool = [x for x in mss if x[0] not in seen and pred(x[1], x[2], x[3])]
    for uid, v, w, m in rnd.sample(pool, min(n, len(pool))):
        seen.add(uid)
        units.append({'uid': uid, 'kind': 'ms', 'stratum': name, 'vol': v,
                      'work_title': w['primary_title'], 'work_heterogeneous': w['is_heterogeneous'], 'raw': m['raw_text']})
        parsed.append({'uid': uid, 'kind': 'ms', **{k: x for k, x in m.items() if k != 'raw_text'}})

with open(f'{OUT}/units.jsonl', 'w') as fh:
    for u in units: fh.write(json.dumps(u, ensure_ascii=False) + '\n')
with open(f'{OUT}/parsed_v1.1.6.jsonl', 'w') as fh:
    for p in parsed: fh.write(json.dumps(p, ensure_ascii=False) + '\n')
from collections import Counter
print(len(units), Counter((u['kind'], u['stratum']) for u in units))
