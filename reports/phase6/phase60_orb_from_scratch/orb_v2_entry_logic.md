# ORB V2 entry logic

Timeline of one session (IST):

1. 09:15-09:19 one-minute rows are collected; the 5-minute candle is NOT usable before 09:20:00.
2. 09:20:00 signal confirmation (`signal_confirmed_at`). All checks run on the completed candle plus previous-session data only.
3. Conditions (all evaluated; each failure recorded): gap, EMA direction, previous-day level break, colour, pattern, wrong-side wick, zero range.
4. If every condition passes, the first causally executable fill is the OPEN of the 09:20 one-minute bar (provisional convention; rulebook: close of the 9:15 candle, TO CONFIRM).
5. Stop = entry -/+ 30, target = entry +/- 60. The 09:20 bar's own range counts (the fill is at its open). Same-minute collision: stop first. A bar opening through the stop fills at its open; targets fill at the target price.
6. Forced exit at the open of the 15:14 bar (provisional, repository FORCED-EXIT-001); never at or after 15:15; closing-auction bars are never executable.
7. One trade per session; there is no second entry in the model.

Reference execution values and diagnostics are in `all_orb_trades.csv` and `all_orb_exits.csv`; every session (traded or not) has its full condition table in `all_orb_signals.csv`.

## Configurations

| id | summary |
|---|---|
| ORB-V2-A | written-rule reference: 250-pt gap, swing-zone inner levels, close-beyond break, engulfing vs previous session's last continuous candle |
| ORB-V2-B | A with a 300-pt gap limit |
| ORB-V2-C | A with clustered repeated-rejection inner zones |
| ORB-V2-D | A with engulfing disabled at 09:20 |
| DIAG-A-OLDSIDE | diagnostic only: the candle must cross the level |


Settings, authority labels and hashes: `orb_v2_configuration_manifest.json`.