#!/usr/bin/env python3
"""What the old parser glued to the end of an incipit or explicit and is no part of it (fahares item 87, step
14.202; "trimmed" in the comparison report, v2 ending the incipit or explicit before it):
  - a work's bibliographic citation in brackets, «… وهن اعضاء. [فهرستواره منزوی 3258/5]»: the bracket is cut, and
    each of its citations not yet in the work's bibliography is added there;
  - a copy's original, for a photocopy or a microfilm, «… للحیوان نسخه اصل: کتابخانه دانشگاه کراچی 19986»;
  - a copy's script, scribe and date, «… احوال خط: نستعلیق، کا: عبد السلام بلگرامی، تا: 10 شوال 1270ق».
A copy's cut text becomes an editorial note, unless the copy already holds it (its note, or the same script, scribe
and date in their columns); an empty scribe or date column is filled from it. The column and metadata's list item
that holds it are cut alike.
Left out: a bracket that is text (a verse, «[پایان جلد اول]», «[1193ق]»); a copy whose metadata list holds the value
in another form, or whose incipit or explicit is also in text_excerpts; a protected field.
Input: a fankha_v2_db_compare.py report. Output: a fahares:add-corpus-works file (works) and a fahares:rebuild-copies
file (copies).
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

FIELDS = {'incipit_text': 'incipits', 'explicit_text': 'explicits'}
BRACKET = re.compile(r'\s*\[([^\[\]\n]+)\]\s*\.?\s*$')
# a part of a citation: a source's name, then a volume, page or number («دنا 1145/1 (2 نسخه)», «سزگین 4: 75»)
CITE_PART = re.compile(r'^(?!(?:آغاز|انجام|پایان|تم|تمت|و|از)\s)[^\d×«»]{2,}[^×«»]*\d')
ORIGINAL = re.compile(r'(?:[\s؛،.]|^)(?=(?:نسخه[\s‌]*(?:ی\s+)?اصلی?|اصل\s+نسخه)\s*:)')
AUTHOR_LINE = re.compile(r'(?:کاتـ?ب|كاتب|کا)\s*=\s*مؤلف|(?:^|؛\s*)خط(?:\s|$)')
PHYSICAL = re.compile(r'(?:[\s؛،.]|^)(?=(?:خ?ط\s*:|کا\s*:|بی‌کا(?:[،\s]|$)|تا\s*:|بی‌تا\s*$))')


def norm(s):
    return re.sub(r'[\s/:،.\-]+', '', (s or '').replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('ه‌', 'ه'))


def citation_parts(inner):
    parts = [p.strip() for p in inner.split('؛') if p.strip()]
    return parts if parts and all(len(p) <= 90 and CITE_PART.match(p) for p in parts) else None


def works(report, db, counts):
    rows = [d for d in report if d['table'] == 'Work' and d['field'] in FIELDS and d['category'] == 'trimmed' and not d['protected']]
    ids = sorted({int(d['id']) for d in rows})
    site = {}
    for i in range(0, len(ids), 500):
        for r in q(db, "select json_object('id', id, 'slug', slug, 'incipit_text', incipit_text, 'explicit_text', explicit_text, "
                       f"'bibliography', bibliography) from works where id in ({','.join(map(str, ids[i:i + 500]))})"):
            b = r['bibliography']
            r['bibliography'] = json.loads(b) if isinstance(b, str) else b
            site[r['id']] = r
    updates = {}
    for d in rows:
        s, f = site.get(int(d['id'])), d['field']
        if not s or s[f] != d['db']:
            counts['work: changed since the report'] += 1
            continue
        m = BRACKET.search(s[f])
        if not m:
            continue
        parts = citation_parts(m.group(1))
        if not parts:
            counts['work: bracket is text'] += 1
            continue
        cut = s[f][:m.start()].rstrip()
        if letters(cut) != letters(d['v2'] or '') and not letters(d['v2'] or '').startswith(letters(cut)):
            counts['work: v2 ends elsewhere'] += 1
            continue
        u = updates.setdefault(s['id'], {'work_slug': s['slug'], 'v2': None, 'changes': {}, '_bib': list(s['bibliography'] or [])})
        u['changes'][f] = {'from': s[f], 'to': cut}
        held = norm(' '.join(map(str, u['_bib'])))
        for p in parts:
            if norm(p) not in held:
                u['_bib'].append(p)
                counts['work: citation added to bibliography'] += 1
        counts['work: cut ' + f] += 1
    out = []
    for wid, u in updates.items():
        bib = u.pop('_bib')
        if bib != (site[wid]['bibliography'] or []):
            u['changes']['bibliography'] = {'from': site[wid]['bibliography'], 'to': bib}
        out.append(u)
    return out


def copies(report, db, counts):
    rows = [d for d in report if d['table'] == 'Manuscript' and d['field'] in FIELDS and d['category'] == 'trimmed' and not d['protected']]
    ids = sorted({int(d['id']) for d in rows})
    site = {}
    for i in range(0, len(ids), 500):
        for r in q(db, "select json_object('id', id, 'shelfmark', shelfmark, 'incipit_text', incipit_text, 'explicit_text', explicit_text, "
                       "'scribe_name', scribe_name, 'scribe_id', scribe_id, 'script_names', script_names, 'copy_date_raw', copy_date_raw, "
                       f"'is_bita', is_bita, 'is_autograph', is_autograph, 'metadata', metadata) from manuscripts where id in ({','.join(map(str, ids[i:i + 500]))})"):
            r['metadata'] = json.loads(r['metadata']) if isinstance(r['metadata'], str) else (r['metadata'] or {})
            site[r['id']] = r
    excerpts = {(r['id'], r['kind']) for r in q(db, "select json_object('id', owner_id, 'kind', kind) from text_excerpts "
                                                  "where owner_type = 'App\\\\Models\\\\Manuscript'")}
    records = {}
    for d in rows:
        rid, f = int(d['id']), d['field']
        s = site.get(rid)
        if not s or s[f] != d['db']:
            counts['copy: changed since the report'] += 1
            continue
        val = s[f]
        # the glued part runs to the end of the value, on its last line
        last = val.rsplit('\n', 1)[-1]
        kind, m = None, None
        for k, rx in (('original', ORIGINAL), ('physical', PHYSICAL)):
            hits = list(rx.finditer(last))
            if hits:
                kind, m = k, hits[0] if k == 'physical' else hits[-1]
                break
        v2 = d['v2'] or ''
        if kind:
            start = len(val) - len(last) + m.end()
        # the next line, «جلد اول و دوم؛ کاتب = مؤلف», «خط مختلف کا ابوالحسن»: v2 ends before it
        if '\n' in val and AUTHOR_LINE.search(last) and letters(val[:len(val) - len(last)]) == letters(v2):
            kind, start = 'line', len(val) - len(last)
        if not kind:
            continue
        cut = re.sub(r'[\s؛،]+$', '', val[:start])
        tail = val[start:].strip(' .؛،\n')
        # v2 keeps the script, «… لوجه الله خط: شکسته، نستعلیق», and ends there
        script_kept = letters(v2).startswith(letters(cut)) and re.fullmatch(r'\s*خ?ط\s*:[^؛]*', v2[len(cut):] if v2.startswith(cut) else '')
        if letters(cut) != letters(v2) and not script_kept:
            counts[f'copy {kind}: v2 ends elsewhere'] += 1
            continue
        if (rid, 'explicit' if f == 'explicit_text' else 'incipit') in excerpts:
            counts['copy: in text_excerpts'] += 1
            continue
        rec = records.setdefault(rid, {'table': 'manuscripts', 'id': rid, 'shelfmark': s['shelfmark'], 'category': 'rebuild', 'v2': None,
                                       'changes': {}, '_meta': json.loads(json.dumps(s['metadata']))})
        meta = rec['_meta']
        lst = meta.get(FIELDS[f]) or []
        hit = [i for i, e in enumerate(lst) if isinstance(e, dict) and e.get('text') == val]
        list_ok = not hit and lst and isinstance(lst[0], dict) and letters(lst[0].get('text') or '') == letters(cut)
        if lst and len(hit) != 1 and not list_ok:
            counts['copy: metadata list differs'] += 1
            if not rec['changes']:
                del records[rid]
            continue
        if hit:
            lst[hit[0]]['text'] = cut
        rec['changes'][f] = {'from': val, 'to': cut}
        # the tail's parts: «خط: نسخ، کا: …، تا: …؛ محشی» is the fields, then a remark
        parts = [p.strip(' .،') for p in tail.split('؛') if p.strip(' .،')]
        notes = parts
        if kind == 'physical':
            held = True
            for piece in [x.strip() for x in parts[0].split('،') if x.strip()]:
                p = re.match(r'^(خط|ط|کا|تا)\s*:\s*(.+)$', piece)
                col = {'خط': 'script_names', 'ط': 'script_names', 'کا': 'scribe_name', 'تا': 'copy_date_raw'}.get(p.group(1)) if p else None
                if col:
                    v = p.group(2).strip()
                    if s[col]:
                        held = held and letters(v) == letters(s[col])
                    elif col == 'copy_date_raw' or (col == 'scribe_name' and not s['scribe_id']):
                        rec['changes'][col] = {'from': None, 'to': v}
                        counts[f'copy physical: {col} filled'] += 1
                    else:
                        held = False
                elif piece == 'بی‌کا':
                    held = held and not s['scribe_name']
                elif piece == 'بی‌تا':
                    if not s['copy_date_raw'] and not s['is_bita']:
                        rec['changes']['is_bita'] = {'from': s['is_bita'], 'to': 1}
                        counts['copy physical: bita set'] += 1
                    held = held and not s['copy_date_raw']
                else:
                    held = False
            notes = parts[1:] if held else parts
        if kind == 'line' and re.search(r'=\s*مؤلف', tail) and '(گویا)' not in tail and '؟' not in tail and not s['is_autograph']:
            rec['changes']['is_autograph'] = {'from': s['is_autograph'], 'to': 1}
            counts['copy line: autograph set'] += 1
        for note in notes:
            held_text = letters(json.dumps(meta, ensure_ascii=False))
            # a part the copy holds already, or whose end it holds (a note that repeats a longer one)
            if letters(note) not in held_text and letters(note)[-100:] not in held_text:
                meta['editorial_notes'] = (meta.get('editorial_notes') or []) + [note]
                counts[f'copy {kind}: note added'] += 1
        counts[f'copy {kind}: cut {f}'] += 1
    out = []
    for rid, rec in records.items():
        meta = rec.pop('_meta')
        if meta != site[rid]['metadata']:
            rec['changes']['metadata'] = {'from': site[rid]['metadata'], 'to': meta}
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--works-out', required=True)
    ap.add_argument('--copies-out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.202')
    args = ap.parse_args()
    report = [json.loads(l) for l in open(Path(args.report) / 'diffs.jsonl', encoding='utf-8')]
    counts = Counter()
    w = works(report, args.db, counts)
    c = copies(report, args.db, counts)
    src = f"{{}} cut from the end of an incipit or explicit ({args.report}), {date.today()}; fahares step {args.step}"
    Path(args.works_out).write_text(json.dumps({'source': src.format("a work's bibliographic citation"), 'category': 'corpus_fix',
                                                'works': [], 'fills': [], 'work_updates': w}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    Path(args.copies_out).write_text(json.dumps({'source': src.format("a copy's original, script, scribe or date"), 'records': c},
                                                ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(w), 'works,', len(c), 'copies', dict(sorted(counts.items())))


if __name__ == '__main__':
    main()
