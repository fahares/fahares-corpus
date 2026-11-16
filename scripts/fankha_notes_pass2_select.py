#!/usr/bin/env python3
"""The notes of the second pass (Opus): where the first pass (Sonnet) and v2's rule name two different types, where
the first pass set a continuation of a field or a free-text field name, typed «other», or a type outside the list.
Run in scratch/notes_typing (in/, out/); writes in2/ in chunks of 150 and rule_types.json."""
import collections, glob, hashlib, json, os
T = {'contents', 'annex', 'marginalia', 'cataloguer', 'transcription', 'decoration', 'codicology', 'ownership', 'collation',
     'certificate', 'endowment', 'diagram', 'seal', 'illustration', 'other', 'acquisition'}
rule = collections.defaultdict(collections.Counter)
def walk(o):
    if isinstance(o, dict):
        for n in o.get('notes') or []:
            if isinstance(n, dict) and 'text' in n:
                rule[hashlib.sha1(n['text'].encode()).hexdigest()[:12]][n['type']] += 1
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
for f in glob.glob('../../json/fankha_v2/*.json'): walk(json.load(open(f)))
json.dump({i: c.most_common(1)[0][0] for i, c in rule.items()}, open('rule_types.json', 'w'))
picked, why = [], collections.Counter()
for f in sorted(os.listdir('in')):
    ins = [json.loads(l) for l in open('in/' + f)]
    outs = [json.loads(l) for l in open('out/' + f)]
    assert [i['id'] for i in ins] == [o['id'] for o in outs], f
    for i, o in zip(ins, outs):
        c, t, r = o.get('c'), o.get('t'), rule[i['id']].most_common(1)[0][0]
        k = None
        if c and c not in T: k = 'continuation'
        elif not c and t not in T: k = 'stray'
        elif (c or t) == 'other': k = 'other'
        elif r != 'other' and r != (c or t) and r not in (o.get('a') or []): k = 'disagree'
        if k:
            why[k] += 1; picked.append(i)
os.makedirs('in2', exist_ok=True); os.makedirs('out2', exist_ok=True)
for n in range(0, len(picked), 150):
    with open('in2/chunk_%04d.jsonl' % (n // 150), 'w') as fh:
        for i in picked[n:n + 150]: fh.write(json.dumps(i, ensure_ascii=False) + '\n')
print(len(picked), dict(why), 'chunks', (len(picked) + 149) // 150)
