"""Phase 2.2: user-approved stop baseline, structure trend, swing points, execution eligibility, selection policies.

Everything here is synthetic. No test uses the performance report's profit figures as an acceptance criterion.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from synthetic import PREV_DAY, ctx, frame

from nifty_trading.core.execution_eligibility import (
    BarEligibility,
    classify_bar,
    entry_executable,
    is_executable,
)
from nifty_trading.core.exit_policy import (
    Bar,
    EodPolicy,
    ExitPolicyConfig,
    TradeOutcome,
    evaluate_exit,
    policy_for,
)
from nifty_trading.strategies import (
    IRFStrategy,
    ORBStrategy,
    PDRStrategy,
    PDSStrategy,
    ProposalConfig,
    RFStrategy,
)
from nifty_trading.strategies.base import Direction, SignalStatus
from nifty_trading.strategies.definitions import (
    Candle,
    bearish_pin,
    bullish_pin,
    confirmed_swing_highs,
    confirmed_swing_lows,
    is_small,
    strong_bearish,
    strong_bullish,
    structure_trend,
    trend_check,
)
from nifty_trading.strategies.params import (
    DEFAULT_TRADE,
    STOP_ALTERNATE,
    STOP_BASELINE,
    TradeConfig,
)
from nifty_trading.strategies.selection import (
    NO_POSITION,
    SelectionPolicy,
    apply_policy,
    fill_from_next_bar,
    position_end_from_result,
    simulate_exit,
)

IST = ZoneInfo("Asia/Kolkata")
E = 24000.0


def B(i, o, h, l, c, executable=True):  # noqa: E741
    return Bar(f"m{i}", o, h, l, c, executable)


def C(o, h, l, c, ema=math.nan):  # noqa: E741
    t = datetime(2026, 1, 9, 9, 15, tzinfo=IST)
    return Candle(t, t + timedelta(minutes=5), o, h, l, c, ema)


# ======================================================================= stop-loss baseline (user-approved)
@pytest.mark.rules("EXE-STOP-001")
@pytest.mark.parametrize("strategy,expected", [("IRF", 35.0), ("PDR", 35.0), ("PDS", 35.0), ("RF", 35.0), ("ORB", 30.0)])
def test_default_stop_is_the_user_approved_35_and_orb_keeps_its_documented_30(strategy, expected):
    pol = policy_for(strategy)
    assert pol.stop_points == expected and DEFAULT_TRADE.stop_points(strategy) == expected == STOP_BASELINE[strategy]
    assert pol.stop_status == ("VERIFIED_EXPLICIT" if strategy == "ORB" else "USER_APPROVED")
    assert pol.stop_variant == "BASELINE" and pol.execution_status == "RESEARCH_ONLY"


@pytest.mark.rules("EXE-STOP-001")
@pytest.mark.parametrize("strategy,expected", [("IRF", 40.0), ("PDR", 40.0), ("PDS", 40.0), ("RF", 40.0), ("ORB", 30.0)])
def test_alternate_stop_is_40_for_the_four_strategies_and_orb_is_preserved(strategy, expected):
    pol = policy_for(strategy, trade=TradeConfig(stop_variant="ALTERNATE_40"))
    assert pol.stop_points == expected == STOP_ALTERNATE[strategy]
    assert pol.stop_status == ("VERIFIED_EXPLICIT" if strategy == "ORB" else "PROPOSED_FOR_REVIEW")  # a sensitivity variant, not approved


@pytest.mark.rules("EXE-STOP-001")
def test_the_stop_distance_actually_moves_the_stop_level_and_the_loss():
    for variant, dist in (("BASELINE", 35.0), ("ALTERNATE_40", 40.0)):
        pol = policy_for("IRF", trade=TradeConfig(stop_variant=variant))
        r = evaluate_exit("SHORT", E, [B(0, E, E + dist, E - 1, E + dist - 1)], pol)
        assert r.outcome is TradeOutcome.STOP_LOSS and r.stop_level == E + dist
        assert r.pnl_rupees == -dist * 390
    # one point short of the stop does not stop out
    r = evaluate_exit("SHORT", E, [B(0, E, E + 34.99, E - 1, E)], policy_for("IRF"))
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD


@pytest.mark.rules("EXE-STOP-001")
def test_unknown_stop_variant_is_rejected():
    with pytest.raises(Exception, match="stop_variant"):
        TradeConfig(stop_variant="OPTIMISED")


@pytest.mark.rules("EXE-STOP-001", "EXE-T2-001")
def test_target_table_statuses_never_promote_rf_or_hide_the_pdr_pds_conflict():
    assert [(s, policy_for(s).t2_points) for s in ("IRF", "ORB", "PDR", "PDS", "RF")] == [
        ("IRF", 60.0), ("ORB", 60.0), ("PDR", 70.0), ("PDS", 70.0), ("RF", 60.0)]
    assert policy_for("RF").t2_status == "PROPOSED_FOR_REVIEW"
    assert all(policy_for(s).t2_status == "VERIFIED_EXPLICIT" for s in ("IRF", "ORB"))
    assert all(policy_for(s).t2_status == "CONFLICTING" for s in ("PDR", "PDS"))  # guide says 70, the report's winners disagree
    assert policy_for("PDR").conflicts and policy_for("PDS").conflicts and not policy_for("IRF").conflicts


# ======================================================================= signal carries the configuration that produced it
@pytest.mark.rules("EXE-STOP-001", "IRF-M1-001")
def test_signal_records_the_rule_configuration_and_is_never_marked_verified_wholesale():
    IR = (95, 100, 90, 98)
    [m1] = [r for r in IRFStrategy().evaluate_session(ctx([IR, (98, 104, 97, 103), (103, 103.5, 98, 99)])) if r.signal_status == "CONFIRMED"]
    ec = m1.execution_config
    assert (ec["strategy"], ec["method"]) == ("IRF", "Method 1")
    assert (ec["stop_distance"], ec["stop_status"], ec["target_1"], ec["target_2"], ec["target_2_status"]) == (35.0, "USER_APPROVED", 27.0, 60.0, "VERIFIED_EXPLICIT")
    assert ec["trend_mode"] == "NOT_APPLICABLE" and ec["execution_status"] == "RESEARCH_ONLY"
    assert ec["entry_rule_status"] == "PROPOSAL_DEPENDENT" != "VERIFIED_EXPLICIT"  # IRF-GLOBAL-004 is unresolved
    alt = IRFStrategy(trade=TradeConfig(stop_variant="ALTERNATE_40")).evaluate_session(ctx([IR, (98, 104, 97, 103), (103, 103.5, 98, 99)]))
    assert [r for r in alt if r.signal_status == "CONFIRMED"][0].execution_config["stop_distance"] == 40.0


@pytest.mark.rules("EXE-STOP-001")
def test_engines_report_trend_mode_only_where_a_trend_proposal_is_used():
    assert IRFStrategy().exec_config("Method 1", "X", "RESEARCH_ONLY")["trend_mode"] == "NOT_APPLICABLE"
    assert PDRStrategy().exec_config("PDR", "X", "RESEARCH_ONLY")["trend_mode"] == "NOT_APPLICABLE"
    assert PDSStrategy().exec_config("Method 1", "X", "RESEARCH_ONLY")["trend_mode"] == "NOT_APPLICABLE"
    assert RFStrategy().exec_config("RF", "X", "RESEARCH_ONLY")["trend_mode"] == ProposalConfig().trend_mode
    orb = ORBStrategy()
    assert orb.exec_config("Method 1", "X", "RESEARCH_ONLY")["trend_mode"] == ProposalConfig().trend_mode
    assert orb.exec_config("Gap/200DMA", "X", "RESEARCH_ONLY")["trend_mode"] == "NOT_APPLICABLE"
    assert RFStrategy().exec_config("RF", "X", "RESEARCH_ONLY")["target_2_status"] == "PROPOSED_FOR_REVIEW"


# ======================================================================= swing points (TREND-SWING-001)
@pytest.mark.rules("TREND-SWING-001")
def test_swing_high_is_strict_and_needs_two_candles_each_side():
    cs = [C(1, h, 0, 1) for h in (5, 6, 9, 6, 5)]
    assert confirmed_swing_highs(cs, 4) == [2]
    assert confirmed_swing_highs([C(1, h, 0, 1) for h in (5, 6, 9, 9, 5)], 4) == []  # an equal neighbour is not "exceeds"
    assert confirmed_swing_highs([C(1, h, 0, 1) for h in (5, 9, 9, 6, 5)], 4) == []
    assert confirmed_swing_highs(cs, 4, k=1) == [2]


@pytest.mark.rules("TREND-SWING-001")
def test_swing_point_is_unknown_until_the_second_following_candle_has_closed():
    cs = [C(1, h, 0, 1) for h in (5, 6, 9, 6, 5)]
    assert confirmed_swing_highs(cs, 3) == []  # only one candle after the peak has closed
    assert confirmed_swing_highs(cs, 2) == []
    assert confirmed_swing_highs(cs, 4) == [2]  # confirmed exactly when candle j+2 has closed
    lows = [C(9, 9, lw, 9) for lw in (5, 4, 1, 4, 5)]
    assert confirmed_swing_lows(lows, 3) == [] and confirmed_swing_lows(lows, 4) == [2]


@pytest.mark.rules("TREND-SWING-001")
def test_swing_detection_is_prefix_invariant():
    highs = [5, 6, 9, 6, 5, 7, 12, 8, 6, 9, 11, 7, 6, 4]
    cs = [C(1, h, 0, 1) for h in highs]
    for upto in range(len(cs)):
        full = confirmed_swing_highs(cs, upto)
        assert full == confirmed_swing_highs(cs[: upto + 1], upto)  # the future candles change nothing
        assert all(j <= upto - 2 for j in full)


# ======================================================================= structure trend (TREND-STRUCT-001)
def _structure_prev(highs_lows, last_close, ema):
    """Previous session from explicit (high, low) pairs plus a final candle closing at ``last_close``."""
    cands = [((h + lw) / 2, h, lw, (h + lw) / 2 + (0.1 if i % 2 else -0.1)) for i, (h, lw) in enumerate(highs_lows)]
    cands.append((last_close, last_close + 0.5, last_close - 0.5, last_close))
    return {"cands": cands, "close": last_close, "ema_last": ema}


# swing highs at index 2 (30) and 8 (38): rising. swing lows at index 5 (9) and 10 (11): rising.
HL_UP = [(20, 12), (22, 12), (30, 14), (22, 12), (20, 11), (21, 9), (23, 12), (26, 16), (38, 18), (28, 16), (26, 11), (25, 17), (24, 19)]


def _swings(hl):
    cs = [C(*c) for c in _structure_prev(hl, 30.0, 25.0)["cands"]]
    return confirmed_swing_highs(cs, len(cs) - 1), confirmed_swing_lows(cs, len(cs) - 1), cs


def _long(hl, last_close=30.0, ema=25.0):
    return structure_trend(ctx([(100, 101, 99, 100)], prev=_structure_prev(hl, last_close, ema)), "LONG", ProposalConfig())


@pytest.mark.rules("TREND-STRUCT-001", "TREND-SWING-001")
def test_structure_trend_up_needs_close_above_ema_and_rising_swing_highs_and_lows():
    sh, sl, cs = _swings(HL_UP)
    assert (sh, sl) == ([2, 8], [5, 10]) and cs[8].h > cs[2].h and cs[10].l > cs[5].l  # fixture sanity
    t = _long(HL_UP)
    assert t.ok is True and t.ma_value == 25.0 and "STRUCTURE" in t.reason
    # lower second swing HIGH (29 < 30) -> not an uptrend
    lower_high = [(h if i != 8 else 29, lw) for i, (h, lw) in enumerate(HL_UP)]
    assert _swings(lower_high)[0] == [2, 8] and _long(lower_high).ok is False
    # lower second swing LOW (8 < 9) -> not an uptrend
    lower_low = [(h, lw if i != 10 else 8) for i, (h, lw) in enumerate(HL_UP)]
    assert _swings(lower_low)[1] == [5, 10] and _long(lower_low).ok is False
    # equal second swing high is not "higher"
    equal_high = [(h if i != 8 else 30, lw) for i, (h, lw) in enumerate(HL_UP)]
    assert _long(equal_high).ok is False
    # close exactly on the EMA, or below it, is not "above"
    assert _long(HL_UP, 30.0, 30.0).ok is False and _long(HL_UP, 30.0, 40.0).ok is False


@pytest.mark.rules("TREND-STRUCT-001")
def test_structure_trend_none_and_false_cases_never_become_true():
    assert _long(HL_UP, ema=math.nan).ok is None  # EMA still warming up in the previous session
    assert structure_trend(ctx([(100, 101, 99, 100)]), "LONG", ProposalConfig()).ok is None  # no previous session
    short_prev = _structure_prev(HL_UP[:4], 30.0, 25.0)  # too few candles for two swings of each kind
    t = structure_trend(ctx([(100, 101, 99, 100)], prev=short_prev), "LONG", ProposalConfig())
    assert t.ok is False and "fewer than two" in t.reason


@pytest.mark.rules("TREND-STRUCT-001")
def test_structure_trend_down_is_the_mirror():
    mirror = [(100 - lw, 100 - h) for h, lw in HL_UP]  # reflect prices: rising structure becomes falling structure
    def short(hl, last_close=70.0, ema=75.0):
        return structure_trend(ctx([(100, 101, 99, 100)], prev=_structure_prev(hl, last_close, ema)), "SHORT", ProposalConfig())
    assert short(mirror).ok is True
    assert short(mirror, 70.0, 70.0).ok is False and short(mirror, 70.0, 60.0).ok is False  # on/above the EMA
    assert structure_trend(ctx([(100, 101, 99, 100)], prev=_structure_prev(mirror, 70.0, 75.0)), "LONG", ProposalConfig()).ok is False
    assert structure_trend(ctx([(100, 101, 99, 100)], prev=_structure_prev(HL_UP, 30.0, 25.0)), "SHORT", ProposalConfig()).ok is False


@pytest.mark.rules("TREND-STRUCT-001", "RF-001")
def test_the_opening_gap_cannot_establish_the_trend():
    """Structure uses previous-session information only: wildly different TODAY candles give the identical answer."""
    prev = _structure_prev(HL_UP, last_close=30.0, ema=25.0)
    a = trend_check(ctx([(500, 600, 400, 550)], prev=prev), 0, "LONG", "STRUCTURE_EMA_SWING2", ProposalConfig())
    b = trend_check(ctx([(10, 11, 9, 10)], prev=prev), 0, "LONG", "STRUCTURE_EMA_SWING2", ProposalConfig())
    assert (a.ok, a.reason) == (b.ok, b.reason)


@pytest.mark.rules("TREND-STRUCT-001")
def test_structure_trend_is_selectable_as_a_proposal_and_validated():
    assert ProposalConfig(trend_mode="STRUCTURE_EMA_SWING2").trend_mode == "STRUCTURE_EMA_SWING2"
    with pytest.raises(Exception, match="trend_mode"):
        ProposalConfig(trend_mode="EMA_SLOPE")  # slope is not an approved mandatory condition


# ======================================================================= candle thresholds (CANDLE-DEF-001)
@pytest.mark.rules("CANDLE-DEF-001")
def test_owner_pin_bar_close_must_lie_in_the_favourable_30_percent():
    p = ProposalConfig()
    assert p.pin_bar == "OWNER_2X_CLOSE30"
    assert bullish_pin(C(70, 100, 0, 80), p)         # body 10, lower wick 70, close 20% below the high
    assert bullish_pin(C(70, 100, 0, 70), p)         # close exactly 30% below the high: allowed (boundary)
    assert not bullish_pin(C(70, 100, 0, 69.99), p)  # 30.01% below the high: outside
    assert not bullish_pin(C(70, 100, 50, 50), p) # long wick but the close sits at the low


@pytest.mark.rules("CANDLE-DEF-001")
def test_owner_pin_bar_wick_to_body_boundary():
    p = ProposalConfig()
    assert bullish_pin(C(20, 30, 0, 30), p)           # lower wick 20 == 2 x body 10: qualifies
    assert not bullish_pin(C(19.9, 30, 0, 30), p)     # wick 19.9 < 2 x 10.1: does not
    assert not bullish_pin(C(30, 100, 30, 100), p)    # marubozu: no lower wick


@pytest.mark.rules("CANDLE-DEF-001")
def test_bearish_pin_is_the_mirror_and_needs_an_upper_wick():
    p = ProposalConfig()
    assert bearish_pin(C(30, 100, 0, 20), p)          # upper wick 70 >= 2 x body 10; close 20% above the low
    assert bearish_pin(C(30, 100, 0, 30), p)          # doji, close exactly 30% above the low: boundary
    assert not bearish_pin(C(30, 100, 0, 30.01), p)   # 30.01% above the low
    assert bearish_pin(C(10, 30, 0, 0), p)            # upper wick 20 == 2 x body 10
    assert not bearish_pin(C(10.1, 30, 0, 0), p)      # upper wick 19.9 < 2 x 10.1
    assert not bearish_pin(C(50, 50, 0, 0), p)        # no upper wick
    assert not bearish_pin(C(50, 50, 50, 50), p)      # zero range


@pytest.mark.rules("CANDLE-DEF-001")
def test_owner_thresholds_keep_strong_candle_and_pin_bar_mutually_exclusive():
    p = ProposalConfig()
    import itertools
    pts = [x * 5.0 for x in range(0, 21)]
    for o, c, h, l in itertools.product(pts, pts, pts, pts):  # noqa: E741
        if h < max(o, c) or l > min(o, c) or h <= l:
            continue
        cand = C(o, h, l, c)
        assert not (strong_bearish(cand, p) and bearish_pin(cand, p))
        assert not (strong_bullish(cand, p) and bullish_pin(cand, p))


@pytest.mark.rules("CANDLE-DEF-001")
def test_strong_and_small_candle_thresholds():
    p = ProposalConfig()
    assert strong_bullish(C(20, 100, 0, 80), p)           # body 60%, upper wick 20%: both at the limit
    assert not strong_bullish(C(20, 100, 0, 79.99), p)    # body 59.99%
    assert not strong_bullish(C(0, 100, 0, 79.99), p)     # upper wick 20.01%
    assert strong_bullish(C(0, 100, 0, 80), p)            # body 80%, upper wick exactly 20%
    assert strong_bearish(C(80, 100, 0, 20), p) and not strong_bearish(C(80, 100, 0, 20.01), p)
    assert is_small(C(0, 100, 0, 30), p) and not is_small(C(0, 100, 0, 30.01), p)  # body <= 30% of range
    assert is_small(C(5, 5, 5, 5), p)                     # a zero-range candle is small


# ======================================================================= closing-auction execution eligibility
def T(day, h, m):
    return datetime(day.year, day.month, day.day, h, m, tzinfo=IST)


@pytest.mark.rules("EXE-AUCTION-001")
def test_bar_eligibility_on_a_closing_auction_day_and_a_pre_regime_day():
    cas, pre = date(2026, 8, 4), date(2026, 7, 31)
    assert classify_bar(T(cas, 15, 14)) is BarEligibility.CONTINUOUS
    assert classify_bar(T(cas, 15, 15)) is BarEligibility.CLOSING_AUCTION_REFERENCE
    assert classify_bar(T(cas, 15, 28)) is BarEligibility.CLOSING_AUCTION_REFERENCE
    assert classify_bar(T(cas, 15, 29)) is BarEligibility.CLOSING_AUCTION_REFERENCE
    assert classify_bar(T(cas, 15, 30)) is BarEligibility.POST_CLOSE
    assert classify_bar(T(cas, 9, 14)) is BarEligibility.NON_TRADING and classify_bar(T(cas, 9, 15)) is BarEligibility.CONTINUOUS
    # before the regime date 15:15-15:29 is ordinary continuous trading
    assert classify_bar(T(pre, 15, 15)) is BarEligibility.CONTINUOUS and classify_bar(T(pre, 15, 29)) is BarEligibility.CONTINUOUS
    assert classify_bar(T(pre, 15, 30)) is BarEligibility.POST_CLOSE


@pytest.mark.rules("EXE-AUCTION-001")
def test_regime_boundary_date_and_non_trading_days():
    assert classify_bar(T(date(2026, 8, 3), 15, 15)) is BarEligibility.CLOSING_AUCTION_REFERENCE  # first regime day
    assert classify_bar(T(date(2026, 7, 31), 15, 20)) is BarEligibility.CONTINUOUS  # last day before
    assert classify_bar(T(date(2026, 1, 15), 10, 0)) is BarEligibility.NON_TRADING  # confirmed holiday
    assert classify_bar(T(date(2026, 1, 17), 10, 0)) is BarEligibility.NON_TRADING  # ordinary Saturday
    assert classify_bar(T(date(2025, 10, 21), 14, 0)) is BarEligibility.SPECIAL_SESSION_NONSTANDARD  # Muhurat
    assert classify_bar(T(date(2026, 2, 1), 10, 0)) is BarEligibility.CONTINUOUS  # Budget Sunday, normal hours


@pytest.mark.rules("EXE-AUCTION-001")
def test_an_entry_whose_next_bar_is_a_reference_bar_is_blocked():
    cas = date(2026, 8, 4)
    assert entry_executable(T(cas, 15, 14))      # next bar starts 15:14: fillable
    assert not entry_executable(T(cas, 15, 15))  # a candle closing at 15:15: next bar is a reference bar
    assert entry_executable(T(date(2026, 7, 31), 15, 15))  # same clock time before the regime: ordinary
    assert is_executable(T(cas, 12, 0)) and not is_executable(T(cas, 15, 40))


@pytest.mark.rules("EXE-AUCTION-001", "EXE-FILL-001")
def test_signal_in_the_auction_window_is_flagged_entry_blocked():
    cas = date(2026, 8, 4)
    eng = IRFStrategy()
    assert eng._execution_status(T(cas, 15, 10)) == "RESEARCH_ONLY"
    assert eng._execution_status(T(cas, 15, 15)) == "ENTRY_BLOCKED_CLOSING_AUCTION_REFERENCE"
    assert eng._execution_status(None) == "NOT_EVALUATED"


# ======================================================================= exit model never fills in non-executable bars
def _cas_bars(*specs):
    return [Bar(f"m{i}", *s) for i, s in enumerate(specs)]


@pytest.mark.rules("EXE-AUCTION-001", "EXE-MISSING-001")
def test_stop_touched_in_a_reference_bar_is_not_filled_and_the_position_is_flagged_unresolved():
    pol = policy_for("IRF")  # 35 / 60
    bars = [B(0, E, E + 5, E - 5, E), B(1, E, E + 10, E - 10, E), B(2, E + 200, E + 201, E + 199, E + 200, executable=False)]  # catch-up jump
    r = evaluate_exit("SHORT", E, bars, pol)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.leg2_exit is None and r.pnl_rupees == 0
    assert r.unresolved_at_closing_auction and r.non_executable_bars_skipped == 1
    assert any("UNRESOLVED_AT_CLOSING_AUCTION" in u for u in r.unresolved)
    assert any("NON-EXECUTABLE" in a and "stop" in a for a in r.ambiguities)  # the touch is recorded but never filled


@pytest.mark.rules("EXE-AUCTION-001")
def test_target_touched_in_a_reference_bar_is_not_filled_either():
    pol = policy_for("IRF")
    bars = [B(0, E, E + 5, E - 5, E), B(1, E - 80, E - 79, E - 81, E - 80, executable=False)]
    r = evaluate_exit("SHORT", E, bars, pol)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.pnl_rupees == 0 and r.unresolved_at_closing_auction


@pytest.mark.rules("EXE-AUCTION-001")
def test_a_normal_exit_before_the_auction_is_unaffected():
    pol = policy_for("IRF")
    bars = [B(0, E, E - 1, E - 90, E - 80), B(1, E - 80, E - 79, E - 81, E - 80, executable=False)]
    r = evaluate_exit("SHORT", E, bars, pol)
    assert r.outcome is TradeOutcome.TARGET and not r.unresolved_at_closing_auction and r.non_executable_bars_skipped == 0


@pytest.mark.rules("EXE-AUCTION-001")
def test_research_eod_flatten_uses_the_last_executable_bar_not_the_auction_catch_up():
    cfg = ExitPolicyConfig(t2_points=60, stop_points=35, eod_policy=EodPolicy.EXIT_AT_LAST_CLOSE)
    bars = [B(0, E, E + 5, E - 5, E - 3), B(1, E + 300, E + 301, E + 299, E + 300, executable=False)]
    r = evaluate_exit("SHORT", E, bars, cfg)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.leg1_exit == E - 3  # never the +300 reference value
    assert not r.unresolved_at_closing_auction


@pytest.mark.rules("EXE-AUCTION-001")
def test_t1_booked_before_the_auction_keeps_leg_two_open_and_unresolved():
    pol = policy_for("IRF")
    bars = [B(0, E, E - 1, E - 30, E - 28), B(1, E - 28, E - 20, E - 40, E - 30), B(2, E + 50, E + 51, E + 49, E + 50, executable=False)]
    r = evaluate_exit("SHORT", E, bars, pol)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.leg1_exit == E - 27 and r.leg2_exit is None
    assert r.unresolved_at_closing_auction and r.pnl_rupees == 27 * 195  # only the booked Leg 1 counts


# ======================================================================= selection policies (EXE-SEL-001)
def _rec(engine, ts_hm, day=date(2026, 1, 12), status="CONFIRMED", blocked=False, direction=Direction.SHORT):
    from nifty_trading.strategies.base import SignalRecord
    ts = T(day, *ts_hm)
    return SignalRecord(
        strategy=engine, method="M", direction=direction.value, signal_date=day, signal_timestamp=ts, signal_candle_start=ts - timedelta(minutes=5),
        signal_candle_open=E, signal_candle_high=E, signal_candle_low=E, signal_candle_close=E, reference_levels={}, rule_ids_satisfied=[],
        rule_ids_failed=[], signal_status=status, invalidation_reason=None, verification_status="PROPOSAL_DEPENDENT",
        execution_config={"execution_status": "ENTRY_BLOCKED_CLOSING_AUCTION_REFERENCE" if blocked else "RESEARCH_ONLY"})


@pytest.mark.rules("EXE-SEL-001")
def test_all_valid_signals_keeps_every_confirmed_executable_event_and_logs_the_rest():
    recs = [_rec("IRF", (10, 0)), _rec("IRF", (10, 30)), _rec("IRF", (11, 0), status="INVALIDATED"), _rec("IRF", (15, 15), blocked=True)]
    s = apply_policy(recs, SelectionPolicy.ALL_VALID_SIGNALS)
    assert len(s.accepted) == 2 and len(s.skipped) == 2
    assert {why.split("(")[0] for _, why in s.skipped} == {"NOT_CONFIRMED", "ENTRY_BLOCKED_CLOSING_AUCTION_REFERENCE"}
    assert s.status == "RESEARCH_POLICY_NOT_APPROVED"


@pytest.mark.rules("EXE-SEL-001")
def test_first_valid_signal_per_day_is_per_day_and_per_strategy():
    d1, d2 = date(2026, 1, 12), date(2026, 1, 13)
    recs = [_rec("IRF", (11, 0), d1), _rec("IRF", (10, 0), d1), _rec("IRF", (12, 0), d2), _rec("ORB", (9, 20), d1)]
    s = apply_policy(recs, "FIRST_VALID_SIGNAL_PER_DAY")
    got = sorted((r.strategy, r.signal_date, r.signal_timestamp.hour) for r in s.accepted)
    assert got == [("IRF", d1, 10), ("IRF", d2, 12), ("ORB", d1, 9)]
    assert [why for _, why in s.skipped] == ["LATER_SIGNAL_SAME_DAY"]


@pytest.mark.rules("EXE-SEL-001")
def test_one_active_position_skips_signals_while_a_position_is_open():
    r1, r2, r3 = _rec("IRF", (10, 0)), _rec("IRF", (10, 30)), _rec("IRF", (11, 30))
    ends = {id(r1): T(date(2026, 1, 12), 11, 0), id(r2): T(date(2026, 1, 12), 11, 45), id(r3): T(date(2026, 1, 12), 12, 0)}
    s = apply_policy([r1, r2, r3], SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME, lambda r: ends[id(r)])
    assert s.accepted == [r1, r3]  # r2 arrives at 10:30 while r1 is open until 11:00; r3 at 11:30 is after it
    assert s.skipped[0][0] is r2 and "POSITION_STILL_OPEN_UNTIL_11:00" in s.skipped[0][1]
    # a signal exactly when the previous position ends may be taken
    s2 = apply_policy([r1, _rec("IRF", (11, 0))], "ONE_ACTIVE_POSITION_AT_A_TIME", lambda r: ends.get(id(r), T(date(2026, 1, 12), 12, 0)))
    assert len(s2.accepted) == 2


@pytest.mark.rules("EXE-SEL-001")
def test_a_position_that_never_closes_blocks_the_rest_of_that_session_visibly():
    r1, r2 = _rec("IRF", (10, 0)), _rec("IRF", (13, 0))
    s = apply_policy([r1, r2], SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME, lambda r: None)
    assert s.accepted == [r1] and "NEVER_CLOSED" in s.skipped[0][1]
    # ...but not the next day
    r3 = _rec("IRF", (10, 0), date(2026, 1, 13))
    assert len(apply_policy([r1, r3], SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME, lambda r: None).accepted) == 2


@pytest.mark.rules("EXE-SEL-001")
def test_one_active_requires_an_end_function_and_unknown_policy_is_rejected():
    with pytest.raises(ValueError):
        apply_policy([_rec("IRF", (10, 0))], SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME)
    with pytest.raises(ValueError):
        apply_policy([], "BEST_SIGNAL")


@pytest.mark.rules("EXE-SEL-001", "EXE-FILL-001")
def test_causal_fill_is_the_next_bar_open_and_exit_end_follows_the_final_bar():
    day = date(2026, 1, 12)
    bars = [Bar(T(day, 9, 20) + timedelta(minutes=k), E + k, E + k + 1, E + k - 1, E + k) for k in range(6)]
    sig = _rec("IRF", (9, 20), day)  # candle ends 09:20 -> acted on from the 09:20 bar, filled at its OPEN
    entry, rest = fill_from_next_bar(bars, sig.signal_timestamp)
    assert entry == E and rest[0].ts == T(day, 9, 20)
    assert fill_from_next_bar(bars, T(day, 9, 26)) is None  # no such bar
    bad = bars[:2] + [Bar(T(day, 9, 22), E, E, E, E, executable=False)]
    assert fill_from_next_bar(bad, T(day, 9, 22)) is None  # next bar not fillable: entry blocked
    res = simulate_exit(_rec("IRF", (9, 20), day), [Bar(T(day, 9, 20), E, E - 1, E - 90, E - 80)])
    assert res.outcome is TradeOutcome.TARGET and position_end_from_result(res) == T(day, 9, 21)
    assert position_end_from_result(None) is NO_POSITION  # no fill = no position, never 'open forever'


# ======================================================================= no-look-ahead for the new trend mode
@pytest.mark.rules("TREND-STRUCT-001", "DATA-TIME-001")
def test_orb_and_rf_with_structure_trend_never_use_candles_beyond_the_prefix():
    prev = {**_structure_prev(HL_UP, last_close=30.0, ema=25.0), "close": 30.0}
    full = ctx([(31, 40, 30, 38), (38, 39, 20, 25), (25, 33, 24, 32)] + [(32, 33, 31, 32)] * 10, prev=prev, ema=20.0)
    p = ProposalConfig(trend_mode="STRUCTURE_EMA_SWING2")
    for eng in (RFStrategy(proposals=p), ORBStrategy(proposals=p)):
        whole = [(r.method, r.signal_status, r.signal_timestamp) for r in eng.evaluate_session(full)]
        for n in range(1, len(full.candles) + 1):
            pre = [(r.method, r.signal_status, r.signal_timestamp) for r in eng.evaluate_session(full.prefix(n))
                   if r.signal_timestamp is not None and r.signal_timestamp <= full.candles["bar_end"].iloc[n - 1]]
            assert all(x in whole for x in pre if x[1] == SignalStatus.CONFIRMED.value)


def test_helper_frame_is_importable():  # keeps the shared helpers exercised so a refactor cannot silently break them
    assert len(frame([(1, 2, 0, 1)])) == 1 and PREV_DAY.year == 2026


# ======================================================================= zone selection candidates (PDR-ZONE-002 / PDS-ZONE-002)
from nifty_trading.strategies.definitions import pdr_zone, pds_zone  # noqa: E402


def _prev_from_highs(highs, red_idx=()):
    cands = []
    for i, h in enumerate(highs):
        if i in red_idx:
            cands.append((h - 3, h, h - 10, h - 8))   # red: close < open
        else:
            cands.append((h - 8, h, h - 10, h - 3))   # green
    return {"cands": cands, "close": cands[-1][3]}


H = [100, 104, 130, 104, 100, 110, 118, 111, 105, 118.5, 108, 104, 100, 98, 97]
RED = {11, 12, 13}


def _zone(method, highs=H, red=RED, **kw):
    c = ctx([(100, 101, 99, 100)], prev=_prev_from_highs(highs, red))
    return pdr_zone(c.previous, ProposalConfig(pdr_zone_method=method, **kw))


@pytest.mark.rules("PDR-ZONE-002", "PDR-002", "PDR-003")
def test_pdr_zone_method_a_is_the_absolute_highest_high_candle():
    z = _zone("A_HIGHEST_HIGH")
    assert (z.candle_index, z.high, z.method, z.diagnostic_only) == (2, 130, "A_HIGHEST_HIGH", True)  # a DIAGNOSTIC reference
    assert z.low == 130 - 3  # Phase 2.2 default ZONE_WICK: body TOP (max(open, close)) to the wick tip
    assert _zone("A_HIGHEST_HIGH", zone_lower_boundary="ZONE_FULL").low == 130 - 8  # candidate: body BOTTOM to the wick tip


@pytest.mark.rules("PDR-ZONE-002")
def test_pdr_zone_method_b_is_the_latest_confirmed_swing_high_with_a_bearish_reversal_candle():
    z = _zone("B_SWING_HIGH_REVERSAL")
    assert (z.candle_index, z.high, z.method, z.members) == (9, 118.5, "B_SWING_HIGH_REVERSAL", (9,))
    # no red candle at/after the latest swing high -> the next older swing high with one is used (idx 6: red inside 6..8 needed)
    no_red = _zone("B_SWING_HIGH_REVERSAL", red={7})
    assert no_red.candle_index == 6
    # no red candle anywhere near any swing high -> falls back to method A and says so
    assert _zone("B_SWING_HIGH_REVERSAL", red=set()) is None  # Phase 2.3: no candidate = NO zone, never a silent fall back to the highest high


@pytest.mark.rules("PDR-ZONE-002")
def test_pdr_zone_method_c_is_the_highest_cluster_of_repeated_swing_highs():
    z = _zone("C_REPEATED_TOUCHES")
    assert z.members == (6, 9) and z.high == 118.5 and not z.diagnostic_only
    assert z.low == min(118 - 3, 118.5 - 3)  # spans the cluster (default ZONE_WICK: lowest body top)
    assert _zone("C_REPEATED_TOUCHES", zone_lower_boundary="ZONE_FULL").low == min(118 - 8, 118.5 - 8)
    assert _zone("C_REPEATED_TOUCHES", zone_cluster_tolerance_points=0.1) is None  # 118 and 118.5 no longer cluster -> no zone
    wide = _zone("C_REPEATED_TOUCHES", zone_cluster_tolerance_points=15)  # now the spike clusters with the shelf: highest cluster wins
    assert 2 in wide.members and wide.high == 130


@pytest.mark.rules("PDR-ZONE-002")
def test_zone_method_uses_only_previous_session_candles_and_swing_confirmation():
    """A swing high in the LAST two candles of the previous session is unconfirmed and can never be picked by B/C."""
    highs = [100, 104, 110, 104, 100, 102, 99, 98, 140, 130]  # the 140 peak is candle 8 of 10: only one candle follows it
    z = _zone("B_SWING_HIGH_REVERSAL", highs=highs, red={9, 4, 3})
    assert z.candle_index != 8
    assert _zone("C_REPEATED_TOUCHES", highs=highs, red={9}) is None  # no cluster -> no zone (the 140 peak is only the diagnostic highest high)
    assert _zone("A_HIGHEST_HIGH", highs=highs, red={9}).high == 140


@pytest.mark.rules("PDS-ZONE-002", "PDS-002")
def test_pds_zone_methods_mirror_with_lows_and_do_not_assume_an_exact_mirror_of_pdr():
    lows = [200 - h for h in H]
    cands = []
    for i, lw in enumerate(lows):
        cands.append((lw + 3, lw + 10, lw, lw + 8) if i in {11, 12, 13} else (lw + 8, lw + 10, lw, lw + 3))  # green after the trough / red before
    c = ctx([(100, 101, 99, 100)], prev={"cands": cands, "close": cands[-1][3]})
    a = pds_zone(c.previous, ProposalConfig(pds_zone_method="A_LOWEST_LOW"))
    assert (a.candle_index, a.low) == (2, 70) and a.high == 70 + 8  # ZONE_FULL: wick tip to body TOP
    b = pds_zone(c.previous, ProposalConfig(pds_zone_method="B_SWING_LOW_REVERSAL"))
    assert (b.candle_index, b.low) == (9, 81.5)
    cc = pds_zone(c.previous, ProposalConfig(pds_zone_method="C_REPEATED_TOUCHES"))
    assert cc.members == (6, 9) and cc.low == 81.5
    wick = pds_zone(c.previous, ProposalConfig(pds_zone_method="A_LOWEST_LOW", pds_zone_upper_boundary="ZONE_WICK"))
    assert wick.high == 70 + 3  # ZONE_WICK: wick tip to body BOTTOM


@pytest.mark.rules("PDR-ZONE-002")
def test_zone_config_is_validated():
    for bad in ({"pdr_zone_method": "HIGHEST_PROFIT"}, {"pds_zone_method": "X"}, {"zone_cluster_min_touches": 1}, {"zone_proximity_points": -1}):
        with pytest.raises(Exception):  # noqa: B017
            ProposalConfig(**bad)


# ======================================================================= strict zone intersection is the default (PDR-006)
PDR_PREV = {"cands": [(23960, 23970, 23950, 23965), (23980, 24000, 23970, 23975), (23975, 23985, 23960, 23962)], "close": 23950.0}
# zone (ZONE_FULL) = [23975, 24000]


def _pdr(cands, **p):
    p.setdefault("pdr_zone_method", "A_HIGHEST_HIGH")  # these synthetic sessions have no swing structure: the highest-high candle marks the zone (DIAGNOSTIC)
    return PDRStrategy(proposals=ProposalConfig(**p)).evaluate_session(ctx(cands, prev=PDR_PREV))


def _confirmed(recs):
    return [r for r in recs if r.signal_status == "CONFIRMED"]


@pytest.mark.rules("PDR-006")
def test_default_proximity_is_zero_so_a_near_miss_is_not_a_zone_test():
    assert ProposalConfig().zone_proximity_points == 0.0
    green = (24003, 24030, 24002, 24025)
    touch = [(24050, 24060, 24040, 24055), (24055, 24058, 24000.0, 24003), green]
    near = [(24050, 24060, 24040, 24055), (24055, 24058, 24004.9, 24006), (24006, 24030, 24005, 24025)]
    assert _confirmed(_pdr(touch)) and not _confirmed(_pdr(near))
    assert _confirmed(_pdr(near, zone_proximity_points=5.0))  # the labelled near-touch variant


@pytest.mark.rules("PDR-006")
def test_a_candle_entirely_below_the_zone_is_not_an_intersection_even_with_zero_proximity():
    below = [(24050, 24060, 24040, 24055), (23955, 23969, 23950, 23965), (23965, 23966, 23960, 23964)]
    assert not _confirmed(_pdr(below))
    assert not _confirmed(_pdr(below, zone_proximity_points=5.0))  # 23969 + 5 < ... zone bottom 23975 is 6 points above the high


PDS_PREV = {"cands": [(24040, 24050, 24030, 24045), (24020, 24030, 24000, 24025), (24025, 24040, 24020, 24035)], "close": 24050.0}


@pytest.mark.rules("PDS-005")
def test_pds_default_requires_the_candle_to_intersect_the_zone():
    c = ctx([(23950, 23960, 23940, 23945), (23945, 23996, 23950, 23952), (23960, 23999.95, 23950, 23951)], prev=PDS_PREV)
    z = pds_zone(c.previous, ProposalConfig())
    assert (z.low, z.high) == (24000, 24025)
    assert not _confirmed(PDSStrategy().evaluate_session(c))  # highs 23996 / 23999.95 stay below the zone: strict default sees no test
    c2 = ctx([(23950, 23960, 23940, 23945), (23960, 24005, 23950, 23952)], prev=PDS_PREV)
    assert PDSStrategy().evaluate_session(c2)[0].reference_levels["zone_method"] == "A_LOWEST_LOW"


# ======================================================================= documented Phase 2.2 defaults
@pytest.mark.rules("EXE-STOP-001", "CANDLE-DEF-001", "TREND-STRUCT-001", "PDR-006", "PDR-ZONE-002")
def test_the_documented_phase22_defaults():
    p = ProposalConfig()
    assert (p.trend_mode, p.swing_k) == ("STRUCTURE_EMA_SWING2", 2)
    assert (p.strong_candle, p.pin_bar) == ("MODERATE", "OWNER_2X_CLOSE30")
    assert p.small_candle_body_ratio_max == 0.30
    assert (p.zone_proximity_points, p.zone_lower_boundary) == (0.0, "ZONE_WICK")
    assert (p.pdr_zone_method, p.pds_zone_method, p.pds_zone_upper_boundary) == ("B_SWING_HIGH_REVERSAL", "A_LOWEST_LOW", "ZONE_FULL")
    assert p.m3_compression_def == "C1"  # 'small candle <= 30% of range' (C3) is NOT supported by IRF Fig 5, so it is only a variant
    assert (p.irf_support_def, p.max_signals_per_session) == ("SWING_K1", 1)  # IRF's own worked examples (p6/p10) reproduce with the 3-candle swing
    assert DEFAULT_TRADE.stop_variant == "BASELINE" and DEFAULT_TRADE.t1_points == 27.0


# ======================================================================= source-example geometry (no profit figures used)
from pathlib import Path  # noqa: E402

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)

_HAVE_DATA = (Path(__file__).resolve().parents[1] / "data" / "processed" / "nifty50_daily").exists()
needs_data = pytest.mark.skipif(not _HAVE_DATA, reason="processed NIFTY data not available")


@pytest.fixture(scope="module")
def real():
    ctxs, infos = build_session_contexts(load_one_minute(), daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    return ctxs


@needs_data
@pytest.mark.rules("PDR-002", "PDR-003", "PDR-006", "PDR-007")
@pytest.mark.parametrize("day,entry_start,drawn", [
    (date(2025, 9, 2), "09:25", (24632.0, 24640.0)),      # PDR p.3 chart 1 (journal PDR 09:25)
    (date(2025, 10, 6), "09:30", (24901.9, 24905.6)),     # PDR p.3 chart 2 (journal PDR 09:30)
    (date(2025, 11, 20), "09:45", (26061.8, 26074.2)),    # PDR p.4 chart 4 (journal PDR 09:45)
])
def test_pdr_dated_charts_reproduce_with_the_strict_wick_zone_default(real, day, entry_start, drawn):
    """Candle geometry only: the engine's zone sits on the candle that carries the previous session's high, its bottom is the body TOP
    (matching the drawn zones within chart-reading error) and the signal is the green candle the chart marks. Profit figures are not used."""
    c = real[day]
    [r] = [x for x in PDRStrategy().evaluate_session(c) if x.signal_status == "CONFIRMED"]
    assert r.signal_candle_start.strftime("%H:%M") == entry_start
    lv = r.reference_levels
    assert abs(lv["zone_high"] - drawn[1]) <= 5.5 and abs(lv["zone_low"] - drawn[0]) <= 2.5  # chart 1 overshoots its wick tip by ~5 points
    assert lv["zone_method"] == "B_SWING_HIGH_REVERSAL" and lv["zone_status"] == "OWNER_APPROVED_RESEARCH_CANDIDATE"
    assert lv["diagnostic_highest_high_zone"] == [lv["zone_low"], lv["zone_high"]]  # on these three charts the diagnostic highest high coincides
    assert r.execution_config["stop_distance"] == 35.0 and r.execution_config["target_2"] == 70.0


@needs_data
@pytest.mark.rules("PDR-ZONE-002")
def test_no_zone_method_reproduces_chart_3_so_the_candle_choice_stays_open(real):
    """PDR p.4 chart 3 (2025-10-07) draws a shelf of equal highs, [25,080.8, 25,084.4]; no mechanical method here reproduces it (PDR-D09)."""
    prev = real[date(2025, 10, 7)].previous
    for m in ("A_HIGHEST_HIGH", "B_SWING_HIGH_REVERSAL", "C_REPEATED_TOUCHES"):
        z = pdr_zone(prev, ProposalConfig(pdr_zone_method=m))
        assert not (abs(z.low - 25080.8) <= 2.5 and abs(z.high - 25084.4) <= 2.5), m


@needs_data
@pytest.mark.rules("DATA-CAS-001", "EXE-AUCTION-001")
def test_every_closing_auction_session_has_its_reference_bars_marked_non_executable(real):
    from nifty_trading.core.execution_eligibility import classify_bar
    n = 0
    for d, c in real.items():
        if c.info.cas_regime:
            n += 1
            assert classify_bar(datetime(d.year, d.month, d.day, 15, 14, tzinfo=IST)) is BarEligibility.CONTINUOUS
            assert classify_bar(datetime(d.year, d.month, d.day, 15, 15, tzinfo=IST)) is BarEligibility.CLOSING_AUCTION_REFERENCE
    assert n == 21


# ======================================================================= fixes from the independent Phase 2.2 review
@pytest.mark.rules("EXE-FILL-001", "POST-T1-STOP-006")
def test_entry_bar_that_reaches_target_1_is_not_stopped_merely_because_it_opened_at_the_entry():
    """F1 (Phase 2.2) re-expressed under the Phase 2.3 rule: the post-T1 stop is 6 points away, so the entry bar's open can never touch it."""
    pol = policy_for("IRF")
    r = evaluate_exit("LONG", E, [B(0, E, E + 30, E, E + 29)], policy_for("ORB"), entry_at_first_bar_open=True)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.leg1_exit == E + 27 and not r.ambiguities  # T1 booked, Leg 2 still open
    t = evaluate_exit("LONG", E, [B(0, E, E + 61, E, E + 60)], policy_for("ORB"), entry_at_first_bar_open=True)
    assert t.outcome is TradeOutcome.TARGET
    s = evaluate_exit("SHORT", E, [B(0, E, E, E - 90, E - 80)], pol, entry_at_first_bar_open=True)
    assert s.outcome is TradeOutcome.TARGET and not s.ambiguities
    # reaching the post-T1 stop (entry - 6) in the same bar is the adverse ambiguity
    amb = evaluate_exit("LONG", E, [B(0, E, E + 30, E - 6, E + 29)], policy_for("ORB"), entry_at_first_bar_open=True)
    assert amb.outcome is TradeOutcome.T1_THEN_BUFFER_STOP and amb.ambiguities
    # the SUPERSEDED exact-entry mode keeps the Phase 2.2 behaviour: strictly beyond the entry is required in the entry bar
    legacy = ExitPolicyConfig(t2_points=60, stop_points=30, post_t1_stop_mode="ENTRY_BREAKEVEN")
    assert evaluate_exit("LONG", E, [B(0, E, E + 30, E, E + 29)], legacy, entry_at_first_bar_open=True).outcome is TradeOutcome.INCOMPLETE_EOD
    assert evaluate_exit("LONG", E, [B(0, E, E + 30, E - 0.05, E + 29)], legacy, entry_at_first_bar_open=True).outcome is TradeOutcome.BREAKEVEN
    assert evaluate_exit("LONG", E, [B(0, E, E + 30, E, E + 29)], legacy).outcome is TradeOutcome.BREAKEVEN
    # a later bar's stop test is unchanged
    later = evaluate_exit("LONG", E, [B(0, E, E + 30, E + 1, E + 29), B(1, E + 29, E + 30, E - 6, E + 5)], policy_for("ORB"), entry_at_first_bar_open=True)
    assert later.outcome is TradeOutcome.T1_THEN_BUFFER_STOP


@pytest.mark.rules("EXE-AUCTION-001", "EXE-FILL-001")
def test_simulate_exit_uses_the_causal_fill_and_does_not_force_breakeven_on_the_entry_bar():
    day = date(2026, 1, 12)
    bars = [Bar(T(day, 9, 20), E, E, E - 90, E - 80)]  # SHORT: opens at the entry, falls 90 without trading above it
    res = simulate_exit(_rec("IRF", (9, 20), day), bars)
    assert res.outcome is TradeOutcome.TARGET


@pytest.mark.rules("EXE-AUCTION-001")
def test_post_close_bars_are_not_reported_as_a_closing_auction_problem():
    """F2: an ordinary pre-regime day with a 15:30 stub row must not carry UNRESOLVED_AT_CLOSING_AUCTION."""
    pol = policy_for("IRF")
    post = Bar("m1", E - 5, E - 4, E - 6, E - 5, executable=False, ineligible="POST_CLOSE")
    r = evaluate_exit("SHORT", E, [B(0, E, E - 1, E - 5, E - 3), post], pol)
    assert r.outcome is TradeOutcome.INCOMPLETE_EOD and r.non_executable_bars_skipped == 1
    assert not r.unresolved_at_closing_auction and not r.closing_auction_truncated
    assert not any("CLOSING_AUCTION" in u for u in r.unresolved)
    auction = Bar("m1", E - 5, E - 4, E - 6, E - 5, executable=False, ineligible="CLOSING_AUCTION_REFERENCE")
    r2 = evaluate_exit("SHORT", E, [B(0, E, E - 1, E - 5, E - 3), auction], pol)
    assert r2.unresolved_at_closing_auction and r2.closing_auction_truncated


@pytest.mark.rules("EXE-AUCTION-001")
def test_research_flatten_still_reports_that_the_auction_truncated_the_day():
    """F10: the EXIT_AT_LAST_CLOSE option must not look like an ordinary end-of-day exit on an auction day."""
    cfg = ExitPolicyConfig(t2_points=60, stop_points=35, eod_policy=EodPolicy.EXIT_AT_LAST_CLOSE)
    r = evaluate_exit("SHORT", E, [B(0, E, E - 1, E - 5, E - 3), Bar("m1", E, E, E, E, executable=False)], cfg)
    assert r.closing_auction_truncated and not r.unresolved_at_closing_auction


@pytest.mark.rules("EXE-AUCTION-001")
def test_bars_from_frame_marks_real_auction_and_post_close_rows():
    import pandas as pd

    from nifty_trading.core.execution_eligibility import bars_from_frame
    rows = [{"timestamp": pd.Timestamp(datetime(2026, 8, 4, h, m, tzinfo=IST)), "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5}
            for h, m in ((15, 14), (15, 15), (15, 29), (15, 30))]
    bars = bars_from_frame(pd.DataFrame(rows))
    assert [(b.executable, b.ineligible) for b in bars] == [(True, "CONTINUOUS"), (False, "CLOSING_AUCTION_REFERENCE"),
                                                            (False, "CLOSING_AUCTION_REFERENCE"), (False, "POST_CLOSE")]


@pytest.mark.rules("EXE-AUCTION-001")
def test_eligibility_uses_exchange_time_and_refuses_to_run_without_the_auction_calendar():
    """F9: a UTC-aware timestamp is converted to IST; a calendar lacking the regime must not silently make auction bars fillable."""
    from zoneinfo import ZoneInfo

    from nifty_trading.data.market_calendar import MarketCalendar
    utc = ZoneInfo("UTC")
    assert classify_bar(datetime(2026, 8, 4, 9, 50, tzinfo=utc)) is BarEligibility.CLOSING_AUCTION_REFERENCE  # 15:20 IST
    assert classify_bar(datetime(2026, 8, 4, 10, 0, tzinfo=utc)) is BarEligibility.POST_CLOSE                  # 15:30 IST
    empty = MarketCalendar(source="MISSING_FILE")
    with pytest.raises(RuntimeError, match="closing-auction calendar missing"):
        classify_bar(T(date(2026, 8, 4), 15, 20), empty)
    assert classify_bar(T(date(2026, 7, 31), 15, 20), empty) is BarEligibility.CONTINUOUS  # before the regime the empty calendar is fine


@pytest.mark.rules("EXE-STOP-001", "EXE-FILL-001")
def test_the_source_distance_stop_variant_works_through_simulate_exit():
    """F11: simulate_exit now passes the recent green candle reference, so SOURCE_35_40_BY_DISTANCE is usable."""
    day = date(2026, 1, 12)
    rec = _rec("IRF", (9, 20), day)
    rec.reference_levels["recent_green_high"] = E + 38  # 38 > 35 -> the 40-point stop
    bars = [Bar(T(day, 9, 20), E, E + 39, E - 1, E + 5), Bar(T(day, 9, 21), E + 5, E + 41, E, E + 40)]
    research = TradeConfig(stop_variant="SOURCE_35_40_BY_DISTANCE")
    r = simulate_exit(rec, bars, research)
    assert r.outcome is TradeOutcome.STOP_LOSS and r.stop_level == E + 40
    assert simulate_exit(rec, bars).outcome is TradeOutcome.STOP_LOSS  # baseline 35: stopped in the first bar already


@pytest.mark.rules("EXE-SEL-001")
def test_no_fill_is_not_a_position_and_blocks_nothing():
    """F12: an unfillable signal is skipped with a reason; it does not block later signals of the day."""
    r1, r2 = _rec("IRF", (10, 0)), _rec("IRF", (10, 30))
    ends = {id(r1): NO_POSITION, id(r2): T(date(2026, 1, 12), 11, 0)}
    s = apply_policy([r1, r2], SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME, lambda r: ends[id(r)])
    assert s.accepted == [r2] and "ENTRY_NOT_FILLABLE" in s.skipped[0][1]
    # a stale fill is refused: if the exact next bar is missing, a later bar is never used
    day = date(2026, 1, 12)
    bars = [Bar(T(day, 9, 22), E, E, E, E)]
    assert fill_from_next_bar(bars, T(day, 9, 20)) is None
    assert position_end_from_result(simulate_exit(_rec("IRF", (9, 20), day), bars)) is NO_POSITION


@pytest.mark.rules("EXE-STOP-001", "PDR-008")
def test_signals_carry_the_complete_rule_configuration_and_the_target_conflict():
    """F3/F4/F5: PDR/PDS signals expose the guide-vs-report conflict; every record lists all proposals and the trade config;
    non-signal records never claim an entry-rule status."""
    prev = {"cands": [(23960, 23970, 23950, 23965), (23980, 24000, 23970, 23975), (23975, 23985, 23960, 23962)], "close": 23950.0}
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24000, 24003), (24003, 24030, 24002, 24025)]
    diag = ProposalConfig(pdr_zone_method="A_HIGHEST_HIGH")
    [s] = _confirmed(PDRStrategy(proposals=diag).evaluate_session(ctx(cands, prev=prev)))
    ec = s.execution_config
    assert ec["execution_status"] == "DIAGNOSTIC_ONLY_NOT_TRADABLE"  # the highest-high zone never yields a tradable signal
    assert ec["target_2"] == 70.0 and ec["target_2_status"] == "CONFLICTING" and "1 of its 6" in ec["target_2_conflict"]
    assert ec["proposal_config"] == diag.to_dict() and ec["trade_config"]["stop_variant"] == "BASELINE"
    assert ec["proposal_config"]["swing_k"] == 2 and ec["proposal_config"]["small_candle_body_ratio_max"] == 0.30
    assert "UNRESOLVED(PDR-009)" not in str(s.reference_levels.values())
    alt = PDRStrategy(proposals=ProposalConfig(swing_k=1, pdr_zone_method="A_HIGHEST_HIGH"), trade=TradeConfig(stop_variant="ALTERNATE_40")).evaluate_session(ctx(cands, prev=prev))
    assert _confirmed(alt)[0].execution_config != ec  # different settings are distinguishable
    inv = PDRStrategy(proposals=diag).evaluate_session(ctx([(23990, 24010, 23985, 24005), (24005, 24020, 24000, 24015)], prev=prev))[0]
    assert inv.signal_status == "INVALIDATED" and inv.execution_config["entry_rule_status"] == "NOT_A_CONFIRMED_SIGNAL"
    assert IRFStrategy().exec_config("Method 1", "X", "RESEARCH_ONLY")["target_2_conflict"] is None


@pytest.mark.rules("EXE-STOP-001")
def test_entry_rule_status_maps_a_verified_record_and_never_labels_non_signals():
    from nifty_trading.strategies.base import SignalStatus as SS
    eng = IRFStrategy()
    c = ctx([(95, 100, 90, 98), (98, 104, 97, 103)])
    cd = eng.__class__.__mro__  # noqa: F841 - keeps the import graph exercised
    from nifty_trading.strategies.definitions import to_candles
    cs = to_candles(c.candles)
    ok = eng._rec(c, cs[1], "Method 1", Direction.SHORT, {}, ["IRF-GLOBAL-001"], status=SS.CONFIRMED)
    assert ok.verification_status == "VERIFIED" and ok.execution_config["entry_rule_status"] == "VERIFIED_EXPLICIT"
    not_sig = eng._rec(c, cs[1], "Method 1", Direction.SHORT, {}, ["IRF-GLOBAL-001"], status=SS.INVALIDATED, why="x")
    assert not_sig.execution_config["entry_rule_status"] == "NOT_A_CONFIRMED_SIGNAL"
    assert not_sig.execution_config["execution_status"] == "NOT_A_CONFIRMED_SIGNAL"


# --- float boundaries at index-scale prices (F8): exact-arithmetic boundary candles must classify the same way every time
@pytest.mark.rules("CANDLE-DEF-001")
def test_boundary_candles_at_index_scale_prices_are_not_flipped_by_float_error():
    p = ProposalConfig()
    assert is_small(C(24016.9, 24017.05, 24016.55, 24016.75), p)   # body 0.15 is exactly 30% of the 0.50 range
    assert bullish_pin(C(24003.1, 24003.25, 24002.9, 24003.2), p)  # wick 0.2 == 2 x body 0.1 -> exactly on the limit; close 0.05 below the high
    assert strong_bullish(C(24000.1, 24001.0, 24000.0, 24000.8), p)  # body 70%, upper wick 20%: the wick limit is hit exactly
    assert not is_small(C(24016.9, 24017.05, 24016.55, 24016.74), p)  # clearly over the limit still fails


# --- gaps found by the reviewer's mutation run
@pytest.mark.rules("TREND-SWING-001")
def test_swing_low_is_strict_and_an_equal_neighbour_is_not_a_swing():
    lows = [C(9, 9, lw, 9) for lw in (5, 4, 1, 4, 5)]
    assert confirmed_swing_lows(lows, 4) == [2]
    assert confirmed_swing_lows([C(9, 9, lw, 9) for lw in (5, 1, 1, 4, 5)], 4) == []   # equal neighbour before
    assert confirmed_swing_lows([C(9, 9, lw, 9) for lw in (5, 4, 1, 1, 5)], 4) == []   # equal neighbour after
    assert confirmed_swing_lows([C(9, 9, lw, 9) for lw in (0, 5, 1, 4, 5)], 4) == []   # the candle two before is lower
    assert confirmed_swing_lows([C(9, 9, lw, 9) for lw in (5, 4, 1, 5, 0)], 4) == []   # the candle two after is lower


@pytest.mark.rules("TREND-STRUCT-001")
def test_structure_trend_with_a_single_swing_high_or_low_is_false_not_an_error_and_each_condition_matters():
    one_high = [(20, 12), (22, 12), (30, 14), (22, 12), (20, 11), (19, 9), (18, 12), (17, 16), (16, 14), (16, 12), (15, 13), (15, 14), (14, 14)]
    prev = _structure_prev(one_high, 30.0, 25.0)
    cs = [C(*c) for c in prev["cands"]]
    assert len(confirmed_swing_highs(cs, len(cs) - 1)) == 1 and len(confirmed_swing_lows(cs, len(cs) - 1)) >= 2
    t = structure_trend(ctx([(100, 101, 99, 100)], prev=prev), "LONG", ProposalConfig())
    assert t.ok is False and "fewer than two" in t.reason
    # SHORT side: the mirror needs BOTH lower highs and lower lows; one failing condition is enough to reject
    mirror = [(100 - lw, 100 - h) for h, lw in HL_UP]
    def short(hl):
        return structure_trend(ctx([(100, 101, 99, 100)], prev=_structure_prev(hl, 70.0, 75.0)), "SHORT", ProposalConfig()).ok
    assert short(mirror) is True
    higher_second_high = [(h + (3 if i == 10 else 0), lw) for i, (h, lw) in enumerate(mirror)]
    assert short(higher_second_high) is False                       # swing highs no longer falling (low side still falling)
    higher_second_low = [(h, lw + (9 if i == 8 else 0)) for i, (h, lw) in enumerate(mirror)]
    assert short(higher_second_low) is False                        # swing lows no longer falling (high side still falling)


@pytest.mark.rules("CANDLE-DEF-001", "IRF-M3-001")
def test_compression_c3_needs_every_candle_small_and_inside_the_range():
    from nifty_trading.strategies.definitions import compression_ok
    small, big = (100, 102, 98, 100.5), (100, 104, 96, 103)  # small: body 0.5 of range 4 (12%); big: body 3 of 8 (37.5%)
    cs = [C(95, 110, 90, 100), C(*small), C(*small), C(*big)]
    p3 = ProposalConfig(m3_compression_def="C3", m3_compression_n=2)
    assert compression_ok(cs, 3, 90, 110, p3)                       # candles 1-2 are small and inside
    cs2 = [C(95, 110, 90, 100), C(*big), C(*small), C(*big)]
    assert not compression_ok(cs2, 3, 90, 110, p3)                  # one big candle among the two -> not compressed
    assert compression_ok(cs2, 3, 90, 110, ProposalConfig(m3_compression_def="C1", m3_compression_n=2))  # C1 ignores shape
    outside = [C(95, 110, 90, 100), C(*small), C(100, 120, 99, 100.5), C(*big)]
    assert not compression_ok(outside, 3, 90, 110, p3)              # a small candle that leaves the range still fails


@pytest.mark.rules("PDR-ZONE-002")
def test_zone_b_counts_the_peak_candle_itself_as_the_reversal_and_cluster_tolerance_is_inclusive():
    # only the peak candle (idx 9) is red: it must count (window starts AT the peak)
    z = _zone("B_SWING_HIGH_REVERSAL", red={9})
    assert z.candle_index == 9
    # idx 6 and 9 highs 118 / 118.5 are 0.5 apart: tolerance 0.5 is inclusive, 0.49 is not
    assert _zone("C_REPEATED_TOUCHES", zone_cluster_tolerance_points=0.5).members == (6, 9)
    assert _zone("C_REPEATED_TOUCHES", zone_cluster_tolerance_points=0.49) is None
    # Zone.candle_index for a cluster is its LAST member, for method A the (tie-broken) high candle
    assert _zone("C_REPEATED_TOUCHES").candle_index == 9 and _zone("A_HIGHEST_HIGH").candle_index == 2


@pytest.mark.rules("PDR-006")
def test_proximity_is_applied_on_the_correct_side_of_the_zone_bottom():
    """The zone is [23975, 24000]. A candle entirely below it interacts only within the proximity ON THAT SIDE."""
    green = (23976, 23995, 23970, 23992)
    c0 = (24050, 24060, 24040, 24055)
    def run(high_below, prox):
        below = (23960, high_below, 23950, 23962)
        return _confirmed(_pdr([c0, below, green], zone_proximity_points=prox, zone_lower_boundary="ZONE_FULL"))
    assert run(23969.9, 5.0) == [] and run(23970.0, 5.0) != []  # 23970 = zone bottom 23975 - 5: inclusive
    assert run(23974.9, 0.0) == []                               # below the zone with no proximity: no interaction


@pytest.mark.rules("TREND-SWING-001")
def test_a_swing_needs_k_candles_on_both_sides_and_never_wraps_around_the_start():
    """A candle at index 1 has only one candle before it: it can never be a swing (negative indexing must not wrap to the last candle)."""
    assert confirmed_swing_lows([C(9, 9, lw, 9) for lw in (5, 1, 4, 6, 7)], 4) == []
    assert confirmed_swing_highs([C(1, h, 0, 1) for h in (5, 9, 6, 4, 3)], 4) == []
    assert confirmed_swing_lows([C(9, 9, lw, 9) for lw in (5, 6, 1, 6, 7)], 4) == [2]  # index 2 is the first candle that can be one


@pytest.mark.rules("PDS-005")
def test_pds_ignores_a_candle_that_jumps_entirely_above_the_zone_without_intersecting_it():
    c = ctx([(23950, 23960, 23940, 23945), (24030, 24040, 24027, 24035)], prev=PDS_PREV)  # zone [24000, 24025]; candle 2 lies wholly above it
    assert PDSStrategy().evaluate_session(c) == []


@pytest.mark.rules("ORB-M2-LONG-004")
def test_orb_near_ma_uses_the_opening_candle_ema_under_the_structure_trend():
    from nifty_trading.strategies.definitions import TrendResult
    orb = ORBStrategy()
    c = ctx([(100, 101, 99, 100)], prev=_structure_prev(HL_UP, 30.0, 25.0), ema=77.0)
    prev_ema_result = TrendResult(True, "x", 25.0)
    assert orb._near_ma_value(c, prev_ema_result) == 77.0  # today's EMA, not the previous session's 25
    legacy = ORBStrategy(proposals=ProposalConfig(trend_mode="EMA5M_PREV_SESSION"))
    assert legacy._near_ma_value(c, TrendResult(True, "x", 77.5)) == 77.5  # the older modes already report the opening candle's EMA


@pytest.mark.rules("PDR-004", "PDS-003", "RF-003")
def test_a_flat_open_is_no_gap_so_nothing_is_evaluated_at_all():
    """Open exactly equal to the previous official close: neither a gap up nor a gap down. The engines return no record (not an INVALIDATED one)."""
    flat = ctx([(23950, 23960, 23940, 23955), (23955, 23990, 23950, 23985)], prev={**PDR_PREV, "close": 23950.0})
    assert PDRStrategy().evaluate_session(flat) == []
    assert PDSStrategy().evaluate_session(flat) == []


@pytest.mark.rules("PDS-M2-001")
def test_pds_pin_bar_whose_high_only_reaches_the_zone_bottom_counts_as_pushing_into_it():
    """Method 2 needs the pin's wick to push INTO the zone: a high exactly at the zone bottom (24,000) qualifies, 0.05 short does not."""
    first = (23950, 23960, 23940, 23945)
    at = ctx([first, (23992, 24000.0, 23990.6, 23991)], prev=PDS_PREV)
    assert [r.method for r in _confirmed(PDSStrategy().evaluate_session(at))] == ["Method 2"]
    near = PDSStrategy(proposals=ProposalConfig(zone_proximity_points=5.0))  # within 5 points counts as 'at the zone', but a pin must still reach it
    short = ctx([first, (23992, 23999.95, 23990.6, 23991)], prev=PDS_PREV)
    assert [r.method for r in _confirmed(near.evaluate_session(at))] == ["Method 2"]
    assert "Method 2" not in [r.method for r in _confirmed(near.evaluate_session(short))]  # 0.05 short of the zone: not a Method-2 pin
    assert not _confirmed(PDSStrategy().evaluate_session(short))  # strict default: not even at the zone
