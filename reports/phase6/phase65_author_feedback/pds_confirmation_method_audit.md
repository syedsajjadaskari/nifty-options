# PDS confirmation methods: first versus second

| method | source | first-vs-second applicable? | mandatory support break? |
|---|---|---|---|
| Method 1 - good red candle | PDS guide: 'good red candle'; the first red candle at the zone must be good (body size and close numerically undefined) | YES (research): second = a later independently good red candle at the zone | no |
| Method 2 - red pin bar, higher-price rejection | PDS guide: red pin bar with a long upper wick into / above the zone (ratio undefined) | YES (research): second = a later independent red pin bar | no |
| Method 3 - small-support break (fallback) | PDS guide: a weak first red candle is NOT taken; wait for a small support to form and break | NO: the mandatory support break is the trigger; no first-red-candle entry exists; no source-supported alternative | YES - never bypassed; left unchanged |


Variants compared: the frozen numeric-threshold engine (source-consistent reference), the Phase 5.3 first-eligible engine (= the baseline), and PDS-SECOND (first eligible bearish candle registered but not traded; a later independently eligible candle triggers; the cycle is abandoned if price closes above the zone first). Required zone interaction, bearish pattern and close location are those of the baseline tests; the retest candle may be the first eligible candle (as in the baseline).

Primary-window effect on PDS trades: baseline 19, frozen 15, second-confirmation 11; Methods 1/2 second-confirmation signals found: window A 29, window B 75 (Method 3 signals are not second confirmations and are no longer listed as such).

Method 3 signal counts are NOT identical to the baseline's (window A 19 to 18: 1 baseline-only, 0 variant-only; window B 43 to 41: 2 baseline-only, 0 variant-only). A baseline-only Method 3 signal is one whose cycle was consumed by the second-confirmation path (a displacement); the variant emits no Method 3 signal that lacks the support break, so the mandatory break is never bypassed.

**Convention interplay (open decision).** The variant keeps the frozen branch 'a weak red candle at the zone sends the cycle to Method 3'. After the first eligible candle is registered, a later WEAK red candle therefore ends the Methods 1/2 path of that cycle. If such a candle were simply skipped instead, the independent re-derivation finds 39 instead of 29 second signals in window A and 90 instead of 75 in window B (`pds_second_weak_red_interplay.json`). PDS-SECOND results are for the as-implemented reading; the alternative reading was not simulated.

Approval status of the second-confirmation variant: MECHANICAL_RESEARCH_CONVENTION / AUTHOR_CONFIRMATION_REQUIRED. The Method 3 trigger rule is unchanged (counts differ only by displacement, above). No candidate bypasses a mandatory support break. Per changed entry: date, method, original signal, first / second eligible candle, zone, body and wick percentages, time and entry-price differences, approval status - `pds_confirmation_variants.csv`; charts in `charts_pds/`.