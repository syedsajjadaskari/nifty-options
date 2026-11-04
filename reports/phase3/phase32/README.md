# Phase 3.2 - explainable backtest, per-trade journals and daily verification

**Written for:** the strategy owner, who will check the system one trading day at a time against the candles and the manual journal.
Start with `backtest_summary.md`, then open the workbook `NIFTY_Daily_Trade_Verification.xlsx` (sheet *Daily Review Checklist*) or any daily journal.

Nothing here changes a rule, parameter, stop, target, cutoff or the selection controller. The Phase 3.0 baseline is re-run unchanged (its ledger is reproduced field by field) and
all earlier reports are untouched. P&L is **synthetic NIFTY 50 index-point P&L x quantity** (the index is not tradable); "illustrative net" = Rs 500 per trade + 0.5 index point adverse on every fill.
Nothing is marked as reviewed or approved: every owner-review field is blank.

## Files

| file | what it holds |
|---|---|
| `backtest_summary.md` | headline results, re-verification of the Phase 3.1 figures, explanation completeness, journal agreement, observations, limits |
| `independent_audit.md`, `independent_audit_results.json` | the independent audit (re-implemented candles, EMA, exits, P&L, zones; workbook = CSV) and the QA review |
| `daily/YYYY-MM/YYYY-MM-DD.md` | one journal per evaluable session (247), including no-trade days: overview, signal timeline, trade journals, manual comparison, conclusion |
| `charts/<trade_id>.svg` | one chart per executed trade (213) on the real 5-minute candles with EMA, levels/zones, entry, stop, targets, post-T1 stop, both leg exits and the manual entry marker |
| `NIFTY_Daily_Trade_Verification.xlsx` | 13 required sheets + *Verification Issues* (frozen headers, filters, PASS/FAIL colours, links, blank review columns) |
| `daily_summary.csv` | one row per session |
| `automated_trades_detailed.csv` | one row per executed trade: identity, entry (with source bar), setup and selection explanations, stops/targets, exit narrative, P&L, manual match |
| `trade_entry_conditions.csv` | every entry condition of every trade: rule id, source, calculation, observed values, requirement, PASS/FAIL/NOT_APPLICABLE/UNRESOLVED, rule status, numeric-definition status, availability time, why it matters |
| `trade_exits_detailed.csv` | both legs of every trade: quantity, exit time/price, reason, trigger evidence, source 1-minute bar (OHLC), gross P&L, slippage, flags |
| `candle_analysis.csv` | every candle used by a decision: OHLC, range, body %, wick %, direction, EMA, strong/pin/small classification, role, availability time |
| `all_strategy_signals.csv` | every CONFIRMED signal of all five engines, in time order, with the controller's decision and the engine's rule-id lists and levels |
| `ignored_signals.csv`, `rejected_signals.csv` | signals ignored by the controller; controller rejections and conflicts; engine setups that failed or never completed (with failed rule ids) |
| `manual_vs_automated.csv`, `manual_journal_normalized.csv`, `manual_verification_issues.csv` | the 190 journal rows and the 129 extra automated trades with the match class and reason; the normalised journal; every item needing the owner's eye |
| `configuration_snapshot.json`, `data_provenance.json` | active parameters and approval status; code/data hashes, calendar, timezone, cost assumptions, Phase 3.0 ledger check |

## Glossary

* **Rule status** (`rule_status`): the registry's classification of the *rule* - `SOURCE_VERIFIED` (the PDF states it, explicitly or qualitatively), `USER_APPROVED` (owner decision, e.g. portfolio rules, stops), `PROPOSED_FOR_REVIEW`, `CONFLICTING`, `UNRESOLVED`. Read it with **`definition_status`** (`EXPLICIT_IN_SOURCE`, or `QUALITATIVE_SOURCE_NUMERIC_DEFINITION_PROPOSED_FOR_REVIEW` = the guide is qualitative and the numbers used are proposals) and **`source_fidelity`** (how the engine's reading compares with the wording: `ENGINE_RELAXES_SOURCE`, `ENGINE_STRICTER_THAN_SOURCE`, `PIN_BAR_ROUTE_USED`, `ZONE_IS_NOT_THE_DAY_HIGH`, `EMA_ONLY_PROXY`, `SOURCE_RULE_WOULD_SELECT_40`, ...; blank = not assessed).
* **Trend modes / zone methods:** `EMA_PREV_SESSION_CLOSE` = research variant A (the previous session's last 5-minute close versus its EMA(200), nothing else); `B_SWING_HIGH_REVERSAL` = the PDR zone is the latest confirmed swing high (2 candles each side) that has a red candle among the peak and the next two; `A_LOWEST_LOW` = the PDS zone is the previous session's lowest-low candle; `FIRST_PUSH_TOP` / `SWING_K1` = IRF resistance / support are 3-candle fractal extremes; `DAILY_VENDOR` = the previous close is the official daily close.
* **Day states:** `READY_FOR_FIRST_TRADE`, `FIRST_TRADE_ACTIVE`, `SECOND_TRADE_ELIGIBLE` (the first trade hit its original full stop; a newly confirmed PDR/PDS may still trade), `SECOND_TRADE_ACTIVE`, `DAY_FINISHED`, `UNRESOLVED_EXECUTION` (a same-minute collision between strategies, or an unresolved exit: nothing more is traded). `DAY-T2-001` = after Target 2 the day is finished; `DAY-BUF-001` = after T1 and the post-T1 stop the day is finished; `DAY-SL-001` = the original full stop allows one more PDR/PDS trade.
* **Outcomes:** `TARGET` (T1 then T2), `T1_THEN_BUFFER_STOP` (T1 booked, the remaining lots stopped at entry -/+ 6), `INITIAL_FULL_STOP` (both legs at the original stop before T1).
* **Win rate** counts every trade with a positive gross P&L, so a T1-then-post-T1-stop trade (+Rs 4,095 in most cases) counts as a win.

## Reading one trade

Trade ID = `YYYYMMDD-<trade no of the day>-<STRATEGY>`, e.g. `20250903-2-PDR`; the same ID links every sheet, CSV, chart and daily journal.
Times are IST. A 5-minute candle is labelled by its **start** (09:15 = rows 09:15-09:19, usable at 09:20); a journal "Entry Time" is a candle start; the automated fill is the **open of the 1-minute bar that starts when the signal candle ends**.
Each condition has a rule status (`SOURCE_VERIFIED`, `USER_APPROVED`, `PROPOSED_FOR_REVIEW`, `CONFLICTING`) and, separately, a numeric-definition status: where the guide is qualitative ("strong body", "near the zone") the numbers used are research proposals and are labelled so.
`UNRESOLVED` marks (a) a rule the source leaves open and (b) a condition the engine does **not** test (for example whether a PDR zone held) - never a hidden pass.

## How the explanations were produced (and what that means)

The engines were **not modified** and no tracing code was added to them. Each condition is recomputed with the engines' own definition functions and active configuration and compared with the values the engine stored on its signal record
(levels, extension/red/support indices, state trace, rule ids); a disagreement would appear as a `FAIL` and as an `EXPLANATION_RECOMPUTATION_MISMATCH` issue (there are none). The unchanged Phase 3.0 ledger shows that nothing in execution changed.
Numeric per-condition evidence exists for the 213 executed trades; for the other signals the engine's rule-id lists, levels and state traces are exported.

## Reproduce

```
.venv/bin/python scripts/phase32_build.py     # CSVs, daily journals, charts, workbook, JSON (about half a minute)
.venv/bin/python scripts/phase32_docs.py      # backtest_summary.md
.venv/bin/python scripts/phase32_audit.py     # independent audit (imports nothing from nifty_trading)
.venv/bin/python -m pytest -q && .venv/bin/ruff check .
```
