# Candle body-strength research

`body_percentage = |close - open| / (high - low) * 100`; zero-range candles have no percentage and are flagged, never treated as 0 or 100. No global strength filter is active by default; variants B, C, D are opt-in research wrappers (`strategies/strength_gate.py`).

## Authority matrix (is a strength threshold in the source?)

| strategy | method | confirming_candle | body_strength_in_source | later_candle_required | threshold_status | note |
|---|---|---|---|---|---|---|
| IRF | Method 1 (frozen) / new Method 1 rulebook | close back inside / below IRH | none | yes: the candle after the breakout (frozen) or any later candle (new rulebook) | DIAGNOSTIC_ONLY | no body rule in either IRF guide or the new rulebooks |
| IRF | Method 2A (first red candle support break) | a later candle closes below the first red candle's wick low | none | yes (after the reference red candle) | DIAGNOSTIC_ONLY | colour/size of the breaking candle is not specified |
| IRF | Method 2B (resistance break) | a red candle closes back below resistance | colour only (red) | yes | DIAGNOSTIC_ONLY | 'red candle' has no size requirement |
| IRF | Method 3 (sweep) | red sweep candle closing below support | NO body rule; the 60-70% is the share of the UPPER WICK outside IRH | no (the sweep candle itself confirms) | NOT_A_BODY_RULE (exempt) | must not be read as a 60-70% body requirement |
| IRF (new rulebooks) | New Method 1 / New Method 2 | failure candle closing back below the level | none | yes | DIAGNOSTIC_ONLY | both rulebooks specify closes only |
| ORB V2 | 09:20 decision | the 09:15 candle | full-body route = total wick <= 20% (=> body >= 80%); other routes: pin bar / engulfing | no | SOURCE_SUPPORTED for the full-body route (already stricter than 60/70) | a 60/70% gate cannot remove a full-body ORB signal; pin-bar / engulfing routes are exempt |
| PDR | confirmation after the zone retest | a green candle (or lower-price rejection) closing strictly above the ceiling | colour only; the guide and the author say no fixed percentage or wick size is required | yes (after the retest) | AUTHOR_PROPOSED (60/70%) - not in the source | hammer / rejection route exempt; the owner asked for the FIRST eligible candle |
| PDS | Method 1 good red candle | a red candle at the zone with a good body | 'good body' is required but NOT numerically defined | the first red candle at the zone | SOURCE_SUPPORTED_REQUIREMENT, threshold undefined (60% is a candidate) | weak first red candle -> Method 3 |
| PDS | Method 2 pin bar / Method 3 small-support break | red pin bar with higher price rejection / break of a small support | none (pin-bar ratio unspecified) | Method 3: yes | NOT_A_BODY_RULE (exempt) | a small body is normal for a pin bar |
| RF | RF confirmation | see RF guide | not specified (the guide only says to measure the whole candle including wicks) | nan | DIAGNOSTIC_ONLY | no strength statement found in the RF guide |


## Body-percentage distribution of the confirming candles (configuration C, primary window)

| strategy | method | signals | zero_range | mean_body_pct | median_body_pct | share_below_60_pct | share_below_70_pct | colour_matches_direction_pct |
|---|---|---|---|---|---|---|---|---|
| IRF | Method 1 | 267 | 0 | 64.4 | 68.2 | 37.5 | 53.2 | 100.0 |
| IRF | Method 2A | 271 | 0 | 60.0 | 63.9 | 45.4 | 57.2 | 95.9 |
| IRF | Method 2B | 248 | 0 | 53.7 | 57.7 | 53.2 | 68.1 | 100.0 |
| ORB | ORB-V2 | 39 | 0 | 71.5 | 83.8 | 25.6 | 25.6 | 100.0 |
| PDR | PDR | 147 | 0 | 58.5 | 57.7 | 51.0 | 62.6 | 98.0 |
| PDS | Method 1 | 73 | 0 | 66.4 | 66.9 | 42.5 | 56.2 | 100.0 |
| PDS | Method 2 | 19 | 0 | 24.7 | 28.1 | 100.0 | 100.0 | 100.0 |
| PDS | Method 3 | 19 | 0 | 66.5 | 69.4 | 31.6 | 63.2 | 100.0 |
| RF | RF | 12 | 0 | 59.1 | 59.3 | 58.3 | 75.0 | 100.0 |


## Variants through the frozen controller (primary window; the gate is a post-hoc filter and an engine does not search for a stronger LATER candle after a rejection; the controller then re-sequences the day, so a variant is a different portfolio and its trade count is a NET figure)

| window | variant | strategy | trades | win_rate_pct | profit_factor | gross_rs | net_rs_70 | max_drawdown_rs |
|---|---|---|---|---|---|---|---|---|
| A | A | ALL | 183 | 53.55 | 1.033 | 37420 | 24610 | 239831 |
| A | B | ALL | 159 | 55.35 | 1.133 | 123844 | 112714 | 159491 |
| A | C | ALL | 149 | 53.69 | 1.058 | 51967 | 41537 | 152880 |
| A | D | ALL | 182 | 54.4 | 1.062 | 67382 | 54642 | 239831 |


True trade-set changes versus the baseline:

| window | variant | baseline_trades | variant_trades | baseline_trades_kept_identical | baseline_trades_removed | new_trades_added_by_resequencing | removed_by_strategy | added_by_strategy | gross_rs_of_removed_baseline_trades | gross_rs_of_added_trades | net_gross_change_rs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | B | 183 | 159 | 118 | 65 | 41 | {"IRF": 40, "PDR": 13, "RF": 7, "PDS": 5} | {"IRF": 29, "PDR": 7, "PDS": 5} | -43232.0 | 43192.0 | 86424.0 |
| A | C | 183 | 149 | 100 | 83 | 49 | {"IRF": 51, "PDR": 15, "RF": 9, "PDS": 8} | {"IRF": 34, "PDS": 8, "PDR": 7} | -60976.0 | -46430.0 | 14547.0 |
| A | D | 183 | 182 | 178 | 5 | 4 | {"PDS": 5} | {"PDS": 3, "IRF": 1} | 10403.0 | 40365.0 | 29962.0 |
| B | B | 603 | 535 | 394 | 209 | 141 | {"IRF": 144, "PDR": 39, "PDS": 14, "RF": 12} | {"IRF": 114, "PDR": 19, "PDS": 5, "RF": 3} | -193498.0 | 38249.0 | 231748.0 |
| B | C | 603 | 468 | 310 | 293 | 158 | {"IRF": 184, "PDR": 60, "RF": 28, "PDS": 21} | {"IRF": 116, "PDR": 32, "PDS": 8, "RF": 2} | -92479.0 | -37216.0 | 55263.0 |
| B | D | 603 | 600 | 590 | 13 | 10 | {"PDS": 13} | {"IRF": 7, "PDS": 3} | -5392.0 | -7215.0 | -1823.0 |


Per strategy (win rate = share of trades with positive gross P&L):

| window | variant | strategy | trades | win_rate_pct | profit_factor | gross_rs | net_rs_70 | max_drawdown_rs |
|---|---|---|---|---|---|---|---|---|
| A | A | IRF | 85 | 48.24 | 0.794 | -123952 | -129902 | 207685 |
| A | A | ORB | 39 | 48.72 | 0.932 | -15971 | -18701 | 83246 |
| A | A | PDR | 31 | 67.74 | 1.9 | 117975 | 115805 | 35490 |
| A | A | PDS | 19 | 57.89 | 1.457 | 50008 | 48678 | 64155 |
| A | A | RF | 9 | 66.67 | 1.229 | 9360 | 8730 | 36855 |
| A | B | IRF | 74 | 52.7 | 0.908 | -43953 | -49133 | 116805 |
| A | B | ORB | 39 | 48.72 | 0.932 | -15971 | -18701 | 83246 |
| A | B | PDR | 25 | 68.0 | 2.062 | 112183 | 110433 | 31590 |
| A | B | PDS | 19 | 63.16 | 1.848 | 81139 | 79809 | 50505 |
| A | B | RF | 2 | 50.0 | 0.3 | -9555 | -9695 | 13650 |
| A | C | IRF | 68 | 48.53 | 0.749 | -120120 | -124880 | 158457 |
| A | C | ORB | 39 | 48.72 | 0.932 | -15971 | -18701 | 83246 |
| A | C | PDR | 23 | 69.57 | 2.162 | 106918 | 105308 | 27300 |
| A | C | PDS | 19 | 63.16 | 1.848 | 81139 | 79809 | 37031 |
| A | C | RF | 0 | nan | nan | 0 | 0 | 0 |
| A | D | IRF | 86 | 48.84 | 0.8 | -119857 | -125877 | 207685 |
| A | D | ORB | 39 | 48.72 | 0.932 | -15971 | -18701 | 83246 |
| A | D | PDR | 31 | 67.74 | 1.9 | 117975 | 115805 | 35490 |
| A | D | PDS | 17 | 64.71 | 1.924 | 75874 | 74684 | 50505 |
| A | D | RF | 9 | 66.67 | 1.229 | 9360 | 8730 | 36855 |


Signals gated:

| window | variant | strategy | method | gate_applies | kept | signals |
|---|---|---|---|---|---|---|
| A | B | IRF | Method 1 | True | False | 100 |
| A | B | IRF | Method 1 | True | True | 167 |
| A | B | IRF | Method 2A | True | False | 113 |
| A | B | IRF | Method 2A | True | True | 147 |
| A | B | IRF | Method 2B | True | False | 132 |
| A | B | IRF | Method 2B | True | True | 116 |
| A | B | ORB | ORB-V2 | True | True | 16 |
| A | B | PDR | PDR | True | False | 60 |
| A | B | PDR | PDR | True | True | 72 |
| A | B | PDS | Method 1 | True | False | 31 |
| A | B | PDS | Method 1 | True | True | 42 |
| A | B | RF | RF | True | False | 7 |
| A | B | RF | RF | True | True | 5 |
| A | C | IRF | Method 1 | True | False | 142 |
| A | C | IRF | Method 1 | True | True | 125 |
| A | C | IRF | Method 2A | True | False | 145 |
| A | C | IRF | Method 2A | True | True | 115 |
| A | C | IRF | Method 2B | True | False | 169 |
| A | C | IRF | Method 2B | True | True | 79 |
| A | C | ORB | ORB-V2 | True | True | 16 |
| A | C | PDR | PDR | True | False | 77 |
| A | C | PDR | PDR | True | True | 55 |
| A | C | PDS | Method 1 | True | False | 41 |
| A | C | PDS | Method 1 | True | True | 32 |
| A | C | RF | RF | True | False | 9 |
| A | C | RF | RF | True | True | 3 |
| A | D | ORB | ORB-V2 | True | True | 16 |
| A | D | PDS | Method 1 | True | False | 31 |
| A | D | PDS | Method 1 | True | True | 42 |


## Manual-journal reconciliation per variant (primary window; Phase 5.6 matcher)

| variant | trades | strict | time_tolerant | date_strategy_only | manual_only | automated_only | strict_IRF | strict_ORB | strict_PDR | strict_PDS | strict_RF | tolerant_IRF | tolerant_ORB | tolerant_PDR | tolerant_PDS | tolerant_RF | outcome_label_agree_strict_tolerant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 183 | 67 | 15 | 17 | 91 | 84 | 20 | 38 | 4 | 1 | 4 | 11 | 0 | 1 | 0 | 3 | 74 |
| B | 159 | 58 | 9 | 17 | 106 | 75 | 16 | 38 | 2 | 1 | 1 | 8 | 0 | 1 | 0 | 0 | 64 |
| C | 149 | 55 | 8 | 17 | 110 | 69 | 14 | 38 | 1 | 2 | 0 | 7 | 0 | 1 | 0 | 0 | 58 |
| D | 182 | 67 | 15 | 17 | 91 | 83 | 20 | 38 | 4 | 1 | 4 | 11 | 0 | 1 | 0 | 3 | 74 |


## Win rate by body bucket of the executed trades' confirming candle (DIAGNOSTIC only; no filter decision follows from it)

| strategy | bucket | trades | win_rate_pct | profit_factor | gross_rs | net_rs_70 |
|---|---|---|---|---|---|---|
| IRF | <60% | 42 | 47.62 | 0.787 | -63970 | -66910 |
| IRF | 60-70% | 11 | 45.45 | 0.721 | -22815 | -23585 |
| IRF | >=70% | 32 | 50.0 | 0.83 | -37167 | -39407 |
| ORB | <60% | 10 | 30.0 | 0.307 | -56745 | -57445 |
| ORB | >=70% | 29 | 55.17 | 1.266 | 40774 | 38744 |
| PDR | <60% | 17 | 58.82 | 1.277 | 24960 | 23770 |
| PDR | 60-70% | 2 | 50.0 | 1.386 | 5265 | 5125 |
| PDR | >=70% | 12 | 83.33 | 4.214 | 87750 | 86910 |
| PDS | <60% | 10 | 50.0 | 0.89 | -7537 | -8237 |
| PDS | 60-70% | 3 | 66.67 | 1.686 | 9360 | 9150 |
| PDS | >=70% | 6 | 66.67 | 2.754 | 48184 | 47764 |
| RF | <60% | 7 | 71.43 | 1.693 | 18915 | 18425 |
| RF | 60-70% | 2 | 50.0 | 0.3 | -9555 | -9695 |


Reading: ORB V2 is untouched by every gate that matters (its full-body route already means body >= 80%; pin-bar / engulfing routes are exempt); IRF Method 3 is wick-based and exempt; PDR's guide and the author specify only 'a green candle'; PDS Method 1 'good red candle' is the only place where the source asks for a body quality it never defines. Variant D rejects PDS Method 1 signals only; B and C act mainly on IRF Methods 1/2A/2B and PDR green-body confirmations, which have no body-strength statement in any source. Because the controller takes one trade at a time, removing even a single signal can re-sequence a day and move the P&L, so differences between variants must not be read as evidence for a threshold. The journal view agrees with caution: strict journal matches fall from 67 (A) to 58 (B) and 55 (C).

Variant A equals configuration C exactly: True.