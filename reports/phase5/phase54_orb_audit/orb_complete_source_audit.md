# ORB - complete source audit (Phase 5.4)

> Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved.

**Stage 1 only.** Nothing in Stages 2 and 3 (the complete backtest, the journal reconciliation) was started. The owner reviews this report and approves an ORB configuration before anything else runs.

## 1. What was read

* `docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf` - all **13 pages rendered and read visually** (text, figures and the three real reference charts), plus the extracted text.
* `docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf` - all **6 handwritten pages rendered and read**. The ORB remarks are text only (no drawings).
* The ORB engine (`strategies/orb.py`), its rule registry entries, the Phase 5.1 / 5.2 / 5.3 reports, the Phase 3.6 signal / trade tables, the manual journal workbook (read-only) and the one-minute data.

## 2. The rulebook, page by page

| page | content | visual evidence |
|---|---|---|
| 1 | Overview: decision at 9:20 once the first 5-minute candle has closed; same rules both directions; stop 30, target 60 (1:2); the three setups (Method 1: previous day's level; Method 2: inner level + trendline; Gap + 200 DMA) and the long / short table | - |
| 2 | The first candle 9:15-9:20 (its close is not known until 9:20 - 'never pre-empt the close'); the five 9:20 checks | - |
| 3 | Method 1 long: confirm uptrend ('price above the 200 EMA is a basic confirmation, supported by bullish price structure'), mark previous-day resistance with a horizontal line, the 9:20 candle must break AND close above it with a strong green body and small upper wick, enter at 9:20 | figure: staircase of candles to a horizontal previous-day resistance; the 09:15-09:20 candle opens below and closes above it; 200 EMA below |
| 4 | Method 1 short (mirror); Method 2 introduction: major level = top / bottom of the previous day's range, inner level = a smaller level within it; Method 2 needs the trendline | mirror figure (descending candles, 200 EMA above) |
| 5 | Method 2 long: eight steps (trend, rising trendline, major resistance for context, inner resistance, 9:20 break and close, candle strength, 200 EMA filter, enter) | figure: rising trendline through swing lows, inner resistance (a recent candle's high) inside the previous day's range, major resistance above and unbroken |
| 6-7 | Method 2 short (mirror, falling trendline); reference chart caption: major resistance NOT yet broken at 9:20, a small inner resistance near the trendline breaks; condition table; the reminder 'a trendline by itself is not an entry signal. Verify the exact levels and first-candle close on your original chart' | annotated REAL chart ('inner level drawn approximately') |
| 7-9 | Gap above / below the 200 DMA: gap in direction, the gap must bring price through the average, 'a candle that only crosses the line but closes below it does not qualify', strong candle or suitable pin bar; 'not every gap is valid' (reject extended gaps and strong rejection wicks) | - |
| 9-10 | Candle-quality rules: preferred / conditional (pin bar) / reject (opposite-wick rejection) | figure: strong bullish, bullish pin bar, upper-wick rejection |
| 11 | Trade parameters: entry 9:20, stop entry -/+ 30, target +/- 60; 'standardise your units' (index points, instrument units or rupees) | - |
| 12 | Consolidated rule matrix (trend, level, gap, first-candle confirmation, wick rule, 30/60) | - |
| 13 | REF IMAGES: three real charts - two short breakdowns of a purple horizontal zone that extends across several sessions (EMA above price), one long above a rising blue trendline with a purple zone | three real charts |

## 3. The source-rule registry

`orb_source_rule_registry.csv` lists 47 rows (the 36 registry rules with page, diagram, method, existing code and status, plus the visual evidence, the author clarifications and the engine's research assumptions). Classification counts: {'EXPLICIT_DOCUMENT_RULE': 40, 'UNRESOLVED': 2, 'AUTHOR_CLARIFICATION': 2, 'OWNER_APPROVED': 1, 'CURRENT_ENGINE_ASSUMPTION': 2}. No research assumption is described as a source rule (an audit check enforces this).

## 4. What the source defines and what it does not

| element | defined by the source? | engine |
|---|---|---|
| first candle 09:15-09:20, decision at 09:20, entry after its close | yes, explicit | implemented (verified on all 13 dates: first candle 09:15-09:20, fill = open of the 09:20 minute bar) |
| Method 1 level = previous day's top / bottom | yes, explicit (p.4 table) | implemented |
| break AND close beyond the level | yes, explicit | implemented |
| established trend; price above the 200 EMA as the basic confirmation | qualitative; sampling time and 'structure' undefined | owner variant: previous close vs its EMA (the structure variant is inactive) |
| Method 2 inner level | qualitative + schematics; no algorithm; 'drawn approximately' | research assumption: latest fractal k=2 |
| Method 2 trendline | qualitative | research assumption: last two fractals |
| strong candle / pin bar / rejection wick | qualitative; no numbers; clean figures | research numbers (MODERATE, owner pin test, 33%) |
| near the EMA / convincing close | qualitative | research numbers (15 points / 5 points) |
| Gap setup: gap through the 200 average, candle closes beyond | explicit but the open-versus-candle crossing is ambiguous | frozen reading: the OPEN must be beyond the average |
| multi-session zones (p.13) | shown, never defined | not implemented |
| 30-point stop, 60-point target | explicit (units ambiguous) | implemented as index points (owner-approved) |

## 5. The 13 disputed dates

See `orb_author_corrections.md` and `orb_13_disputed_dates.csv`. In brief: 12 green first candles and 1 red; no ORB signal on any date; the missing conditions are level (9 dates, Method 1), inner level (6), trendline (4), trend (2), strength (3) and a gap-average tie (1) - the dispute is not one defect. All 13 case studies (`daily/<date>.md`, `charts/<date>.svg`) show the original one-minute bars, the five-minute candles, the first candle, the previous-day levels, the multi-session constructions, the EMA(200), the frozen trendline, the engine's eligibility checks and the IRF / other trade taken.

## 6. The manual journal as descriptive evidence (read only)

The original journal has 190 rows ({'IRF': 73, 'PDR': 8, 'ORB': 89, 'RF': 17, 'PDS': 3}); 5 rows carry weekend dates (2025-10-11, 2026-02-14, 2026-08-15, 2026-08-22, 2026-08-29) and are kept as supplied. It records 89 ORB entries. On the 85 of them that fall on a dataset session the engine has a confirmed ORB signal on 35; the other 50 (11 of them among the 13) have none; conversely the engine has ORB signals on 6 dates with no journal ORB. First candles of the 50 missed dates: {'GREEN': 30, 'RED': 20}. Binding predicate (the only failing predicate of the closest method): {'level_broken': 15, 'candle_quality': 13, 'candle_shape': 9, '2 predicates fail': 9, 'trend': 2, 'gap_crosses_200_average': 2}. The journal has no direction, price or level, so it cannot define a rule; it shows that the engine's ORB under-generates broadly, not only on the 13. Full reconciliation is Phase 5.6.

## 7. Findings

1. The previous finding is confirmed: the engine produced no ORB signal on the 13 dates; this is a qualification problem, not a priority problem (ORB decides at 09:20, before any IRF).
2. The failures are heterogeneous. A single missing rule would not reproduce them: every single-construction variant reproduces at most 2 of 13.
3. The rulebook itself concedes that Method 2's level is approximate and defers to the author's original chart; the handwritten pages contain no drawings. The author's levels, trendlines and entry candles for the disputed dates are the missing evidence.
4. The engine is stricter than the written method in three places (trend sampling, single research constructions for the inner level / trendline, numeric candle thresholds) - all labelled as assumptions, none an explicit source rule.
5. The rulebook's own figures show clean candles, so the numeric thresholds cannot be loosened on the source's authority alone; the author's expectation on 2025-12-12 and 2025-12-30 (LOOSE would admit both) conflicts with the figures.
6. The Gap setup has a genuine reading ambiguity (open versus candle crossing the average) that affects 10 of 246 gap cases.

## 8. What the owner is asked to decide (Stage 1 stop)

Provide the author's drawn level / trendline / entry candle for the disputed dates (at least the six level dates), then choose from `orb_rule_decision_matrix.md`. No ORB configuration is selected here, no backtest was run, and Stage 2 will not start until an ORB configuration is explicitly approved.

## 9. Verification

* Tests: **737 passed, 1 skipped (full suite; 717 passed / 1 skipped before; 20 new Phase 5.4 tests)**; ruff: **All checks passed**.
* Independent audit script: ALL 16 CHECKS PASS.
* The frozen configuration, the Phase 3.0-5.3 reports, the data and the source documents are byte-identical to the baseline snapshot.
