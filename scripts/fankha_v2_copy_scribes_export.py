#!/usr/bin/env python3
"""The scribes parser v2.6.0 newly reads from a copy's own text, for the site (fahares item 87, step 14.294): the
hands of an album of calligraphy («کا: احمد نیریزی در 1134ق، محمد شفیع حسینی، …»), the scribe of each part
(«… (جزء اول)، … (جزء دوم)»), and the first scribe's name printed in two pieces («رفسنجانی، یوسف (گویا)»).

The copies whose scribes differ between two parser outputs (--before DIR, and json/fankha_v2 now) are matched to the
site's copies by their text. A record gives the first scribe's name before and now (with his note: where he lived,
his date in a list) and the scribes after him, each with a note of his part, his date and the cataloguer's doubt.
Left out: a copy whose text the site holds twice or not at all, and one whose first scribe became another person's
name. Output: a file for `fahares:add-copy-scribes`, which writes only where the copy still has that one scribe.

Usage: fankha_v2_copy_scribes_export.py --before scratch/fankha_v2_250 --out FILE [--step 14.N] [--db fahares_prod]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fankha_v2_db_compare import query, rkey  # noqa: E402
import fankha_parser_v2 as P  # noqa: E402


def note(s):
    """A scribe's part, date and the cataloguer's doubt, as one note."""
    return '، '.join(x for x in (s.get('portion'), s.get('note'), s.get('hedge')) if x) or None


def clean_first(name, remark):
    """The first scribe's own name: his part and date, which v2 leaves in the name, go to his note
    («جزء اول سراج الدین بن احمد شوشتری (جزء اول)», «تا پایان ج 6 به قلم مسیب بن منصور», «… (جزء اول) تا: 1098»)."""
    notes = []
    m = re.match(r'^(تا\s+پایان\s+\S+\s+\S+)\s+به\s+(?:قلم|خط)\s+(.+)$', name)
    if m:
        notes.append(m.group(1))
        name = m.group(2)
    m = re.match(r'^(.+?)\s+(تا\s*:\s*\d.*)$', name)
    if m:
        name, tail = m.group(1), m.group(2)
        notes.append(tail)
    m = re.match(r'^(.*?)\s*\(([^()]*)\)\s*(.*)$', name)
    if m and m.group(1):
        name = (m.group(1) + ' ' + m.group(3)).strip()
        notes.insert(0, m.group(2).strip())
    m = re.match(r'^(' + P.SCRIBE_PART + r')\s*:?\s+(?=\S+\s+\S)', name)
    if m:
        if m.group(1) not in ' '.join(notes):
            notes.insert(0, m.group(1))
        name = name[m.end():]
    out = {'to': name.strip(' ،:')}
    full = '، '.join(dict.fromkeys(x for x in notes + [remark] if x))
    if full:
        out['note'] = full
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.294')
    args = ap.parse_args()
    changed = defaultdict(list)
    for f in sorted(glob.glob(str(ROOT / 'json/fankha_v2/*.json'))):
        now = json.load(open(f, encoding='utf-8'))['works']
        was = json.load(open(os.path.join(args.before, os.path.basename(f)), encoding='utf-8'))['works']
        for wn, wb in zip(now, was):
            for cn, cb in zip(wn['copies'], wb['copies']):
                if cn['scribes'] != cb['scribes'] and cn['scribes']:
                    changed[rkey(cn['raw_text'])].append((cb['scribes'], cn['scribes']))
    site = defaultdict(list)
    for r in query(args.db, "select json_object('id', id, 'raw', raw_text, 'shelfmark', shelfmark) from manuscripts where catalog_id = 1"):
        k = rkey(r['raw'])
        if k in changed:
            site[k].append(r)
    records, counts = [], Counter()
    for k, pairs in changed.items():
        if len(pairs) != 1 or len(site[k]) != 1:
            counts['left: not one copy with this text on the site'] += 1
            continue
        was, now = pairs[0]
        # a copy that had no scribe gets its first («کا نعمت الله بن محمد محسن», the label now marked in the text)
        was = was or [{'name': ''}]
        if len(was) != 1 or not now[0]['name'].startswith(was[0]['name'].split('،')[0]):
            counts['left: the first scribe is another name, or there were several'] += 1
            continue
        first = {'from': was[0]['name'], 'to': now[0]['name']}
        head = dict(now[0])
        dm = P.SCRIBE_DATED.match(head['name']) if len(now) > 1 else None
        if dm and dm.group('d').startswith('در'):          # «درویش در 1182ق، محمدهاشم …»: the first hand's date, as the others'
            first['to'], head['note'] = dm.group('n').strip(), '، '.join(x for x in (dm.group('d').strip(), head.get('note')) if x)
        if note(head):
            first['note'] = note(head)
        # «…، نستعلیق محمد زاده از طایفه بای بقا در»: a sentence cut off, not a name
        scribes = [{k2: v for k2, v in (('name', s['name']), ('note', note(s))) if v} for s in now[1:]
                   if not re.search(r'طایفه|\sدر$', s['name'])]
        first.update(clean_first(first['to'], first.get('note')))
        if 'note' in first:
            first['note'] = first['note'].replace(':،', '،').rstrip(' :')
        # a first name that still holds a part, a date or a second hand is left for a reviewer
        if first['to'].startswith('=') or re.search(r'\d|:|به\s+خط|ندارد', first['to']) or (not scribes and first['to'] == first['from'] and 'note' not in first):
            counts['left: no scribe to add, or a first name that is not a name alone'] += 1
            continue
        records.append({'id': site[k][0]['id'], 'shelfmark': site[k][0]['shelfmark'], 'first': first, 'scribes': scribes})
        counts['copies'] += 1
        counts['scribes added'] += len(scribes)
        counts['first scribe: a fuller name'] += first['from'] != first['to']
        counts['first scribe: a note'] += 'note' in first
    records.sort(key=lambda r: r['id'])
    src = f"scribes parser v2.6.0 newly reads (before: {args.before}), {date.today()}; fahares step {args.step}"
    json.dump({'source': src, 'records': records}, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(dict(counts), file=sys.stderr)


if __name__ == '__main__':
    main()
