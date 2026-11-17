# Entry / exit execution audit

Method: `scripts/phase62_audit.py` re-derives, from the RAW one-minute bars and with a separate NumPy simulator (it does not call `exit_policy` or `trading_day`), the entry price, all levels, both leg exits (price and minute), the outcome class, the same-minute-ambiguity flag and the gross rupee P&L of every executed trade.

| window|config | trades | fully_verified | problems |
|---|---|---|---|
| A/A | 196 | 196 | 0 |
| A/B | 188 | 188 | 0 |
| A/C | 183 | 183 | 0 |
| A/D1 | 188 | 188 | 0 |
| A/D2 | 200 | 200 | 0 |
| B/A | 609 | 609 | 0 |
| B/B | 598 | 598 | 0 |
| B/C | 603 | 603 | 0 |
| B/D1 | 598 | 598 | 0 |
| B/D2 | 633 | 633 | 0 |


**3996 of 3996 executed trades verified, 0 problems** (see `execution_audit_problems.csv`).

Checks per trade: (1) the fill is the open of the 1-minute bar that starts when the signal candle ends (never before the signal is complete) and not after 13:00; (2) entry price = raw bar open; (3) stop / T1 / T2 / post-T1 levels = entry -/+ the strategy's distances (35 or 30; 27; 60 or 70; 6); (4) position 195 + 195; (5) the exit sequence under the documented conventions: stop before target in one bar (flagged), a bar opening through a stop fills at its open, targets at their level, Target 1 then Target 2 in one bar allowed, post-T1 stop = entry -/+ 6 with no trailing, forced exit at the 15:14 open, nothing at/after 15:15 or on a closing-auction bar; (6) P&L.

Regression gates inside `phase62_run.py` (the run aborts otherwise): configuration A reproduces the Phase 5.5 ledger (196 trades, 0 mismatches), B reproduces the Phase 5.5 ledger (188 trades, 0 mismatches), A on the 2022-25 window reproduces Phase 4 (609 trades), D1 equals B on both windows.

Same-minute ambiguities: 30 (all configurations and windows); each is resolved adversely by the predeclared conservative policy and listed in `intrabar_ambiguities.csv`.

ORB V2 integration checks (`orb_v2_integration_checks.csv`): for every session the 09:15-09:20 candle of ORB V2 equals the controller's own session candle; every ORB V2 signal candle runs 09:15-09:20 and its fill is the 09:20 bar open.