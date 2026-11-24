# PDR: first versus second confirmation, and the 215 delayed cycles

**Baseline PDR-A is unchanged.** All variants are separate opt-in research candidates; none is selected.

## The delayed cycles (215 of 600 confirmed cycles, both windows)

Categories (each cycle counted once; priority F > G > D > C > A): A = 195, B = 0, C = 20, D = 0, E = 0, F = 0, G = 0. All 215 delayed cycles have a first green candle after the retest that closed at or below the ceiling; in 20 of them the retest candle itself was additionally green above the ceiling and is reported under C by priority (`retest_candle_green_and_above_ceiling` in the CSV).

* **A** - an earlier green candle after the retest closed at or below the zone ceiling, so the approved strict close-above rule (not the engine) delayed the entry.
* **B** - an earlier green candle closed above the ceiling but failed a quality convention: cannot occur (the baseline's quality test is any green candle); count must be 0.
* **C** - the earliest green candle was the retest candle itself, which would qualify but is excluded by the provisional retest-then-confirmation convention.
* **D** - an earlier candle met every approved requirement but the engine rejected it: an implementation defect.
* **E** - belongs to a different setup cycle: cycles are separated by construction; count 0.
* **F / G** - data or timing discrepancy / insufficient evidence.

Exact dates, candle timestamps, per-candle rejection reasons and the variant entries for all delayed cycles are in `pdr_215_delayed_cycles.csv` (and `pdr_first_eligible_audit.csv` for every confirmed cycle).

## Variant comparison (signals per cycle versus the baseline; windows combined)

| variant | SAME | EARLIER | LATER | REMOVED_BY_VARIANT | NEW_SIGNAL |
|---|---|---|---|---|---|
| PDR_B1 | 312 | 188 | 27 | 73 | 714 |
| PDR_B2 | 233 | 331 | 18 | 18 | 1051 |
| PDR_C | 424 | 140 | 16 | 20 | 70 |
| PDR_D | 0 | 0 | 378 | 222 | 41 |


SAME / EARLIER / LATER compare a variant signal with the baseline signal of the same setup cycle; REMOVED_BY_VARIANT = a baseline cycle with no variant signal; NEW_SIGNAL = a variant signal in a cycle the baseline does not have (variants that accept more candles open more retest cycles).

* Distinct setup cycles in which B1 or B2 entered earlier than the baseline because a green candle closing at or below the ceiling was accepted: 205 (B1 and B2 rows counted separately: 379). Cycles in which PDR-C entered earlier because the retest candle itself confirmed: 140. Delayed cycles whose first green candle after the retest closed at or below the ceiling: 215 of 215 (in 20 of them the retest candle was additionally green above the ceiling).

## B1, B2 and C change two things at once

The owner's definitions of B1, B2 and C are green-only, so besides the ceiling / retest-candle change each also drops the baseline's lower-price-rejection (non-green) confirmation route. Variant-versus-baseline differences in cycles whose baseline entry used that dropped route (windows combined): PDR_B1 - later 27, earlier 0, removed 5; PDR_B2 - later 18, earlier 12, removed 2; PDR_C - later 16, earlier 12, removed 4. Those differences are not caused by the ceiling or retest-candle question and must not be attributed to it (`baseline_confirmation_route` column in the variant CSVs). A variant that keeps the rejection route was not run.

## Entry cutoff

Only 404 of the 600 baseline cycle signals fall at or before the 13:00 entry cutoff (and 133 of the 215 delayed cycles); the rest can never trade and the portfolio controller discards them. The cycle-level audit keeps them because the 215 is a cycle count; use `engine_signal_tradable_before_13_00_cutoff` to restrict to tradable cycles. Portfolio results are unaffected.

* Candle-strength: the body percentage of every variant's signal candle is in the variant CSVs; no strength threshold is applied inside PDR variants.

## Approval status

| variant | status |
|---|---|
| PDR-A | approved baseline |
| PDR-B1 / B2 | AUTHOR_CONFIRMATION_REQUIRED (bypass the owner-approved close-above-ceiling rule) |
| PDR-C | AUTHOR_CONFIRMATION_REQUIRED (retest-candle sequencing unresolved) |
| PDR-D | MECHANICAL_RESEARCH_CONVENTION (second-confirmation conditions are not defined by the author) |

Files: `pdr_variant_B_signals.csv` (B1 and B2), `pdr_variant_C_signals.csv`, `pdr_variant_D_signals.csv`, charts in `charts_pdr/`.