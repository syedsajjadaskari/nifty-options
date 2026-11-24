# Latest author clarification (received with the Phase 7.1 brief)

> "Sir, the 27 points gap near the 200 EMA is common for all the strategies sir."

**Status: AUTHOR_STATEMENT, relayed by the owner; undated; the wording defines neither the measure, the inequality, the timing, the timeframe nor the action.** It is evidence of intent, not a mechanical rule. Nothing in the engines uses it by default.

## Evidence trail for the EMA number

| # | Source | Wording | What it supports |
|---|---|---|---|
| 1 | Handwritten pages AC13 / AC18 (`docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf` p3-4; `reports/phase5/phase51_author_corrections/new_author_rules.md` NR2) | "The candle should close below EMA when the space btn. the entry candle is less than 27." / "Should be ignored as Tgt 1 is not above EMA, tgt 1 is less than 27. Should wait until EMA break." (IRF SHORT; "200 EMA [5 min TF]" written on the drawing) | 27 = Target 1 distance; the drawing places the EMA BELOW the short entry, between the entry and Target 1; action: skip or wait for a close below the EMA. Supports a **target-side / path** reading (EMA-5) and the 5-minute EMA(200) |
| 2 | Phone call (`reports/phase5/phase52_author_rules/author_call_clarifications.md` C3) | "Sometimes IRF is correct, but the gap between the EMA and the candle should be 28 points." | A **candle-to-EMA gap**, number 28, scope IRF only; inequality not stated |
| 3 | Phase 5.3 implementation (owner approved the NUMBER only) | `ema_min_clearance=28`, nearest point of the signal candle's range to the EMA, inclusive, all IRF methods - **PROVISIONAL** measure | The EMA-2/EMA-4 family (range clearance) |
| 4 | Latest IRF PDFs (p2 of each) | "As you described it, IRF has no 200 EMA filter ..." | **Contradicts** a universal EMA rule for IRF V3 (the PDFs describe an earlier conversation) |
| 5 | **New** (this brief) | "the 27 points gap near the 200 EMA is common for all the strategies" | Number is 27 (agrees with 1, not 2); scope ALL FIVE strategies; 'near the EMA' hints at a proximity zone; direction of the inequality still not given |

The words 'gap' (not 'distance to target'), 'near the 200 EMA' and 'common for all the strategies' are the only new facts. **Decisions that need the author are listed in `remaining_author_questions.md`.**
