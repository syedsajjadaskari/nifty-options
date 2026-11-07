# IRF - the 28-point EMA gap (investigation; diagnostics only)

Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

**Statement (call):** 'Sometimes IRF is correct, but the gap between the EMA and the candle should be 28 points.' **Handwritten pages (Phase 5.1):** 'space between the entry candle and the EMA less than 27 -> wait for the EMA break' (AC13, AC18).

## Source search

The IRF guide never mentions the 200 EMA in its text (the reference charts draw a moving-average line without a rule). The 27 of the handwritten pages equals Target 1 (27 points); 28 is new. **No deterministic rule can be derived from the sources.** Nothing is activated.

## What cannot be established (so it is not guessed)

* the measurement: signal-candle close, high, low, the entry price, or the whole candle against the EMA;
* the inequality: a minimum clearance (EMA at least 28 below), a maximum distance, or |close - EMA| in either direction;
* the action: skip the signal, or wait until a candle closes below the EMA (and for how long);
* the scope: every IRF method or only some;
* 28 (call) versus 27 (handwritten).

## Diagnostics computed for every confirmed IRF signal (874 signals, 115 signal rows matching a Phase 3.6 executed trade; EMA = EMA(200) of completed five-minute closes)

Per signal: EMA(200), candle high / low / close, entry price (the next one-minute open), close - EMA, high - EMA, low - EMA, entry - EMA, |close - EMA|, whether the EMA lies between the entry and Target 1 (entry - 27), EMA - T1. See `irf_signal_diagnostics.csv`.

| alternative reading (none is a rule) | all confirmed IRF signals | of which executed in Phase 3.6 | signals within the 13:00 cutoff | executed within cutoff |
|---|---|---|---|---|
| close is 0..28 points ABOVE the EMA (E1) | 70 | 12 | 43 | 12 |
| entry price is 0..28 points above the EMA (E2) | 70 | 12 | 42 | 12 |
| signal-candle LOW is 0..28 above the EMA (E3) | 60 | 11 | 35 | 11 |
| /close - EMA/ < 28 on either side (E4) | 116 | 19 | 70 | 19 |
| the same as E1 with 27 (handwritten number) | 65 | 10 | 39 | 10 |
| close - EMA in [27, 28): where 27 and 28 give DIFFERENT answers | 5 | 2 | 4 | 2 |
| EMA between the entry and Target 1 | 66 | 10 | 39 | 10 |

Reading E1 (close-based, 0 < close - EMA < N): the choice between 27 and 28 changes the answer for 5 signals (2 matching executed trades). Under reading E2 (entry-based) it changes the answer for 4 signals (2 executed). Union of the two readings: 2025-11-19 10:50 Method 2A, 2026-02-17 10:45 Method 2B (executed), 2026-05-27 10:40 Method 2B (executed), 2026-07-01 15:05 Method 2B, 2026-07-10 13:00 Method 1, 2026-07-10 13:10 Method 1, 2026-08-10 12:25 Method 1 (executed). The number is not a rounding detail.

## The two dated handwritten examples

| date | correction | measurements |
|---|---|---|
| 2025-10-09 | AC13 | close_minus_ema=2.92640380451121; entry_minus_ema=2.7264038045104826; ema_between_entry_and_t1=True; ema_minus_t1=24.273596195489517; E1_close_gap_below_ema_28=True; E2_entry_gap_below_ema_28=True |
| 2025-11-10 | AC18 | close_minus_ema=25.269671700712934; entry_minus_ema=25.369671700715116; ema_between_entry_and_t1=True; ema_minus_t1=1.6303282992848835; E1_close_gap_below_ema_28=True; E2_entry_gap_below_ema_28=True |

Both examples are consistent with every reading above (EMA 2.93 and 25.27 points below the entry), so they cannot discriminate between 'skip' and 'wait', between close and entry, or between 27 and 28.

## Conclusion and request

Preserve the current IRF engine; no EMA rule is implemented. **Owner decision O2:** the measure, the inequality, skip versus wait, the scope, and 27 versus 28.
