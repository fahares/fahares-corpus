#!/usr/bin/env python3
"""The descriptions steps 14.98 and 14.118 left, third round (fahares item 87, step 14.223): the rows of the comparison
report where v2 has no description at all ("emptied"), besides the trimmed ones. The rules are step 14.118's
(fankha_v2_description_extras2_export.py), with these more:
- a label with nothing after it also in the forms «نامعلوم:», «همانندی نامعلوم», «احتمالاً غیرهمانند»;
- a line that is only a citation in brackets, held by the work's bibliography (or filled from v2 where empty);
- «آغاز کتاب: …» / «انجام کتاب: …» where the work's incipit or explicit is empty and v2 fills it with that text;
- «تاریخ تالیف: …» where the date column is empty and v2 fills it with that text.
A line in Latin letters that is a title in its own language, not a transliteration, stays.
As before a line is taken out only when its column holds it or takes it from v2, and only where what is left is
v2's description, letter for letter (here mostly: nothing).

Input: a fankha_v2_db_compare.py report, v2's json. Output: work_updates for fahares:add-corpus-works.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_v2_fill_columns_export import letters, norm, site, tight  # noqa: E402
from fankha_v2_leading_author_export import bare  # noqa: E402
from fankha_v2_author_from_description_export import v2_works  # noqa: E402

FIELDS = ['description', 'incipit_text', 'explicit_text', 'composition_date_raw', 'composition_place', 'author_name',
          'bibliography', 'related_work', 'dedication']
EXCERPT = re.compile(r'^(?:آغاز|انجام|جلد|\d+\s*:)')
LABEL = re.compile(r'^(?:(?:آغاز|انجام)(?:\s*و\s*انجام)?\s*(?:کتاب)?\s*\d*\s*:?\s*)?(?:(?:آغاز|انجام)\s*\d*\s*:\s*)?'
                   r'(?:جلد\s*\S+?\s*:|\d+\s*:)?\s*')
DATE = re.compile(r'^تاریخ ت[اأ]لیف\s*:\s*([^؛،]*?)\s*(?:[؛،]\s*محل ت[اأ]لیف\s*:\s*(.*?))?\s*؛?\s*$')
LATIN = re.compile(r'^[^؀-ۿ]*[a-zA-Zāīūšḥṣṭẓ‘][^؀-ۿ]*$')
EMPTY = re.compile(r'^(?:(?:ظاهرا|ظاهراً|احتمالاً|احتمالا)?\s*غیر\s*همانند|همانندی\s+نامعلوم|نامعلوم|ناشناس|ناشناخته|شرح و حواشی)\s*:?$')
CITE_LINE = re.compile(r'^\[([^\[\]]+)\]\.?$')
RELATED = re.compile(r'^وابسته به\s*:\s*(.+)$')
DEDICATION = re.compile(r'^(?:به دستور|به نام|به درخواست|اهداء به|تقدیم به)\s*:\s*(.+)$')
CITED = re.compile(r'^(.*?\S)\s*\[([^\]]+)\]\s*$')


def key(t):
    return norm(t or '').replace(' ', '').replace('،', '')


def excerpts(db, ids):
    q = ("select owner_id, text from text_excerpts where owner_type='App\\\\Models\\\\Work' and owner_id in (%s)"
         % ','.join(map(str, ids)))
    out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                          f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -N -B {db}'],
                         input=q, capture_output=True, text=True, check=True).stdout
    held = {}
    for line in out.splitlines():
        i, t = line.split('\t', 1)
        held.setdefault(int(i), []).append(t.replace('\\n', '\n'))
    return held


def within(part, column):
    if isinstance(column, list):
        column = '\n'.join(column)
    return len(letters(part)) >= 3 and letters(part) in letters(column or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True, help='a fankha_v2_db_compare.py report directory')
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--v2', default='json/fankha_v2')
    ap.add_argument('--step', default='14.223')
    args = ap.parse_args()
    rows, filled = [], {}
    for d in map(json.loads, open(Path(args.report) / 'diffs.jsonl', encoding='utf-8')):
        if d['table'] != 'Work' or d['protected']:
            continue
        if d['field'] == 'description' and d['category'] in ('trimmed', 'trimmed_inner', 'emptied'):
            rows.append(d)
        elif d['category'] == 'filled':
            filled.setdefault(int(d['id']), {})[d['field']] = d['v2']
    works = site(args.db, 'works', [int(r['id']) for r in rows], FIELDS)
    for w in works.values():
        if w['bibliography']:
            w['bibliography'] = json.loads(w['bibliography'])
    held, v2 = excerpts(args.db, list(works)), v2_works(args.v2)
    updates, counts, kinds = [], Counter(), Counter()
    for r in rows:
        rid = int(r['id'])
        w, f = works[rid], filled.get(rid, {})
        if w['description'] != r['db']:
            counts['changed_since_report'] += 1
            continue
        target = letters(r['v2'] or '')
        if letters(w['description']) == target:
            counts['already'] += 1
            continue
        pool = '\n'.join([w['incipit_text'] or '', w['explicit_text'] or ''] + held.get(rid, []))
        a2 = (v2.get('-' + r['label'].split(' ')[0]) or {}).get('author') or {}
        keep, taken, fill = [], [], {}
        for line in w['description'].split('\n'):
            s, kind = line.strip(), None
            if len(letters(s)) > 2 and letters(s) in target:
                keep.append(line)
                continue
            if not s:
                kind = 'blank'
            elif m := DATE.match(s):
                place = m.group(2)
                if not w['composition_date_raw'] and f.get('composition_date_raw') and tight(m.group(1)) == tight(f['composition_date_raw']) \
                        and (not place or within(place, w['composition_place']) or (not w['composition_place'] and within(place, f.get('composition_place')))):
                    kind, fill['composition_date_raw'] = 'date_moved', f['composition_date_raw']
                    if place and not w['composition_place']:
                        fill['composition_place'] = f['composition_place']
                elif w['composition_date_raw'] and tight(m.group(1)) == tight(w['composition_date_raw']):
                    if not place or within(place, w['composition_place']):
                        kind = 'date'
                    elif not w['composition_place'] and within(place, f.get('composition_place')):
                        kind, fill['composition_place'] = 'place_moved', f['composition_place']
            elif EMPTY.match(s):
                kind = 'empty_label'
            elif m := CITE_LINE.match(s):
                if within(m.group(1), w['bibliography']):
                    kind = 'citation_line'
                elif not w['bibliography'] and within(m.group(1), f.get('bibliography')):
                    kind, fill['bibliography'] = 'citation_line_moved', f['bibliography']
            elif LATIN.match(s):
                # a title in its own language («Travels in Beloochistan and Sinde, …») is no transliteration and stays
                if not (len(s.split()) >= 4 and not re.search(r"[āīūšḥṣṭẓḏġčžʻ‘]", s)):
                    kind = 'transliteration'
            elif m := RELATED.match(s):
                if within(m.group(1), w['related_work']):
                    kind = 'related'
                elif not w['related_work'] and within(m.group(1), f.get('related_work')):
                    kind, fill['related_work'] = 'related_moved', f['related_work']
            elif m := DEDICATION.match(s):
                if within(m.group(1), w['dedication']):
                    kind = 'dedication'
                elif not w['dedication'] and within(m.group(1), f.get('dedication')):
                    kind, fill['dedication'] = 'dedication_moved', f['dedication']
            elif EXCERPT.match(s):
                body = LABEL.sub('', s, count=1)
                col = 'explicit_text' if s.startswith('انجام') else 'incipit_text'
                if within(body, pool):
                    kind = 'excerpt'
                elif not w[col] and col not in fill and f.get(col) and letters(body) == letters(f[col]):
                    kind, fill[col] = 'excerpt_moved', f[col]
            elif (m := CITED.match(s)) and letters(m.group(1)) in target:
                if within(m.group(2), w['bibliography']):
                    keep.append(line[:line.rindex('[')].rstrip())
                    taken.append('citation')
                    continue
                if not w['bibliography'] and within(m.group(2), f.get('bibliography')):
                    keep.append(line[:line.rindex('[')].rstrip())
                    taken.append('citation_moved')
                    fill['bibliography'] = f['bibliography']
                    continue
            elif (w['author_name'] and key(bare(s)) == key(w['author_name'])):
                kind = 'author'
            elif (not w['author_name'] and a2.get('name') and not a2.get('hedge') and '؟' not in bare(s)
                  and key(bare(s)) in (key(a2['name']), key(a2.get('name_raw')))):
                # the name as the line gives it: v2 reads a given name after the comma as an epithet («اموی، امام الدین یوسف»)
                kind, fill['author_name'] = 'author_moved', a2.get('name_raw') or a2['name']
            if not kind:
                keep.append(line)
                continue
            taken.append(kind)
        rest = '\n'.join(keep).strip('\n')
        if not taken or letters(rest) != target:
            counts['kept'] += 1
            continue
        counts['ok'] += 1
        kinds.update(set(taken))
        changes = {'description': {'from': w['description'], 'to': rest or None}}
        for field, value in fill.items():
            changes[field] = {'from': w[field], 'to': value}
        death = a2.get('death') or {}
        author = ({'name': fill['author_name'], 'century': death['century']}
                  if 'author_name' in fill and death.get('century') else None)
        updates.append({'work_slug': w['key'], 'v2': r['label'].split(' ')[0], 'id': rid, 'changes': changes,
                        'author': author})
    out = {
        'source': ("lines of other columns left in a work's description that step 14.98 did not read (numbered "
                   "incipits and explicits held in text_excerpts, the place of composition with «تألیف», the author "
                   "line, «وابسته به», a dedication, a citation at a line's end, an empty label), taken out where "
                   "their column holds them or v2 fills it with them, and only where what is left is v2's description "
                   f"({args.report}), {date.today()}; fahares step {args.step}"),
        'category': 'description_extras', 'works': [], 'fills': [], 'work_updates': updates,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(dict(counts), dict(kinds.most_common()), Counter(f for u in updates for f in u['changes'] if f != 'description'))


if __name__ == '__main__':
    main()
