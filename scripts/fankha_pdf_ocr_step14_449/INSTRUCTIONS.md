# Judging OCR differences in the Fankha text

Fankha (فهرستگان نسخه‌های خطی ایران) is a printed union catalogue of manuscripts: Persian descriptions, Arabic
incipits/explicits quoted from the manuscripts, titles, authors' and scribes' names, Turkish/Urdu now and then.

Each row of `batch_NN.tsv` is one word where two witnesses disagree:

- `text_word`: the word in our text file, which was made by OCR (sometimes an LLM OCR that silently "corrected" words).
- `print_word`: the word as actually printed, taken from the typeset PDF. It is reliable for letters. Ignore its
  extraction quirks: Arabic ي/ك instead of Persian ی/ک, missing ZWNJ, «االله» for «الله», Persian vs Latin digits.
- `context`: the text file around the word; the word is marked ⟦…⟧.

Decide, row by row, by reading it yourself (no scripts or rules for deciding):

- **PRINT**: the printed form is a legitimate word, spelling or name as printed. This includes older or variant
  spellings (هیأت/هیئت، ایطالیا/ایتالیا، طلوزان)، archaic or unusual Arabic forms in quotations, a different but
  plausible word, and any plausible proper name. The text file will be changed to the printed form.
- **TYPO**: the printed form is an obvious typing slip of the print (a non-word: a doubled, dropped, extra or swapped
  letter or dot in a known word, e.g. «نگررد»، «المنترله»، «قضل» for «فضل» in a clear context) AND `text_word` is
  exactly the intended word. The text keeps its form.
- **UNSURE**: you cannot tell; both are plausible; or the print is a typo but `text_word` is not the right correction.

When the printed form is a plausible word or name, choose PRINT. Choose TYPO only when the slip is obvious.

Read the context, not just the two words. A printed form that is a real word somewhere but makes no sense in this
sentence, while `text_word` is the evident word there, is TYPO: «الشیخ الأحد» for «الشیخ الأوحد»، «اقوال الجواب»
for «اقول الجواب»، «پنچ قسم» for «پنج قسم». The PDF also misreads a few dotted letters (ج/چ، ح/خ، د/ذ، ب/ی):
a printed form that differs only by such a dot and is a non-word or odd in context is TYPO, not PRINT.
Old Persian ذال after a vowel («داذه»، «بذان»، «خداى ذو») in quoted verse or old prose is the old orthography of the
manuscript, not a slip: PRINT.
PRINT is right for: spelling variants (هیأت، ایطالیا، قریم for Crimea), names, and Arabic or Persian wording that
reads correctly in context (e.g. «فلعلك» in a Qur'anic quotation).

## Output

Write `verdict_NN.tsv` (same NN as the batch) next to the batch, UTF-8, header `id\tverdict\tnote`, one row per
input id, every id exactly once, in input order. `verdict` is PRINT, TYPO or UNSURE. `note` is empty for PRINT; for
TYPO and UNSURE at most eight words (for UNSURE, the correct form if you know it). You may use a script only to
write the file and check that every id is there.

Reply with only the counts of each verdict.
