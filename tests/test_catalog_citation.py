"""A catalogue cited by name at the end of a copy is its catalog_citation (fahares item 49).

Run: python3 -m unittest discover tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from fankha_parser import FankhaParser, is_bib_citation, is_catalog_citation


class IsCatalogCitationTest(unittest.TestCase):
    def test_catalogue_names_with_and_without_a_locator(self):
        for text in [
            'الفبائی: -512', 'ف مخ: 1', 'ف مخ', 'ف مخ:', 'رایانه', 'رايانه', 'د.ث. مجلس', 'د.ت. مجلس', 'د.ث',
            'اهدائی رهبر: 2 اخبار 1-112', 'اهدائی رهبر: 1علوم قرآن - 79', 'سنا - ف: 1-5', 'ف: 47/1 - 15',
            'تراثنا: س6ش4-102', 'تراثنا س2ش4: -51', 'آینه پژوهش: سال4ش22-104', 'نسخه‌پژوهی 3: -108',
            'میراث اسلامی: <!-- page: 156 --> دفتر دهم - 770', 'محدث ارموی مخ: -', 'سلطانی - ف',
            'عمومی ساری و تنکابن: ف', 'گنجینه (موزه)', 'ف - 140', '3: - 63',
        ]:
            with self.subTest(text=text):
                self.assertTrue(is_catalog_citation(text))

    def test_editorial_notes_are_not_citations(self):
        for text in [
            'از طهارت تا حج', 'از روی نسخه اصل', 'از آیه 102 سوره آل عمران تا اول سوره یونس (آیه 2)',
            'از شماره ثبت 1 تا 824', 'تذکر: نام مؤلف به قرینه آغاز نسخه تعیین شد',
            'این رساله در فهرست نیست و با توجه به نقل مدرس رضوی افزوده شد', 'کذا', 'ناخوانا', 'قال',
            'احتمالاً همان نسخه بالا', ': -', '1350', 'انجام: بر لب خشکم چکانی شبنمی',
        ]:
            with self.subTest(text=text):
                self.assertFalse(is_catalog_citation(text))


class ManuscriptCitationTest(unittest.TestCase):
    def parse(self, body):
        return FankhaParser(1)._parse_manuscript(['1. مشهد؛ رضوی؛ شماره نسخه: 123', body], 10, 10, 1)

    def test_a_named_catalogue_in_the_last_bracket_is_the_citation(self):
        ms = self.parse('نسخ، بی‌کا، بی‌تا؛ 120گ [از طهارت تا حج] [الفبائی: -512]')
        self.assertEqual(ms.catalog_citation, '[الفبائی: -512]')
        self.assertEqual(ms.editorial_notes, ['از طهارت تا حج'])

    def test_a_bare_catalogue_name(self):
        ms = self.parse('نستعلیق، بی‌کا، بی‌تا [رایانه]')
        self.assertEqual(ms.catalog_citation, '[رایانه]')
        self.assertEqual(ms.editorial_notes, [])

    def test_a_note_in_the_last_bracket_stays_a_note(self):
        ms = self.parse('نستعلیق، بی‌کا، بی‌تا [از روی نسخه اصل]')
        self.assertIsNone(ms.catalog_citation)
        self.assertEqual(ms.editorial_notes, ['از روی نسخه اصل'])

    def test_a_named_catalogue_before_the_last_bracket_stays_a_note(self):
        ms = self.parse('نستعلیق، بی‌کا، بی‌تا [رایانه] [از روی نسخه اصل]')
        self.assertIsNone(ms.catalog_citation)

    def test_a_bibliographic_citation_is_kept(self):
        ms = self.parse('نستعلیق، بی‌کا، بی‌تا [ف: 12 - 340] [صد و شصت نسخه: -7]')
        self.assertTrue(is_bib_citation('ف: 12 - 340'))
        self.assertEqual(ms.catalog_citation, '[ف: 12 - 340]')
        self.assertEqual(ms.editorial_notes, ['صد و شصت نسخه: -7'])


if __name__ == '__main__':
    unittest.main()
