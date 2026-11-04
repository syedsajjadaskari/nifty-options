"""IRF signal engine. Fixtures marked (pN) reproduce worked examples printed on page N of the IRF guide."""

import pytest
from synthetic import ctx

from nifty_trading.core.exit_policy import levels, policy_for
from nifty_trading.strategies import IRFStrategy, ProposalConfig
from nifty_trading.strategies.base import IllegalTransition, SetupFSM, SignalStatus, State

IR = (95, 100, 90, 98)  # IRH = 100, IRL = 90


def run(cands, **prop):
    return IRFStrategy(proposals=ProposalConfig(**prop)).evaluate_session(ctx(cands))


def conf(recs, method=None):
    return [r for r in recs if r.signal_status == "CONFIRMED" and (method is None or r.method == method)]


# --------------------------------------------------------------------------- Method 1
@pytest.mark.rules("IRF-GLOBAL-001", "IRF-M1-001", "IRF-M1-002", "IRF-M1-004", "IRF-GLOBAL-003")
def test_m1_page6_worked_example_enters_at_close_of_second_candle():
    """(p6) IRH=100; candle 1 closes 103 (valid breakout close); candle 2 closes 99 -> entry at 99."""
    recs = run([IR, (98, 104, 97, 103), (103, 103.5, 98, 99)])
    [m1] = conf(recs, "Method 1")
    assert m1.signal_candle_close == 99 and m1.direction == "SHORT"
    assert m1.signal_timestamp.strftime("%H:%M") == "09:30"  # candle 09:25-09:30 is usable only at its close
    assert m1.signal_candle_start.strftime("%H:%M") == "09:25"
    assert m1.reference_levels["IRH"] == 100 and m1.reference_levels["IRL"] == 90
    # IRF-GLOBAL-004 (trades/day, time window, re-arming) is absent from the guide: no IRF signal is ever "VERIFIED"
    assert m1.verification_status == "PROPOSAL_DEPENDENT" and "IRF-GLOBAL-004" in m1.rule_ids_unresolved
    assert m1.reference_price_is_fill is False
    assert any("SIGNAL_CONFIRMED" in t for t in m1.state_trace)


@pytest.mark.rules("IRF-M1-001", "IRF-M1-002", "IRF-GLOBAL-003")
@pytest.mark.parametrize("cands,why", [
    ([IR, (98, 103, 97, 99), (99, 101, 95, 96)], "wick above IRH without a close above it: no breakout candle (p6)"),
    ([IR, (98, 104, 97, 103), (103, 104, 98, 101)], "next candle closes above IRH again (p6)"),
    ([IR, (98, 104, 97, 103), (103, 104, 98, 100.5)], "next candle dips inside but closes above IRH (p6)"),
    ([IR, (98, 101, 97, 100), (100, 100.5, 95, 96)], "close exactly at IRH is not 'above IRH'"),
    ([IR, (98, 104, 97, 103), (103, 104, 85, 89)], "next candle closes below IRL: not 'inside the range' (literal reading)"),
])
def test_m1_non_qualifying(cands, why):
    assert not conf(run(cands), "Method 1"), why


@pytest.mark.rules("IRF-M1-002")
def test_m1_is_not_available_before_the_failure_candle_closes():
    c = ctx([IR, (98, 104, 97, 103), (103, 103.5, 98, 99)])
    assert not conf(IRFStrategy().evaluate_session(c.prefix(2)))  # only the breakout candle has closed
    assert conf(IRFStrategy().evaluate_session(c.prefix(3)), "Method 1")


@pytest.mark.rules("IRF-M1-003")
def test_m1_boundary_close_below_irl_is_a_flagged_proposal_variant():
    cands = [IR, (98, 104, 97, 103), (103, 104, 85, 89)]
    [m1] = conf(run(cands, m1_close_below_irl_counts_as_inside=True), "Method 1")
    assert m1.verification_status == "PROPOSAL_DEPENDENT" and "IRF-M1-003" in m1.rule_ids_satisfied


@pytest.mark.rules("IRF-M1-C001", "IRF-M1-002")
def test_m1_conflict_next_candle_vs_following_candle_is_resolved_by_default_and_kept_as_variant():
    cands = [IR, (98, 104, 97, 103), (103, 103, 99.5, 100), (100, 100, 95, 96)]  # c2 closes exactly at IRH, c3 inside
    assert not conf(run(cands), "Method 1")  # pp.5,6,13: the VERY next candle only
    [m1] = conf(run(cands, m1_max_candles_after_breakout=2), "Method 1")
    assert "IRF-M1-C001" in m1.rule_ids_satisfied and m1.verification_status == "PROPOSAL_DEPENDENT"
    assert any("research variant of p.14" in f for f in m1.flags)


@pytest.mark.rules("IRF-M2-002", "IRF-M2-003", "IRF-M1-C001")
@pytest.mark.parametrize("window", [1, 2, 3])
def test_regression_d_irf_1_the_method_1_window_variant_must_not_blind_method_2_to_the_extension(window):
    """Phase 3.1 defect D-IRF-1: ``m1_max_candles_after_breakout`` (the p.14 Method 1 research variant) was also used as the
    start offset of the Method 2 state machine, so with a window >= 2 the extension and the red candle that form during
    the first window-1 candles after the breakout were never recorded and a valid Method 2A was lost although no
    Method 1 had occurred. Method 2 (IRF p.7: extension, red candle, support break) is independent of that window."""
    cands = [IR, (98, 104, 97, 103), (103, 106, 102, 105), (105, 105.5, 101, 102), (102, 103, 101.5, 102.5),
             (102.5, 103, 101.2, 102.8), (102.8, 103, 100, 100.5)]
    recs = run(cands, m1_max_candles_after_breakout=window)
    assert not conf(recs, "Method 1")
    [a] = conf(recs, "Method 2A")
    assert a.signal_candle_close == 100.5 and a.signal_timestamp.strftime("%H:%M") == "09:50"
    assert a.signal_candle_start.strftime("%H:%M") == "09:45"


# --------------------------------------------------------------------------- Method 2
M2A = [IR, (98, 104, 97, 103), (103, 106, 102, 105), (105, 106.5, 101, 102), (102, 105, 101.5, 104), (104, 104.2, 100.5, 100.8)]


@pytest.mark.rules("IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002")
def test_m2a_support_break_after_extension_and_red_candle():
    recs = run(M2A)
    [a] = conf(recs, "Method 2A")
    assert a.signal_candle_close == 100.8 and a.reference_levels["recent_support"] == 101
    assert a.signal_timestamp.strftime("%H:%M") == "09:45"
    assert a.verification_status == "PROPOSAL_DEPENDENT"  # 'recent support' is a proposal-based level
    assert not conf(recs, "Method 1") and not conf(recs, "Method 2B")  # one method at a time here


@pytest.mark.rules("IRF-M2A-002", "IRF-GLOBAL-003")
def test_m2a_wick_below_support_without_a_close_does_not_trigger():
    cands = M2A[:-1] + [(104, 104.2, 100.5, 101.5)]  # low pierces 101 but closes above it
    assert not conf(run(cands), "Method 2A")


@pytest.mark.rules("IRF-M2-002")
def test_m2_requires_extension_beyond_the_breakout_candle():
    cands = [IR, (98, 104, 97, 103), (103, 103.5, 101, 102), (102, 103, 100.2, 100.6), (100.6, 101, 100.1, 100.3),
             (100.3, 100.8, 100.0, 100.1)]  # lower highs only: never extends
    recs = run(cands)
    assert not conf(recs, "Method 2A") and not conf(recs, "Method 2B")


@pytest.mark.rules("IRF-M2-005")
def test_m2_red_candle_alone_is_not_confirmation():
    recs = run(M2A[:4])  # breakout, extension, red candle ... and then the session ends
    assert not conf(recs)
    assert any(r.signal_status == SignalStatus.INCOMPLETE_AT_EOD.value for r in recs)  # end-of-day incomplete setup


@pytest.mark.rules("IRF-M2-003", "IRF-M2A-002")
def test_m2a_chronology_break_candle_may_not_be_the_first_red_candle_by_default():
    seq = [IR, (98, 104, 97, 103), (103, 106, 101, 105), (101, 104, 100.5, 103.5), (103.5, 105, 101, 104.5),
           (104.5, 104.6, 99, 99.5), (99.5, 100, 98, 98.5)]
    default = [r.signal_candle_start.strftime("%H:%M") for r in conf(run(seq), "Method 2A")]
    variant = [r.signal_candle_start.strftime("%H:%M") for r in conf(run(seq, m2a_break_may_be_red_candle=True), "Method 2A")]
    assert default == ["09:45"] and variant == ["09:40"]  # strict order fires one candle later than the permissive reading


M2B_IR = (24060.0, 24081.75, 24039.95, 24070.0)  # IRH 24,081.75 / IRL 24,039.95 (p10)
M2B = [M2B_IR,
       (24070.0, 24110.0, 24068.0, 24100.0),   # breakout: closes above IRH
       (24100.0, 24128.75, 24095.0, 24120.0),  # first push tops out at 24,128.75 (recent resistance)
       (24120.0, 24122.0, 24100.0, 24105.0),   # pull back (red)
       (24105.0, 24135.0, 24103.0, 24130.0),   # trades back above 24,128.75 (green)
       (24130.0, 24131.0, 24120.0, 24123.5)]   # red candle closes back below it at 24,123.50


@pytest.mark.rules("IRF-M2B-001", "IRF-M2B-002", "IRF-M2B-003", "IRF-SL-001", "IRF-TGT-001")
def test_m2b_page10_worked_example_entry_stop_and_target():
    """(p10) entry 24,123.50 ; most recent green candle within 35 -> SL 24,158.50 ; target 60 below -> 24,063.50."""
    [b] = conf(run(M2B), "Method 2B")
    assert b.signal_candle_close == 24123.5 and b.reference_levels["recent_resistance"] == 24128.75
    assert b.reference_levels["IRH"] == 24081.75 and b.reference_levels["IRL"] == 24039.95
    cfg = policy_for("IRF", reference_price=b.reference_levels["recent_green_high"], entry=b.signal_candle_close)
    assert cfg.stop_points == 35.0
    lv = levels("SHORT", b.signal_candle_close, cfg)
    assert lv["stop"] == 24158.5 and lv["t2"] == 24063.5 and lv["t1"] == 24096.5


@pytest.mark.rules("IRF-M2B-002")
def test_m2b_requires_price_to_trade_back_above_resistance_first():
    cands = list(M2B)
    cands[4] = (24105.0, 24125.0, 24103.0, 24120.0)  # never trades above 24,128.75 again ...
    cands[5] = (24127.0, 24128.0, 24120.0, 24123.5)  # ... and the red candle's own high stays below it too
    assert not conf(run(cands), "Method 2B")
    cands2 = list(M2B)
    cands2[5] = (24130.0, 24131.0, 24129.0, 24130.0)  # still holding above the resistance
    assert not conf(run(cands2), "Method 2B")


@pytest.mark.rules("IRF-M2-004", "IRF-M1-002")
def test_conflicting_methods_on_one_candle_are_flagged_not_merged():
    seq = M2A[:5] + [(104, 104.2, 99, 99.5)]  # break closes inside the range after a close above it: M1 and M2A together
    recs = run(seq)
    m1, a = conf(recs, "Method 1")[0], conf(recs, "Method 2A")[0]
    assert m1.signal_timestamp == a.signal_timestamp
    assert m1.concurrent_methods == ["Method 2A"] and a.concurrent_methods == ["Method 1"]


# --------------------------------------------------------------------------- Method 3
M3_IR = (90, 100, 80, 95)  # IRH 100, IRL 80
M3 = [M3_IR, (94, 97, 88, 91), (91, 95, 85, 90), (90, 96, 86, 92), (92, 115, 81, 82)]


@pytest.mark.rules("IRF-M3-001", "IRF-M3-002", "IRF-M3-003", "IRF-M3-004", "IRF-M3-005")
def test_m3_page12_illustration_sweep_candle_closes_below_support():
    """(p12) IRH 100; red candle opens 92, high 115, close 82 (share 65%); support 85 broken -> confirmed."""
    [m] = conf(run(M3), "Method 3")
    assert m.signal_candle_close == 82 and m.reference_levels["recent_support"] == 85
    assert m.reference_levels["wick_share_outside_irh"] == pytest.approx(15 / 23)
    assert m.signal_timestamp.strftime("%H:%M") == "09:40"


@pytest.mark.rules("IRF-M3-005", "IRF-M3-006")
def test_m3_sweep_alone_is_never_enough_support_must_break():
    recs = run(M3[:-1] + [(92, 115, 81, 87)])  # same sweep, but it closes at 87 (above support 85)
    assert not conf(recs, "Method 3")
    [inv] = [r for r in recs if r.method == "Method 3"]
    assert inv.signal_status == "INVALIDATED" and "SUPPORT_NOT_BROKEN" in inv.invalidation_reason
    assert "IRF-M3-005" in inv.rule_ids_failed


@pytest.mark.rules("IRF-M3-003", "IRF-M3-006")
def test_m3_wick_that_barely_clears_irh_does_not_qualify():
    recs = run(M3[:-1] + [(92, 105, 81, 82)])  # share = 5/13 = 38%
    assert not conf(recs, "Method 3")
    assert [r.invalidation_reason for r in recs if r.method == "Method 3"] == ["WICK_SHARE_OUT_OF_BAND"]


@pytest.mark.rules("IRF-M3-001", "IRF-M3-006")
def test_m3_needs_compression_inside_the_range_not_a_trending_advance():
    recs = run([M3_IR, (94, 97, 88, 91), (91, 101, 85, 99), (99, 112, 98, 111), (111, 120, 81, 82)])
    assert not [r for r in recs if r.method == "Method 3"]  # preceding candles are not inside the range


@pytest.mark.rules("IRF-M3-002")
def test_m3_sweep_candle_must_be_red():
    assert not conf(run(M3[:-1] + [(82, 115, 81, 112)]), "Method 3")


# --------------------------------------------------------------------------- general
@pytest.mark.rules("IRF-DEF-001")
def test_red_and_green_candle_definitions_use_close_vs_open_and_a_doji_is_neither():
    from nifty_trading.strategies.definitions import Candle, is_green, is_red
    assert is_red(Candle(None, None, 10, 11, 9, 9.5, 0)) and not is_green(Candle(None, None, 10, 11, 9, 9.5, 0))
    assert is_green(Candle(None, None, 10, 11, 9, 10.5, 0)) and not is_red(Candle(None, None, 10, 11, 9, 10.5, 0))
    doji = Candle(None, None, 10, 11, 9, 10, 0)
    assert not is_red(doji) and not is_green(doji)


@pytest.mark.rules("IRF-M2-006")
def test_m2_setup_has_no_expiry_by_default_and_expiry_is_a_labelled_proposal():
    late = [IR, (98, 104, 97, 103), (103, 106, 102, 105)] + [(105, 106, 104.5, 105.2)] * 12 + [(105, 105.5, 100.5, 100.8)]
    base = run(late)
    assert not [r for r in base if r.invalidation_reason == "M2_EXPIRED"]
    exp = run(late, m2_expiry_candles=5)
    expired = [r for r in exp if r.invalidation_reason == "M2_EXPIRED"]
    assert expired and expired[0].signal_candle_start.strftime("%H:%M") == "09:20"  # the first breakout candle's attempt lapses first
    # a later candle that closes above IRH legitimately starts a NEW attempt (documented in ambiguous_rules.md)
    assert len(expired) >= 1 and not conf(exp, "Method 2A")


@pytest.mark.rules("IRF-GLOBAL-002")
def test_irf_is_short_only():
    for recs in (run([IR, (98, 104, 97, 103), (103, 103.5, 98, 99)]), run(M2B), run(M3), run(M2A)):
        assert {r.direction for r in recs} <= {"SHORT"}


@pytest.mark.rules("IRF-GLOBAL-001")
def test_initial_range_includes_wicks_not_just_the_body():
    # opening candle body is 98..95 but the wick reaches 110: a close at 105 is NOT above IRH=110
    recs = run([(95, 110, 90, 98), (98, 106, 97, 105), (105, 106, 96, 97)])
    assert not conf(recs)


@pytest.mark.rules("IRF-M2-001")
def test_data_gap_invalidates_an_open_setup_and_never_bridges_it():
    c = ctx([IR, (98, 104, 97, 103), (103, 106, 102, 105), (105, 106.5, 101, 102), (102, 105, 101.5, 104), (104, 104.2, 100.5, 100.8)])
    c.candles = c.candles.drop(index=3).reset_index(drop=True)  # the 09:30 candle is missing
    recs = IRFStrategy().evaluate_session(c)
    assert not conf(recs, "Method 2A")
    assert any(r.invalidation_reason == "DATA_GAP" for r in recs)


@pytest.mark.rules("IRF-GLOBAL-001")
def test_unusable_session_is_reported_not_silently_skipped():
    [r] = IRFStrategy().evaluate_session(ctx([IR, (98, 104, 97, 103)], usable=False))
    assert r.signal_status == "NOT_EVALUATED" and r.verification_status == "NOT_READY" and "SESSION_NOT_EVALUABLE" in r.invalidation_reason


def test_state_machine_enforces_order_and_chronology():
    from datetime import datetime
    t = datetime(2026, 1, 12, 9, 20)
    f = SetupFSM("x")
    with pytest.raises(IllegalTransition):
        f.to(State.SIGNAL_CONFIRMED, t, "skipped detection")
    f.to(State.SETUP_DETECTED, t, "a")
    with pytest.raises(IllegalTransition):
        f.to(State.WAITING_FOR_CONFIRMATION, datetime(2026, 1, 12, 9, 15), "earlier than the previous event")
    f.to(State.SIGNAL_CONFIRMED, t, "b")
    with pytest.raises(IllegalTransition):
        f.to(State.SETUP_INVALIDATED, t, "terminal")
