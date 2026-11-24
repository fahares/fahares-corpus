"""Parser v2 on the lines that went wrong before (fahares item 87, steps 14.282 to 14.346).

The gold set (tests/gold/fankha) is 110 works read whole; every family of slips this round found lay outside it. Each
case here is one line of a copy as the catalogue prints it (before the text was put right, where it was), with the
fields it must give. A later change of the parser that breaks one of them fails here by name.
Run: python3 -m unittest tests.test_fankha_v2_cases"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import fankha_parser_v2 as P  # noqa: E402


def physical(text):
    c = P.new_copy()
    P.parse_physical(c, text)
    return c


def copy(*lines):
    """A copy read whole: its heading and the lines under it."""
    rows = [P.Line(i + 1, t, 1, 1, None) for i, t in enumerate(('1. قم؛ مرعشی؛ شماره نسخه: 1',) + lines)]
    return P.parse_copy(rows, 1, False)


def date(c):
    return (c['copy_date'] or {}).get('raw')


def scribes(c):
    return [s['name'] for s in c['scribes']]


def notes(c):
    return [n['text'] for n in c['notes']]


class LabelsWithoutTheirMark(unittest.TestCase):
    """2.4.0, step 14.282"""

    def test_no_scribe_and_a_date_run_together(self):
        c = physical('خط: نسخ، بی‌کا تا قرن 13؛ جلد: تیماج')
        self.assertEqual((c['no_scribe'], date(c), c['binding']), (True, 'قرن 13', 'تیماج'))

    def test_a_date_with_no_colon(self):
        self.assertEqual(date(physical('خط: نستعلیق، کا: محمد علی، تا رجب 1200ق')), 'رجب 1200ق')

    def test_a_size_with_no_colon_and_a_misprinted_label(self):
        self.assertEqual(physical('12گ، 15 سطر، اندازه 11×17سم')['dimensions'], '11×17سم')
        self.assertEqual(physical('12گ، 15 سطر، ادنازه: 14×22سم')['dimensions'], '14×22سم')

    def test_lines_printed_short(self):
        c = physical('جلد: تیماج، 20گ، 29سط (10×20)، اندازه: 15×21سم')
        self.assertEqual((c['lines'], c['text_dimensions']), ('29 سطر', '10×20'))

    def test_a_label_printed_as_a_chunk_of_its_own(self):
        c = physical('بی‌کا، بی‌تا؛ کاغذ ،اصفهانی، جلد مقوا، 10گ')
        self.assertEqual((c['paper'], c['binding']), ('اصفهانی', 'مقوا'))

    def test_a_date_after_the_scribe_is_the_copys(self):
        self.assertEqual(date(physical('خط: نسخ، کاتب = مؤلف، قرن 11ق؛ 5گ')), 'قرن 11ق')

    def test_a_date_after_an_owner_or_a_donor_stays_theirs(self):
        c = physical('خط: نسخ، بی‌کا، بی‌تا؛ اهدایی: رهبری، خرداد 1373؛ 10گ')
        self.assertIsNone(c['copy_date'])
        self.assertTrue(c['undated'])
        self.assertFalse(any(n['type'] == 'date_guess' for n in c['notes']))

    def test_the_cataloguers_own_wording_is_kept(self):
        self.assertEqual(physical('نوع جلد: تیماج، 10گ')['binding'], 'تیماج')


class PiecesThatContinueAField(unittest.TestCase):
    """2.5.0, step 14.287: a piece a model read as the rest of a field, right after the field's value"""

    def test_a_remark_on_the_date_is_its_note(self):
        c = physical('خط: نسخ، بی‌کا، تا: قرن 12، در عصر مؤلف؛ 5گ')
        self.assertEqual((date(c), c['copy_date'].get('note')), ('قرن 12', 'در عصر مؤلف'))

    def test_another_field_run_on_does_not_join(self):
        c = physical('بی‌کا، بی‌تا؛ کاغذ: دولت، آبادی جلد مقوایی با تیماج آلبالویی، 333گ')
        self.assertEqual(c['paper'], 'دولت')


class ScribesAfterTheFirst(unittest.TestCase):
    """2.6.0, step 14.294"""

    def test_the_hands_of_an_album(self):
        c = physical('کا: احمد نیریزی در 1134ق، محمد شفیع حسینی، میر علی کاتب، میرزا حسن، عبدالغفار در 1230ق؛ مجدول')
        self.assertEqual(scribes(c), ['احمد نیریزی در 1134ق', 'محمد شفیع حسینی', 'میر علی کاتب', 'میرزا حسن', 'عبدالغفار'])
        self.assertEqual(c['scribes'][-1].get('note'), 'در 1230ق')

    def test_the_scribe_of_each_part(self):
        # the second hand is one a model read as the rest of the scribe (reconciliations/fankha_note_types.jsonl)
        c = physical('کا: عبدالله بن محمد بن حسن بن علی عتسی امامی (بخش اول)، علی بن فارس بن محمد بن يوسف بن احمد بن ابراهيم (بخش دوم)، تا: 857ق')
        self.assertEqual([(s['name'], s['portion']) for s in c['scribes']],
                         [('عبدالله بن محمد بن حسن بن علی عتسی امامی', 'بخش اول'), ('علی بن فارس بن محمد بن يوسف بن احمد بن ابراهيم', 'بخش دوم')])


class ACommaOneWordEarly(unittest.TestCase):
    """2.7.0, step 14.302"""

    def test_in_the_script(self):
        c = physical('خط: نسخ ،خوش بی‌کا، تا: قرن 12؛ مجدول')
        self.assertEqual((c['script_raw'], c['no_scribe'], date(c)), ('نسخ خوش', True, 'قرن 12'))

    def test_in_the_scribes_name(self):
        c = physical('خط: نستعلیق، کا: محمد تقی ،آشتیانی تا 15 ربیع الثانی 1266ق؛ مجدول')
        self.assertEqual((scribes(c), date(c)), (['محمد تقی آشتیانی'], '15 ربیع الثانی 1266ق'))

    def test_paper_and_binding_run_together(self):
        c = physical('کاغذ: دولت آبادی نخودی جلد تیماج ،مشکی 348گ 21 سطر (10×21)، اندازه: 18×30سم')
        self.assertEqual((c['paper'], c['binding'], c['folios'], c['lines']), ('دولت آبادی نخودی', 'تیماج مشکی', '348گ', '21 سطر'))

    def test_paper_and_binding_of_both_is_one_value(self):
        self.assertIsNone(physical('کاغذ و جلد: کلاسیوری، 10گ')['binding'])

    def test_a_qualifier_between_two_commas(self):
        c = physical('خط: نستعلیق ،زیبا، کا: محمد بن علی، تا: 1200ق؛ 12گ')
        self.assertEqual((c['script_raw'], scribes(c)), ('نستعلیق زیبا', ['محمد بن علی']))


class TheCopysOwnLine(unittest.TestCase):
    """2.8.0 and 2.9.0, steps 14.335 and 14.346"""

    def test_a_scribes_group_in_mid_line(self):
        c = copy('آغاز و انجام: برابر', 'یک برگ از ابتدا افتاده است؛ کاتب: اسمعیل بن مجد الدین، تا: ذیحجه 1036ق؛ افتادگی: آغاز؛ 10گ')
        self.assertEqual((scribes(c), date(c)), (['اسمعیل بن مجد الدین'], 'ذیحجه 1036ق'))

    def test_an_incipit_broken_over_two_lines(self):
        c = copy('آغاز: بسمله. اما بعد چنین گوید بنده عاصی ...', 'شرح: شکر سپاس و ستایش خدای را؛ انجام: و آنها را ذکر نمودیم تمام شد',
                 'خط: نستعلیق، بی‌کا، بی‌تا؛ 20گ')
        self.assertEqual(c['explicit']['text'], 'و آنها را ذکر نمودیم تمام شد')
        self.assertTrue(c['incipit']['text'].startswith('بسمله. اما بعد'))
        self.assertEqual(c['script_raw'], 'نستعلیق')

    def test_an_explicit_given_inside_the_description(self):
        c = copy('خط: نستعلیق، بی‌کا، بی‌تا؛ انجام: «ورق او را بگیرد برسر خود بگذارد»؛ واقف: مرتضی مدرس، 10گ')
        self.assertEqual(c['explicit']['text'], 'ورق او را بگیرد برسر خود بگذارد')

    def test_a_second_explicit_beside_the_copys_own_stays_a_note(self):
        c = copy('آغاز و انجام: برابر', 'خط: نستعلیق، بی‌کا، بی‌تا؛ انجام: «ورق او را بگیرد برسر خود بگذارد»؛ 10گ')
        self.assertTrue(c['explicit']['same_as_work'])
        self.assertIn('انجام: «ورق او را بگیرد برسر خود بگذارد»', notes(c))

    def test_the_parts_of_a_collection_are_not_the_copys_explicit(self):
        c = copy('خط: نستعلیق، بی‌کا، بی‌تا؛ انجام: «تمام شد»، 2. در تفضیل نبوت، آغاز: «بدانکه»؛ 10گ')
        self.assertIsNone(c['explicit'])


if __name__ == '__main__':
    unittest.main()
