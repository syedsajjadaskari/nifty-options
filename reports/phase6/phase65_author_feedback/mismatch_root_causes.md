# Manual-journal mismatch root causes (primary window)

The journal records date, time label, strategy and outcome only. 'Manual-only' = a journal row with no one-to-one automated counterpart; 'wrong-strategy date' = the configuration traded that day but not the journal's strategy.

| config | manual_only | weekend_rows | wrong_strategy_dates | no_automated_trade_that_day | automated_only |
|---|---|---|---|---|---|
| BASE | 91 | 5 | 53 | 33 | 84 |
| S60 | 106 | 5 | 51 | 50 | 75 |
| S70 | 110 | 5 | 48 | 57 | 69 |
| SD | 91 | 5 | 54 | 32 | 83 |
| PDR_B1 | 92 | 5 | 55 | 32 | 94 |
| PDR_B2 | 94 | 5 | 55 | 34 | 94 |
| PDR_C | 93 | 5 | 53 | 35 | 84 |
| PDR_D | 91 | 5 | 53 | 33 | 84 |
| PDS_FROZEN | 89 | 5 | 52 | 32 | 81 |
| PDS_SECOND | 88 | 5 | 51 | 32 | 77 |


## Direct versus portfolio effect

A change in agreement caused by a RULE accepting or rejecting a signal is a DIRECT effect; a change caused by the controller then selecting a different later signal (one trade at a time; the second trade only after a full stop and only PDR/PDS) is a PORTFOLIO effect. `trade_set_attribution.csv` labels every removed and added trade; `configuration_trade_comparison.csv` totals them:

| config | baseline_trades_removed | removed_direct_effect | removed_portfolio_effect | new_trades_added | added_direct_effect | added_portfolio_effect | same_day_strategy_changed | earlier_entry_same_strategy | later_entry_same_strategy | changed_second_trade_eligibility_days |
|---|---|---|---|---|---|---|---|---|---|---|
| S60 | 65 | 65 | 0 | 41 | 0 | 41 | 6 | 0 | 34 | 32 |
| S70 | 83 | 83 | 0 | 49 | 0 | 49 | 8 | 0 | 41 | 44 |
| SD | 5 | 5 | 0 | 4 | 0 | 4 | 0 | 0 | 4 | 3 |
| PDR_B1 | 12 | 6 | 6 | 21 | 21 | 0 | 1 | 9 | 2 | 11 |
| PDR_B2 | 19 | 6 | 13 | 26 | 26 | 0 | 1 | 14 | 1 | 13 |
| PDR_C | 8 | 6 | 2 | 6 | 5 | 1 | 0 | 5 | 1 | 2 |
| PDR_D | 27 | 27 | 0 | 27 | 21 | 6 | 0 | 0 | 27 | 8 |
| PDS_FROZEN | 10 | 10 | 0 | 9 | 5 | 4 | 2 | 0 | 6 | 3 |
| PDS_SECOND | 16 | 16 | 0 | 12 | 1 | 11 | 3 | 0 | 9 | 6 |


Standing causes (unchanged by any variant): the journal's 5 weekend-dated rows; of 89 manual ORB rows the baseline has 38 with a strict or time-tolerant counterpart; IRF and PDS journal rows that no signal of the engine reproduces; automated trades on days with no journal row (the journal is not exhaustive evidence). The journal's own summary tab states 189 trades while 190 data rows are read (not reconciled by the source). Date-only agreements are never counted as matches and no exact trade match is claimed.