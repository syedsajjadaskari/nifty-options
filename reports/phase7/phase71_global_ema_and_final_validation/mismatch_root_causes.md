# Journal mismatch root causes (configuration B, window A)

Journal integrity recount (independent of earlier reports): `190` data rows (workbook SHA-256 `97a9ad4dfb552061...`), Summary sheet states 189 (discrepancy of 1 unresolved, not corrected), 5 weekend-dated rows that can never match (2025-10-11 ORB, 2026-02-14 IRF, 2026-08-15 ORB, 2026-08-22 ORB, 2026-08-29 ORB), rows by strategy {'IRF': 73, 'PDR': 8, 'ORB': 89, 'RF': 17, 'PDS': 3}. Columns present: sl no, date, entry-time label, strategy, outcome (no direction / price / exit time). No direction, price or exit time exists, so **no verified exact trade match is possible**; every class is a match on date / strategy / time label / outcome label only.

Result for B: strict 71, +time-tolerant 22, date-and-strategy-only 13, manual-only 84 (of which 5 weekend), automated-only 84, wrong-strategy dates 53, outcome-label agreement on strict+tolerant 81 of 93.

## Manual-only rows (non-weekend) by cause
| strategy | category | manual_only_rows |
|---|---|---|
| IRF | NO_SIGNAL_FROM_THE_JOURNAL_STRATEGY | 1 |
| IRF | SIGNAL_ONLY_AFTER_13_00_CUTOFF | 2 |
| IRF | WRONG_STRATEGY_DATE (the automated system traded another strategy that day) | 16 |
| ORB | NO_SIGNAL_FROM_THE_JOURNAL_STRATEGY | 20 |
| ORB | WRONG_STRATEGY_DATE (the automated system traded another strategy that day) | 27 |
| PDR | WRONG_STRATEGY_DATE (the automated system traded another strategy that day) | 2 |
| PDS | WRONG_STRATEGY_DATE (the automated system traded another strategy that day) | 1 |
| RF | NO_SIGNAL_FROM_THE_JOURNAL_STRATEGY | 3 |
| RF | WRONG_STRATEGY_DATE (the automated system traded another strategy that day) | 7 |

## Automated-only trades by cause
| strategy | kind | automated_only_trades |
|---|---|---|
| IRF | JOURNAL_HAS_ANOTHER_STRATEGY_THAT_DAY | 25 |
| IRF | NO_JOURNAL_ENTRY_THAT_DAY | 15 |
| ORB | NO_JOURNAL_ENTRY_THAT_DAY | 1 |
| PDR | JOURNAL_HAS_ANOTHER_STRATEGY_THAT_DAY | 19 |
| PDR | NO_JOURNAL_ENTRY_THAT_DAY | 6 |
| PDS | JOURNAL_HAS_ANOTHER_STRATEGY_THAT_DAY | 13 |
| PDS | NO_JOURNAL_ENTRY_THAT_DAY | 3 |
| RF | NO_JOURNAL_ENTRY_THAT_DAY | 2 |

## Reading the causes
* ORB dominates the manual-only rows: the journal's ORB entries carry the label 09:15 on 89 rows; ORB V2 (provisional conventions, wrong-side-wick rule, gap limit) emits only 39 trades. Phase 6.5 audited the ORB-vs-IRF disputes (0 implementation defects).
* 'Wrong-strategy dates' mean the automated first-valid-signal controller took a different strategy than the manual trader on the same date; the journal gives no way to tell which was 'right'.
* These disputes are NOT resolved by IRF V3, the EMA readings or the PDR/PDS variants in any consistent way: strict matches (window A) B 71, D 68, E 49, F 4, K 49, L 73, G1-H 71/70/70/67, I1/I2 72/72. No rule was changed to fit the journal.
