#!/usr/bin/env python3
"""Field-by-field comparison of parser v2 output (json/fankha_v2) with the site database (fahares item 87, phase 3).

Read-only. Works are matched by the natural key in their slug (`-v{volume}-{ordinal}`), copies within a work by
their Fankha text (`raw_text`, page tags and spacing ignored), then by city, library and shelfmark. Local and
production ids differ, so nothing here keys on ids.

Every difference gets one category (see `categorise`). A difference that is only a `<!-- page: N -->` tag in the
database value is its own category, `page_tag_only`, not normalised away: that is the leftover of item 19. Each
difference also records whether the database still holds the v1 parser's value (`site: v1`) or something else
(`site: edited`, an approved correction, a merge or an older corpus release), and whether the column has a reviewed
correction in the audit log (`protected`, the guard of step 11.6).

    python3 scripts/fankha_v2_db_compare.py [--out DIR] [--volumes 1 2 …] [--db fahares_prod]

Writes DIR/diffs.jsonl (every difference), DIR/other_work.jsonl (copies the site keeps under another work than v2),
DIR/report.json (counts and samples) and DIR/report.md.
"""
import argparse
import glob
import json
import os
import random
import re
import subprocess
from collections import Counter, defaultdict
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_TAG = re.compile(r'<!--\s*page:\s*\d+\s*-->')
HEDGES = ('گویا', 'ظاهراً', 'ظاهرا', 'احتمالاً', 'احتمالا', 'شاید', 'منسوب به', 'به احتمال')
SAMPLES = 30
MISSING = object()                                      # no v1 record to compare with

WORK_FIELDS = {
    'clean_title': lambda w: w['title'],
    'author_name': lambda w: (w['author'] or {}).get('name'),
    'transliteration': lambda w: w['transliteration'],
    'composition_date_raw': lambda w: (w['composition'] or {}).get('date'),
    'composition_place': lambda w: (w['composition'] or {}).get('place'),
    'work_form': lambda w: w['work_form'],
    'incipit_text': lambda w: w['incipit'],
    'explicit_text': lambda w: w['explicit'],
    'description': lambda w: w['description'],
    'dedication': lambda w: w['dedication'],
    'related_work': lambda w: w['related_work'],
    'print_info': lambda w: w['print_info'],
    'bibliography': lambda w: w['bibliography'],
    'commentaries_and_glosses': lambda w: w['commentaries'],
}
V1_WORK = {'clean_title': 'clean_title', 'author_name': 'author_name', 'transliteration': 'transliteration',
           'composition_date_raw': 'composition_date', 'composition_place': 'composition_place',
           'work_form': 'work_form', 'incipit_text': 'incipit', 'explicit_text': 'explicit',
           'description': 'description', 'dedication': 'dedication', 'related_work': 'related_work',
           'print_info': 'print_info', 'bibliography': 'bibliography',
           'commentaries_and_glosses': 'commentaries_and_glosses'}


def lead_int(s):
    m = re.match(r'\s*(\d+)', s or '')
    return int(m.group(1)) if m else None


def count_of(s, unit):
    m = re.search(r'(\d+)\s*' + unit, s or '')
    return int(m.group(1)) if m else None


def ie_text(rec):
    """The site keeps «برابر1» (the work's first incipit) as text and a plain «برابر» as empty."""
    rec = rec or {}
    if rec.get('same_as_work_n'):
        return f"برابر{rec['same_as_work_n']}"
    if rec.get('same_as_ref'):
        return f"برابر {rec['same_as_ref']}"          # «برابر جلد 6» stays readable on the site
    return rec.get('text')


FLAGS = {'is_corrected': 'corrected', 'has_marginal_notes': 'marginal_notes', 'is_ruled': 'ruled',
         'has_catchwords': 'catchwords', 'is_facsimile': 'facsimile', 'is_collated': 'collated',
         'is_illuminated': 'illuminated', 'is_illustrated': 'illustrated',
         'has_author_marginalia': 'author_marginalia'}
COPY_FIELDS = {
    'city': lambda c: c['city'],
    'library': lambda c: c['library'],
    'shelfmark': lambda c: c['shelfmark'],
    'scribe_name': lambda c: c['scribes'][0]['name'] if c['scribes'] else None,
    'is_bika': lambda c: c['no_scribe'],
    'is_bita': lambda c: c['undated'],
    'is_autograph': lambda c: c['is_autograph'],
    'copy_date_raw': lambda c: (c['copy_date'] or {}).get('raw'),
    'copy_place': lambda c: (c['copy_place'] or {}).get('v'),
    'commissioned_by': lambda c: c['commissioned_by'],
    # since step 13.86 the site keeps leaves in folios and pages in pages («86گ، 170ص» holds both)
    'folios': lambda c: count_of(c['folios'], 'گ'),
    'pages': lambda c: count_of(c['folios'], 'ص'),
    'lines': lambda c: lead_int(c['lines']),
    'dimensions': lambda c: c['dimensions'],
    'paper': lambda c: c['paper'],
    'binding': lambda c: c['binding'],
    'incipit_text': lambda c: ie_text(c['incipit']),
    'explicit_text': lambda c: ie_text(c['explicit']),
    'catalog_citation': lambda c: c['catalog_citation'],
    **{col: (lambda f: lambda c: f in c['flags'])(f) for col, f in FLAGS.items()},
}
V1_COPY = {k: k for k in COPY_FIELDS}
V1_COPY.update({'scribe_name': 'scribe_name', 'catalog_citation': 'catalog_citation'})
# v2 fields with no column on the site yet: how many copies or works would gain them
NEW_COPY = {
    'contents_scope': lambda c: c['contents_scope'],
    'copy_description': lambda c: c['copy_description'],
    'original_copy': lambda c: c['original_copy'],
    'other_listings': lambda c: c['other_listings'],
    'typed_notes': lambda c: [n for n in c['notes'] if n['type'] != 'remark'],
    'seals': lambda c: c['seals'],
    'acquisition': lambda c: c['acquisition'],
    'scribe_hedge': lambda c: any(s['hedge'] for s in c['scribes']),
    'scribe_portion': lambda c: any(s['portion'] for s in c['scribes']),
    'copy_date_hedge': lambda c: (c['copy_date'] or {}).get('hedge'),
    'copy_place_hedge': lambda c: (c['copy_place'] or {}).get('hedge'),
    'extra_scribes': lambda c: len(c['scribes']) > 1,
}
NEW_WORK = {
    'author_hedge': lambda w: (w['author'] or {}).get('hedge'),
    'author_epithet': lambda w: (w['author'] or {}).get('epithet'),
    'death_hedge': lambda w: ((w['author'] or {}).get('death') or {}).get('hedge'),
    'heterogeneous': lambda w: w['heterogeneous'],
    'translator': lambda w: w['translator'],
}

# --- normalisation -------------------------------------------------------------------------------------------


def ws(s):
    return re.sub(r'\s+', ' ', s).strip()


def untag(s):
    return ws(PAGE_TAG.sub(' ', s))


def norm(s):
    s = untag(s).replace('‌', '').replace('ي', 'ی').replace('ك', 'ک').replace('ى', 'ی')
    s = re.sub(r'(?<=برابر)\s+(?=\d)', '', s)
    s = re.sub(r'[\s.،؛:,;]+', ' ', s)
    return s.strip()


def as_text(v):
    if v is None or v == '' or v == []:
        return None
    if isinstance(v, list):
        return ' ¦ '.join(as_text(x) or '' for x in v)
    if isinstance(v, dict):
        return v.get('raw') or v.get('text') or json.dumps(v, ensure_ascii=False)
    return str(v)


def removed_fate(db, v2, cat, v2_rest):
    """For text v2 takes out of a field: `moved` when it sits in another v2 field of the same record (a contents
    scope, a note, a hedge, the commissioner …), `dropped` when v2 has it nowhere."""
    if cat not in ('emptied', 'trimmed', 'trimmed_inner') or not isinstance(db, str):
        return None
    a = norm(db)
    b = norm(as_text(v2) or '')
    gone = a.replace(b, ' ', 1) if b else a
    parts = [p for p in re.split(r'\s{2,}|^\s|\s$', gone) if p.strip()] or [gone]
    gone = max(parts, key=len).strip()
    if not gone:
        return None
    return 'moved' if gone[:40] in v2_rest else 'dropped'


def categorise(db, v2):
    """One category for a difference between the database value and v2's, or None when they agree."""
    if isinstance(v2, bool) or isinstance(db, bool):
        db, v2 = bool(db), bool(v2)
        return None if db == v2 else ('flag_on' if v2 else 'flag_off')
    if isinstance(v2, int) or isinstance(db, int):
        if db == v2:
            return None
        return 'filled' if db is None else 'emptied' if v2 is None else 'different'
    d, n2 = as_text(db), as_text(v2)
    if d == n2:
        return None
    if d is None:
        return 'filled'
    if n2 is None:
        return 'page_tag_only' if not untag(d) else 'emptied'
    if PAGE_TAG.search(d) and untag(d) == ws(n2):
        return 'page_tag_only'
    a, b = norm(d), norm(n2)
    if a == b:
        return 'trivial'
    for h in HEDGES:
        if a.startswith(h + ' ') and a[len(h) + 1:].strip() == b or a.endswith(' ' + h) and a[:-len(h) - 1] == b:
            return 'hedge_split'
    if a.startswith(b):
        return 'trimmed'
    if b.startswith(a):
        return 'extended'
    if b in a:
        return 'trimmed_inner'
    if a in b:
        return 'extended_inner'
    return 'different'


# --- database ------------------------------------------------------------------------------------------------


def query(db, sql):
    """Rows of a SELECT JSON_OBJECT(...) from the local MariaDB container, one dict per line."""
    cmd = ['docker', 'exec', '-e', 'Q=' + sql, 'fahares_mariadb', 'sh', '-c',
           f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw -B -e "$Q"']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    for line in proc.stdout:
        if line.strip():
            yield json.loads(line)
    if proc.wait():
        raise SystemExit(f'query failed: {sql[:80]}')


def load_db(db, volumes):
    vols = ','.join(map(str, volumes))
    works = {}
    cols = ', '.join(f"'{c}', {c}" for c in WORK_FIELDS)
    for r in query(db, f"SELECT JSON_OBJECT('id', id, 'slug', slug, 'volume_number', volume_number, {cols}) "
                       f"FROM works WHERE volume_number IN ({vols})"):
        m = re.search(r'-v(\d+)-(\d+)$', r['slug'])
        if m:
            works.setdefault((int(m.group(1)), int(m.group(2))), []).append(r)
    copy_cols = [c for c in COPY_FIELDS if c != 'catalog_citation']
    cols = ', '.join(f"'{c}', m.{c}" for c in copy_cols)
    copies = defaultdict(list)
    for r in query(db, f"SELECT JSON_OBJECT('id', m.id, 'work_id', m.work_id, 'sequence_number', m.sequence_number, "
                       f"'raw_text', m.raw_text, 'catalog_citation', JSON_VALUE(m.metadata, '$.catalog_citation'), "
                       f"{cols}) FROM manuscripts m JOIN works w ON w.id = m.work_id "
                       f"WHERE w.volume_number IN ({vols})"):
        copies[r['work_id']].append(r)
    protected = defaultdict(set)
    for r in query(db, "SELECT JSON_OBJECT('t', auditable_type, 'id', auditable_id, 'v', new_values) FROM audit_logs "
                       "WHERE action = 'verify' AND auditable_type IN ('App\\\\Models\\\\Work', 'App\\\\Models\\\\Manuscript')"):
        vals = json.loads(r['v']) if isinstance(r['v'], str) else (r['v'] or {})
        protected[(r['t'].rsplit('\\', 1)[-1], r['id'])].update(vals)
    return works, copies, protected


# --- matching ------------------------------------------------------------------------------------------------


def rkey(raw):
    return norm(raw or '')


def shelf_key(c):
    return (norm(c.get('city') or ''), norm(c.get('library') or ''), norm(c.get('shelfmark') or ''))


def match_copies(db_copies, v2_copies):
    """Pairs (db, v2, how) plus the leftovers of each side. A v2 copy that absorbed a «همان نسخه بالا» line
    matches its database row by a raw_text prefix; the absorbed row is then `merged_in_v2`."""
    pairs, left_db = [], []
    by_raw = defaultdict(list)
    for c in v2_copies:
        by_raw[rkey(c['raw_text'])].append(c)
    used = set()
    pending = []
    for d in db_copies:
        k = rkey(d['raw_text'])
        cand = [c for c in by_raw.get(k, []) if id(c) not in used]
        if cand:
            used.add(id(cand[0]))
            pairs.append((d, cand[0], 'raw'))
        else:
            pending.append(d)
    for d in pending:
        k = rkey(d['raw_text'])
        cand = [c for c in v2_copies if id(c) not in used and k and rkey(c['raw_text']).startswith(k)]
        if len(cand) == 1:
            used.add(id(cand[0]))
            pairs.append((d, cand[0], 'raw_prefix'))
            continue
        absorbed = [c for c in v2_copies if k and k in rkey(c['raw_text'])]
        if absorbed or ('همان نسخه بالا' in (d['raw_text'] or '') and 'نسخه اصل' not in d['raw_text']):
            left_db.append((d, 'merged_in_v2'))
            continue
        sk = shelf_key(d)
        cand = [c for c in v2_copies if id(c) not in used and shelf_key(c) == sk]
        if len(cand) == 1:
            used.add(id(cand[0]))
            pairs.append((d, cand[0], 'shelfmark'))
        else:
            left_db.append((d, 'unmatched'))
    left_v2 = [c for c in v2_copies if id(c) not in used]
    return pairs, left_db, left_v2


# --- main ----------------------------------------------------------------------------------------------------


def align(v2_works, v1_works):
    """v2 ordinal -> v1 ordinal (= the site's slug ordinal). Equal while the text keeps its entries; when a page
    restored from its image adds entries (vol 10 p. 150, vol 16 p. 930) the later ordinals shift, so the two title
    sequences are aligned and an added work maps to nothing."""
    a = [norm(w['title_line']) for w in v2_works]
    b = [norm(w['primary_title']) for w in v1_works]
    if a == b:
        return {w['key']['ordinal']: w['key']['ordinal'] for w in v2_works}
    out = {}
    for blk in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            out[v2_works[blk.a + k]['key']['ordinal']] = blk.b + k + 1
    return out


def load_json(dirname, vol):
    return json.load(open(os.path.join(ROOT, 'json', dirname, f'fankha_vol_{vol:02d}.json')))['works']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'reports', 'fankha_v2_db'))
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--volumes', type=int, nargs='*', default=list(range(1, 35)))
    ap.add_argument('--seed', type=int, default=87)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    db_works, db_copies, protected = load_db(args.db, args.volumes)
    match = Counter()
    counts = Counter()          # (table, field, category) -> n
    site = Counter()            # (table, field, category, site) -> n
    fates = Counter()           # (table, field, category, moved|dropped) -> n
    prot = Counter()            # (table, field, category) -> protected n
    tag_mixed = Counter()       # (table, field) -> differences that also carry a page tag
    new = Counter()
    samples = defaultdict(list)
    seen = Counter()
    rng = random.Random(args.seed)
    out = open(os.path.join(args.out, 'diffs.jsonl'), 'w')
    other = open(os.path.join(args.out, 'other_work.jsonl'), 'w')

    def record(table, rec_id, label, field, db_val, v1_val, v2_val, raw=None, v2_rest=''):
        if field in ('folios', 'lines') and not db_val:
            db_val = None                               # the seeder stored a missing count as 0
        cat = categorise(db_val, v2_val)
        if cat is None:
            return
        key = (table, field, cat)
        counts[key] += 1
        state = 'unknown' if v1_val is MISSING else 'v1' if categorise(db_val, v1_val) is None else 'edited'
        site[key + (state,)] += 1
        is_prot = field in protected.get((table, rec_id), ())
        prot[key] += is_prot
        fate = removed_fate(db_val, v2_val, cat, v2_rest)
        if fate:
            fates[key + (fate,)] += 1
        if cat != 'page_tag_only' and isinstance(db_val, str) and PAGE_TAG.search(db_val):
            tag_mixed[(table, field)] += 1
        row = {'table': table, 'id': rec_id, 'label': label, 'field': field, 'category': cat, 'site': state, 'fate': fate,
               'protected': is_prot, 'db': db_val, 'v2': v2_val}
        out.write(json.dumps(row, ensure_ascii=False) + '\n')
        seen[key] += 1                                  # reservoir sample per category
        row = dict(row, raw=raw)
        if len(samples[key]) < SAMPLES:
            samples[key].append(row)
        elif (j := rng.randrange(seen[key])) < SAMPLES:
            samples[key][j] = row

    def compare_copy(d, c, v1c, label):
        clabel = f'{label} › {c["city"]}، {c["library"]}، {c["shelfmark"]}'
        rest = norm(json.dumps({k: v for k, v in c.items() if k != 'raw_text'}, ensure_ascii=False))
        for field, get in COPY_FIELDS.items():
            v1_val = v1c.get(V1_COPY[field]) if v1c else MISSING
            if field in ('folios', 'lines') and v1c:
                v1_val = lead_int(str(v1_val)) if v1_val else None
            record('Manuscript', d['id'], clabel, field, d.get(field), v1_val, get(c), d['raw_text'], rest)
        for k, get in NEW_COPY.items():
            new[('Manuscript', k)] += bool(get(c))

    # A copy the site keeps under another work (the vol 34 addenda attached to earlier works, merged works)
    # is looked up across all volumes by its text.
    where = {}
    for vol in args.volumes:
        for w in load_json('fankha_v2', vol):
            for i, c in enumerate(w['copies']):
                where.setdefault(rkey(c['raw_text']), (vol, w['key']['ordinal'], i))
    # works fahares:add-corpus-works made from v2 (step 13.79): their slug ordinal is the volume's next free one,
    # and the audit log keeps the v2 key they came from
    added = defaultdict(dict)                           # vol -> v2 ordinal -> site ordinal
    for r in query(args.db, "select json_object('v2', json_unquote(json_extract(a.new_values, '$.v2')), 'slug', w.slug) "
                            "from audit_logs a join works w on w.id = a.auditable_id where a.auditable_type like '%Work' "
                            "and a.action = 'create' and json_extract(a.new_values, '$.v2') is not null"):
        vol, ordinal = (int(x) for x in r['v2'][1:].split('-'))
        added[vol][ordinal] = int(r['slug'].rsplit('-', 1)[1])
    deferred = defaultdict(list)                        # vol -> (db row, label, (ordinal, index))
    aligned = {}                                        # vol -> v2 ordinal -> site ordinal
    v2_left = set()

    for vol in args.volumes:
        v2_works = load_json('fankha_v2', vol)
        v1_works = load_json('fankha', vol)
        amap = aligned[vol] = align(v2_works, v1_works)
        amap.update(added[vol])
        for w in v2_works:
            ordinal = w['key']['ordinal']
            site_ord = amap.get(ordinal)
            if site_ord is None:
                match['work_new_in_v2'] += 1
                if len(samples[('Work', '_match', 'new_in_v2')]) < SAMPLES:
                    samples[('Work', '_match', 'new_in_v2')].append({'label': f'v{vol}-{ordinal} «{w["title"]}»'})
                continue
            rows = db_works.get((vol, site_ord), [])
            if len(rows) != 1:
                match['work_' + ('missing' if not rows else 'ambiguous')] += 1
                continue
            match['work_matched'] += 1
            row = rows[0]
            v1 = v1_works[site_ord - 1] if site_ord <= len(v1_works) else None
            label = f'v{vol}-{ordinal} «{w["title"]}»'
            wrest = norm(json.dumps({k: v for k, v in w.items() if k not in ('raw_text', 'copies')}, ensure_ascii=False))
            for field, get in WORK_FIELDS.items():
                v1_val = v1.get(V1_WORK[field]) if v1 else MISSING
                db_val = row.get(field)
                if field in ('bibliography', 'commentaries_and_glosses') and isinstance(db_val, str):
                    db_val = json.loads(db_val or 'null')
                record('Work', row['id'], label, field, db_val, v1_val, get(w), w.get('raw_text'), wrest)
            for k, get in NEW_WORK.items():
                new[('Work', k)] += bool(get(w))

            v1_by_raw = {rkey(m['raw_text']): m for m in (v1 or {}).get('manuscripts', [])}
            pairs, left_db, left_v2 = match_copies(db_copies.get(row['id'], []), w['copies'])
            for d, how in left_db:
                hit = where.get(rkey(d['raw_text'])) if how == 'unmatched' else None
                if hit and hit[:2] != (vol, ordinal):
                    deferred[hit[0]].append((d, label, hit[1:]))
                    continue
                match['copy_db_' + how] += 1
                if how == 'unmatched' and len(samples[('Manuscript', '_match', how)]) < SAMPLES:
                    samples[('Manuscript', '_match', how)].append({'id': d['id'], 'label': label, 'db': d['raw_text']})
            for c in left_v2:
                v2_left.add((vol, ordinal, w['copies'].index(c)))
            for d, c, how in pairs:
                match['copy_' + how] += 1
                compare_copy(d, c, v1_by_raw.get(rkey(d['raw_text'])), label)
        print(f'vol {vol}: done', flush=True)

    for vol, items in deferred.items():
        v2_works = {w['key']['ordinal']: w for w in load_json('fankha_v2', vol)}
        v1_works = load_json('fankha', vol)
        for d, label, (ordinal, i) in items:
            c = v2_works[ordinal]['copies'][i]
            so = aligned.get(vol, {}).get(ordinal)
            v1 = v1_works[so - 1] if so else {}
            v1c = next((m for m in v1.get('manuscripts', []) if rkey(m['raw_text']) == rkey(d['raw_text'])), None)
            match['copy_other_work'] += 1
            other.write(json.dumps({'id': d['id'], 'site_work': label, 'v2_work': f'v{vol}-{ordinal} «{v2_works[ordinal]["title"]}»',
                                    'v2_page': (c.get('provenance') or {}).get('page_start'), 'raw_text': d['raw_text']},
                                   ensure_ascii=False) + '\n')
            v2_left.discard((vol, ordinal, i))
            compare_copy(d, c, v1c, f'{label} ← v{vol}-{ordinal}')
    match['copy_v2_unmatched'] = len(v2_left)
    rng.seed(args.seed)
    picked = defaultdict(list)
    for vol, ordinal, i in rng.sample(sorted(v2_left), min(SAMPLES, len(v2_left))):
        picked[vol].append((ordinal, i))
    for vol, items in sorted(picked.items()):
        works = {w['key']['ordinal']: w for w in load_json('fankha_v2', vol)}
        for ordinal, i in items:
            samples[('Manuscript', '_match', 'v2_unmatched')].append(
                {'label': f'v{vol}-{ordinal} «{works[ordinal]["title"]}»', 'v2': works[ordinal]['copies'][i]['raw_text']})
    out.close()

    def key_str(k): return ' / '.join(map(str, k))
    report = {
        'db': args.db, 'volumes': args.volumes, 'matching': dict(match),
        'protected_records': len(protected),
        'differences': [{'table': t, 'field': f, 'category': c, 'n': n,
                         'site_v1': site[(t, f, c, 'v1')], 'site_edited': site[(t, f, c, 'edited')],
                         'site_unknown': site[(t, f, c, 'unknown')],
                         'moved': fates[(t, f, c, 'moved')], 'dropped': fates[(t, f, c, 'dropped')],
                         'protected': prot[(t, f, c)]}
                        for (t, f, c), n in sorted(counts.items(), key=lambda x: (x[0][0], x[0][1], -x[1]))],
        'page_tag_with_other_change': {key_str(k): n for k, n in tag_mixed.items()},
        'new_fields': {key_str(k): n for k, n in sorted(new.items())},
        'samples': {key_str(k): v for k, v in samples.items()},
    }
    json.dump(report, open(os.path.join(args.out, 'report.json'), 'w'), ensure_ascii=False, indent=1)
    write_md(report, os.path.join(args.out, 'report.md'))


def short(v, n=160):
    s = as_text(v) if not isinstance(v, (bool, int)) else str(v)
    s = (s or '∅').replace('\n', ' ⏎ ')
    return s if len(s) <= n else s[:n] + '…'


def write_md(r, path):
    L = [f"# v2 در برابر {r['db']}", '', '## تطبیق', '']
    L += [f'- `{k}`: {v:,}' for k, v in sorted(r['matching'].items())]
    L += ['', f"رکوردهای دارای اصلاح داوری‌شده در لاگ ممیزی: {r['protected_records']}", '',
          '## اختلاف‌ها', '', '| جدول | فیلد | دسته | شمار | هنوز v1 | ویرایش‌شده | حفاظت‌شده | جابه‌جا | حذف |', '|---|---|---|---|---|---|---|---|---|']
    L += [f"| {d['table']} | {d['field']} | {d['category']} | {d['n']:,} | {d['site_v1']:,} | {d['site_edited']:,} | {d['protected']} | {d['moved']:,} | {d['dropped']:,} |"
          for d in r['differences']]
    L += ['', '## برچسب صفحه همراه تغییر دیگر', '']
    L += [f'- {k}: {v:,}' for k, v in r['page_tag_with_other_change'].items()]
    L += ['', '## فیلدهای تازه‌ی v2 (بی ستون در سایت)', '']
    L += [f'- {k}: {v:,}' for k, v in r['new_fields'].items()]
    L += ['', '## نمونه‌ها (۵ از هر دسته؛ ۳۰ در report.json)', '']
    for k, rows in r['samples'].items():
        L += [f'### {k}', '']
        for x in rows[:5]:
            L.append(f"- {x.get('label', '')} (#{x.get('id', '')}, {x.get('site', '')})")
            if 'db' in x:
                L.append(f"  - DB: {short(x['db'])}")
            if 'v2' in x:
                L.append(f"  - v2: {short(x['v2'])}")
        L.append('')
    open(path, 'w').write('\n'.join(L))


if __name__ == '__main__':
    main()
