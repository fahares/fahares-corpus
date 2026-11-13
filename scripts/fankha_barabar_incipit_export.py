#!/usr/bin/env python3
"""A copy's incipit that is «برابر» (as the work's) glued to what follows it (fahares step 14.161). The site shows a bare
«برابر» as «منطبق بر آغاز اثر», but not these:
- «و انجام: برابر» (Fankha: «آغاز و انجام: برابر», cut after «آغاز»): incipit and explicit both «برابر»;
- «برابرانجام: …» / «برابر انجام: …» (the explicit glued on, which the explicit column already has): incipit «برابر»;
- «برابر خط: …» / «برابر بی‌کا، …» (the description's fields, which their own columns have): incipit «برابر»;
- «برابر کامل» / «برابر از اول تا آخر» / «برابر نام مؤلف …» (a remark): incipit «برابر»;
  with these two, an explicit holding the same value («آغاز و انجام: برابر …») becomes «برابر» too.
What the incipit loses and metadata does not hold (a remark, the rest of a glued explicit) becomes an editorial note.
Left out: «برابر جلد 1», «برابر 2», «برابر، 2. (ص…)» (a pointer the site reads), and a value that fits no rule.
Output: a fahares:rebuild-copies file.
"""
import argparse
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
VA_ANJAM = re.compile(r'^و ?انجام[: ]+برابر[ .]*(?:\n(?P<note>.+))?$', re.S)
ANJAM = re.compile(r'^برابر ?[؛.،]? ?انجام ?: ?(?P<exp>[^\n]*)(?:\n(?P<note>.+))?$', re.S)
FIELD = re.compile(r'^برابر[ ؛،.]*(?:خط ?:|کا ?:|بی‌کا|بی‌تا|تا ?:)')
REMARK = re.compile(r'^برابر[ ؛،.]*(?P<note>(?:کامل|از |همان|نام ).*)$', re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.161')
    args = ap.parse_args()
    rows = q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'incipit_text', incipit_text, 'explicit_text', explicit_text, "
                      "'metadata', metadata) from manuscripts where incipit_text like 'برابر%' or incipit_text regexp '^و ?انجام[: ]+برابر'")
    out, counts = [], Counter()
    for s in rows:
        inc, exp = s['incipit_text'], s['explicit_text'] or ''
        meta = json.loads(s['metadata']) if isinstance(s['metadata'], str) else (s['metadata'] or {})
        new_exp, note = None, None
        if m := VA_ANJAM.match(inc):
            kind, note = 'va-anjam', m['note']
            if not exp.strip():
                new_exp = BAR
            elif exp.strip() != BAR:
                counts['va-anjam, an explicit of its own'] += 1
                continue
        elif m := ANJAM.match(inc):
            kind, note = 'glued explicit', m['note']
            if not exp.strip():
                new_exp = m['exp'].strip()
            elif not letters(m['exp']).startswith(letters(exp)) and not letters(exp).startswith(letters(m['exp'])):
                counts['glued explicit, the column differs'] += 1
                continue
            elif len(letters(m['exp'])) > len(letters(exp)):
                new_exp = m['exp'].strip()   # the column holds a cut-short copy of it
        elif FIELD.match(inc):
            kind = 'glued fields'
        elif m := REMARK.match(inc):
            kind, note = 'remark', m['note']
        else:
            counts['left: ' + (re.match(r'برابر\s*(\S{0,4})', inc) or [None, '?'])[1] if inc.startswith(BAR) else 'left: other'] += 1
            continue
        if inc.strip() in (BAR, BAR + '.', BAR + '؛'):
            continue
        if kind in ('glued fields', 'remark') and exp.strip() == inc.strip():
            new_exp = BAR   # «آغاز و انجام: برابر …»: the explicit carries the same glued value
        new = json.loads(json.dumps(meta))
        for key, old_val, new_val in (('incipits', inc, BAR), ('explicits', exp, new_exp)):
            if new_val is None:
                continue
            lst = new.get(key) or []
            hit = [i for i, e in enumerate(lst) if isinstance(e, dict) and (e.get('text') or '') == old_val]
            if hit:
                lst[hit[0]]['text'] = new_val
            elif not lst or not old_val:
                new[key] = [{'label': None, 'text': new_val}] + [e for e in lst if letters(e.get('text') or '') != letters(new_val)] if not old_val else [{'label': None, 'text': new_val}]
            else:
                kind = None
                break
        if kind is None:
            counts['metadata list differs'] += 1
            continue
        if note and (note := note.strip(' .؛،:\n')) and letters(note) not in letters(json.dumps(new, ensure_ascii=False)):
            new['editorial_notes'] = (new.get('editorial_notes') or []) + [note]
            counts['note added'] += 1
        changes = {'incipit_text': {'from': inc, 'to': BAR}}
        if new_exp is not None and new_exp != exp:
            changes['explicit_text'] = {'from': s['explicit_text'], 'to': new_exp}
        if new != meta:
            changes['metadata'] = {'from': meta, 'to': new}
        out.append({'table': 'manuscripts', 'id': s['id'], 'shelfmark': s['shelfmark'], 'category': 'rebuild', 'v2': None, 'kind': kind, 'changes': changes})
        counts[kind] += 1
        counts['explicit set'] += 'explicit_text' in changes
    Path(args.out).write_text(json.dumps({'source': f"a copy's incipit «برابر» glued to what follows it, {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(counts))


if __name__ == '__main__':
    main()
