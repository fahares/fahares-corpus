#!/usr/bin/env python3
"""Per-field accuracy of parser v2 (json/fankha_v2) against the gold set (gold_version 2).

Usage: compare_v2.py [--mismatches FILE]   prints the table; returns per-field results via evaluate()."""
import json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
PAGE = re.compile(r'<!--\s*page:\s*\d+\s*-->')


def norm(s):
    if s is None or isinstance(s, bool):
        return s
    s = PAGE.sub(' ', str(s)).replace('ي', 'ی').replace('ك', 'ک').replace('‌', '').replace('ـ', '')
    s = re.sub(r'\s+', ' ', s).strip(' ،؛.,;:«»"')
    return s or None


def lst(x): return sorted({norm(i) for i in (x or []) if norm(i)})
def digits(s): return sorted(re.findall(r'\d+', s or '')) or None
def starts(full, fw): f, g = norm(full), (re.sub(r'^برابر\s*\d{0,2}$', 'برابر', norm(fw) or '') or None); return f == g if not (f and g) else f.startswith(g)
def ends(full, lw): f, g = norm(full), norm(lw); return f == g if not (f and g) else f.endswith(g)
def first_line(raw): return norm(re.sub(r'^\d+\s*[\.\-]\s*', '', PAGE.sub(' ', raw).strip().split('\n')[0]))


def scripts_key(items): return sorted((norm(i['type']), tuple(sorted(norm(q) for q in i['qualifiers']))) for i in items or [])


def ie(rec):
    if not rec: return None
    return 'برابر' if rec['same_as_work'] else rec['text']


FLAGS = ['corrected', 'marginal_notes', 'illuminated', 'illustrated', 'facsimile']


def work_fields(w, g):
    a = w.get('author') or {}
    d = a.get('death') or {}
    het = w.get('heterogeneous')
    tr = ' = '.join([w['transliteration']] + w['alt_transliterations']) if w['transliteration'] else None
    return {
        'title': (norm((w['title_line'] or '').split(' = ')[0]), norm(g['title'])),
        'alt_titles': (lst(w['alt_titles']), lst(g['alt_titles'])),
        'subjects': (lst(w['subjects']), lst(g['subjects'])),
        'languages': (lst(w['languages']), lst(g['languages'])),
        'transliteration': (norm(tr), norm(g['transliteration'])),
        'author_name': (norm(a.get('name')), norm(g['author_name'])),
        'author_hedge': (bool(a.get('hedge')), bool(g.get('author_hedge'))),
        'author_epithet': (norm(a.get('epithet')), norm(g.get('author_epithet'))),
        'author_death_digits': (digits(d.get('raw')), digits(g.get('author_death_raw'))),
        'death_hedge': (bool(d.get('hedge')), bool(g.get('death_hedge'))),
        'translator_name': (norm((w.get('translator') or {}).get('name')), norm(g.get('translator_name'))),
        'is_heterogeneous': (het is not None, bool(g['is_heterogeneous'])),
        'heterogeneous_qualifier': ((het or {}).get('qualifier'), g.get('heterogeneous_qualifier')),
        'composition_date': (norm((w.get('composition') or {}).get('date')), norm(g.get('composition_date'))),
        'composition_place': (norm((w.get('composition') or {}).get('place')), norm(g.get('composition_place'))),
        'related_work': (norm(w['related_work']), norm(g.get('related_work'))),
        'description_fw': (True if starts(w['description'], g.get('description_fw')) else norm(w['description']), True if g.get('description_fw') or w['description'] else None),
        'description_lw': (True if ends(w['description'], g.get('description_lw')) else norm(w['description']), True if g.get('description_lw') or w['description'] else None),
        'incipit_fw': (True if starts(w['incipit'], g.get('incipit_fw')) else norm(w['incipit']), True if g.get('incipit_fw') or w['incipit'] else None),
        'explicit_lw': (True if ends(w['explicit'], g.get('explicit_lw')) else norm(w['explicit']), True if g.get('explicit_lw') or w['explicit'] else None),
        'bibliography_present': (bool(w['bibliography']), bool(g.get('bibliography_present'))),
    }


def copy_fields(c, g):
    sc = c['scribes']
    oc = c.get('original_copy') or {}
    notes = [n['text'] for n in c['notes']] + ([c['copy_description']] if c['copy_description'] else [])
    gnote = norm(g.get('ms_note'))
    note_ok = None
    if gnote:
        cand = [norm(x) for x in notes + [c['contents_scope'] or '', oc.get('raw') or '']] + \
               [norm('نسخه اصل: ' + (oc.get('raw') or '')), norm('اصل نسخه: ' + (oc.get('raw') or ''))]
        note_ok = any(x and (x.startswith(gnote) or gnote.startswith(x[:len(gnote)])) for x in cand if x)
    guess = [n for n in c['notes'] if n['type'] in ('scribe_guess', 'date_guess')]
    def s(x): return norm(x)
    return {
        'seq': (c['key']['seq'], g.get('seq')),
        'city': (s(c['city']), s(g['city'])), 'library': (s(c['library']), s(g['library'])),
        'shelfmark': (s(c['shelfmark']), s(g['shelfmark'])),
        'scripts': (scripts_key(c['scripts']), scripts_key(g.get('scripts'))),
        'scribe_name': (s(' و '.join(x['name'] for x in sc)) if sc else None, s(g.get('scribe_name'))),
        'scribe_hedge': (any(x['hedge'] for x in sc) or bool(c['autograph_hedge']), bool(g.get('scribe_hedge'))),
        'scribe_portion': (s(sc[0]['portion']) if sc else None, s(g.get('scribe_portion'))),
        'is_autograph': (c['is_autograph'], bool(g.get('is_autograph'))),
        'is_bika': (c['no_scribe'], bool(g.get('is_bika'))), 'is_bita': (c['undated'], bool(g.get('is_bita'))),
        'copy_date_raw': (s((c['copy_date'] or {}).get('raw')), s(g.get('copy_date_raw'))),
        'date_hedge': (bool((c['copy_date'] or {}).get('hedge')), bool(g.get('date_hedge'))),
        'guess_note': (bool(guess), bool(g.get('scribe_guess') or g.get('date_guess'))),
        'copy_place': (s((c['copy_place'] or {}).get('v')), s(g.get('copy_place'))),
        'commissioned_by': (s(c['commissioned_by']), s(g.get('commissioned_by'))),
        **{k: (s(c[k]), s(g.get(k))) for k in ('folios', 'text_dimensions', 'dimensions', 'paper', 'binding', 'defects')},
        'incipit_fw': (True if starts(ie(c['incipit']), g.get('incipit_fw')) else s(ie(c['incipit'])), True if g.get('incipit_fw') or c['incipit'] else None),
        'explicit_lw': (True if ends(ie(c['explicit']), g.get('explicit_lw')) else s(ie(c['explicit'])), True if g.get('explicit_lw') or c['explicit'] else None),
        'lines': (s(' '.join(x for x in (c['lines'], c['lines_note']) if x)), s(g.get('lines'))),
        'contents_scope': (s(c['contents_scope']), s(g.get('contents_scope'))),
        'note_placed': (note_ok, True if gnote else None),
        'original_copy_raw': (s(oc.get('raw')), s(g.get('original_copy_raw'))),
        'catalog_citation': (s(c['catalog_citation']), s(g.get('catalog_citation'))),
        'flags': (sorted(set(c['flags']) & set(FLAGS)), sorted(set(g.get('flags') or []) & set(FLAGS))),
    }


def load_v2():
    vols = {}
    def vol(v):
        if v not in vols:
            vols[v] = json.load(open(os.path.join(ROOT, 'json', 'fankha_v2', f'fankha_vol_{v:02d}.json')))
        return vols[v]
    return vol


def evaluate(prefix=''):
    """prefix '' = development gold set; 'holdout_' = the held-out set not used while writing the parser."""
    units = {json.loads(l)['uid']: json.loads(l) for l in open(os.path.join(HERE, prefix + 'units.jsonl'))}
    v1 = {json.loads(l)['uid']: json.loads(l) for l in open(os.path.join(HERE, prefix + 'parsed_v1.1.6.jsonl'))}
    gold = [json.loads(l) for l in open(os.path.join(HERE, prefix + 'gold.jsonl'))]
    vol = load_v2()
    tot, ok, mism = Counter(), Counter(), defaultdict(list)
    missing = []
    for g in gold:
        u, p = units[g['uid']], v1[g['uid']]
        wid = g['uid'].split('m')[0] if g['kind'] == 'ms' else g['uid']
        pw = v1.get(wid)
        v = u['vol']
        # locate the v2 work: same title line, nearest page
        title = (pw or p)['primary_title'] if g['kind'] == 'work' or pw else None
        works = vol(v)['works']
        if g['kind'] == 'work':
            cands = [w for w in works if norm(w['title_line']) == norm(p['primary_title'])]
            rl = [x.strip() for x in PAGE.sub(' ', u['raw']).split('\n') if x.strip()]
            tl = norm(rl[1]) if len(rl) > 1 else None
            same = [w for w in cands if norm(' = '.join([w['transliteration'] or ''] + w['alt_transliterations'])) == tl]
            cands = same or cands
            # same title on one page («جنگ», «جنگ نامه»): the author line of the entry decides
            al = norm(rl[2]) if len(rl) > 2 else ''
            own = [w for w in cands if w['author'] and al.startswith(norm(w['author']['name_raw'] or '-'))]
            cands = own or cands
            page = p['page_start']
        else:
            cands = [w for w in works if norm(w['title_line']) == norm(u['work_title'])]
            page = p['page_start']
        if not cands:
            missing.append(g['uid']); continue
        w = min(cands, key=lambda w: abs(w['provenance']['page_start'] - page))
        idx = int(wid.split('w')[1]) if g['kind'] == 'work' else None
        if idx is not None and idx < len(works) and norm(works[idx]['title_line']) == norm(p['primary_title']) \
                and works[idx] in cands and works[idx]['provenance']['page_start'] == page:
            w = works[idx]                     # same segmentation as v1: the ordinal is exact
        # (an ordinal can shift when the text gains entries, e.g. a page restored from its image; then the
        # transliteration and page decide)
        if g['kind'] == 'work':
            fields = work_fields(w, g)
        else:
            fl = first_line(u['raw'])
            cs = sorted((c for w_ in cands for c in w_['copies'] if first_line(c['raw_text']) == fl),
                        key=lambda c: (c['key']['seq'] != g.get('seq'), abs(c['provenance']['page_start'] - page)))
            if g.get('merged_into_previous'):
                ol = [x for w_ in cands for c in w_['copies'] for x in c['other_listings']]
                lib = (g.get('other_listing') or {}).get('library') or g.get('library')
                ok_ = any(norm(x['library']) == norm(lib) for x in ol) and not cs
                fields = {'merged_into_previous': (ok_, True)}
            elif not cs:
                missing.append(g['uid']); continue
            else:
                fields = copy_fields(cs[0], g)
        for k, (pv, gv) in fields.items():
            key = (g['kind'], k)
            if pv is True and gv is None: continue
            if gv in (None, [], False) and pv in (None, [], False): continue
            tot[key] += 1
            if pv == gv: ok[key] += 1
            else: mism[key].append((g['uid'], gv, pv))
    return tot, ok, mism, missing


if __name__ == '__main__':
    tot, ok, mism, missing = evaluate('holdout_' if '--holdout' in sys.argv else '')
    print('units not found in v2 output:', missing)
    for k in sorted(tot, key=lambda k: ok[k] / tot[k]):
        print(f'{k[0]:4} {k[1]:24} {ok[k]:4}/{tot[k]:<4} {100 * ok[k] / tot[k]:5.1f}%')
    if '--mismatches' in sys.argv:
        with open(sys.argv[sys.argv.index('--mismatches') + 1], 'w') as fh:
            for k in sorted(mism):
                for uid, gv, pv in mism[k]:
                    fh.write(json.dumps({'field': f'{k[0]}.{k[1]}', 'uid': uid, 'gold': gv, 'v2': pv}, ensure_ascii=False) + '\n')
