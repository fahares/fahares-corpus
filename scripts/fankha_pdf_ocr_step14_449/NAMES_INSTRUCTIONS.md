# Judging OCR fixes that reach a person's name (Fankha)

Fankha is a printed union catalogue of manuscripts. Its text was made by OCR, and the typeset PDF showed that in each
row below the OCR misread a word that stands in an author's or scribe's name on the site. `old` is the OCR's word,
`new` the printed word. A judge earlier found the printed word right in the text; here the question is what the site's
person records should do about it.

Columns: `record` (work: author; copy: scribe), `site_value` (the name as the record holds it), `title` (the work),
`person_*` (the person record the name is linked to: its name, dates, how many records it has, its other names
`aliases` and known misspellings `wrong_names`), `person_with_corrected_name` (a person whose name is exactly the
linked person's name with `new` for `old`, if any), `corpus_line` (the catalogue line with the OCR's word).

Decide, row by row, by reading it yourself:

- **RECORD**: the person's name is already right (it has the printed form, or the person has no such word), or there is
  no person; only the record's own name (`site_value`) carries the OCR's word. Fix the record's name only.
- **RENAME**: the person's name itself carries the OCR's misreading, the printed form is this same person's right name
  (dates, title and the rest of the name fit), and the OCR form is no real other spelling. The person is renamed; the
  OCR form goes to `wrong_names`.
- **VARIANT**: both forms are real spellings of the same name (عبدالعلی/عبدعلی، لاهیجی/لاهجی، طولوزان/طلوزان). The
  person keeps its name; the record's name takes the printed form, which is added to the person's `aliases`.
- **OTHER**: with the printed form the name is another person (ابن الجزری/ابن جزی), or `person_with_corrected_name`
  names someone else who fits. Nothing changes; it is listed for a cataloguer.
- **TYPO**: the printed form is an obvious slip of the print and the site's form is the right name. Nothing changes.
- **UNSURE**: you cannot tell.

Prefer RECORD when the person's name is already right. Choose RENAME only when you are confident the person record's
name is wrong. A person with many records needs more care: its name is shown on all of them.

Write `names_verdict_X.tsv` (X as in the input) with header `n\tverdict\tnote`: one row per input row, every `n` once.
`note` is at most twelve words: for RENAME the full corrected name; for OTHER and UNSURE why. Use a script only to write
the file and check it. Reply only with the counts of each verdict.
