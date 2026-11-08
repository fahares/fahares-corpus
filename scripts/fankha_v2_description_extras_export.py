#!/usr/bin/env python3
"""Lines a work's description on the site still carries that belong to another column (fahares item 87, step 14.98).

The v1 parser left labelled lines inside the description: the incipit and explicit at its end («آغاز کتاب: …»,
«انجام کتاب: …»), an empty «غیر همانند:» label, a «[source page]» citation, and at its head a transliteration, the
author line or «تاریخ تالیف: …؛ محل تالیف: …». v2 reads them into their own columns. A line is taken out of the
description only where its column already holds it, or where the column is empty on the site and v2 fills it with
the same text (the column then takes v2's value); and only where what is left is v2's description, letter for letter.

Input: the trimmed and trimmed_inner Work/description rows of a fankha_v2_db_compare.py report.
Output: work_updates for fahares:add-corpus-works.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_v2_fill_columns_export import letters, norm, site, tight  # noqa: E402
from fankha_v2_leading_author_export import bare  # noqa: E402

FIELDS = ['description', 'incipit_text', 'explicit_text', 'bibliography', 'composition_date_raw', 'composition_place',
          'author_name']
INCIPIT = re.compile(r'^\s*آغاز\s*(?:کتاب|\d+)?\s*:\s*(.*)$')
EXPLICIT = re.compile(r'^\s*انجام\s*(?:کتاب|\d+)?\s*:\s*(.*)$')
LATIN = re.compile(r'^[^؀-ۿ]*[a-zA-Zāīūšḥṣṭẓ][^؀-ۿ]*$')
DATE = re.compile(r'^تاریخ تالیف\s*:\s*([^؛]*?)\s*(?:؛\s*محل تالیف\s*:\s*(.*))?$')


def within(part, column):
    if isinstance(column, list):
        column = '\n'.join(column)
    return len(letters(part)) >= 3 and letters(part) in letters(column)


class Line:
    """Whether one description line is held by another column; `fill` names the column v2 fills from it."""

    def __init__(self, text, work, v2, where):
        self.kind, self.fill = None, {}
        s = text.strip()
        if not s:
            self.kind = 'blank'
            return
        m = INCIPIT.match(s)
        if m:
            self.column('incipit', 'incipit_text', re.sub(r'^\s*آغاز\s*\d*\s*:\s*', '', m.group(1)), work, v2)
            return
        m = EXPLICIT.match(s)
        if m:
            self.column('explicit', 'explicit_text', m.group(1), work, v2)
            return
        if re.fullmatch(r'غیر\s*همانند\s*:?', s):
            self.kind = 'empty_label'
        elif re.fullmatch(r'\[[^\]]+\]', s):
            self.column('citation', 'bibliography', s.strip('[]'), work, v2)
        elif where == 'head' and LATIN.match(s):
            self.kind = 'transliteration'
        elif where == 'head' and (m := DATE.match(s)):
            if not work['composition_date_raw'] or tight(m.group(1)) != tight(work['composition_date_raw']):
                return
            if m.group(2):
                self.column('date', 'composition_place', m.group(2), work, v2)
            else:
                self.kind = 'date'
        elif where == 'head' and work['author_name'] and key(bare(s)) == key(work['author_name']):
            self.kind = 'author'

    def column(self, kind, field, part, work, v2):
        if within(part, work[field]):
            self.kind = kind
        elif not work[field] and field in v2 and within(part, v2[field]):
            self.kind, self.fill = kind + '_moved', {field: v2[field]}


def key(t):
    return norm(t).replace(' ', '').replace('،', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True, help='a fankha_v2_db_compare.py report directory')
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.98')
    args = ap.parse_args()
    rows, v2 = [], {}
    for d in map(json.loads, open(Path(args.report) / 'diffs.jsonl', encoding='utf-8')):
        if d['table'] != 'Work' or d['protected']:
            continue
        if d['field'] == 'description' and d['category'] in ('trimmed', 'trimmed_inner'):
            rows.append(d)
        elif d['field'] in FIELDS and d['category'] == 'filled':
            v2.setdefault(int(d['id']), {})[d['field']] = d['v2']
    works = site(args.db, 'works', [int(r['id']) for r in rows], FIELDS)
    for w in works.values():
        if w['bibliography']:
            w['bibliography'] = json.loads(w['bibliography'])
    updates, counts, kinds = [], Counter(), Counter()
    for r in rows:
        rid = int(r['id'])
        w = works[rid]
        if w['description'] != r['db']:
            counts['changed_since_report'] += 1
            continue
        lines, target = w['description'].split('\n'), letters(r['v2'])
        head, tail, taken, fill = 0, len(lines), [], {}
        for where in ('tail', 'head'):
            while head < tail and letters('\n'.join(lines[head:tail])) != target:
                line = Line(lines[tail - 1 if where == 'tail' else head], w, v2.get(rid, {}), where)
                if not line.kind:
                    break
                taken.append(line.kind)
                fill.update(line.fill)
                if where == 'tail':
                    tail -= 1
                else:
                    head += 1
        rest = '\n'.join(lines[head:tail]).strip('\n')
        if not taken or letters(rest) != target:
            counts['kept'] += 1
            continue
        counts['ok'] += 1
        kinds.update(set(taken))
        changes = {'description': {'from': w['description'], 'to': rest or None}}
        for field, value in fill.items():
            changes[field] = {'from': w[field], 'to': value}
        updates.append({'work_slug': w['key'], 'v2': r['label'].split(' ')[0], 'id': rid, 'changes': changes, 'author': None})
    out = {
        'source': ("lines left in a work's description that belong to another column (incipit, explicit, an empty "
                   "«غیر همانند:», a citation, a transliteration, the author line, the date and place of composition), "
                   "taken out where that column holds them or v2 fills it with them, and only where what is left is "
                   f"v2's description ({args.report}), {date.today()}; fahares step {args.step}"),
        'category': 'description_extras', 'works': [], 'fills': [], 'work_updates': updates,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(dict(counts), dict(kinds.most_common()), Counter(f for u in updates for f in u['changes'] if f != 'description'))


if __name__ == '__main__':
    main()
