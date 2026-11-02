#!/usr/bin/env python3
"""Copies' shelfmarks put right in the Fankha text, and the site's diff for them (fahares step 13.148).

Usage:
  fankha_shelfmark_fixes.py --fixes FILE                  list each fix and the text line it finds
  fankha_shelfmark_fixes.py --fixes FILE --write          correct text/fankha/*.txt
  fankha_shelfmark_fixes.py --fixes FILE --export OUT --db fahares_prod
                                                          the decision file for `fahares:rebuild-copies`

FILE is a JSON list of {id, volume, page, library, from, to, why}: the copy's site id, its Fankha volume and printed
page, the library as the text names it, its shelfmark as the text has it and as it should be. The fixes come from
fahares step 13.148: shelfmarks whose two first numbers came out swapped («1/2591/104» for the library's
«2591/1/104», «2/15980» for «15980/2»), Golpayegani's «6/105-1015» for the printed «1015-6/105», and digits misread
(«15725/8» for the printed «15775/8»).

A fix is made on the copy's heading line «N. city؛ library؛ شماره نسخه: FROM…»: in the volume's text, among the
lines of that library with that shelfmark, the one under the page marker nearest to the copy's page. A fix whose
line is not found, or found twice on one page, is left out and listed.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT.parent / 'fahares'
PAGE = re.compile(r'<!--\s*page:\s*(\d+)\s*-->')


def heading(library: str, shelfmark: str) -> re.Pattern:
    # the shelfmark ends where the line does, or at a space or a letter that is not part of a number
    return re.compile(r'؛\s*' + re.escape(library) + r'\s*؛\s*شماره نسخه:\s*(' + re.escape(shelfmark) + r')(?![\d/])')


def locate(fix: dict, lines: list[str]) -> tuple[int | None, str]:
    """The index of the copy's heading line in its volume's text, or None with the reason."""
    pat = heading(fix['library'], fix['from'])
    page, found = 0, []
    for i, line in enumerate(lines):
        for m in PAGE.finditer(line):
            page = int(m.group(1))
        if pat.search(line):
            found.append((abs(page - fix['page']), i))
    if not found:
        return None, 'line not found'
    found.sort()
    if len(found) > 1 and found[0][0] == found[1][0]:
        return None, f'{len(found)} lines as near to page {fix["page"]}'
    if found[0][0] > 2:
        return None, f'nearest line is {found[0][0]} pages away'
    return found[0][1], ''


def corrected(line: str, fix: dict) -> str:
    pat = heading(fix['library'], fix['from'])
    return pat.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + fix['to'], line, count=1)


def site_rows(db: str, ids: list[int]) -> dict[int, dict]:
    """The copies as the site keeps them (id, shelfmark, raw_text), read with the site's own database user."""
    env = dict(line.split('=', 1) for line in (SITE / '.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    sql = f"select json_object('id', id, 'shelfmark', shelfmark, 'raw', raw_text) from manuscripts where id in ({','.join(map(str, ids))})"
    out = subprocess.run(['docker', 'exec', '-i', '-e', f'MYSQL_PWD={env["DB_PASSWORD"]}', 'fahares_mariadb', 'mariadb', f'-u{env["DB_USERNAME"]}', db, '-N', '--raw'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    return {r['id']: r for r in (json.loads(line) for line in out.split('\n') if line)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixes', required=True)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--export')
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    fixes = json.loads(Path(args.fixes).read_text(encoding='utf-8'))

    texts, found, missing = {}, [], []
    for fix in fixes:
        if fix['volume'] not in texts:
            texts[fix['volume']] = (ROOT / f'text/fankha/fankha_vol_{fix["volume"]:02d}.txt').read_text(encoding='utf-8').split('\n')
        i, why = locate(fix, texts[fix['volume']])
        if i is None:
            missing.append(f'#{fix["id"]} v{fix["volume"]} p{fix["page"]} «{fix["from"]}»: {why}')
            continue
        found.append((fix, i, texts[fix['volume']][i], corrected(texts[fix['volume']][i], fix)))
    for fix, i, old, new in found:
        print(f'#{fix["id"]} v{fix["volume"]}:{i + 1} ({fix["why"]})\n  - {old[:140]}\n  + {new[:140]}')
    print(f'{len(found)} lines found, {len(missing)} left out')
    for m in missing:
        print('  left out:', m)

    if args.export:
        rows = site_rows(args.db, [f['id'] for f, *_ in found])
        records, skipped = [], []
        for fix, i, old, new in found:
            row = rows.get(fix['id'])
            raw = (row or {}).get('raw') or ''
            if not row or row['shelfmark'] != fix['from'] or 'شماره نسخه: ' not in raw:
                skipped.append(f'#{fix["id"]}: the site has «{(row or {}).get("shelfmark")}»')
                continue
            head = heading(fix['library'], fix['from'])
            new_raw = head.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + fix['to'], raw, count=1)
            changes = {'shelfmark': {'from': row['shelfmark'], 'to': fix['to']}}
            if new_raw != raw:
                changes['raw_text'] = {'from': raw, 'to': new_raw}
            records.append({'table': 'manuscripts', 'id': fix['id'], 'shelfmark': row['shelfmark'], 'category': 'shelfmark',
                            'v2': f'v{fix["volume"]}:{i + 1} {fix["why"]}', 'changes': changes})
        Path(args.export).write_text(json.dumps({'from': 'fankha text before step 13.148', 'to': 'shelfmarks put right (step 13.148)',
                                                 'records': records}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'{len(records)} copies written to {args.export}')
        for s in skipped:
            print('  not exported:', s)

    if args.write:
        by_volume = {}
        for fix, i, old, new in found:
            by_volume.setdefault(fix['volume'], {})[i] = (old, new)
        for vol, lines in by_volume.items():
            text = texts[vol]
            for i, (old, new) in lines.items():
                assert text[i] == old
                text[i] = new
            (ROOT / f'text/fankha/fankha_vol_{vol:02d}.txt').write_text('\n'.join(text), encoding='utf-8')
        print(f'{len(found)} lines corrected in {len(by_volume)} volumes')


if __name__ == '__main__':
    main()
