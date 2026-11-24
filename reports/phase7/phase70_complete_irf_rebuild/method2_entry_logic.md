# IRF_V3_METHOD_2 - entry logic (from IRF_Method2_First_Red_Candle_Rulebook.pdf only)

```
S0 AWAIT_A_BREAKOUT : Level A = HIGH of the 09:15 candle (wick included). Each later candle at its END:
                        close > A  -> rally breakout (any colour)                                         [R03]
                        red candle (close < open) before that -> ignored, counted                          [R06]
S1 AWAIT_FIRST_RED  : the FIRST later candle with close < open sets Level B = its OPEN (top of body, wick ignored); later reds ignored   [R05, R07]
S2 AWAIT_B_BREAKOUT : a later candle with close > B -> second breakout, NO entry                          [R08]
S3 AWAIT_FAILURE    : a later candle with close < B -> FAILURE: SHORT signal at that candle's end         [R09, R11]
close == a level -> ignored (R13). Nothing invalidates an armed setup (R18 - source silent).
```
**Reading choices where the PDF can be read two ways (all disclosed in `rule_authority_registry.csv` / `unresolved_author_questions.md`):**
* *Breakout candle itself red?* Primary: NOT eligible ('first red candle AFTER the rally breakout'). The variant `M2_ALT_BREAKOUT_RED` (eligible) is run as a sensitivity - it changes -1 M2 trades across both windows (net of both windows).
* *Setup expiry:* none; a Level B set at 09:35 is still armed at 12:55.
* *Red candle that closes below Level A* can still set Level B (the PDF does not require the rally to be intact).

Execution is the same labelled scenario set as Method 1 (assumed, because the Method 2 text is silent on entry price, tie and exit).

**Rejection / no-trade reasons:** `NO_CLOSE_ABOVE_LEVEL_A`, `NO_RED_CANDLE_AFTER_RALLY_BREAKOUT`, `NO_CLOSE_ABOVE_LEVEL_B`, `SECOND_BREAKOUT_WITHOUT_FAILURE`, `SIGNAL_AFTER_CUTOFF`, `NOT_EVALUATED:<reason>`.
