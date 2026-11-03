#!/usr/bin/env python3
"""Works whose head on the site is still the text the OCR lost (fahares step 14.19).

The OCR dropped the top of about 180 pages; their text came back from the page images (commit 100db7f, fahares step
13.60) and the copies it held were added to the site (step 13.106). The site's works kept the columns v1 read from
the old text: an entry whose author line, description, print or bibliography had been lost has none on the site,
and its «متن مأخذ» (raw_text) lacks them. Where a copy's heading was lost too, the work took that copy's incipit
and citation as its own («تفسیر چرخی», vol 8 p. 682).

A work is taken when a line of its head in the text today (after its title and transliteration, up to its first
copy) is not on the site's raw_text (similarity 0.8 at most against every line). Its site work is the one of the
same title in the volume, the closest by text inside a run of one title («ساقی نامه», vol 17), else the work the
title alignment of v1 and v2 gives. The work is left when the pair is in doubt: the site's header line is another
(similarity under 0.9, «کیمیا / فارسی» for «كيميا / ترکی»), the site names another author («شرح زبدة الاصول», vol
19, where v2 has two works the site lacks), or a lost line is a copy's («شماره نسخه»). The decision file sets, for `fahares:add-corpus-works` (work_updates):

- raw_text: the head in the text today, page tags kept as v1 kept them, when the site still holds v1's raw_text;
- author_name, description, print_info, bibliography, incipit_text, explicit_text, composition_date_raw,
  dedication, related_work: v2's
  value, only when the site still holds v1's value and that value is empty or v2's value comes from a lost line
  (a dedication only where the site has none); emptied where v2 has none and no line of the site's value is in
  the head (v1 took it from the next entry).

A column with a reviewed correction (audit `verify`) is left out. The command checks again that the site holds
each `from` value.

Usage: fankha_lost_heads_export.py --out FILE [--db fahares_prod] [--volumes 1 2 …] [--report FILE]
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_v2_db_compare import ROOT, PAGE_TAG, align, load_json, norm, query  # noqa: E402

FIELDS = {
    'author_name': (lambda w: (w['author'] or {}).get('name'), 'author_name'),
    'description': (lambda w: w['description'], 'description'),
    'print_info': (lambda w: w['print_info'], 'print_info'),
    'bibliography': (lambda w: w['bibliography'] or None, 'bibliography'),
    'incipit_text': (lambda w: w['incipit'], 'incipit'),
    'explicit_text': (lambda w: w['explicit'], 'explicit'),
    'composition_date_raw': (lambda w: (w['composition'] or {}).get('date'), 'composition_date'),
    'dedication': (lambda w: w['dedication'], 'dedication'),
    'related_work': (lambda w: w['related_work'], 'related_work'),
}
SIMILAR = 0.8
RUN_MATCH = 0.6
SAME_HEADER = 0.9
COPY_LINE = re.compile(r'شماره نسخه')
CLEARABLE = ('description', 'print_info', 'incipit_text', 'explicit_text', 'composition_date_raw', 'dedication', 'related_work')


def lines_of(text):
    return [norm(x) for x in (text or '').split('\n') if norm(x)]


def similar(a, b):
    return SequenceMatcher(None, a, b, autojunk=False).ratio() > SIMILAR


def empty(v):
    return v is None or v == '' or v == []


def same(a, b):
    if empty(a) and empty(b):
        return True
    if isinstance(a, list) or isinstance(b, list):
        return [norm(x) for x in (a or [])] == [norm(x) for x in (b or [])]
    return norm(str(a)) == norm(str(b))


def from_lost(value, lost):
    """v2's value comes from a lost line: one of its parts is (nearly) in one."""
    parts = value if isinstance(value, list) else [value]
    return any(norm(p) and any(norm(p)[:60] in x or similar(norm(p)[:len(x)], x) for x in lost) for p in parts)


def site_works(db, vol):
    cols = ', '.join(f"'{c}', {c}" for c in list(FIELDS) + ['raw_text', 'primary_title'])
    out = {}
    for r in query(db, f"SELECT JSON_OBJECT('id', id, 'slug', slug, {cols}) FROM works WHERE volume_number = {vol}"):
        m = re.search(r'-v(\d+)-(\d+)$', r['slug'])
        if m and int(m.group(1)) == vol:
            if isinstance(r['bibliography'], str):
                r['bibliography'] = json.loads(r['bibliography'])
            out[int(m.group(2))] = r
    return out


def protected_columns(db):
    prot = defaultdict(set)
    for r in query(db, "SELECT JSON_OBJECT('id', auditable_id, 'v', new_values) FROM audit_logs "
                       "WHERE action = 'verify' AND auditable_type = 'App\\\\Models\\\\Work'"):
        vals = json.loads(r['v']) if isinstance(r['v'], str) else (r['v'] or {})
        prot[r['id']].update(vals)
    return prot


def volume(db, vol, prot):
    text = open(os.path.join(ROOT, 'text', 'fankha', f'fankha_vol_{vol:02d}.txt'), encoding='utf-8').read().split('\n')
    v2, v1 = load_json('fankha_v2', vol), load_json('fankha', vol)
    by_v2 = align(v2, v1)
    site = site_works(db, vol)
    by_title = defaultdict(list)
    for ordinal, s in site.items():
        by_title[norm(s['primary_title'] or '')].append(ordinal)
    updates, report, used = [], [], set()
    for w in v2:
        p = w['provenance']
        end = w['copies'][0]['provenance']['line_start'] - 1 if w['copies'] else p['line_end']
        head = '\n'.join(text[p['line_start'] - 1:end]).strip()
        hlines = lines_of(head)
        titled = by_title.get(norm(w['title_line']), [])
        if len(titled) == 1:
            ordinal = titled[0]
        elif titled:
            # a run of one title: the closest text, and none when no site work is close (a work the site lacks)
            key = ' '.join(hlines)[:600]
            score = {o: SequenceMatcher(None, key, ' '.join(lines_of(site[o]['raw_text']))[:600], autojunk=False).ratio()
                     for o in titled if o not in used}
            ordinal = max(score, key=score.get) if score else None
            if ordinal is None or score[ordinal] < RUN_MATCH:
                continue
        else:
            ordinal = by_v2.get(w['key']['ordinal'])
        s = site.get(ordinal)
        if not s or ordinal > len(v1):
            continue
        used.add(ordinal)
        slines = lines_of(s['raw_text'])
        lost = [x for x in hlines[2:] if len(x) >= 10 and not any(similar(x, y) for y in slines)]
        if not lost:
            continue
        label = f"v{vol}-{w['key']['ordinal']} «{w['title']}»"
        author = (w['author'] or {}).get('name')
        # another entry of the same title (a work the site lacks, or the site's run is in another order), or a copy's
        # lines that v2 reads into the head: the work is left
        if not slines or SequenceMatcher(None, hlines[0], slines[0], autojunk=False).ratio() < SAME_HEADER:
            why = 'another header on the site'
        elif s['author_name'] and author and norm(s['author_name']) != norm(author):
            why = 'another author on the site'
        elif any(COPY_LINE.search(x) for x in lost):
            why = 'a copy line in the head'
        else:
            why = None
        if why:
            report.append({'id': s['id'], 'slug': s['slug'], 'label': label, 'lost': lost, 'fields': [], 'kept': [], 'left': why})
            continue
        old = v1[ordinal - 1]
        changes, kept = {}, []
        if same(s['raw_text'], old['raw_text']) and 'raw_text' not in prot[s['id']]:
            changes['raw_text'] = {'from': s['raw_text'], 'to': head}
        for field, (get, v1_field) in FIELDS.items():
            new, cur = get(w), s[field]
            if same(cur, new):
                continue
            if empty(new):
                # what v1 read from the next entry where the lost text joined the two («دیوان عبدالرزاق کاشی», vol
                # 15: its description was «دیوان عبدالعلی شاه»'s header): text the head today does not hold goes
                if field in CLEARABLE and isinstance(cur, str) and not any(similar(x, y) for x in lines_of(cur) for y in hlines) \
                        and same(cur, old.get(v1_field)) and field not in prot[s['id']]:
                    changes[field] = {'from': cur, 'to': None}
                continue
            if field in prot[s['id']]:
                kept.append(f'{field}: reviewed correction')
            elif not same(cur, old.get(v1_field)):
                kept.append(f'{field}: edited on the site')
            elif field == 'dedication' and not empty(cur):
                # a longer dedication is the rest of the entry's text («سفرنامه آب گرم قفقاز», vol 18), not more people
                kept.append(f'{field}: the site has one')
            elif not empty(cur) and not from_lost(new, lost):
                kept.append(f'{field}: not from a lost line')
            else:
                changes[field] = {'from': cur, 'to': new}
        report.append({'id': s['id'], 'slug': s['slug'], 'label': label, 'lost': lost,
                       'fields': sorted(changes), 'kept': kept, 'left': None})
        if changes:
            death = ((w['author'] or {}).get('death') or {})
            updates.append({'work_slug': s['slug'], 'v2': f"v{vol}-{w['key']['ordinal']}", 'id': s['id'],
                            'changes': changes,
                            'author': {'name': w['author']['name'], 'century': death['century']}
                            if 'author_name' in changes and death.get('century') else None})
    return updates, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--report')
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--volumes', type=int, nargs='*', default=list(range(1, 35)))
    args = ap.parse_args()
    prot = protected_columns(args.db)
    updates, report = [], []
    for vol in args.volumes:
        u, r = volume(args.db, vol, prot)
        updates += u
        report += r
        print(f'vol {vol:2d}: {len(r)} works with lost lines, {len(u)} updates', file=sys.stderr)
    out = {'source': f'Fankha text today against the site ({args.db}), {date.today()}; works whose head the OCR '
                     f'lost (fahares step 14.19)',
           'category': 'lost_head', 'works': [], 'fills': [], 'work_updates': updates}
    json.dump(out, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if args.report:
        json.dump(report, open(args.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(updates)} works to update, {len(report)} with lost lines', file=sys.stderr)


if __name__ == '__main__':
    main()
