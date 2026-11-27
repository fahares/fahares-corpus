# Fankha text against the PDF text layer (fahares step 14.449)

The Fankha PDF (`fahares-sources/fankha/pdf/fankha-labeled.pdf`) is typeset, so its text layer has the printed letters.
These scripts were run once from `fahares-sources/fankha/pdf-check/`; their paths point there.

1. `rec.py`: rebuilds a page's lines from the PDF words (two columns, right-to-left, Latin runs kept in order).
2. `full.py VOL`: matches each PDF page to a text page.
3. `pairs.py VOL`: pairs a text word with the PDF word that differs from it on the same page, by edit distance and a shared neighbour word.
4. `classify.py`, `classify2.py`: word counts over the whole text and PDF; drops loose pairs.
5. Sonnet judged each pair by `INSTRUCTIONS.md`: PRINT (OCR error), TYPO (the print's own slip, kept as the text has it) or UNSURE.
6. `apply.py --corpus text/fankha --write`: replaces the PRINT words, but not on heading lines (●) and not where the PDF drops an alef of «اا».

The outcome is in `reconciliations/fankha_*_step14_449.tsv`.
