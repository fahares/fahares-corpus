#!/usr/bin/env python3
"""One-time migration of gold.jsonl to the user's rulings (fahares item 87, plan sections 6-8, 5 Aban 1405).

Kept for audit; running it twice is harmless (it is idempotent)."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'scripts'))
from fankha_parser_v2 import parse_scripts  # noqa: E402

PAGE = re.compile(r'<!--\s*page:\s*\d+\s*-->')
units = {json.loads(l)['uid']: json.loads(l) for l in open(os.path.join(HERE, 'units.jsonl'))}
gold = [json.loads(l) for l in open(os.path.join(HERE, 'gold.jsonl'))]

OVR = {
    'v15w00424': {'heterogeneous_qualifier': 'doubtful'},
    'v10w00201': {'heterogeneous_qualifier': 'partial'},
    'v26w00129m273': {'scribe_portion': 'ورق اول و چند ورق از آخر'},
    'v27w01046m7': {'scribe_name': None, 'scribe_hedge': None, 'is_bika': True,
                    'scribe_guess': 'محمد بن علی تستری - کاتب جلد ربا', 'scribe_guess_hedge': 'احتمالاً'},
    'v33w01274m17': {'copy_date_raw': None, 'date_hedge': None, 'is_bita': True,
                     'date_guess': 'در عصر ناظم', 'date_guess_hedge': 'شاید'},
    'v18w01020': {'death_hedge': '؟'}, 'v20w00442': {'death_hedge': '؟'}, 'v07w01189': {'death_hedge': '؟'},
    'v13w01767': {'author_name': 'علی بن ابی طالب (ع)', 'author_epithet': 'امام اول', 'author_hedge': 'منسوب به'},
    'v15w00604mNone': {'contents_scope': None},
    # annotation slips found while adjudicating v2 (raw text checked)
    'v26w01153m9': {'contents_scope': 'شامل: 1. قصاید، 2. اوصاف الاشراف، 3. رساله دلگشا، 4. نامه، 5. ریش نامه، 6. فالنامه'},
    'v02w00184m1': {'paper': 'فرنگی'},
    'v03w00295': {'description_lw': 'مقصد 6. انساب فاطمیین'},   # «چاپ:» is print_info, not description
    # «همان نسخه بالا» without «نسخه اصل»: not a copy of its own, merged into the previous copy (section 7)
    'v34w01611m11': {'merged_into_previous': True,
                     'other_listing': {'city': 'مشهد', 'library': 'مولوی', 'shelfmark': '666'}},
}

for g in gold:
    g['gold_version'] = 2
    if g['kind'] == 'ms':
        if g.get('scripts') and isinstance(g['scripts'][0], str):
            g['scripts'] = parse_scripts('، '.join(g['scripts']))
        raw = PAGE.sub(' ', units[g['uid']]['raw'])
        m = re.search(r'(?:نسخه\s+اصل[یی]?|اصل\s+نسخه)\s*:\s*([^؛\n\[]+)', raw)
        g['original_copy_raw'] = ' '.join(m.group(1).split()).strip(' ،.') if m else None
        g.setdefault('scribe_portion', None)
    else:
        g.setdefault('heterogeneous_qualifier', None)
        g.setdefault('author_epithet', None)
        g.setdefault('death_hedge', None)
        if re.search(r'[؟?]', g.get('author_death_raw') or ''):   # ruling 5
            g['death_hedge'] = '؟'
    g.update(OVR.get(g['uid'], {}))

with open(os.path.join(HERE, 'gold.jsonl'), 'w') as fh:
    for g in gold:
        fh.write(json.dumps(g, ensure_ascii=False) + '\n')
print(len(gold), 'units migrated;', sum(1 for g in gold if g['uid'] in OVR), 'overrides')
