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
| ALL | NOT_EVALUATED | 27 |
| Gap/200DMA | CONFIRMED | 7 |
| Gap/200DMA | INVALIDATED | 35 |
| Gap/200DMA | NOT_EVALUATED | 2 |
| Method 1 | CONFIRMED | 23 |
| Method 1 | INVALIDATED | 75 |
| Method 1 | NOT_EVALUATED | 1 |
| Method 2 | CONFIRMED | 15 |
| Method 2 | INVALIDATED | 156 |
| Method 2 | NOT_EVALUATED | 2 |

Confirmed signals by verification status: Gap/200DMA|RESEARCH_VARIANT=7, Method 1|PROPOSAL_DEPENDENT=23, Method 2|RESEARCH_VARIANT=15

## PDR

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 27 |
| PDR | CONFIRMED | 35 |
| PDR | INVALIDATED | 67 |

Confirmed signals by verification status: PDR|PROPOSAL_DEPENDENT=35

## PDS

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 27 |
| Method 1/2/3 | INCOMPLETE_AT_EOD | 5 |
| Method 1/2/3 | INVALIDATED | 55 |
| Method 1 | CONFIRMED | 8 |
| Method 3 | CONFIRMED | 14 |

Confirmed signals by verification status: Method 1|PROPOSAL_DEPENDENT=8, Method 3|PROPOSAL_DEPENDENT=14

## RF

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 27 |
| RF | CONFIRMED | 11 |
| RF | INCOMPLETE_AT_EOD | 34 |
| RF | INVALIDATED | 109 |
| RF | NOT_EVALUATED | 1 |

Confirmed signals by verification status: RF|PROPOSAL_DEPENDENT=11

## Single-parameter sensitivity (records: default -> variant; only changed rows)

| variant | changed `method|status` : default -> variant |
|---|---|
| IRF m1_max_candles_after_breakout=2 (p.14 'or following candle') | Method 1/2|INCOMPLETE_AT_EOD: 130→135; Method 1|CONFIRMED: 349→352; Method 2A|CONFIRMED: 215→197; Method 2B|CONFIRMED: 310→306 |
| IRF m1_close_below_irl_counts_as_inside=True | Method 1/2|INCOMPLETE_AT_EOD: 130→129; Method 1|CONFIRMED: 349→356; Method 2A|CONFIRMED: 215→214; Method 2B|CONFIRMED: 310→313 |
| IRF m2_extension_definition=E2 | Method 1/2|INCOMPLETE_AT_EOD: 130→103; Method 2A|CONFIRMED: 215→334; Method 2B|CONFIRMED: 310→321 |
| IRF m2a_break_may_be_red_candle=True | Method 2A|CONFIRMED: 215→218; Method 2B|CONFIRMED: 310→314 |
| IRF m2_red_may_be_extension_candle=True | no change |
| IRF irf_support_def=SWING_K2 | Method 1/2|INCOMPLETE_AT_EOD: 130→132; Method 2A|CONFIRMED: 215→154; Method 2B|CONFIRMED: 310→296 |
| IRF irf_support_def=LAST_N3 | Method 1/2|INCOMPLETE_AT_EOD: 130→131; Method 2A|CONFIRMED: 215→309; Method 2B|CONFIRMED: 310→308 |
| IRF irf_resistance_def=LATEST_SWING_HIGH | Method 1/2|INCOMPLETE_AT_EOD: 130→108; Method 2A|CONFIRMED: 215→190; Method 2B|CONFIRMED: 310→408 |
| IRF m2_expiry_candles=6 (30 min) | Method 1/2|INCOMPLETE_AT_EOD: 130→98; Method 1/2|INVALIDATED: 0→705; Method 2A|CONFIRMED: 215→84; Method 2B|CONFIRMED: 310→211 |
| IRF m3_wick_share_band=MIN_60 | no change |
| IRF m3_wick_share_band=BAND_55_75 | no change |
| IRF m3_compression_n=3 | Method 3|INVALIDATED: 37→27 |
| IRF m3_compression_def=C2 | Method 3|INVALIDATED: 37→33 |
| ORB strong_candle=STRICT | Gap/200DMA|CONFIRMED: 7→4; Gap/200DMA|INVALIDATED: 35→38; Method 1|CONFIRMED: 23→15; Method 1|INVALIDATED: 75→83; Method 2|CONFIRMED: 15→12; Method 2|INVALIDATED: 156→159 |
| ORB strong_candle=LOOSE | Method 1|CONFIRMED: 23→29; Method 1|INVALIDATED: 75→69; Method 2|CONFIRMED: 15→20; Method 2|INVALIDATED: 156→151 |
| ORB trend_mode=EMA5M_BASIC | Method 1|CONFIRMED: 23→28; Method 1|INVALIDATED: 75→70; Method 2|CONFIRMED: 15→16; Method 2|INVALIDATED: 156→155 |
| ORB trend_mode=EMA5M_PREV_3_SESSIONS | Method 1|CONFIRMED: 23→8; Method 1|INVALIDATED: 75→89; Method 1|NOT_EVALUATED: 1→2; Method 2|CONFIRMED: 15→7; Method 2|INVALIDATED: 156→162; Method 2|NOT_EVALUATED: 2→4 |
| ORB trend_mode=SMA200_DAILY (47 evaluable sessions) | Method 1|CONFIRMED: 23→1; Method 1|INVALIDATED: 75→15; Method 1|NOT_EVALUATED: 1→83; Method 2|CONFIRMED: 15→0; Method 2|INVALIDATED: 156→22; Method 2|NOT_EVALUATED: 2→151 |
| ORB ma_mode=SMA200_DAILY for the gap setup | Gap/200DMA|CONFIRMED: 7→0; Gap/200DMA|INVALIDATED: 35→0; Gap/200DMA|NOT_EVALUATED: 2→193 |
| ORB gap_max_points=150 | Gap/200DMA|CONFIRMED: 7→6; Gap/200DMA|INVALIDATED: 35→36 |
| PDR zone_lower_boundary=ZONE_WICK | no change |
| PDR zone_proximity_points=0 | PDR|CONFIRMED: 35→33 |
| PDR zone_proximity_points=10 | PDR|CONFIRMED: 35→37 |
| PDR pdr_green_may_be_interaction_candle=True | no change |
| PDR require_open_clear_of_zone=False | PDR|CONFIRMED: 35→102; PDR|INVALIDATED: 67→0 |
| PDR pdr_reversal_filter=DEPTH_25PCT | PDR|CONFIRMED: 35→18; PDR|INVALIDATED: 67→91 |
| PDS strong_candle=STRICT | Method 1/2/3|INCOMPLETE_AT_EOD: 5→6; Method 1|CONFIRMED: 8→2; Method 3|CONFIRMED: 14→19 |
| PDS strong_candle=LOOSE | Method 1|CONFIRMED: 8→10; Method 3|CONFIRMED: 14→12 |
| PDS zone_proximity_points=0 | Method 1/2/3|INCOMPLETE_AT_EOD: 5→4; Method 1|CONFIRMED: 8→7 |
| PDS zone_proximity_points=10 | Method 1|CONFIRMED: 8→9 |
| PDS pds_m3_break_basis=TOUCH | Method 1/2/3|INCOMPLETE_AT_EOD: 5→4; Method 3|CONFIRMED: 14→15 |
| PDS pds_m3_standalone=True | Method 1/2/3|INCOMPLETE_AT_EOD: 5→4; Method 3|CONFIRMED: 14→15 |
| PDS require_open_clear_of_zone=False | Method 1/2/3|INCOMPLETE_AT_EOD: 5→19; Method 1/2/3|INVALIDATED: 55→0; Method 1|CONFIRMED: 8→29; Method 2|CONFIRMED: 0→2; Method 3|CONFIRMED: 14→32 |
| RF rf_return_inside_def=R2 | RF|CONFIRMED: 11→13; RF|INCOMPLETE_AT_EOD: 34→19; RF|INVALIDATED: 109→122 |
| RF rf_return_inside_def=R3 | RF|CONFIRMED: 11→7; RF|INCOMPLETE_AT_EOD: 34→0; RF|INVALIDATED: 109→147 |
| RF trend_mode=EMA5M_BASIC | RF|CONFIRMED: 11→16; RF|INVALIDATED: 109→104 |
| RF trend_mode=EMA5M_PREV_3_SESSIONS | RF|CONFIRMED: 11→6; RF|INVALIDATED: 109→112; RF|NOT_EVALUATED: 1→3 |
