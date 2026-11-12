# EMA and gap research (ORB V2)

All counts use the primary 5paisa windows (A = 2025-09..2026-08, B = 2022-09..2025-08) and config ORB-V2-A unless stated. EMA(200) is the independent 5-minute recursion; it agrees with the TradingView/FYERS screenshot labels within 0.25 point.

## The three EMA-opening scenarios

Direction is close-based, exactly as the rulebook states. The scenario label records how the candle relates to the EMA: **A** already beyond it with the previous session on the same side; **B** the candle opens on the wrong side/at the EMA and closes beyond it (intrabar cross); **C** an overnight gap carries the open across the EMA. All three pass the close-based filter. The rulebook does not require the candle to stay on one side, so none is rejected; whether an intrabar cross and an overnight-gap cross should be treated alike is recorded as a source interpretation (not decided here).

| window | direction | scenario | sessions | signals |
|---|---|---|---|---|
| A | BUY | A_ALREADY_BEYOND_EMA | 100 | 16 |
| A | BUY | B_INTRABAR_CROSS_OF_EMA | 11 | 3 |
| A | BUY | C_OVERNIGHT_GAP_CROSSES_EMA | 20 | 1 |
| A | SELL | A_ALREADY_BEYOND_EMA | 87 | 10 |
| A | SELL | B_INTRABAR_CROSS_OF_EMA | 11 | 5 |
| A | SELL | C_OVERNIGHT_GAP_CROSSES_EMA | 18 | 4 |
| B | BUY | A_ALREADY_BEYOND_EMA | 360 | 30 |
| B | BUY | B_INTRABAR_CROSS_OF_EMA | 21 | 6 |
| B | BUY | C_OVERNIGHT_GAP_CROSSES_EMA | 64 | 4 |
| B | SELL | A_ALREADY_BEYOND_EMA | 224 | 35 |
| B | SELL | B_INTRABAR_CROSS_OF_EMA | 31 | 15 |
| B | SELL | C_OVERNIGHT_GAP_CROSSES_EMA | 38 | 3 |


## Gap filter (250 versus 300 points)

| window | sessions | abs_gap>250 | abs_gap>300 | 250<abs_gap<=300 | max_abs_gap | gap_up_above_prev_high | gap_down_below_prev_low |
|---|---|---|---|---|---|---|---|
| A | 247 | 17 | 12 | 5 | 1176.5 | 62 | 46 |
| B | 738 | 20 | 12 | 8 | 1096.7 | 201 | 101 |


Sessions where the two limits change the decision (A = 250, B = 300): 
| window | date | gap_points | A(250) | B(300) |
|---|---|---|---|---|
| B | 2022-09-01 | -273.6 | - | BUY |


Both limits are fixed research scenarios; neither is preferred. The gap is the first one-minute open minus the previous trading day's OFFICIAL daily close (vendor daily series). The opening print differs between feeds (see `candle_pattern_validation.md`), so the gap itself is feed-dependent.