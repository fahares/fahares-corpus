# Fankha parser gold set (fahares item 87, phase 1)

- `units.jsonl`: 260 sampled units (110 work headers, 150 manuscripts) with raw text; `sample.py` rebuilds it (seed 87).
- `gold.jsonl`: blind field-by-field annotation per `GUIDE.md`; `unclear` marks cases awaiting the scholar's ruling.
- `parsed_v1.1.6.jsonl`: the current parser's output for the same units.
- `compare.py <dir>`: per-field accuracy, raw and adjusted (design differences of the v1 JSON not counted).
  Writes `accuracy*.json` and `mismatches.jsonl` next to the inputs (not committed).

Report and plan: `fahares/docs/plans/fankha-parser-v2.md`.
