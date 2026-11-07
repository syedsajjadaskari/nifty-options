# Approved author decisions (Phase 5.3 brief) and how each was implemented

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

| # | decision | authority | implementation | status |
|---|---|---|---|---|
| D1 | IRF support reference = the FIRST qualifying red candle's wick LOW | Owner approved | `IRFPhase53Strategy(support_ref='FIRST_RED_LOW')`, Method 2A only; the search for the first red candle starts after the extension candle (provisional assumption, variant available) | IMPLEMENTED (level approved; search start and method scope PROVISIONAL) |
| D2 | IRF minimum 28 index points from EMA(200) | Owner approved (the number) | `ema_min_clearance=28.0`, measure PROVISIONAL_EMA_RANGE_DISTANCE (nearest point of the signal candle's high-low range), inclusive, all IRF methods | IMPLEMENTED (measure, inequality direction and scope PROVISIONAL) |
| D3 | PDR: enter on the first eligible candle, no unnecessary delay | Owner approved | `PDRFirstEligibleStrategy`: setup, retest-first sequencing and close above the ceiling preserved; numeric strength thresholds replaced by the smallest transparent conventions (green candle per the guide, or lower-price rejection) | IMPLEMENTED (pattern convention PROVISIONAL) |
| D4 | PDS: enter on the first eligible candle, no unnecessary delay | Owner approved | `PDSFirstEligibleStrategy`: numeric thresholds replaced by parameter-free quality tests for Methods 1/2; the source rule that a weak first red candle goes to Method 3 (small-support break) is PRESERVED | IMPLEMENTED (quality tests PROVISIONAL; conflict with the author's 'first candle' flagged) |
| D5 | ORB priority over IRF | NOT approved | no change: the controller's first-valid-signal rule stands; the missing ORB definitions are listed | DIAGNOSTIC ONLY |
| D6 | IRF day's-low restriction | Author stated; predicate unresolved | not applied (`PENDING_OWNER_DEFINITION`); eight readings measured at decision time | PENDING |
| D7 | IRF red-candle method scope | Scope verification required | Method 2A only; Method 2B (resistance-based), Method 1 and Method 3 have no red-candle-created support in the guide | VERIFIED FROM THE GUIDE; extension to 2B needs owner approval |

The combined configuration is selectable as `phase53-author-corrected`; every rule is also selectable alone (see `rule_authority_matrix.md`). The frozen Phase 3.6 default and the Phase 5.2 configurations are untouched.
