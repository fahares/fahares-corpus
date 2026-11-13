#!/usr/bin/env python3
"""A copy's date (copy_date_raw) that carries the text after it (fahares item 87, step 14.165): a gift
(«اهدایی: رهبری، خرداد 1373»), a commission («به فرموده آقا بابا خان»), a remark on the copying. v2 reads the date
alone. Here the site's date is cut where v2's ends, keeping the site's own spelling, and the cut text goes where the
copy's page still shows it: a gift, endowment or seal to metadata's ownership_and_seals, anything else to the date's
note (copy_date_note, shown under the date). rebuild-copies then sets the sortable year from the cut date, and
DerivedData its range, so a gift's year no longer stands for the copy's.
Left out: a tail that is part of the date, which the site reads for its range or certainty (a hedge «؟», «گویا»,
«ظاهراً», «احتمالاً»; the author's time «در عصر مؤلف», «در حیات مؤلف»; a bare «ق»); a value v2 does not hold as the
start of the site's; a cut that leaves no number or century (v2 then
holds a name or a word, not the date); a date protected by a reviewed correction.
Input: a fankha_v2_db_compare.py report. Output: a fahares:rebuild-copies file.
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

def key(ch):
    """A character's part in the comparison: letters and digits (a date's year counts), Arabic forms as Persian."""
    return letters(ch) or (ch if ch.isdigit() else '')


def cut(site, v2):
    """The site's date up to where v2's ends, letter and digit for letter and digit; None when v2's is not its start."""
    want = ''.join(map(key, v2))
    have = ''.join(map(key, site))
    if len(want) < 2 or not have.startswith(want) or have == want:
        return None
    n = 0
    for i, ch in enumerate(site):
        n += len(key(ch))
        if n >= len(want):
            # a date's number does not stop in the middle
            if ch.isdigit() and i + 1 < len(site) and site[i + 1].isdigit():
                return None
            j = i + 1
            # a bracket opened in the kept text closes there
            if site[j:j + 1] == ')' and site[:j].count('(') > site[:j].count(')'):
                j += 1
            return site[:j].rstrip()
    return None


# what the site reads as part of the date (CopyDateRange: hedges and the author's time)
DATE_PART = re.compile(r'؟|\?|گویا|ظاهر|احتمال|محتمل|تقریب|حدود|اوایل|اواخر|اواسط|نیمه|(?:عصر|زمان|حیات|حیوة|روزگار)\s*(?:مؤلف|مولف|مصنف|شارح|ناظم)|'
                       r'^\s*[(،]?\s*ق\s*\)?\s*$|^\s*(?:ق|ه|هـ|ش|م)\b')
OWNERSHIP = re.compile(r'^(?:اهدا|اهدایی|وقف|واقف|مهر|تملک)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default='fahares_prod')
    ap.add_argument('--step', default='14.165')
    args = ap.parse_args()
    rows = [d for d in map(json.loads, open(Path(args.report) / 'diffs.jsonl', encoding='utf-8'))
            if d['table'] == 'Manuscript' and d['field'] == 'copy_date_raw' and d['category'] == 'trimmed' and not d['protected']]
    ids = sorted({int(d['id']) for d in rows})
    site = {}
    for i in range(0, len(ids), 500):
        part = ','.join(map(str, ids[i:i + 500]))
        for r in q(args.db, "select json_object('id', id, 'shelfmark', shelfmark, 'copy_date_raw', copy_date_raw, 'copy_date_note', copy_date_note, "
                            f"'metadata', metadata) from manuscripts where id in ({part})"):
            r['metadata'] = json.loads(r['metadata']) if isinstance(r['metadata'], str) else (r['metadata'] or {})
            site[r['id']] = r
    out, counts = [], Counter()
    for d in rows:
        s = site.get(int(d['id']))
        if not s or s['copy_date_raw'] != d['db']:
            counts['changed since the report'] += 1
            continue
        new = cut(s['copy_date_raw'], d['v2'] or '')
        if not new:
            counts['v2 not its start'] += 1
            continue
        # v2's date with no number or century left (a scribe's name, «صفر», «تاریخ پایان رساله»): v2 is wrong there
        if not re.search(r'\d|قرن|سده', new):
            counts['v2 keeps no date'] += 1
            continue
        tail = s['copy_date_raw'][len(new):].strip(' ،؛.,:\n')
        if not tail:
            counts['nothing after it'] += 1
            continue
        if DATE_PART.search(tail):
            counts['tail is part of the date'] += 1
            continue
        changes = {'copy_date_raw': {'from': s['copy_date_raw'], 'to': new}}
        meta = s['metadata']
        held = letters(json.dumps(meta, ensure_ascii=False)) + letters(s['copy_date_note'] or '')
        if letters(tail) in held:
            counts['tail already held'] += 1
        elif OWNERSHIP.match(tail):
            m2 = json.loads(json.dumps(meta))
            m2['ownership_and_seals'] = (m2.get('ownership_and_seals') or []) + [tail]
            changes['metadata'] = {'from': meta, 'to': m2}
            counts['to ownership'] += 1
        else:
            note = f"{s['copy_date_note']}؛ {tail}" if s['copy_date_note'] else tail
            changes['copy_date_note'] = {'from': s['copy_date_note'], 'to': note[:255]}
            counts['to the date note'] += 1
        out.append({'table': 'manuscripts', 'id': s['id'], 'shelfmark': s['shelfmark'], 'category': 'rebuild',
                    'v2': d['label'].split(' ')[0], 'changes': changes})
    Path(args.out).write_text(json.dumps({'source': f"a copy's date cut where v2's ends, the rest kept as the date's note or an ownership line ({args.report}), {date.today()}; fahares step {args.step}",
                                          'records': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'copies', dict(counts))


if __name__ == '__main__':
    main()
