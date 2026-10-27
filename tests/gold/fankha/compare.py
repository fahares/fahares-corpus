#!/usr/bin/env python3
"""Per-field accuracy of the current Fankha parser against the gold set."""
import glob, json, re, sys
from collections import Counter, defaultdict

G = sys.argv[1]
PAGE = re.compile(r'<!--\s*page:\s*\d+\s*-->')

def norm(s):
    if s is None: return None
    if isinstance(s, bool): return s
    s = PAGE.sub(' ', str(s))
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('‌', '').replace('ـ', '')
    s = re.sub(r'\s+', ' ', s).strip(' ،؛.,;:')
    return s or None

def fw(s, n=5): s = norm(s); return ' '.join(s.split()[:n]) if s else None
def lw(s, n=5): s = norm(s); return ' '.join(s.split()[-n:]) if s else None
def lst(x): return sorted({norm(i) for i in (x or []) if norm(i)})
def digits(s): return sorted(re.findall(r'\d+', s or '')) or None

def P_work(p):
    t = (p.get('primary_title') or '').split(' = ')[0]
    return {
        'title': norm(t), 'alt_titles': lst(p['alternative_titles']), 'subjects': lst(p['subjects']),
        'languages': lst(p['languages']), 'transliteration': norm(p['transliteration']),
        'author_name': norm(p['author_name']), 'author_hedged': p['authorship_status'] != 'certain',
        'author_death_digits': digits(p['author_death_date_raw']), 'translator_name': norm(p['translator_name']),
        'is_heterogeneous': p['is_heterogeneous'], 'composition_date': norm(p['composition_date']),
        'composition_place': norm(p['composition_place']), 'related_work': norm(p['related_work']),
        'description_fw': fw(p['description']), 'description_lw': lw(p['description']),
        'incipit_fw': fw(p['incipit']), 'explicit_lw': lw(p['explicit']),
        'bibliography_present': bool(p['bibliography']),
    }

def G_work(g):
    return {
        'title': norm(g['title']), 'alt_titles': lst(g['alt_titles']), 'subjects': lst(g['subjects']),
        'languages': lst(g['languages']), 'transliteration': norm(g['transliteration']),
        'author_name': norm(g['author_name']), 'author_hedged': bool(g.get('author_hedge')),
        'author_death_digits': digits(g.get('author_death_raw')), 'translator_name': norm(g.get('translator_name')),
        'is_heterogeneous': bool(g['is_heterogeneous']), 'composition_date': norm(g.get('composition_date')),
        'composition_place': norm(g.get('composition_place')), 'related_work': norm(g.get('related_work')),
        'description_fw': fw(g.get('description_fw')), 'description_lw': lw(g.get('description_lw')),
        'incipit_fw': fw(g.get('incipit_fw')), 'explicit_lw': lw(g.get('explicit_lw')),
        'bibliography_present': bool(g.get('bibliography_present')),
    }

FLAGS = {'is_corrected': 'corrected', 'has_marginal_notes': 'marginal_notes', 'is_illuminated': 'illuminated',
         'is_illustrated': 'illustrated', 'is_facsimile': 'facsimile'}
MS_SIMPLE = ['city', 'library', 'shelfmark', 'scribe_name', 'copy_date_raw', 'copy_place', 'commissioned_by',
             'folios', 'lines', 'text_dimensions', 'dimensions', 'paper', 'binding', 'defects', 'catalog_citation']

def P_ms(p):
    r = {k: norm(p[k]) for k in MS_SIMPLE}
    r.update(seq=p['sequence_number'], scripts=lst(p['scripts']), is_autograph=p['is_autograph'],
             is_bika=p['is_bika'], is_bita=p['is_bita'], incipit_fw=fw(p['incipit_text']),
             explicit_lw=lw(p['explicit_text']), contents_scope=norm(p['contents_note']),
             flags=sorted(v for k, v in FLAGS.items() if p.get(k)))
    return r

def G_ms(g):
    r = {k: norm(g.get(k)) for k in MS_SIMPLE}
    r.update(seq=g.get('seq'), scripts=lst(g.get('scripts')), is_autograph=bool(g.get('is_autograph')),
             is_bika=bool(g.get('is_bika')), is_bita=bool(g.get('is_bita')), incipit_fw=fw(g.get('incipit_fw')),
             explicit_lw=lw(g.get('explicit_lw')), contents_scope=norm(g.get('contents_scope')),
             flags=sorted(set(g.get('flags') or []) & set(FLAGS.values())))
    return r

parsed = {json.loads(l)['uid']: json.loads(l) for l in open(f'{G}/parsed_v1.1.6.jsonl')}
units = {json.loads(l)['uid']: json.loads(l) for l in open(f'{G}/units.jsonl')}
gold = {}
for f in sorted([f'{G}/gold.jsonl']) + [f'{G}/gold_overrides.jsonl']:
    try:
        for l in open(f):
            if l.strip():
                o = json.loads(l); gold.setdefault(o['uid'], {}).update(o)
    except FileNotFoundError:
        pass

tot, ok = Counter(), Counter()
mism = defaultdict(list)
leak = Counter()
for uid, g in gold.items():
    p = parsed[uid]
    for k, v in p.items():
        vals = v if isinstance(v, list) else [v]
        if any(isinstance(x, str) and PAGE.search(x) for x in vals): leak[(p['kind'], k)] += 1
    a, b = (P_work(p), G_work(g)) if g['kind'] == 'work' else (P_ms(p), G_ms(g))
    for k in b:
        key = (g['kind'], k)
        # count a field only where either side has a value (presence-aware accuracy)
        if b[k] in (None, [], False) and a[k] in (None, [], False): continue
        tot[key] += 1
        if a[k] == b[k]: ok[key] += 1
        else: mism[key].append((uid, units[uid]['stratum'], b[k], a[k]))

with open(f'{G}/accuracy.json', 'w') as fh:
    json.dump({'fields': {f'{k[0]}.{k[1]}': [ok[k], tot[k]] for k in sorted(tot)},
               'page_tag_leaks_in_sample': {f'{k[0]}.{k[1]}': n for k, n in leak.items()}}, fh, ensure_ascii=False, indent=1)
with open(f'{G}/mismatches.jsonl', 'w') as fh:
    for k in sorted(mism):
        for uid, s, gv, pv in mism[k]:
            fh.write(json.dumps({'field': f'{k[0]}.{k[1]}', 'uid': uid, 'stratum': s, 'gold': gv, 'parser': pv}, ensure_ascii=False) + '\n')
print(f'gold units: {len(gold)}')
for k in sorted(tot, key=lambda k: ok[k] / tot[k]):
    print(f'{k[0]:4} {k[1]:22} {ok[k]:4}/{tot[k]:<4} {100*ok[k]/tot[k]:5.1f}%')
print('page-tag leaks (sample):', dict(leak))

# ---- adjusted metric: design differences of the current JSON are not errors ----
BASE = ['نستعلیق', 'نسخ', 'شکسته', 'تعلیق', 'رقعه', 'رقعی', 'کوفی', 'ثلث', 'ریحان', 'محقق', 'تایپی', 'لاتین', 'چلیپا']
def bases(xs): return sorted({b for x in xs for b in BASE if b in (x or '')} - ({'رقعی'} and set()))
atot, aok = Counter(), Counter()
amism = defaultdict(list)
for uid, g in gold.items():
    p = parsed[uid]
    if g['kind'] == 'work':
        a, b = P_work(p), G_work(g)
        a['transliteration'] = norm(p['transliteration']); b['transliteration'] = norm((g['transliteration'] or '').split(' = ')[0])
        for k, full, gv in (('incipit_fw', p['incipit'], g.get('incipit_fw')), ('explicit_lw', p['explicit'], g.get('explicit_lw')),
                            ('description_fw', p['description'], g.get('description_fw')), ('description_lw', p['description'], g.get('description_lw'))):
            f, gv = norm(full), norm(gv)
            ok_ = (f == gv) if not (f and gv) else (f.startswith(gv) or gv.startswith(f[:len(gv)]) if k.endswith('fw') else f.endswith(gv))
            a[k], b[k] = (b[k] if ok_ else a[k]), b[k]
    else:
        a, b = P_ms(p), G_ms(g)
        if b['seq'] is None and a['seq'] == 1: a['seq'] = None
        a['scripts'] = bases(a['scripts'] + [p.get('script') if not p['scripts'] else ''][:0]); b['scripts'] = bases(b['scripts'])
        if b['scripts'] == ['تایپی'] and not a['scripts']: a['scripts'] = ['تایپی']
        for k, full, gv, flag in (('incipit_fw', p['incipit_text'], g.get('incipit_fw'), p['incipit_matches_work']),
                                  ('explicit_lw', p['explicit_text'], g.get('explicit_lw'), p['explicit_matches_work'])):
            f, gv = norm(full), norm(gv)
            if gv == 'برابر': ok_ = (f is None and flag) or f == 'برابر'
            elif not (f and gv): ok_ = f == gv
            else: ok_ = f.startswith(gv) if k == 'incipit_fw' else f.endswith(gv)
            a[k] = b[k] if ok_ else a[k]
        a.pop('contents_scope'); b.pop('contents_scope')   # parser field has other semantics; reported separately
    for k in b:
        key = (g['kind'], k)
        if b[k] in (None, [], False) and a[k] in (None, [], False): continue
        atot[key] += 1
        if a[k] == b[k]: aok[key] += 1
        else: amism[key].append(uid)
print('\nADJUSTED')
for k in sorted(atot, key=lambda k: aok[k] / atot[k]):
    if aok[k] < atot[k]: print(f'{k[0]:4} {k[1]:22} {aok[k]:4}/{atot[k]:<4} {100*aok[k]/atot[k]:5.1f}%  {amism[k][:6]}')
json.dump({f'{k[0]}.{k[1]}': [aok[k], atot[k], amism[k]] for k in atot}, open(f'{G}/accuracy_adjusted.json', 'w'), ensure_ascii=False, indent=1)
