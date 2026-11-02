#!/usr/bin/env python3
"""Copies' catalogue citations printed «page-volume», put back as «volume-page» (fahares step 14.12, item 112).

Usage:
  fankha_reversed_copy_citations.py [--db fahares_prod]                 list each citation and the text it finds
  fankha_reversed_copy_citations.py --write                             correct text/fankha/*.txt
  fankha_reversed_copy_citations.py --export OUT [--db fahares_prod]    the decision file for `fahares:fix-reversed-citations`

Fankha cites a copy's catalogue «volume-page» («[نشریه: 7-104]»), but some citations are printed the other way
round: vol. 4 p. 986 has «[فیلمها ف: 3-250]» and, a few lines below, «[فیلمها ف: 160-3]». The text has them as
printed, so the site reads volume 160, page 3. The print cannot tell which order a citation means; the catalogue
can. A citation is taken as reversed when the site has tied the copy to a catalogue (--db, a copy of production)
and its first number is not one of the catalogue's volumes while its second is: «[ف مخ: 314-1]» of a catalogue in 3
volumes is volume 1, page 314. A catalogue's volumes are those the site holds and those its copies cite at least 5
times and in 1% of its citations, since the site may hold fewer volumes than the copies cite (the photo catalogue
of the Great Islamic Encyclopaedia has one, its copies cite two): «[عکسی - ف: 2-1]» there is left alone. Only the two numbers the site read as volume and page are swapped,
so «[اهدائی رهبر: 524-3 و ف: 21-1032]» keeps its second citation.

The citation is found in the copy's own block: in the volume's text, after the heading line «N. city؛ library؛
شماره نسخه: …» the site's raw text starts with, the citation as the site has it, allowing for spaces and page
markers between its parts. A citation not found once is left out and listed.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT.parent / 'fahares'
GAP = r'(?:\s|<!--\s*page:\s*\d+\s*-->)*'
PAGE = re.compile(r'<!--\s*page:\s*\d+\s*-->')


def query(db: str, sql: str) -> list[dict]:
    """Rows of json_object() from the site's database, read with its own database user."""
    env = dict(line.split('=', 1) for line in (SITE / '.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    out = subprocess.run(['docker', 'exec', '-i', '-e', f'MYSQL_PWD={env["DB_PASSWORD"]}', 'fahares_mariadb', 'mariadb', f'-u{env["DB_USERNAME"]}', db, '-N', '--raw'],
                         input=sql, capture_output=True, text=True, check=True).stdout
    return [json.loads(line) for line in out.split('\n') if line]


def candidates(db: str) -> list[dict]:
    """Each copy whose cited volume is not one of its catalogue's volumes while its cited page is one of them."""
    return query(db, """
        with tot as (select source_id, count(*) n from source_entries
                     where legacy_type = 'fankha_citation' and source_id is not null group by source_id),
        volumes as (select e.source_id, e.volume_number v from source_entries e join tot on tot.source_id = e.source_id
                    where e.legacy_type = 'fankha_citation' and e.volume_number is not null
                    group by e.source_id, e.volume_number having count(*) >= greatest(5, 0.01 * max(tot.n))
                    union select source_id, volume_number from source_volumes)
        select json_object('id', m.id, 'volume', m.volume_number, 'shelfmark', m.shelfmark, 'raw', m.raw_text,
            'citation', json_unquote(json_extract(m.metadata, '$.catalog_citation')), 'cited', e.citation_text,
            'a', e.volume_number, 'b', e.page_start, 'source', s.code,
            'volumes', (select group_concat(v order by v) from volumes where volumes.source_id = e.source_id))
        from source_entries e
        join sources s on s.id = e.source_id
        join manuscripts m on m.id = e.legacy_id
        where e.legacy_type = 'fankha_citation' and e.volume_number is not null
          and not exists (select 1 from volumes where volumes.source_id = e.source_id and volumes.v = e.volume_number)
          and exists (select 1 from volumes where volumes.source_id = e.source_id and volumes.v = e.page_start)
        order by m.volume_number, m.id""")


def pattern(citation: str) -> str:
    tokens = re.findall(r'\d+|[\[\]]|[^\s\d\[\]]+', PAGE.sub(' ', citation))
    return GAP.join(re.escape(t) for t in tokens)


def swapped(text: str, a: int, b: int) -> str | None:
    """The text with «a-b» made «b-a», or None when it does not hold that pair once."""
    pair = re.compile(r'(?<!\d)' + str(a) + r'(' + GAP + r'[-–]' + GAP + r')' + str(b) + r'(?!\d)')
    if len(pair.findall(text)) != 1:
        return None
    return pair.sub(lambda m: f'{b}{m.group(1)}{a}', text)


def heading(raw: str) -> str:
    return re.sub(r'^\d+\.\s*', '', raw.split('\n')[0].strip())


def locate(c: dict, text: str) -> tuple[tuple[int, int] | None, str]:
    """The span of the copy's citation in its volume's text, or None with the reason."""
    head = heading(c['raw'] or '')
    spans = []
    for m in re.finditer(pattern(c['cited']), text):
        h = text.rfind('شماره نسخه:', 0, m.start())
        start, end = text.rfind('\n', 0, h) + 1, text.find('\n', h)
        if re.sub(r'^\d+\.\s*', '', text[start:end].strip()) == head:
            spans.append((m.start(), m.end()))
    if len(spans) != 1:
        return None, f'{len(spans)} places in the text'
    return spans[0], ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--export')
    ap.add_argument('--db', default='fahares_prod')
    args = ap.parse_args()

    texts, found, missing = {}, [], []
    for c in candidates(args.db):
        vol = c['volume']
        if vol not in texts:
            texts[vol] = (ROOT / f'text/fankha/fankha_vol_{vol:02d}.txt').read_text(encoding='utf-8')
        span, why = locate(c, texts[vol])
        new = span and swapped(texts[vol][span[0]:span[1]], c['a'], c['b'])
        if not new:
            missing.append(f'#{c["id"]} v{vol} «{c["cited"]}»: {why or "the pair is not there once"}')
            continue
        found.append((c, span, new))

    for c, (s, e), new in found:
        print(f'#{c["id"]} v{c["volume"]} {c["source"]} (volumes {c["volumes"]}): {texts[c["volume"]][s:e]!r} → {new!r}')
    print(f'{len(found)} citations found, {len(missing)} left out')
    for m in missing:
        print('  left out:', m)

    if args.export:
        records, skipped = [], []
        for c, span, new in found:
            fixed = {key: swapped(c[key] or '', c['a'], c['b']) for key in ('citation', 'raw')}
            if not fixed['citation'] or not fixed['raw']:
                skipped.append(f'#{c["id"]}: the site\'s citation or raw text does not hold «{c["a"]}-{c["b"]}» once')
                continue
            records.append({'id': c['id'], 'volume': c['volume'], 'shelfmark': c['shelfmark'], 'source': c['source'],
                            'pair': [c['a'], c['b']],
                            'changes': {'catalog_citation': {'from': c['citation'], 'to': fixed['citation']},
                                        'raw_text': {'from': c['raw'], 'to': fixed['raw']}}})
        Path(args.export).write_text(json.dumps({'from': 'fankha text before step 14.12', 'to': 'reversed copy citations put right (step 14.12)',
                                                 'records': records}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'{len(records)} copies written to {args.export}')
        for s in skipped:
            print('  not exported:', s)

    if args.write:
        by_volume = {}
        for c, span, new in found:
            by_volume.setdefault(c['volume'], []).append((span, new))
        for vol, fixes in by_volume.items():
            text = texts[vol]
            # from the end, so the earlier spans keep their place
            for (s, e), new in sorted(fixes, reverse=True):
                text = text[:s] + new + text[e:]
            (ROOT / f'text/fankha/fankha_vol_{vol:02d}.txt').write_text(text, encoding='utf-8')
        print(f'{len(found)} citations corrected in {len(by_volume)} volumes')


if __name__ == '__main__':
    main()
