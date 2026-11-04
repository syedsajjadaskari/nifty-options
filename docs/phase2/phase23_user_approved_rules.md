# Phase 2.3 - user-approved rules (generated from the rule registry)

Authority vocabulary: **SOURCE_VERIFIED** (stated in a PDF/the report) · **USER_APPROVED** (the strategy owner's instruction; NOT a rule written in the PDFs) · **PROPOSED_FOR_REVIEW** · **CONFLICTING** · **UNRESOLVED**. Every rule below carries `effective_phase = 2.3`. History is never erased: a replaced rule stays in the registry, marked `SUPERSEDED_BY_USER_APPROVED_RULE`.

Registry: 146 rules; 19 created or re-authorised in Phase 2.3.

| rule | authority | approval source | replaces / replaced by | implementing function | verifying tests |
|---|---|---|---|---|---|
| **EXE-BE-001** | SOURCE_VERIFIED | - | SUPERSEDED BY **POST-T1-STOP-006** | - (superseded; legacy mode `post_t1_stop_mode='ENTRY_BREAKEVEN'`) | `test_r5_03_the_legacy_breakeven_class_also_finishes_the_day_through_the_controller`<br>`test_the_causal_entry_bar_rule_applies_through_simulate_exit_in_the_legacy_exact_entry_mode`<br>`test_breakeven_stop_gapped_through_fills_at_the_open_not_at_entry`<br>(+2 more) |
| **TREND-STRUCT-001** | USER_APPROVED | Strategy owner, earlier approval confirmed in Phase 2.3 instructions s7 | - | `strategies.definitions.structure_trend` | `test_orb_and_rf_with_structure_trend_never_use_candles_beyond_the_prefix`<br>`test_structure_trend_down_is_the_mirror`<br>`test_structure_trend_is_selectable_as_a_proposal_and_validated`<br>(+5 more) |
| **PDR-ZONE-002** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s7 | - | `strategies.definitions.pdr_diagnostic_zone`<br>`strategies.definitions.pdr_zone` | `test_no_zone_method_reproduces_chart_3_so_the_candle_choice_stays_open`<br>`test_pdr_zone_method_a_is_the_absolute_highest_high_candle`<br>`test_pdr_zone_method_b_is_the_latest_confirmed_swing_high_with_a_bearish_reversal_candle`<br>(+5 more) |
| **DATA-OPEN-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s7 | - | `strategies.definitions.gap_info` | `test_the_original_first_one_minute_open_is_the_session_open_not_the_vendor_daily_open` |
| **SEL-FIRST-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.1 | supersedes **EXE-SEL-001 (as the only selection rule; the evaluation policies remain as research diagnostics)** | `strategies.trading_day.run_trading_day` | `test_a_diagnostic_only_or_entry_blocked_signal_is_rejected_and_the_next_valid_one_trades`<br>`test_a_signal_whose_entry_bar_is_a_closing_auction_reference_bar_cannot_trade`<br>`test_decisions_do_not_depend_on_later_signals_or_on_bars_before_the_fill`<br>(+3 more) |
| **SEL-ACTIVE-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.1-3.2 | - | `strategies.trading_day.run_trading_day` | `test_r5_03_signals_are_also_ignored_while_the_second_trade_is_active_and_the_entry_price_is_recorded`<br>`test_the_first_valid_signal_in_time_order_opens_the_first_trade_and_later_ones_are_only_logged`<br>`test_signal_counts_classify_the_diagnostic_log` |
| **SEL-TIE-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.1 and Scenario F | - | `strategies.trading_day.run_trading_day` | `test_one_strategy_and_direction_with_several_methods_at_one_timestamp_is_one_trade`<br>`test_opposite_directions_of_one_strategy_at_one_timestamp_are_also_a_conflict`<br>`test_simultaneous_signals_of_different_strategies_are_a_logged_conflict_not_an_arbitrary_choice`<br>(+1 more) |
| **SEL-TIE-003** | PROPOSED_FOR_REVIEW | none yet | - | `strategies.trading_day.run_trading_day` | `test_r5_02_an_approved_winner_that_signals_both_ways_at_once_is_still_a_conflict` |
| **SEL-TIE-002** | UNRESOLVED | Strategy owner, Phase 2.3 instructions: policy left unresolved | - | `strategies.trading_day.run_trading_day` | `test_a_tie_break_policy_is_applied_only_when_explicitly_approved`<br>`test_r5_02_an_approved_winner_that_signals_both_ways_at_once_is_still_a_conflict`<br>`test_simultaneous_signals_of_different_strategies_are_a_logged_conflict_not_an_arbitrary_choice` |
| **DAY-T2-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.2 | - | `strategies.trading_day.run_trading_day` | `test_scenario_a_target_2_finishes_the_day_and_a_later_signal_is_ignored` |
| **DAY-BUF-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.2 and s5 | - | `strategies.trading_day.run_trading_day` | `test_scenario_c_t1_then_buffer_stop_finishes_the_day_without_a_second_trade` |
| **DAY-SL-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.2 and Scenario B/D | - | `strategies.trading_day.run_trading_day` | `test_r5_03_signals_are_also_ignored_while_the_second_trade_is_active_and_the_entry_price_is_recorded`<br>`test_scenario_b_initial_full_stop_allows_one_pdr_trade_and_then_the_day_is_finished`<br>`test_scenario_d_only_pdr_or_pds_may_be_the_second_trade`<br>(+1 more) |
| **DAY-NOREUSE-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.2 | - | `strategies.trading_day.run_trading_day` | `test_a_signal_confirmed_in_the_same_minute_as_the_exit_bar_is_still_ignored_and_the_next_minute_is_allowed`<br>`test_a_signal_ignored_while_the_first_position_was_active_is_never_reused_for_the_second_trade` |
| **DAY-UNRES-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.2 and s9 | - | `strategies.trading_day.run_trading_day` | `test_a_first_trade_left_open_at_the_end_of_the_data_is_unresolved_and_allows_no_second_trade`<br>`test_a_position_still_open_when_the_closing_auction_starts_is_unresolved_not_invented`<br>`test_an_exit_policy_that_cannot_be_evaluated_is_reported_as_no_position_to_the_selection_helpers`<br>(+3 more) |
| **DAY-MAX-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.2 | - | `strategies.trading_day.run_trading_day` | `test_the_entries_per_day_limit_is_enforced_by_the_rules_object_not_only_by_the_state_machine_shape`<br>`test_the_second_trade_may_end_in_any_outcome_and_still_finishes_the_day`<br>`test_there_is_never_a_third_trade_even_after_two_full_stops` |
| **ENTRY-CUTOFF-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.3 | - | `strategies.trading_day.run_trading_day` | `test_a_13_00_signal_whose_fill_bar_would_come_later_is_rejected`<br>`test_a_signal_confirmed_at_exactly_13_00_fills_at_13_00_and_is_eligible_but_13_01_is_not`<br>`test_r5_08_records_of_another_session_are_rejected_and_naive_timestamps_are_read_as_ist`<br>(+4 more) |
| **SIZE-LOT-001** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s3.4 (report: [P2] [P7]) | - | `core.exit_policy.policy_for` | `test_r5_09_configuration_cannot_make_the_legs_unequal_or_widen_the_stop`<br>`test_six_lots_in_two_equal_legs_of_three_and_a_configurable_lot_size` |
| **POST-T1-STOP-006** | USER_APPROVED | Strategy owner, Phase 2.3 instructions s5 | supersedes **EXE-BE-001** | `core.exit_policy.evaluate_exit` | `test_entry_bar_that_reaches_target_1_is_not_stopped_merely_because_it_opened_at_the_entry`<br>`test_gap_through_the_post_t1_stop_fills_at_the_open_and_logs_the_adverse_slippage`<br>`test_initial_full_stop_exits_all_six_lots_before_target_1`<br>(+11 more) |
| **TREND-EMA-001** | USER_APPROVED | Strategy owner, earlier approval confirmed in Phase 2.3 instructions s7 | - | `strategies.definitions.ema_prev_session_trend` | `test_r5_10_variant_a_is_wired_through_the_engines_not_only_the_helper`<br>`test_variant_a_uses_only_the_previous_sessions_close_against_its_ema_and_never_the_gap_day` |

## What each approved rule says

### EXE-BE-001 - SOURCE_VERIFIED
Once Target 1 is booked, the stop on Leg 2 moves to the entry price. [PHASE 2.3: SUPERSEDED by the owner's POST-T1-STOP-006 (stop at entry -/+ 6 instead of exactly at the entry). Kept only as the legacy mode post_t1_stop_mode='ENTRY_BREAKEVEN' for report reconciliation.]

### TREND-STRUCT-001 - USER_APPROVED
PROPOSED established trend (Phase 2.2 'structure' mode). Uptrend: close of the last candle before the open above its EMA(200) AND the latest two confirmed swing highs rising AND the latest two confirmed swing lows rising (downtrend: mirror). Evaluated on PREVIOUS-session information only, so the opening gap can never establish the trend. EMA slope is NOT a condition. [PHASE 2.3: approved as research variant B (EMA plus confirmed swing structure). The swing look-back k=2 itself (TREND-SWING-001) is still a proposal; neither variant is claimed to reproduce the discretionary trend.]

### PDR-ZONE-002 - USER_APPROVED
PROPOSED zone-marking candidates (which candle(s) mark the previous-day resistance): A absolute highest-high candle; B latest confirmed swing high with a bearish reversal candle; C highest cluster of >=2 swing highs (repeated resistance). The PDR guide says only 'find the high where price reached a peak and then reversed' and 'note the candle's body and upper wick'; the selection is NOT defined. Chosen by agreement with the source charts, never by profitability. [PHASE 2.3: the owner approved TWO independent research candidates - A: confirmed reversal swing high (B_SWING_HIGH_REVERSAL), B: repeated resistance shelf (C_REPEATED_TOUCHES). The absolute highest-high candle is kept as a DIAGNOSTIC reference only and never produces a tradable signal. Neither candidate reproduces PDR chart 3.]

### DATA-OPEN-001 - USER_APPROVED
OPEN-PRICE DEFINITION (found in Phase 2.2, not resolved): the 09:15 candle's open is the first 1-minute row's open, but the vendor DAILY open differs from it by more than 5 points on 98 of 247 sessions (up to 64) and equals the open drawn on the guide's own chart in PDR example 1 (2025-09-02: daily open 24,653.00, first-minute open 24,683.25; the author's chart shows a GREEN first candle, ours is red). Using the daily open would change the gap direction on 10 sessions and the first-candle colour on 13. Nothing was changed; the data is untouched. [PHASE 2.3: RESOLVED by the owner: use the ORIGINAL first 1-minute row's open for the opening gap, the first 5-minute candle and all signals; the vendor's separately published daily open is NOT substituted. The observation above stays on record.]

### SEL-FIRST-001 - USER_APPROVED
Only the FIRST valid signal among the five strategies, in chronological order of signal confirmation, initiates the first trade of the day. The strategies are not five independent positions: one shared portfolio-level controller selects.

### SEL-ACTIVE-001 - USER_APPROVED
While a position is active every later signal is ignored for execution and kept in a diagnostic log with the reason; an ignored signal is never reused later.

### SEL-TIE-001 - USER_APPROVED
Independently valid signals of DIFFERENT strategies confirmed at the same timestamp are a conflict: it is logged as SIMULTANEOUS_SIGNAL_CONFLICT and no strategy is chosen arbitrarily.

### SEL-TIE-003 - PROPOSED_FOR_REVIEW
CONTROLLER INTERPRETATION awaiting the owner's confirmation (not stated in the instructions): (a) several METHODS of the SAME strategy and direction at one timestamp are treated as ONE trade (identical stop and target; the other methods are listed); (b) opposite directions of one strategy at one timestamp are a conflict, like different strategies. Both choices are unobservable in the data today (all 64 IRF and 8 ORB same-timestamp multi-method groups carry identical references).

### SEL-TIE-002 - UNRESOLVED
A tie-breaking priority between strategies that signal at the same timestamp has NOT been approved. The controller accepts a TieBreakPolicy only if it is explicitly marked approved; with none, the collision is unresolved: no trade is taken and the day is UNRESOLVED_EXECUTION.

### DAY-T2-001 - USER_APPROVED
If the first trade reaches Target 2 the trading day is finished: no further trade.

### DAY-BUF-001 - USER_APPROVED
If the first trade reaches Target 1 and the remaining legs then exit at the post-T1 protective stop (T1_THEN_BUFFER_STOP), no second trade is allowed.

### DAY-SL-001 - USER_APPROVED
If the first trade hits its ORIGINAL full stop-loss before Target 1 (INITIAL_FULL_STOP), exactly one additional trade is permitted, and only a PDR or PDS trade from a valid, independently confirmed signal confirmed after the first trade has fully stopped out.

### DAY-NOREUSE-001 - USER_APPROVED
A signal that was ignored while the first position was active is never used retroactively for the second trade.

### DAY-UNRES-001 - USER_APPROVED
No second trade if the first trade closed by end of day, by an unresolved execution (for example an open position when the closing auction starts, or a NOT_EVALUABLE exit policy) or by any exit class not explicitly approved for re-entry; the day is UNRESOLVED_EXECUTION and nothing is invented.

### DAY-MAX-001 - USER_APPROVED
At most 2 entries per day; after the second trade, whatever its outcome, no further trade.

### ENTRY-CUTOFF-001 - USER_APPROVED
1:00 PM IST is the strict entry cutoff: no new position may be entered with a fill later than 13:00:00 IST. A candle that closes after 13:00 is not an eligible entry. With the causal fill convention (the open of the bar starting at the signal candle's end) a signal confirmed at exactly 13:00 fills at 13:00:00 and is eligible; one confirmed at 13:05 is rejected as ENTRY_CUTOFF_EXCEEDED. The cutoff concerns new entries only, not open positions. Evaluated in Asia/Kolkata, never in the machine's timezone.

### SIZE-LOT-001 - USER_APPROVED
6 lots, in two equal legs of 3 lots; the lot multiplier is configurable (the historical report used 65 per lot: 390 units, 195 per leg). Synthetic index-point model, not an executable index order.

### POST-T1-STOP-006 - USER_APPROVED
After Target 1 the remaining 3 lots use a protective stop 6 index points against the ORIGINAL entry: LONG entry - 6, SHORT entry + 6. No trailing, no further adjustment, no move back to entry, no widening. T1 then this stop = T1_THEN_BUFFER_STOP (Leg 1 keeps +27, Leg 2 books about -6 or worse after a gap) and no second trade. A gap through the stop fills at the worse of the level and the open; the adverse slippage is logged.

### TREND-EMA-001 - USER_APPROVED
Approved research variant A of the ORB/RF trend: the five-minute EMA(200) price location only (previous session's last close above/below its EMA(200); for RF the trend must exist BEFORE the opening gap, so the gap day contributes nothing). Not claimed to reproduce the discretionary trend definition.

## The supersession record

| old rule | authority of the old rule | new rule | status |
|---|---|---|---|
| **EXE-SEL-001** (PROPOSED evaluation policies for repeated signals (none is a source rule): ALL_VALID_SIGNALS, FIRST_VALID_SIGN...) | PROPOSED_FOR_REVIEW (performance report) | **SEL-FIRST-001** | old: `IMPLEMENTED_WITH_PROPOSAL`; new: APPROVED (USER_APPROVED) |
| **EXE-BE-001** (Once Target 1 is booked, the stop on Leg 2 moves to the entry price. [PHASE 2.3: SUPERSEDED by the owner's POS...) | SOURCE_VERIFIED (performance report) | **POST-T1-STOP-006** | old: `SUPERSEDED_BY_USER_APPROVED_RULE`; new: APPROVED (USER_APPROVED) |

Example: `RULE POST_T1_STOP_006 | AUTHORITY USER_APPROVED | OLD_RULE EXACT_ENTRY_BREAKEVEN (EXE-BE-001) | NEW_RULE ENTRY_MINUS_6_LONG / ENTRY_PLUS_6_SHORT | STATUS APPROVED`.
