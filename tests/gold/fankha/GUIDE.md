# Gold annotation guide — Fankha (فهرستگان نسخه‌های خطی ایران) entries

You annotate entries of a Persian union catalogue of manuscripts **from the raw text only**. Each unit is either a
`work` (the header block of a work entry: title line, transliteration, author line(s), description, incipit/explicit,
bibliography in brackets) or an `ms` (one manuscript line-group of a work).

General rules
- Copy values **verbatim** from the text (same spelling, digits, ZWNJ), but: remove any `<!-- page: N -->` tag and
  collapse the whitespace it leaves (a tag in the middle of a name is NOT part of the name); trim spaces and trailing
  `،؛.` punctuation.
- Hedge words (گویا، ظاهراً/ظاهرا، احتمالاً/احتمالا، شاید، (؟)، منسوب به) are NOT part of a value. Put the value
  without them, and put the exact hedge word(s) in the matching `*_hedge` field. If the whole field is only a guess
  with no extractable value, value = null, hedge = the word.
- `null` when the field is absent. Do not invent, normalise, or translate.
- If you are genuinely unsure how a scholar would parse something (field boundary unclear, OCR garbage, two columns
  mixed, ambiguous whether text is a name), still give your best value AND add a short note to `unclear` (English or
  Persian) saying what is ambiguous. Do not hide doubts. Expect ~10% of units to need a note; do not over-flag.
- `fw(x)` below = the first 5 words of the text x, verbatim; `lw(x)` = the last 5 words.

## work fields
- `title`: the main title (first segment of the `●` line before the first ` / `), including any `= alt` part removed:
  `title` is the part before ` = `.
- `alt_titles`: list of the ` = ` alternatives on the title line (and «با عنوان …» alt titles stated in the header), else [].
- `subjects`: list of subjects (second segment of the `●` line; split on `،` or ` و ` only when they are clearly
  separate subjects, e.g. «فقه و اصول» stays one subject if it reads as one field name; when unsure keep as one and note).
- `languages`: list (third segment; «عربی - فارسی» → ["عربی","فارسی"]).
- `transliteration`: the Latin line right after the `●` line (first one only).
- `author_name`: the person name of the author line, without dates, without the role word, without hedges.
  Fankha author line form: `Surname, given names، dates` then a Latin transliteration line. An author line may have
  **no dates at all**. If there is no author line, null. If the author line is something like «مؤلف ناشناخته», null.
- `author_hedge`: hedge words around the author (e.g. «منسوب به», «(؟)»), else null.
- `author_death_raw`: the date part of the author line exactly as printed (e.g. «- 926 قمری», «1223ق 13 قمری», «ق 10»),
  else null.
- `translator_name`: if the header names a translator (مترجم/ترجمه: …), the name; else null.
- `is_heterogeneous`: true if the header contains «غیر همانند» (the manuscripts are different works with this title).
- `composition_date`: text after «تاریخ تألیف:» up to `؛` or line end, else null. `composition_place`: after «محل تألیف:».
- `related_work`: text after «وابسته به:» up to line end, else null.
- `description_fw` / `description_lw`: fw/lw of the free descriptive text about the work (the paragraph(s) after the
  author block and «وابسته به/اهدا به/تاریخ تألیف» lines, before «آغاز:» and before the bracket bibliography). null if none.
  If the author name + its transliteration appear where you would expect description (author line without date), they
  are the author, NOT description.
- `incipit_fw`, `explicit_lw`: of the work-level «آغاز:» / «انجام:» text; null if none.
- `bibliography_present`: true if a `[...]` bibliography bracket ends the header.

## ms fields
First line form: `N. City؛ Library؛ شماره نسخه: SHELFMARK`. Later lines: incipit/explicit, optional content text,
physical description with labels: خط: (script) کا: (scribe) بی‌کا (no scribe) تا: (copy date) بی‌تا (undated)
جا: (copy place) کاغذ: (paper) جلد: (binding) NNگ (folios) NN سطر (lines) اندازه: (size) افتادگی: (defects),
then a final `[...]` catalogue citation.
- `seq`: N (int) or null. `city`, `library`, `shelfmark`: verbatim (shelfmark = everything after «شماره نسخه:» on that line).
- `scripts`: list of script names in the «خط:» field (e.g. «نستعلیق و نسخ» → ["نستعلیق","نسخ"], «شکسته نستعلیق» stays
  one item). Only the script field — stop at the next label (`،` + کا/بی‌کا/تا/بی‌تا, or `؛`). [] if none.
- `scribe_name`: name after «کا:» up to the next label, without hedges; null if «بی‌کا» or absent.
  «کاتب = مؤلف» or «کا: مؤلف» or «به خط مؤلف» → scribe_name null and `is_autograph` true.
- `scribe_hedge`, `is_autograph` (bool), `is_bika` (bool, «بی‌کا»), `is_bita` (bool, «بی‌تا»).
- `copy_date_raw`: text after «تا:» up to the next `،` + label or `؛` (e.g. «رجب 934ق», «قرن 11»), without hedges; null if none.
- `date_hedge`: hedge words of the date («احتمالاً قرن 13» → date «قرن 13», hedge «احتمالاً»).
- `copy_place`: text after «جا:» up to the next `؛` or `،` + another label/clause (e.g. «جا: مسجد حبیب الله، حسب الامر
  شمس الدین» → «مسجد حبیب الله»; the «حسب الامر …» is a commission clause, put it in `commissioned_by` = «شمس الدین»).
- `commissioned_by`: name after «به دستور/حسب الامر/برای …», else null.
- `folios` (e.g. «35گ (253-287)» — include the parenthesised range), `lines` (e.g. «17 سطر (8×12)» → «17 سطر»,
  and the parenthesis → `text_dimensions` «8×12»), `dimensions` (after «اندازه:», e.g. «13×18سم»), `paper` (after
  «کاغذ:»), `binding` (after «جلد:»), `defects` (after «افتادگی:»): verbatim up to the next `،` + label or `؛`.
- `incipit_fw`, `explicit_lw`: of the manuscript's «آغاز:» / «انجام:» text («برابر» stays as «برابر»). The explicit
  ends at the end of its line or at the next label; text on the NEXT line before «؛ خط:» is NOT explicit.
- `contents_scope`: text at the start of the physical-description line before the first «؛» that is followed by a
  physical label (خط:/کا:/بی‌کا/تا:/بی‌تا), when it says which part of the work the copy contains (e.g.
  «جلد 4 و 5», «کتاب ایمان و کفر را دارد», «از فصل دوم»); else null.
- `ms_note`: any other such leading text that is NOT a contents scope (a description of this copy's content in a
  «غیر همانند» entry, a remark, «تذکر: …», an original-copy reference) — fw of it; else null.
- `catalog_citation`: the final bracket verbatim including brackets (e.g. «[ف: 14 - 3898]»); if two brackets joined by
  « و », the whole «[...] و [...]». null if none.
- `flags`: list of those present: «مصحح»→corrected, «محشی»/«حاشیه»→marginal_notes, «مذهب»/«تذهیب»→illuminated,
  «مصور»/«تصویر»/«مجالس»→illustrated, «عکسی»/«فیلم»(as copy type)→facsimile. [] if none.

## output
One JSON object per line, `{"uid": ..., "kind": ..., <fields>, "unclear": null | "note"}`, in the same order as input.
Output only the JSONL file you are asked to write.

## gold_version 2: the scholar's rulings (5 Aban 1405) — they override anything above
- `scripts` is a list of objects `{"type": ..., "qualifiers": [...]}`. «تحریری» alone is a type; after another script it is
  a qualifier («نسخ تحریری» → {نسخ, [تحریری]}). «چلیپا» is always a qualifier; alone → type null. «شکسته نستعلیق» /
  «نستعلیق شکسته» is one type «شکسته نستعلیق». «نسخ مایل به رقعه» → {نسخ, [مایل به رقعه]}. «نستعلیق راسته و چلیپا» →
  one script with two qualifiers. Quality words (خوش، زیبا، ریز، خوب …) are qualifiers. «سطور چلیپا»/«مختلف السطر» go to
  `lines`, not scripts. «تایپی» is a type.
- «ظاهراً غیر همانند» → is_heterogeneous true, `heterogeneous_qualifier` "doubtful"; «بعضاً غیر همانند» → "partial"; else null.
- Scribe who wrote only part: `scribe_name` the name, `scribe_portion` the parenthesis («ورق اول و …»).
- «بی‌کا»/«بی‌تا» followed by a hedged guess: keep is_bika/is_bita true, scribe/date null; put the guess in
  `scribe_guess`/`date_guess` with `scribe_guess_hedge`/`date_guess_hedge`.
- «؟» inside the author's death date → `death_hedge` "؟" (doubt about the date, not the author).
- `contents_scope` only when the text names a part of the work (جلد، کتاب، باب، فصل، «از … تا …»، «را دارد»، «شامل:»،
  «شامل/دارای ابواب|کتب …»); everything else is `ms_note`.
- Epithet after the author's name («، امام اول») → `author_epithet`, not part of `author_name`.
- `original_copy_raw`: text after «نسخه اصل:»/«اصل نسخه:» up to «؛» or «[». A bare line «همان نسخه بالا» after a
  copy header without «نسخه اصل» is the same copy as the previous one: `merged_into_previous` true.
- «آغاز: برابر» → incipit_fw «برابر».
- Subjects joined by « و » that are two fields («صرف و نحو») are two subjects (ruling, 6 Aban 1405).
