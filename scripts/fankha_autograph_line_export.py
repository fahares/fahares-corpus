#!/usr/bin/env python3
"""A copy's incipit or explicit that carries the next line of Fankha, «کاتب = مؤلف، تا: …؛ …» (fahares item 87,
step 14.171; v2 reads that line as the copy's scribe and date, "dropped" in the comparison report). The incipit or
explicit is cut before the line, in the column and in metadata's list. What the line says goes to its own place
first, where the site does not hold it: the autograph flag (the old parser missed «كاتب» with an Arabic kaf), the
date («تا: …»), «بی‌تا», the place («جا: …»); what follows its first «؛» becomes an editorial note, unless metadata
already holds it.
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

LINE = re.compile(r'\n[ \t]*(?:كاتب|کاتب)\s*=\s*مؤلف[^\n]*$')
KNOWN = re.compile(r'(?:(?:كاتب|کاتب)\s*=|تا\s*:|بی‌تا|جا\s*:|کاغذ\s*:|جلد\s*:|اندازه|قطع|[\d۰-۹]+\s*(?:گ|برگ|ص|سطر))')
FIELDS = {'incipit_text': 'incipits', 'explicit_text': 'explicits'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.171')
    args = ap.parse_args()
    rows = q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'incipit_text', incipit_text, 'explicit_text', explicit_text, "
                      "'is_autograph', is_autograph, 'is_bita', is_bita, 'copy_date_raw', copy_date_raw, 'copy_place', copy_place, "
                      "'metadata', metadata) from manuscripts where incipit_text regexp '\\n[ \\t]*(كاتب|کاتب)[ ]*=[ ]*مؤلف' "
                      "or explicit_text regexp '\\n[ \\t]*(كاتب|کاتب)[ ]*=[ ]*مؤلف'")
    out, counts = [], Counter()
    for s in rows:
        meta = json.loads(s['metadata']) if isinstance(s['metadata'], str) else (s['metadata'] or {})
        new_meta = json.loads(json.dumps(meta))
        changes, line = {}, None
        for f, key in FIELDS.items():
            m = LINE.search(s[f] or '')
            if not m:
                continue
            cut = re.sub(r'[\s؛]+$', '', s[f][:m.start()])   # the quote's own dots («...») stay
            lst = new_meta.get(key) or []
            hit = [i for i, e in enumerate(lst) if isinstance(e, dict) and (e.get('text') or '') == s[f]]
            if hit:
                lst[hit[0]]['text'] = cut
            elif any(letters(m.group(0)) in letters(e.get('text') or '') for e in lst if isinstance(e, dict)):
                # an item holds the line but is not the column's value: left for a look
                counts['metadata list differs'] += 1
                changes = None
                break
            changes[f] = {'from': s[f], 'to': cut}
            line = m.group(0).strip()
        if not changes:
            continue
        head, _, rest = line.partition('؛')
        if not s['is_autograph'] and '(گویا)' not in head and '؟' not in head:
            changes['is_autograph'] = {'from': s['is_autograph'], 'to': 1}
            counts['autograph set'] += 1
        if (d := re.search(r'(?:^|[،\s])تا\s*:\s*([^،؛]+)', head)) and not s['copy_date_raw']:
            changes['copy_date_raw'] = {'from': None, 'to': d.group(1).strip()}
            counts['date set'] += 1
        elif 'بی‌تا' in head and not s['is_bita'] and not s['copy_date_raw']:
            changes['is_bita'] = {'from': s['is_bita'], 'to': 1}
            counts['bita set'] += 1
        if (p := re.search(r'(?:^|[،\s])جا\s*:\s*([^،؛]+)', head)) and not s['copy_place']:
            changes['copy_place'] = {'from': None, 'to': p.group(1).strip()}
            counts['place set'] += 1
        # a part of the line that is no field of the description (a commission, a remark) goes to the note too
        extra = [x.strip() for x in head.split('،')[1:] if x.strip() and not KNOWN.match(x.strip())]
        note = '، '.join(extra + ([rest.strip(' .؛،:\n')] if rest.strip(' .؛،:\n') else []))
        if note and letters(note) not in letters(json.dumps(new_meta, ensure_ascii=False)):
            new_meta['editorial_notes'] = (new_meta.get('editorial_notes') or []) + [note]
            counts['note added'] += 1
        if new_meta != meta:
            changes['metadata'] = {'from': meta, 'to': new_meta}
        out.append({'table': 'manuscripts', 'id': s['id'], 'shelfmark': s['shelfmark'], 'category': 'rebuild', 'v2': None, 'changes': changes})
        counts['copies'] += 1
        for f in FIELDS:
            counts['cut ' + f] += f in changes
    Path(args.out).write_text(json.dumps({'source': f"a copy's incipit or explicit cut before the «کاتب = مؤلف» line glued to it, the line's data to its own columns, {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(counts))


if __name__ == '__main__':
    main()
