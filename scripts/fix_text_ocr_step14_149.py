#!/usr/bin/env python3
"""Fankha text: copy headings the print or the OCR bent, two lines run together, and labels in Arabic letter forms
(fahares backlog item 124, step 14.149).
Each fix replaces one exact run of lines, checked against the page image; a fix whose old text is not found once is
reported and skipped. City, library and shelfmark stay as printed; only the heading's form is put right.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'text' / 'fankha'
FIXES = [
    # p. 835: «برابر» of the next line («آغاز و انجام: برابر») set into the heading
    (4, '6. قم؛ مرکز احیاء؛ برابرشماره نسخه: 4010\nآغاز و انجام: خط: ',
        '6. قم؛ مرکز احیاء؛ شماره نسخه: 4010\nآغاز و انجام: برابر\nخط: '),
    (5, '184. تهران؛ کتابخانه (پژوهشگاه) مؤسسه مطالعات و تحقیقات فرهنگی؛\n<!-- page: 123 -->\n185. شماره نسخه: 175A\n',
        # p. 122-123: the heading of copy 184 runs over the page, and its second half was numbered «185.»
        '184. تهران؛ کتابخانه (پژوهشگاه) مؤسسه مطالعات و تحقیقات فرهنگی؛ شماره نسخه: 175A\n<!-- page: 123 -->\n'),
    (7, '\n4 شیراز علامه طباطبائی؛ شماره نسخه 68/3\n', '\n4. شیراز؛ علامه طباطبائی؛ شماره نسخه: 68/3\n'),
    (7, '\n2. قم،فرهاد معتمد شماره نسخه: 1554/12\n', '\n2. قم؛ فرهاد معتمد؛ شماره نسخه: 1554/12\n'),   # p. 720: «قم‌فرهاد معتمد»
    (7, '\n6. قم؛ فرهاد معتمد شماره نسخه: 1008/4\n', '\n6. قم؛ فرهاد معتمد؛ شماره نسخه: 1008/4\n'),
    (7, '\n65. قم؛ فیضیه، شماره نسخه: 1036/1\n', '\n65. قم؛ فیضیه؛ شماره نسخه: 1036/1\n'),
    # the author's name on the transliteration's line
    (7, '● تحفة الملوک / اخلاق / فارسی\ntohfat-ol molūk لقمان\n\nloqmān\n',
        '● تحفة الملوک / اخلاق / فارسی\ntohfat-ol molūk\n\nلقمان\nloqmān\n'),
    (10, '\n68. تبریز؛ قاضی طباطبائی؛ شماره نسخه بدون شماره\n', '\n68. تبریز؛ قاضی طباطبائی؛ شماره نسخه: بدون شماره\n'),
    (12, '\n3. شیراز؛ شاهچراغ؛ برابر شماره نسخه: 342/3\nآغاز و انجام:\n',
         '\n3. شیراز؛ شاهچراغ؛ شماره نسخه: 342/3\nآغاز و انجام: برابر\n'),
    (22, '\n2. تهران؛ لغت نامه دهخدا شماره نسخه: 76 خط: ', '\n2. تهران؛ لغت نامه دهخدا؛ شماره نسخه: 76\nخط: '),
    # the explicit's last word glued to the next line's label
    (31, 'توران شاه شامی نوشته استنسخه اصل: ملی تبریز ش 3626؛', 'توران شاه شامی نوشته است\nنسخه اصل: ملی تبریز ش 3626؛'),
]


# the copy description's labels in Arabic letter forms («كا:»، «بى كا»، «بى‌تا»، «كاغذ:»), outside «…» quotations, which
# keep their letters; the words around them stay as printed
LABELS = [(re.compile(r'(?<![\w‌])كا(\s*):'), r'کا\1:'),
          (re.compile(r'(?<![\w‌])ب[یى][‌ ]?كا(?![\w‌])'), 'بی‌کا'),
          (re.compile(r'(?<![\w‌])بى[‌ ]?کا(?![\w‌])'), 'بی‌کا'),
          (re.compile(r'(?<![\w‌])بى[‌ ]?تا(?![\w‌])'), 'بی‌تا'),
          (re.compile(r'(?<![\w‌])كاغذ(\s*):'), r'کاغذ\1:')]


def labels(line):
    parts = re.split(r'(«[^«»]*»)', line)
    out = []
    for p in parts:
        if not p.startswith('«'):
            for rx, rep in LABELS:
                p = rx.sub(rep, p)
        out.append(p)
    return ''.join(out)


def main():
    done, missing = 0, []
    for vol, old, new in FIXES:
        p = ROOT / f'fankha_vol_{vol:02d}.txt'
        t = p.read_text(encoding='utf-8')
        n = t.count(old)
        if n != 1:
            missing.append((vol, n, old[:50]))
            continue
        p.write_text(t.replace(old, new), encoding='utf-8')
        done += 1
    print(f'{done} fixed', missing or '')
    changed = 0
    for vol in range(1, 35):
        p = ROOT / f'fankha_vol_{vol:02d}.txt'
        lines = p.read_text(encoding='utf-8').split('\n')
        new = [labels(l) for l in lines]
        changed += sum(a != b for a, b in zip(lines, new))
        p.write_text('\n'.join(new), encoding='utf-8')
    print(f'{changed} lines with Arabic-letter labels')
    # a page tag inside an incipit or explicit line that joined the cataloguer's next line to it: a line break after
    # the tag, as judged in reconciliations/page_tag_breaks_step14_149.json (the quotation running on stays)
    plan = json.loads((ROOT.parent.parent / 'reconciliations' / 'page_tag_breaks_step14_149.json').read_text(encoding='utf-8'))
    broken, skipped = 0, []
    for it in plan['items']:
        if it['label'] != 'NEW_LINE':
            continue
        vol = int(it['key'].split(':')[0])
        p = ROOT / f'fankha_vol_{vol:02d}.txt'
        t = p.read_text(encoding='utf-8')
        # spaces on the same line only, so a line already broken is not broken again
        rx = re.compile(re.escape(it['before'][-40:]) + r'[ \t]*(<!-- page: \d+ -->)[ \t]*' + re.escape(it['after'][:40]))
        hits = list(rx.finditer(t))
        if len(hits) != 1:
            if len(hits) > 1:
                skipped.append((it['key'], len(hits)))
            continue
        m = hits[0]
        t = t[:m.start(1)].rstrip(' \t') + '\n' + m.group(1) + '\n' + t[m.end(1):].lstrip(' \t')
        p.write_text(t, encoding='utf-8')
        broken += 1
    print(f'{broken} lines broken after a page tag', skipped[:10] if skipped else '', len(skipped))


if __name__ == '__main__':
    main()
