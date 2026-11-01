#!/usr/bin/env python3
"""Export reviewed categories of the v2-vs-site comparison as a decision file for `fahares:apply-corpus-categories`.

Usage: fankha_v2_apply_export.py --diffs reports/fankha_v2_db_review2/diffs.jsonl --out FILE CATEGORY ...

Categories (item 87, sample review step 13.65):
  facsimile  manuscripts with «نسخه اصل: …» get is_facsimile = 1 (site still has the v1 value 0)
  print_bib  the bracket of citations glued to the end of «چاپ» leaves print_info, when every citation in it is
             already in the work's bibliography; the command checks that again before writing
  commissioner  a copy's commissioner («حسب الامر میرزا …») that v2 split off the copy date or found elsewhere
             (fahares item 96): the name, for a people row of role patron; the date loses its tail only when the
             tail is that commissioner and nothing else (its phrase and name), so no other text leaves the site.
             The phrase itself is read by the command from the copy's raw text on the site
  copy_date_note  a note on the date («در حیات مؤلف») that v2 split off it: the date loses the tail only when the
             tail is that note
  lines      a copy the site left without a line count gets v2's, only when the copy's own raw text on the site
             names one count («21 سطر») and it is that number; ranges («18 و 21 سطر»), several counts and counts
             the site's text does not hold are left (step 13.132)

Each record names the row by id and by natural key (its work's slug suffix and, for a copy, its shelfmark, as
the site has them in --db, a copy of production: the command then finds a record merged, moved or renumbered since), and each change
by the value the site had in the comparison, so the command writes only where nothing changed since.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date


def site_keys(db, table, ids):
    """The natural key (slug suffix «-v2-856») of each record's work as the site has it: a work's ordinal in v2 can
    differ from the site's after restored works, so the comparison's label is not used."""
    keys = {}
    for i in range(0, len(ids), 2000):
        chunk = ','.join(map(str, ids[i:i + 2000]))
        sql = (f'select m.id, w.slug, m.shelfmark from manuscripts m join works w on w.id = m.work_id where m.id in ({chunk})'
               if table == 'manuscripts' else f'select id, slug, null from works where id in ({chunk})')
        out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        for line in out.strip().split('\n'):
            rid, slug, shelfmark = line.split('\t')
            m = re.search(r'-v\d+-\d+$', slug)
            keys[int(rid)] = (m.group(0) if m else None, shelfmark)
    return keys


PAGE_TAG = re.compile(r'\s*<!--\s*page:\s*\d+\s*-->\s*')
LINE_COUNT = re.compile(r'(?<![\d/×\-و])\s*(\d+)\s*سطر')


def raw_texts(db, ids):
    """Each copy's raw text on the site, page tags out and Persian digits as Latin ones."""
    texts = {}
    for i in range(0, len(ids), 2000):
        sql = f"select id, replace(replace(raw_text, '\\n', ' '), '\\t', ' ') from manuscripts where id in ({','.join(map(str, ids[i:i + 2000]))})"
        out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        for line in out.strip().split('\n'):
            rid, raw = line.split('\t', 1)
            texts[int(rid)] = PAGE_TAG.sub(' ', raw).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
    return texts


def single_line_count(raw):
    """The one line count a copy's text names, or None for none, several or a range («18 و 21 سطر», «15-22 سطر»)."""
    found = LINE_COUNT.findall(raw)
    if len(found) != 1 or re.search(r'\d\s*(?:و|-)\s*\d+\s*سطر', raw):
        return None
    return int(found[0])


def date_tail(d):
    """What v2 cut off the end of a copy date, without the separating «،», or None when it is not a cut."""
    if not d or d['category'] != 'trimmed':
        return None
    db, v2 = d['db'] or '', d['v2'] or ''
    if not v2 or not db.startswith(v2):
        return None
    return db[len(v2):].strip(' ،,.')


def date_notes(v2dir):
    """The note v2 split off each copy date, by the date as the catalogue printed it (raw date and note)."""
    import glob
    notes = {}
    for f in sorted(glob.glob(f'{v2dir}/fankha_vol_*.json')):
        for w in json.load(open(f, encoding='utf-8'))['works']:
            for c in w.get('copies') or []:
                cd = c.get('copy_date') or {}
                if cd.get('note'):
                    notes[f"{cd['raw']}، {cd['note']}".strip()] = cd['note']
    return notes


def citations(bracket):
    return [t.strip() for t in re.split(r'[؛;]', bracket.strip(' ،.[]')) if t.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diffs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--v2', default='json/fankha_v2', help='parser v2 JSON, for the notes on copy dates')
    ap.add_argument('categories', nargs='+', choices=['facsimile', 'print_bib', 'commissioner', 'copy_date_note', 'lines'])
    args = ap.parse_args()

    records, skipped = [], {}
    dates, commissioners, lines = {}, {}, {}
    for line in open(args.diffs, encoding='utf-8'):
        x = json.loads(line)
        if x['protected'] or x['site'] == 'unknown':
            continue
        if x['table'] == 'Manuscript' and x['field'] == 'copy_date_raw':
            dates[x['id']] = x
        if x['table'] == 'Manuscript' and x['field'] == 'commissioned_by' and x['category'] == 'filled':
            commissioners[x['id']] = x
        if x['table'] == 'Manuscript' and x['field'] == 'lines' and x['category'] == 'filled':
            lines[int(x['id'])] = x
        if 'facsimile' in args.categories and x['field'] == 'is_facsimile' and x['category'] == 'flag_on':
            records.append({'table': 'manuscripts', 'id': x['id'],
                            'category': 'facsimile', 'changes': {'is_facsimile': {'from': 0, 'to': 1}}})
        elif 'print_bib' in args.categories and x['table'] == 'Work' and x['field'] == 'print_info' \
                and x['category'] == 'trimmed':
            db, v2 = x['db'], x['v2'] or ''
            tail = db[len(v2):] if db.startswith(v2) else None
            if not tail or not re.match(r'^[\s،.]*\[[^\[\]]*\][\s.]*$', tail):
                skipped[x['id']] = 'the cut is not one trailing bracket'
                continue
            records.append({'table': 'works', 'id': x['id'], 'category': 'print_bib',
                            'changes': {'print_info': {'from': db, 'to': v2 or None}},
                            'require_in_bibliography': citations(tail)})

    if 'commissioner' in args.categories:
        for rid, c in commissioners.items():
            name = (c['v2'] or '').strip()
            if not name:
                continue
            rec = {'table': 'manuscripts', 'id': rid, 'category': 'commissioner', 'changes': {},
                   'commissioner': name}
            d = dates.get(rid)
            tail = date_tail(d)
            # «، حسب الامر میرزا …»: a short phrase with no digits, then the name, and nothing after it
            if tail is not None and tail.endswith(name) and len(tail) - len(name) <= 30 \
                    and not re.search(r'[0-9۰-۹]', tail[:len(tail) - len(name)]):
                rec['changes']['copy_date_raw'] = {'from': d['db'], 'to': d['v2']}
            records.append(rec)
    if 'copy_date_note' in args.categories:
        notes = date_notes(args.v2)
        for rid, d in dates.items():
            tail = date_tail(d)
            note = notes.get((d['db'] or '').strip())
            if tail and note and tail == note.strip(' ،.'):
                records.append({'table': 'manuscripts', 'id': rid, 'category': 'copy_date_note',
                                'changes': {'copy_date_raw': {'from': d['db'], 'to': d['v2']},
                                            'copy_date_note': {'from': None, 'to': note}}})

    if 'lines' in args.categories:
        texts = raw_texts(args.db, sorted(lines))
        for rid, x in lines.items():
            if x['db'] is not None or x['v2'] is None:
                continue
            if single_line_count(texts.get(rid, '')) != int(x['v2']):
                skipped[rid] = 'the copy text does not name that one line count'
                continue
            records.append({'table': 'manuscripts', 'id': rid, 'category': 'lines',
                            'changes': {'lines': {'from': None, 'to': int(x['v2'])}}})

    for table in ('manuscripts', 'works'):
        keys = site_keys(args.db, table, [r['id'] for r in records if r['table'] == table])
        for r in records:
            if r['table'] == table:
                r['work_key'], shelfmark = keys.get(r['id'], (None, None))
                if table == 'manuscripts':
                    r['shelfmark'] = shelfmark
    lost = [r for r in records if not r['work_key']]
    records = [r for r in records if r['work_key']]
    out = {'source': f'fankha parser v2 against the site ({args.diffs}), {date.today()}',
           'categories': args.categories, 'records': records,
           'skipped': [{'id': k, 'why': v} for k, v in skipped.items()]
           + [{'id': r['id'], 'why': 'not on the site'} for r in lost]}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f'{len(records)} records, {len(skipped)} skipped', file=sys.stderr)


if __name__ == '__main__':
    main()
