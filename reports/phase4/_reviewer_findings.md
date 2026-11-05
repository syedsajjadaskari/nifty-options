## Fresh independent reviewer

A reviewer with no prior context on this phase was given the master prompt, the repository (read-only) and the generated reports, and asked to attack the work: re-walk trades from raw minutes, check the freeze, check the claims in the documents against the CSV files, and look for look-ahead, silent merging and overstated conclusions.

**Verdict (first pass):** the numbers were reproduced; the *words* and a few guards needed correction. Re-walking all 1,726 trades from the processed minute files gave **zero mismatches** in entry, exit, outcome and P&L. The reviewer found no look-ahead, no vendor mixing inside a run and no change to a strategy file. The findings below concern disclosure, guard strength and wording. Every one was acted on; none was dismissed.

| # | Finding | Disposition |
|---|---|---|
| F1 | Fixed-point stops/targets are not scaled to the index level (index ~2.3x lower in 2018-19), so years are not like-for-like | New section 11 in `robustness_report.md` (scale table: stop as % of index, forced-exit share, holding time); caveat added to the 2018, 2019 and readiness text. Nothing rescaled (that would be a rule change) |
| F2 | The statement "secondary first open equals the 5paisa daily open in 99% of sessions" was true only for 2022-25 | Replaced by a table for every window incl. Window A; the relationship reverses in 2019; which convention matches the exchange is stated as not established |
| F3 | Coverage text quoted whole-window numbers under per-slice rows | Coverage is now per period row (sessions of that slice only) |
| F4 | `DATA_VALIDATED` could be read as "strategy validated" | Defined in README, three-year summary and workbook README: data quality gate only |
| F5 | Run guard checked fewer files than documented | `verify_freeze()` checks every file hashed in the freeze and every parameter; tamper tests added for framework files |
| F6 | Strategy-share column misleading when the window gross is not positive | Shown as "n/m" |
| F7 | Data-quality diagnostic counted dropped sessions instead of the predeclared issues | Rebuilt: missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle; trades and gross on issue vs other sessions |
| F8 | PDR's loss over the three years was not stated in the summary | Stated with per-year numbers; IRF is the main source of profit; PDR+PDS offset IRF in 2023-24 |
| F9 | The same-minute conflict rule (no approved tie-break) was not quantified | Conflict-day counts per year added to the three-year summary |
| F10 | Overlap percentages were rounded in a way that hid a one-tick case | Rounding fixed, one-tick test added |
| F11 | Calendar-method validation is partly circular | Disclosed; derived dates also not compared with NSE circulars |
| F12 | "Seven years" wording | Replaced by "six distinct years" (2018, 2019 appears in two vendor runs, 2022-23, 2023-24, 2024-25, Window A) |
| F13 | float32 wording: the noise is in the DAILY candles, not the minute responses | Corrected |
| F14 | README of the secondary vendor says nothing on 2018-19 cleaning; Muhurat bars kept as exception | Added to data source discovery |
| F15 | 2018-07-09 labelled as a special session | Reworded: a normal Monday with a missing 09:15 bar, excluded by the gate |
| F16 | 2020-2021 minute data not retrieved: vendor gaps looked like holidays | Coverage notes say each source is only expected inside the years retrieved |
| F17 | Source snapshot already contains the (behaviour-preserving) Phase 4 edits to three framework files | Stated in the audit; pre-Phase-4 state is `before_snapshot.json`; a test rebuilds Phase 3.6 with the defaults |
| F18 | Windows B and B_TV are not on identical session sets | Disclosed (2023-10-19 excluded in B only) |
| F19 | `RiskLimits` note in the readiness text | Added: its Rs 10,000 daily loss limit is below the strategy's own single-trade loss (Rs 13,650) |
| F20 | Probe file path in the docs was relative to the wrong directory | Fixed |
| F21 | Test/ruff results were placeholders | Real results recorded below |

**Limits the reviewer could not remove:** the quality of the 2018 secondary-vendor data cannot be checked against any other source; which vendor's 09:15 bar is the exchange's is unknown; the result at 390 fixed units says nothing about what was executable historically.
