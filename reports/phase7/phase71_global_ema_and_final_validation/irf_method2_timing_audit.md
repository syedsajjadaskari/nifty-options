# IRF Method 2 entry timing - the 3 November 2026 discrepancy (Priority 2)

**Finding: the discrepancy is a data-feed effect, not a rule problem.** Phase 7.0 used the secondary vendor's feed (the only one then available for 3 Nov). The newly retrieved 5paisa feed reproduces the screenshot's sequence with the rule AS WRITTEN (any strict close below Level B):

| Feed | Level A (stated 23,611.15) | Level B (stated 23,621.90) | First candle closing below B | Close | Stated entry 23,612.80 |
|---|---|---|---|---|---|
| 5paisa (new) | 23,607.30 (-3.85) | 23,621.70 (-0.20) | **10:05-10:10** | 23,613.00 | **+0.20** |
| Secondary (Phase 7.0) | 23,610.70 (-0.45) | 23,621.70 (-0.20) | 10:00-10:05 | 23,621.00 | +8.20 |

On the 5paisa feed the 10:00-10:05 candle closes ABOVE Level B (see the raw rows in `november_3_raw_one_minute_rows.csv`), so the first strict close below B is the 10:05 candle, whose close matches the screenshot's entry to 0.20 points. On the secondary feed the 10:00 candle closes 0.70 below B, i.e. at a margin that vendor differences can erase. **Nothing was adjusted to force the match.**

## Timestamp conventions (candle open vs close)
* Both feeds label a one-minute row by its START (verified in Phase 2); a five-minute candle labelled 10:05 covers 10:05:00-10:10:00 and is usable at 10:10:00. A TradingView chart also labels a candle by its OPEN time, so 'the 10:00 candle' means 10:00-10:05. The screenshot's crosshair label ('03 Nov 26 10:50') and position box start (~10:05-10:10) are consistent with an entry at the close of the 10:05 candle.
* Distinguishing the timestamps: failure candle 10:05-10:10 (5paisa) -> confirmation/signal 10:10:00 -> first executable fill = open of the 10:10 one-minute bar. The screenshot's entry price (23,612.80) equals the failure candle's CLOSE (the rulebook's own TO-CONFIRM entry convention), 23,613.00 here; the Phase 7.0 fill convention (next open) differs from it by the 10:09->10:10 move.

## Close-below-B requirement candidates (diagnostics only; the original rule is preserved)
Nov-3 result of each candidate - 5paisa: {"strict close below B (rule as written)": "10:05-10:10 close 23613.00 (B 23621.70)", "margin >=1pt": "10:05-10:10 close 23613.00 (B 23621.70)", "margin >=2pt": "10:05-10:10 close 23613.00 (B 23621.70)", "margin >=5pt": "10:05-10:10 close 23613.00 (B 23621.70)", "failure candle must be red": "10:05-10:10 close 23613.00 (B 23621.70)", "extra confirming candle": "no signal"}; secondary: {"strict close below B (rule as written)": "10:00-10:05 close 23621.00 (B 23621.70)", "margin >=1pt": "10:05-10:10 close 23613.00 (B 23621.70)", "margin >=2pt": "10:05-10:10 close 23613.00 (B 23621.70)", "margin >=5pt": "10:05-10:10 close 23613.00 (B 23621.70)", "failure candle must be red": "10:00-10:05 close 23621.00 (B 23621.70)", "extra confirming candle": "10:05-10:10 close 23613.00 (B 23621.70)"}.
The only candidate that reproduces the screenshot on BOTH feeds is the 'extra confirming candle' (secondary feed); it removes the signal on the 5paisa feed. No candidate is supported by more than one screenshot, so none is adopted. Historical effect (window A, standalone SL40, `irf_method_comparison.csv`): margin>=1/2/5 points changes the Method 2 signal set marginally; 'extra candle' removes 9 of 86 trades; 'red failure candle' changes nothing.

| variant | trades | win_rate_pct | profit_factor | gross_points | journal_strict |
|---|---|---|---|---|---|
| M2-A (persistent; Phase 7.0 headline) | 86 | 38.37 | 0.9 | -202.45 | 14.0 |
| M2-B0 (Phase 7.0 sensitivity: close below A before Level B is marked; permanent) | 62 | 35.48 | 0.806 | -304.2 | 11.0 |
| M2-B (close below A before the sequence completes; permanent) | 43 | 32.56 | 0.688 | -354.6 | 11.0 |
| M2-B-REARM (same, a new rally breakout may start a new setup) | 87 | 37.93 | 0.859 | -299.1 | 12.0 |
| CAND margin>=1pt below B | 86 | 37.21 | 0.868 | -268.7 | 14.0 |
| CAND margin>=2pt below B | 86 | 36.05 | 0.864 | -278.35 | 15.0 |
| CAND margin>=5pt below B | 80 | 38.75 | 0.937 | -117.05 | 14.0 |
| CAND failure candle must be red | 86 | 38.37 | 0.9 | -202.45 | 14.0 |
| CAND extra confirming candle below B | 77 | 37.66 | 0.915 | -153.45 | 3.0 |
