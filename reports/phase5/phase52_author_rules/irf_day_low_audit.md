# IRF - 'not at the day's low' (investigation; diagnostics only)

Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

**Statement (call):** 'IRF should not be activated if it is at the day's low. This is already in the documents.'

## Source verification

Searched: the extracted text of the five strategy PDFs (IRF, ORB, PDR, PDS, RF) for day's low / day low / session low / lowest / intraday low, and the IRF reference chart pages (viewed). **The statement was not found.** The IRF guide uses the low only for marking the initial range (IRL) and for Method 3's recent support. The handwritten pages (Phase 5.1) contain it as the author's red-star remark (G02) and in AC19 / AC32. So the 'already in the documents' claim could not be verified; the rule is treated as an author statement whose meaning is open.

## Alternative meanings, measured at the decision time only

Computed with ONLY candles that had closed when the signal was confirmed (the running session low before the signal candle, and including it); the final daily low is never used (an audit check confirms the values and counts the signals where the final low differs from the running low, i.e. where a look-ahead implementation would have disagreed).

| reading (none is a rule) | meaning | all confirmed IRF signals | of which executed in Phase 3.6 | within the 13:00 cutoff | executed within cutoff |
|---|---|---|---|---|---|
| D1 | the entry price (next one-minute open) is at or below the running low | 3 | 0 | 3 | 0 |
| D2 | the signal candle CLOSES below the running low of the earlier candles (a short entered after the low has been broken) | 3 | 0 | 3 | 0 |
| D3 | the signal candle closes on its own low and that is the running low | 0 | 0 | 0 | 0 |
| D4 | Target 1 (entry - 27) lies below the running low: too close to the day's low to permit the first target | 28 | 1 | 20 | 1 |
| D5 | the entry is within 28 points of the running low | 26 | 1 | 18 | 1 |
| D6 | the session's running low (before the signal) is already below the initial range low (IRL): the day has already broken the opening range downwards | 352 | 35 | 184 | 35 |
| D7 | an earlier candle in the session already closed below IRL | 227 | 19 | 97 | 19 |
| D8 | the entry price is below the PREVIOUS day's low | 95 | 14 | 58 | 14 |

All counts include signals after the 13:00 cutoff (317 of 874 confirmed IRF signals are post-cutoff and not tradable); the cutoff columns show the tradable subset.

The readings are NOT equivalent: D1-D3 touch a handful of signals and no executed trade, D4 and D5 a few dozen, and D6 / D7 / D8 (added after review because AC19 reads 'entry is below days low') hundreds. Fields per signal (running low before / including the signal candle, signal candle low and close, entry level, distance to the running low, Target 1 clearance) are in `irf_signal_diagnostics.csv`.

## The dated handwritten examples

| date | correction | measurements |
|---|---|---|
| 2025-11-12 | AC19 | running_low_before_signal_candle=25781.25; entry_minus_running_low_before=66.25; t1_clearance_above_running_low=39.25; D1_entry_at_or_below_running_low=False; D2_close_below_running_low_before=False; D4_t1_beyond_running_low=False; irl=25805.4; D6_running_low_already_below_irl=True; D7_earlier_close_below_irl=True; previous_day_low=25450.85; D8_entry_below_previous_day_low=False |
|  | G02 | general remark (no date) |
| 2025-12-11 | AC32 | running_low_before_signal_candle=25727.9; entry_minus_running_low_before=59.39999999999782; t1_clearance_above_running_low=32.39999999999782; D1_entry_at_or_below_running_low=False; D2_close_below_running_low_before=False; D4_t1_beyond_running_low=False; irl=25727.9; D6_running_low_already_below_irl=False; D7_earlier_close_below_irl=False; previous_day_low=25734.9; D8_entry_below_previous_day_low=False |

AC19 (2025-11-12; the author's words: 'IRF is already activate[d] ... entry is below days low'): the executed trade is 66 points above the running low, so D1-D5 do NOT reproduce the remark. D6 and D7 do (the running low 25781.25 was already below the initial range low 25805.40 at the 10:05 signal): the remark is consistent with 'the day has already broken the opening range downwards'. AC32 (2025-12-11): the second candle closes below the running low (D2). Which reading is meant is an owner decision (O3).

## Conclusion and request

No rule is implemented: the brief requires an unambiguous source rejection condition, and none exists. **Owner decision O3:** which meaning, and where the rule is written in the documents.
