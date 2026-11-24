# Combined IRF V3 signal engine

Both methods run on the SAME session independently; neither can see the other's state.

```
session -> [Method 1 machine] -> M1 signal? (time t1)        \
        -> [Method 2 machine] -> M2 signal? (time t2)         >-> eligibility (fill bar <= 13:00:00, bar exists & continuous)
                                                              /-> select earliest eligible signal_time
```
Cases handled and counted (window A / window B first signals, from `overlap_analysis.csv` and the signal ledgers):

| Case | A | B |
|---|---|---|
| Only M1 qualifies | 49 | 156 |
| Only M2 qualifies | 9 | 55 |
| Both, M1 first | 60 | 151 |
| Both, M2 first | 37 | 106 |
| Both, same instant | 7 | 20 |
| Signal(s) only after the 13:00 cutoff | A: M1 28, M2 27 | B: M1 57, M2 64 |

* Ledger: `combined_irf_signals.csv` keeps every first signal of both methods with `selected_in_combined`, `overlap_class`, `status`.
* One trade per day: the earliest ELIGIBLE signal. Because both methods' trades are simulated by the same function, a same-instant pair has identical entry, stop, target and exit - **counting is by day, never by method, so no trade is double counted** (verified by test `test_combined_book_has_no_double_counted_trades`).
* **Same-instant tie** (both signals on one failure candle): the documents define no priority. Policy `TIE_METHOD_1` is a deterministic research label (NOT author-approved) that only attributes the trade; P&L is unaffected (`overlap_analysis.csv`, column `same_entry_price_and_exit`).
* A method that produced its first signal after 13:00 is not eligible; the other method (if earlier) is selected. If both are late: `NO_ELIGIBLE_SIGNAL`.
* A setup that invalidates before confirmation: neither PDF states any invalidation, so none exists; a setup that never completes appears as a no-signal day with its missing conditions in `daily_verification.csv`.
