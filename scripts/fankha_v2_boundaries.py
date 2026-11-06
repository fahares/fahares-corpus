#!/usr/bin/env python3
"""Copies whose text ends in another place on the site than in parser v2 (fahares item 87, step 14.51).

Usage: fankha_v2_boundaries.py --out FILE [--db fahares_prod] [--ids FILE]

The copies are paired as fankha_v2_db_compare.py pairs them. A pair matched by its text is the same copy on both
sides; the rest (matched by shelfmark or by a text prefix) are compared on their text without spaces, and a
difference of more than a few letters gets a verdict from where the differing text sits:

  site_glued_v2_right   the site's copy holds text that is another v2 copy's (the copy after it, often one whose
                        heading the site lost at a page break): v2 is right
  site_lost_end_v2_has  the site's copy lacks text that v2 gives it and that no other copy on the site holds
  gemini                the site's text holds the error message a page's transcription gave instead of the page
  v2_glued_site_right   v2 holds in this copy text that is another copy on the site: the site is right
  needs_page_check      both sides hold text the other lacks: a page image decides

--out gets one row per copy (verdict, site id, v2 key, page, the v2 copy the site's extra text belongs to and
whether that copy has a pair on the site, both citations, and the differing text). --ids writes the copies v2 is
right for in the form fankha_v2_rebuild_export.py reads (id, vol, ordinal, copy index).
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fankha_v2_db_compare as C  # noqa: E402

V2_RIGHT = ('site_glued_v2_right', 'site_lost_end_v2_has', 'gemini')
TRIVIAL = 12        # a difference of up to this many letters (a lost «[») is no boundary


def flat(t):
    return C.norm(t or '').replace(' ', '')


def common(a, b, rev=False):
    if rev:
        a, b = a[::-1], b[::-1]
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--ids')
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    vols = list(range(1, 35))
    db_works, db_copies, _ = C.load_db(args.db, vols)
    v2_text = {}                                    # (vol, ordinal, index) -> flat text
    site_text = collections.defaultdict(list)       # vol -> [(id, flat text)]
    paired = set()                                  # v2 keys that have a site copy
    pairs = []
    for vol in vols:
        v2_works = C.load_json('fankha_v2', vol)
        amap = C.align(v2_works, C.load_json('fankha', vol))
        for w in v2_works:
            o = w['key']['ordinal']
            for i, c in enumerate(w['copies']):
                v2_text[(vol, o, i)] = flat(c['raw_text'])
            rows = db_works.get((vol, amap.get(o)), []) if amap.get(o) else []
            if len(rows) != 1:
                continue
            dbc = db_copies.get(rows[0]['id'], [])
            for d in dbc:
                site_text[vol].append((d['id'], flat(d['raw_text'])))
            got, _, _ = C.match_copies(dbc, w['copies'])
            idx = {id(c): i for i, c in enumerate(w['copies'])}
            for d, c, how in got:
                paired.add((vol, o, idx[id(c)]))
                if how != 'raw':
                    pairs.append((vol, o, idx[id(c)], d, c))
        print(f'vol {vol}', file=sys.stderr, flush=True)
    # a v2 copy whose text the site keeps whole, under another work, has a site copy too
    whole = {t for v in site_text.values() for _, t in v}
    paired |= {k for k, t in v2_text.items() if t in whole}
    by_vol = collections.defaultdict(list)
    for k, t in v2_text.items():
        by_vol[k[0]].append((k, t))

    def in_v2(vol, piece, me):
        q = piece[:40]
        return [k for k, t in by_vol[vol] if q in t and k != me][:1] if len(piece) >= 15 else []

    def in_site(vol, piece, me):
        q = piece[:40]
        return [i for i, t in site_text[vol] if q in t and i != me][:1] if len(piece) >= 15 else []

    out, ids = [], []
    for vol, o, i, d, c in pairs:
        a, b = flat(d['raw_text']), flat(c['raw_text'])
        p, s = common(a, b), common(a, b, rev=True)
        site_only = a[p:len(a) - s] if len(a) - s > p else ''
        v2_only = b[p:len(b) - s] if len(b) - s > p else ''
        if max(len(site_only), len(v2_only)) <= TRIVIAL:
            continue
        host = in_v2(vol, site_only, (vol, o, i))
        other_site = in_site(vol, v2_only, d['id'])
        if 'blocked by Gemini' in (d['raw_text'] or ''):
            verdict = 'gemini'
        elif other_site and not site_only:
            verdict = 'v2_glued_site_right'
        elif host and not other_site:
            verdict = 'site_glued_v2_right'
        elif v2_only and not site_only and not other_site:
            verdict = 'site_lost_end_v2_has'
        else:
            verdict = 'needs_page_check'
        h = host[0] if host else None
        out.append([verdict, d['id'], f'v{vol}-{o}#{i}', (c.get('provenance') or {}).get('page_start'),
                    f'v{h[0]}-{h[1]}#{h[2]}' if h else '', ('' if not h else 'paired' if h in paired else 'not_on_site'),
                    d['catalog_citation'] or '', c['catalog_citation'] or '', site_only[:80], v2_only[:80]])
        if verdict in V2_RIGHT:
            ids.append((d['id'], vol, o, i))
    out.sort(key=lambda r: (r[0], r[1]))
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write('verdict\tid\tv2\tpage\thost\thost_on_site\tsite_citation\tv2_citation\tsite_only\tv2_only\n')
        for r in out:
            fh.write('\t'.join(map(str, r)) + '\n')
    if args.ids:
        with open(args.ids, 'w', encoding='utf-8') as fh:
            for r in sorted(ids):
                fh.write('\t'.join(map(str, r)) + '\n')
    print(collections.Counter(r[0] for r in out), file=sys.stderr)


if __name__ == '__main__':
    main()
