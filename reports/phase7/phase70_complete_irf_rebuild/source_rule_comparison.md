# Source-rule comparison: Method 1 vs Method 2

Both documents were read independently. Where they say the same thing it is recorded as a SIMILARITY; where only one speaks it is a DIFFERENCE or a SILENCE; where one reading of a shared row could be contradictory it is a CONFLICT. Method-specific definitions are preserved - no rule was borrowed across methods.

| Topic | Method 1 (IRF_Inverse_Retest_Failure_Rulebook.pdf) | Method 2 (IRF_Method2_First_Red_Candle_Rulebook.pdf) | Classification |
|---|---|---|---|
| Instrument / timeframe | Nifty 50 index, 5 min | same | similarity |
| First level | marked level = high of 09:15 candle incl. wick (p1,p3) | Level A = high of 09:15 candle incl. wick (p1,p3) | similarity (identical definition; each module computes it independently) |
| What must break | the first-candle high itself | Level B = body top (open) of the first red candle after the rally breakout | difference (core) |
| Breakout | any later candle (any colour) closes above the marked level | any later candle (any colour) closes above Level A (rally) AND later above Level B (second breakout) | difference (two breakouts in M2) |
| Failure | later close below the SAME marked level | later close below Level B | difference |
| Red candle | irrelevant | decisive (first red candle after the rally breakout); red candles before the breakout ignored (TO CONFIRM) | difference |
| Entry | after the failure candle closes; price = failure close (TO CONFIRM) | after the failure candle closes; price not stated | similarity + M2 silence |
| SL / target | entry +35..40 / entry -60 | entry +35..40 / entry -60 | similarity |
| Filters | none (no EMA200, S/R, gap, trend) | none (same list) | similarity |
| Trades per day | 1 (TO CONFIRM) | 1 (TO CONFIRM) | similarity |
| Latest entry / exit | row 'Latest entry time and exit time' prints 'No entry after 1 Pm' | same row prints '1 pm' | **CONFLICT / ambiguity**: M2's single value could also be an exit clock; M1 separately says the end-of-session exit time is to be confirmed. Preserved: entry cutoff 13:00 for both; a 13:00 forced exit is a labelled sensitivity |
| Tie SL/target in one candle | SL first (TO CONFIRM) | not stated | M2 silence - the M1 convention is applied to M2 as a flagged assumption |
| End-of-session exit | 'closed at end of session, time to be confirmed' | not stated | silence |
| Invalidation | none stated | none stated (order of steps only) | shared silence |
| Which method wins when both fire | not stated | not stated | shared silence - see `combined_irf_state_machine.md` |
| Colour of first candle | not restricted (TO CONFIRM) | examples include green and red first candles | similarity (no rule) |

**Implementation consequence:** `method1.py` and `method2.py` share no code. Both read the same candle list, but nothing of M2's red-candle/second-breakout logic exists in M1, and M1's single-level confirmation is not reused in M2.
