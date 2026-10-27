# Gold annotation guide — types of manuscript-copy notes (Fankha)

Each unit is one **note**: a piece of a manuscript copy's description that the parser could not place in a labelled
field. You get the note text and the full text of its copy (`copy_text`) for context. Decide what the note is.
Types were approved by the user (a manuscript scholar) on 6 Aban 1405.

## Step 1: is it a note at all?
Some pieces are only the **continuation of the field just before them** in `copy_text`, cut off by a «،». Find the
note inside `copy_text` and look at what precedes it. If it continues the previous field, set
`continuation_of` to that field and leave `type` null:
- a date or name after «اهدایی:/خریداری از/انتقالی از …» → `acquisition` (e.g. «… اهدایی: رهبری، خرداد 1373»)
- a name/date after «تملک:», «مهر:», «واقف:/وقف» → `ownership` / `seal` / `endowment`
- a page range «(43پ-66پ)» after the folio count → `folios`; «چلیپا (15×22/5)» or «24 تا 33 سطر» → `lines`
- a nisba/second half of a name after «کا:» → `scribe`; text after «جلد:» describing the binding → `binding`;
  after «کاغذ:» → `paper`; after «خط:» → `script`
- a label the parser missed because of Arabic letters or spacing («كا:», «بى‌تا», «ابعادمتن:») → the field it labels
Otherwise `continuation_of` is null and you choose a `type`.

## Step 2: type (one main type; other applicable types go in `also`)
| type | what it is |
|---|---|
| `acquisition` | how the copy came to the library: اهدایی، خریداری، انتقالی، واگذاری، امانی |
| `ownership` | ownership statements (تملک), owners' names, «در نزد …» |
| `seal` | a seal and its legend (سجع «…»), shape (مربع، بیضی …), «با مهر …» when the seal is the subject |
| `endowment` | waqf: endowment notes, endower, date of endowment, «از موقوفات …» |
| `certificate` | اجازه، سماع، قرائت، انهاء، **بلاغ** (reading/hearing marks and licences) |
| `collation` | مقابله، تصحیح، نسخه‌بدل «خ ل» (collation and correction, not a licence) |
| `marginalia` | حواشی، تعلیقات، notes in the margin that comment on the text |
| `transcription` | how the copy was made: the exemplar («از روی نسخه …»، «نقل از خط …»), facts about the scribe, commission («به خواهش …») |
| `decoration` | تذهیب، سرلوح، جدول/مجدول، کمند، ترنج، شنگرف/لاجورد، کتیبه، gold |
| `illustration` | paintings, miniatures, pictures (نگاره، تصویر، مجلس) |
| `diagram` | scientific figures and tables (اشکال، جداول نجومی، دایره، نقشه) |
| `codicology` | physical facts not in a labelled field: رکابه، عطف/لبه، صحافی، damage (آب‌دیدگی، موریانه، وصالی)، layout (ستون، سطور مورب)، page order, image quality of a facsimile |
| `annex` | added texts in the copy that are not the work: فوائد و رسائل مندرج, poems/prayers/notes written on flyleaves, margins or at the end, copies of ijazas *as texts* |
| `contents` | what this copy of the work contains when it is not a contents scope: lists of poems or poets in an anthology, structure («در یک مقدمه و …»), interlinear translation |
| `cataloguer` | the cataloguer's own remark: identification or attribution reasoning («نام مؤلف به قرینه …»)، reference to other copies or numbers, «در فهرست …» |
| `other` | none of the above (say why in `unclear`) |

Precedence when two fit: the more specific provenance type wins (endowment > ownership > seal > acquisition), and a
seal mentioned inside an ownership or endowment note goes to `also`.

## Step 3: attributes
- `by_author`: true when the note says the marginalia / collation / certificate / annex is by the work's author
  («حواشی مؤلف»، «مقابله شده‌ی مؤلف»، «به خط مؤلف»); else false. `by_author_hedge`: the hedge word if hedged
  («احتمالاً به خط مؤلف» → by_author true, hedge «احتمالاً»), else null.
- `seal_legend`: for seal (main or also) the legend text inside «…» if given, else null. `seal_shape`: e.g. «مربع», else null.
- `hedge`: a hedge word that qualifies the whole note («گویا»، «ظاهراً» …), else null.
- `unclear`: null, or a short note (English or Persian) when the type is genuinely debatable. Do not hide doubts; do not over-flag.

## Output
One JSON object per line, same order as input:
`{"uid", "continuation_of", "type", "also": [], "by_author", "by_author_hedge", "seal_legend", "seal_shape", "hedge", "unclear"}`
