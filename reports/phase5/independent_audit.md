# Phase 5 - independent audit

`scripts/phase5_independent_audit.py` is a second implementation written from the raw provider files, their manifests, the broker's master copy and the delivered CSVs only (no `src/` imports; candle, EMA and exit-walk helpers come from the Phase 3.2 audit script, itself free of `src/` imports). Result: **ALL 144 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | [BANKNIFTY] the instrument is the BANKNIFTY INDEX: exactly one index row (code >= 999000) with that name on the right exchange and cash/index segment in the broker's master (hash-matched copy), equal to the mapping used for every request | 1 | PASS | scrip 999920005, exchange N; look-alike ETF / fund rows with the same name (not the index): 0 |
| 2 | [BANKNIFTY] daily closes stay in a plausible range for the index and the 2022-09-01 daily close agrees with the minute data of that day to within 400 points (identity sanity check) | 2391 | PASS | min 16,918 max 61,551 |
| 3 | [BANKNIFTY] every raw provider file equals the SHA-256 recorded at retrieval (secondary files also equal the repository's git blob SHA-1); licence MIT recorded | 96 | PASS | secondary commit 6bdda6e571 |
| 4 | [BANKNIFTY] every processed partition equals the SHA-256 in its source manifest | 196 | PASS |  |
| 5 | [BANKNIFTY] processed minute and daily data equal an independent reload of the raw files; Parquet compression is ZSTD | 1497743 | PASS | compression ['ZSTD'] |
| 6 | [BANKNIFTY] 5paisa minute rows: IST, at most one 15:30 stub row per session, a 09:15 bar on >95% of sessions (bar-START labels) | 452443 | PASS |  |
| 7 | [BANKNIFTY] closing-auction regime: the freeze pattern (15:16..15:26 flat) is absent before 2026-08-03 and present on >=90% of sessions from it, and the calendar applies the regime exactly then | 21 | PASS | before 0/44, from 21/21, applied True |
| 8 | [BANKNIFTY] the derived trading calendar equals an independent derivation (holidays and special sessions with their evaluable flag) | 150 | PASS | holidays 135 vs 135; special 15 vs 15 |
| 9 | [BANKNIFTY] holiday dates versus the NIFTY calendars (information: NSE vs BSE closures should agree) | 135 | PASS | 0 date(s) differ from the NIFTY derived/evidence calendars: [] |
| 10 | [BANKNIFTY] no trade falls on a derived holiday or on a non-evaluable special session | 1139 | PASS |  |
| 11 | [BANKNIFTY][M] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 820 trades) | 820 | PASS |  |
| 12 | [BANKNIFTY][M] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 820 | PASS |  |
| 13 | [BANKNIFTY][M] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 820 | PASS |  |
| 14 | [BANKNIFTY][M] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (3198 candles with an EMA) | 3198 | PASS |  |
| 15 | [BANKNIFTY][M] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 3198 | PASS |  |
| 16 | [BANKNIFTY][M] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 984 | PASS |  |
| 17 | [BANKNIFTY][M] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 761 | PASS | 13 conflict day(s) |
| 18 | [BANKNIFTY][M] all five strategies produced signals and were traded | 5 | PASS | signals {'IRF': 3399, 'RF': 95, 'ORB': 221, 'PDR': 409, 'PDS': 183}, trades {'IRF': 445, 'RF': 61, 'ORB': 147, 'PDR': 131, 'PDS': 36} |
| 19 | [BANKNIFTY][M] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 992 | PASS | expected 992 vs 992, in source 991 vs 991 |
| 20 | [BANKNIFTY][M] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 20 | 1401 | PASS |  |
| 21 | [BANKNIFTY][MS] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 328 trades) | 328 | PASS |  |
| 22 | [BANKNIFTY][MS] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 328 | PASS |  |
| 23 | [BANKNIFTY][MS] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 328 | PASS |  |
| 24 | [BANKNIFTY][MS] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (1310 candles with an EMA) | 1310 | PASS |  |
| 25 | [BANKNIFTY][MS] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 1310 | PASS |  |
| 26 | [BANKNIFTY][MS] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 385 | PASS |  |
| 27 | [BANKNIFTY][MS] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 296 | PASS | 10 conflict day(s) |
| 28 | [BANKNIFTY][MS] all five strategies produced signals and were traded | 5 | PASS | signals {'IRF': 1336, 'RF': 35, 'ORB': 77, 'PDR': 202, 'PDS': 78}, trades {'IRF': 179, 'RF': 22, 'ORB': 47, 'PDR': 68, 'PDS': 12} |
| 29 | [BANKNIFTY][MS] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 389 | PASS | expected 389 vs 389, in source 389 vs 389 |
| 30 | [BANKNIFTY][MS] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 30 | 1401 | PASS |  |
| 31 | [BANKNIFTY][C] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 194 trades) | 194 | PASS |  |
| 32 | [BANKNIFTY][C] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 194 | PASS |  |
| 33 | [BANKNIFTY][C] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 194 | PASS |  |
| 34 | [BANKNIFTY][C] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (736 candles with an EMA) | 736 | PASS |  |
| 35 | [BANKNIFTY][C] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 736 | PASS |  |
| 36 | [BANKNIFTY][C] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 244 | PASS |  |
| 37 | [BANKNIFTY][C] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 180 | PASS | 3 conflict day(s) |
| 38 | [BANKNIFTY][C] all five strategies produced signals (a strategy may have no first-valid-signal trade in a short window) | 5 | PASS | signals {'PDR': 75, 'IRF': 911, 'RF': 19, 'PDS': 43, 'ORB': 58}, trades {'PDR': 30, 'IRF': 109, 'RF': 11, 'PDS': 6, 'ORB': 38} |
| 39 | [BANKNIFTY][C] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 246 | PASS | expected 246 vs 246, in source 246 vs 246 |
| 40 | [BANKNIFTY][C] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 30 | 248 | PASS |  |
| 41 | [BANKNIFTY][D_5P] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 157 trades) | 157 | PASS |  |
| 42 | [BANKNIFTY][D_5P] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 157 | PASS |  |
| 43 | [BANKNIFTY][D_5P] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 157 | PASS |  |
| 44 | [BANKNIFTY][D_5P] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (593 candles with an EMA) | 606 | PASS |  |
| 45 | [BANKNIFTY][D_5P] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 606 | PASS |  |
| 46 | [BANKNIFTY][D_5P] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 195 | PASS |  |
| 47 | [BANKNIFTY][D_5P] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 145 | PASS | 3 conflict day(s) |
| 48 | [BANKNIFTY][D_5P] all five strategies produced signals (a strategy may have no first-valid-signal trade in a short window) | 5 | PASS | signals {'IRF': 710, 'PDR': 62, 'RF': 18, 'ORB': 53, 'PDS': 21}, trades {'IRF': 89, 'PDR': 17, 'RF': 13, 'ORB': 35, 'PDS': 3} |
| 49 | [BANKNIFTY][D_5P] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 201 | PASS | expected 201 vs 201, in source 196 vs 196 |
| 50 | [BANKNIFTY][D_5P] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 0 | 537 | PASS |  |
| 51 | [BANKNIFTY][D_TV] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 197 trades) | 197 | PASS |  |
| 52 | [BANKNIFTY][D_TV] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 197 | PASS |  |
| 53 | [BANKNIFTY][D_TV] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 197 | PASS |  |
| 54 | [BANKNIFTY][D_TV] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (750 candles with an EMA) | 750 | PASS |  |
| 55 | [BANKNIFTY][D_TV] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 750 | PASS |  |
| 56 | [BANKNIFTY][D_TV] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 243 | PASS |  |
| 57 | [BANKNIFTY][D_TV] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 187 | PASS | 3 conflict day(s) |
| 58 | [BANKNIFTY][D_TV] all five strategies produced signals (a strategy may have no first-valid-signal trade in a short window) | 5 | PASS | signals {'RF': 28, 'IRF': 879, 'PDR': 79, 'ORB': 69, 'PDS': 24}, trades {'IRF': 106, 'RF': 18, 'ORB': 47, 'PDS': 4, 'PDR': 22} |
| 59 | [BANKNIFTY][D_TV] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 244 | PASS | expected 244 vs 244, in source 244 vs 244 |
| 60 | [BANKNIFTY][D_TV] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 29 | 494 | PASS |  |
| 61 | [BANKNIFTY] annual_comparison.csv and strategy_performance.csv equal an independent recomputation for every row (trades, index points, drawdown, profit factor, win rate, outcomes, stop % of index, per-strategy points; points x 390 = rupees) | 10 | PASS |  |
| 62 | [BANKNIFTY] the four annual slices sum to the main window (trades, index points) | 4 | PASS |  |
| 63 | [BANKNIFTY] cost sensitivity (fill-level costs) recomputed independently for two periods x four scenarios | 8 | PASS |  |
| 64 | [BANKNIFTY] every trade of every window records index, minute-source id, daily-source id, partition SHA-256 (= the real file hash) and raw-file SHA-256; ids are unique; each trade has its chart and journal section; each evaluated session has a journal | 1696 | PASS |  |
| 65 | [BANKNIFTY] every journal ends with the option-feasibility block and contains NO option premium, strike, expiry or option P&L number (no invented option executions) | 2056 | PASS |  |
| 66 | [BANKNIFTY] journals carry the correct instrument label (no residual 'NIFTY 50' instrument phrase) | 2056 | PASS |  |
| 67 | [BANKNIFTY] no trade table has an option / premium / strike column | 5 | PASS |  |
| 68 | [BANKNIFTY] the verification workbook's main sheets equal the CSV files cell by cell | 143322 | PASS |  |
| 69 | [BANKNIFTY] the 2022-08..2026-04-22 vendor-overlap figures (bars compared, share identical, mean /close difference/) equal an independent recomputation | 343698 | PASS | bars 343,698; identical 0.4580; mean /diff/ 1.0141 |
| 70 | [SENSEX] the instrument is the SENSEX INDEX: exactly one index row (code >= 999000) with that name on the right exchange and cash/index segment in the broker's master (hash-matched copy), equal to the mapping used for every request | 1 | PASS | scrip 999901, exchange B; look-alike ETF / fund rows with the same name (not the index): 0 |
| 71 | [SENSEX] daily closes stay in a plausible range for the index and the 2022-09-01 daily close agrees with the minute data of that day to within 400 points (identity sanity check) | 2389 | PASS | min 25,981 max 85,836 |
| 72 | [SENSEX] every raw provider file equals the SHA-256 recorded at retrieval (secondary files also equal the repository's git blob SHA-1); licence MIT recorded | 96 | PASS | secondary commit e385abcde7 |
| 73 | [SENSEX] every processed partition equals the SHA-256 in its source manifest | 133 | PASS |  |
| 74 | [SENSEX] processed minute and daily data equal an independent reload of the raw files; Parquet compression is ZSTD | 1010934 | PASS | compression ['ZSTD'] |
| 75 | [SENSEX] 5paisa minute rows: IST, at most one 15:30 stub row per session, a 09:15 bar on >95% of sessions (bar-START labels) | 453597 | PASS |  |
| 76 | [SENSEX] closing-auction regime: the freeze pattern (15:16..15:26 flat) is absent before 2026-08-03 and present on >=90% of sessions from it, and the calendar applies the regime exactly then | 21 | PASS | before 0/44, from 21/21, applied True |
| 77 | [SENSEX] the derived trading calendar equals an independent derivation (holidays and special sessions with their evaluable flag) | 150 | PASS | holidays 134 vs 134; special 16 vs 16 |
| 78 | [SENSEX] holiday dates versus the NIFTY calendars (information: NSE vs BSE closures should agree) | 134 | PASS | 1 date(s) differ from the NIFTY derived/evidence calendars: ['2022-08-09'] |
| 79 | [SENSEX] no trade falls on a derived holiday or on a non-evaluable special session | 1091 | PASS |  |
| 80 | [SENSEX][M] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 821 trades) | 821 | PASS |  |
| 81 | [SENSEX][M] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 821 | PASS |  |
| 82 | [SENSEX][M] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 821 | PASS |  |
| 83 | [SENSEX][M] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (3195 candles with an EMA) | 3195 | PASS |  |
| 84 | [SENSEX][M] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 3195 | PASS |  |
| 85 | [SENSEX][M] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 982 | PASS |  |
| 86 | [SENSEX][M] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 755 | PASS | 10 conflict day(s) |
| 87 | [SENSEX][M] all five strategies produced signals and were traded | 5 | PASS | signals {'IRF': 3381, 'RF': 94, 'PDR': 361, 'PDS': 217, 'ORB': 184}, trades {'IRF': 444, 'RF': 65, 'PDR': 129, 'ORB': 127, 'PDS': 56} |
| 88 | [SENSEX][M] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 988 | PASS | expected 988 vs 988, in source 985 vs 985 |
| 89 | [SENSEX][M] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 20 | 1403 | PASS |  |
| 90 | [SENSEX][MS] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 326 trades) | 326 | PASS |  |
| 91 | [SENSEX][MS] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 326 | PASS |  |
| 92 | [SENSEX][MS] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 326 | PASS |  |
| 93 | [SENSEX][MS] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (1283 candles with an EMA) | 1283 | PASS |  |
| 94 | [SENSEX][MS] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 1283 | PASS |  |
| 95 | [SENSEX][MS] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 385 | PASS |  |
| 96 | [SENSEX][MS] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 298 | PASS | 4 conflict day(s) |
| 97 | [SENSEX][MS] all five strategies produced signals and were traded | 5 | PASS | signals {'IRF': 1321, 'RF': 36, 'PDS': 75, 'PDR': 166, 'ORB': 78}, trades {'IRF': 170, 'RF': 24, 'ORB': 56, 'PDS': 17, 'PDR': 59} |
| 98 | [SENSEX][MS] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 387 | PASS | expected 387 vs 387, in source 387 vs 387 |
| 99 | [SENSEX][MS] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 31 | 1403 | PASS |  |
| 100 | [SENSEX][C] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 151 trades) | 151 | PASS |  |
| 101 | [SENSEX][C] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 151 | PASS |  |
| 102 | [SENSEX][C] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 151 | PASS |  |
| 103 | [SENSEX][C] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (569 candles with an EMA) | 575 | PASS |  |
| 104 | [SENSEX][C] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 575 | PASS |  |
| 105 | [SENSEX][C] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 197 | PASS |  |
| 106 | [SENSEX][C] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 143 | PASS | 1 conflict day(s) |
| 107 | [SENSEX][C] all five strategies produced signals (a strategy may have no first-valid-signal trade in a short window) | 5 | PASS | signals {'IRF': 621, 'ORB': 49, 'PDR': 96, 'RF': 23, 'PDS': 16}, trades {'IRF': 75, 'ORB': 35, 'RF': 10, 'PDR': 31} |
| 108 | [SENSEX][C] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 246 | PASS | expected 246 vs 246, in source 200 vs 200 |
| 109 | [SENSEX][C] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 0 | 248 | PASS |  |
| 110 | [SENSEX][D_5P] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 170 trades) | 170 | PASS |  |
| 111 | [SENSEX][D_5P] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 170 | PASS |  |
| 112 | [SENSEX][D_5P] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 170 | PASS |  |
| 113 | [SENSEX][D_5P] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (646 candles with an EMA) | 655 | PASS |  |
| 114 | [SENSEX][D_5P] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 655 | PASS |  |
| 115 | [SENSEX][D_5P] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 200 | PASS |  |
| 116 | [SENSEX][D_5P] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 157 | PASS | 1 conflict day(s) |
| 117 | [SENSEX][D_5P] all five strategies produced signals (a strategy may have no first-valid-signal trade in a short window) | 5 | PASS | signals {'IRF': 680, 'PDR': 122, 'RF': 27, 'ORB': 57, 'PDS': 12}, trades {'IRF': 82, 'PDR': 29, 'ORB': 40, 'RF': 17, 'PDS': 2} |
| 118 | [SENSEX][D_5P] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 202 | PASS | expected 202 vs 202, in source 201 vs 201 |
| 119 | [SENSEX][D_5P] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 0 | 537 | PASS |  |
| 120 | [SENSEX][D_TV] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all 191 trades) | 191 | PASS |  |
| 121 | [SENSEX][D_TV] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 191 | PASS |  |
| 122 | [SENSEX][D_TV] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled) | 191 | PASS |  |
| 123 | [SENSEX][D_TV] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (738 candles with an EMA) | 738 | PASS |  |
| 124 | [SENSEX][D_TV] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 738 | PASS |  |
| 125 | [SENSEX][D_TV] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation | 234 | PASS |  |
| 126 | [SENSEX][D_TV] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 177 | PASS | 1 conflict day(s) |
| 127 | [SENSEX][D_TV] all five strategies produced signals (a strategy may have no first-valid-signal trade in a short window) | 5 | PASS | signals {'RF': 31, 'IRF': 752, 'PDR': 131, 'ORB': 60, 'PDS': 12}, trades {'RF': 20, 'IRF': 94, 'PDR': 34, 'ORB': 42, 'PDS': 1} |
| 128 | [SENSEX][D_TV] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 245 | PASS | expected 245 vs 245, in source 245 vs 245 |
| 129 | [SENSEX][D_TV] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: 29 | 494 | PASS |  |
| 130 | [SENSEX] annual_comparison.csv and strategy_performance.csv equal an independent recomputation for every row (trades, index points, drawdown, profit factor, win rate, outcomes, stop % of index, per-strategy points; points x 390 = rupees) | 10 | PASS |  |
| 131 | [SENSEX] the four annual slices sum to the main window (trades, index points) | 4 | PASS |  |
| 132 | [SENSEX] cost sensitivity (fill-level costs) recomputed independently for two periods x four scenarios | 8 | PASS |  |
| 133 | [SENSEX] every trade of every window records index, minute-source id, daily-source id, partition SHA-256 (= the real file hash) and raw-file SHA-256; ids are unique; each trade has its chart and journal section; each evaluated session has a journal | 1659 | PASS |  |
| 134 | [SENSEX] every journal ends with the option-feasibility block and contains NO option premium, strike, expiry or option P&L number (no invented option executions) | 2003 | PASS |  |
| 135 | [SENSEX] journals carry the correct instrument label (no residual 'NIFTY 50' instrument phrase) | 2003 | PASS |  |
| 136 | [SENSEX] no trade table has an option / premium / strike column | 5 | PASS |  |
| 137 | [SENSEX] the verification workbook's main sheets equal the CSV files cell by cell | 140278 | PASS |  |
| 138 | [SENSEX] the 2022-08..2024-03-22 vendor-overlap figures (bars compared, share identical, mean /close difference/) equal an independent recomputation | 151931 | PASS | bars 151,931; identical 0.7770; mean /diff/ 0.3141 |
| 139 | every file of the before-snapshot (all git-tracked files incl. strategies, controller, execution, framework, tests, docs; data/processed/nifty50*; data/phase4; data/raw/phase4_*; reports/phase3; reports/phase4) is byte-identical | 6659 | PASS | snapshot of git head 9cada7fcd0 |
| 140 | no file was added inside any NIFTY data or earlier-report directory | 6441 | PASS |  |
| 141 | every strategy, controller, execution, session-construction and framework file hashed in the Phase 4 freeze is unchanged | 26 | PASS | FROZEN-PHASE36-42cea2600bd4 |
| 142 | configuration_snapshot.json records the frozen id, equal active-file hashes and the stop / target / cutoff values of the brief | 1 | PASS |  |
| 143 | the NIFTY main-window reference in the comparison (Phase 4 window B + the unchanged Phase 3.6 window A) equals an independent sum of those trade tables | 805 | PASS | 805 trades, 2,069.65 index points |
| 144 | option-data availability claims are backed by the saved probe: the master lists no expired contract and no returned candle has a bid, ask or open-interest column | 50 | PASS |  |

**Independence caveat.** The audit script is a second implementation, but it was written by the same author as the pipeline; unlike Phase 4, no separate fresh-reviewer pass was run in this phase. Two genuine defects were found by it and fixed before delivery: (1) a vendor defect in one source (SENSEX 5paisa, 2023-10-19, missing 09:15-09:18) had made the date a 'special session' for the other source's run, and (2) the secondary-source partitions did not record their raw file hash on each trade.

## What this does and does not prove

* Every trade of every window was re-walked from the raw one-minute bars: entry price, stop-before-target ordering, gap fills, partial exit at T1, the post-T1 stop at entry -/+ 6, T2, the 15:14 forced exit, and the index-point P&L. The trade tables, exit tables, annual tables and workbooks agree with that recomputation.
* The 5-minute candles and EMA(200) quoted in the explanations equal an independent aggregation and a causal recomputation; no explanation candle ends after its signal.
* The controller rules hold on the delivered signal tables, with 'no fillable bar' rejections checked against the raw rows.
* Signal DETECTION by the five strategy engines is the frozen Phase 2-3.6 code (hash-verified); it was not re-implemented a second time here. Its correctness on NIFTY was reviewed in Phases 3.3-3.6 and its unchanged hash is what carries it to the new indices. The sample table below shows representative executed trades per strategy and index for human review.
* NIFTY is untouched: every git-tracked file, NIFTY data, earlier report and the Phase 4 freeze equal the before-snapshot taken before any Phase 5 output existed.
* Option claims: no journal or table contains an option premium, strike or option P&L (checked by pattern), and the availability statements are backed by the saved probe file.

## Tests and lint

* `pytest -q`: **636 passed, 1 skipped (full suite, pytest -q)**
* `ruff check src tests scripts`: **ruff check src tests scripts: All checks passed**

# Sample review of executed trades (every index, every strategy)

Three trades per strategy per index from the main window, re-derived from the raw bars by `scripts/phase5_independent_audit.py`: entry price, stop / T1 / T2 levels, the independently walked outcome, exit times and index points (each equals the delivered trade table; the audit fails otherwise). The signal-candle column shows the delivered explanation candle (open/high/low/close) and the 5-minute EMA(200) that were separately re-aggregated from the raw rows.

| index | strategy | trade | direction | signal at | entry | outcome | leg exits | weighted index points | signal candle o/h/l/c | EMA200 (5m) | levels |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BANKNIFTY | IRF | 20220901-1-IRF | SHORT | 2022-09-01 10:40 | 39472.75 | INITIAL_FULL_STOP | 10:40/10:40 | -35.00 | 39592.55/39592.55/39452.45/39475.75 | 38977.764 | stop 39507.75, T1 39445.75, T2 39412.75 |
| BANKNIFTY | IRF | 20240108-1-IRF | SHORT | 2024-01-08 09:30 | 48038.25 | TARGET | 09:34/09:40 | +43.50 | 48136.95/48141.85/48034.35/48036.95 | 48048.6847 | stop 48073.25, T1 48011.25, T2 47978.25 |
| BANKNIFTY | IRF | 20250424-1-IRF | SHORT | 2025-04-24 09:45 | 55277.10 | T1_THEN_BUFFER_STOP | 09:45/09:45 | +10.50 | 55438.55/55438.55/55276.3/55276.55 | 55220.1255 | stop 55312.10, T1 55250.10, T2 55217.10 |
| BANKNIFTY | ORB | 20220905-1-ORB | LONG | 2022-09-05 09:20 | 39670.30 | INITIAL_FULL_STOP | 09:21/09:21 | -30.00 | 39412.05/39670.25/39412.05/39667.9 | 39274.0852 | stop 39640.30, T1 39697.30, T2 39730.30 |
| BANKNIFTY | ORB | 20240102-1-ORB | SHORT | 2024-01-02 09:20 | 48084.75 | INITIAL_FULL_STOP | 09:21/09:21 | -30.00 | 48194.8/48194.8/48069.4/48085.6 | 48264.7163 | stop 48114.75, T1 48057.75, T2 48024.75 |
| BANKNIFTY | ORB | 20250317-1-ORB | LONG | 2025-03-17 09:20 | 48310.70 | INITIAL_FULL_STOP | 09:23/09:23 | -30.00 | 48223.35/48317.7/48210.1/48313.1 | 48131.856 | stop 48280.70, T1 48337.70, T2 48370.70 |
| BANKNIFTY | PDR | 20220906-1-PDR | LONG | 2022-09-06 11:45 | 39852.85 | TARGET | 11:55/11:58 | +48.50 | 39802.25/39852.5/39797.8/39851.95 | 39599.0552 | stop 39817.85, T1 39879.85, T2 39922.85 |
| BANKNIFTY | PDR | 20230928-1-PDR | LONG | 2023-09-28 10:10 | 44707.25 | INITIAL_FULL_STOP | 10:10/10:10 | -35.00 | 44643.8/44717.45/44623.9/44705.7 | 44600.8779 | stop 44672.25, T1 44734.25, T2 44777.25 |
| BANKNIFTY | PDR | 20250404-1-PDR | LONG | 2025-04-04 09:35 | 51846.75 | INITIAL_FULL_STOP | 09:35/09:35 | -35.00 | 51603.35/51844.35/51570.2/51844.35 | 51376.2595 | stop 51811.75, T1 51873.75, T2 51916.75 |
| BANKNIFTY | PDS | 20220928-2-PDS | SHORT | 2022-09-28 10:00 | 38162.95 | T1_THEN_BUFFER_STOP | 10:00/10:01 | +10.50 | 38188.15/38257.6/38161.15/38167.05 | 38903.0911 | stop 38197.95, T1 38135.95, T2 38092.95 |
| BANKNIFTY | PDS | 20240124-2-PDS | SHORT | 2024-01-24 12:05 | 44756.30 | T1_THEN_BUFFER_STOP | 12:05/12:06 | +10.50 | 44931.7/44942.1/44748.6/44764.65 | 45537.4054 | stop 44791.30, T1 44729.30, T2 44686.30 |
| BANKNIFTY | PDS | 20250804-1-PDS | SHORT | 2025-08-04 09:45 | 55536.40 | TARGET | 09:45/09:48 | +48.50 | 55664.6/55664.6/55536.4/55536.4 | 55952.1888 | stop 55571.40, T1 55509.40, T2 55466.40 |
| BANKNIFTY | RF | 20220902-1-RF | LONG | 2022-09-02 12:20 | 39376.90 | T1_THEN_BUFFER_STOP | 12:25/12:38 | +10.50 | 39422.3/39594.4/39373.15/39433.15 | 39141.6091 | stop 39341.90, T1 39403.90, T2 39436.90 |
| BANKNIFTY | RF | 20240215-1-RF | LONG | 2024-02-15 10:25 | 45909.75 | INITIAL_FULL_STOP | 10:29/10:29 | -35.00 | 46059.95/46076.95/45883.65/45950.7 | 45436.4199 | stop 45874.75, T1 45936.75, T2 45969.75 |
| BANKNIFTY | RF | 20250515-1-RF | LONG | 2025-05-15 10:35 | 54654.15 | T1_THEN_BUFFER_STOP | 10:36/10:36 | +10.50 | 54853.7/54906.2/54634.65/54687.2 | 54839.8285 | stop 54619.15, T1 54681.15, T2 54714.15 |
| SENSEX | IRF | 20220901-1-IRF | SHORT | 2022-09-01 10:40 | 59094.07 | INITIAL_FULL_STOP | 10:41/10:41 | -35.00 | 59206.6/59208.01/59081.07/59094.48 | 58814.7902 | stop 59129.07, T1 59067.07, T2 59034.07 |
| SENSEX | IRF | 20240118-1-IRF | SHORT | 2024-01-18 10:55 | 71173.06 | T1_THEN_BUFFER_STOP | 10:55/10:56 | +10.50 | 71211.77/71237.93/71165.9/71173.95 | 72126.0384 | stop 71208.06, T1 71146.06, T2 71113.06 |
| SENSEX | IRF | 20250424-1-IRF | SHORT | 2025-04-24 09:40 | 79999.30 | TARGET | 09:40/09:40 | +43.50 | 80073.55/80169.89/79981.8/79993.75 | 79517.9433 | stop 80034.30, T1 79972.30, T2 79939.30 |
| SENSEX | ORB | 20220912-1-ORB | LONG | 2022-09-12 09:20 | 60096.65 | INITIAL_FULL_STOP | 09:20/09:20 | -30.00 | 59912.29/60111.38/59912.29/60093.5 | 59607.8815 | stop 60066.65, T1 60123.65, T2 60156.65 |
| SENSEX | ORB | 20231010-1-ORB | LONG | 2023-10-10 09:20 | 65824.19 | INITIAL_FULL_STOP | 09:22/09:22 | -30.00 | 65703.16/65848.91/65703.16/65823.44 | 65668.2047 | stop 65794.19, T1 65851.19, T2 65884.19 |
| SENSEX | ORB | 20250512-1-ORB | LONG | 2025-05-12 09:20 | 81256.88 | TARGET | 09:20/09:20 | +43.50 | 80803.8/81265.99/80658.0/81262.3 | 80056.7963 | stop 81226.88, T1 81283.88, T2 81316.88 |
| SENSEX | PDR | 20220906-1-PDR | LONG | 2022-09-06 12:00 | 59330.86 | T1_THEN_BUFFER_STOP | 12:01/12:03 | +10.50 | 59265.53/59337.33/59258.32/59327.8 | 59083.152 | stop 59295.86, T1 59357.86, T2 59400.86 |
| SENSEX | PDR | 20240111-2-PDR | LONG | 2024-01-11 11:00 | 71771.42 | T1_THEN_BUFFER_STOP | 11:45/12:00 | +10.50 | 71706.88/71773.6/71689.53/71772.12 | 71626.1793 | stop 71736.42, T1 71798.42, T2 71841.42 |
| SENSEX | PDR | 20250306-2-PDR | LONG | 2025-03-06 12:05 | 73960.33 | INITIAL_FULL_STOP | 12:06/12:06 | -35.00 | 73875.57/73964.04/73875.57/73959.84 | 73553.1002 | stop 73925.33, T1 73987.33, T2 74030.33 |
| SENSEX | PDS | 20220921-1-PDS | SHORT | 2022-09-21 09:40 | 59685.54 | TARGET | 09:43/09:45 | +48.50 | 59767.69/59772.01/59669.05/59685.76 | 59664.0802 | stop 59720.54, T1 59658.54, T2 59615.54 |
| SENSEX | PDS | 20240906-1-PDS | SHORT | 2024-09-06 09:40 | 81941.27 | TARGET | 09:40/09:41 | +48.50 | 82195.41/82203.78/81830.7/81940.09 | 82276.7808 | stop 81976.27, T1 81914.27, T2 81871.27 |
| SENSEX | PDS | 20251103-2-PDS | SHORT | 2025-11-03 12:10 | 83834.74 | T1_THEN_BUFFER_STOP | 12:14/12:18 | +10.50 | 83872.54/83888.65/83835.42/83836.02 | 84242.4828 | stop 83869.74, T1 83807.74, T2 83764.74 |
| SENSEX | RF | 20220902-1-RF | LONG | 2022-09-02 13:00 | 58898.63 | T1_THEN_BUFFER_STOP | 13:01/13:04 | +10.50 | 58969.02/59104.53/58895.42/58907.66 | 58842.3949 | stop 58863.63, T1 58925.63, T2 58958.63 |
| SENSEX | RF | 20240426-1-RF | LONG | 2024-04-26 09:40 | 74448.71 | INITIAL_FULL_STOP | 09:44/09:44 | -35.00 | 74509.31/74509.31/74375.25/74411.61 | 73939.8201 | stop 74413.71, T1 74475.71, T2 74508.71 |
| SENSEX | RF | 20250102-1-RF | LONG | 2025-01-02 09:35 | 78658.86 | TARGET | 09:37/09:37 | +43.50 | 78657.52/78749.22/78615.79/78666.44 | 78385.9947 | stop 78623.86, T1 78685.86, T2 78718.86 |



