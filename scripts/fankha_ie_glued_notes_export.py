#!/usr/bin/env python3
"""A copy's incipit or explicit that ends in what is no part of it, or is nothing else (fahares item 87, step 14.215;
"emptied" and "trimmed" in the comparison report):
  - the endowment, «…»؛ واقف: حسین کی استوان، آبان 1348»: cut, and kept in ownership_and_seals;
  - the copy's decoration and state after the closing quotation, «…»، مجدول، دارای سرلوح، مذهب»: cut to an editorial
    note, with is_ruled («مجدول») and is_illuminated («سرلوح»، «مذهب»، «لوح») set where off;
  - a value that is only the copy's script, scribe and date, read from the line after an empty «آغاز و انجام:»
    («خط: نستعلیق، کا: …، تا: 18 رمضان 1076ق»): the column is emptied, an empty scribe or date column filled.
What is cut goes where the copy does not hold it yet (letter for letter in metadata or the column); the column and
metadata's list item that holds it are cut alike. Left out: a value whose list item differs, one in text_excerpts, a
protected field, a «کا:» that names another scribe than the copy's («کا: عن عدة من اصحابنا ...»).
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

FIELDS = {'incipit_text': 'incipits', 'explicit_text': 'explicits'}
WAQF = re.compile(r'\s*[؛،]\s*(?=(?:واقف|وقف|تاریخ\s+وقف)(?:\s*:|\s))')
DECOR_PIECE = re.compile(r'^(?:مجدول(?:\s+و\s+مذهب)?|مذهب|منقش|(?:دارای|با)\s*(?:\S+\s+){0,2}(?:سرلوح|لوح|کتیبه)(?:\s+\S+){0,3}|'
                         r'مصحح(?:\s.*)?|محشی(?:\s.*)?|مقابله(?:\s.*)?|(?:مقابله|تصحیح)\s+شده.*)$')
FIELD_PIECE = re.compile(r'^(خط|کا|تا|جا)\s*:\s*(.+)$')


def physical(value, s, changes, counts):
    """The value as the copy's fields alone: the parts that are not held (None when it is something else)."""
    head, _, rest = value.partition('؛')
    held, rest_parts = True, [p.strip(' .،') for p in rest.split('؛') if p.strip(' .،')]
    for piece in [x.strip() for x in head.split('،') if x.strip()]:
        m = FIELD_PIECE.match(piece)
        if piece in ('بی‌کا', 'بی‌تا'):
            held = held and not s['scribe_name' if piece == 'بی‌کا' else 'copy_date_raw']
            continue
        if not m:
            return None
        col = {'خط': 'script_names', 'کا': 'scribe_name', 'تا': 'copy_date_raw', 'جا': 'copy_place'}[m.group(1)]
        v = m.group(2).strip()
        if s[col]:
            if letters(v) != letters(s[col]):
                if col == 'scribe_name':
                    return None
                held = False
        elif col in ('copy_date_raw', 'copy_place') or (col == 'scribe_name' and not s['scribe_id']):
            changes[col] = {'from': None, 'to': v}
            counts[f'{col} filled'] += 1
        else:
            held = False
    return ([] if held else [head.strip()]) + rest_parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.215')
    args = ap.parse_args()
    rows = q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'incipit_text', incipit_text, 'explicit_text', explicit_text, "
                      "'scribe_name', scribe_name, 'scribe_id', scribe_id, 'script_names', script_names, 'copy_date_raw', copy_date_raw, "
                      "'copy_place', copy_place, 'is_ruled', is_ruled, 'is_illuminated', is_illuminated, 'metadata', metadata) from manuscripts "
                      "where incipit_text regexp '[؛،][[:space:]]*(واقف|وقف|تاریخ وقف)[[:space:]]*:|»[؛،][[:space:]]*(مجدول|مذهب|منقش|دارای|با|مصحح|محشی|مقابله)|^[[:space:]]*(خط|کا)[[:space:]]*:' "
                      "or explicit_text regexp '[؛،][[:space:]]*(واقف|وقف|تاریخ وقف)[[:space:]]*:|»[؛،][[:space:]]*(مجدول|مذهب|منقش|دارای|با|مصحح|محشی|مقابله)|^[[:space:]]*(خط|کا)[[:space:]]*:'")
    excerpts = {(r['id'], r['kind']) for r in q(args.db, "select json_object('id', owner_id, 'kind', kind) from text_excerpts "
                                                      "where owner_type = 'App\\\\Models\\\\Manuscript'")}
    out, counts = [], Counter()
    for s in rows:
        meta = json.loads(s['metadata']) if isinstance(s['metadata'], str) else (s['metadata'] or {})
        new_meta = json.loads(json.dumps(meta))
        changes, notes, owner = {}, [], []
        for f, key in FIELDS.items():
            val = s[f]
            if not val:
                continue
            if (s['id'], 'explicit' if f == 'explicit_text' else 'incipit') in excerpts:
                counts['in text_excerpts'] += 1
                continue
            new, kind = val, None
            if re.match(r'^\s*(?:خط|کا)\s*:', val) and '\n' not in val.strip():
                parts = physical(val.strip(), s, changes, counts)
                if parts is None:
                    counts['fields: not the copy\'s'] += 1
                    continue
                new, kind = None, 'fields'
                for p in parts:
                    (owner if re.match(r'(?:واقف|وقف|تاریخ\s+وقف)\s*:', p) else notes).append(p)
            else:
                last_start = val.rfind('\n') + 1
                last = val[last_start:]
                m = WAQF.search(last)
                if m:
                    # «واقف: فهرستی، 12گ، مختلف السطر، اندازه: …»: the extent after the endowment goes to a note
                    o = last[m.end():].strip(' .')
                    p = re.search(r'،\s*(?=[\d۰-۹]+\s*(?:گ|برگ|ص)(?!\w)|اندازه|مختلف\s+السطر)', o)
                    if p:
                        o, phys = o[:p.start()], o[p.end():]
                        notes.append(phys.strip(' .'))
                    owner.append(o.strip(' .،'))
                    new, kind = val[:last_start + m.start()], 'endowment'
                    last = last[:m.start()]
                # the decoration after the closing quotation
                d = re.search(r'»((?:\s*[،؛]\s*[^،؛«»]+)+)\s*$', last)
                if d and all(DECOR_PIECE.match(p.strip()) for p in re.split(r'[،؛]', d.group(1)) if p.strip()):
                    pieces = [p.strip() for p in re.split(r'[،؛]', d.group(1)) if p.strip()]
                    notes.append('، '.join(pieces))
                    new = val[:last_start + d.start() + 1]
                    kind = (kind + '+' if kind else '') + 'decoration'
                    text = ' '.join(pieces)
                    if 'مجدول' in text and not s['is_ruled']:
                        changes['is_ruled'] = {'from': s['is_ruled'], 'to': 1}
                        counts['is_ruled set'] += 1
                    if re.search(r'سرلوح|لوح|مذهب', text) and not s['is_illuminated']:
                        changes['is_illuminated'] = {'from': s['is_illuminated'], 'to': 1}
                        counts['is_illuminated set'] += 1
                if not kind:
                    continue
                new = re.sub(r'[\s؛،]+$', '', new)
            lst = new_meta.get(key) or []
            hit = [i for i, e in enumerate(lst) if isinstance(e, dict) and e.get('text') == val]
            # the list parted by line: its last item ends in what the column loses («…»؛ واقف: …»)
            tail = val[len(new):] if new is not None and val.startswith(new) else None
            ends = [i for i, e in enumerate(lst) if isinstance(e, dict) and tail and (e.get('text') or '').endswith(tail)]
            if hit and new is None:
                lst.pop(hit[0])
            elif len(hit) == 1 or (not hit and len(ends) == 1):
                i = hit[0] if hit else ends[0]
                lst[i]['text'] = new if hit else re.sub(r'[\s؛،]+$', '', lst[i]['text'][:-len(tail)])
            elif lst:
                counts['metadata list differs'] += 1
                changes = None
                break
            changes[f] = {'from': val, 'to': new}
            counts[f'{kind}: {f}'] += 1
        if not changes or not any(f in changes for f in FIELDS):
            continue
        for o in dict.fromkeys(owner):
            if o and letters(o) not in letters(json.dumps(new_meta, ensure_ascii=False)):
                new_meta['ownership_and_seals'] = (new_meta.get('ownership_and_seals') or []) + [o]
                counts['endowment kept'] += 1
        for n in dict.fromkeys(notes):
            if n and letters(n) not in letters(json.dumps(new_meta, ensure_ascii=False)):
                new_meta['editorial_notes'] = (new_meta.get('editorial_notes') or []) + [n]
                counts['note added'] += 1
        if new_meta != meta:
            changes['metadata'] = {'from': meta, 'to': new_meta}
        out.append({'table': 'manuscripts', 'id': s['id'], 'shelfmark': s['shelfmark'], 'category': 'rebuild', 'v2': None, 'changes': changes})
        counts['copies'] += 1
    Path(args.out).write_text(json.dumps({'source': f"an endowment, the decoration or the copy's fields cut from an incipit or explicit, {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(sorted(counts.items())))


if __name__ == '__main__':
    main()
