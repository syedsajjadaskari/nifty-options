# PDR first-eligible-candle audit

Every PDR setup cycle (retest candle -> confirmation) was re-derived chronologically from the raw five-minute candles and the engine's zone (`research/phase65.pdr_cycle_audit`). Preserved: previous-day body-based zone, open strictly above the ceiling, the retest, a confirmation close strictly above the ceiling, green / lower-price-rejection patterns. Not every green candle is valid.

| window | cls | cycles |
|---|---|---|
| A | ENGINE_EQUALS_FIRST_ELIGIBLE | 147 |
| A | NO_CONFIRMATION_IN_CYCLE | 19 |
| B | ENGINE_EQUALS_FIRST_ELIGIBLE | 453 |
| B | NO_CONFIRMATION_IN_CYCLE | 83 |


Per window: {'A': {'cycles': 166, 'ENGINE_EQUALS_FIRST_ELIGIBLE': 147, 'NO_CONFIRMATION_IN_CYCLE': 19, 'earlier_green_failed_strict_close': 45, 'retest_candle_would_qualify': 61, 'with_next_eligible_candle': 68}, 'B': {'cycles': 536, 'ENGINE_EQUALS_FIRST_ELIGIBLE': 453, 'NO_CONFIRMATION_IN_CYCLE': 83, 'earlier_green_failed_strict_close': 170, 'retest_candle_would_qualify': 171, 'with_next_eligible_candle': 221}}

Meaning of the classes: ENGINE_EQUALS_FIRST_ELIGIBLE = the engine selected the first fully eligible candle (when an earlier green candle existed it closed at or below the zone ceiling, so the strict-close rule - not the engine - delayed the entry); DEFECT_* = the engine selected a later candidate than the audit's first eligible one (a genuine late-entry defect); NO_CONFIRMATION_IN_CYCLE = no eligible candle occurred. **The audit reuses the engine's own two conventions** (strict close above the ceiling; the retest candle may not confirm), so 'no defect' means 'the engine follows its own rules', not 'the author's complaint is wrong'. The 'retest candle would qualify' column marks cycles where the retest candle itself was green and closed above the ceiling: the engine excludes it by the preserved (unresolved) retest-then-confirmation sequencing convention; whether such a candle may confirm is an author decision, not a defect.

Actual late-entry defects found: **0** of 702 cycles.

File: `pdr_setup_audit.csv`. PDR-B and later confirmation variants are held (the prompt was cut off in section 5).