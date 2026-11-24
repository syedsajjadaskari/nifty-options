# Phase 7.0 - complete IRF reconstruction from the two new rulebooks

**Written for:** the strategy owner. Research only: synthetic NIFTY **index-point** results (not options/futures P&L); no order placed; no parameter optimised; no existing strategy, dataset, journal or paper-trading configuration touched; nothing committed, staged or pushed. The two PDFs remain untracked.

Method 1 and Method 2 were rebuilt **independently, from their own PDF only**, in the new package `src/nifty_trading/research/irf_v3/` (no call into any older IRF engine; generic one-minute readers, the NSE calendar and the bar-executability classifier were reused after verification). A third, separately written NumPy/`resample` implementation (`audit.py`) reconstructed every signal and trade; **0 mismatches** over all scenarios and both windows.

Start with this README, then `source_rule_comparison.md`, `unresolved_author_questions.md`, `source_example_reproduction.csv`, `historical_performance_comparison.csv`, `manual_journal_reconciliation.csv`.

## Performance (index points; SL scenarios are separately labelled because the PDFs do not choose between 35 and 40)

Window A = 2025-09-01..2026-08-31 (5paisa one-minute data, 246 evaluable sessions). Window B = 2022-09-01..2025-08-31 (736 sessions). Win = gross points > 0 on a closed trade. `signals` = first signals incl. those after the 13:00 cutoff (not tradable); for COMBINED it is the number of days traded.

| window | scenario | book | sessions | signals | trades | W | L | win% | PF | gross pts | avg W | avg L | max DD pts | SL | TP | forced |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | SL40_T60 | M1 | 246 | 153 | 125 | 55 | 70 | 44.0 | 1.142 | 397.8 | 58.17 | -40.02 | 400.0 | 70 | 52 | 3 |
| A | SL40_T60 | M2 | 246 | 113 | 86 | 33 | 53 | 38.37 | 0.9 | -202.45 | 55.33 | -38.27 | 592.9 | 49 | 28 | 9 |
| A | SL40_T60 | COMBINED | 246 | 139 | 139 | 58 | 81 | 41.73 | 1.032 | 103.2 | 57.24 | -39.71 | 501.2 | 80 | 54 | 5 |
| A | SL35_T60 | M1 | 246 | 153 | 125 | 48 | 77 | 38.4 | 1.05 | 135.55 | 58.97 | -35.0 | 410.0 | 77 | 46 | 2 |
| A | SL35_T60 | M2 | 246 | 113 | 86 | 32 | 54 | 37.21 | 0.967 | -61.3 | 55.77 | -34.19 | 448.55 | 51 | 28 | 7 |
| A | SL35_T60 | COMBINED | 246 | 139 | 139 | 52 | 87 | 37.41 | 0.995 | -14.35 | 57.9 | -34.77 | 440.0 | 86 | 49 | 4 |
| B | SL40_T60 | M1 | 736 | 433 | 376 | 168 | 208 | 44.68 | 1.159 | 1248.9 | 54.3 | -37.85 | 803.6 | 191 | 144 | 41 |
| B | SL40_T60 | M2 | 736 | 332 | 268 | 119 | 149 | 44.4 | 1.123 | 684.9 | 52.61 | -37.42 | 735.95 | 136 | 97 | 35 |
| B | SL40_T60 | COMBINED | 736 | 440 | 440 | 199 | 241 | 45.23 | 1.173 | 1580.85 | 53.96 | -38.0 | 567.95 | 224 | 169 | 47 |
| B | SL35_T60 | M1 | 736 | 433 | 376 | 152 | 224 | 40.43 | 1.105 | 789.0 | 54.86 | -33.71 | 610.35 | 211 | 132 | 33 |
| B | SL35_T60 | M2 | 736 | 332 | 268 | 113 | 155 | 42.16 | 1.174 | 896.15 | 53.62 | -33.31 | 738.75 | 144 | 95 | 29 |
| B | SL35_T60 | COMBINED | 736 | 440 | 440 | 184 | 256 | 41.82 | 1.152 | 1317.75 | 54.24 | -33.84 | 480.0 | 243 | 158 | 39 |

## Final questions

**1. Exact rules of Method 1.** Level = high (wick included) of the 09:15-09:20 candle. A later candle closes strictly above it (any colour; no entry). A later candle then closes strictly below the same level -> SHORT after that failure candle closes. No EMA, gap, previous-day S/R, trend, colour or body filter. Stop entry+35..40 (two scenarios), target entry-60, 1 trade/day, no entry after 1 pm. See `method1_entry_logic.md`.

**2. Exact rules of Method 2.** Level A = first-candle high. A later candle closes above A (rally breakout). The first red candle after it sets Level B = its open (body top, wick ignored); red candles before the breakout are ignored. A later candle closes above B (second breakout, no entry), a later candle closes below B -> SHORT after it closes. Same filters (none), stop and target. See `method2_entry_logic.md`.

**3. Similarities / differences.** Same first level, same stop/target, same filter list, same entry timing. M1 trades the failure of the first-candle high; M2 needs a two-stage sequence (A breakout -> first red candle -> B breakout -> B failure). `source_rule_comparison.md`.

**4. Unresolved assumptions.** 35 vs 40 stop; entry price; exit clock (and the ambiguous '1 pm' exit in M2); inclusive 13:00; same-candle tie for M2; one-trade/after-stop rule; priority between methods; whether the red breakout candle can be 'first red'; whether an armed M2 setup can expire or die. 20 items in `unresolved_author_questions.md`.

**5. Does Method 1 reproduce its source examples?** Partly, and only where it can be tested: the drawn Figure 1 reproduces exactly (level 25,035, failure close 25,030, entry 25,030, stop 25,065/25,070, target 24,970). Of the three screenshots, Example 1 is **undated** (no date is invented; a level-only search of the data stores finds no supporting session), and Examples 2 (11 Nov) and 3 (16 Nov) fall **after the end of every data store** (secondary vendor ends 2026-11-04, primary ends 2026-08-31) - they cannot be replayed. Only their printed arithmetic could be checked (internally consistent).

**6. Does Method 2 reproduce its source examples?** Figure 2 reproduces exactly (A 25,085, B 25,094, failure close 25,090, entry 25,090, target 25,030). Of the four screenshots only **Example 4 (3 Nov 2026)** has data (secondary vendor, the feed the screenshots come from): first-candle high 23,610.70 vs 23,611.15 stated (-0.45), Level B 23,621.70 vs 23,621.90 (-0.20), stop-loss outcome reproduced (-35/-40). **The engine's failure candle is 10:00-10:05 (close 23,621.00, 0.70 below B); the screenshot's entry 23,612.80 equals the close of the 10:05-10:10 candle (23,613.00), i.e. one candle later** - a 0.7-point margin that the cross-vendor differences and/or author discretion could explain; the logic was not changed to fit. Example 1 undated; Examples 2 (12 Nov) and 3 (6 Nov) have no data.

**7. Method 1 signals.** Window A 153 first-signals (125 tradable, 28 after 13:00); window B 433 (376 / 57).

**8. Method 2 signals.** Window A 113 (86 / 27); window B 332 (268 / 64).

**9. Overlap.** Dates where both methods signal: window A 104 ({'BOTH_M1_FIRST': 60, 'BOTH_M2_FIRST': 37, 'BOTH_SAME_TIME': 7}), window B 277.

**10. Which triggers first on overlapping dates.** Window A: Method 1 first on 60, Method 2 first on 37, same instant on 7 (window B: 151 / 106 / 20). The median gap M2-after-M1 is 15 minutes.

**11. Combined IRF trades.** Window A 139, window B 440 (one per day; both stop scenarios trade the same days).

**12. Standalone win rates (A, B).** SL40: M1 44.0% / 44.68%; M2 38.37% / 44.4%. SL35: M1 38.4% / 40.43%; M2 37.21% / 42.16%.

**13. Combined win rate (A, B).** SL40 41.73% / 45.23%; SL35 37.41% / 41.82%.

**14. Profit factors and max drawdowns** are in the table above (window A combined SL40: PF 1.032, DD 501.2 pts; SL35: PF 0.995, DD 440.0 pts). Index-point equity only. Costs/slippage are in `cost_slippage_sensitivity.csv`: window-A combined SL40 earns +103.2 points over 139 trades (0.74 pt/trade) and is already negative after a 1-point round-trip cost (-35.8); SL35 is negative gross (-14.35). Window-B combined SL40 (+1580.85 over 440 trades, 3.6 pt/trade) stays positive up to a 3-point round-trip cost (+260.85) and turns negative at 5 points.

**15. Manual IRF journal rows matched** (73 IRF rows, 1 on a weekend that can never match; the journal has no direction/price so **no exact trade match can be claimed**): Combined strict 34, + time-tolerant 19, + date-and-strategy-only 14, manual-only 6. Method 1 alone 27/16/18/12; Method 2 alone 14/9/17/33 (strict/tolerant/date-only/manual-only). 9 journal dates show a method-attribution difference (combined credits one method, the other's signal is nearer the journal time). Automated-only combined trades: 72 (57 on dates where the journal holds a different strategy).

**16. Versus earlier IRF implementations** (first confirmed IRF signal per date, window A): Phase 3.6 34/18/15/6; Phase 5.3 27/13/19/14; Phase 6.1 27/13/19/14. V3 Combined reaches the same strict agreement as Phase 3.6 (34) and a higher one than Phases 5.3/6.1 (27). The earlier phases' notes say 5.3/6.1 implement owner-approved EMA-28 / first-red-low support rules that the two new PDFs do not mention; this analysis does not attribute the difference to any single cause. Entry candle changed vs Phase 3.6 on 39 of 138 shared dates; vs 5.3/6.1 on 51 of 125 (`changed_entry_times_vs_earlier_phases.csv`).

**17. Primary reasons for missing trades.** Journal rows not matched by the combined engine (manual-only): 6 - listed below. Across all days without a combined trade the dominant reason is simply that price never closes above the first-candle high (`NO_CLOSE_ABOVE_LEVEL`), then breakouts that never fail, then signals that arrive after 13:00 (see `daily_verification.csv`, `no_trade_reason`).

| date | journal_time_label | journal_outcome | v3_reason_no_combined_trade |
|---|---|---|---|
| 2025-09-23 | 10:10 | Target | M1: signal at 14:15 is after the 13:00 entry cutoff ; M2: NO_CLOSE_ABOVE_LEVEL_B (missing: second breakout: close above Level B; failure below Level B) |
| 2026-01-21 | 09:35 | Target | M1: signal at 13:10 is after the 13:00 entry cutoff ; M2: signal at 13:10 is after the 13:00 entry cutoff |
| 2026-02-03 | 09:35 | SL | M1: NO_CLOSE_ABOVE_LEVEL (missing: breakout: a candle closing above the first-candle high; failure: later close below the level) ; M2: NO_CLOSE_ABOVE_LEVEL_A (missing: rally breakout: close above Level A; first red candle of the rally; second breakout above Level B; failure below Level B) |
| 2026-02-14 | 09:40 | BE | WEEKEND_DATE_NOT_AN_EXCHANGE_SESSION |
| 2026-07-24 | 11:00 | BE | M1: signal at 13:45 is after the 13:00 entry cutoff ; M2: signal at 13:05 is after the 13:00 entry cutoff |
| 2026-08-18 | 09:40 | Target | M1: NO_CLOSE_ABOVE_LEVEL (missing: breakout: a candle closing above the first-candle high; failure: later close below the level) ; M2: NO_CLOSE_ABOVE_LEVEL_A (missing: rally breakout: close above Level A; first red candle of the rally; second breakout above Level B; failure below Level B) |

**18. Are all signal timestamps causally valid?** Yes: 1031 signals re-run on candle lists truncated at the failure candle reproduce the same signal and, truncated one candle earlier, produce none; the fill bar is never before the signal time. Failures: 0.

**19. Did independent verification reproduce the results?** Yes - 0 signal/trade mismatches across window A and B in all 9 execution scenarios/variants (`independent_audit.md`). An independent read-only reviewer also reproduced every window-A signal and trade; its findings and what was changed are in `independent_audit.md` section 6.

**20. Were all existing strategies and paper trading preserved?** See `preservation_verification.md` (hash comparison of strategies, ORB V2, broker/core/config code, data, journal and earlier reports before/after; `git diff` of tracked files is empty).

## Source examples (`source_example_reproduction.csv`)

| example | pdf | page | date_stated | status | replay_signal | failure_candle | level_A_diff_vs_source | level_B_diff_vs_source | replay_SL40_exit |
|---|---|---|---|---|---|---|---|---|---|
| M1-ILL | IRF_Inverse_Retest_Failure_Rulebook.pdf | 4 | NONE (undated; not assigned) |  | SIGNAL | 09:30-09:35 | 0.0 |  | TARGET 60.0 |
| M1-E1 | IRF_Inverse_Retest_Failure_Rulebook.pdf | 6 | NONE (undated; not assigned) | NOT_REPRODUCIBLE_UNDATED |  |  |  |  |  |
| M1-E2 | IRF_Inverse_Retest_Failure_Rulebook.pdf | 7 | 2026-11-11 | DATA_UNAVAILABLE (secondary-vendor store ends 2026-11-04; the primary 5paisa store ends 2026-08-31) |  |  |  |  |  |
| M1-E3 | IRF_Inverse_Retest_Failure_Rulebook.pdf | 7 | 2026-11-16 | DATA_UNAVAILABLE (secondary-vendor store ends 2026-11-04; the primary 5paisa store ends 2026-08-31) |  |  |  |  |  |
| M2-ILL | IRF_Method2_First_Red_Candle_Rulebook.pdf | 4 | NONE (undated; not assigned) |  | SIGNAL | 09:50-09:55 | 0.0 | 0.0 | TARGET 60.0 |
| M2-E1 | IRF_Method2_First_Red_Candle_Rulebook.pdf | 5 | NONE (undated; not assigned) | NOT_REPRODUCIBLE_UNDATED |  |  |  |  |  |
| M2-E2 | IRF_Method2_First_Red_Candle_Rulebook.pdf | 6 | 2026-11-12 | DATA_UNAVAILABLE (secondary-vendor store ends 2026-11-04; the primary 5paisa store ends 2026-08-31) |  |  |  |  |  |
| M2-E3 | IRF_Method2_First_Red_Candle_Rulebook.pdf | 6 | 2026-11-06 | DATA_UNAVAILABLE (secondary-vendor store ends 2026-11-04; the primary 5paisa store ends 2026-08-31) |  |  |  |  |  |
| M2-E4 | IRF_Method2_First_Red_Candle_Rulebook.pdf | 7 | 2026-11-03 |  | SIGNAL | 10:00-10:05 | -0.45 | -0.2 | STOP -40.0 |

Level-only candidate search for the two undated screenshots (`undated_example_candidate_search.json`): one secondary-vendor session each within +-1.0 point of the printed level; neither reproduces the printed sequence, so **no date is suggested**.

## Sensitivity of the unresolved readings (Method 2 and combined books; Method 1 rows in `historical_performance_comparison.csv`)

| window | scenario | book | executed_trades | win_rate_pct | profit_factor | gross_points | max_drawdown_points |
|---|---|---|---|---|---|---|---|
| A | SL40_ENTRY_SIGNAL_CLOSE | M2 | 86 | 36.05 | 0.851 | -308.3 | 694.2 |
| A | SL40_ENTRY_SIGNAL_CLOSE | COMBINED | 139 | 39.57 | 0.985 | -48.3 | 502.15 |
| A | SL40_TIE_MINUTE_ORDER | M2 | 86 | 38.37 | 0.9 | -202.45 | 592.9 |
| A | SL40_TIE_MINUTE_ORDER | COMBINED | 139 | 41.73 | 1.032 | 103.2 | 501.2 |
| A | SL40_FORCED_EXIT_1300 | M2 | 86 | 40.7 | 0.855 | -247.1 | 504.05 |
| A | SL40_FORCED_EXIT_1300 | COMBINED | 139 | 43.17 | 1.0 | 1.1 | 437.2 |
| A | SL35_FORCED_EXIT_1300 | M2 | 86 | 39.53 | 0.914 | -136.2 | 398.85 |
| A | SL35_FORCED_EXIT_1300 | COMBINED | 139 | 39.57 | 0.955 | -124.15 | 399.55 |
| A | SL40_CUTOFF_EXCLUSIVE | M2 | 85 | 38.82 | 0.918 | -162.45 | 592.9 |
| A | SL40_CUTOFF_EXCLUSIVE | COMBINED | 138 | 42.03 | 1.045 | 143.2 | 501.2 |
| A | SL40_M2_INVALIDATE_BELOW_A | M2 | 62 | 35.48 | 0.806 | -304.2 | 720.0 |
| A | SL40_M2_INVALIDATE_BELOW_A | COMBINED | 139 | 41.73 | 1.032 | 103.2 | 501.2 |
| B | SL40_ENTRY_SIGNAL_CLOSE | M2 | 268 | 44.4 | 1.126 | 700.75 | 713.7 |
| B | SL40_ENTRY_SIGNAL_CLOSE | COMBINED | 440 | 45.23 | 1.179 | 1639.5 | 603.9 |
| B | SL40_TIE_MINUTE_ORDER | M2 | 268 | 44.4 | 1.123 | 684.9 | 735.95 |
| B | SL40_TIE_MINUTE_ORDER | COMBINED | 440 | 45.23 | 1.173 | 1580.85 | 567.95 |
| B | SL40_FORCED_EXIT_1300 | M2 | 268 | 41.42 | 1.083 | 400.4 | 783.2 |
| B | SL40_FORCED_EXIT_1300 | COMBINED | 440 | 43.18 | 1.144 | 1200.55 | 766.25 |
| B | SL35_FORCED_EXIT_1300 | M2 | 268 | 40.3 | 1.149 | 674.6 | 727.6 |
| B | SL35_FORCED_EXIT_1300 | COMBINED | 440 | 40.68 | 1.121 | 967.3 | 547.65 |
| B | SL40_CUTOFF_EXCLUSIVE | M2 | 267 | 44.19 | 1.112 | 624.9 | 795.95 |
| B | SL40_CUTOFF_EXCLUSIVE | COMBINED | 437 | 45.31 | 1.176 | 1600.85 | 627.95 |
| B | SL40_M2_INVALIDATE_BELOW_A | M2 | 203 | 42.86 | 1.044 | 190.75 | 695.95 |
| B | SL40_M2_INVALIDATE_BELOW_A | COMBINED | 440 | 45.23 | 1.173 | 1580.85 | 567.95 |
| A | SL40_T60__M2_ALT_BREAKOUT_RED | M2 | 86 | 38.37 | 0.9 | -202.45 | 592.9 |
| A | SL40_T60__M2_ALT_BREAKOUT_RED | COMBINED | 139 | 41.73 | 1.032 | 103.2 | 501.2 |
| B | SL40_T60__M2_ALT_BREAKOUT_RED | M2 | 267 | 44.57 | 1.131 | 724.9 | 735.95 |
| B | SL40_T60__M2_ALT_BREAKOUT_RED | COMBINED | 439 | 45.33 | 1.178 | 1620.85 | 567.95 |

Method 2 reading risk quantified (independent review finding): window A has 175 sessions with a rally breakout; in 56 of the 175 where Level B was marked the first red candle itself closed below Level A (window B: 169 of 539). The PDF states no invalidation, so the headline keeps those setups armed; `SL40_M2_INVALIDATE_BELOW_A` shows what the alternative reading does. The red-breakout-candle reading matters little (1 red breakout candles in window A).

## Files
`method1_source_audit.md`, `method2_source_audit.md`, `source_rule_comparison.md`, `rule_authority_registry.csv`, `method1_entry_logic.md`, `method2_entry_logic.md`, `combined_irf_state_machine.md`, `unresolved_author_questions.md`, `method1_signals.csv`, `method2_signals.csv`, `combined_irf_signals.csv`, `method1_backtest.csv`, `method2_backtest.csv`, `combined_irf_backtest.csv`, `daily_verification.csv`, `manual_journal_reconciliation.csv`, `historical_performance_comparison.csv`, `independent_audit.md`, `preservation_verification.md`, `IRF_V3_Complete_Research.xlsx`, `charts_method1/`, `charts_method2/`, `charts_combined/`, `daily/` (one markdown per session, both windows), plus supporting: `overlap_analysis.csv`, `sensitivity_trades.csv`, `monthly_returns_points.csv`, `annual_performance_points.csv`, `cost_slippage_sensitivity.csv`, `manual_journal_match_summary.csv`, `manual_journal_automated_only.csv`, `changed_entry_times_vs_earlier_phases.csv`, `source_example_reproduction.csv`, `undated_example_candidate_search.json`, `audit_results.json`, `source_extracts/` (PDF figures at original resolution).

Charts exist for the 9 source examples and for every executed trade of window A (SL40 drawn; SL35 outcome in the subtitle). Window B (2022-2025) has results, ledgers and daily files but no per-trade charts.

Reproduce: `python scripts/phase70_run.py all && python scripts/phase70_docs.py`.
