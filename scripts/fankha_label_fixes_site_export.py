#!/usr/bin/env python3
"""The site's raw_text of the copies whose text fankha_label_fixes.py put right (fahares step 14.282).

A copy of the parser output from before the fixes (--before DIR) gives each changed copy's old text, by which the
site's copy is found (one site copy and one v2 copy holding it). The same replacements are then made in the site's own
raw_text, which keeps its page tags and spacing: each fix of the copy's lines (reconciliations/
fankha_label_fixes_step14_282.jsonl), where its old text stands exactly once. A copy is written only when every fix of
it was made and the result reads as v2's new text; one with scripts and no «خط:» line is left (the site command would
empty its scripts). Output: a decision file for `fahares:rebuild-copies`.

Usage: fankha_label_fixes_site_export.py --before scratch/fankha_v2_240 --copies FILE [--step 14.302] [--db fahares_prod]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fankha_v2_db_compare import query, rkey  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--copies', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.282', help="the step whose log of fixes is applied (reconciliations/fankha_label_fixes_step<N>.jsonl)")
    args = ap.parse_args()
    log = f"fankha_label_fixes_step{args.step.replace('.', '_')}.jsonl"
    fixes = defaultdict(list)
    for r in map(json.loads, open(ROOT / 'reconciliations' / log, encoding='utf-8')):
        fixes[r['vol']].append(r)
    changed, old_count = {}, Counter()          # old text key -> (new text, the copy's fixes)
    for f in sorted(glob.glob(str(ROOT / 'json/fankha_v2/*.json'))):
        vol = int(re.search(r'(\d+)\.json$', f).group(1))
        now = json.load(open(f, encoding='utf-8'))['works']
        was = json.load(open(os.path.join(args.before, os.path.basename(f)), encoding='utf-8'))['works']
        for wn, wb in zip(now, was):
            for cn, cb in zip(wn['copies'], wb['copies']):
                old_count[rkey(cb['raw_text'])] += 1
                if cn['raw_text'] != cb['raw_text']:
                    p = cn['provenance']
                    changed[rkey(cb['raw_text'])] = (cn['raw_text'], [x for x in fixes[vol] if p['line_start'] <= x['line'] <= p['line_end']])
    site = defaultdict(list)
    for r in query(args.db, "select json_object('id', id, 'raw', raw_text, 'shelfmark', shelfmark, 'scripts', script_names) from manuscripts where catalog_id = 1"):
        k = rkey(r['raw'])
        if k in changed:
            site[k].append(r)
    records, counts = [], Counter()
    for k, (new, fx) in changed.items():
        rows = site.get(k, [])
        if len(rows) != 1 or old_count[k] != 1:
            counts['not one copy on the site and in v2'] += 1
            continue
        raw = rows[0]['raw']
        for x in fx:
            rx = re.compile(r'\s*'.join(re.escape(w) for w in x['old'].split()))
            if len(rx.findall(raw)) != 1:
                raw = None
                break
            lead = re.match(r'\s*(?:<!--[^>]*-->\s*)?', x['old']).group(0)        # a line's own start is not the copy's
            raw = rx.sub(lambda m: x['new'][len(lead):] if lead and not m.group(0).startswith(lead) else x['new'], raw, count=1)
        if raw is None:
            counts["a fix's old text is not once in the site's text"] += 1
        elif rows[0]['scripts'] and 'خط:' not in raw:
            # fahares:rebuild-copies empties the scripts of a copy whose new text has no «خط:» line; these keep theirs
            counts['has scripts and no «خط:» line: left as it is'] += 1
        elif rkey(raw) != rkey(new):
            counts["the result is not v2's text"] += 1
        else:
            records.append({'table': 'manuscripts', 'id': rows[0]['id'], 'shelfmark': rows[0]['shelfmark'], 'category': 'text', 'v2': 'label fixes',
                            'changes': {'raw_text': {'from': rows[0]['raw'], 'to': raw}}})
            counts['copies'] += 1
    src = f"raw_text after the label fixes of the Fankha text ({log}), {date.today()}; fahares step {args.step}"
    json.dump({'source': src, 'records': records}, open(args.copies, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(changed)} v2 copies changed; {dict(counts)}', file=sys.stderr)


if __name__ == '__main__':
    main()
