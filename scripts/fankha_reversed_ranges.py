#!/usr/bin/env python3
"""Page ranges in works' citation brackets that the OCR read reversed, put back as printed (fahares step 13.124).

Usage:
  fankha_reversed_ranges.py                      list what would change
  fankha_reversed_ranges.py --write              correct text/fankha/*.txt
  fankha_reversed_ranges.py --export FILE --db fahares_prod
                                                 the diff file for `fahares:apply-corpus-diff`, from the works of --db
                                                 (a copy of production) whose bibliography holds a reversed citation

In a «volume: pages» citation the print has the first page, then the second, often shortened: «۳۵۵۰-۵۱» for pages
3550-3551 (Fankha vol. 22 p. 93), «۱۰۳-۱۰۴» (vol. 1 p. 298). The OCR has put some of these the other way round:
«فهرستواره منزوی 5: 51-3550», «الذریعة 15: 104-103». Two shapes are taken as reversed:
  short   the first number shorter than the second («51-3550»), which no range is as printed
  falling two numbers of the same length, the first greater («104-103»)
«309: 1-310» (page 309 of volume 1 to page 310, a colon for Fankha's slash) is not touched, nor any other range.
Only bracket lines (a work's citations) are read.
"""
import argparse
import glob
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RANGE = re.compile(r'(?<![\d/:])(\d+)(\s*:\s*)(\d+)(\s*-\s*)(\d+)(?![\d/:-])')


def fixed(m: re.Match) -> str | None:
    vol, colon, a, dash, b = m.groups()
    if len(a) <= 2 and int(a) < int(vol) and len(vol) >= 2 and 0 < abs(int(b) - int(vol)) <= 20:
        return None  # «309: 1-310»
    if len(a) < len(b) or (len(a) == len(b) and int(a) > int(b)):
        return f'{vol}{colon}{b}{dash}{a}'
    return None


def changes():
    """Each reversed range: volume, line number, the line, and the line corrected."""
    for path in sorted(glob.glob(str(ROOT / 'text/fankha/fankha_vol_*.txt'))):
        vol = int(re.search(r'(\d+)\.txt$', path).group(1))
        for n, line in enumerate(Path(path).read_text(encoding='utf-8').split('\n'), 1):
            if not line.startswith('['):
                continue
            new = RANGE.sub(lambda m: fixed(m) or m.group(0), line)
            if new != line:
                yield vol, n, line, new


def site_works(db: str, vol: int, needle: str) -> list[dict]:
    """The works of the volume whose bibliography holds the citation, as the site keeps them."""
    sql = (f"select json_object('id', id, 'slug', slug, 'title', primary_title, 'bib', bibliography, 'raw', raw_text) from works "
           f"where volume_number = {vol} and bibliography like '%{needle.replace(chr(39), chr(39) * 2)}%'")
    out = subprocess.run(['docker', 'exec', '-i', 'fahares_mariadb', 'sh', '-c', f'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" {db} -N --raw'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    rows = []
    for line in filter(None, out.split('\n')):
        r = json.loads(line)
        bib = r['bib'] if isinstance(r['bib'], list) else json.loads(r['bib'] or '[]')
        rows.append({'id': r['id'], 'slug': r['slug'], 'title': r['title'], 'bibliography': bib, 'raw_text': r['raw']})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--export')
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()
    found = list(changes())
    for vol, n, old, new in found:
        print(f'v{vol}:{n}\n  - {old}\n  + {new}')
    print(f'{len(found)} lines')

    if args.export:
        works, missing = [], []
        for vol, n, old, new in found:
            # the citations the line splits into, as the site keeps them («؛» parts of the bracket)
            pairs = [(o.strip(), w.strip()) for o, w in zip(old.strip('[]').split('؛'), new.strip('[]').split('؛')) if o != w]
            # looked for by the reversed range itself: the site's JSON writes «/» as «\\/»
            needle = next((m.group(0) for m in RANGE.finditer(pairs[0][0]) if fixed(m)), None) if pairs else None
            rows = site_works(args.db, vol, needle) if needle else []
            if len(rows) != 1:
                missing.append(f'v{vol}:{n} {len(rows)} works on the site: {pairs}')
                continue
            row = rows[0]
            bib = [x for x in row['bibliography']]
            for o, w in pairs:
                bib = [w if x == o else x for x in bib]
            if bib == row['bibliography']:
                missing.append(f'v{vol}:{n} #{row["id"]}: the site bibliography differs ({row["bibliography"]})')
                continue
            fields = {'bibliography': {'old': row['bibliography'], 'new': bib}}
            if row['raw_text'] and old in row['raw_text']:
                fields['raw_text'] = {'old': None, 'new': None, 'patches': [{'old': old, 'new': new}]}
            works.append({'volume': vol, 'number': row['slug'].rsplit('-', 1)[-1], 'title': row['title'], 'fields': fields})
        Path(args.export).write_text(json.dumps({'from': 'fankha text before step 13.124', 'to': 'reversed ranges put back (step 13.124)',
                                                 'works': works}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'{len(works)} works written to {args.export}')
        for m in missing:
            print('  not exported:', m)

    if args.write:
        by_file = {}
        for vol, n, old, new in found:
            by_file.setdefault(vol, {})[n] = (old, new)
        for vol, lines in by_file.items():
            path = ROOT / f'text/fankha/fankha_vol_{vol:02d}.txt'
            text = path.read_text(encoding='utf-8').split('\n')
            for n, (old, new) in lines.items():
                assert text[n - 1] == old
                text[n - 1] = new
            path.write_text('\n'.join(text), encoding='utf-8')
        print(f'{len(found)} lines corrected in {len(by_file)} volumes')


if __name__ == '__main__':
    main()
