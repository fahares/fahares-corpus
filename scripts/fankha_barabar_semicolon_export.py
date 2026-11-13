#!/usr/bin/env python3
"""A copy's incipit «برابر؛ …» (fahares step 14.162), the incipit «برابر» with what Fankha puts after its «؛»:
- «آغاز و انجام: برابر؛ X» in Fankha's text (the corrected text/fankha files): both are the work's, and X is what
  follows the explicit (a colophon, the copy's last lines). The explicit column already holds «برابر؛ X» (or, when
  empty, is given it); the incipit becomes «برابر».
- «آغاز: برابر؛ انجام X» (the explicit's label without its colon): the incipit becomes «برابر» and an empty explicit
  takes X.
Left out: «آغاز: برابر؛ X» with no «انجام» (X then belongs to the incipit: a translation's own opening, a verse),
a «both» copy whose line in the text is not «آغاز و انجام: برابر؛ X», and a copy whose metadata list differs.
Output: a fahares:rebuild-copies file.
"""
import argparse
import glob
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_v2_fill_columns_export import letters  # noqa: E402
from fankha_v2_ie_tail_export import q  # noqa: E402

BAR = 'برابر'
HEAD = re.compile(r'^برابر ?؛ ?')
BOTH = re.compile(r'آغاز\s*و\s*انجام[:\s]\s*برابر')
ANJAM = re.compile(r'^انجام(?![\w‌])[ :]*(?P<exp>.+)$', re.S)


def set_item(meta, key, old, new):
    """metadata's list item holding the column's value takes the new one; False when the list does not match."""
    lst = meta.get(key) or []
    hit = [i for i, e in enumerate(lst) if isinstance(e, dict) and (e.get('text') or '') == (old or '')]
    if hit:
        lst[hit[0]]['text'] = new
        return True
    if not lst:
        meta[key] = [{'label': None, 'text': new}]
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.162')
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    lines = [l for f in sorted(glob.glob(str(root / 'text' / 'fankha' / '*.txt')))
             for l in open(f, encoding='utf-8') if 'برابر' in l and 'آغاز' in l]
    rows = q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'incipit_text', incipit_text, 'explicit_text', explicit_text, "
                      "'metadata', metadata, 'raw', raw_text) from manuscripts where incipit_text regexp '^برابر ?؛ ?.'")
    out, counts = [], Counter()
    for s in rows:
        inc, exp = s['incipit_text'], (s['explicit_text'] or '').strip()
        tail = HEAD.sub('', inc).strip()
        meta = json.loads(s['metadata']) if isinstance(s['metadata'], str) else (s['metadata'] or {})
        new = json.loads(json.dumps(meta))
        new_exp = None
        if BOTH.search(s['raw']):
            key = tail[:30]
            hits = [l for l in lines if key in l]
            if not hits or not re.search(r'آغاز\s*و\s*انجام[:\s]\s*برابر ?؛ ?$', hits[0][:hits[0].index(key)]):
                counts['both, the text says otherwise'] += 1
                continue
            if not exp:
                new_exp = inc.strip()
            elif exp != inc.strip():
                counts['both, an explicit of its own'] += 1
                continue
            kind = 'both'
        elif m := ANJAM.match(tail):
            if exp and letters(exp) != letters(m['exp']):
                counts['anjam, an explicit of its own'] += 1
                continue
            new_exp = None if exp else m['exp'].strip()
            kind = 'anjam'
        else:
            counts['left: the tail belongs to the incipit'] += 1
            continue
        if not set_item(new, 'incipits', inc, BAR) or (new_exp is not None and not set_item(new, 'explicits', s['explicit_text'], new_exp)):
            counts['metadata list differs'] += 1
            continue
        changes = {'incipit_text': {'from': inc, 'to': BAR}}
        if new_exp is not None:
            changes['explicit_text'] = {'from': s['explicit_text'], 'to': new_exp}
        if new != meta:
            changes['metadata'] = {'from': meta, 'to': new}
        out.append({'table': 'manuscripts', 'id': s['id'], 'shelfmark': s['shelfmark'], 'category': 'rebuild', 'v2': None,
                    'kind': kind, 'changes': changes})
        counts[kind] += 1
        counts['explicit set'] += new_exp is not None
    Path(args.out).write_text(json.dumps({'source': f"a copy's incipit «برابر؛ …» (the explicit's or the colophon's text glued on), {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(counts))


if __name__ == '__main__':
    main()
