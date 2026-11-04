# Signal counts under the default proposals (descriptive only)

Sessions evaluated: **247** usable of 248. `method|status` -> number of records.

> Counts only. They are **not** used to choose among interpretations and must **not** be compared with the performance report's 189 trades to tune anything.


## IRF

| method | status | records |
|---|---|---|
| Method 1/2 | INCOMPLETE_AT_EOD | 130 |
| Method 1 | CONFIRMED | 349 |
| Method 2A | CONFIRMED | 215 |
| Method 2B | CONFIRMED | 310 |
| Method 3 | INVALIDATED | 37 |

Confirmed signals by verification status: Method 1|PROPOSAL_DEPENDENT=349, Method 2A|PROPOSAL_DEPENDENT=215, Method 2B|PROPOSAL_DEPENDENT=310

## ORB

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| Gap/200DMA | CONFIRMED | 9 |
| Gap/200DMA | INVALIDATED | 42 |
| Method 1 | CONFIRMED | 23 |
| Method 1 | INVALIDATED | 85 |
| Method 2 | CONFIRMED | 16 |
| Method 2 | INVALIDATED | 179 |

Confirmed signals by verification status: Gap/200DMA|RESEARCH_VARIANT=9, Method 1|PROPOSAL_DEPENDENT=23, Method 2|RESEARCH_VARIANT=16

## PDR

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| PDR | CONFIRMED | 39 |
| PDR | INVALIDATED | 80 |

Confirmed signals by verification status: PDR|PROPOSAL_DEPENDENT=39

## PDS

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| Method 1/2/3 | INCOMPLETE_AT_EOD | 5 |
| Method 1/2/3 | INVALIDATED | 61 |
| Method 1 | CONFIRMED | 9 |
| Method 3 | CONFIRMED | 15 |

Confirmed signals by verification status: Method 1|PROPOSAL_DEPENDENT=9, Method 3|PROPOSAL_DEPENDENT=15

## RF

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| RF | CONFIRMED | 12 |
| RF | INCOMPLETE_AT_EOD | 38 |
| RF | INVALIDATED | 129 |

Confirmed signals by verification status: RF|PROPOSAL_DEPENDENT=12

## Single-parameter sensitivity (records: default -> variant; only changed rows)

| variant | changed `method|status` : default -> variant |
|---|---|
| IRF m1_max_candles_after_breakout=2 (p.14 'or following candle') | Method 1/2|INCOMPLETE_AT_EOD: 130→135; Method 1|CONFIRMED: 349→352; Method 2A|CONFIRMED: 215→197; Method 2B|CONFIRMED: 310→306 |
| IRF m1_close_below_irl_counts_as_inside=True | Method 1/2|INCOMPLETE_AT_EOD: 130→129; Method 1|CONFIRMED: 349→356; Method 2A|CONFIRMED: 215→214; Method 2B|CONFIRMED: 310→313 |
| IRF m2_extension_definition=E2 | Method 1/2|INCOMPLETE_AT_EOD: 130→106; Method 2A|CONFIRMED: 215→334; Method 2B|CONFIRMED: 310→321 |
| IRF m2a_break_may_be_red_candle=True | Method 2A|CONFIRMED: 215→218; Method 2B|CONFIRMED: 310→314 |
| IRF m2_red_may_be_extension_candle=True | no change |
| IRF irf_support_def=SWING_K2 | Method 1/2|INCOMPLETE_AT_EOD: 130→132; Method 2A|CONFIRMED: 215→154; Method 2B|CONFIRMED: 310→296 |
| IRF irf_support_def=LAST_N3 | Method 1/2|INCOMPLETE_AT_EOD: 130→131; Method 2A|CONFIRMED: 215→309; Method 2B|CONFIRMED: 310→308 |
| IRF irf_resistance_def=LATEST_SWING_HIGH | Method 1/2|INCOMPLETE_AT_EOD: 130→109; Method 2A|CONFIRMED: 215→190; Method 2B|CONFIRMED: 310→408 |
| IRF m2_expiry_candles=6 (30 min) | Method 1/2|INCOMPLETE_AT_EOD: 130→100; Method 1/2|INVALIDATED: 0→706; Method 2A|CONFIRMED: 215→84; Method 2B|CONFIRMED: 310→211 |
| IRF m3_wick_share_band=MIN_60 | no change |
| IRF m3_wick_share_band=BAND_55_75 | no change |
| IRF m3_compression_n=3 | Method 3|INVALIDATED: 37→27 |
| IRF m3_compression_def=C2 | Method 3|INVALIDATED: 37→33 |
| ORB orb_pin_bar_in_methods_1_2=False | Method 1|CONFIRMED: 23→18; Method 1|INVALIDATED: 85→90; Method 2|CONFIRMED: 16→13; Method 2|INVALIDATED: 179→182 |
| ORB strong_candle=STRICT | Gap/200DMA|CONFIRMED: 9→5; Gap/200DMA|INVALIDATED: 42→46; Method 1|CONFIRMED: 23→15; Method 1|INVALIDATED: 85→93; Method 2|CONFIRMED: 16→13; Method 2|INVALIDATED: 179→182 |
| ORB strong_candle=LOOSE | Method 1|CONFIRMED: 23→31; Method 1|INVALIDATED: 85→77; Method 2|CONFIRMED: 16→21; Method 2|INVALIDATED: 179→174 |
| ORB trend_mode=EMA5M_BASIC | Method 1|CONFIRMED: 23→31; Method 1|INVALIDATED: 85→77; Method 2|CONFIRMED: 16→20; Method 2|INVALIDATED: 179→175 |
| ORB trend_mode=EMA5M_PREV_3_SESSIONS | Method 1|CONFIRMED: 23→8; Method 1|INVALIDATED: 85→100; Method 2|CONFIRMED: 16→7; Method 2|INVALIDATED: 179→188 |
| ORB trend_mode=SMA200_DAILY (now evaluable on all 247 sessions) | Method 1|CONFIRMED: 23→13; Method 1|INVALIDATED: 85→95; Method 2|CONFIRMED: 16→8; Method 2|INVALIDATED: 179→187 |
| ORB ma_mode=SMA200_DAILY for the gap setup | Gap/200DMA|CONFIRMED: 9→0; Gap/200DMA|INVALIDATED: 42→1 |
| ORB gap_max_points=150 | Gap/200DMA|CONFIRMED: 9→7; Gap/200DMA|INVALIDATED: 42→44 |
| PDR zone_lower_boundary=ZONE_WICK | no change |
| PDR zone_proximity_points=0 | PDR|CONFIRMED: 39→37 |
| PDR zone_proximity_points=10 | PDR|CONFIRMED: 39→41 |
| PDR pdr_green_may_be_interaction_candle=True | no change |
| PDR pdr_open_vs_zone=ABOVE_ZONE (the text) | no change |
| PDR pdr_open_vs_zone=NOT_BELOW_ZONE | PDR|CONFIRMED: 39→53; PDR|INVALIDATED: 80→66 |
| PDR pdr_open_vs_zone=ANY | PDR|CONFIRMED: 39→119; PDR|INVALIDATED: 80→0 |
| PDR pdr_reversal_filter=DEPTH_25PCT | PDR|CONFIRMED: 39→21; PDR|INVALIDATED: 80→105 |
| PDS strong_candle=STRICT | Method 1/2/3|INCOMPLETE_AT_EOD: 5→6; Method 1|CONFIRMED: 9→3; Method 3|CONFIRMED: 15→20 |
| PDS strong_candle=LOOSE | Method 1|CONFIRMED: 9→11; Method 3|CONFIRMED: 15→13 |
| PDS zone_proximity_points=0 | Method 1/2/3|INCOMPLETE_AT_EOD: 5→4; Method 1|CONFIRMED: 9→8 |
| PDS zone_proximity_points=10 | Method 1|CONFIRMED: 9→10 |
| PDS pds_m3_break_basis=TOUCH | Method 1/2/3|INCOMPLETE_AT_EOD: 5→4; Method 3|CONFIRMED: 15→16 |
| PDS pds_m3_standalone=True | Method 1/2/3|INCOMPLETE_AT_EOD: 5→4; Method 3|CONFIRMED: 15→16 |
| PDS pds_open_vs_zone=NOT_ABOVE_ZONE | Method 1/2/3|INCOMPLETE_AT_EOD: 5→6; Method 1/2/3|INVALIDATED: 61→48; Method 1|CONFIRMED: 9→15; Method 2|CONFIRMED: 0→1; Method 3|CONFIRMED: 15→20 |
| PDS pds_open_vs_zone=ANY | Method 1/2/3|INCOMPLETE_AT_EOD: 5→20; Method 1/2/3|INVALIDATED: 61→0; Method 1|CONFIRMED: 9→34; Method 2|CONFIRMED: 0→1; Method 3|CONFIRMED: 15→35 |
| PDR prev_day_level_window=CONTINUOUS_ONLY | no change |
| PDS prev_day_level_window=CONTINUOUS_ONLY | no change |
| ORB prev_day_level_window=CONTINUOUS_ONLY | Method 1|INVALIDATED: 85→88; Method 2|INVALIDATED: 179→180 |
| RF prev_day_level_window=CONTINUOUS_ONLY | no change |
| ORB prev_close_source=LAST_PRINT_1530 | no change |
| PDR prev_close_source=LAST_PRINT_1530 | PDR|INVALIDATED: 80→76 |
| PDS prev_close_source=LAST_PRINT_1530 | Method 1/2/3|INVALIDATED: 61→65 |
| RF prev_close_source=LAST_PRINT_1530 | no change |
| RF rf_return_inside_def=R2 | RF|CONFIRMED: 12→14; RF|INCOMPLETE_AT_EOD: 38→21; RF|INVALIDATED: 129→144 |
| RF rf_return_inside_def=R3 | RF|CONFIRMED: 12→7; RF|INCOMPLETE_AT_EOD: 38→0; RF|INVALIDATED: 129→172 |
| RF trend_mode=EMA5M_BASIC | RF|CONFIRMED: 12→20; RF|INVALIDATED: 129→121 |
| RF trend_mode=EMA5M_PREV_3_SESSIONS | RF|CONFIRMED: 12→6; RF|INVALIDATED: 129→135 |
