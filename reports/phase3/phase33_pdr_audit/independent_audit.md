# Phase 3.3 - independent audit

Two independent validations, both read-only on the repository, and an own-reading step on the source figures.

## 1. Second implementation (`scripts/phase33_independent_audit.py`)

It imports **nothing** from `nifty_trading`, `phase33_lib` or `phase33_pdr_audit`. Candles come from pandas resampling (the analysis script uses bucket loops), swing highs are found with vectorised comparisons, the PDR sequence is a separate scan, and the journal is read from the raw workbook. Results: `independent_audit_results.json`.

| check | n | result |
|---|---|---|
| the affected set derived from the raw data equals the delivered file (the count is not hard-coded) | 27 of 54 | PASS |
| every PDR trade is LONG and every confirmation candle is bullish | 54 | PASS |
| zone floor/ceiling, source candle, confirmation OHLC, close minus floor, timestamps, and the fill price = the raw 1-minute open at the fill minute | 54 | PASS |
| gap vs the official close, previous-day high, interaction candle, retest low, penetration depth (independent sequence scan) | 54 | PASS |
| every PDR confirmed signal of the engine is reproduced from the raw data (the only extra signal is on 2025-10-23, a day the engine blocks as NOT_EVALUATED because its previous session is the unverifiable Muhurat session) | 383 | PASS |
| each classification follows the documented decision rule when re-applied to the delivered columns | 54 | PASS |
| counterfactual counts A-D recomputed (A 54, B 27, C 20, D 8) | 54 | PASS |
| journal comparison recomputed from the raw workbook (15-minute tolerance; the one alternate-label row verified on the row itself) | 54 | PASS |
| 27 charts exist, with the independently derived close / floor / distance in each title | 27 | PASS |
| Phase 3.0, 3.1 and 3.2 reports and ledgers, raw data, source PDFs and the journal are byte-identical to the hash snapshot taken before this phase | 619 files | PASS |

## 2. Second reviewer (a fresh reviewer with no part in the analysis)

The reviewer read the PDF **before** opening any Phase 3.3 file (text layer plus all four pages rendered and viewed), formed its own reading, then challenged every statement, re-derived the 27 with its own code, recomputed alternative zones and counts, recomputed the journal comparison, rendered and viewed 9 charts, and checked that no profit figure is used.

* **Same conclusion on the hold question:** a zone-hold requirement is not written; the purpose statement ("watched to see whether it now works as support") is a rationale, not an explicit requirement; the figures are consistent with a close at/above the floor but cannot tell reading B from reading C.
* **Reproduced without a difference:** the 27, every numeric field for all 54 trades, 383 of 383 engine signals, the example checks, zone A/C and the flip logic for all 54, counts A-D/D2 with their first/second splits, the journal comparison, the chart labels of all 27, and the no-profit rule.

| finding of the reviewer | disposition |
|---|---|
| S2-1 "D is contradicted by Examples 2 and 3" overclaims: the below-floor lows are the confirmation candle's own wick; D2 holds for Examples 1, 3, 4 and fails only Example 2 by 3.25 points; "likely not intended" is an opinion | **Fixed** in the verification report, the counterfactual table, the owner decisions and `source_example_checks.csv` (new column for the low before the confirmation candle); the opinion was removed |
| S2-2 wrong "38.6-point box" for Example 3's engine zone | **Fixed:** the zone is [25,077.25, 25,095.70], 18.45 points; the registry's older figure is noted as not reproduced |
| S2-3 Example 5 statements unsupported (zone "several sessions" back; possible missing gap-up) | **Fixed:** wording reduced to what a 5x zoom shows (one session; the entry session seems to open at/inside the zone, no visible gap-up; low-resolution reading) and flagged for the owner |
| S2-4 RF-guide page 9 picture used selectively | **Fixed:** stated as not part of the PDR guide, shows a long entry far below its zone, not used as evidence |
| S2-5 `independent_audit.md` missing; cache file not listed | **Fixed:** this file; the cache file was not needed and is no longer written |
| S2-6 `nearest_source_figure` text wrong for unaffected trades | **Fixed:** set to "n/a (not an affected trade)" for them |
| S2-7 journal framing loose (alternate-label row; 20260605-1 closes inside the zone; four journal PDR rows without an engine trade, one on the Example 3 date) | **Fixed** in the owner decisions and the counterfactual evidence text |
| S2-8 classification design: zero SUPPORTED/CONTRADICTED is a property of the rule; 26 trades share one label; the flip test assumes reading B | **Fixed:** stated in the report, an informational severity column and table added (not used by the classification), the dependence on B written into the basis of the flagged trade |
| S3 mislabelled "candles between" column; example rows unrelated to the example's entry; calibration claim; figure-vs-data differences at the open; chart label collisions | **Fixed:** column renamed; `is_the_examples_own_entry_candle` added and shown; edge deviations and open differences disclosed; chart labels moved (zone labels to the left, TEST below the candle, bracket label left of the bracket, previous-day-high label at the right) |

## 3. Software state

`ruff` clean; the full suite passes (see the final report for the count). Phase 3.3 adds 12 tests (`tests/test_phase33_pdr_audit.py`): reconstruction helpers on synthetic candles, the decision order of the classification, the no-outcome/no-profit guard on the classification code, file consistency, and the hash snapshot.

## 4. Not verified by anyone

* Example 5 and the figure price readings are pixel estimates (about 1-2 points); Example 4's date is inferred from its candle sequence (the PDF prints none).
* Why the controller picked these 54 trades out of the 383 signals was not re-derived here (Phase 3.0/3.2 audited that); each trade was only confirmed to be a valid raw-derived signal.
* The remaining 18 charts were checked programmatically for their numbers, not visually.
* The journal's own inconsistencies (190 rows against the report's 189, Saturday-dated rows) are outside this audit's scope.
