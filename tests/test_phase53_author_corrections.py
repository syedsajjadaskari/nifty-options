"""Phase 5.3: the owner-approved author corrections (IRF first-red-candle LOW support, IRF minimum 28-point EMA clearance, PDR / PDS earliest eligible confirmation) as separately versioned configurations.

Synthetic-candle unit tests of every rule and boundary, regression tests on the real 2025-26 sessions (the frozen signals are unchanged, each configuration changes only its own strategy, every surviving IRF signal
satisfies the clearance) and file-level tests on the delivered bundle. No profit is computed anywhere."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pytest
from synthetic import ctx

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase53 as F
from nifty_trading.research import phase53_diag as D
from nifty_trading.strategies.definitions import Candle, to_candles
from nifty_trading.strategies.first_eligible_phase53 import (
    PDRFirstEligibleStrategy,
    PDSFirstEligibleStrategy,
    pdr_minimal_confirmation,
    pds_good_red,
    pds_red_pin,
)
from nifty_trading.strategies.irf import IRFStrategy
from nifty_trading.strategies.irf_phase53 import IRFPhase53Strategy, ema_geometry
from nifty_trading.strategies.pdr_body import PDRBodyStrategy
from nifty_trading.strategies.pds import PDSStrategy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase53_author_corrected"
SC = P.combined_scenario("BODY_BASED_PHASE36")
T0 = datetime(2026, 1, 1, 9, 15)


def key(r):
    return (r.strategy, r.method, r.direction, r.signal_status, None if r.signal_timestamp is None else r.signal_timestamp.isoformat(), r.invalidation_reason)


def confirmed(records, strategy=None, method=None):
    return sorted((r for r in records if r.signal_status == "CONFIRMED" and (strategy is None or r.strategy == strategy) and (method is None or r.method == method)), key=lambda r: r.signal_timestamp)


def hm(ts) -> str:
    return f"{ts:%H:%M}"


# ======================================================================= IRF: first red candle's LOW
IRF_DAY = [(100, 110, 99, 105),  # IRH 110
           (105, 115, 104, 114),  # breakout close 114 > 110
           (114, 118, 113, 117),  # extension (high 118 > 115)
           (117, 118.5, 111, 112),  # FIRST RED candle after the extension: low 111, body low 112
           (112, 114, 110.5, 111.5),  # red, later: closes 111.5, above its low 111 and the first red's low
           (111.5, 113, 109, 110.8),  # closes 110.8 < 111: breaks the first red candle's LOW
           (110.8, 111.2, 108, 108.5)]  # a later red candle (must not become the reference)


def irf(day=IRF_DAY, ema=float("nan"), **kw):
    c = ctx(day, ema=ema)
    eng = IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade, **kw)
    return eng, eng.evaluate_session(c)


def test_first_red_candle_low_is_the_support_and_a_later_red_candle_never_replaces_it():
    _, recs = irf(support_ref="FIRST_RED_LOW")
    m2a = confirmed(recs, "IRF", "Method 2A")
    assert hm(m2a[0].signal_timestamp) == "09:45"  # candle 5 (09:40) closes 110.8 < 111 -> activated at ITS close
    lv = m2a[0].reference_levels
    assert lv["recent_support"] == 111 and lv["support_candle_index"] == 3 and lv["red_candle_index"] == 3 and lv["first_red_candle_low"] == 111 and lv["support_ref"] == "FIRST_RED_LOW"
    assert all(r.reference_levels["support_candle_index"] == 3 for r in m2a)  # the later red candles (indices 4 and 6) are never the reference
    body = [r for r in irf(support_ref="FIRST_RED_BODY_LOW")[1] if r.method == "Method 2A" and r.signal_status == "CONFIRMED"]
    assert body[0].reference_levels["recent_support"] == 112  # the body low is a different (unapproved) level: not used by the Phase 5.3 key


def test_default_arguments_equal_the_frozen_engine_and_the_scope_is_method_2a_only():
    c = ctx(IRF_DAY)
    frozen = [key(r) for r in IRFStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)]
    default = [key(r) for r in IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)]
    assert frozen == default
    cand = IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade, support_ref="FIRST_RED_LOW").evaluate_session(c)
    others = lambda rs: [key(r) for r in rs if r.signal_status == "CONFIRMED" and r.method in ("Method 1", "Method 2B", "Method 3")]  # noqa: E731
    assert others(cand) == others(IRFStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c))
    with pytest.raises(ValueError):
        IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade, red_search_start="LATER")


RED_BEFORE_EXTENSION = [(100, 110, 99, 105),  # IRH 110
                        (105, 115, 104, 114),  # breakout (close 114)
                        (114, 114.5, 111, 112),  # RED after the breakout, close 112 > IRH, high 114.5 < 115: not the extension
                        (112, 119, 111.5, 118),  # extension
                        (119, 119.5, 116, 117),  # first red AFTER THE EXTENSION: low 116
                        (117, 117.5, 114, 115.5),  # closes 115.5 < 116 (after-extension reference) but > 111 (after-breakout reference)
                        (115.5, 116, 110, 110.5)]  # closes 110.5 < 111


def test_the_red_search_start_is_a_selectable_assumption_with_a_visible_effect():
    ext = confirmed(irf(RED_BEFORE_EXTENSION, support_ref="FIRST_RED_LOW", red_search_start="AFTER_EXTENSION")[1], "IRF", "Method 2A")
    brk = confirmed(irf(RED_BEFORE_EXTENSION, support_ref="FIRST_RED_LOW", red_search_start="AFTER_BREAKOUT")[1], "IRF", "Method 2A")
    assert hm(ext[0].signal_timestamp) == "09:45" and ext[0].reference_levels["recent_support"] == 116 and ext[0].reference_levels["red_candle_index"] == 4
    assert hm(brk[0].signal_timestamp) == "09:50" and brk[0].reference_levels["recent_support"] == 111 and brk[0].reference_levels["red_candle_index"] == 2


# ======================================================================= IRF: minimum 28-point EMA clearance
def test_range_clearance_geometry_covers_above_below_and_inside():
    assert ema_geometry(113, 109, 110.8, 81)["relation"] == "EMA_BELOW_CANDLE" and ema_geometry(113, 109, 110.8, 81)["range_clearance"] == 28
    assert ema_geometry(113, 109, 110.8, 141)["relation"] == "EMA_ABOVE_CANDLE" and ema_geometry(113, 109, 110.8, 141)["range_clearance"] == 28
    inside = ema_geometry(113, 109, 110.8, 110)
    assert inside["relation"] == "EMA_INSIDE_CANDLE" and inside["range_clearance"] == 0.0 and round(inside["close_distance"], 6) == 0.8


@pytest.mark.parametrize(("ema", "expected"), [(81.0, True), (81.01, False), (80.0, True), (141.0, True), (141.01, True), (140.99, False), (110.0, False)])
def test_the_28_point_boundary_is_inclusive_and_uses_the_nearest_point_of_the_range(ema, expected):
    # the signal candle (index 5) has H 113, L 109: distance below = 109 - ema, above = ema - 113
    _, recs = irf(support_ref="FIRST_RED_LOW", ema=[ema] * 7, ema_min_clearance=28.0)
    got = any(hm(r.signal_timestamp) == "09:45" for r in confirmed(recs, "IRF", "Method 2A"))
    assert got is expected


def test_a_rejected_candidate_is_logged_and_the_attempt_stays_alive_for_a_later_qualifying_candle():
    ema = [60.0] * 5 + [110.0] + [60.0]  # candle 5: EMA inside the range (rejected); candle 6: EMA 60 far below (passes)
    eng, recs = irf(support_ref="FIRST_RED_LOW", ema=ema, ema_min_clearance=28.0)
    m2a = confirmed(recs, "IRF", "Method 2A")
    assert [hm(r.signal_timestamp) for r in m2a][:1] == ["09:50"]  # the SAME attempt qualifies one candle later
    rej = [x for x in eng.rejections if x["method"] == "Method 2A"]
    assert rej and rej[0]["signal_time"] == "09:45" and rej[0]["relation"] == "EMA_INSIDE_CANDLE" and rej[0]["distance"] == 0.0
    assert any("PHASE53_EMA_RANGE_DISTANCE" in f for f in m2a[0].flags)


def test_ema_available_after_the_decision_cannot_change_the_outcome_and_missing_ema_does_not_reject():
    ema_full = [60.0] * 5 + [110.0] + [60.0]
    full = [hm(r.signal_timestamp) for r in confirmed(irf(support_ref="FIRST_RED_LOW", ema=ema_full, ema_min_clearance=28.0)[1], "IRF", "Method 2A")]
    # a different EMA value AFTER the first decision candle (candle 6) cannot influence the decision taken at candle 5
    other = [hm(r.signal_timestamp) for r in confirmed(irf(support_ref="FIRST_RED_LOW", ema=[60.0] * 5 + [110.0] + [110.0], ema_min_clearance=28.0)[1], "IRF", "Method 2A")]
    assert full[:1] == ["09:50"] and other == []  # candle 6's own EMA decides candle 6, nothing later does
    _, nan_recs = irf(support_ref="FIRST_RED_LOW", ema=float("nan"), ema_min_clearance=28.0)
    assert any(hm(r.signal_timestamp) == "09:45" for r in confirmed(nan_recs, "IRF", "Method 2A"))  # unknown is not 'less than 28'


def test_27_and_28_give_different_answers_and_the_close_reading_differs_from_the_range_reading():
    ema = [81.5] * 7  # range clearance 27.5
    assert not any(hm(r.signal_timestamp) == "09:45" for r in confirmed(irf(support_ref="FIRST_RED_LOW", ema=ema, ema_min_clearance=28.0)[1], "IRF", "Method 2A"))
    assert any(hm(r.signal_timestamp) == "09:45" for r in confirmed(irf(support_ref="FIRST_RED_LOW", ema=ema, ema_min_clearance=27.0)[1], "IRF", "Method 2A"))
    ema2 = [141.0] * 7  # EMA above: range clearance 28 (passes), close distance 30.2 (passes); EMA at 138: range 25, close 27.2
    assert any(hm(r.signal_timestamp) == "09:45" for r in confirmed(irf(support_ref="FIRST_RED_LOW", ema=ema2, ema_min_clearance=28.0)[1], "IRF", "Method 2A"))
    ema3 = [138.0] * 7
    assert not any(hm(r.signal_timestamp) == "09:45" for r in confirmed(irf(support_ref="FIRST_RED_LOW", ema=ema3, ema_min_clearance=28.0)[1], "IRF", "Method 2A"))
    inside = [112.0] * 7  # EMA inside the range: range clearance 0 -> rejected, though |close - EMA| = 1.2 is a small number too: both reject
    assert not confirmed(irf(support_ref="FIRST_RED_LOW", ema=inside, ema_min_clearance=28.0)[1], "IRF", "Method 2A")


def test_scope_variants_gate_the_right_methods():
    c = ctx([(100, 110, 99, 105), (105, 115, 104, 114), (114, 114.5, 103, 109)], ema=[109.0] * 3)  # Method 1: breakout then close back inside the range; the EMA lies inside the candle
    all_m = IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade, ema_min_clearance=28.0, ema_scope="ALL_METHODS")
    m2_only = IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade, ema_min_clearance=28.0, ema_scope="METHOD2_ONLY")
    frozen = confirmed(IRFStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c), "IRF", "Method 1")
    assert frozen  # the scenario does produce a Method 1 signal in the frozen engine
    assert not confirmed(all_m.evaluate_session(c), "IRF", "Method 1") and all_m.rejections and all_m.rejections[0]["method"] == "Method 1"
    assert [key(r) for r in confirmed(m2_only.evaluate_session(c), "IRF", "Method 1")] == [key(r) for r in frozen]


# ======================================================================= PDR: earliest eligible confirmation (minimal convention)
PREV_PDR = {"cands": [(100, 105, 99, 104), (104, 110, 103, 108), (108, 109, 100, 101)], "close": 101.0}  # highest body high = candle 1: zone [104, 108]


def pdr_run(today, cls=PDRFirstEligibleStrategy, open_price=112.0):
    c = ctx(today, prev=PREV_PDR, open_price=open_price)
    eng = cls(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    return c, eng.evaluate_session(c)


WEAK_GREEN_FIRST = [(112, 113, 110, 111),  # 09:15 above the zone, no retest
                    (111, 111.5, 107, 108.5),  # 09:20 retest candle (red)
                    (108.2, 109.0, 107.9, 108.6),  # 09:25 FIRST ELIGIBLE: small green candle (body 36%, upper wick 36%), close above the ceiling 108
                    (108.6, 112, 108.5, 111.8)]  # 09:30 strong green: later and stronger, must not replace the first


def test_the_first_green_candle_after_the_retest_is_the_entry_even_when_it_fails_the_old_numeric_thresholds():
    _, new = pdr_run(WEAK_GREEN_FIRST)
    _, old = pdr_run(WEAK_GREEN_FIRST, cls=PDRBodyStrategy)
    assert hm(confirmed(new, "PDR")[0].signal_timestamp) == "09:30"  # candle 09:25 closes at 09:30
    assert hm(confirmed(old, "PDR")[0].signal_timestamp) == "09:35"  # the frozen engine waited for the strong candle
    assert len([r for r in confirmed(new, "PDR") if hm(r.signal_timestamp) == "09:35"]) == 0  # the later, stronger candle is not an entry
    assert "PROVISIONAL_PDR_MINIMAL_CONFIRMATION" in confirmed(new, "PDR")[0].flags


def test_a_green_candle_must_still_close_strictly_above_the_ceiling_and_come_after_the_retest():
    today = [(112, 113, 110, 111), (107.5, 109.5, 107.2, 109.0),  # 09:20 green, closes above the ceiling, but it IS the retest candle
             (108.0, 108.5, 107.5, 108.0),  # 09:25 close == ceiling: not strictly above (and not green)
             (107.6, 108.0, 107.0, 107.9),  # 09:30 green, closes inside the zone (<= ceiling): not eligible
             (107.9, 109.5, 107.8, 109.0)]  # 09:35 green, closes above: the first eligible confirmation
    _, recs = pdr_run(today)
    conf = confirmed(recs, "PDR")
    assert [hm(r.signal_timestamp) for r in conf][:1] == ["09:40"]
    before = [(112, 120, 111.5, 119), (119, 121, 118.5, 120.5)] + today[1:]  # strong green candles far above the zone before any retest
    _, r2 = pdr_run(before)
    assert [hm(r.signal_timestamp) for r in confirmed(r2, "PDR")][:1] == ["09:45"]


def test_lower_price_rejection_of_any_colour_qualifies_when_the_close_is_above_the_ceiling():
    red_rejection = (111.0, 111.2, 105.0, 110.9)  # red body 0.1, lower wick 5.9 > body and > upper wick, low reached the zone, close above 108
    assert pdr_minimal_confirmation(Candle(T0, T0, 111.0, 111.2, 105.0, 110.9, float('nan')), 104.0, 108.0, 0.0)["qualifies"] is True
    today = [(112, 113, 110, 111), (111, 111.5, 107, 108.5), red_rejection]
    _, recs = pdr_run(today)
    assert hm(confirmed(recs, "PDR")[0].signal_timestamp) == "09:30"
    assert confirmed(recs, "PDR")[0].reference_levels["patterns_passed"] == ["LOWER_PRICE_REJECTION"]


def test_pdr_setup_conditions_are_preserved():
    _, recs = pdr_run(WEAK_GREEN_FIRST, open_price=108.0)  # open == ceiling: not strictly above
    assert not confirmed(recs) and recs[0].invalidation_reason == "OPEN_NOT_STRICTLY_ABOVE_ZONE"
    no_gap = ctx(WEAK_GREEN_FIRST, prev=PREV_PDR, open_price=100.0)
    assert not confirmed(PDRFirstEligibleStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision).evaluate_session(no_gap))


def test_pdr_uses_only_closed_candles_a_prefix_gives_the_same_first_signal():
    eng = PDRFirstEligibleStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    full = ctx(WEAK_GREEN_FIRST, prev=PREV_PDR, open_price=112.0)
    first = hm(confirmed(eng.evaluate_session(full))[0].signal_timestamp)
    assert first == "09:30"
    pre = confirmed(eng.evaluate_session(full.prefix(3)))
    assert hm(pre[0].signal_timestamp) == first  # candles after the decision change nothing
    assert not confirmed(eng.evaluate_session(full.prefix(2)))


def test_diagnostic_setup_agrees_with_the_engine_and_reports_the_retest_candle_separately():
    today = [(112, 113, 110, 111), (107.5, 109.5, 107.2, 109.0), (109.0, 110, 108.6, 109.8)]
    c, recs = pdr_run(today)
    d = D.pdr_phase53_setup(c, SC)
    assert d["status"] == "ARMED" and d["retest_candle_would_qualify_if_permitted"] is True and d["first_eligible_signal_time"] == hm(confirmed(recs, "PDR")[0].signal_timestamp) == "09:30"
    assert d["first_retest_confirmation_if_retest_permitted"] == "09:25"  # what the (unapproved) alternative sequencing would have done


# ======================================================================= PDS: earliest eligible bearish confirmation, source sequence preserved
PREV_PDS = {"cands": [(100, 102, 96, 101), (101, 101.5, 95, 100), (100, 100.5, 96, 99.5)], "close": 99.0}  # lowest low = candle 1 (95): zone [95, 101]


def pds_run(today, cls=PDSFirstEligibleStrategy):
    c = ctx(today, prev=PREV_PDS, open_price=90.0)
    return c, cls(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)


def test_a_red_candle_whose_body_dominates_is_method_1_even_below_the_old_60_percent():
    today = [(90, 92, 89, 91), (91, 96, 90.5, 95.5),  # 09:20 first touch (green)
             (95.5, 97.0, 91.9, 93.0)]  # 09:25 first red candle at the zone: body 2.5 of range 5.1 = 49% > both wicks (1.5, 1.1): good red, but the frozen engine needs 60%
    _, new = pds_run(today)
    _, old = pds_run(today, cls=PDSStrategy)
    n = confirmed(new, "PDS")
    assert n[0].method == "Method 1" and hm(n[0].signal_timestamp) == "09:30" and "PROVISIONAL_PDS_MINIMAL_QUALITY" in n[0].flags
    assert not [r for r in confirmed(old, "PDS") if hm(r.signal_timestamp) == "09:30"]


def test_a_red_pin_bar_is_method_2_and_the_two_tests_are_mutually_exclusive():
    today = [(90, 92, 89, 91), (91, 96, 90.5, 95.5), (95.0, 99.0, 93.9, 94.0)]  # red, upper wick 4.0 > body 1.0 and > lower wick 0.1, high reached the zone
    _, recs = pds_run(today)
    assert confirmed(recs, "PDS")[0].method == "Method 2"
    for o, h, l, c in [(95.0, 99.0, 93.9, 94.0), (95.5, 97.0, 91.9, 93.0), (97, 98, 95.2, 96.5), (95, 96, 90, 94)]:
        cand = Candle(T0, T0, o, h, l, c, float('nan'))
        assert not (pds_good_red(cand) and pds_red_pin(cand, 95.0))


def test_a_weak_first_red_candle_is_never_taken_it_goes_to_method_3_and_needs_the_support_break():
    today = [(90, 92, 89, 91), (91, 96, 90.5, 95.5),
             (97, 98, 95.2, 96.5),  # 09:25 first red candle: body 18% with larger wicks: weak (source quality rule)
             (96.5, 96.8, 94.5, 95.0), (95.0, 96.0, 94.8, 95.8),
             (95.8, 96.0, 93.0, 93.5),  # 09:40 closes below the small support 94.5: Method 3
             (93.5, 94.0, 92.0, 92.5)]
    _, recs = pds_run(today)
    conf = confirmed(recs, "PDS")
    assert conf[0].method == "Method 3" and hm(conf[0].signal_timestamp) == "09:45"
    assert all(hm(r.signal_timestamp) != "09:30" for r in conf)  # not on the weak candle
    no_break = today[:5]
    assert not confirmed(pds_run(no_break)[1], "PDS")  # without the break there is no entry: Method 3's break is mandatory
    d = D.pds_phase53_first_red(ctx(today, prev=PREV_PDS, open_price=90.0), SC)
    assert d["phase53_verdict"].startswith("WEAK") and d["first_red_candle_start"] == "09:25"


# ======================================================================= configurations and global invariants
def test_configurations_are_separately_selectable_and_replace_only_their_own_slot():
    assert {"phase36-frozen", "phase52-approved", "phase53-irf-first-red-low", "phase53-irf-ema28", "phase53-pdr-first-eligible", "phase53-pds-first-eligible", "phase53-author-corrected"} <= set(F.CONFIGS)
    names = {k: [type(e).__name__ for e in F.make_engines53(k, SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)] for k in F.CONFIGS}
    frozen = [type(e).__name__ for e in P.make_engines(SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)]
    assert names["phase36-frozen"] == frozen == ["IRFStrategy", "ORBStrategy", "PDRBodyStrategy", "PDSStrategy", "RFStrategy"]
    comb = names["phase53-author-corrected"]
    assert comb == ["IRFPhase53Strategy", "ORBStrategy", "PDRFirstEligibleStrategy", "PDSFirstEligibleStrategy", "RFStrategy"]  # ORB (no colour rule) and RF frozen
    assert all(n[4] == "RFStrategy" for n in names.values())
    assert names["phase53-var-orb-colour"][1] == "ORBColourStrategy" and all(names[k][1] == "ORBStrategy" for k in names if k != "phase53-var-orb-colour")
    assert dict(F.CONFIGS["phase53-author-corrected"].irf) == {"support_ref": "FIRST_RED_LOW", "ema_min_clearance": 28.0, "ema_scope": "ALL_METHODS", "ema_measure": "RANGE"}


def test_no_calendar_date_is_hardcoded_in_the_new_production_modules():
    for f in ("src/nifty_trading/strategies/irf_phase53.py", "src/nifty_trading/strategies/first_eligible_phase53.py", "src/nifty_trading/research/phase53.py", "src/nifty_trading/research/phase53_diag.py"):
        txt = (ROOT / f).read_text()
        assert not re.search(r"20\d\d-\d\d-\d\d", txt), f


# ======================================================================= real-data regression
@pytest.fixture(scope="module")
def real():
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    m1 = load_one_minute()
    ctxs, _ = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    base = F.signals_for(ctxs, SC, "phase36-frozen")
    return ctxs, base


def keys_of(recs, strategies=None):
    return sorted(key(r) for r in recs if strategies is None or r.strategy in strategies)


def test_real_frozen_reference_is_the_phase_36_signal_set(real):
    _, base = real
    p36 = list(csv.DictReader(open(ROOT / "reports" / "phase3" / "phase36_body_based_pdr" / "all_strategy_signals.csv", newline="")))
    assert len(p36) == sum(len(confirmed(v)) for v in base.values()) == 1083  # the Phase 3.6 table lists exactly the confirmed signals


def test_real_default_phase53_irf_engine_equals_the_frozen_engine(real):
    ctxs, base = real
    eng = IRFPhase53Strategy(proposals=SC.proposals, trade=SC.trade)
    for d, c in ctxs.items():
        assert keys_of(eng.evaluate_session(c)) == keys_of(base[d], {"IRF"})


@pytest.mark.parametrize(("cfg", "changed"), [("phase53-irf-first-red-low", {"IRF"}), ("phase53-irf-ema28", {"IRF"}), ("phase53-pdr-first-eligible", {"PDR"}), ("phase53-pds-first-eligible", {"PDS"}),
                                              ("phase53-author-corrected", {"IRF", "PDR", "PDS"}), ("phase53-var-orb-colour", {"ORB"})])
def test_real_each_configuration_changes_only_its_own_strategies(real, cfg, changed):
    ctxs, base = real
    sig = F.signals_for(ctxs, SC, cfg)
    others = {"IRF", "ORB", "PDR", "PDS", "RF"} - changed
    for d in ctxs:
        assert keys_of(sig[d], others) == keys_of(base[d], others), (cfg, d)


def test_real_every_surviving_irf_signal_in_the_ema_configuration_has_at_least_28_points_of_clearance(real):
    ctxs, _ = real
    rejections: list = []
    sig = F.signals_for(ctxs, SC, "phase53-irf-ema28", rejections)
    n = 0
    for d, recs in sig.items():
        cs = to_candles(ctxs[d].candles)
        for r in confirmed(recs, "IRF"):
            i = next(k for k, c in enumerate(cs) if c.end == r.signal_timestamp)
            e = ctxs[d].candles["ema200_5m"].iloc[i]
            if e == e:  # not NaN
                assert ema_geometry(cs[i].h, cs[i].l, cs[i].c, float(e))["range_clearance"] >= 28.0 - 1e-9, (d, r.method, hm(r.signal_timestamp))
                n += 1
    assert n > 100
    assert rejections and all(x["distance"] < 28.0 for x in rejections if x.get("ema_available"))


def test_real_the_first_red_low_configuration_matches_the_phase_52_candidate(real):
    ctxs, _ = real
    from nifty_trading.research import phase52 as F52
    a = F.signals_for(ctxs, SC, "phase53-irf-first-red-low")
    b = F52.signals_for(ctxs, SC, "phase52-cand-irf-first-red-low")
    for d in ctxs:
        assert keys_of(a[d], {"IRF"}) == keys_of(b[d], {"IRF"})


def test_real_pdr_and_pds_first_eligible_are_never_later_than_the_frozen_first_signal(real):
    ctxs, base = real
    pdr = F.signals_for(ctxs, SC, "phase53-pdr-first-eligible")
    pds = F.signals_for(ctxs, SC, "phase53-pds-first-eligible")
    for strat, sig in (("PDR", pdr), ("PDS", pds)):
        for d in ctxs:
            b = confirmed(base[d], strat)
            n = confirmed(sig[d], strat)
            if b:
                assert n and n[0].signal_timestamp <= b[0].signal_timestamp, (strat, d)


# ======================================================================= bundle (skipped before the runner has produced it)
needs_bundle = pytest.mark.skipif(not (OUT / "signal_comparison.csv").exists(), reason="Phase 5.3 bundle not generated yet")


@needs_bundle
def test_bundle_contains_every_required_deliverable():
    need = ["README.md", "approved_author_decisions.md", "rule_authority_matrix.md", "irf_first_red_low_implementation.md", "irf_ema_28_implementation.md", "pdr_first_eligible_implementation.md", "pds_first_eligible_implementation.md",
            "orb_unresolved_entries.md", "irf_day_low_unresolved.md", "source_to_code_traceability.md", "signal_comparison.csv", "dated_author_corrections.csv", "remaining_owner_decisions.md", "independent_audit.md",
            "Phase53_Author_Corrections_Verification.xlsx"]
    assert [n for n in need if not (OUT / n).exists()] == []
    assert (OUT / "daily").is_dir() and (OUT / "charts").is_dir()


@needs_bundle
def test_baselined_files_are_byte_identical_to_the_before_snapshot():
    snap = json.loads((OUT / "before_snapshot.json").read_text())["hashes"]
    bad = []
    for rel, h in snap.items():
        p = ROOT / rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append(rel)
    assert bad == [] or all(b.endswith(".DS_Store") for b in bad)
    assert os.path.exists(OUT / "before_snapshot.json")
