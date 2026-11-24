# IRF_V3_METHOD_1 - entry logic (from IRF_Inverse_Retest_Failure_Rulebook.pdf only)

```
S0 AWAIT_FIRST_CANDLE  : the 09:15-09:20 candle completes at 09:20:00. level = its HIGH (wick included). Frozen for the day.            [R02]
S1 AWAIT_BREAKOUT      : each later candle, evaluated at its END:
                           close >  level  -> breakout recorded, NO entry; go to S2                                                  [R03, R04]
                           close <  level  -> ignored (no earlier breakout close)                                                    [R06]
                           close == level  -> ignored                                                                                [R10]
S2 AWAIT_FAILURE       : close <  level  -> FAILURE: SHORT signal, signal_time = that candle's end                                    [R05, R07]
                           close >= level  -> keep waiting (any number of candles)
```
Nothing else is tested: no EMA, gap, previous-day structure, trend, first-candle colour, candle body size or breakout size.

**Execution (labelled scenarios, none optimised):** fill = OPEN of the one-minute bar that starts when the failure candle ends (first causally available price; the source's 'close of the failure candle' is the reference scenario `SIGNAL_CLOSE`). Fill bar must start <= 13:00:00 (inclusive), exist and be continuous-session. Stop = entry + 35 (`SL35_T60`) or +40 (`SL40_T60`); target = entry - 60. Both touched in one 5-minute window -> stop. Open at 15:14 forced exit. 1 trade/day; later breakout/failure cycles are counted (`later_cycles_after_first_signal(not_traded)`) but never traded.

**Rejection / no-trade reasons recorded per day:** `FIRST_CANDLE_MISSING`, `NO_CLOSE_ABOVE_LEVEL` (never broke out), `BREAKOUT_WITHOUT_FAILURE`, `SIGNAL_AFTER_CUTOFF`, `NOT_EVALUATED:<session reason>`.

**Provenance:** every signal row in `method1_signals.csv` carries `source_rule_ids` (M1-R02, R03, R05, R06, R07), the reference candle (the first candle), breakout candle, confirmation candle and timestamps.
