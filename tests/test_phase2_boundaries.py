"""Equality / ordering boundary tests added after the independent review found many surviving mutants."""

import math

import pytest
from synthetic import ctx

from nifty_trading.core.exit_policy import (
    Bar,
    ExitPolicyConfig,
    TradeOutcome,
    evaluate_exit,
    policy_for,
    select_stop_distance,
)
from nifty_trading.strategies import (
    IRFStrategy,
    ORBStrategy,
    PDRStrategy,
    PDSStrategy,
    ProposalConfig,
    RFStrategy,
)
from nifty_trading.strategies.definitions import (
    Candle,
    bearish_pin,
    strong_bearish,
    strong_bullish,
    trend_check,
)
from nifty_trading.strategies.params import TradeConfig

IR = (95, 100, 90, 98)  # IRH 100 / IRL 90
M2A = [IR, (98, 104, 97, 103), (103, 106, 102, 105), (105, 106.5, 101, 102), (102, 105, 101.5, 104), (104, 104.2, 100.5, 100.8)]
M3 = [(90, 100, 80, 95), (94, 97, 88, 91), (91, 95, 85, 90), (90, 96, 86, 92), (92, 115, 81, 82)]  # IRH 100, support 85


def irf(cands, **p):
    return IRFStrategy(proposals=ProposalConfig(**p)).evaluate_session(ctx(cands))


def conf(recs, m=None):
    return [r for r in recs if r.signal_status == "CONFIRMED" and (m is None or r.method == m)]


def m3_records(recs):
    return [r for r in recs if r.method == "Method 3"]


# ================================================================== IRF
@pytest.mark.rules("IRF-M1-002")
def test_irf_m1_close_exactly_at_irl_is_inside_the_range():
    assert conf(irf([IR, (98, 104, 97, 103), (103, 104, 90, 90)]), "Method 1")  # IRL <= close


@pytest.mark.rules("IRF-M1-001", "IRF-M2-001")
def test_irf_a_close_exactly_at_irh_does_not_start_a_breakout_attempt():
    cands = [IR, (98, 104, 97, 100)] + M2A[2:]  # candle 1 closes AT IRH (not above); the later candles would complete a Method 2A if it counted
    seq_attempt_from_candle_2 = conf(irf(cands), "Method 2A")
    assert not seq_attempt_from_candle_2


@pytest.mark.rules("IRF-M2A-002")
def test_irf_m2a_close_exactly_at_support_is_not_a_break():
    assert not conf(irf(M2A[:-1] + [(104, 104.2, 100.5, 101.0)]), "Method 2A")  # support is 101
    assert conf(irf(M2A[:-1] + [(104, 104.2, 100.5, 100.99)]), "Method 2A")


@pytest.mark.rules("IRF-M2B-003")
def test_irf_m2b_close_exactly_at_resistance_is_not_a_break_green_candle_never_counts():
    from test_phase2_irf import M2B
    ok = list(M2B)
    assert conf(irf(ok), "Method 2B")
    eq = list(M2B)
    eq[5] = (24130.0, 24131.0, 24120.0, 24128.75)  # red, closes exactly at the resistance
    assert not conf(irf(eq), "Method 2B")
    green = list(M2B)
    green[5] = (24110.0, 24127.0, 24109.0, 24125.0)  # closes below the resistance but is GREEN
    assert not conf(irf(green), "Method 2B")


@pytest.mark.rules("IRF-M2B-002")
def test_irf_m2b_the_closing_candle_may_itself_be_the_one_that_pushed_above_by_default():
    from test_phase2_irf import M2B
    c = list(M2B)
    c[4] = (24105.0, 24125.0, 24103.0, 24120.0)  # earlier candle stays below the resistance
    assert conf(irf(c), "Method 2B")  # candle 5 itself trades above 24,128.75 (high 24,131) then closes back below
    assert not conf(irf(c, m2b_push_must_precede_red_candle=True), "Method 2B")  # proposal: a separate earlier push is required


@pytest.mark.rules("IRF-M2B-001")
def test_irf_resistance_default_is_the_first_push_not_the_latest_swing_high():
    # two swing highs after the breakout: 106 (first push) then 108 (latest). The red candle closes at 105.5 (< 106 but, with 108, also < 108).
    c = [IR, (98, 104, 97, 103), (103, 106, 102, 105), (105, 105.5, 103, 104), (104, 108, 103.5, 107), (107, 107.5, 104, 106.5), (106.5, 107, 105, 105.5)]
    r = conf(irf(c), "Method 2B")
    assert r and r[0].reference_levels["recent_resistance"] == 106  # FIRST_PUSH_TOP: price traded back above 106 (to 108) then closed below it
    assert not conf(irf(c, irf_resistance_def="LATEST_SWING_HIGH"), "Method 2B")  # latest swing high 108 was never exceeded afterwards


@pytest.mark.rules("IRF-M2-002")
def test_irf_extension_needs_a_strictly_higher_high_than_the_breakout_candle():
    # no later candle ever exceeds the breakout candle's high (104); candle 2 merely EQUALS it. Support 101 breaks at candle 5.
    c = [IR, (98, 104, 97, 103), (103, 104, 102, 103.5), (103.5, 103.8, 101, 102), (102, 103.5, 101.5, 103), (103, 103.2, 100.5, 100.8)]
    recs = irf(c)
    assert not conf(recs, "Method 2A") and not conf(recs, "Method 2B")  # nothing else can fire, so only the extension rule decides
    higher = [*c[:2], (103, 104.5, 102, 103.5), *c[3:]]  # one tick above the breakout high: now it IS an extension
    assert conf(irf(higher), "Method 2A")


@pytest.mark.rules("IRF-M2-003")
def test_irf_m2_extension_candle_cannot_be_the_red_candle_by_default():
    c = [IR, (98, 104, 97, 103), (105, 108, 101, 102), (101, 104, 100.8, 103), (103, 104.2, 101.5, 104), (104, 104.1, 100, 100.4)]
    # candle 2 is red AND the first to extend; candles 3-4 are green; candle 5 is red and breaks support 100.8
    assert not conf(irf(c), "Method 2A")
    assert conf(irf(c, m2_red_may_be_extension_candle=True), "Method 2A")


@pytest.mark.rules("IRF-M2A-001")
def test_irf_support_pivot_ties_still_count_as_a_swing_low():
    c = list(M2A)
    c[4] = (102, 105, 101.0, 104)  # low equals the pivot candle's low (101): still a swing low
    assert conf(irf(c[:5] + [(104, 104.2, 100.5, 100.8)]), "Method 2A")


@pytest.mark.rules("IRF-M3-002", "IRF-M3-005")
def test_irf_m3_boundaries_high_equal_irh_and_close_equal_support():
    assert not m3_records(irf(M3[:-1] + [(92, 100, 81, 82)]))  # high == IRH: not a sweep above IRH
    inv = m3_records(irf(M3[:-1] + [(92, 115, 81, 85)]))  # closes exactly at support 85
    assert [r.invalidation_reason.split("(")[0] for r in inv] == ["SUPPORT_NOT_BROKEN"]


@pytest.mark.rules("IRF-M3-001")
def test_irf_m3_compression_candles_may_touch_the_range_edges_and_exclude_the_opening_candle():
    touching = [M3[0], M3[1], (91, 100, 85, 90), M3[3], M3[4]]  # a compression candle with high == IRH is still inside
    assert conf(irf(touching), "Method 3")
    early = [M3[0], M3[1], (92, 115, 81, 82)]  # sweep at index 2: the opening candle would have to be part of the compression
    assert not m3_records(irf(early))


@pytest.mark.rules("IRF-SL-001", "IRF-M1-004")
def test_irf_stop_reference_includes_the_signal_candle_when_it_is_green():
    # candle 2 closes back inside the range AND is green (opens 98.5, closes 99.5): it is the most recent green candle
    r = conf(irf([IR, (98, 104, 97, 103), (98.5, 103.5, 98, 99.5)]), "Method 1")[0]
    assert r.reference_levels["recent_green_high"] == 103.5 and r.reference_levels["recent_green_close"] == 99.5


@pytest.mark.rules("IRF-GLOBAL-004", "IRF-GLOBAL-005")
def test_irf_signals_are_never_verified_while_scope_is_undefined_and_concurrent_methods_are_not_merged():
    recs = irf(M2A[:5] + [(104, 104.2, 99, 99.5)])  # one failure that satisfies Method 1 and Method 2A together
    assert {r.method for r in conf(recs)} == {"Method 1", "Method 2A"}
    for r in conf(recs):
        assert r.verification_status == "PROPOSAL_DEPENDENT" and "IRF-GLOBAL-004" in r.rule_ids_unresolved
        assert r.concurrent_methods and r.method not in r.concurrent_methods
    # without a cap, repeated oscillations across IRH produce several Method 1 signals in one session
    many = [IR] + [(98, 104, 97, 103), (103, 103.5, 98, 99)] * 3
    assert len(conf(irf(many), "Method 1")) == 3


# ================================================================== RF
RFP = {"cands": [(24000, 24100, 23900, 24000)], "close": 24000.0, "ema_last": 23950.0}


def rf(c, prev=RFP, **p):
    p.setdefault("trend_mode", "EMA5M_PREV_SESSION")  # these fixtures test other logic with the Phase 2.1 trend posal; the structure mode is tested in test_phase22_rules
    return RFStrategy(proposals=ProposalConfig(**p)).evaluate_session(ctx(c, prev=prev, ema=23950.0))


@pytest.mark.rules("RF-005")
def test_rf_a_close_exactly_at_rf_low_is_not_a_close_below():
    assert not conf(rf([(24020, 24040, 24000, 24030), (24030, 24032, 23985, 24000), (24000, 24020, 23998, 24015)]))


@pytest.mark.rules("RF-006")
@pytest.mark.parametrize("close,ok", [(24000.0, True), (24040.0, True), (23999.95, False), (24040.05, False)])
def test_rf_return_inside_includes_both_range_edges(close, ok):
    c = [(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 24045, 23988, close)]
    assert bool(conf(rf(c))) is ok


@pytest.mark.rules("RF-004")
def test_rf_open_exactly_at_yesterdays_high_or_low_is_within_the_range():
    hi = rf([(24100, 24120, 24080, 24110), (24110, 24112, 24070, 24075), (24075, 24110, 24074, 24090)])  # open == PrevHigh
    assert conf(hi)
    prev_low = {"cands": [(24000, 24100, 24000, 24000)], "close": 23990.0, "ema_last": 23950.0}  # PrevLow 24000, PrevClose 23990
    lo = rf([(24000, 24040, 23995, 24030), (24030, 24032, 23985, 23990), (23990, 24020, 23988, 24015)], prev=prev_low)  # open == PrevLow
    assert conf(lo)


@pytest.mark.rules("RF-003", "PDR-004")
def test_flat_open_equal_to_previous_close_is_no_gap_for_rf_and_pdr():
    flat = {"cands": [(24000, 24100, 23900, 24000)], "close": 24020.0, "ema_last": 23950.0}  # open 24020 == close
    [r] = rf([(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 24020, 23988, 24015)], prev=flat)
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "GAP_NOT_UP(NONE)"
    pdr_prev = {"cands": [(23980, 24000, 23970, 23975)], "close": 24050.0}
    assert PDRStrategy().evaluate_session(ctx([(24050, 24060, 24001, 24003), (24003, 24030, 24002, 24025)], prev=pdr_prev)) == []


# ================================================================== PDR / PDS
PDRP = {"cands": [(23960, 23970, 23950, 23965), (23980, 24000, 23970, 23975), (23975, 23985, 23960, 23962)], "close": 23950.0}  # zone [23975, 24000]
PDSP = {"cands": [(24040, 24050, 24030, 24045), (24020, 24030, 24000, 24010), (24010, 24060, 24005, 24055)], "close": 24100.0}  # zone [24000, 24020]


def pdr(c, prev=PDRP, **p):
    p.setdefault("pdr_zone_method", "A_HIGHEST_HIGH")  # fixtures use the highest-high candle, a DIAGNOSTIC reference since Phase 2.3
    p.setdefault("zone_lower_boundary", "ZONE_FULL")  # fixtures written for the full-body candidate
    p.setdefault("zone_proximity_points", 5.0)  # near-touch variant; the strict default is tested in test_phase22_rules
    return PDRStrategy(proposals=ProposalConfig(**p)).evaluate_session(ctx(c, prev=prev))


def pds(c, prev=PDSP, **p):
    p.setdefault("zone_proximity_points", 5.0)  # near-touch variant; the strict default is tested in test_phase22_rules
    return PDSStrategy(proposals=ProposalConfig(**p)).evaluate_session(ctx(c, prev=prev))


@pytest.mark.rules("PDR-006")
def test_pdr_touch_is_inclusive_and_candle_zero_can_be_the_interaction_candle():
    base = [(24050, 24060, 24040, 24055)]
    assert conf(pdr(base + [(24055, 24058, 24000.0, 24003), (24003, 24030, 24002, 24025)], zone_proximity_points=0.0))  # low == zone high
    assert not conf(pdr(base + [(24055, 24058, 24000.05, 24003), (24003, 24030, 24002, 24025)], zone_proximity_points=0.0))
    first = pdr([(24050, 24055, 24001, 24003), (24003, 24030, 24002, 24025)])  # the opening candle itself tests the zone
    assert [r.signal_timestamp.strftime("%H:%M") for r in conf(first)] == ["09:25"]


@pytest.mark.rules("PDR-011", "PDS-006")
def test_open_exactly_at_the_zone_edge_does_not_clear_the_zone():
    [r] = pdr([(24000, 24010, 23995, 24005), (24005, 24020, 24000, 24015)], pdr_open_vs_zone="ABOVE_ZONE")
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "GAP_UP_OPEN_NOT_ABOVE_ZONE"  # open == zone_high 24000
    assert not conf(pdr([(24000, 24010, 23995, 24005), (24005, 24020, 24000, 24015)]))  # default = the text: an open at the zone edge is not above it
    assert conf(pdr([(24000, 24010, 23995, 24005), (24005, 24020, 24000, 24015)], pdr_open_vs_zone="ANY"))
    [s] = pds([(24000, 24015, 23990, 23995), (23995, 24000, 23980, 23985)])
    assert s.signal_status == "INVALIDATED" and s.invalidation_reason == "GAP_DOWN_OPEN_NOT_BELOW_ZONE"  # open == zone_low 24000


@pytest.mark.rules("PDS-M-001", "PDS-005")
def test_pds_a_candle_entirely_above_the_zone_band_is_not_at_the_zone():
    # first test candle touches from below, then a strong red candle forms ABOVE zone_high + proximity (24,025)
    c = [(23950, 23960, 23940, 23945), (23990, 23996, 23985, 23994), (24060, 24070, 24030, 24032)]
    assert not conf(pds(c), "Method 1")


@pytest.mark.rules("PDS-M2-001")
def test_pds_pin_bar_must_push_into_or_above_the_zone_not_merely_approach_it():
    pin_below = [(23950, 23960, 23940, 23945), (23990.5, 23999, 23989.8, 23990)]  # long upper wick, high 23,999 < zone_low 24,000
    assert not conf(pds(pin_below), "Method 2")


@pytest.mark.rules("PDS-M3-001")
def test_pds_method3_close_exactly_at_the_small_support_is_not_a_break():
    base = [(23950, 23960, 23940, 23945), (24010, 24012, 24004, 24006), (24006, 24008, 24000, 24005), (24005, 24010, 24003, 24009)]
    assert conf(pds(base + [(24009, 24010, 23980, 23985)]))
    assert not conf(pds(base + [(24009, 24010, 23980, 24000)]))  # closes exactly at support 24,000


# ================================================================== ORB
ORBP = {"cands": [(23900, 24000, 23800, 23900)], "close": 23900.0, "ema_last": 23950.0}
GAP_PREV = {"cands": [(23900, 24200, 23800, 23900)], "close": 23900.0, "ema_last": 23950.0}


def orb(c0, prev=ORBP, ema=23950.0, **p):
    p.setdefault("trend_mode", "EMA5M_PREV_SESSION")  # these fixtures test other logic with the Phase 2.1 trend posal; the structure mode is tested in test_phase22_rules
    return ORBStrategy(proposals=ProposalConfig(**p)).evaluate_session(ctx([c0, (c0[3], c0[3] + 1, c0[3] - 1, c0[3])], prev=prev, ema=ema))


@pytest.mark.rules("ORB-TREND-002")
def test_orb_trend_needs_a_close_strictly_beyond_the_ema():
    [r] = [x for x in orb((24005, 24060, 24000, 24055), ema=24055.0) if x.method == "Method 1"]
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason.startswith("TREND:")
    c = ctx([(24005, 24060, 24000, 24055)], ema=24055.0)
    assert trend_check(c, 0, "LONG", "EMA5M_BASIC").ok is False and trend_check(c, 0, "SHORT", "EMA5M_BASIC").ok is False


@pytest.mark.rules("ORB-GAP-LONG-002", "ORB-GAP-LONG-003")
def test_orb_gap_boundaries_crossing_and_close_beyond_are_strict():
    eq_prev = {**GAP_PREV, "close": 23950.0}  # previous close == MA: price was not below it
    assert not [x for x in orb((24005, 24060, 24000, 24055), prev=eq_prev) if x.method == "Gap/200DMA"]
    [x] = [x for x in orb((23960, 23970, 23900, 23950), prev=GAP_PREV) if x.method == "Gap/200DMA"]
    assert x.invalidation_reason == "CLOSE_NOT_BEYOND_MA"  # close == MA


@pytest.mark.rules("ORB-GAP-LONG-005")
def test_orb_gap_cap_is_exclusive_at_the_boundary():
    gap = 24005 - 23900  # 105 points
    assert [x.signal_status for x in orb((24005, 24060, 24000, 24055), prev=GAP_PREV, gap_max_points=float(gap)) if x.method == "Gap/200DMA"] == ["CONFIRMED"]
    assert [x.signal_status for x in orb((24005, 24060, 24000, 24055), prev=GAP_PREV, gap_max_points=gap - 0.01) if x.method == "Gap/200DMA"] == ["INVALIDATED"]


@pytest.mark.rules("ORB-CANDLE-001")
def test_candle_shape_thresholds_are_inclusive_at_the_boundary():
    mod = ProposalConfig()  # MODERATE: body >= .60, opposite wick <= .20
    assert strong_bullish(Candle(None, None, 102, 110, 100, 108, math.nan), mod)  # body .6, upper wick .2 exactly
    assert not strong_bullish(Candle(None, None, 102, 110, 100, 107, math.nan), mod)  # body .5
    assert strong_bearish(Candle(None, None, 108, 110, 100, 102, math.nan), mod)
    pin = ProposalConfig(pin_bar="MODERATE")  # upper wick >= .60, body <= .33, opposite wick <= .15
    assert bearish_pin(Candle(None, None, 104, 110, 100, 101, math.nan), pin)  # upper wick exactly .6, body .3, lower wick .1
    assert not bearish_pin(Candle(None, None, 104.5, 110, 100, 101, math.nan), pin)  # upper wick .55


@pytest.mark.rules("ORB-M1-LONG-003", "ORB-CANDLE-001")
def test_orb_conditional_pin_bar_is_accepted_in_method1_as_a_labelled_proposal():
    pin = (24020, 24024, 24000, 24022)  # long lower wick? body small, lower wick 20/24: bullish pin that closes beyond the level
    on = [x for x in orb(pin) if x.method == "Method 1"]
    off = [x for x in orb(pin, orb_pin_bar_in_methods_1_2=False) if x.method == "Method 1"]
    assert on and on[0].signal_status == "CONFIRMED"
    assert off and off[0].signal_status == "INVALIDATED"


# ================================================================== exits
E = 24000.0
CFG = policy_for("ORB")


@pytest.mark.rules("EXE-BE-001", "EXE-MISSING-001")
def test_breakeven_stop_gapped_through_fills_at_the_open_not_at_entry():
    t1_bar = Bar("m0", E, E + 28, E + 5, E + 20)
    r = evaluate_exit("LONG", E, [t1_bar, Bar("m1", E - 20, E - 10, E - 25, E - 12)], CFG)  # opens 20 below entry, 14 beyond the E - 6 stop
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 20
    assert r.pnl_rupees == 27 * 195 - 20 * 195 == 1365  # the gap fills at the OPEN (worse than the stop level)
    assert r.adverse_slippage_points == 14  # logged: the fill is 14 points worse than the E - 6 stop
    s = evaluate_exit("SHORT", E, [Bar("m0", E, E - 5, E - 28, E - 20), Bar("m1", E + 20, E + 25, E + 10, E + 12)], CFG)
    assert s.leg2_exit == E + 20 and s.pnl_rupees == 1365 and s.adverse_slippage_points == 14


@pytest.mark.rules("EXE-MISSING-001")
def test_an_exact_touch_of_a_stop_or_target_counts_as_hit():
    assert evaluate_exit("LONG", E, [Bar("m0", E, E, E - 30, E - 1)], CFG).outcome is TradeOutcome.STOP_LOSS  # low == stop
    assert evaluate_exit("LONG", E, [Bar("m0", E, E + 5, E - 29.99, E)], CFG).outcome is TradeOutcome.INCOMPLETE_EOD
    r = evaluate_exit("LONG", E, [Bar("m0", E, E + 27, E + 2, E + 20), Bar("m1", E + 20, E + 60, E + 10, E + 50)], CFG)
    assert r.outcome is TradeOutcome.TARGET  # high == T1, then high == T2


@pytest.mark.rules("IRF-SL-001")
def test_stop_distance_uses_the_absolute_distance_documented_as_a_proposal():
    assert select_stop_distance(E, E - 20) == 35.0 and select_stop_distance(E, E - 50) == 40.0  # sign ignored (AMB-IRF-12)
    assert policy_for("IRF", reference_price=E + 36, entry=E, trade=TradeConfig(stop_variant="SOURCE_35_40_BY_DISTANCE")).stop_points == 40.0
    assert policy_for("IRF", reference_price=E + 36, entry=E).stop_points == 35.0  # baseline ignores the measurement
    assert ExitPolicyConfig(t2_points=60, stop_points=30).missing == ()


# ================================================================== survivors of the first mutation run
@pytest.mark.rules("ORB-TREND-001", "RF-008")
def test_prev_3_sessions_mode_needs_all_three_sessions_on_the_trend_side():
    base = [(100, 101, 99, 100.5)]
    assert trend_check(ctx(base, ema=90.0, prior_above=(True, True, True)), 0, "LONG", "EMA5M_PREV_3_SESSIONS").ok is True
    assert trend_check(ctx(base, ema=90.0, prior_above=(True, True, False)), 0, "LONG", "EMA5M_PREV_3_SESSIONS").ok is False  # third-oldest below
    assert trend_check(ctx(base, ema=90.0, prior_above=(True, True, False)), 0, "LONG", "EMA5M_PREV_SESSION").ok is True


@pytest.mark.rules("PDR-002")
def test_pdr_zone_tie_break_picks_the_first_or_last_candle_sharing_the_days_high():
    prev = {"cands": [(23960, 23970, 23950, 23965), (23990, 24000, 23980, 23985), (23995, 24000, 23970, 23972), (23975, 23985, 23960, 23962)],
            "close": 23950.0}  # candles 1 and 2 both have high 24,000; bodies [23985, 23990] vs [23972, 23995]
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)]
    first = conf(pdr(cands, prev=prev))[0].reference_levels
    last = conf(pdr(cands, prev=prev, zone_tie_break="LAST"))[0].reference_levels
    assert first["zone_low"] == 23985 and last["zone_low"] == 23972


@pytest.mark.rules("ORB-GAP-LONG-002")
def test_orb_gap_crossing_compares_the_previous_close_with_the_ma_AT_that_close():
    prev = {"cands": [(23900, 24200, 23800, 23960)], "close": 23960.0, "ema_last": 23970.0}  # was below the MA (23,970) at yesterday's close
    # today's EMA is 23,950, below yesterday's close; the gap still crossed the MA that price was below
    g = [x for x in orb((24005, 24060, 24000, 24055), prev=prev, ema=23950.0) if x.method == "Gap/200DMA"]
    assert [x.signal_status for x in g] == ["CONFIRMED"]


def _m2_prev(modify_high=None):
    from test_phase2_orb import _prev_session_with_trendline
    prev = _prev_session_with_trendline()
    if modify_high is not None:
        prev["cands"] = [modify_high(i, c) for i, c in enumerate(prev["cands"])]
    return prev


@pytest.mark.rules("ORB-M2-LONG-004")
def test_orb_m2_near_band_is_inclusive_and_the_close_margin_is_exclusive():
    prev = _m2_prev()
    c0 = (24010, 24070, 24005, 24065)
    def m2(ema, **p):
        return [x for x in orb(c0, prev=prev, ema=ema, **p) if x.method == "Method 2"][0]
    # distance 15 == near band, margin 20 -> near and not convincing
    assert m2(24050.0, ma_near_band_points=15.0, ma_close_margin_points=20.0).invalidation_reason == "NEAR_MA_NOT_CONVINCING"
    assert m2(24049.5, ma_near_band_points=15.0, ma_close_margin_points=20.0).signal_status == "CONFIRMED"  # 15.5 > band: not near
    # distance 15 == margin 15 inside the band -> margin reached, passes
    assert m2(24050.0, ma_near_band_points=20.0, ma_close_margin_points=15.0).signal_status == "CONFIRMED"
    assert m2(24050.5, ma_near_band_points=20.0, ma_close_margin_points=15.0).invalidation_reason == "NEAR_MA_NOT_CONVINCING"  # 14.5 < margin


@pytest.mark.rules("ORB-M2-LONG-001")
def test_orb_m2_inner_level_must_lie_strictly_inside_the_previous_days_range():
    def flatten(i, c):  # remove the inner fractal high (index 10) so the only fractal high is the day's own high
        if i == 10:
            o, h, l, cl = c
            return (o, 23900 + 2 * 45, l, cl)
        return c
    recs = orb((24010, 24070, 24005, 24065), prev=_m2_prev(flatten), ema=23900.0)
    assert not [x for x in recs if x.method == "Method 2"]  # a level equal to the previous high is not an INNER level


@pytest.mark.rules("PDS-005")
def test_pds_touch_boundary_high_exactly_at_zone_low_minus_proximity_counts():
    c = [(23950, 23960, 23940, 23945), (23995, 23995, 23970, 23972)]  # strong red, high == zone_low (24,000) - 5
    assert [r.method for r in conf(pds(c))] == ["Method 1"]
    c2 = [(23950, 23960, 23940, 23945), (23994, 23994.95, 23970, 23972)]  # 0.05 short of the band
    assert not conf(pds(c2))


@pytest.mark.rules("PDS-M3-001")
def test_pds_small_support_must_be_near_the_zone_not_far_above_it():
    c = [(23950, 23960, 23940, 23945), (24010, 24012, 24004, 24006),            # weak first red candle at the zone
         (24100, 24110, 24090, 24105), (24105, 24112, 24080, 24095), (24095, 24110, 24085, 24100),  # a swing low at 24,080, far above the zone
         (24100, 24101, 24060, 24070)]                                          # closes below that swing low
    assert not conf(pds(c))


@pytest.mark.rules("EXE-BE-001", "EXE-MISSING-001")
def test_same_bar_target1_and_breakeven_fills_the_leg2_stop_at_the_worse_of_entry_and_open():
    # one bar opens 5 BELOW entry, then reaches Target 1: the order is unknowable, the adverse reading is a breakeven exit at the open
    # the bar opens 8 below entry (2 beyond the E - 6 level), but the post-T1 stop only exists once Target 1 is booked later in that bar: the open
    # predates it, so it is NOT a gap through an active stop - the adverse reading fills Leg 2 at the stop LEVEL with no slippage
    r = evaluate_exit("LONG", E, [Bar("m0", E - 8, E + 28, E - 9, E + 20)], CFG)
    assert r.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and r.leg2_exit == E - 6 and r.ambiguities
    assert r.pnl_rupees == 27 * 195 - 6 * 195 == 4095 and r.adverse_slippage_points == 0
    s = evaluate_exit("SHORT", E, [Bar("m0", E + 8, E + 9, E - 28, E - 20)], CFG)
    assert s.leg2_exit == E + 6 and s.pnl_rupees == 4095 and s.adverse_slippage_points == 0


@pytest.mark.rules("RF-001")
def test_rf_trend_is_judged_at_the_opening_candle_not_at_the_return_inside_candle():
    cands = [(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 24020, 23988, 24015)]
    ema = [23950.0, 23950.0, 24100.0]  # price is above the EMA when RF is armed (candle 0) but below it when it returns inside
    recs = RFStrategy(proposals=ProposalConfig(trend_mode="EMA5M_PREV_SESSION")).evaluate_session(ctx(cands, prev=RFP, ema=ema))
    assert [r.signal_status for r in recs] == ["CONFIRMED"]
    below_at_open = RFStrategy(proposals=ProposalConfig(trend_mode="EMA5M_PREV_SESSION")).evaluate_session(ctx(cands, prev=RFP, ema=[24100.0, 23950.0, 23950.0]))
    assert [r.signal_status for r in below_at_open] == ["INVALIDATED"] and below_at_open[0].invalidation_reason.startswith("TREND:")


@pytest.mark.rules("PDR-011")
def test_pdr_not_below_zone_allows_an_open_exactly_at_the_zone_low():
    ok = [(23975, 23980, 23974, 23976), (23976, 23990, 23975, 23988)]  # zone [23975, 24000]; open == zone low
    assert conf(pdr(ok, pdr_open_vs_zone="NOT_BELOW_ZONE"))
    below = [(23974.95, 23980, 23974, 23976), (23976, 23990, 23975, 23988)]
    [r] = pdr(below, pdr_open_vs_zone="NOT_BELOW_ZONE")
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "GAP_UP_OPEN_BELOW_ZONE"


@pytest.mark.rules("PDS-006")
def test_pds_not_above_zone_allows_an_open_exactly_at_the_zone_high():
    at = [(24020, 24021, 24010, 24012), (24012, 24014, 24000, 24005)]  # zone [24000, 24020]; open == zone high
    assert all(r.invalidation_reason != "GAP_DOWN_OPEN_ABOVE_ZONE" for r in pds(at, pds_open_vs_zone="NOT_ABOVE_ZONE"))
    above = [(24020.05, 24021, 24010, 24012), (24012, 24014, 24000, 24005)]
    assert [r.invalidation_reason for r in pds(above, pds_open_vs_zone="NOT_ABOVE_ZONE")] == ["GAP_DOWN_OPEN_ABOVE_ZONE"]
