#!/usr/bin/env python3
"""The types of Fankha's copy notes, read by a model (fahares item 87): the first pass (Sonnet, every note) and the
second (Opus, the notes fankha_notes_pass2_select.py picked) merged into one line per note text.
Key: the first 12 hex digits of sha1(note text), the text being a note's `text` in json/fankha_v2.
Line: {"id", "t": type, or "c": the field the piece continues (then no type), "a": other types, "ba": by the author,
"bh": the hedge of that, "h": the hedge of the whole note, "m": "o" where the second pass decided}; empty keys left out.
A first-pass continuation of another note («c»: a type's name) is that type.
Run in scratch/notes_typing (in/, out/, in2/, out2/): fankha_notes_merge_types.py <out file>
"""
import collections, json, os, sys
T = {'contents', 'annex', 'marginalia', 'cataloguer', 'transcription', 'decoration', 'codicology', 'ownership', 'collation',
     'certificate', 'endowment', 'diagram', 'seal', 'illustration', 'other', 'acquisition'}
C = {'acquisition', 'ownership', 'seal', 'endowment', 'folios', 'lines', 'scribe', 'binding', 'paper', 'script', 'date', 'place',
     'incipit', 'explicit', 'dimensions', 'citation', 'author', 'title'}


def load(d):
    rows = {}
    for f in sorted(os.listdir('in' + d)):
        ids = [json.loads(l)['id'] for l in open(f'in{d}/{f}')]
        out = [json.loads(l) for l in open(f'out{d}/{f}') if l.strip()]
        assert ids == [o['id'] for o in out], f
        rows.update((o['id'], o) for o in out)
    return rows


first, second = load(''), load('2')
counts, lines = collections.Counter(), []
for i in sorted(first):
    o = second.get(i) or first[i]
    c, t = o.get('c'), o.get('t')
    if i not in second and c in T:
        c, t = None, c
    assert (c in C and not t) or (not c and t in T), (i, c, t)
    row = {'id': i}
    row.update({'c': c} if c else {'t': t})
    also = [a for a in (o.get('a') or []) if a in T and a != t]
    for k, v in (('a', also), ('ba', bool(o.get('ba'))), ('bh', o.get('bh')), ('h', o.get('h')), ('m', 'o' if i in second else None)):
        if v:
            row[k] = v
    lines.append(json.dumps(row, ensure_ascii=False, separators=(',', ':')))
    counts['continuation' if c else t] += 1
open(sys.argv[1], 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(len(lines), 'notes,', len(second), 'by the second pass')
for k, n in counts.most_common():
    print(f'  {k:14} {n:7}')
