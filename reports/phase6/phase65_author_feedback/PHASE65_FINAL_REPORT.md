# PHASE 6.5 - FINAL REPORT (checkpoint sections 1-4 + continuation sections 5-14)

**Written for:** the strategy owner. Synthetic NIFTY index-point P&L (6 lots x 65 units; the index is not tradable; not option or futures P&L). Research only: no configuration selected or ranked, nothing committed or pushed, no order placed, no paper-trading file changed and no Phase 7.0 file written, modified, staged or deleted (Phase 7.0 files were only read for an inventory). Neither window is untouched out-of-sample. The checkpoint findings (ORB disputes, candle-strength variants, 215 delayed PDR cycles) are preserved in `README.md` and their reports.

## Performance matrix (win = positive gross P&L of the whole completed trade; net columns are after Rs 70 per trade; PF and max drawdown are net)

| window | config | trades | winners/losers/BE | gross win rate | net win rate | PF (net) | gross Rs | net Rs | max DD Rs (net) |
|---|---|---|---|---|---|---|---|---|---|
| A | BASE | 183 | 98/85/0 | 53.55% | 53.55% | 1.022 | +37,420 | +24,610 | 243,401 |
| A | S60 | 159 | 88/71/0 | 55.35% | 55.35% | 1.121 | +123,844 | +112,714 | 162,781 |
| A | S70 | 149 | 80/69/0 | 53.69% | 53.69% | 1.046 | +51,967 | +41,537 | 154,210 |
| A | SD | 182 | 99/83/0 | 54.4% | 54.4% | 1.05 | +67,382 | +54,642 | 243,401 |
| A | PDR_B1 | 192 | 102/90/0 | 53.12% | 53.12% | 0.974 | -17,960 | -31,400 | 257,121 |
| A | PDR_B2 | 190 | 100/90/0 | 52.63% | 52.63% | 0.979 | -11,330 | -24,630 | 257,121 |
| A | PDR_C | 181 | 96/85/0 | 53.04% | 53.04% | 1.028 | +44,050 | +31,380 | 243,401 |
| A | PDR_D | 183 | 93/90/0 | 50.82% | 50.82% | 0.932 | -68,250 | -81,060 | 279,505 |
| A | PDS_FROZEN | 182 | 100/82/0 | 54.95% | 54.95% | 1.07 | +88,832 | +76,092 | 199,066 |
| A | PDS_SECOND | 179 | 100/79/0 | 55.87% | 55.87% | 1.097 | +113,188 | +100,658 | 185,346 |
| B | BASE | 603 | 345/258/0 | 57.21% | 57.21% | 1.069 | +281,395 | +239,185 | 291,703 |
| B | S60 | 535 | 309/226/0 | 57.76% | 57.76% | 1.159 | +513,142 | +475,692 | 227,848 |
| B | S70 | 468 | 271/197/0 | 57.91% | 57.91% | 1.117 | +336,658 | +303,898 | 198,896 |
| B | SD | 600 | 343/257/0 | 57.17% | 57.17% | 1.069 | +279,571 | +237,571 | 291,528 |
| B | PDR_B1 | 627 | 365/262/0 | 58.21% | 58.21% | 1.113 | +437,521 | +393,631 | 260,491 |
| B | PDR_B2 | 634 | 366/268/0 | 57.73% | 57.73% | 1.09 | +366,766 | +322,386 | 287,931 |
| B | PDR_C | 606 | 345/261/0 | 56.93% | 56.93% | 1.057 | +240,942 | +198,522 | 332,863 |
| B | PDR_D | 585 | 343/242/0 | 58.63% | 58.63% | 1.149 | +517,930 | +476,980 | 211,629 |
| B | PDS_FROZEN | 600 | 340/260/0 | 56.67% | 56.67% | 1.057 | +241,156 | +199,156 | 309,273 |
| B | PDS_SECOND | 585 | 334/251/0 | 57.09% | 57.09% | 1.071 | +278,635 | +237,685 | 281,404 |


A = 2025-09..2026-08 (primary); B = 2022-09..2025-08 (robustness); both 5paisa.

## Strategy-wise win rates inside each portfolio (winners / trades)

| window | config | IRF | ORB | PDR | PDS | RF |
|---|---|---|---|---|---|---|
| A | BASE | 41/85 = 48.24% | 19/39 = 48.72% | 21/31 = 67.74% | 11/19 = 57.89% | 6/9 = 66.67% |
| A | S60 | 39/74 = 52.7% | 19/39 = 48.72% | 17/25 = 68.0% | 12/19 = 63.16% | 1/2 = 50.0% |
| A | S70 | 33/68 = 48.53% | 19/39 = 48.72% | 16/23 = 69.57% | 12/19 = 63.16% | 0 trades |
| A | SD | 42/86 = 48.84% | 19/39 = 48.72% | 21/31 = 67.74% | 11/17 = 64.71% | 6/9 = 66.67% |
| A | PDR_B1 | 41/85 = 48.24% | 19/39 = 48.72% | 26/41 = 63.41% | 11/19 = 57.89% | 5/8 = 62.5% |
| A | PDR_B2 | 41/85 = 48.24% | 17/37 = 45.95% | 26/41 = 63.41% | 11/19 = 57.89% | 5/8 = 62.5% |
| A | PDR_C | 41/85 = 48.24% | 17/37 = 45.95% | 21/31 = 67.74% | 11/19 = 57.89% | 6/9 = 66.67% |
| A | PDR_D | 41/85 = 48.24% | 19/39 = 48.72% | 16/31 = 51.61% | 11/19 = 57.89% | 6/9 = 66.67% |
| A | PDS_FROZEN | 44/88 = 50.0% | 19/39 = 48.72% | 21/31 = 67.74% | 10/15 = 66.67% | 6/9 = 66.67% |
| A | PDS_SECOND | 45/89 = 50.56% | 19/39 = 48.72% | 21/31 = 67.74% | 9/11 = 81.82% | 6/9 = 66.67% |
| B | BASE | 164/279 = 58.78% | 56/92 = 60.87% | 64/129 = 49.61% | 33/59 = 55.93% | 28/44 = 63.64% |
| B | S60 | 152/249 = 61.04% | 56/92 = 60.87% | 51/109 = 46.79% | 27/50 = 54.0% | 23/35 = 65.71% |
| B | S70 | 133/211 = 63.03% | 56/92 = 60.87% | 47/101 = 46.53% | 23/46 = 50.0% | 12/18 = 66.67% |
| B | SD | 168/286 = 58.74% | 56/92 = 60.87% | 64/129 = 49.61% | 27/49 = 55.1% | 28/44 = 63.64% |
| B | PDR_B1 | 164/279 = 58.78% | 56/92 = 60.87% | 89/161 = 55.28% | 33/59 = 55.93% | 23/36 = 63.89% |
| B | PDR_B2 | 164/279 = 58.78% | 56/92 = 60.87% | 90/168 = 53.57% | 33/59 = 55.93% | 23/36 = 63.89% |
| B | PDR_C | 164/279 = 58.78% | 56/92 = 60.87% | 65/133 = 48.87% | 33/59 = 55.93% | 27/43 = 62.79% |
| B | PDR_D | 165/280 = 58.93% | 56/92 = 60.87% | 61/110 = 55.45% | 33/59 = 55.93% | 28/44 = 63.64% |
| B | PDS_FROZEN | 170/295 = 57.63% | 56/92 = 60.87% | 64/129 = 49.61% | 22/40 = 55.0% | 28/44 = 63.64% |
| B | PDS_SECOND | 168/291 = 57.73% | 57/93 = 61.29% | 64/129 = 49.61% | 17/28 = 60.71% | 28/44 = 63.64% |


## Answers to the 40 questions

**1.** Genuine implementation defects among the 39 ORB-vs-IRF disagreements: **0** (every valid ORB V2 day is selected under first-valid-signal; no priority rule exists). **2.** The 27 ORB rejections: 12 fail only provisional conventions (pattern / level construction); 14 fail the source-supported 20% wrong-side-wick rule (13 of them also fail a provisional convention; the rulebook's own examples are in tension with that rule); 1 fails the unconfirmed 250/300-point gap limit (together with the provisional pattern convention). **3.** Objectively valid ORB V2 entries: **12**, all selected. **4.** Dependent on provisional rules: all 12 valid days rest on at least one provisional element, and 26 of the 27 rejected days fail at least one provisional convention (the remaining 1 fails only the source-supported wick rule). **5.** The 27 rejected days were simulated as hypothetical ORB paths in the EMA-side direction: 12 reach TARGET, 6 T1 then buffer stop, 9 full stop; 8 dates are cases where that hypothetical ORB path reaches target while the executed IRF trade hits its full stop. They are hypotheticals of setups the rulebook-as-coded rejects, not portfolio results.
**6.** Weak (< 60% body) confirming candles per strategy (configuration C, primary): IRF 355/786; ORB 10/39; PDR 75/147; PDS 56/111; RF 7/12. **7.** 60% removes 65 of 183 baseline trades (direct 65, portfolio 0). **8.** and adds 41 new trades (direct 0, portfolio 41). **9.** 70%: removes 83, adds 49. **10.** Pattern-aware: removes 5 (strategies: PDS), adds 4 (strategies: IRF, PDS). **11.** A universal filter would wrongly exclude IRF Method 3 sweeps (wick-based), PDR lower-price-rejection / hammer confirmations, PDS Method 2 pin bars and Method 3 small-support breaks, and ORB pin-bar / engulfing routes. **12.** Strict time-label agreements (same date, same strategy and the same journal time label; not verified trade matches): baseline 67, 60% 58, 70% 55, pattern-aware 67.
**13.** The 215 delayed cycles split into: A (earlier green closed at/below the zone) 195, C (the earliest green was the retest candle) 20, D (rejected by a defect) 0, other 0. **14.** Earlier candles that met every requirement as coded in the repository but were skipped by the engine: **0** (the independent recomputation shares those coded conventions, so this shows the code applies its own rules consistently; it does not show the conventions match the author's intent). **15.** PDR-B earlier entries versus the baseline cycle (windows combined): B1 188, B2 331 (total 519). **16.** PDR-C earlier entries: 140 cycles; C is green-only, so part of its differences from the baseline come from dropping the lower-price-rejection route (cycles whose baseline entry used that route: later 16, earlier 12, removed 4), not from the retest-candle change. **17.** PDR-D later entries: 378. **18.** In 215 of the 215 delayed cycles the first green candle after the retest closed at or below the ceiling, so the owner-approved close-above-ceiling requirement is the proximate cause of the delay in every one of them. **19.** In 20 of those cycles the retest candle itself was additionally a green close above the ceiling and would have qualified under a retest-may-confirm convention (a green-above-ceiling retest candle occurs in 147 of 600 cycle rows). Only 133 of the 215 delayed cycles end at or before the 13:00 entry cutoff and could trade. **20.** Still to confirm: close-above-ceiling, retest candle sequencing, second-confirmation conditions, any strength threshold (see `remaining_author_decisions.md`).
**21.** PDS Methods 1 and 2 support a first-versus-second comparison; Method 3 does not (its mandatory support break is the trigger). **22.** PDS trades inside the portfolio 19 -> 11 (primary window); Methods 1/2 second signals found: A 29, B 75 (A 39 / B 90 if a weak red candle between the two eligible candles were skipped instead of ending the path: an open convention). **23.** No candidate bypasses the mandatory Method 3 support break: the variant never emits a Method 3 signal without it. Method 3 signal counts are not identical to the baseline's (window A 19 to 18, window B 43 to 41) because a second-confirmation cycle can consume a day the baseline used for Method 3 (a displacement, not a bypass).
**24./25.** Strategy-wise win rates and trade counts for every configuration and window are in the matrix above (`strategy_win_rates.csv`). **26.** Combined win rates: see the performance matrix. **27.** Gross / net P&L, profit factor, maximum drawdown: performance matrix; costs in `cost_slippage_sensitivity.csv`. **28.** Across windows: BASE: A +37,420 / B +281,395; S60: A +123,844 / B +513,142; S70: A +51,967 / B +336,658; SD: A +67,382 / B +279,571; PDR_B1: A -17,960 / B +437,521; PDR_B2: A -11,330 / B +366,766; PDR_C: A +44,050 / B +240,942; PDR_D: A -68,250 / B +517,930; PDS_FROZEN: A +88,832 / B +241,156; PDS_SECOND: A +113,188 / B +278,635. Sign of gross P&L differs between the two windows for: PDR_B1, PDR_B2, PDR_D (a single historical path; differences between configurations are not evidence of an edge). **29.** Eligibility versus portfolio effect (primary): S60: removed direct 65/portfolio 0, added direct 0/portfolio 41; S70: removed direct 83/portfolio 0, added direct 0/portfolio 49; SD: removed direct 5/portfolio 0, added direct 0/portfolio 4; PDR_B1: removed direct 6/portfolio 6, added direct 21/portfolio 0; PDR_B2: removed direct 6/portfolio 13, added direct 26/portfolio 0; PDR_C: removed direct 6/portfolio 2, added direct 5/portfolio 1; PDR_D: removed direct 27/portfolio 0, added direct 21/portfolio 6; PDS_FROZEN: removed direct 10/portfolio 0, added direct 5/portfolio 4; PDS_SECOND: removed direct 16/portfolio 0, added direct 1/portfolio 11. **30.** None of the changes is supported by source fidelity: the strength gates have no source threshold, B1/B2 bypass an owner-approved rule, C/D/PDS-SECOND rest on unresolved or undefined conventions; any difference is historical and in-sample. Measured for the strength gates (primary window, gross): S60 removed trades -43,232 Rs and added trades +43,192 Rs; S70 -60,976 / -46,430; SD +10,403 / +40,365. Every added trade is a portfolio effect (a different signal selected after the gate removed an earlier trade), every removed trade a direct effect.
**31.-33.** Journal (primary window, 190 rows; strict / time-tolerant / date-only / manual-only / automated-only / wrong-strategy dates / outcome agreement): BASE: 67/15/17/91/84/53/74 of 82; S60: 58/9/17/106/75/51/64 of 67; S70: 55/8/17/110/69/48/58 of 63; SD: 67/15/17/91/83/54/74 of 82; PDR_B1: 67/14/17/92/94/55/73 of 81; PDR_B2: 66/13/17/94/94/55/71 of 79; PDR_C: 66/14/17/93/84/53/72 of 80; PDR_D: 63/19/17/91/84/53/73 of 82; PDS_FROZEN: 68/15/18/89/81/52/75 of 83; PDS_SECOND: 67/16/19/88/77/51/75 of 83. No verified exact trade match exists or is possible (no direction / price in the journal). **34.** Author observations that the data are consistent with: ORB V2 is selected whenever it is valid; weak candles are accepted because no source defines a body rule; PDR skips earlier green candles that close at or inside the zone (215 of the 215 delayed cycles; 20 of them also had a qualifying green retest candle) because of the approved close-above-ceiling rule and the provisional retest convention - none is an engine defect. **35.** Unresolved: whether the author wants those conventions relaxed, the ORB provisional rules, second-confirmation definitions.
**36.** Frozen baseline modified: **no** (`final_preservation_verification.md`: frozen files changed 0, removed 0). **37.** Phase 7.0 / 7.1 files written, staged, reset, run or deleted by this work: **none** (read-only inventory only: file metadata, the source text parsed but never executed, and the published Markdown / CSV / JSON outputs). During the run the other process itself changed 1 existing and added 1498 new Phase 7.0 file(s) among 2913 present (attributed by ownership, not observed directly), so those files cannot be hash-verified against the start snapshot; a further externally owned Phase 7.1 effort (23 files, none read) appeared during the run. **38.** Paper-trading application changed: **no**. **39.** Reproducible from the manifests: yes (`complete_configuration_manifest.json`, `continuation_before_snapshot.json`); the strength configurations were re-run and match the checkpoint ledgers exactly (True). **40.** Owner decisions before any deployment: the eight items in `remaining_author_decisions.md`; no variant here is recommended.

## Verification summary
* Independent PDR / PDS recomputation, 7623/7623 execution reconstructions, journal recount, trade-set reconciliation and a look-ahead prefix test: `final_independent_audit.md`.
* Phase 7.0 overlap (read-only): `phase7_irf_overlap_inventory.md`, `phase7_signal_comparison.csv`.