"""Phase 6.1 IRF-V2-SUPPORT-BREAK tests: the reference-candle state machine (the brief's regression example, strict close, wick-only, no self-break, first reference never replaced, no retest, search start), the 28-point
clearance, and real-data invariants (IRF V2 == Phase 5.3 IRF; every Method 2A signal's support is its first red candle's wick low and the break close is strictly below; causal diagnostics)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from nifty_trading.strategies.definitions import Candle
from nifty_trading.strategies.irf_phase53 import ema_geometry
from nifty_trading.strategies.irf_v2 import SupportBreakMachine

T0 = datetime(2025, 9, 16, 9, 15)


def mk(i, o, h, l, c):  # noqa: E741
    s = T0 + timedelta(minutes=5 * i)
    return Candle(s, s + timedelta(minutes=5), o, h, l, c, float("nan"))


def run(cs, start="AFTER_EXTENSION", irh=None):
    irh = cs[0].h if irh is None else irh
    m = SupportBreakMachine(1, start)
    for i in range(1, len(cs)):
        m.step(cs, i, irh, "E1", False)
    return m


BASE = [mk(0, 25090, 25100, 25080, 25095),         # initial range: IRH 25100
        mk(1, 25098, 25120, 25096, 25118),         # breakout close above IRH
        mk(2, 25118, 25135, 25115, 25130)]         # extension (higher high than the breakout candle)


def test_brief_regression_example_reference_support_25110_break_only_on_the_later_close_25102():
    cs = BASE + [mk(3, 25150, 25162, 25110, 25125),    # first red candle after the extension: low 25110 = support
                 mk(4, 25124, 25128, 25112, 25118),    # close 25118: NOT below support -> no signal
                 mk(5, 25118, 25120, 25098, 25102)]    # close 25102 < 25110 -> support break confirmed here
    m = run(cs)
    assert m.reference == 3 and m.support == 25110
    assert [b for _, _, b in m.closes_after_reference] == [False, True]
    assert m.broken_at == 5 and m.state == "SUPPORT_BROKEN"


def test_close_equal_to_support_and_a_wick_only_break_are_not_breaks():
    cs = BASE + [mk(3, 25150, 25162, 25110, 25125), mk(4, 25120, 25122, 25100, 25110.0),      # close == support: strict -> no
                 mk(5, 25112, 25114, 25090, 25111)]                                         # wick far below support, close above: no
    m = run(cs)
    assert m.support == 25110 and m.broken_at is None and m.state == "SUPPORT_SET"


def test_closes_are_only_examined_for_candles_after_the_reference_and_the_reference_is_never_replaced():
    cs = BASE + [mk(3, 25150, 25162, 25110, 25111),    # red; its own close 25111 is above its own low (a candle can never close below its own low)
                 mk(4, 25111, 25112, 25095, 25100),    # a LATER red candle with a lower low must NOT replace the reference; it closes below 25110 -> the break
                 ]
    m = run(cs)
    assert m.reference == 3 and m.support == 25110 and m.broken_at == 4
    assert all(idx > m.reference for idx, _, _ in m.closes_after_reference)      # the reference candle itself is never examined as a breaking candle


def test_no_retest_is_required_and_no_entry_without_established_support():
    no_red = BASE + [mk(3, 25130, 25140, 25128, 25138), mk(4, 25138, 25150, 25137, 25149)]     # extension continues; green candles only: no reference, no break
    m = run(no_red)
    assert m.reference is None and m.broken_at is None
    cs = BASE + [mk(3, 25150, 25162, 25110, 25125), mk(4, 25122, 25123, 25090, 25095)]         # price never returns to retest the support; the break at 25095 stands
    assert run(cs).broken_at == 4


def test_red_search_starts_after_the_extension_candle_by_default_and_after_the_breakout_in_the_variant():
    cs = [mk(0, 25090, 25100, 25080, 25095), mk(1, 25098, 25120, 25096, 25118), mk(2, 25118, 25119, 25100, 25105),   # red candle BEFORE any extension (high not above the breakout high)
          mk(3, 25105, 25135, 25104, 25130), mk(4, 25130, 25131, 25120, 25122)]                                       # the extension, then a red candle
    assert run(cs).reference == 4
    assert run(cs, "AFTER_BREAKOUT").reference == 2


def test_a_candle_that_is_green_is_never_a_reference():
    cs = BASE + [mk(3, 25130, 25140, 25100, 25139), mk(4, 25139, 25141, 25101, 25140)]
    assert run(cs).reference is None


@pytest.mark.parametrize("ema,expect", [(25000.0, 28.0), (25100.0, 28.0)])
def test_ema_range_clearance_is_measured_to_the_nearest_point_of_the_range(ema, expect):
    g = ema_geometry(h=ema + 40.0, l=ema + 28.0, c=ema + 30.0, ema=ema)
    assert g["range_clearance"] == expect and g["relation"] == "EMA_BELOW_CANDLE"
    inside = ema_geometry(h=ema + 5.0, l=ema - 5.0, c=ema, ema=ema)
    assert inside["range_clearance"] == 0.0 and inside["relation"] == "EMA_INSIDE_CANDLE"


# ---------------------------------------------------------------------------------------------------------------- real data
@pytest.fixture(scope="module")
def real():
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    from nifty_trading.research import phase3 as P
    from nifty_trading.strategies.irf_phase53 import IRFPhase53Strategy
    from nifty_trading.strategies.irf_v2 import IRFV2SupportBreakStrategy
    ctxs, _ = build_session_contexts(load_one_minute(), daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    days = sorted(ctxs)[::3]                                # every third session: fast and spread over the whole year
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    p53 = IRFPhase53Strategy(proposals=sc.proposals, trade=sc.trade, support_ref="FIRST_RED_LOW", ema_min_clearance=28.0, ema_scope="ALL_METHODS", ema_measure="RANGE")
    v2 = IRFV2SupportBreakStrategy(proposals=sc.proposals, trade=sc.trade)
    out = {"p53": [], "v2": [], "ctx": ctxs, "days": days}
    for d in days:
        out["p53"] += [(str(d), f"{r.signal_timestamp:%H:%M}", r.method) for r in p53.evaluate_session(ctxs[d]) if r.signal_status == "CONFIRMED"]
        out["v2"] += [r for r in v2.evaluate_session(ctxs[d]) if r.signal_status == "CONFIRMED"]
    out["attempts"] = list(v2.attempt_log)
    return out


def test_irf_v2_emits_exactly_the_phase53_signals_on_the_sampled_sessions(real):
    assert sorted((str(r.signal_date), f"{r.signal_timestamp:%H:%M}", r.method) for r in real["v2"]) == sorted(real["p53"]) and len(real["v2"]) > 20


def test_every_method2a_signal_uses_the_first_red_candles_wick_low_and_a_strictly_lower_close(real):
    n = 0
    for r in real["v2"]:
        if r.method != "Method 2A":
            continue
        lv = r.reference_levels
        assert lv["recent_support"] == lv["first_red_candle_low"] and lv["support_ref"] == "FIRST_RED_LOW"
        assert r.signal_candle_close < lv["recent_support"] - 1e-9                      # strictly below
        assert lv["support_break_close"] == r.signal_candle_close and lv["candles_between_reference_and_break"] >= 0
        assert lv["first_red_candle_start"] < f"{r.signal_candle_start:%H:%M}"          # the reference candle is an EARLIER candle
        n += 1
    assert n > 0


def test_attempt_audit_rows_are_consistent_with_the_rule(real):
    n = 0
    for a in real["attempts"]:
        if not a["reference_candle_start"]:
            continue
        o, h, lo, c = (float(x) for x in a["reference_ohlc"].split("/"))
        assert c < o and a["support_wick_low"] == lo                                     # a red candle; support = its wick low
        if a["first_close_below_support"]:
            assert a["first_close_below_support"] > a["reference_candle_start"]
        n += 1
    assert n > 10


def test_diagnostics_are_causal_and_the_days_low_restriction_is_not_applied(real):
    for r in real["v2"][:80]:
        lv = r.reference_levels
        ctx = real["ctx"][r.signal_date]
        lows_to_signal = ctx.candles[ctx.candles["bar_end"] <= pd.Timestamp(r.signal_timestamp)]["low"]
        assert abs(lv["running_low_through_signal_candle"] - float(lows_to_signal.min())) < 1e-9
        assert "NOT applied" in lv["days_low_diagnostic_note"]
        assert r.proposals_used.get("days_low_restriction", "").startswith("NOT_APPLIED") or r.method not in ("Method 2A", "Method 2B")
