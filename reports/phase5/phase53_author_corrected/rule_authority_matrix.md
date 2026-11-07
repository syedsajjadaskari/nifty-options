# Rule authority matrix

Authority levels: SOURCE (a guide states it), OWNER_APPROVED (Phase 5.3 brief), AUTHOR_CALL / HANDWRITTEN (author statement, meaning open), PROVISIONAL (smallest transparent convention chosen here, NOT confirmed), PROPOSED (earlier research parameter).

| rule | authority | state in `phase53-author-corrected` | evidence |
|---|---|---|---|
| IRF Method 2A support = first red candle LOW | OWNER_APPROVED | ACTIVE | irf_first_red_low_implementation.md |
| first red candle searched after the extension candle | PROVISIONAL (guide step order; variant after the breakout selectable) | ACTIVE | red-search variant: 4 of 42 executed Method-2 trades differ |
| first red candle rule limited to Method 2A | SOURCE-VERIFIED scope (2B's reference is a resistance) | ACTIVE | irf_first_red_low_implementation.md |
| IRF minimum 28-point EMA clearance | OWNER_APPROVED (number) | ACTIVE | irf_ema_28_implementation.md |
| clearance measured to the nearest point of the candle range, inclusive, all IRF methods | PROVISIONAL_EMA_RANGE_DISTANCE | ACTIVE | close-distance and 27-point readings are comparison variants |
| PDR first eligible confirmation candle | OWNER_APPROVED | ACTIVE | pdr_first_eligible_implementation.md |
| PDR confirmation = green candle (guide s.4.3) or lower-price rejection; close strictly above the ceiling | PROVISIONAL_PDR_MINIMAL_CONFIRMATION | ACTIVE | replaces the PROPOSED numeric thresholds |
| PDR retest candle may not confirm | PRESERVED convention (sequencing unresolved) | ACTIVE | retest-permitted effect reported separately |
| PDS first eligible confirmation candle | OWNER_APPROVED | ACTIVE | pds_first_eligible_implementation.md |
| PDS good red / red pin tests without percentages | PROVISIONAL_PDS_MINIMAL_QUALITY | ACTIVE | replaces the PROPOSED numeric thresholds |
| PDS weak first red candle -> Method 3 small-support break | SOURCE (PDS guide s.7 quality rule) | ACTIVE (not overridden) | conflict with AC38 flagged |
| ORB priority over IRF | NOT APPROVED | OFF | orb_unresolved_entries.md |
| ORB colour rule | CANDIDATE_NOT_APPROVED (Phase 5.1) | OFF (selectable) | phase53-var-orb-colour |
| IRF day's-low restriction | PENDING_OWNER_DEFINITION | OFF | irf_day_low_unresolved.md |
| portfolio rules, stops, targets, RF, same-minute policy, costs | USER_APPROVED / SOURCE | UNCHANGED (no controller code touched) | frozen hashes verified |

## Selectable configurations (signal level)

| configuration | authority | confirmed signals | IRF | PDR | PDS | ORB | RF |
|---|---|---|---|---|---|---|---|
| phase36-frozen | ACTIVE_REFERENCE | 1083 | 874 | 87 | 57 | 53 | 12 |
| phase52-approved | USER_APPROVED_VERIFIED | 1083 | 874 | 87 | 57 | 53 | 12 |
| phase53-irf-first-red-low | OWNER_APPROVED_LEVEL; SCOPE_AND_SEARCH_START_PROVISIONAL | 1148 | 939 | 87 | 57 | 53 | 12 |
| phase53-irf-ema28 | OWNER_APPROVED_28; MEASURE_PROVISIONAL_EMA_RANGE_DISTANCE | 954 | 745 | 87 | 57 | 53 | 12 |
| phase53-pdr-first-eligible | OWNER_APPROVED_INTENT; CONVENTION_PROVISIONAL | 1143 | 874 | 147 | 57 | 53 | 12 |
| phase53-pds-first-eligible | OWNER_APPROVED_INTENT; CONVENTION_PROVISIONAL | 1137 | 874 | 87 | 111 | 53 | 12 |
| phase53-author-corrected | COMPOSITE: OWNER_APPROVED RULES WITH PROVISIONAL CONVENTIONS | 1109 | 786 | 147 | 111 | 53 | 12 |
| phase53-var-irf-first-red-after-breakout | ASSUMPTION_VARIANT | 1084 | 875 | 87 | 57 | 53 | 12 |
| phase53-var-irf-ema28-method2-only | SCOPE_VARIANT | 1036 | 827 | 87 | 57 | 53 | 12 |
| phase53-var-irf-ema27 | DIAGNOSTIC_VARIANT | 959 | 750 | 87 | 57 | 53 | 12 |
| phase53-var-irf-ema28-close | DIAGNOSTIC_VARIANT | 1002 | 793 | 87 | 57 | 53 | 12 |
| phase53-var-orb-colour | CANDIDATE_NOT_APPROVED | 1080 | 874 | 87 | 57 | 50 | 12 |
