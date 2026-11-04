# Phase 2.2 event counts under the Phase 2.2 defaults (descriptive only)

Sessions evaluated: **247**. `method|status` -> number of records.

> Counts only. Not used to choose among interpretations; not compared with the report's trade counts; no profit computed.


## IRF

| method | status | records |
|---|---|---|
| Method 1/2 | INCOMPLETE_AT_EOD | 130 |
| Method 1 | CONFIRMED | 349 |
| Method 2A | CONFIRMED | 215 |
| Method 2B | CONFIRMED | 310 |
| Method 3 | INVALIDATED | 37 |

## ORB

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| Gap/200DMA | CONFIRMED | 10 |
| Gap/200DMA | INVALIDATED | 41 |
| Method 1 | CONFIRMED | 9 |
| Method 1 | INVALIDATED | 99 |
| Method 2 | CONFIRMED | 10 |
| Method 2 | INVALIDATED | 185 |

## PDR

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| PDR | CONFIRMED | 61 |
| PDR | INVALIDATED | 41 |

## PDS

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| Method 1/2/3 | INCOMPLETE_AT_EOD | 4 |
| Method 1/2/3 | INVALIDATED | 61 |
| Method 1 | CONFIRMED | 8 |
| Method 2 | CONFIRMED | 1 |
| Method 3 | CONFIRMED | 14 |

## RF

| method | status | records |
|---|---|---|
| ALL | NOT_EVALUATED | 1 |
| RF | CONFIRMED | 2 |
| RF | INCOMPLETE_AT_EOD | 38 |
| RF | INVALIDATED | 139 |

## Selection-policy event counts (research policies, none approved)

| strategy | confirmed events | ALL_VALID | FIRST_PER_DAY | ONE_ACTIVE | entry blocked by closing auction |
|---|---|---|---|---|---|
| IRF | 874 | 865 | 174 | 497 | 9 |
| ORB | 29 | 29 | 21 | 21 | 0 |
| PDR | 61 | 61 | 61 | 61 | 0 |
| PDS | 23 | 23 | 23 | 23 | 0 |
| RF | 2 | 2 | 2 | 2 | 0 |

## Zone-method agreement with method A across sessions

```json
{
 "PDR": {
  "B_SWING_HIGH_REVERSAL: differs from diagnostic highest-high": 198,
  "C_REPEATED_TOUCHES: differs from diagnostic highest-high": 217,
  "B_SWING_HIGH_REVERSAL: same as diagnostic highest-high": 49,
  "C_REPEATED_TOUCHES: no zone (no setup)": 16,
  "C_REPEATED_TOUCHES: same as diagnostic highest-high": 14
 },
 "PDS": {
  "B_SWING_LOW_REVERSAL: same as A": 38,
  "B_SWING_LOW_REVERSAL: fell back to A": 0,
  "C_REPEATED_TOUCHES: differs from A": 220,
  "C_REPEATED_TOUCHES: fell back to A": 13,
  "B_SWING_LOW_REVERSAL: differs from A": 209,
  "C_REPEATED_TOUCHES: same as A": 27
 }
}
```

## Single-parameter sensitivity (default -> variant; only changed rows)

| variant | strategy | changed rows |
|---|---|---|
| trend_mode=EMA5M_PREV_SESSION (Phase 2.1 default) | ORB | Method 1|CONFIRMED: 9→27; Method 1|INVALIDATED: 99→81; Method 2|CONFIRMED: 10→16; Method 2|INVALIDATED: 185→179 |
| trend_mode=EMA5M_PREV_SESSION (Phase 2.1 default) | RF | RF|CONFIRMED: 2→12; RF|INVALIDATED: 139→129 |
| trend_mode=EMA5M_BASIC | ORB | Method 1|CONFIRMED: 9→36; Method 1|INVALIDATED: 99→72; Method 2|CONFIRMED: 10→20; Method 2|INVALIDATED: 185→175 |
| trend_mode=EMA5M_BASIC | RF | RF|CONFIRMED: 2→20; RF|INVALIDATED: 139→121 |
| trend_mode=STRUCTURE with swing_k=1 | ORB | Method 1|CONFIRMED: 9→15; Method 1|INVALIDATED: 99→93 |
| trend_mode=STRUCTURE with swing_k=1 | RF | no change |
| pin_bar=MODERATE (ratio style) | ORB | Gap/200DMA|CONFIRMED: 10→9; Gap/200DMA|INVALIDATED: 41→42; Method 1|CONFIRMED: 9→8; Method 1|INVALIDATED: 99→100 |
| pin_bar=MODERATE (ratio style) | PDS | Method 2|CONFIRMED: 1→0; Method 3|CONFIRMED: 14→15 |
| pin_bar=STRICT | ORB | Gap/200DMA|CONFIRMED: 10→9; Gap/200DMA|INVALIDATED: 41→42; Method 1|CONFIRMED: 9→7; Method 1|INVALIDATED: 99→101; Method 2|CONFIRMED: 10→8; Method 2|INVALIDATED: 185→187 |
| pin_bar=STRICT | PDS | Method 2|CONFIRMED: 1→0; Method 3|CONFIRMED: 14→15 |
| pin_bar=LOOSE | ORB | Gap/200DMA|CONFIRMED: 10→9; Gap/200DMA|INVALIDATED: 41→42; Method 1|CONFIRMED: 9→8; Method 1|INVALIDATED: 99→100; Method 2|CONFIRMED: 10→11; Method 2|INVALIDATED: 185→184 |
| pin_bar=LOOSE | PDS | no change |
| m3_compression_def=C3 (small candles: body <= 30% of range) | IRF | Method 3|INVALIDATED: 37→2 |
| m3_compression_def=C2 | IRF | Method 3|INVALIDATED: 37→33 |
| irf_support_def=SWING_K2 | IRF | Method 1/2|INCOMPLETE_AT_EOD: 130→132; Method 2A|CONFIRMED: 215→154; Method 2B|CONFIRMED: 310→296 |
| PDR zone_lower_boundary=ZONE_FULL | PDR | no change |
| PDR zone_proximity_points=5 (near-touch) | PDR | PDR|CONFIRMED: 61→64 |
| PDR pdr_zone_method=B_SWING_HIGH_REVERSAL | PDR | no change |
| PDR pdr_zone_method=C_REPEATED_TOUCHES | PDR | PDR|CONFIRMED: 61→32; PDR|INVALIDATED: 41→66 |
| PDS zone_proximity_points=5 (near-touch) | PDS | Method 1/2/3|INCOMPLETE_AT_EOD: 4→5; Method 1|CONFIRMED: 8→9 |
| PDS pds_zone_upper_boundary=ZONE_WICK | PDS | Method 1/2/3|INCOMPLETE_AT_EOD: 4→5; Method 1|CONFIRMED: 8→9; Method 3|CONFIRMED: 14→12 |
| PDS pds_zone_method=B_SWING_LOW_REVERSAL | PDS | Method 1/2/3|INCOMPLETE_AT_EOD: 4→3; Method 1/2/3|INVALIDATED: 61→27; Method 1|CONFIRMED: 8→16; Method 2|CONFIRMED: 1→4; Method 3|CONFIRMED: 14→18 |
| PDS pds_zone_method=C_REPEATED_TOUCHES | PDS | Method 1/2/3|INVALIDATED: 61→39; Method 1|CONFIRMED: 8→15; Method 2|CONFIRMED: 1→3; Method 3|CONFIRMED: 14→18 |
