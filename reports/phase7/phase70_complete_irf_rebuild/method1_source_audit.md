# Method 1 source audit - IRF_Inverse_Retest_Failure_Rulebook.pdf

Source: `docs/strategy_docs/IRF_Inverse_Retest_Failure_Rulebook.pdf` (untracked in Git, read only, 8 pages, 4 embedded images). Every page was rendered and viewed; every embedded image was extracted at original resolution to `source_extracts/` (`m1_p4_img1.png`, `m1_p6_img1.png`, `m1_p7_img1.png`, `m1_p7_img2.png`).

**Document-level findings**
* The document says rules are marked CONFIRMED or TO CONFIRM and that all TO CONFIRM items are collected in a section 'Open Items to Confirm'. **No such section exists in the 8 pages, and no rule carries an explicit CONFIRMED tag.** Authority classes used here: `STATED` (printed without a TO CONFIRM tag), `TO_CONFIRM` (explicit tag), `SOURCE_SILENT`, `EXAMPLE_ONLY` (see `rule_authority_registry.csv`).
* Prices read from the screenshots are, by the document's own statement, approximate.

| Page | Content | Rules / facts captured (rule id) |
|---|---|---|
| 1 | Summary tiles (SHORT, SL 35-40, target 60, 5 min); how-to-read box; overview table | Nifty 50 index, 5-min (R01); level = first-candle high incl. wick (R02); breakout = any later candle closing above (R03); failure = later close below (R05); entry after the failure candle closes (R07); SL ~35-40 above entry (R12); target 60 below (R13); no trend restriction (R08); 1 trade/day; no entry after 1 pm (R16). Header row 'Latest entry time and exit time' prints only 'No entry after 1 Pm' (R18) |
| 2 | Core principle; 'What IRF does not use' | No EMA(200), no previous-day S/R, no gap filter, price may be above or below the 200 EMA (R08) |
| 3 | Marking the level; the 6-step sequence | First candle 09:15-09:20; level = high incl. wick, marked once, never moves (R02). Example candle O25000 H25035 L24996 C25020 (green) -> level 25,035 not 25,020. Colour of the first candle: TO CONFIRM (R09). Candle that merely wicks above and closes at/below is not a breakout (R03). The failure may come right after the breakout or many candles later (R05) |
| 4 | **Figure 1** (drawn illustration: green first candle, two greens closing above 25,035, red failure candle, 3 red follow-through candles; SL 25,070 (entry+40) / 25,065 (35); target 24,970; entry 25,030 'an illustration') + 'Order matters' | Both closes needed, in order; a close below with no earlier close above is not a signal (R06) |
| 5 | 'What counts' table; entry/SL/TP table; worked example; bullets | Close exactly on the level ignored: TO CONFIRM (R10). Entry price E = close of the failure candle: TO CONFIRM (R11). SL E+35..40, target E-60, risk-reward 1:1.5 (40) / ~1:1.7 (35) (R12, R13). SL/TP measured from the entry, not the level. One trade/day, strategy finished after SL or target: TO CONFIRM (R14). SL and target both inside one 5-minute candle -> SL first: TO CONFIRM (R15). Not hit -> closed at end of session, exit time to be confirmed (R17). Worked example: level 25,035; close 25,048 (breakout); close 25,030 (failure); entry 25,030; SL 25,065-25,070; TP 24,970 |
| 6 | Chart-example table + **Screenshot 1** ('Session marked 5', stop-loss hit) | Level 24,391.80; entry 24,373.25 (18.55 below the level); SL 24,408.50 (35.25); TP 24,314.00 (59.25). **No date.** The text says price rose to ~24,430 and the SL was hit near the end of the box |
| 7 | **Screenshot 2** (11 Nov 2026, target hit +60.50, RR 1.48) and **Screenshot 3** (16 Nov 2026, target hit) | Ex 2: level 'about 25,377.5'; entry 25,363.90; SL 25,404.65 (40.75); TP 25,303.40 (60.50); failure candle 'around 9:55'. Ex 3: level 25,301.55; entry 25,299.75 (1.80 below); SL 25,340.45 (40.70); TP 25,239.10 (60.65); failure 'around 10:00' |
| 8 | Rule matrix | Restates R02, R03, R05, R07, R12, R13, R08, trades/day 1 (TO CONFIRM) |

**What the document does NOT specify:** a rule for choosing 35 vs 40 points; the exit clock; whether a trade may follow a stopped trade; an invalidation of the setup (e.g. by time or distance); a minimum distance of the failure close below the level (the examples show 1.80 to 18.55 points).

**Observed example geometry:** stop distances 35.25 / 40.75 / 40.70 and target distances 59.25 / 60.50 / 60.65 - the author's boxes are placed by hand, so no fixed-point model reproduces the examples' exit prices exactly.
