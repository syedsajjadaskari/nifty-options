# Trade visualization summary (Phase 5.7)

> SYNTHETIC NIFTY 50 index-point P&L (6 lots x 65 units); not option P&L. The journal records no price, direction or exit time, so 'exact' below means exact on DATE, STRATEGY and the entry-time LABEL only - never on price or outcome.

Every executed trade of configurations A, B and C has an enhanced chart in the visual spirit of the Phase 3.6 trade chart (real five-minute candles, EMA(200), reference levels and zones, role marks, dashed manual-journal lines) with the information needed for manual verification added next to the price action. No backtest was run and no rule or matching logic was touched: the numbers on the charts are read from the verified Phase 5.5 ledgers and the match labels from the verified Phase 5.6 files.

## What each chart shows

| element | how it is drawn |
|---|---|
| header | trade id, strategy, method, direction, configuration, date, first / second trade, outcome, signal candle, entry time and price, gross Rs; match-status badge (EXACT_MATCH green, TIME_TOLERANT_MATCH blue, DATE_STRATEGY_ONLY orange, AUTOMATED_ONLY grey) and the journal row reference |
| entry | black triangle at the exact one-minute position and price, labelled `ENTRY hh:mm @ price` next to it and in the right margin; the fill candle (one-minute bar) and the signal candle are listed in the ENTRY block together with the setup explanation and the trigger (strategy / method) |
| initial stop, T1, T2 | named and priced lines (`SL @`, `T1 @`, `T2 @`) from the entry; the stop and T1 lines end when T1 is hit (the stop is then replaced), T2 runs to the last exit; each line continues faintly to its name in the right margin |
| post-T1 stop | orange dotted line `POST-T1 STOP @ price`, drawn ONLY from the moment T1 was booked (never before it; absent when T1 was not hit) |
| exits | leg 1: circle `LEG1 EXIT - T1 hit, hh:mm @ price`; leg 2: square `LEG2 EXIT - T2 hit / Post-T1 stop / Forced exit`; both legs on the same stop: one double ring `FULL EXIT - Initial SL`; the provisional 15:14 forced exit: `FORCED EXIT - 15:14 @ price` |
| journal | dashed magenta vertical line at the candle START of every journal row of the day (bold for the row matched to this trade); the journal records no price, so no manual price is drawn |
| blocks | ENTRY / LEVELS AND EXITS (with points from entry, both legs with reason, time, price) / P&L (3 + 3 lots, 195 + 195 units, points and rupees per leg, gross, net Rs 70 per trade and net with 0.25 / 0.5 / 1.0 point slippage per side) / JOURNAL COMPARISON (match type, journal row, journal label and outcome, agreement, time difference; for AUTOMATED_ONLY the Phase 5.6 root cause and evidence) |
| context | EMA(200) when in range, reference levels of the strategy (opening range, previous-day high / low, support / resistance, small support), the PDR / PDS zone, and the Phase 3.6 role marks (IR, C0, BRK, SIGNAL, CONFIRM, ...); levels far outside the price range are listed above the chart instead of squeezing the candles |

Labels in the right margin are spread vertically so that no two overlap; labels next to markers avoid each other. The time axis starts at 09:15 and ends shortly after the last exit (at least 50 minutes after the entry) so that the candles stay readable.

## Folders

| folder | charts | content |
|---|---|---|
| `charts_all/` | 574 | every executed trade of A, B and C (`<config>_<trade id>.svg`) |
| `charts_exact_matches/` | 197 | EXACT (strict) matches |
| `charts_time_tolerant/` | 49 | time-tolerant matches |
| `charts_automated_only/` | 276 | AUTOMATED_ONLY trades (no journal row of the same date and strategy left) |
| `charts_date_strategy_only/` | 52 | date-and-strategy-only pairs (not matches; an extra folder so that every status has one) |
| `charts_orb_focus/` | 176 | all executed ORB trades plus 50 journal-day charts (`DAY_<date>_ORB.svg`) for every ORB journal date without a counted match (weekend rows excluded) |
| `charts_handwritten_dates/` | 109 | trades on the dates of the handwritten author corrections (index: `handwritten_correction_chart_index.csv`) |
| `charts_config_differences/` | 175 | trades that are not identical in A, B and C (method, direction, signal candle, entry, outcome or P&L differ, or the trade exists in only some configurations) |

The subset folders hold byte-identical copies of the charts in `charts_all/`; the earlier Phase 3.6 / 5.5 / 5.6 charts were not touched.

## How to verify a trade manually

1. Open the chart; read the header for the trade, the configuration and the match status. 2. Check the `ENTRY` marker against the one-minute fill candle printed in the ENTRY block (open of the bar that starts when the signal candle ends). 3. Read the SL / T1 / T2 distances (35 or 30 / 27 / 60 or 70 points). 4. Follow the price to the first exit: leg 1 at T1 (27 points) or the stop; after T1 the stop moves to entry -/+ 6. 5. Compare with the journal block. 6. Row-level numbers are in `Phase57_Trade_Verification.xlsx` and `all_executed_trades_visual_index.csv`.

## Limits

* Markers are drawn at their exact one-minute position on a five-minute candle chart; a one-minute entry or exit sits inside its candle.
* The journal label is the candle start; the journal records no price, direction or exit, so only dates, strategies and times can be compared.
* The 15:14 forced exit, the stop-first convention, the Rs 70 cost and the 390-unit position are provisional assumptions of the backtest; B and C rest on provisional conventions.
* Synthetic index points only: no option premium, strike or expiry is drawn.

