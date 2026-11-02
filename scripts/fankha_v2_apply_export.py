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
  lines_bayt  a copy whose line count on the site is the number of its verses («حدود 540 بیت»): its text names
             no lines at all and that number stands before «بیت», so the count leaves `lines` (step 13.152)
  explicit_tail  the line after a copy's explicit, which the site kept in the explicit («جلد اول», a note on the
             contents): the explicit loses it, and each of its parts («؛») becomes a cataloguer's note, with the
             type v2 gave it when v2 has that part as a scope, description or typed note; a part already in the
             copy's notes on the site is not added twice, and a list of more than three parts stays one note. A
             tail that is the script or scribe («کاتب = مؤلف، بی‌تا») is left. The text moves word for word (step 13.139)
  flags_off  is_ruled and is_illuminated the site set on, v2 off, where the copy's text gives them only from its
             binding («جلد: تیماج مجدول», «جلد: تیماج مذهب») or, for illumination, from the incipit or explicit
             («مذهب المعتزلة» is a school, not gilding) or nothing at all; «مجدول» or «سرلوح» said of the pages keeps
             the flag (step 13.167)
  incipit_tail, incipit_script  the same for a copy's incipit, the line the site kept after it (step 13.164)
  explicit_script  «خط: …، بی‌کا، تا: …» the site kept in the explicit: it goes, when the site has the copy's
             script (or the tail names none) and its date or «بی‌تا»; the copy keeps its raw text (step 13.139)

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


def metadata(db, ids):
    """Each copy's script names, whether it is dated, its metadata JSON and its raw text (no page tags) on the site."""
    rows = {}
    for i in range(0, len(ids), 2000):
        sql = (f"select id, coalesce(script_names, ''), (copy_date_raw is not null or is_bita = 1), replace(to_base64(metadata), '\\n', ''), replace(to_base64(raw_text), '\\n', '') "
               f"from manuscripts where id in ({','.join(map(str, ids[i:i + 2000]))})")
        out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c',
                              f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                             input=sql, capture_output=True, text=True, check=True).stdout
        import base64
        for line in out.strip().split('\n'):
            rid, script, dated, meta, raw = line.split('\t')
            meta = json.loads(base64.b64decode(meta).decode()) if meta != 'NULL' else {}
            raw = base64.b64decode(raw).decode() if raw != 'NULL' else ''
            rows[int(rid)] = (script, dated == '1', meta or {}, PAGE_TAG.sub(' ', raw))
    return rows


def norm(t):
    return re.sub(r'\s+', ' ', (t or '').replace('ي', 'ی').replace('ك', 'ک')).strip(' .،؛')


def v2_parts(v2dir, kind='explicit'):
    """By a copy's explicit (or incipit) in v2: the type of each scope, description and note v2 found in that copy."""
    import glob
    parts = {}
    for f in sorted(glob.glob(f'{v2dir}/fankha_vol_*.json')):
        for w in json.load(open(f, encoding='utf-8'))['works']:
            for c in w.get('copies') or []:
                e = c.get(kind)
                text = e.get('text') if isinstance(e, dict) else e
                if not text:
                    continue
                kinds = parts.setdefault(norm(text), {})
                if c.get('contents_scope'):
                    kinds[norm(c['contents_scope'])] = 'contents_scope'
                if c.get('copy_description'):
                    kinds[norm(c['copy_description'])] = 'copy_description'
                for n in c.get('notes') or []:
                    kinds[norm(n['text'])] = n['type']
    return parts


def site_notes(meta):
    """Every note text the site already shows for a copy, normalised."""
    have = [*(meta.get('editorial_notes') or [])]
    res = meta.get('residual_notes')
    have += res if isinstance(res, list) else [res or '']
    for o in meta.get('ownership_and_seals') or []:
        have.append(o.get('text', '') if isinstance(o, dict) else str(o))
    return {norm(x) for x in have if x}


RULED = re.compile(r'مجدول|جدول')
GILT = re.compile(r'مذهب|تذهیب|سرلوح|زر|طلا')


def flag_without_ground(raw, fields):
    """For each flag, why the copy's text does not give it (None when its pages are said to be ruled or gilt): the
    word is in the binding only, or in the incipit or explicit only, or nowhere."""
    binding = (re.search(r'جلد\s*:[^؛\[]*', raw) or [''])[0]
    body = re.sub(r'(?:آغاز|انجام)\s*:[^؛]*', '', raw).replace(binding, '') if binding else re.sub(r'(?:آغاز|انجام)\s*:[^؛]*', '', raw)
    out = {}
    for field, word in (('is_ruled', RULED), ('is_illuminated', GILT)):
        if field not in fields or word.search(body):
            out[field] = None
        elif word.search(binding):
            out[field] = 'binding'
        elif field == 'is_illuminated':
            out[field] = 'text' if word.search(raw) else 'nowhere'
        else:
            # a ruled flag with no word but in the incipit is left: «جدول» there may be the work's own tables
            out[field] = None
    return out


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
    ap.add_argument('categories', nargs='+', choices=['facsimile', 'print_bib', 'commissioner', 'copy_date_note', 'lines', 'explicit_tail', 'explicit_script', 'lines_bayt', 'incipit_tail', 'incipit_script', 'flags_off'])
    args = ap.parse_args()

    records, skipped = [], {}
    dates, commissioners, lines, explicits, incipits, flags = {}, {}, {}, {}, {}, {}
    for line in open(args.diffs, encoding='utf-8'):
        x = json.loads(line)
        if x['protected'] or x['site'] == 'unknown':
            continue
        if x['table'] == 'Manuscript' and x['field'] == 'copy_date_raw':
            dates[x['id']] = x
        if x['table'] == 'Manuscript' and x['field'] == 'commissioned_by' and x['category'] == 'filled':
            commissioners[x['id']] = x
        if x['table'] == 'Manuscript' and x['field'] == 'explicit_text' and x['category'] == 'trimmed':
            explicits[int(x['id'])] = x
        if x['field'] in ('is_ruled', 'is_illuminated') and x['category'] == 'flag_off':
            flags.setdefault(int(x['id']), []).append(x['field'])
        if x['table'] == 'Manuscript' and x['field'] == 'incipit_text' and x['category'] == 'trimmed':
            incipits[int(x['id'])] = x
        if x['table'] == 'Manuscript' and x['field'] == 'lines' and x['category'] in ('filled', 'emptied'):
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

    if 'lines_bayt' in args.categories:
        texts = raw_texts(args.db, sorted(lines))
        for rid, x in lines.items():
            if x['category'] != 'emptied' or x['db'] is None:
                continue
            raw = texts.get(rid, '')
            if 'سطر' in raw or not re.search(rf'(?<![\d/]){int(x["db"])}\s*بیت', raw):
                skipped[rid] = 'the copy text names lines, or not that number of verses'
                continue
            records.append({'table': 'manuscripts', 'id': rid, 'category': 'lines_bayt',
                            'changes': {'lines': {'from': int(x['db']), 'to': None}}})
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

    if 'flags_off' in args.categories:
        texts = raw_texts(args.db, sorted(flags))
        for rid, fields in flags.items():
            reason = flag_without_ground(texts.get(rid, ''), fields)
            for field in fields:
                if reason.get(field):
                    records.append({'table': 'manuscripts', 'id': rid, 'category': f'{field}_off',
                                    'changes': {field: {'from': 1, 'to': 0}}, 'why': reason[field]})
                else:
                    skipped[rid] = f'{field}: the pages are said to be so'

    for kind, trimmed in (('explicit', explicits), ('incipit', incipits)):
        tail_cat, script_cat, column = f'{kind}_tail', f'{kind}_script', f'{kind}_text'
        if tail_cat not in args.categories and script_cat not in args.categories:
            continue
        kinds = v2_parts(args.v2, kind) if tail_cat in args.categories else {}
        site = metadata(args.db, sorted(trimmed))
        for rid, x in trimmed.items():
            db, v2 = x['db'] or '', x['v2'] or ''
            if not v2 or not db.startswith(v2) or rid not in site:
                skipped[rid] = f'the v2 {kind} is not the start of the site one'
                continue
            tail = db[len(v2):]
            script, dated, meta, raw = site[rid]
            if re.match(r'^[؛\s]*\n', tail) and tail_cat in args.categories:
                if '\n' in tail.strip():
                    skipped[rid] = 'the tail is more than one line'
                    continue
                have, mine, notes = site_notes(meta), kinds.get(norm(v2), {}), []
                if re.match(r'^[؛\s]*(?:خط:|بی‌کا|کا:|کاتب)', tail):
                    skipped[rid] = 'the tail is the copy\'s script or scribe, not a note'
                    continue
                # the tail must be the line right after the explicit (incipit) in the copy's text, not a piece from further on
                if re.sub(r'\s+', ' ', v2 + tail).strip() not in re.sub(r'\s+', ' ', raw):
                    skipped[rid] = f'the tail is not the line after the {kind} in the copy text'
                    continue
                # «…؛ خط: نستعلیق، بی‌کا، بی‌تا»: the script and date after the note stay out of the notes, so the
                # site must hold them already
                said, cut = tail, re.search(r'؛\s*(?:خط:|بی‌کا|کا:|کاتب)', tail)
                if cut:
                    if ('خط:' in tail[cut.start():] and not script) or not dated:
                        skipped[rid] = 'the site has not the script or the date the tail names'
                        continue
                    said = tail[:cut.start()]
                pieces = [p for p in (q.strip(' \n') for q in said.strip(' ؛\n').split('؛')) if p]
                # a long list («فصل …؛ فصل …») stays one note, as the catalogue printed it
                typed = len(pieces) <= 3 and all(norm(p) in mine for p in pieces)
                for p in (pieces if typed else [said.strip(' ؛\n')]):
                    if norm(p) not in have:
                        notes.append({'text': p, 'type': mine.get(norm(p)) if typed else None})
                # a script, scribe or date written inside the note («جلد 3، کا: …، تا: قرن 13») is left for review
                if any(re.search(r'(?:^|[،؛\s])(?:خط:|کا:|تا:|بی‌کا|بی‌تا)', n['text']) for n in notes):
                    skipped[rid] = 'the note holds a script, scribe or date'
                    continue
                # a verse («… ×× …») or a part's own incipit («آغاز كتاب الصلوة: …») goes on the text, it is no note
                if any('××' in n['text'] or re.match(r'^(?:آغاز|انجام)', n['text']) for n in notes):
                    skipped[rid] = f'the line after the {kind} goes on its text'
                    continue
                records.append({'table': 'manuscripts', 'id': rid, 'category': tail_cat,
                                'changes': {column: {'from': db, 'to': v2}}, 'notes': notes})
            elif script_cat in args.categories and re.match(r'^\s*(?:خط:|بی‌کا|کا:)', tail):
                if ('خط:' in tail and not script) or not dated:
                    skipped[rid] = 'the site has not the script or the date the tail names'
                    continue
                records.append({'table': 'manuscripts', 'id': rid, 'category': script_cat,
                                'changes': {column: {'from': db, 'to': v2}}, 'notes': []})

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
