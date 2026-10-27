"""Parser v2 against the Fankha gold set (fahares item 87).

The accuracy test needs json/fankha_v2/ from `python3 scripts/fankha_parser_v2.py` and is skipped otherwise.
Run: python3 -m unittest discover tests"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'gold', 'fankha'))

from fankha_parser_v2 import parse_volume, parse_scripts  # noqa: E402

V2 = os.path.join(ROOT, 'json', 'fankha_v2', 'fankha_vol_01.json')
PAGE = re.compile(r'<!--\s*page:')

# per-field floors on the development gold set; raise them as the parser improves, never lower them silently
FLOOR = {'default': 0.95, ('ms', 'contents_scope'): 0.85, ('ms', 'flags'): 0.85, ('ms', 'note_placed'): 0.85,
         ('work', 'author_hedge'): 0.5, ('ms', 'scribe_hedge'): 0.75, ('work', 'explicit_lw'): 0.85,
         ('work', 'incipit_fw'): 0.85, ('work', 'bibliography_present'): 0.85, ('work', 'description_lw'): 0.9}


class GoldAccuracyTest(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(V2), 'run scripts/fankha_parser_v2.py first')
    def test_field_floors(self):
        from compare_v2 import evaluate
        tot, ok, _, missing = evaluate()
        self.assertEqual(missing, [])
        low = {k: f'{ok[k]}/{tot[k]}' for k in tot if ok[k] / tot[k] < FLOOR.get(k, FLOOR['default'])}
        self.assertEqual(low, {})


class PageTagTest(unittest.TestCase):
    def test_no_page_tag_in_any_field(self):
        for vol in (1, 23, 34):
            with open(os.path.join(ROOT, 'text', 'fankha', f'fankha_vol_{vol:02d}.txt'), encoding='utf-8') as fh:
                data = parse_volume(vol, fh.read())
            leaks = []

            def walk(x, path):
                if isinstance(x, dict):
                    for k, v in x.items():
                        walk(v, f'{path}.{k}')
                elif isinstance(x, list):
                    for i, v in enumerate(x):
                        walk(v, f'{path}[{i}]')
                elif isinstance(x, str) and PAGE.search(x):
                    leaks.append(path)
            walk(data, f'vol{vol}')
            self.assertEqual(leaks[:10], [])


class ScriptRulingsTest(unittest.TestCase):
    CASES = [
        ('نسخ تحریری', [('نسخ', ['تحریری'])]),
        ('تحریری', [('تحریری', [])]),
        ('نسخ و تحریری', [('نسخ', []), ('تحریری', [])]),
        ('نستعلیق راسته و چلیپا', [('نستعلیق', ['راسته', 'چلیپا'])]),
        ('چلیپا', [(None, ['چلیپا'])]),
        ('نسخ مایل به رقعه', [('نسخ', ['مایل به رقعه'])]),
        ('نستعلیق شکسته تحریری', [('شکسته نستعلیق', ['تحریری'])]),
    ]

    def test_cases(self):
        for raw, expected in self.CASES:
            with self.subTest(raw=raw):
                self.assertEqual([(s['type'], s['qualifiers']) for s in parse_scripts(raw)], expected)


if __name__ == '__main__':
    unittest.main()
