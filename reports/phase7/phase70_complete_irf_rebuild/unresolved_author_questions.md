# Unresolved author questions (Phase 7.0)

None of these was answered by either PDF. Each implemented choice is labelled and (where it matters) run as a separate scenario. No choice is approved by the owner.

## Both methods
1. **Stop distance** - 35 or 40 points? The PDFs say 'about 35 to 40' and the examples show 35.2-40.75. Run as `SL35_T60` and `SL40_T60`.
2. **Entry price** - the failure candle's close (M1 TO CONFIRM; M2 silent) or the first executable price after it? Primary: open of the next one-minute bar; the close convention is run as `SL40_ENTRY_SIGNAL_CLOSE`.
3. **Exit clock** - M1: 'end of the session, time to be confirmed'; M2 row 'Latest entry time and exit time = 1 pm'. Primary: forced exit at the 15:14 bar open; `*_FORCED_EXIT_1300` scenarios test a 13:00 exit.
4. **Entry cutoff** - 'no entry after 1 pm': is a fill at exactly 13:00 allowed? Implemented inclusive (13:00:00 allowed), consistent with the repository's ENTRY-CUTOFF-001.
5. **Stop-vs-target in one candle** - SL first (M1, TO CONFIRM); M2 silent; the 5-minute-window reading is primary, chronological one-minute order is `SL40_TIE_MINUTE_ORDER`.
6. **Trades per day** - 1 (TO CONFIRM). Is the day finished after a stop-loss (M1 says so, TO CONFIRM), or may a later failure be traded? Later cycles are only counted.
7. **Priority when both methods fire** - not stated. Earliest signal; same instant -> Method 1 label (P&L unaffected).
8. **Exactly-equal closes** - ignored (TO CONFIRM in both).
9. **Setup expiry** - does an armed setup expire (time of day, distance, number of candles)? Neither PDF says so.

## Method 1
10. First-candle colour - no rule (TO CONFIRM). 11. Is there a minimum depth of the failure close below the level? (examples: 1.80-18.55 points) - none implemented.

## Method 2
12. Can the red rally-breakout candle itself be the first red candle? Primary no; variant `M2_ALT_BREAKOUT_RED` reported.
13. Must the rally stay above Level A until Level B breaks? Primary: no condition. 14. If price closes back below Level A (or below B) before the second breakout, is the setup dead? Primary: no (source silent).
15. Must the first red candle have its open above Level A? Not required here.
16. The orphan sentence '60 points in every case.' on page 5 - what did it qualify?
17. Page references to 'Open Items to Confirm' - the section is missing from both PDFs; please supply the list so TO CONFIRM items can be closed.
18. Undated screenshots (M1 Example 1 'Session marked 5', M2 Example 1) - please supply the dates; and the Nov 2026 data (11, 12, 16 Nov; 6 Nov) is not in any data store.
19. **M2 Example 4 (3 Nov 2026)**: on the secondary-vendor data the first close below Level B is the 10:00 candle (0.70 below B), but the screenshot's entry equals the close of the 10:05 candle. Is a minimum margin below B required, or is the author's failure candle simply the later one?
20. **M2 invalidation**: if price closes below Level A before the first red candle / Level B is marked (roughly a third of M2 rally sessions, `m2_rally_diagnostics.json`), is the setup dead? Primary keeps it armed; `SL40_M2_INVALIDATE_BELOW_A` is the alternative.
