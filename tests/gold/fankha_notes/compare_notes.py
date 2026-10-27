#!/usr/bin/env python3
"""Accuracy of parser v2's note handling against the note gold set (fahares item 87).

A gold `continuation_of` unit is right when its text is no longer a standalone note of the copy and sits inside
one of the copy's fields; a typed unit is right when the note holding its text has the gold main type."""
import json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')


def norm(s): return re.sub(r'\s+', ' ', (s or '').replace('ي', 'ی').replace('ك', 'ک').replace('ى', 'ی').replace('‌', '')).strip(' ،؛.')


def main():
    units = {json.loads(l)['uid']: json.loads(l) for l in open(os.path.join(HERE, 'units.jsonl'))}
    gold = [json.loads(l) for l in open(os.path.join(HERE, 'gold.jsonl'))]
    vols, res, conf, bad = {}, Counter(), Counter(), []
    for g in gold:
        m = re.match(r'v(\d+)w(\d+)c(\d+)n\d+', g['uid'])
        v, wo, co = map(int, m.groups())
        if v not in vols:
            vols[v] = json.load(open(os.path.join(ROOT, 'json', 'fankha_v2', f'fankha_vol_{v:02d}.json')))
        cp = vols[v]['works'][wo - 1]['copies'][co - 1]
        t = norm(units[g['uid']]['note'])
        notes = [n for n in cp['notes'] if t and (t in norm(n['text']) or norm(n['text']) in t and len(norm(n['text'])) > 3)]
        if g.get('continuation_of'):
            rest = {k: x for k, x in cp.items() if k not in ('notes', 'raw_text')}
            ok = not notes and t[:25] in norm(json.dumps(rest, ensure_ascii=False))
            res['continuation', ok] += 1
            if not ok: bad.append((g['uid'], 'cont:' + g['continuation_of'], [n['type'] for n in notes], t[:70]))
        else:
            got = notes[0]['type'] if notes else 'MISSING'
            FIELD = {'acquisition': 'acquisition', 'endowment': 'donor', 'ownership': 'ownership', 'seal': 'seals'}
            if not notes:                       # moved into a provenance field of its own
                for typ, f in FIELD.items():
                    if t[:25] in norm(json.dumps(cp.get(f), ensure_ascii=False)):
                        got = typ
                        break
            ok = got == g['type']
            res['type', ok] += 1
            conf[(g['type'], got)] += 1
            if not ok: bad.append((g['uid'], g['type'], got, t[:70]))
            if notes:
                res['by_author', bool(notes[0].get('by_author')) == bool(g.get('by_author'))] += 1
    for k in ('continuation', 'type', 'by_author'):
        a, b = res[k, True], res[k, True] + res[k, False]
        print(f'{k:14} {a}/{b} {100 * a / max(b, 1):.1f}%')
    if '-v' in sys.argv:
        for x in bad: print(' ', *x)


if __name__ == '__main__':
    main()
