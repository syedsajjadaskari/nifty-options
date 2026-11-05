# Phase 3.6 - author-corrected PDR (body-based zone) in the complete five-strategy NIFTY 50 backtest

**Written for:** the strategy owner, for manual review. All P&L is **synthetic index-point P&L x quantity** (the NIFTY 50 index is not tradable); "illustrative net" deducts Rs 500 per trade and 0.5 index point of adverse slippage on every fill (the Phase 3.0 headline assumption, kept for comparability). Nothing was tuned or selected by profit, nothing was traded live, no broker API was called, no data file or earlier report was changed.

## How this run was produced

One run of the **existing** Phase 3.0 shared portfolio controller over the original one-minute NIFTY 50 candles (2025-09-01 .. 2026-08-31), reported with the **existing** Phase 3.2 framework. The only change of input is the PDR engine: the new `PDRBodyStrategy` (`src/nifty_trading/strategies/pdr_body.py`, version PDR_BODY_PHASE36). IRF, ORB, PDS and RF are constructed exactly as before; stops, targets, sizing, cutoff, forced exit and the controller are untouched. The Phase 3.5 engine (`--pdr-engine revised`, wick-high ceiling) and its results are preserved unchanged.

**Exact command to rerun (macOS terminal):**

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase36_run.py
```

Equivalent: `python scripts/phase35_run.py --pdr-engine body-based`. (`--pdr-engine revised` still means the Phase 3.5 configuration.)

## What the author's corrections changed in PDR

* **Resistance = the previous day's highest BODY high** (`max(open, close)` of the 5-minute candles); wick-only prices are ignored (Phase 3.5 used the highest wick as the ceiling).
* **Open strictly above the zone ceiling** (equal or inside rejects the setup) - now an author-approved rule, no longer a legacy proposal.
* **One of three confirmation candles** (good green body, lower-price rejection, hammer) that **closes above the zone**; the author says fixed percentage / wick-size thresholds are not required.
* **Provisional, NOT author-approved:** the numeric thresholds that make the three patterns programmable (the Phase 3.5 profile RESEARCH_DEFAULT is carried over for comparability), the zone's lower boundary (body low of the anchor candle for candidate A, hull of the member bodies for candidate B), the multiple-body-high cluster numbers, the zero-height policy and the wait policy. No signal is VERIFIED. See `pdr_body_zone_rule_audit.md` and `pdr_pattern_classification.md`.

## Headline result (247 evaluable sessions)

| item | value |
|---|---|
| Executed trades | 196 (188 first trades, 8 second trades; 188 days with a trade, 59 without; 2 same-minute conflict days) |
| Trades by strategy | IRF 109, ORB 41, PDR 25, PDS 11, RF 10 |
| Gross P&L | Rs 297,765 |
| Illustrative net P&L | Rs 123,325 |
| Win rate / profit factor (gross) | 59.69% / 1.2839 |
| Average trade / max drawdown / longest losing streak (gross) | Rs 1,519 / Rs 130,650 / 4 |
| Outcomes | Target 2: 65; Target 1 then post-T1 stop: 52; initial full stop: 78; provisional forced exit (15:14 open): 1; unresolved: 0 |
| Manual journal (190 rows) | 88 matched (66 exact + 22 time-shifted); 102 unmatched; 108 automated trades without a journal counterpart |

### By strategy

| strategy | trades (1st / 2nd) | gross Rs | illustrative net Rs | win % | profit factor | Target 2 / T1+stop / full stop | share of gross |
|---|---|---|---|---|---|---|---|
| IRF | 109 (109 / 0) | -11,408 | -108,418 | 55.05 | 0.9829 | 32 / 28 / 49 | -3.8% |
| ORB | 41 (41 / 0) | 138,470 | 101,980 | 65.85 | 1.8385 | 15 / 12 / 14 | 46.5% |
| PDR | 25 (21 / 4) | 94,438 | 72,188 | 64.0 | 1.7917 | 10 / 6 / 8 | 31.7% |
| PDS | 11 (7 / 4) | 80,554 | 70,764 | 72.73 | 2.9587 | 6 / 2 / 3 | 27.1% |
| RF | 10 (10 / 0) | -4,290 | -13,190 | 60.0 | 0.9214 | 2 / 4 / 4 | -1.4% |

### Did all five engines feed the shared controller?

| strategy | engine | confirmed signals | within 13:00 | executed trades | ignored | rejected by controller |
|---|---|---|---|---|---|---|
| IRF | IRFStrategy (unchanged) | 874 | 557 | 109 | 503 | 256 |
| ORB | ORBStrategy (unchanged) | 53 | 53 | 41 | 0 | 0 |
| PDR | PDRBodyStrategy (Phase 3.6, body-based zone, open strictly above, provisional thresholds) | 87 | 62 | 25 | 57 | 5 |
| PDS | PDSStrategy (unchanged) | 57 | 35 | 11 | 38 | 8 |
| RF | RFStrategy (unchanged) | 12 | 10 | 10 | 1 | 1 |

## Phase 3.0 vs Phase 3.5 vs Phase 3.6

| metric | Phase 3.0 (legacy PDR) | Phase 3.5 (wick-ceiling PDR) | Phase 3.6 (body-based PDR) |
|---|---|---|---|
| Total trades | 213 | 198 | 196 |
| IRF | 102 | 111 | 109 |
| ORB | 41 | 41 | 41 |
| PDR | 54 | 25 | 25 |
| PDS | 11 | 11 | 11 |
| RF | 5 | 10 | 10 |
| Gross P&L (Rs) | 172,146 | 204,692 | 297,765 |
| Illustrative net (Rs) | -17,424 | 28,472 | 123,325 |
| Journal matches (of 190) | 84 | 89 | 88 |
| ... exact / time-shifted | 67 / 17 | 68 / 21 | 66 / 22 |

| strategy | gross Rs 3.0 | gross Rs 3.5 | gross Rs 3.6 | net Rs 3.0 | net Rs 3.5 | net Rs 3.6 |
|---|---|---|---|---|---|---|
| IRF | -56,062 | -20,962 | -11,408 | -146,842 | -119,752 | -108,418 |
| ORB | 138,470 | 138,470 | 138,470 | 101,980 | 101,980 | 101,980 |
| PDR | 29,074 | 10,920 | 94,438 | -18,986 | -11,330 | 72,188 |
| PDS | 80,554 | 80,554 | 80,554 | 70,764 | 70,764 | 70,764 |
| RF | -19,890 | -4,290 | -4,290 | -24,340 | -13,190 | -13,190 |
| ALL | 172,146 | 204,692 | 297,765 | -17,424 | 28,472 | 123,325 |

**Do not read the higher Phase 3.6 P&L as proof of a better strategy.** The three runs differ in one PDR convention at a time under provisional thresholds, on one historical year, with PDR trades of only 25 (gross Rs 94,438, profit factor 1.7917); a difference of a few signals moves the result by tens of thousands of rupees. No setting was chosen by profit or by journal agreement.

### Monthly P&L (gross Rs)

| month | Phase 3.0 | Phase 3.5 | Phase 3.6 | net Phase 3.6 |
|---|---|---|---|---|
| 2025-09 | 6,737 | 36,182 | 36,182 | 21,052 |
| 2025-10 | 16,770 | 12,675 | 27,495 | 12,365 |
| 2025-11 | 22,669 | 48,574 | 16,010 | -1,790 |
| 2025-12 | 106,070 | 108,810 | 141,375 | 124,465 |
| 2026-01 | -48,360 | -7,410 | -7,410 | -20,760 |
| 2026-02 | -7,215 | -15,405 | -15,405 | -27,865 |
| 2026-03 | 31,220 | -1,346 | 44,870 | 35,080 |
| 2026-04 | -68,835 | -68,835 | -72,930 | -89,840 |
| 2026-05 | -29,640 | -38,610 | -24,960 | -39,200 |
| 2026-06 | 17,745 | 39,780 | 58,695 | 45,345 |
| 2026-07 | 103,145 | 117,965 | 117,965 | 99,275 |
| 2026-08 | 21,840 | -27,690 | -24,122 | -34,802 |

## PDR: signals, trades and what changed

| PDR stream | raw confirmed signals | days with a signal | executed trades |
|---|---|---|---|
| Phase 3.0 legacy engine (reversal-swing zone) | 383 | 61 | 54 |
| Phase 3.5 wick-ceiling engine | 81 | 31 | 25 |
| Phase 3.6 body-based engine | 87 | 33 | 25 |

Against Phase 3.5: 63 signals are common (the same candle qualifies; the ceiling is lower by the ignored wick), 18 are removed and 24 are new (NEWLY_VALID_CLOSE_ABOVE_BODY_CEILING 16, NEWLY_VALID_OPEN_ABOVE_BODY_ZONE 7, NEWLY_VALID_SEQUENCE 1, REMOVED_BY_BODY_ZONE_NO_ARMED_TEST 16, REMOVED_BY_BODY_ZONE_PATTERN 2). Of the 87 signals 25 are timed after 13:00 and 25 became trades; the rest were ignored by the controller (DAY_FINISHED 41, POSITION_ACTIVE 16) or rejected by the cutoff. PDR trade outcomes: TARGET 10, INITIAL_FULL_STOP 8, T1_THEN_BUFFER_STOP 6, FORCED_EXIT 1. The body-based open-above-zone test is passed on 68 sessions (the wick-ceiling test: 61); the status changes on 7 sessions. Zones with zero height: 0.

**New or removed days.** PDR signal days: 5 new (2025-10-07, 2025-12-31, 2026-03-17, 2026-05-19, 2026-06-05), 3 removed (2025-11-20, 2026-01-22, 2026-04-16), 14 with a changed signal set. Trading days (any strategy): 1 new, 1 removed relative to Phase 3.5; 12 sessions have a different trade set (see `comparison_vs_phase35_by_day.csv`, one row per session with the removed / added trades), 51 relative to Phase 3.0 (`comparison_vs_phase30_by_day.csv`). Per-session zone data for every session: `pdr_daily_zone_comparison.csv`; every signal with its tag and reason: `old_vs_new_pdr_signals.csv`.

Journal agreement against Phase 3.5: 1 rows gained a match, 2 lost one. Gained: row 22 (PDR 2025-10-07). Lost: row 105 (IRF 2026-03-17), row 152 (PDR 2026-06-12). The PDR journal rows under all three runs are in `manual_pdr_rows_three_phases.csv`.

Largest day-level changes vs Phase 3.5 (gross Rs): 2025-12-31 +32,565; 2026-03-17 +32,565; 2025-10-07 +14,820 (higher); 2025-11-20 -32,565; 2026-04-16 -4,095; 2025-12-01 +0 (lower). This describes the difference; it is not a reason to prefer a configuration.

## What the PDR P&L swing rests on (read this before the P&L)

* **Trade level.** 21 PDR trade ids are common to Phase 3.5 and 3.6 (5 of them enter on a different candle and end differently); 4 Phase 3.5 trades disappear (gross Rs 13,455) and 4 appear (gross Rs 60,840). The change of PDR gross (10,920 -> 94,438) is the sum of about a dozen trades, not a systematic shift.
* **Thin margins.** The smallest opens above the ceiling are 1.50, 1.75, 2.85 points (`pdr_trade_open_margins.csv`); the new winners are among them. The engine uses the first 1-minute open; the vendor daily open differs by more than 0.05 point on 170 sessions and would flip the open-above-zone test on 5 (2025-12-31, 2026-01-05, 2026-05-04, 2026-06-09, 2026-08-05).
* **Zones price had already left.** 35 of 87 signals and 14 of 25 executed PDR trades occur after a candle CLOSED BELOW the zone floor between the test and the confirmation (`pdr_signal_zone_state.csv`; the wait policy is a research assumption, rule PDR-B07, flagged in every trade's explanation).
* **Patterns.** The active default thresholds pass 0 of the author's 4 dated entry candles as a pattern (`pdr_source_chart_validation.md`); the pattern numbers are provisional.
* **The zone floor and the gap-up condition do not change any signal** (`pdr_body_zone_rule_audit.md` part 5).

## Where to look (per executed trade; Trade ID = `YYYYMMDD-n-STRATEGY`)

| what you asked to see | where |
|---|---|
| Why entered: strategy, method, conditions with numbers, OHLC, EMA / trend / zones, body-high calculation, selection against competitors | `all_trades_detailed.csv` (`setup_explanation`, `selection_explanation`); `entry_condition_details.csv` (one row per condition); the trade's section in `daily/YYYY-MM/YYYY-MM-DD.md`; `candle_analysis.csv` |
| Entry timestamp and price, stop, targets, post-T1 stop | `all_trades_detailed.csv`; section 4 of the daily journal |
| Why exited: T1, T2, stop, post-T1 stop, forced exit; exact fill time and price; source 1-minute bar; leg P&L | `exit_details.csv` (one row per leg); `all_trades_detailed.csv` (`exit_narrative`) |
| Manual journal comparison and the reason for each mismatch | `manual_journal_comparison.csv` (190 rows + every extra automated trade); `manual_pdr_rows_three_phases.csv` |
| Every evaluable session, including no-trade days | `daily/` (247 journals), `daily_summary.csv` |
| Charts on the real candles | `charts/` (196 SVG files, one per trade) |
| Everything in one workbook | `NIFTY_Daily_Trade_Verification.xlsx` |

## Independent verification

* `scripts/phase36_independent_audit.py` re-implements from the raw parquet files and the delivered CSVs only: 37 checks, **ALL PASS** (details and the fresh-reviewer findings: `independent_audit.md`).
* Recomputation mismatches inside the trade explanations: 0; failed entry conditions on executed trades: 0.
* `pytest`: 589 passed, 1 skipped (the superseded Phase 3.4 freeze test); `ruff`: All checks passed.

## Limits and open points

* The pattern thresholds, the zone lower boundary and the multiple-body-high numbers are provisional. With the example-read thresholds the body-based stream would have 113 signals instead of 87 (44 lenient-only candles are preserved as AMBIGUOUS, never traded); this run does not use them.
* Allowing any open (not the author's rule) would give 164 signals - not used.
* The guide's own drawn boxes for Examples 1, 2 and 4 follow the wick high, which contradicts the later 'wick should be ignored' clarification (Example 3 follows the body); the owner must confirm which governs (`pdr_source_chart_validation.md`).
* The forced exit at the 15:14 minute open is a provisional implementer assumption (as in Phase 3.0); RF's Target 2 of 60 is a research assumption; PDR / PDS Target 2 is 70 (the guide) while the performance report's winners suggest 60 - a recorded source conflict.
* Simultaneous signals of different strategies in the same minute have no approved tie-break: the day is marked unresolved and nothing is traded (preserved).
* Not done, by design: no tuning, no live trading, no forward testing, no commit or push, no Phase 3.7.
