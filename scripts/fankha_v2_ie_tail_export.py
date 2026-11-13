#!/usr/bin/env python3
"""A copy's incipit or explicit on the site that carries the text after it (fahares item 87, step 14.160): the next
line (a scope, a remark, «کاتب = مؤلف، بی‌تا»), or a second labelled part on the same line. v2 reads the incipit or
explicit alone and puts the rest in another column ("moved" in the comparison report). Here the site's value is cut
where v2's ends, keeping the site's own spelling, in the column and in metadata's list, which the copy's page shows;
the cut text becomes an editorial note of the copy, so nothing leaves its page. A tail that is quoted text (a second
incipit, a verse, «…», a date's year) stays.
Left out: a value v2 does not hold as the start of the site's; a tail v2 keeps in no compared column ("dropped", for
a later round that first fills those columns); a tail that runs on after a page tag (the quotation goes on, and v2
cuts it there wrongly); a copy whose incipit or explicit is also in text_excerpts.
Input: a fankha_v2_db_compare.py report. Output: a fahares:rebuild-copies file.
"""
import argparse
import json
import re
import subprocess
import unicodedata
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_v2_fill_columns_export import letters  # noqa: E402

FIELDS = {'explicit_text': 'explicits', 'incipit_text': 'incipits'}


def q(db, sql):
    out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c', f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -N -B {db}'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    return [json.loads(l.replace('\\\\', '\\')) for l in out.splitlines() if l.strip()]


def cut(site, v2):
    """The site's value up to where v2's ends, letter for letter; None when v2's is not its start."""
    want = letters(v2)
    if len(want) < 3 or not letters(site).startswith(want) or letters(site) == want:
        return None
    n = 0
    for i, ch in enumerate(site):
        if letters(ch):
            n += 1
            if n == len(want):
                j = i + 1
                # a letter's marks (tanwin, shadda, kasra) belong to it, and a bracket opened in the kept text closes there
                while j < len(site) and unicodedata.combining(site[j]):
                    j += 1
                if site[j:j + 1] == ')' and site[:j].count('(') > site[:j].count(')'):
                    j += 1
                return site[:j].rstrip()
    return None


# words of a cataloguer's note (scope, completeness, attribution), as against the rest of a quotation
NOTE_WORD = re.compile(r'(?<![\w\u200c])(?:است|اند|شامل|کامل|ناقص|جلد|کاتب|رساله|نسخه|مؤلف|ترجمه|بخش|باب|کتاب|دانسته|گویا|'
                       r'تذکر|فاقد|مقدمه|قصیده|غزل|تقریرات|جزء|سوره|درس|فصل|شرح|بیاض|جنگ|منتخب|مطالب|آغاز|انجام|پایان|'
                       r'نام|خط|تا)(?![\w\u200c])')


def is_note(tail, kept):
    """The cut text reads as a cataloguer's note: short, a repeat of the kept text, or with a note's words near its start."""
    t = tail.strip(' .؛،:\n')
    return len(letters(t)) <= 20 or letters(t) in letters(kept) or bool(NOTE_WORD.search(t[:100].replace('ك', 'ک').replace('ي', 'ی')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.160')
    args = ap.parse_args()
    rows = [d for d in map(json.loads, open(Path(args.report) / 'diffs.jsonl', encoding='utf-8'))
            if d['table'] == 'Manuscript' and d['field'] in FIELDS and d['category'] == 'trimmed'
            and not d['protected'] and d['fate'] == 'moved']
    ids = sorted({int(d['id']) for d in rows})
    site = {}
    for i in range(0, len(ids), 500):
        part = ','.join(map(str, ids[i:i + 500]))
        for r in q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'raw', raw_text, 'incipit_text', incipit_text, "
                            f"'explicit_text', explicit_text, 'metadata', metadata) from manuscripts where id in ({part})"):
            r['metadata'] = json.loads(r['metadata']) if isinstance(r['metadata'], str) else (r['metadata'] or {})
            site[r['id']] = r
    excerpts = {(r['id'], r['kind']) for r in q(args.db, "select json_object('id', owner_id, 'kind', kind) from text_excerpts "
                                                       "where owner_type = 'App\\\\Models\\\\Manuscript'")}
    judged = json.loads((Path(__file__).resolve().parent.parent / 'reconciliations' / 'page_tag_breaks_step14_149.json').read_text(encoding='utf-8'))
    runs_on = [it['after'] for it in judged['items'] if it['label'] == 'CONTINUES']
    records, counts = {}, Counter()
    for d in rows:
        rid, f = int(d['id']), d['field']
        s = site.get(rid)
        if not s or s[f] != d['db']:
            counts['changed since the report'] += 1
            continue
        if (rid, 'explicit' if f == 'explicit_text' else 'incipit') in excerpts:
            counts['in text_excerpts'] += 1
            continue
        new = cut(s[f], d['v2'] or '')
        if not new:
            counts['v2 not its start'] += 1
            continue
        tail = s[f][len(new):].strip()
        # the quotation running on after a page tag, as judged in step 14.149 (the text after it is not a new line)
        if any(letters(tail[:30]) and letters(c)[:len(letters(tail[:30]))] == letters(tail[:30]) for c in runs_on):
            counts['runs on after a page tag'] += 1
            continue
        # a second incipit, a verse or a quotation, a date's year («… سنه» / «1114»): part of what is quoted, not a note
        if re.match(r'^[\s.؛،:]*(?:«|\(|\d|بسمله|بسم|الحمد|×|\.\.\.|…)', tail) or '××' in tail[:80]:
            counts['tail is quoted text'] += 1
            continue
        if not is_note(tail, new):
            counts['tail not clearly a note'] += 1
            continue
        key = FIELDS[f]
        meta = s['metadata']
        lst = meta.get(key) or []
        hit = [i for i, e in enumerate(lst) if isinstance(e, dict) and e.get('text') == s[f]]
        # the list already parted (its first item the incipit alone, the rest other parts): only the column is cut
        list_ok = not hit and lst and isinstance(lst[0], dict) and letters(lst[0].get('text') or '') == letters(new)
        if lst and len(hit) != 1 and not list_ok:
            counts['metadata list differs'] += 1
            continue
        rec = records.setdefault(rid, {'table': 'manuscripts', 'id': rid, 'shelfmark': s['shelfmark'], 'category': 'rebuild',
                                       'v2': d['label'].split(' ')[0], 'changes': {}, '_meta': json.loads(json.dumps(meta))})
        rec['changes'][f] = {'from': s[f], 'to': new}
        if hit:
            rec['_meta'][key][hit[0]]['text'] = new
        # the cut text stays on the copy's page, as an editorial note, unless metadata already holds it (another part, a note)
        note = tail.strip(' .؛،:\n')
        held = letters(json.dumps(rec['_meta'], ensure_ascii=False))
        notes = rec['_meta'].get('editorial_notes') or []
        if note and letters(note) not in held:
            notes.append(note)
            rec['_meta']['editorial_notes'] = notes
        counts['cut ' + f] += 1
    out = []
    for rid, rec in records.items():
        meta = rec.pop('_meta')
        if meta != site[rid]['metadata']:
            rec['changes']['metadata'] = {'from': site[rid]['metadata'], 'to': meta}
        out.append(rec)
    Path(args.out).write_text(json.dumps({'source': f"a copy's incipit or explicit cut where v2's ends, the rest being in another v2 column ({args.report}), {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(counts))


if __name__ == '__main__':
    main()
