"""Exit-rule specification: targets, stops, partial exits, breakeven, same-bar ambiguity (Task 9)."""

import pytest

from nifty_trading.core.exit_policy import (
    Bar,
    EodPolicy,
    ExitPolicyConfig,
    TradeOutcome,
    evaluate_exit,
    levels,
    policy_for,
    select_stop_distance,
)
from nifty_trading.strategies.params import TradeConfig

E = 24000.0


def B(i, o, h, l, c):  # noqa: E741
    return Bar(f"m{i}", o, h, l, c)


def quiet(i):
    return B(i, E, E + 1, E - 1, E)


ORB = policy_for("ORB")  # T1 27, T2 60, SL 30


@pytest.mark.rules("EXE-POS-001", "EXE-T1-001")
def test_position_model_matches_the_report():
    assert ORB.total_qty == 390 and ORB.leg1_qty == 195 and ORB.leg2_qty == 195 and ORB.lot_size == 65 and ORB.t1_points == 27
    with pytest.raises(ValueError):
        ExitPolicyConfig(leg1_lots=2, leg2_lots=3)  # legs must add up to 6 lots
    with pytest.raises(ValueError):
        ExitPolicyConfig(t2_points=20.0)  # Target 2 must lie beyond Target 1


@pytest.mark.rules("EXE-T1-001", "EXE-T2-001", "ORB-GLOBAL-003", "IRF-TGT-001")
def test_target_stop_levels_long_and_short():
    L = levels("LONG", E, ORB)
    assert (L["t1"], L["t2"], L["stop"]) == (E + 27, E + 60, E - 30)
    S = levels("SHORT", E, ORB)
    assert (S["t1"], S["t2"], S["stop"]) == (E - 27, E - 60, E + 30)


@pytest.mark.rules("EXE-OUT-001", "EXE-PNL-001")
def test_target_outcome_books_both_legs_rs_16965_for_a_60_point_target2():
    r = evaluate_exit("LONG", E, [quiet(0), B(1, E, E + 28, E + 2, E + 28), B(2, E + 28, E + 61, E + 27, E + 60)], ORB)
    assert r.outcome is TradeOutcome.TARGET and r.leg1_exit == E + 27 and r.leg2_exit == E + 60
    assert r.pnl_rupees == 27 * 195 + 60 * 195 == 16965
    assert r.pnl_points_weighted == pytest.approx(16965 / 390)


@pytest.mark.rules("POST-T1-STOP-006", "EXE-OUT-001", "EXE-PNL-001")
def test_after_target1_the_remaining_legs_stop_6_points_against_the_entry_not_at_the_entry():
    """USER_APPROVED (Phase 2.3) replaces the report's exact-entry breakeven: LONG stop = entry - 6, so Leg 2 books -6 points (-Rs 1,170)."""
    r = evaluate_exit("LONG", E, [B(0, E, E + 28, E + 5, E + 20), B(1, E + 20, E + 25, E - 6, E - 5.5)], ORB)
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 6 and r.post_t1_stop_level == E - 6
    assert r.pnl_rupees == 27 * 195 - 6 * 195 == 4095 and not r.ambiguities  # T1 and the stop touch were on different bars
    # exact entry (and anything above entry - 6) no longer stops Leg 2
    still_open = evaluate_exit("LONG", E, [B(0, E, E + 28, E + 5, E + 20), B(1, E + 20, E + 25, E - 5.95, E - 5)], ORB)
    assert still_open.outcome is TradeOutcome.INCOMPLETE_EOD and still_open.pnl_rupees == 5265


@pytest.mark.rules("EXE-BE-001", "POST-T1-STOP-006")
def test_the_superseded_exact_entry_breakeven_survives_only_as_a_labelled_legacy_mode():
    legacy = ExitPolicyConfig(t2_points=60, stop_points=30, post_t1_stop_mode="ENTRY_BREAKEVEN")
    r = evaluate_exit("LONG", E, [B(0, E, E + 28, E + 5, E + 20), B(1, E + 20, E + 25, E - 1, E - 0.5)], legacy)
    assert r.outcome is TradeOutcome.BREAKEVEN and r.leg2_exit == E and r.pnl_rupees == 5265
    assert policy_for("ORB").post_t1_stop_mode == "BUFFER"  # the default is the owner's rule


@pytest.mark.rules("EXE-OUT-001", "EXE-PNL-001")
def test_stop_loss_loses_full_390_quantity():
    r = evaluate_exit("LONG", E, [quiet(0), B(1, E, E + 5, E - 31, E - 20)], ORB)
    assert r.outcome is TradeOutcome.STOP_LOSS and r.pnl_rupees == -30 * 390 == -11700
    s = evaluate_exit("SHORT", E, [B(0, E, E + 31, E - 2, E + 10)], ORB)
    assert s.outcome is TradeOutcome.STOP_LOSS and s.pnl_rupees == -11700


@pytest.mark.rules("POST-T1-STOP-006")
def test_short_side_mirrors_target_and_the_buffer_stop_at_entry_plus_6():
    r = evaluate_exit("SHORT", E, [B(0, E, E - 2, E - 28, E - 27), B(1, E - 27, E - 25, E - 61, E - 60)], ORB)
    assert r.outcome is TradeOutcome.TARGET and r.pnl_rupees == 16965
    buf = evaluate_exit("SHORT", E, [B(0, E, E - 1, E - 28, E - 20), B(1, E - 20, E + 6, E - 22, E)], ORB)
    assert buf.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and buf.leg2_exit == E + 6 and buf.pnl_rupees == 27 * 195 - 6 * 195
    assert evaluate_exit("SHORT", E, [B(0, E, E - 1, E - 28, E - 20), B(1, E - 20, E + 5.95, E - 22, E)], ORB).outcome is TradeOutcome.INCOMPLETE_EOD


@pytest.mark.rules("EXE-MISSING-001")
def test_same_bar_stop_and_target1_is_ambiguous_and_resolved_adversely():
    r = evaluate_exit("LONG", E, [B(0, E, E + 30, E - 31, E)], ORB)
    assert r.outcome is TradeOutcome.STOP_LOSS and r.pnl_rupees == -11700
    assert len(r.ambiguities) == 1 and "resolved as STOP" in r.ambiguities[0]


@pytest.mark.rules("EXE-MISSING-001", "POST-T1-STOP-006")
def test_same_bar_target1_and_post_t1_stop_touch_is_ambiguous_and_resolved_adversely():
    r = evaluate_exit("LONG", E, [B(0, E, E + 28, E - 6, E + 10)], ORB)  # high reaches T1, low reaches entry - 6
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.pnl_rupees == 4095
    assert r.ambiguities and "resolved as the STOP (adverse)" in r.ambiguities[0]
    calm = evaluate_exit("LONG", E, [B(0, E, E + 28, E - 5.9, E + 10)], ORB)  # the stop level is not reached: T1 only
    assert calm.outcome is TradeOutcome.INCOMPLETE_EOD and not calm.ambiguities


@pytest.mark.rules("EXE-MISSING-001")
def test_same_bar_leg2_stop_and_target2_resolved_as_stop():
    r = evaluate_exit("LONG", E, [B(0, E, E + 28, E + 5, E + 20), B(1, E + 20, E + 61, E - 6, E + 30)], ORB)
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and len(r.ambiguities) == 1 and r.pnl_rupees == 4095


@pytest.mark.rules("EXE-MISSING-001")
def test_no_favourable_fills_gapped_stop_fills_at_open_gapped_target_fills_at_level():
    stop = evaluate_exit("LONG", E, [B(0, E - 50, E - 45, E - 55, E - 50)], ORB)  # opens 20 beyond the stop
    assert stop.leg1_exit == E - 50 and stop.pnl_rupees == -50 * 390  # worse than the -30 stop level
    tgt = evaluate_exit("LONG", E, [B(0, E + 100, E + 110, E + 99, E + 105)], ORB)  # opens beyond Target 2
    assert tgt.outcome is TradeOutcome.TARGET and tgt.leg1_exit == E + 27 and tgt.leg2_exit == E + 60  # not the better open


@pytest.mark.rules("EXE-MISSING-001")
def test_end_of_day_incomplete_is_reported_and_never_counted_as_a_win():
    r = evaluate_exit("LONG", E, [quiet(0), quiet(1)], ORB)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.pnl_rupees == 0 and "end-of-day" in r.unresolved[0]
    t1_only = evaluate_exit("LONG", E, [B(0, E, E + 28, E + 5, E + 20), B(1, E + 20, E + 25, E + 10, E + 15)], ORB)
    assert t1_only.outcome is TradeOutcome.INCOMPLETE_EOD and t1_only.pnl_rupees == 5265  # only the booked leg is realised
    flat = evaluate_exit("LONG", E, [B(0, E, E + 28, E + 5, E + 20), B(1, E + 20, E + 25, E + 10, E + 15)],
                         ExitPolicyConfig(t2_points=60, stop_points=30, eod_policy=EodPolicy.EXIT_AT_LAST_CLOSE))
    assert flat.pnl_rupees == 27 * 195 + 15 * 195 and "research option" in flat.unresolved[0]


@pytest.mark.rules("RF-011", "RF-009", "EXE-T2-001", "EXE-STOP-001")
def test_rf_policy_carries_a_proposed_target_and_the_user_approved_stop():
    rf = policy_for("RF")
    assert (rf.t2_points, rf.t2_status) == (60.0, "PROPOSED_FOR_REVIEW")  # never VERIFIED_EXPLICIT / USER_APPROVED
    assert (rf.stop_points, rf.stop_status) == (35.0, "USER_APPROVED") and rf.execution_status == "RESEARCH_ONLY"
    assert rf.missing == ()


@pytest.mark.rules("RF-011", "EXE-T2-001")
def test_rf_without_a_configured_target_is_still_not_evaluable():
    rf = policy_for("RF", trade=TradeConfig(rf_t2_points=None))
    assert rf.t2_points is None and "t2_points" in rf.missing and rf.t2_status == "UNRESOLVED"
    r = evaluate_exit("LONG", E, [B(0, E, E + 200, E - 200, E)], rf)
    assert r.outcome is TradeOutcome.NOT_EVALUABLE and r.pnl_rupees == 0 and r.unresolved


@pytest.mark.rules("PDR-008", "PDS-TGT-001", "PDR-009", "EXE-T2-001")
def test_pdr_pds_targets_are_70_per_guide_but_flagged_as_conflicting_with_the_report():
    pdr = policy_for("PDR")
    assert pdr.t2_points == 70.0 and pdr.stop_points == 35.0 and pdr.t2_status == "CONFLICTING"
    assert len(pdr.conflicts) == 1 and "1 of its 6" in pdr.conflicts[0]  # the conflict is recorded, never overwritten
    pds = policy_for("PDS")
    assert pds.t2_points == 70.0 and pds.stop_points == 35.0 and "2 of its 3" in pds.conflicts[0]
    assert policy_for("IRF").conflicts == () and policy_for("ORB").conflicts == ()
    r = evaluate_exit("SHORT", E, [B(0, E, E - 1, E - 80, E - 75)], pds)  # a recorded conflict does not block evaluation
    assert r.outcome is TradeOutcome.TARGET


@pytest.mark.rules("IRF-SL-001", "IRF-SL-002", "PDS-SL-001")
def test_stop_distance_selection_35_or_40_boundaries():
    assert select_stop_distance(E, E + 34.99) == 35.0
    assert select_stop_distance(E, E + 35.0) == 35.0  # 'within 35' (p10): boundary resolved as <= (PROPOSED)
    assert select_stop_distance(E, E + 35.0, inclusive_35=False) == 40.0
    assert select_stop_distance(E, E + 35.01) == 40.0
    assert select_stop_distance(E, None) is None  # never guess when no green candle is available
    research = TradeConfig(stop_variant="SOURCE_35_40_BY_DISTANCE")
    assert policy_for("IRF", reference_price=None, entry=E, trade=research).stop_points is None
    assert policy_for("IRF", reference_price=E + 50, entry=E, trade=research).stop_points == 40.0
    assert policy_for("ORB", trade=research).stop_points == 30.0  # ORB keeps its documented stop in every variant


@pytest.mark.rules("IRF-TGT-001", "ORB-GLOBAL-003")
def test_irf_and_orb_policy_values_come_from_the_documents():
    irf = policy_for("IRF", reference_price=E + 50, entry=E)  # the reference is ignored by the user-approved baseline
    assert (irf.t2_points, irf.stop_points, irf.stop_status) == (60.0, 35.0, "USER_APPROVED")
    assert (ORB.t2_points, ORB.stop_points) == (60.0, 30.0)


def test_breakeven_disabled_is_rejected_because_no_source_defines_it():
    with pytest.raises(ValueError):
        ExitPolicyConfig(t2_points=60, stop_points=30, breakeven_after_t1=False)
