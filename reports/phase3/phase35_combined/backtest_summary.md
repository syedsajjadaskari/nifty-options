# Phase 3.5 - complete five-strategy NIFTY 50 backtest (IRF, ORB, PDR revised, PDS, RF)

**Written for:** the strategy owner, for manual review. All P&L is **synthetic index-point P&L x quantity** (the NIFTY 50 index is not tradable); "illustrative net" deducts Rs 500 per trade and 0.5 index point of adverse slippage on every fill (the Phase 3.0 headline assumption). Nothing was tuned, nothing was traded live, no broker API was called, no data file was written.

## How this run was produced

One run of the **existing** Phase 3.0 shared portfolio controller over the original one-minute NIFTY 50 candles (2025-09-01 .. 2026-08-31), reported with the **existing** Phase 3.2 explainable-backtest framework. The only change of input is the PDR engine: the slot of the legacy `PDRStrategy` now holds the Phase 3.4 `PDRRevisedStrategy` (`--pdr-engine revised`). IRF, ORB, PDS and RF are constructed exactly as in Phase 3.0; stops, targets, sizing, cutoff, forced exit and the controller are untouched. The five strategies were **not** back-tested separately and added: one controller decides, in time order, which signal becomes a trade.

**Exact command to rerun (macOS terminal):**

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase35_run.py --pdr-engine revised
```

(`--pdr-engine legacy` re-runs the Phase 3.0 baseline into `reports/phase3/phase35_legacy_check/` and must reproduce the frozen Phase 3.0 ledger with zero field differences - it does.)

## Revised PDR - what is and is not approved

* **Author statements (AUTHOR_APPROVED):** the previous-day high is considered and a zone is drawn; one good green body OR lower-price rejection OR hammer candle is required; the confirmation candle should close above the zone.
* **Provisional research assumptions (NOT approved by the strategy author):** the numeric thresholds of the three patterns (green body 60% / upper wick 20%; rejection 2x wick, close in the top 30%; hammer 2x wick, upper wick 10%, body in the upper 60%), the zone floor (body top of the day-high candle), reading 'above' as **strictly above the zone ceiling**, and the requirement that the session **open above the zone** (legacy PDR-011, kept as a labelled research assumption).
* Candidate A (day-high anchored zone) is used; candidate B (multiple-high zone) gives the identical signals by construction. No signal is VERIFIED.

## Headline result (247 evaluable sessions)

| item | value |
|---|---|
| Executed trades | 198 (188 first trades, 10 second trades, 188 days with a trade; 59 days without a trade, of which 2 are same-minute conflicts) |
| Trades by strategy | IRF 111, ORB 41, PDR 25, PDS 11, RF 10 |
| Gross P&L | Rs 204,692 |
| Illustrative net P&L | Rs 28,472 |
| Win rate (gross) / profit factor (gross) | 58.59% / 1.1872 |
| Average trade (gross) / max drawdown (gross) / longest losing streak | Rs 1,034 / Rs 178,016 / 5 |
| Outcomes | Target 2: 62; Target 1 then post-T1 stop: 54; initial full stop: 82; provisional forced exit: 0; unresolved: 0 |
| Manual journal (190 rows) | 89 matched (68 exact + 21 time-shifted), 101 unmatched; 109 automated trades have no journal counterpart |

### By strategy

| strategy | trades (1st / 2nd) | gross Rs | illustrative net Rs | win % | profit factor | Target 2 / T1+stop / full stop | share of gross |
|---|---|---|---|---|---|---|---|
| IRF | 111 (111 / 0) | -20,962 | -119,752 | 54.95 | 0.9693 | 32 / 29 / 50 | -10.2% |
| ORB | 41 (41 / 0) | 138,470 | 101,980 | 65.85 | 1.8385 | 15 / 12 / 14 | 67.6% |
| PDR | 25 (19 / 6) | 10,920 | -11,330 | 56.0 | 1.0727 | 7 / 7 / 11 | 5.3% |
| PDS | 11 (7 / 4) | 80,554 | 70,764 | 72.73 | 2.9587 | 6 / 2 / 3 | 39.4% |
| RF | 10 (10 / 0) | -4,290 | -13,190 | 60.0 | 0.9214 | 2 / 4 / 4 | -2.1% |

### Did all five engines feed the shared controller?

| strategy | engine | confirmed signals | valid signals | within 13:00 | executed trades | ignored | rejected by controller |
|---|---|---|---|---|---|---|---|
| IRF | IRFStrategy (unchanged) | 874 | 865 | 557 | 111 | 491 | 265 |
| ORB | ORBStrategy (unchanged) | 53 | 53 | 53 | 41 | 0 | 0 |
| PDR | PDRRevisedStrategy (Phase 3.4, candidate A, provisional thresholds) | 81 | 81 | 58 | 25 | 51 | 5 |
| PDS | PDSStrategy (unchanged) | 57 | 56 | 35 | 11 | 38 | 8 |
| RF | RFStrategy (unchanged) | 12 | 12 | 10 | 10 | 1 | 1 |

Yes: every engine produced confirmed signals and every engine was traded at least once.

## Comparison with Phase 3.0 (baseline: legacy PDR)

| strategy | trades 3.0 -> 3.5 | share of trades 3.0 -> 3.5 | gross Rs 3.0 -> 3.5 (delta) | illustrative net Rs 3.0 -> 3.5 (delta) |
|---|---|---|---|---|
| IRF | 102 -> 111 (+9) | 47.9% -> 56.1% | -56,062 -> -20,962 (+35,100) | -146,842 -> -119,752 (+27,090) |
| ORB | 41 -> 41 (+0) | 19.2% -> 20.7% | 138,470 -> 138,470 (+0) | 101,980 -> 101,980 (+0) |
| PDR | 54 -> 25 (-29) | 25.4% -> 12.6% | 29,074 -> 10,920 (-18,154) | -18,986 -> -11,330 (+7,656) |
| PDS | 11 -> 11 (+0) | 5.2% -> 5.6% | 80,554 -> 80,554 (+0) | 70,764 -> 70,764 (+0) |
| RF | 5 -> 10 (+5) | 2.3% -> 5.1% | -19,890 -> -4,290 (+15,600) | -24,340 -> -13,190 (+11,150) |
| ALL | 213 -> 198 (-15) | 100.0% -> 100.0% | 172,146 -> 204,692 (+32,546) | -17,424 -> 28,472 (+45,896) |

| manual journal (190 rows) | Phase 3.0 | Phase 3.5 |
|---|---|---|
| matched | 84 | 89 |
| ... exact | 67 | 68 |
| ... time-shifted (<= 15 min) | 17 | 21 |
| unmatched manual trades | 106 | 101 |
| automated trades with no journal counterpart | 129 | 109 |

**What changed and why.** 49 of 247 sessions have a different trade set (47 involve a PDR trade, 18 also change a trade of another strategy through the controller). The revised PDR produced 81 confirmed signals (the legacy engine: 383), 23 of them timed after 13:00; 25 became trades (54 before). The rest were ignored by the controller because the day was already finished or a position was active (DAY_FINISHED 36, POSITION_ACTIVE 15), or were explicitly rejected by the 13:00 cutoff (5; the other signals after 13:00 were already ignored for the first reason). Because a PDR trade no longer occupies the day as often, later signals of other strategies are taken: IRF +9 net (11 trades added, 2 removed), RF +5 net (5 trades added, 0 removed). That downstream effect is why the controller must be re-run rather than the PDR ledger edited. ORB and PDS trades are identical to Phase 3.0 (same day, entry, price, outcome and P&L).

Journal agreement: 8 journal rows became matched and 3 lost their match. Gained: row 7 (RF 2025-09-08), row 11 (RF 2025-09-15), row 42 (RF 2025-11-18), row 54 (IRF 2025-12-10), row 58 (IRF 2025-12-17), row 91 (RF 2026-02-18), row 105 (IRF 2026-03-17), row 152 (PDR 2026-06-12). Lost: row 44 (PDR 2025-11-20), row 147 (PDR 2026-06-05), row 200 (IRF 2026-08-26). Most gains are IRF/RF journal rows that the legacy PDR trade had pre-empted ('rejected by the portfolio controller' in Phase 3.0); **PDR itself matches the journal no better** (see `manual_pdr_rows_phase30_vs_phase35.csv`).

Largest day-level changes (gross Rs): 2025-12-17 +44,265; 2026-07-31 +32,565; 2025-11-18 +30,615 (better); 2026-03-17 -32,565; 2026-05-07 -31,395; 2026-08-26 -30,615 (worse). The net change over all changed days is Rs +32,546 gross. This is a description of the difference, **not** a reason to prefer either configuration: no parameter was chosen by profit, and the PDR thresholds are provisional.

Full tables: `comparison_vs_phase30.csv`, `comparison_vs_phase30_by_day.csv` (one row per changed session, with the removed / added trades and tags), `manual_pdr_rows_phase30_vs_phase35.csv`.

## Where to look (per executed trade)

| what you asked to see | where |
|---|---|
| Date, strategy and method, why it was entered | `all_trades_detailed.csv` (`setup_explanation`, `selection_explanation`), the trade's section in `daily/YYYY-MM/YYYY-MM-DD.md` |
| Each condition with its numerical value, rule, status | `trade_entry_conditions.csv` (one row per condition), section C of the daily journal |
| Candle OHLC, EMA, trend, support / resistance / zone values | daily journal 'Candle and indicator calculations' table; `candle_analysis.csv` |
| Entry timestamp and price, initial stop, targets | `all_trades_detailed.csv` (`fill_timestamp`, `entry_price`, `initial_stop`, `target_1`, `target_2`, `post_t1_stop`); journal section 4 |
| Target 1 exit, remaining position's final exit, reason for each exit | `trade_exits_detailed.csv` (one row per leg, with the raw 1-minute bar); `all_trades_detailed.csv` (`exit_narrative`) |
| Gross and illustrative net P&L | `all_trades_detailed.csv`; `strategy_performance.csv`; the workbook dashboard |
| Manual journal match and the explanation of every mismatch | `manual_journal_comparison.csv` (190 journal rows + every extra automated trade), `manual_verification_issues.csv` |
| Every evaluable session, including no-trade days | `daily/` (247 journals), `daily_summary.csv` |
| Charts on the real candles | `charts/` (198 SVG files, one per trade) |
| Everything in one workbook | `NIFTY_Daily_Trade_Verification.xlsx` (review columns are blank for the owner) |

## Independent verification

* `scripts/phase35_independent_audit.py` re-implements from the raw parquet files and the delivered CSVs only (it imports nothing from `src/`): 32 checks, **ALL PASS** - entry prices, every exit leg re-walked bar by bar, P&L (gross and illustrative net), stops and targets, candles / EMA / geometry, the revised PDR signal stream (81 / 81), the four unchanged engines' signals versus the Phase 3.2 export (996 / 996), the controller rules, the performance and comparison tables, the manual-journal matching (89 matches), and a hash proof that data, earlier reports, other engines and the controller are unchanged. Details: `independent_audit.md`.
* Recomputation mismatches inside the trade explanations: 0. Failed entry conditions on executed trades: 0.

## Limits and open points

* The PDR pattern thresholds and the open-above-zone requirement are provisional; with the open-above-zone requirement dropped the PDR stream would be roughly twice as large (Phase 3.4 sensitivity) - this run does not use that.
* The forced exit at the 15:14 minute open is a provisional implementer assumption (as in Phase 3.0). RF's Target 2 (60) is a research assumption. PDR / PDS Target 2 is 70 (the guide's value; the performance report's winners suggest 60 - a recorded source conflict).
* Simultaneous signals from different strategies in the same minute are not resolved by any approved tie-break: the day is marked unresolved and nothing is traded (preserved from Phase 3.0).
* The journal records no entry or exit price, so matching uses date, strategy and the candle start within 15 minutes; P&L is never used to match.
* Not done, by design: no parameter tuning, no live trading, no forward testing, no Phase 3.6.
