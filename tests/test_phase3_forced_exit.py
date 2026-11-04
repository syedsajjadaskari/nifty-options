"""Phase 3: the forced exit before 15:15 (FORCED-EXIT-001/002). Synthetic paths only."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from nifty_trading.core.exit_policy import Bar, TradeOutcome, evaluate_exit, policy_for
from nifty_trading.strategies.params import TradeConfig
from nifty_trading.strategies.trading_day import DayRules, DayState, run_trading_day

IST = ZoneInfo("Asia/Kolkata")
E = 25000.0
FX = TradeConfig(forced_exit_time=time(15, 14))


def at(day: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, h, m, tzinfo=IST)


def path(day: date, over: dict | None = None, first="09:15", last="15:29"):
    """Flat 1-minute bars; the closing-auction minutes (15:15+ on/after 2026-08-03) are marked non-executable."""
    from nifty_trading.core.execution_eligibility import classify_bar
    over, out, t = over or {}, [], at(day, first)
    while t <= at(day, last):
        o, h, lo, c = over.get(f"{t:%H:%M}", (E, E, E, E))
        k = classify_bar(t)
        out.append(Bar(t, o, h, lo, c, k.value == "CONTINUOUS", k.value))
        t += timedelta(minutes=1)
    return out


ORD, AUC = date(2026, 1, 12), date(2026, 8, 4)


@pytest.mark.rules("FORCED-EXIT-001", "FORCED-EXIT-002")
@pytest.mark.parametrize("day", [ORD, AUC])
def test_a_position_still_open_at_15_14_is_closed_at_that_minutes_open_whole_position(day):
    pol = policy_for("IRF", trade=FX)
    # SHORT entered 09:30 at E; price drifts to E - 10 by the forced-exit minute (no stop, no T1)
    bars = path(day, {"15:13": (E - 10, E - 10, E - 10, E - 10), "15:14": (E - 9, E - 9, E - 12, E - 11)})
    r = evaluate_exit("SHORT", E, [b for b in bars if b.ts >= at(day, "09:30")], pol, entry_at_first_bar_open=True)
    assert r.outcome is TradeOutcome.FORCED_EXIT and r.leg1_exit == E - 9 and r.leg2_exit == E - 9 and r.leg2_ts == at(day, "15:14")
    assert r.pnl_rupees == 9 * 390 and r.forced_exit_reference_close == E - 11  # filled at the OPEN; the close is only a reference
    assert not r.unresolved_at_closing_auction and r.non_executable_bars_skipped == 0  # the auction bars are never reached


@pytest.mark.rules("FORCED-EXIT-001")
def test_after_target_1_only_leg_two_is_force_closed_and_leg_one_keeps_its_27_points():
    pol = policy_for("IRF", trade=FX)
    bars = path(ORD, {"11:00": (E, E, E - 27, E - 27), "15:14": (E - 20, E - 20, E - 21, E - 21)})
    r = evaluate_exit("SHORT", E, bars, pol)
    assert r.outcome is TradeOutcome.FORCED_EXIT and r.leg1_exit == E - 27 and r.leg2_exit == E - 20
    assert r.pnl_rupees == 27 * 195 + 20 * 195 and r.post_t1_stop_level == E + 6


@pytest.mark.rules("FORCED-EXIT-001")
def test_a_stop_or_target_before_the_forced_minute_wins_and_the_forced_minute_bar_is_not_walked():
    pol = policy_for("IRF", trade=FX)
    stop = evaluate_exit("SHORT", E, path(ORD, {"14:00": (E, E + 35, E, E + 35)}), pol)
    assert stop.outcome is TradeOutcome.INITIAL_FULL_STOP
    # a spike INSIDE the forced-exit minute is ignored: the position was already closed at that minute's open
    spike = evaluate_exit("SHORT", E, path(ORD, {"15:14": (E, E + 40, E - 70, E)}), pol)
    assert spike.outcome is TradeOutcome.FORCED_EXIT and spike.leg2_exit == E and spike.pnl_rupees == 0
    tgt = evaluate_exit("SHORT", E, path(ORD, {"10:00": (E, E, E - 27, E - 27), "10:30": (E, E, E - 60, E - 60)}), pol)
    assert tgt.outcome is TradeOutcome.TARGET


@pytest.mark.rules("FORCED-EXIT-001")
def test_without_the_policy_the_old_behaviour_is_unchanged():
    r = evaluate_exit("SHORT", E, path(AUC), policy_for("IRF"))
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.unresolved_at_closing_auction


@pytest.mark.rules("FORCED-EXIT-001", "FORCED-EXIT-002")
def test_if_the_forced_exit_minute_cannot_be_filled_the_position_stays_unresolved_never_invented():
    pol = policy_for("IRF", trade=FX)
    holey = [b for b in path(ORD) if b.ts != at(ORD, "15:14")]  # no 15:14 bar: the next bar (15:15) would be a fill AT 15:15, not before it
    assert evaluate_exit("SHORT", E, holey, pol).outcome is TradeOutcome.INCOMPLETE_EOD  # never filled late
    ended = [b for b in path(ORD) if b.ts < at(ORD, "15:14")]  # ...but with no bar at/after 15:14 at all nothing is invented
    assert evaluate_exit("SHORT", E, ended, pol).outcome is TradeOutcome.INCOMPLETE_EOD
    blocked = [Bar(b.ts, b.o, b.h, b.l, b.c, False, "POST_CLOSE") if b.ts == at(ORD, "15:14") else b for b in path(ORD)]
    assert evaluate_exit("SHORT", E, blocked, pol).outcome is TradeOutcome.INCOMPLETE_EOD  # the forced minute itself must be fillable


@pytest.mark.rules("FORCED-EXIT-001", "DAY-UNRES-001")
def test_the_day_controller_finishes_the_day_after_a_forced_exit_and_allows_no_second_trade():
    from datetime import datetime as dt

    from nifty_trading.strategies.base import SignalRecord

    def sig(strategy, hhmm, direction):
        ts = at(ORD, hhmm)
        return SignalRecord(strategy=strategy, method="M", direction=direction, signal_date=ORD, signal_timestamp=ts, signal_candle_start=ts - timedelta(minutes=5),
                            signal_candle_open=E, signal_candle_high=E, signal_candle_low=E, signal_candle_close=E, reference_levels={}, rule_ids_satisfied=[],
                            rule_ids_failed=[], signal_status="CONFIRMED", invalidation_reason=None, verification_status="PROPOSAL_DEPENDENT",
                            execution_config={"execution_status": "RESEARCH_ONLY"})
    res = run_trading_day(ORD, [sig("IRF", "09:30", "SHORT"), sig("PDR", "12:00", "LONG")], path(ORD), FX, DayRules())
    assert [t.classification for t in res.trades] == ["FORCED_EXIT"] and res.final_state is DayState.DAY_FINISHED
    assert dt is not None and any(d.reason.startswith("POSITION_ACTIVE") for d in res.diagnostics)
    # and without the policy the same day is UNRESOLVED_EXECUTION (Phase 2.3 behaviour)
    plain = run_trading_day(ORD, [sig("IRF", "09:30", "SHORT")], path(ORD), TradeConfig(), DayRules())
    assert plain.final_state is DayState.UNRESOLVED_EXECUTION
