#!/usr/bin/env python3
"""A copy's notes with their types, for the site's manuscript_notes table (fahares item 87, step 14.254).
Each v2 copy is matched to the site's copy by its text (raw_text, normalised as the comparison does): a text one site
copy and one v2 copy hold. The copy's notes come from:
  - v2's `notes`, with the type a model read (reconciliations/fankha_note_types.jsonl); a piece the model read as the
    cut-off rest of a field is left out; a text the file lacks keeps v2's rule type;
  - v2's labelled fields: seals («مهر:») as seal, ownership («تملک:») as ownership, acquisition («اهدایی: …»،
    «خریداری …») as acquisition, donor («واقف:») as endowment; typed_by is "field".
The notes are in the order of the copy's text. Output: gzipped JSON lines, one copy a line:
{"id", "shelfmark", "notes": [{"type", "text", "typed_by", "also"?, "by_author"?, "by_author_hedge"?, "hedge"?}]}
"""
import argparse, glob, gzip, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fankha_v2_db_compare import query, rkey  # noqa: E402

FIELDS = (('seals', 'seal'), ('ownership', 'ownership'), ('acquisition', 'acquisition'), ('donor', 'endowment'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    types = {r['id']: r for r in map(json.loads, open(ROOT / 'reconciliations/fankha_note_types.jsonl', encoding='utf-8'))}
    v2 = defaultdict(list)
    for f in sorted(glob.glob(str(ROOT / 'json/fankha_v2/*.json'))):
        for w in json.load(open(f, encoding='utf-8'))['works']:
            for c in w['copies']:
                v2[rkey(c['raw_text'])].append(c)
    site = defaultdict(list)
    for r in query(args.db, "select json_object('id', id, 'raw', raw_text, 'shelfmark', shelfmark) from manuscripts where catalog_id = 1"):
        site[rkey(r['raw'])].append(r)
    counts, by_type = Counter(), Counter()
    with gzip.open(args.out, 'wt', encoding='utf-8') as out:
        rows = []
        for k, ss in site.items():
            cs = v2.get(k)
            if not cs:
                counts['site copies not in v2'] += len(ss)
                continue
            if len(ss) != 1 or len(cs) != 1:
                counts['copies of a text held twice'] += len(ss)
                continue
            s, c = ss[0], cs[0]
            notes = []
            for n in c.get('notes') or []:
                if not n['text'].strip():
                    continue
                t = types.get(hashlib.sha1(n['text'].encode()).hexdigest()[:12])
                if t and 'c' in t:
                    counts['pieces that continue a field, left out'] += 1
                    continue
                if t:
                    note = {'type': t['t'], 'text': n['text'], 'typed_by': 'opus' if t.get('m') else 'sonnet'}
                    for a, b in (('a', 'also'), ('ba', 'by_author'), ('bh', 'by_author_hedge'), ('h', 'hedge')):
                        if t.get(a):
                            note[b] = t[a]
                else:
                    note = {'type': n['type'], 'text': n['text'], 'typed_by': 'rule'}
                    counts['notes typed by the rule'] += 1
                notes.append(note)
            for field, typ in FIELDS:
                v = c.get(field)
                for text in ([v] if isinstance(v, str) else v or []):
                    if text.strip():                    # «مهر:» with nothing after it
                        notes.append({'type': typ, 'text': text, 'typed_by': 'field'})
            if not notes:
                continue
            raw = c['raw_text']
            notes = [n for _, _, n in sorted(((raw.find(n['text']) if n['text'] in raw else len(raw)), i, n) for i, n in enumerate(notes))]
            for n in notes:
                by_type[n['type']] += 1
                counts['typed_by ' + n['typed_by']] += 1
            rows.append({'id': s['id'], 'shelfmark': s['shelfmark'], 'notes': notes})
        for r in sorted(rows, key=lambda r: r['id']):
            out.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(len(rows), 'copies,', sum(by_type.values()), 'notes')
    for k, n in sorted(counts.items()):
        print(f'  {k:42} {n:7}')
    for k, n in by_type.most_common():
        print(f'  {k:14} {n:7}')


if __name__ == '__main__':
    main()
