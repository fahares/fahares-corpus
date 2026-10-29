#!/usr/bin/env python3
"""
Flag Fankha pages whose OCR text may have its two columns out of order (fahares item 87 follow-up).

On a two-column page the right column is printed first. When the OCR read the left column first, or read a
column twice, or dropped one, the text alone shows it in a few ways. Each volume is parsed in-process with
parser v2 (the text, not json/fankha_v2/, which may be stale), and these signals are collected:

  seq_back     a copy number lower than or equal to the one before it in the same work (strong)
  seq_gap      a copy number that skips ahead
  seq_typo     one misprinted number between two that are two apart (1, 2, 114, 4): reported, not scored
  seq_first    a work whose first copy number is not 1
  title_order  an entry title (work or referral) whose first three letters break the order of its neighbours
  bib_in_copy  a work-level bibliography («دنا … نسخه», «الذریعة») read as a copy's citation (strong)
  two_phys     two physical-description lines («خط:») or two catalogue citations in one copy (strong)
  mid_field    a copy whose text ends on a label or a separator («تا:», «،», «؛»)
  empty_copy   a copy with a header line and nothing else
  dup_lines    a run of text lines with two or more copy headers, repeated within 3000 lines (strong)
  tool_text    English prose (an OCR tool's error, a model's reasoning) in place of print (strong)
  lost_page    a page with no text whose image is full of print (strong)
  thin_page    a page whose text is short for the ink on its image, e.g. one column dropped (strong)

The two page signals need the page images (FAHARES_IMAGES, default the fahares checkout's
storage/app/public/catalogs/fankha); without them, or without Pillow and numpy, they are skipped.

Every flag is mapped to the page where it occurs. Output: one line per flagged page, strongest first,
or JSON with --json.

Usage: fankha_column_check.py [--json] [--no-images] [VOL ...]   (default: all 34 volumes, one process per core)
"""
import json
import os
import re
import sys
from collections import defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_parser_v2 import parse_volume, prepare, split_entries  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.environ.get('FAHARES_IMAGES', os.path.join(os.path.dirname(ROOT), 'fahares', 'storage', 'app',
                                                       'public', 'catalogs', 'fankha'))
PAGE_TAG = re.compile(r'<!--\s*page:\s*(\d+)\s*-->')
ENGLISH = re.compile(r"\b(?:request|blocked|filters|wait|let me|I'm|I am|cannot|seems|actually|maybe|hmm|"
                     r"looks like|the text|the image|column)\b", re.I)
STRONG = {'tool_text', 'seq_back', 'bib_in_copy', 'two_phys', 'dup_lines', 'lost_page', 'thin_page'}
WEIGHT = {'seq_back': 3, 'bib_in_copy': 3, 'two_phys': 3, 'dup_lines': 3, 'seq_gap': 2, 'seq_first': 1,
          'title_order': 1, 'mid_field': 2, 'empty_copy': 2, 'seq_typo': 0, 'lost_page': 5, 'thin_page': 4, 'tool_text': 5}

ALPHABET = 'ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی'
ORDER = {ch: i for i, ch in enumerate(ALPHABET)}
FOLD = str.maketrans({'آ': 'ا', 'أ': 'ا', 'إ': 'ا', 'ٱ': 'ا', 'ة': 'ه', 'ۀ': 'ه', 'ي': 'ی', 'ى': 'ی', 'ئ': 'ی',
                      'ء': 'ی', 'ك': 'ک', 'ؤ': 'و'})


def sort_key(title: str) -> str:
    """Letters only, a leading «ال» dropped, «ة» and a word-final «ت» as «ه», «ء» as «ی».

    Fankha sorts «وحدت» with «وحدة» and «تحفه» with «تحفة», letter by letter across spaces."""
    t = re.sub(r'ت(?=[\s‌(]|$)', 'ه', title.strip().translate(FOLD))
    if t.startswith('ال') and len(t) > 3:
        t = t[2:]
    return ''.join(ch for ch in t if ch in ORDER)


def key_tuple(title: str, n: int = 3):
    return tuple(ORDER[ch] for ch in sort_key(title)[:n])


def check_volume(vol: int, text: str):
    flags = []  # (page, signal, detail)
    data = parse_volume(vol, text)

    # copy numbers and copy shapes
    for w in data['works']:
        copies = w['copies']
        title = w['title']
        seqs = [c['key']['seq'] for c in copies]
        if seqs and seqs[0] not in (None, 1) and len(copies) > 1:
            flags.append((copies[0]['provenance']['page_start'], 'seq_first', f'{title}: starts at {seqs[0]}'))
        # a single misprinted number between two that are two apart (1, 2, 114, 4) is a print typo
        typos = {i for i in range(1, len(seqs) - 1)
                 if None not in seqs[i - 1:i + 2] and seqs[i + 1] == seqs[i - 1] + 2 and seqs[i] != seqs[i - 1] + 1}
        for i in range(1, len(copies)):
            a, b = seqs[i - 1], seqs[i]
            if a is None or b is None or b == a + 1:
                continue
            page = copies[i]['provenance']['page_start']
            if i in typos or i - 1 in typos:
                flags.append((page, 'seq_typo', f'{title}: {a} → {b}'))
            elif b <= a:
                flags.append((page, 'seq_back', f'{title}: {a} → {b}'))
            else:
                flags.append((page, 'seq_gap', f'{title}: {a} → {b}'))
        for i, c in enumerate(copies):
            page = c['provenance']['page_start']
            raw = c['raw_text']
            body = [l.strip() for l in raw.split('\n')[1:] if l.strip()]
            cit = c['catalog_citation'] or ''
            if re.search(r'دنا\s*\d|الذریعة|الذريعة', cit) and re.search(r'نسخه\)', cit):
                flags.append((c['provenance']['page_end'], 'bib_in_copy', f'{title} #{c["key"]["seq"]}: {cit[:60]}'))
            if sum(1 for l in body if l.startswith('خط:')) > 1 or \
                    sum(1 for l in body if re.search(r'\[(?:ف|نشریه|اهدائی)[^\]]*\]\s*$', l)) > 1:
                flags.append((page, 'two_phys', f'{title} #{c["key"]["seq"]}'))
            last_copy_of_vol = False
            if not body and not last_copy_of_vol:
                flags.append((page, 'empty_copy', f'{title} #{c["key"]["seq"]}'))
            elif body and re.search(r'(?:[:،؛\-–]|\bتا|\bجلد|\bکا)$', body[-1]) and not body[-1].endswith(']'):
                flags.append((c['provenance']['page_end'], 'mid_field', f'{title} #{c["key"]["seq"]}: …{body[-1][-30:]}'))

    # alphabetical order of all entries (works and referrals) in text order
    lines = prepare(text)
    entries = []
    for kind, ls in split_entries(lines):
        head = ls[0].text
        if kind == 'work':
            t = head.lstrip('●').split('/')[0].split('=')[0]
        else:
            t = head.partition('←')[0]
        entries.append((ls[0].page_start, t.strip(), key_tuple(t)))
    for i in range(1, len(entries) - 1):
        p, c, n = entries[i - 1][2], entries[i][2], entries[i + 1][2]
        if not p or not c or not n:
            continue
        if (c < p and n >= p) or (c > n and p <= n):
            flags.append((entries[i][0], 'title_order',
                          f'{entries[i - 1][1][:25]} | {entries[i][1][:25]} | {entries[i + 1][1][:25]}'))

    # English prose from the OCR tool or a language model in place of the printed text
    for l in lines:
        if len(ENGLISH.findall(l.text)) >= 2:
            flags.append((l.page_start, 'tool_text', f'line {l.no}: {l.text.strip()[:60]}'))

    # runs of three or more repeated text lines (blank lines skipped) holding two or more copy headers;
    # a work's header lines and one-copy entries repeat legitimately in commentary families and collections
    body = [l for l in lines if l.text.strip() and not l.text.lstrip().startswith('●')]
    seen = defaultdict(list)
    for idx, l in enumerate(body):
        seen[l.text.strip()].append(idx)
    reported = set()
    for idx, l in enumerate(body):
        if idx in reported or len(l.text.strip()) < 40:
            continue
        for j in seen[l.text.strip()]:
            if not idx < j < idx + 3000:
                continue
            n = 0
            while j + n < len(body) and idx + n < j and body[idx + n].text.strip() == body[j + n].text.strip():
                n += 1
            if n >= 3 and sum('شماره نسخه' in body[idx + k].text for k in range(n)) >= 2:
                reported.update(range(idx, idx + n))
                flags.append((body[j].page_start, 'dup_lines',
                              f'{n} lines from {body[idx].no} again at {body[j].no}: {l.text.strip()[:40]}'))
                break
    return flags


def ink(vol: int, page: int):
    """Percentage of dark pixels on the page image, or None."""
    try:
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(os.path.join(IMAGES, f'v{vol:02d}', f'p{page:04d}.webp')).convert('L'))
    except Exception:
        return None
    return float((a < 128).mean()) * 100


def check_pages(vol: int, text: str):
    """Pages whose text is short for the print on their image (lost pages and dropped columns)."""
    parts = PAGE_TAG.split(text)
    sizes = [(int(parts[i]), len(re.sub(r'\s', '', parts[i + 1]))) for i in range(1, len(parts), 2)]
    if not sizes:
        return []
    ratios, inks = [], {}
    for page, n in sizes:
        k = ink(vol, page)
        if k is None:
            continue
        inks[page] = k
        if n and k > 2:
            ratios.append(n / k)
    if not ratios:
        return []
    ratios.sort()
    med = ratios[len(ratios) // 2]
    flags = []
    for page, n in sizes:
        k = inks.get(page)
        if k is None or k <= 1.5:   # blank, divider or plate pages
            continue
        if n == 0:
            flags.append((page, 'lost_page', f'no text, image ink {k:.1f}%'))
        elif n / k < 0.6 * med:
            flags.append((page, 'thin_page', f'{n} letters, {n / k / med:.0%} of the usual for its ink'))
    return flags


def check(job):
    vol, images = job
    with open(os.path.join(ROOT, 'text', 'fankha', f'fankha_vol_{vol:02d}.txt'), encoding='utf-8') as fh:
        text = fh.read()
    return vol, check_volume(vol, text) + (check_pages(vol, text) if images else [])


def main(argv):
    as_json = '--json' in argv
    images = '--no-images' not in argv
    vols = [int(a) for a in argv if not a.startswith('--')] or list(range(1, 35))
    pages = defaultdict(list)
    with Pool(min(len(vols), os.cpu_count() or 1)) as pool:
        for v, flags in pool.imap_unordered(check, [(v, images) for v in vols]):
            for page, sig, detail in flags:
                pages[(v, page)].append((sig, detail))
    rows = []
    for (v, p), fl in pages.items():
        score = sum(WEIGHT[s] for s, _ in fl)
        strong = any(s in STRONG for s, _ in fl)
        rows.append({'vol': v, 'page': p, 'score': score, 'strong': strong,
                     'flags': [{'signal': s, 'detail': d} for s, d in fl]})
    rows.sort(key=lambda r: (-r['strong'], -r['score'], r['vol'], r['page']))
    if as_json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
        return
    for r in rows:
        if r['score'] == 0:
            continue
        sigs = '; '.join(f'{f["signal"]}: {f["detail"]}' for f in r['flags'])
        print(f'v{r["vol"]:02d} p{r["page"]:4d} score {r["score"]:2d}{" *" if r["strong"] else "  "} {sigs}')


if __name__ == '__main__':
    main(sys.argv[1:])
