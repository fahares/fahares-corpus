#!/usr/bin/env python3
"""Copies' catalogue citations with a second opening bracket, put right (fahares step 14.41, item 112).

Usage:
  fankha_stray_bracket_citations.py [--db fahares_prod]                 list each citation and the text it finds
  fankha_stray_bracket_citations.py --write                             correct text/fankha/*.txt
  fankha_stray_bracket_citations.py --export OUT [--db fahares_prod]    the decision file for `fahares:fix-reversed-citations`

Some 60 citations have an opening bracket after the series' colon: «[ف: [1851 - 10]», «[ف: 32- [73]», «[نشریه:
[103-2]». The print has one bracket; the second keeps the site from reading the volume, so most of these copies are
on no volume. The bracket goes, and where the numbers are printed «page-volume» they are put back as «volume-page»,
by the rule of `fankha_reversed_copy_citations.py`: the first number is not one of the catalogue's volumes and the
second is. The catalogue is the one the site ties the copy to, or, for a copy on none, the catalogue its library's
other copies citing the same series are on (when nine in ten of them are on it). The decision file names that
catalogue and volume for a copy on none, so the site can tie it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fankha_reversed_copy_citations import ROOT, PAGE, locate, pattern, query, swapped  # noqa: E402

STRAY = r'^\[[^]\[]{1,40}: *[-0-9 –]*\[[-–0-9 /]+\]$'


def candidates(db: str) -> list[dict]:
    return query(db, f"""
        select json_object('id', m.id, 'volume', m.volume_number, 'shelfmark', m.shelfmark, 'raw', m.raw_text, 'library', m.library_id,
            'citation', json_unquote(json_extract(m.metadata, '$.catalog_citation')), 'source', s.code)
        from manuscripts m
        left join source_entries e on e.legacy_type = 'fankha_citation' and e.legacy_id = m.id
        left join sources s on s.id = e.source_id
        where json_unquote(json_extract(m.metadata, '$.catalog_citation')) regexp '{STRAY.replace(chr(92), chr(92) * 2)}'
        order by m.volume_number, m.id""")


def series(citation: str) -> str:
    return re.sub(r'\s+', ' ', citation[1:citation.index(':')]).strip()


def library_catalogue(db: str, library: int, name: str) -> str | None:
    """The catalogue nine in ten of the library's copies citing the series are on."""
    rows = query(db, f"""
        select json_object('code', s.code, 'n', count(*)) from manuscripts m
        join source_entries e on e.legacy_type = 'fankha_citation' and e.legacy_id = m.id
        join sources s on s.id = e.source_id
        where m.library_id = {int(library)} and json_unquote(json_extract(m.metadata, '$.catalog_citation')) like '[{name.replace(chr(39), '')}:%'
        group by s.code order by count(*) desc""")
    total = sum(r['n'] for r in rows)
    return rows[0]['code'] if rows and rows[0]['n'] >= 0.9 * total else None


def volumes(db: str, code: str) -> list[int]:
    """The catalogue's volumes: those the site holds and those its copies cite at least 5 times and in 1%."""
    rows = query(db, f"""
        with src as (select id from sources where code = '{code}'),
        tot as (select count(*) n from source_entries where legacy_type = 'fankha_citation' and source_id = (select id from src))
        select json_object('v', v) from (
            select volume_number v from source_volumes where source_id = (select id from src)
            union select volume_number from source_entries where legacy_type = 'fankha_citation' and source_id = (select id from src)
                and volume_number is not null group by volume_number having count(*) >= greatest(5, 0.01 * (select n from tot))) x""")
    return sorted(r['v'] for r in rows if r['v'] is not None)


def corrected(citation: str, have: list[int]) -> tuple[str, list[int]]:
    """The citation without its second bracket, its numbers «volume-page», and those numbers."""
    head, tail = citation[:citation.index(':') + 1], citation[citation.index(':') + 1:]
    tail = tail.replace('[', '', 1)
    fixed = head + tail
    # a page marker in the citation is the print's page break, not a number of it
    numbers = [int(n) for n in re.findall(r'\d+', PAGE.sub(' ', tail))[:2]]
    # «188 - 27/1» (volume 27, part 1) is left as it is: only its bracket goes
    if len(numbers) == 2 and have and numbers[0] not in have and numbers[1] in have and not re.search(r'\d\s*/\s*\d', PAGE.sub(' ', tail)):
        fixed = swapped(fixed, numbers[0], numbers[1]) or fixed
        numbers = numbers[::-1]
    return fixed, numbers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--export')
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()

    texts, found, missing = {}, [], []
    cache = {}
    for c in candidates(args.db):
        vol = c['volume']
        if vol not in texts:
            texts[vol] = (ROOT / f'text/fankha/fankha_vol_{vol:02d}.txt').read_text(encoding='utf-8')
        code = c['source']
        tie = None
        if code is None and series(c['citation']) == 'ف':
            code = cache.setdefault((c['library'], 'ف'), library_catalogue(args.db, c['library'], 'ف'))
            tie = code
        have = cache.setdefault(code, volumes(args.db, code)) if code else []
        fixed, numbers = corrected(c['citation'], have)
        c['cited'] = c['citation']
        span, why = locate(c, texts[vol])
        if not span:
            missing.append(f'#{c["id"]} v{vol} «{c["citation"]}»: {why}')
            continue
        text = texts[vol][span[0]:span[1]]
        new_text = corrected(text, have)[0]
        # a copy on no volume is tied to the one its corrected citation names, «volume-page» of a volume the catalogue has
        # only when the other number is no volume: «31-16» of a catalogue of fifty volumes could be either
        volume = numbers[0] if tie and len(numbers) == 2 and numbers[0] in have and numbers[1] not in have \
            and not re.search(r'\d\s*/\s*\d', fixed) else None
        found.append((c, span, new_text, fixed, {'source': tie, 'volume': volume} if tie and volume else None, have))

    for c, (s, e), new, fixed, tie, _ in found:
        print(f'#{c["id"]} v{c["volume"]} {c["source"] or "-"}: {texts[c["volume"]][s:e]!r} → {new!r}' + (f'  tie {tie["source"]} v{tie["volume"]}' if tie else ''))
    print(f'{len(found)} citations found, {len(missing)} left out')
    for m in missing:
        print('  left out:', m)

    if args.export:
        records = []
        for c, span, new, fixed, tie, have in found:
            raw = c['raw'] or ''
            # the site's raw text holds the citation as the text does, page marker and all
            spans = [(m.start(), m.end()) for m in re.finditer(pattern(c['citation']), raw)]
            if len(spans) != 1:
                print(f'  not exported: #{c["id"]}: the site\'s raw text holds its citation {len(spans)} times')
                continue
            a, b = spans[0]
            new_raw = raw[:a] + corrected(raw[a:b], have)[0] + raw[b:]
            rec = {'id': c['id'], 'volume': c['volume'], 'shelfmark': c['shelfmark'], 'source': c['source'],
                   'changes': {'catalog_citation': {'from': c['citation'], 'to': fixed},
                               'raw_text': {'from': raw, 'to': new_raw}}}
            if tie:
                rec['tie'] = tie
            records.append(rec)
        Path(args.export).write_text(json.dumps({'from': 'fankha text before step 14.41', 'to': 'stray brackets of copy citations taken out (step 14.41)',
                                                 'category': 'stray_bracket', 'records': records}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'{len(records)} copies written to {args.export}')

    if args.write:
        by_volume = {}
        for c, span, new, fixed, tie, _ in found:
            by_volume.setdefault(c['volume'], []).append((span, new))
        for vol, fixes in by_volume.items():
            text = texts[vol]
            for (s, e), new in sorted(fixes, reverse=True):
                text = text[:s] + new + text[e:]
            (ROOT / f'text/fankha/fankha_vol_{vol:02d}.txt').write_text(text, encoding='utf-8')
        print(f'{len(found)} citations corrected in {len(by_volume)} volumes')


if __name__ == '__main__':
    main()
