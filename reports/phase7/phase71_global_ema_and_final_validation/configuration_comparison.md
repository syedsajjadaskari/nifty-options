# Configuration comparison (synthetic NIFTY index P&L; 6 lots x 65 = 390 units; neither window is untouched out-of-sample; NOTHING is selected)

Configurations are predeclared (`configuration_manifest.json`); each changes ONE declared dimension relative to **B** (IRF V3 + ORB V2-A + PDR/PDS first-eligible + RF) except A (the frozen Phase 3.6 combined configuration, reproduced exactly: window A 196 trades / Rs +297,765, window B 609 / Rs +509,398 = the saved Phase 6.2 'A'). A win = positive gross P&L of the WHOLE completed trade (two legs).

* **A** - A - existing frozen combined configuration (Phase 3.6 frozen engines; Phase 6.2 key A)
* **B** - B - IRF V3 (Method 1 + Method 2, Phase 7.0) + ORB V2-A + PDR/PDS first-eligible + RF; no universal EMA rule
* **C** - C - B with Method 2 invalidated permanently by a close below Level A before the sequence completes (M2-B)
* **C2** - C2 - B with Method 2 invalidation that RE-ARMS (a new rally breakout may start a new setup)
* **D** - D - B + universal EMA-1: minimum 27-point |close - EMA| (all five strategies)
* **E** - E - B + universal EMA-2: minimum 27-point candle-range clearance (all five strategies)
* **F** - F - B + universal EMA-3: maximum 27-point |close - EMA| proximity (all five strategies)
* **K** - K - B + EMA-4: 28-point candle-range clearance (Phase 5.3 historical convention, comparator; all five strategies)
* **L** - L - B + EMA-5: target-side (EMA not within 27 points in the trade's path; handwritten AC13/AC18 reading; all five strategies)
* **G1** - G1 - B with PDR-B1 (first green candle after the retest, no ceiling requirement; owner confirmation required)
* **G2** - G2 - B with PDR-B2 (first green candle, retest candle may confirm, no ceiling requirement)
* **G3** - G3 - B with PDR-C (first green candle closing above the zone ceiling, retest candle may confirm)
* **H** - H - B with PDR-D (second eligible confirmation)
* **I1** - I1 - B with the frozen numeric-threshold PDS (source-consistent reference)
* **I2** - I2 - B with PDS second confirmation (Methods 1/2 only)
* **J60** - J60 - B + candle-strength gate 60% body (Phase 6.5 variant B)
* **J70** - J70 - B + candle-strength gate 70% body (Phase 6.5 variant C)
* **JD** - JD - B + pattern-aware candle-strength gate (Phase 6.5 variant D)

## Portfolio performance

| cfg | win | trades | IRF | ORB | PDR | PDS | RF | win% | PF | gross pts | gross Rs | net Rs (70/trade) | max DD Rs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | A | 196 | 109 | 41 | 25 | 11 | 10 | 59.69 | 1.269 | 763.5 | 297765.0 | 284045.0 | 133450.0 |
| A | B | 609 | 328 | 101 | 106 | 27 | 47 | 57.8 | 1.136 | 1306.15 | 509398.0 | 466768.0 | 194503.0 |
| B | A | 190 | 93 | 39 | 31 | 18 | 9 | 58.42 | 1.212 | 594.5 | 231855.0 | 218555.0 | 107866.0 |
| B | B | 614 | 293 | 92 | 129 | 58 | 42 | 57.98 | 1.151 | 1449.17 | 565178.0 | 522198.0 | 316898.0 |
| C | A | 190 | 93 | 39 | 31 | 18 | 9 | 58.42 | 1.212 | 594.5 | 231855.0 | 218555.0 | 107866.0 |
| C | B | 614 | 293 | 92 | 129 | 58 | 42 | 57.98 | 1.151 | 1449.17 | 565178.0 | 522198.0 | 316898.0 |
| C2 | A | 190 | 93 | 39 | 31 | 18 | 9 | 58.42 | 1.212 | 594.5 | 231855.0 | 218555.0 | 107866.0 |
| C2 | B | 614 | 293 | 92 | 129 | 58 | 42 | 57.98 | 1.151 | 1449.17 | 565178.0 | 522198.0 | 316898.0 |
| D | A | 175 | 83 | 36 | 30 | 18 | 8 | 56.57 | 1.101 | 289.5 | 112905.0 | 100655.0 | 104421.0 |
| D | B | 543 | 256 | 81 | 122 | 47 | 37 | 57.83 | 1.127 | 1095.95 | 427420.0 | 389410.0 | 311826.0 |
| E | A | 145 | 78 | 21 | 27 | 13 | 6 | 55.86 | 1.05 | 135.5 | 52845.0 | 42695.0 | 124671.0 |
| E | B | 491 | 252 | 57 | 116 | 40 | 26 | 56.42 | 1.066 | 579.55 | 226024.0 | 191654.0 | 383163.0 |
| F | A | 33 | 22 | 3 | 3 | 4 | 1 | 72.73 | 2.38 | 429.0 | 167310.0 | 165000.0 | 39210.0 |
| F | B | 131 | 76 | 11 | 12 | 21 | 11 | 54.96 | 0.981 | -15.4 | -6006.0 | -15176.0 | 169387.0 |
| K | A | 143 | 77 | 21 | 27 | 12 | 6 | 55.94 | 1.047 | 127.0 | 49530.0 | 39520.0 | 124671.0 |
| K | B | 486 | 249 | 57 | 115 | 40 | 25 | 56.58 | 1.074 | 629.22 | 245398.0 | 211378.0 | 373134.0 |
| L | A | 184 | 88 | 39 | 31 | 17 | 9 | 57.61 | 1.168 | 473.0 | 184470.0 | 171590.0 | 116066.0 |
| L | B | 588 | 272 | 92 | 129 | 53 | 42 | 58.16 | 1.163 | 1484.15 | 578818.0 | 537658.0 | 322471.0 |
| G1 | A | 199 | 93 | 39 | 41 | 18 | 8 | 57.79 | 1.147 | 452.5 | 176475.0 | 162545.0 | 120906.0 |
| G1 | B | 638 | 293 | 92 | 161 | 58 | 34 | 58.93 | 1.193 | 1849.5 | 721305.0 | 676645.0 | 286408.0 |
| G2 | A | 197 | 93 | 37 | 41 | 18 | 8 | 57.36 | 1.153 | 469.5 | 183105.0 | 169315.0 | 107866.0 |
| G2 | B | 645 | 293 | 92 | 168 | 58 | 34 | 58.45 | 1.169 | 1668.07 | 650549.0 | 605399.0 | 309461.0 |
| G3 | A | 188 | 93 | 37 | 31 | 18 | 9 | 57.98 | 1.218 | 611.5 | 238485.0 | 225325.0 | 107866.0 |
| G3 | B | 617 | 293 | 92 | 133 | 58 | 41 | 57.7 | 1.138 | 1345.45 | 524725.0 | 481535.0 | 349387.0 |
| H | A | 190 | 93 | 39 | 31 | 18 | 9 | 55.79 | 1.102 | 323.55 | 126184.0 | 112884.0 | 124286.0 |
| H | B | 596 | 294 | 92 | 110 | 58 | 42 | 59.4 | 1.237 | 2055.67 | 801713.0 | 759993.0 | 228153.0 |
| I1 | A | 189 | 98 | 39 | 31 | 12 | 9 | 59.26 | 1.249 | 675.82 | 263572.0 | 250342.0 | 107866.0 |
| I1 | B | 609 | 311 | 92 | 129 | 35 | 42 | 57.47 | 1.133 | 1294.5 | 504855.0 | 462225.0 | 307027.0 |
| I2 | A | 186 | 100 | 39 | 31 | 7 | 9 | 60.22 | 1.285 | 738.27 | 287927.0 | 274907.0 | 107866.0 |
| I2 | B | 594 | 308 | 93 | 129 | 22 | 42 | 57.74 | 1.143 | 1340.1 | 522639.0 | 481059.0 | 306598.0 |
| J60 | A | 164 | 81 | 39 | 25 | 17 | 2 | 60.98 | 1.395 | 876.45 | 341815.0 | 330335.0 | 111891.0 |
| J60 | B | 547 | 263 | 92 | 109 | 49 | 34 | 56.86 | 1.123 | 1089.75 | 425002.0 | 386712.0 | 310961.0 |
| J70 | A | 154 | 75 | 39 | 23 | 17 | 0 | 57.14 | 1.173 | 411.15 | 160348.0 | 149568.0 | 130466.0 |
| J70 | B | 486 | 230 | 92 | 101 | 45 | 18 | 56.17 | 1.054 | 477.77 | 186332.0 | 152312.0 | 347774.0 |
| JD | A | 189 | 96 | 39 | 31 | 14 | 9 | 59.26 | 1.258 | 699.32 | 272737.0 | 259507.0 | 107866.0 |
| JD | B | 611 | 300 | 92 | 129 | 48 | 42 | 57.61 | 1.136 | 1320.5 | 514995.0 | 472225.0 | 316722.0 |

## Strategy-wise (trades, winners/losers/breakeven, win rate, profit factor)

| win | cfg | strategy | trades | W/L/BE | win% | PF |
|---|---|---|---|---|---|---|
| A | A | IRF | 109 | 60/49/0 | 55.05 | 0.972 |
| A | A | ORB | 41 | 27/14/0 | 65.85 | 1.816 |
| A | A | PDR | 25 | 16/9/0 | 64.0 | 1.773 |
| A | A | PDS | 11 | 8/3/0 | 72.73 | 2.93 |
| A | A | RF | 10 | 6/4/0 | 60.0 | 0.909 |
| A | B | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | B | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | B | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | B | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | B | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | C | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | C | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | C | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | C | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | C | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | C2 | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | C2 | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | C2 | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | C2 | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | C2 | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | D | IRF | 83 | 46/37/0 | 55.42 | 0.988 |
| A | D | ORB | 36 | 18/18/0 | 50.0 | 0.943 |
| A | D | PDR | 30 | 20/10/0 | 66.67 | 1.848 |
| A | D | PDS | 18 | 10/8/0 | 55.56 | 1.137 |
| A | D | RF | 8 | 5/3/0 | 62.5 | 0.802 |
| A | E | IRF | 78 | 42/36/0 | 53.85 | 0.904 |
| A | E | ORB | 21 | 11/10/0 | 52.38 | 1.021 |
| A | E | PDR | 27 | 16/11/0 | 59.26 | 1.36 |
| A | E | PDS | 13 | 8/5/0 | 61.54 | 1.484 |
| A | E | RF | 6 | 4/2/0 | 66.67 | 1.056 |
| A | F | IRF | 22 | 16/6/0 | 72.73 | 2.033 |
| A | F | ORB | 3 | 1/2/0 | 33.33 | 0.718 |
| A | F | PDR | 3 | 3/0/0 | 100.0 | inf |
| A | F | PDS | 4 | 3/1/0 | 75.0 | 4.121 |
| A | F | RF | 1 | 1/0/0 | 100.0 | inf |
| A | K | IRF | 77 | 41/36/0 | 53.25 | 0.869 |
| A | K | ORB | 21 | 11/10/0 | 52.38 | 1.021 |
| A | K | PDR | 27 | 16/11/0 | 59.26 | 1.36 |
| A | K | PDS | 12 | 8/4/0 | 66.67 | 1.854 |
| A | K | RF | 6 | 4/2/0 | 66.67 | 1.056 |
| A | L | IRF | 88 | 50/38/0 | 56.82 | 1.043 |
| A | L | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | L | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | L | PDS | 17 | 10/7/0 | 58.82 | 1.453 |
| A | L | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | G1 | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | G1 | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | G1 | PDR | 41 | 26/15/0 | 63.41 | 1.373 |
| A | G1 | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | G1 | RF | 8 | 5/3/0 | 62.5 | 0.802 |
| A | G2 | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | G2 | ORB | 37 | 17/20/0 | 45.95 | 0.887 |
| A | G2 | PDR | 41 | 26/15/0 | 63.41 | 1.445 |
| A | G2 | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | G2 | RF | 8 | 5/3/0 | 62.5 | 0.802 |
| A | G3 | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | G3 | ORB | 37 | 17/20/0 | 45.95 | 0.887 |
| A | G3 | PDR | 31 | 21/10/0 | 67.74 | 1.992 |
| A | G3 | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | G3 | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | H | IRF | 93 | 54/39/0 | 58.06 | 1.095 |
| A | H | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | H | PDR | 31 | 16/15/0 | 51.61 | 1.05 |
| A | H | PDS | 18 | 11/7/0 | 61.11 | 1.649 |
| A | H | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | I1 | IRF | 98 | 58/40/0 | 59.18 | 1.145 |
| A | I1 | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | I1 | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | I1 | PDS | 12 | 8/4/0 | 66.67 | 2.2 |
| A | I1 | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | I2 | IRF | 100 | 60/40/0 | 60.0 | 1.184 |
| A | I2 | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | I2 | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | I2 | PDS | 7 | 6/1/0 | 85.71 | 6.081 |
| A | I2 | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| A | J60 | IRF | 81 | 51/30/0 | 62.96 | 1.343 |
| A | J60 | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | J60 | PDR | 25 | 17/8/0 | 68.0 | 2.04 |
| A | J60 | PDS | 17 | 12/5/0 | 70.59 | 2.559 |
| A | J60 | RF | 2 | 1/1/0 | 50.0 | 0.293 |
| A | J70 | IRF | 75 | 41/34/0 | 54.67 | 0.905 |
| A | J70 | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | J70 | PDR | 23 | 16/7/0 | 69.57 | 2.139 |
| A | J70 | PDS | 17 | 12/5/0 | 70.59 | 2.559 |
| A | J70 | RF | 0 | 0/0/0 |  |  |
| A | JD | IRF | 96 | 57/39/0 | 59.38 | 1.167 |
| A | JD | ORB | 39 | 19/20/0 | 48.72 | 0.921 |
| A | JD | PDR | 31 | 21/10/0 | 67.74 | 1.879 |
| A | JD | PDS | 14 | 9/5/0 | 64.29 | 1.953 |
| A | JD | RF | 9 | 6/3/0 | 66.67 | 1.212 |
| B | A | IRF | 328 | 192/136/0 | 58.54 | 1.18 |
| B | A | ORB | 101 | 58/43/0 | 57.43 | 1.2 |
| B | A | PDR | 106 | 54/52/0 | 50.94 | 0.852 |
| B | A | PDS | 27 | 18/9/0 | 66.67 | 1.661 |
| B | A | RF | 47 | 30/17/0 | 63.83 | 1.235 |
| B | B | IRF | 293 | 176/117/0 | 60.07 | 1.27 |
| B | B | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | B | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | B | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | B | RF | 42 | 27/15/0 | 64.29 | 1.278 |
| B | C | IRF | 293 | 176/117/0 | 60.07 | 1.27 |
| B | C | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | C | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | C | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | C | RF | 42 | 27/15/0 | 64.29 | 1.278 |
| B | C2 | IRF | 293 | 176/117/0 | 60.07 | 1.27 |
| B | C2 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | C2 | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | C2 | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | C2 | RF | 42 | 27/15/0 | 64.29 | 1.278 |
| B | D | IRF | 256 | 152/104/0 | 59.38 | 1.206 |
| B | D | ORB | 81 | 49/32/0 | 60.49 | 1.453 |
| B | D | PDR | 122 | 60/62/0 | 49.18 | 0.787 |
| B | D | PDS | 47 | 26/21/0 | 55.32 | 0.94 |
| B | D | RF | 37 | 27/10/0 | 72.97 | 1.918 |
| B | E | IRF | 252 | 144/108/0 | 57.14 | 1.122 |
| B | E | ORB | 57 | 34/23/0 | 59.65 | 1.323 |
| B | E | PDR | 116 | 56/60/0 | 48.28 | 0.74 |
| B | E | PDS | 40 | 23/17/0 | 57.5 | 1.109 |
| B | E | RF | 26 | 20/6/0 | 76.92 | 2.385 |
| B | F | IRF | 76 | 44/32/0 | 57.89 | 1.113 |
| B | F | ORB | 11 | 7/4/0 | 63.64 | 2.083 |
| B | F | PDR | 12 | 7/5/0 | 58.33 | 1.367 |
| B | F | PDS | 21 | 11/10/0 | 52.38 | 0.754 |
| B | F | RF | 11 | 3/8/0 | 27.27 | 0.11 |
| B | K | IRF | 249 | 144/105/0 | 57.83 | 1.154 |
| B | K | ORB | 57 | 34/23/0 | 59.65 | 1.323 |
| B | K | PDR | 115 | 55/60/0 | 47.83 | 0.718 |
| B | K | PDS | 40 | 23/17/0 | 57.5 | 1.109 |
| B | K | RF | 25 | 19/6/0 | 76.0 | 2.336 |
| B | L | IRF | 272 | 164/108/0 | 60.29 | 1.29 |
| B | L | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | L | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | L | PDS | 53 | 30/23/0 | 56.6 | 1.003 |
| B | L | RF | 42 | 28/14/0 | 66.67 | 1.391 |
| B | G1 | IRF | 293 | 176/117/0 | 60.07 | 1.27 |
| B | G1 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | G1 | PDR | 161 | 89/72/0 | 55.28 | 0.968 |
| B | G1 | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | G1 | RF | 34 | 22/12/0 | 64.71 | 1.398 |
| B | G2 | IRF | 293 | 176/117/0 | 60.07 | 1.27 |
| B | G2 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | G2 | PDR | 168 | 90/78/0 | 53.57 | 0.904 |
| B | G2 | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | G2 | RF | 34 | 22/12/0 | 64.71 | 1.398 |
| B | G3 | IRF | 293 | 176/117/0 | 60.07 | 1.27 |
| B | G3 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | G3 | PDR | 133 | 65/68/0 | 48.87 | 0.771 |
| B | G3 | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | G3 | RF | 41 | 26/15/0 | 63.41 | 1.259 |
| B | H | IRF | 294 | 177/117/0 | 60.2 | 1.28 |
| B | H | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | H | PDR | 110 | 61/49/0 | 55.45 | 1.066 |
| B | H | PDS | 58 | 33/25/0 | 56.9 | 1.001 |
| B | H | RF | 42 | 27/15/0 | 64.29 | 1.278 |
| B | I1 | IRF | 311 | 182/129/0 | 58.52 | 1.179 |
| B | I1 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | I1 | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | I1 | PDS | 35 | 21/14/0 | 60.0 | 1.286 |
| B | I1 | RF | 42 | 27/15/0 | 64.29 | 1.278 |
| B | I2 | IRF | 308 | 182/126/0 | 59.09 | 1.215 |
| B | I2 | ORB | 93 | 57/36/0 | 61.29 | 1.551 |
| B | I2 | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | I2 | PDS | 22 | 13/9/0 | 59.09 | 1.024 |
| B | I2 | RF | 42 | 27/15/0 | 64.29 | 1.278 |
| B | J60 | IRF | 263 | 155/108/0 | 58.94 | 1.222 |
| B | J60 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | J60 | PDR | 109 | 50/59/0 | 45.87 | 0.724 |
| B | J60 | PDS | 49 | 27/22/0 | 55.1 | 0.972 |
| B | J60 | RF | 34 | 23/11/0 | 67.65 | 1.551 |
| B | J70 | IRF | 230 | 136/94/0 | 59.13 | 1.17 |
| B | J70 | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | J70 | PDR | 101 | 46/55/0 | 45.54 | 0.66 |
| B | J70 | PDS | 45 | 23/22/0 | 51.11 | 0.821 |
| B | J70 | RF | 18 | 12/6/0 | 66.67 | 1.368 |
| B | JD | IRF | 300 | 178/122/0 | 59.33 | 1.23 |
| B | JD | ORB | 92 | 56/36/0 | 60.87 | 1.511 |
| B | JD | PDR | 129 | 64/65/0 | 49.61 | 0.802 |
| B | JD | PDS | 48 | 27/21/0 | 56.25 | 0.993 |
| B | JD | RF | 42 | 27/15/0 | 64.29 | 1.278 |

## Cost / slippage sensitivity, configuration B (all configurations: `cost_sensitivity.csv`)
Window A:

| scenario | net_rs | net_win_rate_pct | profit_factor_net |
|---|---|---|---|
| GROSS | 231855.0 | 58.42 | 1.226 |
| C70_TRADE | 218555.0 | 58.42 | 1.212 |
| C70_FILL | 191955.0 | 58.42 | 1.184 |
| C70_S025 | 181505.0 | 58.42 | 1.173 |
| C70_S05 | 144455.0 | 58.42 | 1.136 |
| C70_S1 | 70355.0 | 58.42 | 1.064 |

Window B:

| scenario | net_rs | net_win_rate_pct | profit_factor_net |
|---|---|---|---|
| GROSS | 565178.0 | 57.98 | 1.164 |
| C70_TRADE | 522198.0 | 57.98 | 1.151 |
| C70_FILL | 436238.0 | 57.98 | 1.125 |
| C70_S025 | 402468.0 | 57.98 | 1.115 |
| C70_S05 | 282738.0 | 57.98 | 1.08 |
| C70_S1 | 43278.0 | 57.98 | 1.012 |

Indicative only: Rs 70 per completed trade, Rs 70 per fill, 0.25 / 0.5 / 1.0 point slippage per side on 390 units. Synthetic index P&L is **not** NIFTY futures or option P&L.

## Journal agreement (window A; 190 rows, one-to-one; strict = same date + strategy + time label == signal candle start; no exact match is possible - the journal has no direction or price)

| config | automated_trades | strict | time_tolerant | date_strategy_only | manual_only | automated_only | wrong_strategy_dates | outcome_label_agree_strict_tolerant |
|---|---|---|---|---|---|---|---|---|
| A | 196 | 66 | 21 | 18 | 85 | 91 | 61 | 80 |
| B | 190 | 71 | 22 | 13 | 84 | 84 | 53 | 81 |
| C | 190 | 71 | 22 | 13 | 84 | 84 | 53 | 81 |
| C2 | 190 | 71 | 22 | 13 | 84 | 84 | 53 | 81 |
| D | 175 | 68 | 14 | 13 | 95 | 80 | 51 | 72 |
| E | 145 | 49 | 12 | 12 | 117 | 72 | 51 | 53 |
| F | 33 | 4 | 10 | 3 | 173 | 16 | 11 | 10 |
| K | 143 | 49 | 12 | 12 | 117 | 70 | 50 | 53 |
| L | 184 | 73 | 15 | 15 | 87 | 81 | 51 | 77 |
| G1 | 199 | 71 | 21 | 13 | 85 | 94 | 55 | 80 |
| G2 | 197 | 70 | 20 | 13 | 87 | 94 | 55 | 78 |
| G3 | 188 | 70 | 21 | 13 | 86 | 84 | 53 | 79 |
| H | 190 | 67 | 26 | 13 | 84 | 84 | 53 | 80 |
| I1 | 189 | 72 | 23 | 15 | 80 | 79 | 50 | 82 |
| I2 | 186 | 72 | 24 | 16 | 78 | 74 | 48 | 83 |
| J60 | 164 | 63 | 13 | 15 | 99 | 73 | 48 | 70 |
| J70 | 154 | 61 | 10 | 15 | 104 | 68 | 46 | 62 |
| JD | 189 | 71 | 23 | 14 | 82 | 81 | 52 | 81 |

## Trade-set changes against B (attribution DIRECT vs PORTFOLIO in `trade_set_attribution.csv`)

| window | config | B_trades | config_trades | kept_identical | removed | added | removed_direct | added_direct | net_gross_change_rs |
|---|---|---|---|---|---|---|---|---|---|
| A | A | 190 | 196 | 113 | 77 | 83 | 75 | 76 | 65910.0 |
| A | C | 190 | 190 | 190 | 0 | 0 | 0 | 0 | 0.0 |
| A | C2 | 190 | 190 | 190 | 0 | 0 | 0 | 0 | 0.0 |
| A | D | 190 | 175 | 166 | 24 | 9 | 24 | 0 | -118950.0 |
| A | E | 190 | 145 | 137 | 53 | 8 | 53 | 0 | -179010.0 |
| A | F | 190 | 33 | 23 | 167 | 10 | 166 | 0 | -64545.0 |
| A | K | 190 | 143 | 135 | 55 | 8 | 55 | 0 | -182325.0 |
| A | L | 190 | 184 | 178 | 12 | 6 | 12 | 0 | -47385.0 |
| A | G1 | 190 | 199 | 178 | 12 | 21 | 6 | 21 | -55380.0 |
| A | G2 | 190 | 197 | 171 | 19 | 26 | 6 | 26 | -48750.0 |
| A | G3 | 190 | 188 | 182 | 8 | 6 | 6 | 5 | 6630.0 |
| A | H | 190 | 190 | 163 | 27 | 27 | 27 | 21 | -105671.0 |
| A | I1 | 190 | 189 | 181 | 9 | 8 | 9 | 2 | 31717.0 |
| A | I2 | 190 | 186 | 175 | 15 | 11 | 15 | 0 | 56072.0 |
| A | J60 | 190 | 164 | 128 | 62 | 36 | 62 | 0 | 109960.0 |
| A | J70 | 190 | 154 | 107 | 83 | 47 | 83 | 0 | -71507.0 |
| A | JD | 190 | 189 | 185 | 5 | 4 | 5 | 0 | 40882.0 |
| B | A | 614 | 609 | 363 | 251 | 246 | 242 | 222 | -55780.0 |
| B | C | 614 | 614 | 614 | 0 | 0 | 0 | 0 | 0.0 |
| B | C2 | 614 | 614 | 614 | 0 | 0 | 0 | 0 | 0.0 |
| B | D | 614 | 543 | 525 | 89 | 18 | 89 | 0 | -137758.0 |
| B | E | 614 | 491 | 457 | 157 | 34 | 157 | 0 | -339154.0 |
| B | F | 614 | 131 | 89 | 525 | 42 | 525 | 0 | -571184.0 |
| B | K | 614 | 486 | 453 | 161 | 33 | 161 | 0 | -319780.0 |
| B | L | 614 | 588 | 576 | 38 | 12 | 37 | 0 | 13640.0 |
| B | G1 | 614 | 638 | 540 | 74 | 98 | 47 | 96 | 156127.0 |
| B | G2 | 614 | 645 | 526 | 88 | 119 | 24 | 119 | 85371.0 |
| B | G3 | 614 | 617 | 585 | 29 | 32 | 24 | 31 | -40453.0 |
| B | H | 614 | 596 | 495 | 119 | 101 | 118 | 76 | 236535.0 |
| B | I1 | 614 | 609 | 581 | 33 | 28 | 33 | 8 | -60323.0 |
| B | I2 | 614 | 594 | 566 | 48 | 28 | 45 | 0 | -42539.0 |
| B | J60 | 614 | 547 | 439 | 175 | 108 | 173 | 0 | -140176.0 |
| B | J70 | 614 | 486 | 356 | 258 | 130 | 257 | 0 | -378846.0 |
| B | JD | 614 | 611 | 600 | 14 | 11 | 14 | 0 | -50183.0 |

## What changes source fidelity versus what only changes historical P&L
* **Fidelity (the rule is supported by a source):** B adopts the two new IRF PDFs exactly (replaces the Phase 6.1 IRF V2 whose EMA-28 / first-red-low rules the PDFs do not contain); journal strict matches rise from 67 (Phase 6.2 C, IRF V2) to 71 with no rule tuned to the journal. C/C2 (Method 2 invalidation) change **no portfolio trade** in either window (Method 1 or other strategies already own those days) - the question matters for standalone Method 2 (113 -> 53 first signals, window A), not for the portfolio.
* **Not fidelity - only P&L moves:** EMA-1/2/3/4 remove many profitable and unprofitable trades alike; EMA-5 (target-side, the only reading with a drawn example) removes 12 baseline trades and raises strict journal matches to 73, but this is not evidence the reading is right. PDR/PDS and candle-strength variants change trades because the rule is changed, not because a source says so; the journal helps only weakly (strict 67-72 for the PDR/PDS variants; J60/J70 lower).
* **J60 / J70 / JD wrap ALL five engines, including IRF V3.** The Phase 6.5 gate applies a body-strength test to any non-exempt directional confirmation, but the two IRF PDFs contain no body-size rule; IRF trades therefore fall under J60/J70 (window A IRF 81 and 75 vs 93). These rows measure the Phase 6.5 proposal, not a source rule.
* Gross P&L ranks are shown for completeness only; the two windows disagree in sign for some candidates (e.g. F: A +167,310 on 33 trades vs B -6,006 on 131 trades).
