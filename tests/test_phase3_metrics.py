"""Phase 3: the research metrics (drawdown, streaks, profit factor, costs, monthly, signal counts). Pure arithmetic on tiny ledgers."""

import math

import pytest

from nifty_trading.research import phase3 as P


def row(d, t, n, pnl, strat="IRF", outcome="TARGET", q=390, hold=10.0):
    return {"date": d, "entry_time": t, "trade_no": n, "gross_pnl_rs": pnl, "strategy": strat, "outcome": outcome, "qty_total": q, "holding_minutes": hold}


R = [row("2025-09-01", "09:20", 1, 1000.0), row("2025-09-02", "09:20", 1, -500.0, outcome="INITIAL_FULL_STOP"),
     row("2025-09-02", "10:20", 2, -300.0, strat="PDR", outcome="INITIAL_FULL_STOP"), row("2025-10-01", "09:20", 1, 700.0, outcome="T1_THEN_BUFFER_STOP"),
     row("2025-10-02", "09:20", 1, -200.0, outcome="FORCED_EXIT", hold=None)]


@pytest.mark.rules("EXE-DD-001")
def test_drawdown_uses_a_running_high_that_starts_at_zero_and_streaks_count_only_losses():
    assert P.drawdown([-100.0, -50.0]) == (150.0, 1)  # the initial 0 is the first peak
    assert P.drawdown([100.0, -30.0, -20.0, 60.0, -10.0]) == (50.0, 2)
    assert P.drawdown([]) == (0.0, -1) and P.drawdown([5.0, 5.0]) == (0.0, -1)
    assert P.max_consecutive_losses([1, -1, -1, 0, -1, -1, -1, 2]) == 3  # a zero breaks the run
    assert P.max_consecutive_losses([]) == 0


@pytest.mark.rules("EXE-PNL-001")
def test_summary_numbers_on_a_known_ledger():
    s = P.summarize(R)
    assert s["entries"] == 5 and s["days_traded"] == 4 and s["first_trades"] == 4 and s["second_trades"] == 1
    assert s["total_pnl_rs"] == 700.0 and s["gross_profit_rs"] == 1700.0 and s["gross_loss_rs"] == -1000.0
    assert s["profit_factor"] == pytest.approx(1.7) and s["win_rate_pct"] == pytest.approx(40.0) and s["avg_trade_rs"] == pytest.approx(140.0)
    assert s["max_drawdown_rs"] == 800.0 and s["max_consecutive_losses"] == 2  # 1000 -> 500 -> 200: down 800 before the +700... order: 1000, 500, 200, 900, 700
    assert (s["target2"], s["t1_then_buffer_stop"], s["initial_full_stop"], s["forced_exit"], s["unresolved"]) == (1, 1, 2, 1, 0)
    assert s["avg_holding_minutes"] == pytest.approx(10.0)


@pytest.mark.rules("EXE-PNL-001")
def test_profit_factor_edge_cases():
    assert math.isinf(P.summarize([row("d", "09:20", 1, 5.0)])["profit_factor"])
    assert P.summarize([row("d", "09:20", 1, -5.0)])["profit_factor"] == 0.0
    assert P.summarize([])["entries"] == 0


@pytest.mark.rules("EXE-PNL-001")
def test_costs_are_a_fixed_amount_plus_slippage_on_every_unit_in_and_out():
    one = [row("d", "09:20", 1, 1000.0)]
    assert P.apply_costs(one) == [1000.0]
    assert P.apply_costs(one, cost_per_trade=500.0) == [500.0]
    assert P.apply_costs(one, slippage_points_per_fill=0.5) == [1000.0 - 0.5 * 2 * 390]  # entry 390 units + exits 390 units, 0.5 point each
    assert P.apply_costs(one, 500.0, 1.0) == [1000.0 - 500.0 - 780.0]


@pytest.mark.rules("EXE-PNL-001")
def test_monthly_equity_and_ordering():
    pn = [r["gross_pnl_rs"] for r in sorted(R, key=P.sequence_key)]
    assert P.monthly(R, pn) == {"2025-09": 200.0, "2025-10": 500.0}
    days = ["2025-09-01", "2025-09-02", "2025-09-03", "2025-10-01", "2025-10-02"]
    eq = P.equity_curve(R, pn, days)
    assert [e["cumulative_pnl_rs"] for e in eq] == [1000.0, 200.0, 200.0, 900.0, 700.0] and eq[1]["drawdown_rs"] == 800.0 and eq[2]["daily_pnl_rs"] == 0.0
    shuffled = [R[3], R[0], R[4], R[2], R[1]]
    assert [P.sequence_key(r) for r in sorted(shuffled, key=P.sequence_key)] == [P.sequence_key(r) for r in sorted(R, key=P.sequence_key)]


@pytest.mark.rules("SEL-ACTIVE-001")
def test_signal_counts_classify_the_diagnostic_log():
    log = [{"strategy": "IRF", "event": "REJECTED", "reason": "ENTRY_CUTOFF_EXCEEDED(fill 13:05 IST > 13:00)"},
           {"strategy": "ORB", "event": "IGNORED", "reason": "POSITION_ACTIVE (signal kept for diagnostics only; never reused)"},
           {"strategy": "PDR+RF", "event": "CONFLICT", "reason": "SIMULTANEOUS_SIGNAL_CONFLICT_UNRESOLVED: x"},
           {"strategy": "IRF", "event": "IGNORED", "reason": "DAY_FINISHED"}, {"strategy": "IRF", "event": "REJECTED", "reason": "SECOND_TRADE_RESTRICTED_TO_PDR_PDS"}]
    c = P.signal_counts(log)["total"]
    assert c == {"rejected_cutoff_13_00": 1, "ignored_position_active": 1, "simultaneous_conflicts": 1, "ignored_day_already_decided": 1,
                 "rejected_not_pdr_pds_for_second_trade": 1}


@pytest.mark.rules("EXE-STOP-001")
def test_the_four_scenarios_are_distinct_fixed_and_never_combined():
    sc = P.scenarios()
    assert list(sc) == ["baseline", "ema_structure", "pdr_shelf", "sl40"]
    b = sc["baseline"]
    assert b.proposals.trend_mode == "EMA_PREV_SESSION_CLOSE" and b.proposals.pdr_zone_method == "B_SWING_HIGH_REVERSAL" and b.trade.stop_variant == "BASELINE"
    assert sc["ema_structure"].proposals.trend_mode == "STRUCTURE_EMA_SWING2" and sc["ema_structure"].proposals.pdr_zone_method == b.proposals.pdr_zone_method
    assert sc["pdr_shelf"].proposals.pdr_zone_method == "C_REPEATED_TOUCHES" and sc["pdr_shelf"].proposals.trend_mode == b.proposals.trend_mode
    assert sc["sl40"].trade.stop_variant == "ALTERNATE_40" and sc["sl40"].proposals == b.proposals
    assert all(s.trade.forced_exit_time == P.FORCED_EXIT_TIME and s.proposals.max_signals_per_session == 99 for s in sc.values())
    for k in ("ema_structure", "pdr_shelf"):  # exactly one setting differs from the baseline
        diff = {f for f in b.proposals.__dataclass_fields__ if getattr(b.proposals, f) != getattr(sc[k].proposals, f)}
        assert len(diff) == 1, (k, diff)
