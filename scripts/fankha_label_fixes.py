#!/usr/bin/env python3
"""Fankha text: labels of a copy's description that lost their mark or were misprinted, put right in the text itself
(fahares backlog item 124, step 14.282; the user's ruling of 30 Aban 1405: a slip of the text, the print's own too, is
corrected in the text, so the parser need not guess).

The parser (v2.4.0) finds each place while it reads a copy: «بی‌کا تا قرن 13» → «بی‌کا، تا: قرن 13», «تا رجب 1200ق» →
«تا: رجب 1200ق», «اندازه 11×17سم» and «ادنازه: …» → «اندازه: …», «: جلد تیماج» → «جلد: تیماج», «29سط (…)» and «19 س» →
«… سطر», «کاغذ ،اصفهانی» → «کاغذ: اصفهانی», «خط تحریری» → «خط: تحریری», «آغا و انجام: برابر» and «آغاز و انجام برابر» →
«آغاز و انجام: برابر», «آغاز …» and «؛ انجام …» with no «:». Only the label and its mark change; every word of the
value stays as printed. A place whose old text is not found exactly once on its line is reported and left.
Each change is written to reconciliations/fankha_label_fixes_step14_282.jsonl ({vol, line, old, new}).

Usage: fankha_label_fixes.py [--apply] [VOL ...]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import fankha_parser_v2 as P  # noqa: E402

LOG = ROOT / 'reconciliations' / 'fankha_label_fixes_step14_282.jsonl'


def pattern(kind, old, new):
    """The regex of the old text on its line, and what it becomes."""
    sp = lambda s: r'\s*'.join(re.escape(w) for w in s.split())          # the text file's own spacing
    if kind == 'bare':            # «کاغذ ،اصفهانی»: old is the label, new the chunk after it
        return re.compile(r'(?<![\w‌])' + re.escape(old) + r'\s*،\s*(?=' + sp(' '.join(new.split()[:2])) + ')'), old + ': '
    if kind == 'head':
        return re.compile(r'^(\s*(?:<!--[^>]*-->\s*)?)' + sp(old)), None
    return re.compile(r'(?<![\w‌])' + sp(old) + r'(?![\w‌])'), new


def main(argv):
    apply = '--apply' in argv
    vols = [int(a) for a in argv if a.isdigit()] or list(range(1, 35))
    kinds, missed, records = Counter(), [], []
    for vol in vols:
        path = ROOT / 'text' / 'fankha' / f'fankha_vol_{vol:02d}.txt'
        text = path.read_text(encoding='utf-8')
        P.FIX_LOG = []
        P.parse_volume(vol, text)
        lines = text.split('\n')
        for no, kind, old, new in dict.fromkeys(P.FIX_LOG):
            if no is None or no > len(lines):
                missed.append((vol, no, kind, old))
                continue
            if kind != 'bare' and re.sub(r'\s', '', old) == re.sub(r'\s', '', new):          # spacing alone is no slip
                continue
            rx, to = pattern(kind, old, new)
            line = lines[no - 1]
            hits = rx.findall(line)
            if len(hits) != 1:
                missed.append((vol, no, kind, old))
                continue
            m = rx.search(line)
            put = (m.group(1) + new.rstrip()) if kind == 'head' else to.rstrip() if kind == 'bare' else to
            tail = line[m.end():]
            if kind in ('head', 'bare') and not tail.startswith(' '):
                put += ' '
            fixed = line[:m.start()] + put + tail
            records.append({'vol': vol, 'line': no, 'old': m.group(0), 'new': put})
            lines[no - 1] = fixed
            kinds[kind] += 1
        if apply:
            path.write_text('\n'.join(lines), encoding='utf-8')
    if apply:
        with open(LOG, 'a', encoding='utf-8') as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"{'Fixed' if apply else 'Would fix'} {len(records)} places {dict(kinds)}; {len(missed)} not found on their line", file=sys.stderr)
    for r in records[:0 if apply else 40]:
        print(r['vol'], r['line'], '|', r['old'], '→', r['new'])
    for m in missed[:25]:
        print('MISSED', *m, file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])
