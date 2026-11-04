"""Phase 2.3: the shared trading-day controller, the 13:00 cutoff, six-lot sizing and the post-T1 stop (USER_APPROVED rules).

All scenarios are synthetic 1-minute paths: they test the RULES, not profitability. No historical P&L backtest is run anywhere in this file.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from nifty_trading.core.exit_policy import Bar, TradeOutcome, evaluate_exit, levels, policy_for
from nifty_trading.strategies import ProposalConfig
from nifty_trading.strategies.base import SignalRecord
from nifty_trading.strategies.params import TradeConfig
from nifty_trading.strategies.trading_day import DayRules, DayState, TieBreakPolicy, run_trading_day

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 1, 12)  # an ordinary Monday, before the closing-auction regime
E = 25000.0


def at(hhmm: str, day: date = DAY) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, h, m, tzinfo=IST)


def bars(over: dict[str, tuple[float, float, float, float]] | None = None, day: date = DAY, first="09:15", last="15:29", price=E) -> list[Bar]:
    """Flat 1-minute bars at ``price`` from ``first`` to ``last``; ``over`` replaces chosen minutes by (o, h, l, c)."""
    over = over or {}
    out, t = [], at(first, day)
    end = at(last, day)
    while t <= end:
        key = f"{t:%H:%M}"
        o, h, lo, c = over.get(key, (price, price, price, price))
        out.append(Bar(t, o, h, lo, c))
        t += timedelta(minutes=1)
    return out


def sig(strategy: str, hhmm: str, direction: str | None = None, method: str = "M1", status: str = "CONFIRMED", day: date = DAY,
        exec_status: str = "RESEARCH_ONLY") -> SignalRecord:
    direction = direction or ("SHORT" if strategy in ("IRF", "PDS") else "LONG")
    ts = at(hhmm, day)
    return SignalRecord(
        strategy=strategy, method=method, direction=direction, signal_date=day, signal_timestamp=ts, signal_candle_start=ts - timedelta(minutes=5),
        signal_candle_open=E, signal_candle_high=E, signal_candle_low=E, signal_candle_close=E, reference_levels={}, rule_ids_satisfied=[],
        rule_ids_failed=[], signal_status=status, invalidation_reason=None, verification_status="PROPOSAL_DEPENDENT",
        execution_config={"execution_status": exec_status})


def run(records, over=None, rules=None, trade=None, **bk):
    return run_trading_day(DAY, records, bars(over, **bk), trade or TradeConfig(), rules)


# Price paths used below (entry price E = 25,000 because every bar is flat at E unless overridden).
SHORT_T1_T2 = {"10:00": (E, E, E - 27, E - 27), "10:40": (E, E, E - 60, E - 60)}  # IRF SHORT: T1 at 10:00, T2 (60) at 10:40
LONG_SL30 = {"09:40": (E, E, E - 30, E - 30)}  # ORB LONG original stop (30) at 09:40
LONG_SL35 = {"10:40": (E, E, E - 35, E - 35)}


def reasons(res):
    return [d.reason for d in res.diagnostics]


# ======================================================================= trade selection (SEL-*)
@pytest.mark.rules("SEL-FIRST-001", "SEL-ACTIVE-001")
def test_the_first_valid_signal_in_time_order_opens_the_first_trade_and_later_ones_are_only_logged():
    """09:20 ORB wins over a 09:35 IRF: chronological, not by strategy list order; the ignored signal stays in the diagnostic log."""
    res = run([sig("IRF", "09:35"), sig("ORB", "09:20", method="Method 1"), sig("RF", "10:05")], {"09:20": (E, E, E, E)})
    assert [t.signal.strategy for t in res.trades] == ["ORB"] and res.trades[0].trade_no == 1
    ignored = [(d.strategy, d.reason) for d in res.diagnostics if d.event == "IGNORED"]
    assert ("IRF", "POSITION_ACTIVE (signal kept for diagnostics only; never reused)") in ignored and any(s == "RF" for s, _ in ignored)
    assert res.final_state is DayState.UNRESOLVED_EXECUTION  # the ORB position never closes in this flat path: nothing is invented


@pytest.mark.rules("SEL-FIRST-001")
def test_only_confirmed_signals_count_and_non_confirmed_records_are_never_traded():
    res = run([sig("ORB", "09:20", status="INVALIDATED"), sig("IRF", "09:35", status="NOT_EVALUATED"), sig("PDR", "09:40", status="INCOMPLETE_AT_EOD")])
    assert res.trades == [] and res.final_state is DayState.READY_FOR_FIRST_TRADE and res.diagnostics == []


@pytest.mark.rules("SEL-FIRST-001")
def test_a_diagnostic_only_or_entry_blocked_signal_is_rejected_and_the_next_valid_one_trades():
    res = run([sig("PDR", "09:20", exec_status="DIAGNOSTIC_ONLY_NOT_TRADABLE"), sig("IRF", "09:30")], SHORT_T1_T2)
    assert [t.signal.strategy for t in res.trades] == ["IRF"]
    assert any(d.strategy == "PDR" and d.reason == "DIAGNOSTIC_ONLY_NOT_TRADABLE" for d in res.diagnostics)


@pytest.mark.rules("SEL-TIE-001", "SEL-TIE-002")
def test_simultaneous_signals_of_different_strategies_are_a_logged_conflict_not_an_arbitrary_choice():
    """Scenario F: two engines independently valid at 09:20 and no approved priority -> no trade, conflict logged, day unresolved."""
    res = run([sig("ORB", "09:20", method="Method 1"), sig("IRF", "09:20"), sig("PDR", "10:30")])
    assert res.trades == [] and res.final_state is DayState.UNRESOLVED_EXECUTION
    [c] = res.conflicts
    assert "SIMULTANEOUS_SIGNAL_CONFLICT_UNRESOLVED" in c.reason and "ORB" in c.reason and "IRF" in c.reason
    assert "DAY_UNRESOLVED_EXECUTION" in reasons(res)  # the later PDR signal is not silently used


@pytest.mark.rules("SEL-TIE-001")
def test_opposite_directions_of_one_strategy_at_one_timestamp_are_also_a_conflict():
    res = run([sig("ORB", "09:20", "LONG", "Method 1"), sig("ORB", "09:20", "SHORT", "Gap/200DMA")])
    assert res.trades == [] and len(res.conflicts) == 1


@pytest.mark.rules("SEL-TIE-001")
def test_one_strategy_and_direction_with_several_methods_at_one_timestamp_is_one_trade():
    res = run([sig("IRF", "09:30", method="Method 1"), sig("IRF", "09:30", method="Method 2A")], SHORT_T1_T2)
    assert len(res.trades) == 1 and res.trades[0].concurrent_methods == ["Method 2A"] and not res.conflicts
    assert any(d.event == "NOTE" and "SAME_STRATEGY_CONCURRENT_METHOD" in d.reason for d in res.diagnostics)


@pytest.mark.rules("SEL-TIE-002")
def test_a_tie_break_policy_is_applied_only_when_explicitly_approved():
    both = [sig("ORB", "09:20", method="Method 1"), sig("IRF", "09:20")]
    unapproved = DayRules(tie_break=TieBreakPolicy(priority=("ORB", "IRF"), approved=False))
    assert run(both, rules=unapproved).trades == [] and run(both, rules=unapproved).final_state is DayState.UNRESOLVED_EXECUTION
    assert DayRules().tie_break is None  # nothing is approved by default
    approved = DayRules(tie_break=TieBreakPolicy(priority=("IRF", "ORB"), approved=True, source="TEST ONLY - not a real approval"))
    res = run(both, SHORT_T1_T2, rules=approved)
    assert [t.signal.strategy for t in res.trades] == ["IRF"] and not res.conflicts
    assert any("LOST_APPROVED_TIE_BREAK_TO_IRF" in r for r in reasons(res))
    partial = DayRules(tie_break=TieBreakPolicy(priority=("PDR",), approved=True))  # a policy that does not rank the colliding strategies decides nothing
    assert run(both, rules=partial).trades == []


# ======================================================================= day outcomes (DAY-*)
@pytest.mark.rules("DAY-T2-001")
def test_scenario_a_target_2_finishes_the_day_and_a_later_signal_is_ignored():
    res = run([sig("IRF", "09:30"), sig("PDR", "11:00")], SHORT_T1_T2)
    t = res.trades[0]
    assert t.classification == "TARGET" and t.result.outcome is TradeOutcome.TARGET
    assert len(res.trades) == 1 and res.final_state is DayState.DAY_FINISHED and "DAY_FINISHED" in reasons(res)


@pytest.mark.rules("DAY-BUF-001", "POST-T1-STOP-006")
def test_scenario_c_t1_then_buffer_stop_finishes_the_day_without_a_second_trade():
    path = {"10:00": (E, E, E - 27, E - 27), "10:20": (E, E + 6, E, E)}
    res = run([sig("IRF", "09:30"), sig("PDR", "11:00")], path)
    t = res.trades[0]
    assert t.classification == "T1_THEN_BUFFER_STOP" and t.result.leg2_exit == E + 6
    assert t.result.pnl_rupees == 27 * 195 - 6 * 195
    assert len(res.trades) == 1 and res.final_state is DayState.DAY_FINISHED and "DAY_FINISHED" in reasons(res)


@pytest.mark.rules("DAY-SL-001")
def test_scenario_b_initial_full_stop_allows_one_pdr_trade_and_then_the_day_is_finished():
    path = {**LONG_SL30, "11:00": (E, E, E, E), "11:30": (E, E + 27, E, E + 27), "12:00": (E, E + 70, E, E + 70)}
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "10:20"), sig("PDS", "12:10"), sig("IRF", "12:20")], path)
    first, second = res.trades
    assert first.classification == "INITIAL_FULL_STOP" and first.result.pnl_rupees == -30 * 390
    assert second.signal.strategy == "PDR" and second.trade_no == 2 and second.classification == "TARGET"
    assert res.final_state is DayState.DAY_FINISHED
    assert reasons(res).count("DAY_FINISHED") == 2  # the PDS and IRF signals after the second trade are ignored: no third trade
    trace = " | ".join(res.state_trace)
    assert "SECOND_TRADE_ELIGIBLE" in trace and "SECOND_TRADE_ACTIVE" in trace


@pytest.mark.rules("DAY-SL-001")
def test_scenario_d_only_pdr_or_pds_may_be_the_second_trade():
    res = run([sig("ORB", "09:20", method="Method 1"), sig("IRF", "10:15"), sig("RF", "10:16"), sig("ORB", "10:17", method="Method 1")], LONG_SL30)
    assert len(res.trades) == 1 and res.final_state is DayState.SECOND_TRADE_ELIGIBLE  # still waiting for a PDR/PDS signal
    rej = [d.reason for d in res.diagnostics if d.event == "REJECTED"]
    assert rej.count("SECOND_TRADE_RESTRICTED_TO_PDR_PDS") == 3
    # ... and the second trade can be PDS (a SHORT) as well
    res2 = run([sig("ORB", "09:20", method="Method 1"), sig("PDS", "10:20")], LONG_SL30)
    assert [t.signal.strategy for t in res2.trades] == ["ORB", "PDS"]


@pytest.mark.rules("DAY-NOREUSE-001")
def test_a_signal_ignored_while_the_first_position_was_active_is_never_reused_for_the_second_trade():
    """A PDR signal at 09:30 arrives while the ORB trade is still open (stopped out only at 09:40): it stays ignored."""
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "09:30")], LONG_SL30)
    assert len(res.trades) == 1 and res.trades[0].classification == "INITIAL_FULL_STOP"
    assert res.final_state is DayState.SECOND_TRADE_ELIGIBLE  # eligible, but nothing new was confirmed afterwards
    assert any(d.strategy == "PDR" and d.reason.startswith("POSITION_ACTIVE") for d in res.diagnostics)


@pytest.mark.rules("DAY-NOREUSE-001")
def test_a_signal_confirmed_in_the_same_minute_as_the_exit_bar_is_still_ignored_and_the_next_minute_is_allowed():
    """Position end = exit bar + 1 minute (the exit happens inside the 09:40 bar), so a 09:40 signal is ignored; 09:41 may trade."""
    early = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "09:40")], LONG_SL30)
    assert len(early.trades) == 1 and any(d.reason.startswith("POSITION_ACTIVE") for d in early.diagnostics)
    later = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "09:41")], LONG_SL30)
    assert [t.signal.strategy for t in later.trades] == ["ORB", "PDR"]


@pytest.mark.rules("DAY-MAX-001")
def test_there_is_never_a_third_trade_even_after_two_full_stops():
    path = {**LONG_SL30, "10:40": (E, E, E - 35, E - 35)}
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "10:20"), sig("PDR", "11:00"), sig("PDS", "11:10")], path)
    assert [t.classification for t in res.trades] == ["INITIAL_FULL_STOP", "INITIAL_FULL_STOP"]
    assert res.final_state is DayState.DAY_FINISHED and reasons(res).count("DAY_FINISHED") == 2


@pytest.mark.rules("DAY-MAX-001")
def test_the_second_trade_may_end_in_any_outcome_and_still_finishes_the_day():
    path = {**LONG_SL30, "11:00": (E, E + 27, E, E + 27), "11:20": (E, E, E - 6, E - 6)}  # second trade: T1 then the buffer stop
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "10:20"), sig("PDS", "11:30")], path)
    assert [t.classification for t in res.trades] == ["INITIAL_FULL_STOP", "T1_THEN_BUFFER_STOP"] and res.final_state is DayState.DAY_FINISHED


@pytest.mark.rules("DAY-UNRES-001")
def test_a_first_trade_left_open_at_the_end_of_the_data_is_unresolved_and_allows_no_second_trade():
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "14:00")], {"09:30": (E, E + 27, E, E + 27)})  # T1 only; Leg 2 never exits
    assert res.trades[0].classification == "INCOMPLETE_EOD" and len(res.trades) == 1
    assert res.final_state is DayState.UNRESOLVED_EXECUTION


@pytest.mark.rules("DAY-UNRES-001")
def test_an_exit_policy_that_cannot_be_evaluated_makes_the_day_unresolved():
    no_target = TradeConfig(rf_t2_points=None)
    res = run([sig("RF", "09:30"), sig("PDR", "10:30")], trade=no_target)
    assert res.trades[0].classification == "NOT_EVALUABLE" and res.final_state is DayState.UNRESOLVED_EXECUTION and len(res.trades) == 1


@pytest.mark.rules("DAY-UNRES-001", "EXE-AUCTION-001")
def test_a_position_still_open_when_the_closing_auction_starts_is_unresolved_not_invented():
    day = date(2026, 8, 4)  # a closing-auction day
    res = run_trading_day(day, [sig("IRF", "09:30", day=day), sig("PDR", "10:30", day=day)], _auction_bars(day), TradeConfig())
    t = res.trades[0]
    assert t.classification == "INCOMPLETE_EOD" and t.result.unresolved_at_closing_auction and t.result.leg2_exit is None
    assert res.final_state is DayState.UNRESOLVED_EXECUTION and len(res.trades) == 1


def _auction_bars(day):
    from nifty_trading.core.execution_eligibility import classify_bar
    out, t = [], at("09:15", day)
    while t <= at("15:30", day):
        k = classify_bar(t)
        out.append(Bar(t, E, E, E, E, k.value == "CONTINUOUS", k.value))
        t += timedelta(minutes=1)
    return out


# ======================================================================= the 13:00 IST entry cutoff (ENTRY-CUTOFF-001)
@pytest.mark.rules("ENTRY-CUTOFF-001")
def test_scenario_e_a_signal_confirmed_after_13_00_is_not_entered():
    res = run([sig("PDS", "13:05")])
    assert res.trades == [] and res.final_state is DayState.READY_FOR_FIRST_TRADE
    assert any(r.startswith("ENTRY_CUTOFF_EXCEEDED") for r in reasons(res))


@pytest.mark.rules("ENTRY-CUTOFF-001")
def test_a_signal_confirmed_at_exactly_13_00_fills_at_13_00_and_is_eligible_but_13_01_is_not():
    """Convention: the fill is the open of the bar starting at the signal candle's end, so a 13:00 confirmation fills at 13:00:00 (allowed)."""
    ok = run([sig("PDS", "13:00")], {"13:10": (E, E, E - 27, E - 27), "13:30": (E, E, E - 70, E - 70)})
    assert len(ok.trades) == 1 and ok.trades[0].fill_timestamp == at("13:00") and ok.trades[0].classification == "TARGET"
    late = run([sig("PDS", "13:01")])
    assert late.trades == [] and any(r.startswith("ENTRY_CUTOFF_EXCEEDED") for r in reasons(late))


@pytest.mark.rules("ENTRY-CUTOFF-001")
def test_a_13_00_signal_whose_fill_bar_would_come_later_is_rejected():
    """No 13:00 bar exists (data hole): the next bar is 13:01, i.e. a later fill -> rejected, never silently filled late."""
    holey = [b for b in bars() if b.ts != at("13:00")]
    res = run_trading_day(DAY, [sig("PDS", "13:00")], holey, TradeConfig())
    assert res.trades == [] and any(r.startswith("ENTRY_NOT_FILLABLE") for r in reasons(res))


@pytest.mark.rules("ENTRY-CUTOFF-001")
def test_the_cutoff_uses_asia_kolkata_not_the_machine_or_signal_timezone():
    utc = ZoneInfo("UTC")
    base = sig("PDS", "13:00")
    # 07:30 UTC == 13:00 IST (allowed); 07:35 UTC == 13:05 IST (rejected). The bars carry IST stamps; equality of instants is what matters.
    ok = SignalRecord(**{**base.__dict__, "signal_timestamp": datetime(2026, 1, 12, 7, 30, tzinfo=utc)})
    late = SignalRecord(**{**base.__dict__, "signal_timestamp": datetime(2026, 1, 12, 7, 35, tzinfo=utc)})
    assert len(run([ok]).trades) == 1
    assert run([late]).trades == []


@pytest.mark.rules("ENTRY-CUTOFF-001", "DAY-SL-001")
def test_the_second_trade_is_subject_to_the_cutoff_too():
    path = {"12:50": (E, E, E - 30, E - 30)}
    res = run([sig("ORB", "12:40", method="Method 1"), sig("PDR", "13:10")], path)
    assert [t.classification for t in res.trades] == ["INITIAL_FULL_STOP"] and any(r.startswith("ENTRY_CUTOFF_EXCEEDED") for r in reasons(res))
    assert res.final_state is DayState.SECOND_TRADE_ELIGIBLE


@pytest.mark.rules("ENTRY-CUTOFF-001")
def test_the_cutoff_governs_new_entries_only_an_open_position_keeps_running_past_13_00():
    res = run([sig("IRF", "12:30")], {"13:20": (E, E, E - 27, E - 27), "14:00": (E, E, E - 60, E - 60)})
    assert res.trades[0].classification == "TARGET" and res.trades[0].result.leg2_ts == at("14:00")
    # a custom cutoff is honoured
    early = run([sig("IRF", "12:30")], rules=DayRules(entry_cutoff=time(12, 0)))
    assert early.trades == []


# ======================================================================= six lots, targets and stops
@pytest.mark.rules("SIZE-LOT-001")
def test_six_lots_in_two_equal_legs_of_three_and_a_configurable_lot_size():
    pol = policy_for("IRF")
    assert (pol.total_lots, pol.leg1_lots, pol.leg2_lots, pol.lot_size) == (6, 3, 3, 65)
    assert (pol.total_qty, pol.leg1_qty, pol.leg2_qty) == (390, 195, 195)
    small = policy_for("IRF", trade=TradeConfig(total_lots=4, leg1_lots=2, lot_size=50))
    assert (small.total_qty, small.leg1_qty, small.leg2_qty) == (200, 100, 100)
    for bad in (dict(total_lots=5, leg1_lots=3), dict(total_lots=6, leg1_lots=2), dict(lot_size=0)):
        with pytest.raises(Exception):  # noqa: B017
            TradeConfig(**bad)
    r = evaluate_exit("SHORT", E, [Bar("a", E, E, E - 90, E - 80)], pol)
    assert r.pnl_rupees == 27 * 195 + 60 * 195  # Target 1 on 195 units, Target 2 on 195 units
    r2 = evaluate_exit("SHORT", E, [Bar("a", E, E, E - 90, E - 80)], small)
    assert r2.pnl_rupees == 27 * 100 + 60 * 100


@pytest.mark.rules("EXE-T1-001", "EXE-T2-001", "EXE-STOP-001")
@pytest.mark.parametrize("strategy,direction,t2,stop", [("IRF", "SHORT", 60, 35), ("ORB", "LONG", 60, 30), ("PDR", "LONG", 70, 35),
                                                         ("PDS", "SHORT", 70, 35), ("RF", "LONG", 60, 35)])
def test_target_and_stop_levels_per_strategy(strategy, direction, t2, stop):
    lv = levels(direction, E, policy_for(strategy))
    sgn = 1 if direction == "LONG" else -1
    assert lv["t1"] == E + sgn * 27 and lv["t2"] == E + sgn * t2 and lv["stop"] == E - sgn * stop


@pytest.mark.rules("EXE-STOP-001")
def test_the_40_point_alternative_applies_to_the_four_strategies_and_orb_stays_30():
    alt = TradeConfig(stop_variant="ALTERNATE_40")
    assert [policy_for(s, trade=alt).stop_points for s in ("IRF", "ORB", "PDR", "PDS", "RF")] == [40.0, 30.0, 40.0, 40.0, 40.0]
    res = run([sig("IRF", "09:30")], {"10:00": (E, E + 35, E, E)}, trade=alt)  # +35 would stop out the baseline, not the 40-point variant
    assert res.trades[0].classification == "INCOMPLETE_EOD"
    assert run([sig("IRF", "09:30")], {"10:00": (E, E + 35, E, E)}).trades[0].classification == "INITIAL_FULL_STOP"


@pytest.mark.rules("POST-T1-STOP-006")
def test_the_worked_examples_of_the_owner_long_and_short():
    """Entry 25,000 LONG: SL 24,965, T1 25,027, T2 25,060, post-T1 stop 24,994. SHORT: SL 25,035, T1 24,973, T2 24,940, post-T1 25,006."""
    lg = levels("LONG", 25000.0, policy_for("RF"))  # LONG, stop 35, target 60 (RF research proposal)
    assert (lg["stop"], lg["t1"], lg["t2"], lg["post_t1_stop"]) == (24965.0, 25027.0, 25060.0, 24994.0)
    sh = levels("SHORT", 25000.0, policy_for("IRF"))
    assert (sh["stop"], sh["t1"], sh["t2"], sh["post_t1_stop"]) == (25035.0, 24973.0, 24940.0, 25006.0)


@pytest.mark.rules("POST-T1-STOP-006")
def test_long_post_t1_stop_is_entry_minus_6_and_short_is_entry_plus_6_exactly():
    up = [Bar("a", E, E + 27, E, E + 27), Bar("b", E + 27, E + 30, E - 5.99, E)]  # LONG: 5.99 below entry does NOT stop
    assert evaluate_exit("LONG", E, up, policy_for("RF")).outcome is TradeOutcome.INCOMPLETE_EOD
    r = evaluate_exit("LONG", E, [up[0], Bar("b", E + 27, E + 30, E - 6, E)], policy_for("RF"))
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 6 and r.post_t1_stop_level == E - 6
    dn = [Bar("a", E, E, E - 27, E - 27), Bar("b", E - 27, E + 5.99, E - 30, E)]
    assert evaluate_exit("SHORT", E, dn, policy_for("IRF")).outcome is TradeOutcome.INCOMPLETE_EOD
    s = evaluate_exit("SHORT", E, [dn[0], Bar("b", E - 27, E + 6, E - 30, E)], policy_for("IRF"))
    assert s.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and s.leg2_exit == E + 6 and s.post_t1_stop_level == E + 6
    assert s.pnl_rupees == 27 * 195 - 6 * 195 == 4095


@pytest.mark.rules("POST-T1-STOP-006")
def test_there_is_no_trailing_stop_the_post_t1_level_never_moves_whatever_price_does():
    """After T1 price runs +50 (no Target 2) and falls back: Leg 2 still exits at entry - 6, not at a trailed level."""
    path = [Bar("a", E, E + 27, E, E + 27), Bar("b", E + 27, E + 50, E + 20, E + 50), Bar("c", E + 50, E + 55, E + 10, E + 12), Bar("d", E + 12, E + 12, E - 6, E - 6)]
    r = evaluate_exit("LONG", E, path, policy_for("RF"))
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 6 and r.post_t1_stop_level == E - 6
    assert not any("trail" in e.lower() for e in r.events)
    # the stop is not moved back to entry either: a dip to exactly the entry does not stop Leg 2
    dip = [Bar("a", E, E + 27, E, E + 27), Bar("b", E + 27, E + 30, E, E + 10)]
    assert evaluate_exit("LONG", E, dip, policy_for("RF")).outcome is TradeOutcome.INCOMPLETE_EOD


@pytest.mark.rules("POST-T1-STOP-006", "EXE-MISSING-001")
def test_gap_through_the_post_t1_stop_fills_at_the_open_and_logs_the_adverse_slippage():
    gap = [Bar("a", E, E + 27, E, E + 27), Bar("b", E - 15, E - 10, E - 20, E - 12)]  # opens 9 points beyond the E - 6 stop
    r = evaluate_exit("LONG", E, gap, policy_for("RF"))
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 15 and r.adverse_slippage_points == 9
    assert r.pnl_rupees == 27 * 195 - 15 * 195
    full = evaluate_exit("LONG", E, [Bar("a", E - 50, E - 48, E - 52, E - 49)], policy_for("RF"))  # opens 15 beyond the 35-point stop
    assert full.outcome is TradeOutcome.INITIAL_FULL_STOP and full.leg1_exit == E - 50 and full.adverse_slippage_points == 15


@pytest.mark.rules("POST-T1-STOP-006", "EXE-MISSING-001")
def test_same_bar_conservatism_stop_before_target_and_post_t1_stop_before_target_2():
    pol = policy_for("IRF")
    a = evaluate_exit("SHORT", E, [Bar("a", E, E + 36, E - 28, E)], pol)  # initial stop and T1 in one bar
    assert a.outcome is TradeOutcome.INITIAL_FULL_STOP and a.ambiguities
    b = evaluate_exit("SHORT", E, [Bar("a", E, E, E - 27, E - 27), Bar("b", E - 27, E + 6, E - 61, E)], pol)  # post-T1 stop and T2 in one bar
    assert b.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and b.ambiguities


@pytest.mark.rules("POST-T1-STOP-006", "EXE-OUT-001")
def test_initial_full_stop_exits_all_six_lots_before_target_1():
    r = evaluate_exit("LONG", E, [Bar("a", E, E, E - 35, E - 35)], policy_for("PDR"))
    assert r.outcome is TradeOutcome.INITIAL_FULL_STOP and r.pnl_rupees == -35 * 390 and r.post_t1_stop_level is None
    assert TradeOutcome.INITIAL_FULL_STOP is TradeOutcome.STOP_LOSS  # the same outcome under its Phase 2.3 name


# ======================================================================= non-fillable auction bars, look-ahead, original open
@pytest.mark.rules("EXE-AUCTION-001", "SEL-FIRST-001")
def test_a_signal_whose_entry_bar_is_a_closing_auction_reference_bar_cannot_trade():
    day = date(2026, 8, 4)
    res = run_trading_day(day, [sig("IRF", "15:15", day=day)], _auction_bars(day), TradeConfig(), DayRules(entry_cutoff=time(23, 59)))
    assert res.trades == [] and any("ENTRY_NOT_FILLABLE" in r for r in reasons(res))


@pytest.mark.rules("SEL-FIRST-001", "DATA-TIME-001")
def test_decisions_do_not_depend_on_later_signals_or_on_bars_before_the_fill():
    """No look-ahead: removing every signal after the first trade's entry leaves the first trade identical, and altering bars BEFORE the
    signal changes nothing (the controller and exit model read bars only from the fill bar onwards)."""
    recs = [sig("IRF", "09:30"), sig("PDR", "10:30"), sig("RF", "11:00")]
    full = run(recs, SHORT_T1_T2)
    solo = run(recs[:1], SHORT_T1_T2)
    key = lambda r: (r.trades[0].signal.strategy, r.trades[0].fill_timestamp, r.trades[0].classification, r.trades[0].result.pnl_rupees)  # noqa: E731
    assert key(full) == key(solo)
    noisy = {**SHORT_T1_T2, "09:16": (E, E + 500, E - 500, E), "09:29": (E, E + 300, E - 300, E)}
    assert key(run(recs, noisy)) == key(full)
    # truncating the future of the signal list never changes an earlier decision
    for k in range(1, len(recs) + 1):
        part = run(recs[:k], SHORT_T1_T2)
        assert part.trades[0].fill_timestamp == full.trades[0].fill_timestamp


@pytest.mark.rules("DATA-OPEN-001")
def test_the_original_first_one_minute_open_is_the_session_open_not_the_vendor_daily_open():
    """USER_APPROVED: gap and first candle use the first 1-minute row's open. 2025-09-02: first minute 24,683.25 vs vendor daily open 24,653.00."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    if not (root / "data" / "processed" / "nifty50_daily").exists():
        pytest.skip("processed data not available")
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    m = load_one_minute()
    d = date(2025, 9, 2)
    day_rows = m[m.timestamp.dt.date == d].sort_values("timestamp")
    first_open = float(day_rows.iloc[0].open)
    ctxs, _ = build_session_contexts(m, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    c = ctxs[d]
    daily = load_daily_official().set_index("date")
    assert first_open == 24683.25 and float(daily.loc[d, "open"]) == 24653.0
    assert c.open_price == first_open and float(c.candles.open.iloc[0]) == first_open  # the vendor daily open is NOT substituted
    from nifty_trading.strategies.definitions import gap_info
    assert gap_info(c, ProposalConfig()).points == pytest.approx(first_open - c.previous.close_official)


@pytest.mark.rules("ORB-GLOBAL-003")
def test_the_trend_research_variants_a_and_b_are_both_selectable_and_neither_is_chosen_by_results():
    a = ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE")
    b = ProposalConfig(trend_mode="STRUCTURE_EMA_SWING2")
    assert a.trend_mode != b.trend_mode
    with pytest.raises(Exception, match="trend_mode"):
        ProposalConfig(trend_mode="BEST_PERFORMING")


# ======================================================================= research variant A of the trend (EMA(200) price location only)
@pytest.mark.rules("TREND-EMA-001", "RF-001")
def test_variant_a_uses_only_the_previous_sessions_close_against_its_ema_and_never_the_gap_day():
    from synthetic import ctx

    from nifty_trading.strategies.definitions import ema_prev_session_trend, trend_check

    def tr(direction, close, ema, today=(25500, 25600, 25400, 25550)):
        c = ctx([today], prev={"cands": [(close, close + 1, close - 1, close)], "close": close, "ema_last": ema})
        return ema_prev_session_trend(c, direction, ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE"))
    assert tr("LONG", 30.0, 25.0).ok is True and tr("LONG", 30.0, 30.0).ok is False and tr("LONG", 30.0, 40.0).ok is False
    assert tr("SHORT", 20.0, 25.0).ok is True and tr("SHORT", 20.0, 20.0).ok is False and tr("SHORT", 30.0, 25.0).ok is False
    assert tr("LONG", 30.0, float("nan")).ok is None  # EMA still warming up: not evaluable, never silently True
    assert tr("LONG", 30.0, 25.0, today=(1, 2, 0.5, 1.5)).ok is tr("LONG", 30.0, 25.0, today=(9000, 9100, 8900, 9050)).ok  # today's candles are irrelevant
    c = ctx([(100, 101, 99, 100)], prev={"cands": [(30, 31, 29, 30)], "close": 30.0, "ema_last": 25.0})
    assert trend_check(c, 0, "LONG", "EMA_PREV_SESSION_CLOSE", ProposalConfig()).ok is True  # the dispatcher reaches it
    assert ema_prev_session_trend(ctx([(1, 2, 0, 1)]), "LONG", ProposalConfig()).ok is None  # no previous session


# ======================================================================= gaps found by the Phase 2.3 mutation run
@pytest.mark.rules("SEL-TIE-001")
def test_two_strategies_going_the_same_way_in_the_same_minute_are_still_a_conflict():
    """The real 2026-02-18 09:30 case: PDR and RF, both LONG. Same direction is not enough - different strategies have different stops/targets."""
    res = run([sig("PDR", "09:30", "LONG"), sig("RF", "09:30", "LONG")])
    assert res.trades == [] and len(res.conflicts) == 1 and res.final_state is DayState.UNRESOLVED_EXECUTION
    assert "PDR" in res.conflicts[0].reason and "RF" in res.conflicts[0].reason


@pytest.mark.rules("EXE-SEL-001", "DAY-UNRES-001")
def test_an_exit_policy_that_cannot_be_evaluated_is_reported_as_no_position_to_the_selection_helpers():
    from nifty_trading.strategies.selection import (
        NO_POSITION,
        position_end_from_result,
        simulate_exit,
    )
    rec = sig("RF", "09:30")
    res = simulate_exit(rec, bars(), TradeConfig(rf_t2_points=None))
    assert res is not None and res.outcome is TradeOutcome.NOT_EVALUABLE
    assert position_end_from_result(res) is NO_POSITION


@pytest.mark.rules("EXE-FILL-001", "EXE-BE-001")
def test_the_causal_entry_bar_rule_applies_through_simulate_exit_in_the_legacy_exact_entry_mode():
    """Legacy ENTRY_BREAKEVEN: filling at the entry bar's own open must not count as touching the entry (simulate_exit passes entry_at_first_bar_open)."""
    from nifty_trading.strategies.selection import simulate_exit
    legacy = TradeConfig(post_t1_stop_mode="ENTRY_BREAKEVEN")
    entry_only = [Bar(at("09:30"), E, E, E - 27, E - 27)]  # SHORT: T1 reached; the bar's high equals the entry (it opened there)
    r = simulate_exit(sig("IRF", "09:30"), entry_only, legacy)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.leg1_exit == E - 27 and not r.ambiguities


@pytest.mark.rules("DAY-MAX-001")
def test_the_entries_per_day_limit_is_enforced_by_the_rules_object_not_only_by_the_state_machine_shape():
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "10:20")], LONG_SL30, rules=DayRules(max_entries=1))
    assert len(res.trades) == 1 and "MAX_ENTRIES_PER_DAY" in reasons(res)


# ======================================================================= fixes from the Phase 2.3 independent review (Reviewer 5)
@pytest.mark.rules("POST-T1-STOP-006")
def test_r5_01_a_bar_that_opens_below_the_stop_level_before_target_1_is_not_a_gap_through_the_post_t1_stop():
    r = evaluate_exit("LONG", E, [Bar("a", E, E + 1, E - 1, E), Bar("b", E - 10, E + 30, E - 12, E + 28)], policy_for("RF"))
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 6 and r.adverse_slippage_points == 0
    assert r.pnl_rupees == 27 * 195 - 6 * 195 == 4095


@pytest.mark.rules("SEL-TIE-002", "SEL-TIE-003")
def test_r5_02_an_approved_winner_that_signals_both_ways_at_once_is_still_a_conflict():
    pol = DayRules(tie_break=TieBreakPolicy(priority=("ORB",), approved=True, source="TEST ONLY"))
    res = run([sig("ORB", "09:20", "LONG", "Method 1"), sig("ORB", "09:20", "SHORT", "Gap/200DMA"), sig("IRF", "09:20")], rules=pol)
    assert res.trades == [] and len(res.conflicts) == 1 and res.final_state is DayState.UNRESOLVED_EXECUTION


@pytest.mark.rules("DAY-UNRES-001", "EXE-BE-001")
def test_r5_03_the_legacy_breakeven_class_also_finishes_the_day_through_the_controller():
    legacy = TradeConfig(post_t1_stop_mode="ENTRY_BREAKEVEN")
    path = {"10:00": (E, E, E - 27, E - 27), "10:10": (E - 5, E, E - 5, E - 5)}  # T1, then a touch of the entry
    res = run([sig("IRF", "09:30"), sig("PDR", "11:00")], path, trade=legacy)
    assert res.trades[0].classification == "BREAKEVEN" and res.final_state is DayState.DAY_FINISHED and len(res.trades) == 1


@pytest.mark.rules("DAY-SL-001", "SEL-ACTIVE-001")
def test_r5_03_signals_are_also_ignored_while_the_second_trade_is_active_and_the_entry_price_is_recorded():
    path = {**LONG_SL30, "12:00": (E, E, E - 35, E - 35)}  # second trade (PDR, 10:20) is stopped out only at 12:00
    res = run([sig("ORB", "09:20", method="Method 1"), sig("PDR", "10:20"), sig("PDS", "10:30"), sig("PDR", "11:00")], path)
    assert [t.signal.strategy for t in res.trades] == ["ORB", "PDR"] and [t.entry_price for t in res.trades] == [E, E]
    assert sum(d.reason.startswith("POSITION_ACTIVE") for d in res.diagnostics) == 2  # the 10:30 PDS and the 11:00 PDR


@pytest.mark.rules("SIZE-LOT-001", "POST-T1-STOP-006")
def test_r5_09_configuration_cannot_make_the_legs_unequal_or_widen_the_stop():
    from nifty_trading.core.exit_policy import ExitPolicyConfig
    with pytest.raises(ValueError, match="EQUAL"):
        ExitPolicyConfig(total_lots=6, leg1_lots=2, leg2_lots=4)
    with pytest.raises(ValueError, match="no widening"):
        ExitPolicyConfig(t2_points=60, stop_points=5, post_t1_buffer_points=6)
    with pytest.raises(ValueError, match=">= 0"):
        ExitPolicyConfig(t2_points=60, stop_points=30, post_t1_buffer_points=-1)
    with pytest.raises(Exception, match="widen"):
        TradeConfig(post_t1_buffer_points=36)
    with pytest.raises(Exception, match=">= 0"):
        TradeConfig(post_t1_buffer_points=-1)


@pytest.mark.rules("SEL-FIRST-001", "ENTRY-CUTOFF-001")
def test_r5_08_records_of_another_session_are_rejected_and_naive_timestamps_are_read_as_ist():
    other = sig("IRF", "09:30", day=date(2026, 1, 13))
    res = run([other])
    assert res.trades == [] and any(r.startswith("RECORD_FOR_ANOTHER_DAY") for r in reasons(res))
    base = sig("IRF", "09:30")
    naive = SignalRecord(**{**base.__dict__, "signal_timestamp": datetime(2026, 1, 12, 9, 30)})
    assert len(run([naive], SHORT_T1_T2).trades) == 1  # naive 09:30 == 09:30 IST; no TypeError against the aware bars


@pytest.mark.rules("TREND-EMA-001", "ORB-TREND-001", "RF-001")
def test_r5_10_variant_a_is_wired_through_the_engines_not_only_the_helper():
    import test_phase2_pdr_pds_rf as o
    from synthetic import ctx

    from nifty_trading.strategies import RFStrategy
    a = RFStrategy(proposals=ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE"))
    ok = [r for r in a.evaluate_session(ctx(o.RF_OK, prev=o.RF_PREV, ema=23950.0)) if r.signal_status == "CONFIRMED"]
    assert ok and ok[0].execution_config["trend_mode"] == "EMA_PREV_SESSION_CLOSE"
    below = {**o.RF_PREV, "ema_last": 24500.0}  # yesterday closed BELOW its EMA: no uptrend -> no RF signal
    assert not [r for r in a.evaluate_session(ctx(o.RF_OK, prev=below, ema=23950.0)) if r.signal_status == "CONFIRMED"]


# ======================================================================= Phase 3.1: the collision policy is a switchable diagnostic, default unchanged
@pytest.mark.rules("SEL-TIE-002")
def test_collision_policy_default_marks_the_day_unresolved_and_the_diagnostic_policy_lets_the_day_continue():
    recs = [sig("PDR", "09:30", "LONG"), sig("RF", "09:30", "LONG"), sig("IRF", "10:30")]
    default = run(recs, SHORT_T1_T2)
    assert default.trades == [] and default.final_state is DayState.UNRESOLVED_EXECUTION and "DAY_UNRESOLVED_EXECUTION" in reasons(default)
    cont = run(recs, {"10:50": (E, E, E - 27, E - 27), "11:30": (E, E, E - 60, E - 60)}, rules=DayRules(collision_policy="SKIP_COLLISION_EVENT_CONTINUE_DAY"))
    assert len(cont.conflicts) == 1 and [t.signal.strategy for t in cont.trades] == ["IRF"]  # the colliding pair was skipped, the later IRF signal traded
    assert DayRules().collision_policy == "MARK_DAY_UNRESOLVED"
    with pytest.raises(ValueError, match="collision_policy"):
        DayRules(collision_policy="PICK_THE_BEST")
