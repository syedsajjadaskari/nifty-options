# Phase 3.3 - independent PDR entry-validation audit

**Written for:** the strategy owner. Question: of the 54 PDR trades of the Phase 3.2 baseline, **27** entered LONG on a bullish confirmation candle that closed **below the selected resistance-zone floor**. Is that consistent with the original PDR guide, contradicted by an explicit rule, or unresolved because the guide is qualitative?

**Answer in one paragraph.** The guide (4 pages) requires: a previous-day high/reversal zone, a gap-up open, a return to the zone (wick, body, inside or very close), then *a green candle after the interaction*. It says nothing about where that candle must close, and nothing about price trading through the zone. All 27 entries satisfy every written condition, none is contradicted by an explicit rule, and none is clearly *supported* either: the purpose statement ("watched to see whether it now works as support") and all four dated figures (every confirmation closes above the zone ceiling) point to a hold, but a hold requirement is **not written** - it is UNRESOLVED in the source and only the owner can decide it. Classification: 26 SOURCE_AMBIGUOUS, 1 ZONE_SELECTION_DISPUTED, 0 SOURCE_SUPPORTED, 0 SOURCE_CONTRADICTED, 0 DATA_OR_IMPLEMENTATION_ISSUE, 0 INSUFFICIENT_EVIDENCE.

Nothing was changed: no entry rule, zone selection, stop, target, cutoff, controller, ledger or data file; no portfolio re-run; no P&L is used for any classification or count. The earlier Phase 3.0/3.1/3.2 reports and ledgers are byte-identical to a hash snapshot taken before this phase (`earlier_phase_hashes_before.json`).

## Files (every trade is traceable by Trade ID, e.g. `20260113-1-PDR`, across all of them)

| file | content |
|---|---|
| `pdr_source_rule_verification.md` | what the guide says page by page (EXPLICIT / FIGURE / UNRESOLVED), the four audit questions, the evidence on a zone-hold requirement, the classification rule, the counterfactual table, the source figures against the data |
| `affected_27_trades.csv` | the affected trades: confirmation candle OHLC, zone source candle, zone floor/ceiling, close below the floor, entry, configuration, journal status, source-rule status |
| `pdr_confirmation_calculations.csv` | all 54 PDR trades: gap, interaction candle, retest low and penetration, confirmation geometry, close position, POST_ENTRY context (labelled), alternative zones, cross-checks |
| `pdr_trade_classifications.csv` | classification, confidence, basis, owner clarification needed, secondary zone-selection flag, informational severity band, nearest figure (affected trades only) |
| `manual_journal_comparison.csv` | the Phase 3.1 matching (exact / within 15 minutes) restated per trade next to every journal row of the day |
| `zone_rule_counterfactual_counts.csv` | readings A-D (+ a sensitivity row D2): counts only |
| `source_example_checks.csv` | the guide's dated Examples 1-4 re-run on the data under the drawn, engine, previous-day-high and shelf zones |
| `trade_by_trade_audit.md` | one section per affected trade with its chart |
| `charts/<trade_id>.svg` | per-trade chart: previous session with the zone source candle, ZOOM on the retest and confirmation (close measured against the floor, POST_ENTRY shaded), the whole session with the journal markers |
| `independent_audit.md`, `independent_audit_results.json` | the independent validation (second implementation + second reviewer) |
| `owner_decisions_required.md` | the decisions only the owner can make |

## Reading conventions

Times are IST; a 5-minute candle is labelled by its start (09:15 covers 09:15-09:19, usable at 09:20); the signal is confirmed at the candle end and filled at the open of the next 1-minute bar. Zone = body top .. wick high of the selected previous-session candle ("floor" = body top, "ceiling" = wick high). "Retest low" = the lowest 5-minute low from the interaction (test) candle through the confirmation candle. Everything after the entry is POST_ENTRY and for context only. Confirmation close positions over all 54 trades: above the ceiling 20, inside the zone 7, below the floor 27.

## Reproduce

```
.venv/bin/python scripts/phase33_pdr_audit.py          # CSVs and charts (raw-data reconstruction, imports nothing from the engine)
.venv/bin/python scripts/phase33_independent_audit.py  # second implementation; compares everything
.venv/bin/python scripts/phase33_docs.py               # markdown reports from the CSVs
.venv/bin/python -m pytest -q && .venv/bin/ruff check .
```
