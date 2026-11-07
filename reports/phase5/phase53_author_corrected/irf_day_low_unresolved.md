# IRF - 'should not activate at the day's low' (PENDING_OWNER_DEFINITION)

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

The statement is not located in the five guides (Phase 5.2 search of the text and the IRF reference charts) and its predicate is not unique. **Nothing is applied**; the previous behaviour is preserved. No final-session low is used: every reading uses only candles that had closed when the signal was confirmed (no look-ahead).

Measured on the 786 IRF signals of the author-corrected configuration (510 within 13:00):

| reading (none is a rule) | meaning | signals | within 13:00 |
|---|---|---|---|
| D1 | entry price at or below the running session low | 3 | 1 |
| D2 | the signal candle closes below the running low of earlier candles | 3 | 1 |
| D3 | closes on its own low and that is the running low | 0 | 0 |
| D4 | Target 1 (entry - 27) lies below the running low | 27 | 20 |
| D5 | entry within 28 points of the running low | 25 | 20 |
| D6 | running low already below the opening-range low (IRL) | 324 | 166 |
| D7 | an earlier candle already closed below IRL | 209 | 91 |
| D8 | entry below the previous day's low | 92 | 54 |
| IRL | entry already below the opening-range low | 3 | 1 |

Per signal (`irf_day_low_diagnostics.csv`): running session low at the signal time, signal candle low, proposed entry price, previous-day low, opening-range low, whether the entry has already broken the opening-range low, and the distance between the entry and the latest running low.

Handwritten: AC19 2025-11-12; G02 (general remark, no date); AC32 2025-12-11 (see `dated_author_corrections.csv`). D6 and D7 are the readings that reproduce AC19 ('entry is below days low').

**Owner decision O3:** which meaning (and where in the documents the rule is written), and whether the response is to skip the signal or to stop the day (AC19 says 'this day trading should be completely stopped').
