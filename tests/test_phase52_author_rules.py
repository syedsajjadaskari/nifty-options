"""Phase 5.2: the author's latest clarifications. Unit tests on synthetic candles (first eligible confirmation candle for PDR and PDS, IRF first-red-candle candidates, EMA and running-low measurements, ORB
audit categories), regression tests on the real 2025-26 sessions (the frozen signals are unchanged, the approved configuration equals them, candidates change only their own strategy) and file-level tests on the
delivered bundle. No profit is computed anywhere."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path

import pytest
from synthetic import ctx

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase52 as F
from nifty_trading.research import phase52_diag as D
from nifty_trading.strategies.definitions import to_candles
from nifty_trading.strategies.irf import IRFStrategy
from nifty_trading.strategies.irf_candidates import IRFFirstRedStrategy
from nifty_trading.strategies.pds import PDSStrategy
from nifty_trading.strategies.pds_first_eligible import FLAG, PDSCoConfirmStrategy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase52_author_rules"
SC = P.combined_scenario("BODY_BASED_PHASE36")


def rows(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def key(r):
    return (r.strategy, r.method, r.direction, r.signal_status, None if r.signal_timestamp is None else r.signal_timestamp.isoformat(), r.invalidation_reason)


def confirmed(records, strategy=None):
    return sorted((r for r in records if r.signal_status == "CONFIRMED" and (strategy is None or r.strategy == strategy)), key=lambda r: r.signal_timestamp)


def hm(ts) -> str:
    return f"{ts:%H:%M}"


# ======================================================================= PDR: first eligible confirmation candle (synthetic)
PREV_PDR = {"cands": [(100, 105, 99, 104), (104, 110, 103, 108), (108, 109, 100, 101)], "close": 101.0}  # highest body high = candle 1: zone [104, 108]


def pdr_ctx(today):
    return ctx(today, prev=PREV_PDR, open_price=112.0)


def pdr(today):
    c = pdr_ctx(today)
    from nifty_trading.strategies.pdr_body import PDRBodyStrategy
    eng = PDRBodyStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    return c, eng.evaluate_session(c)


RETEST_THEN_ELIGIBLE = [(112, 113, 110, 111),  # 09:15 above the zone: no retest yet
                        (111, 111.5, 107, 108.5),  # 09:20 retest candle (red); close above the ceiling but not a pattern
                        (108.5, 109.5, 107.5, 108.0),  # 09:25 close == ceiling: not strictly above -> not eligible
                        (108.0, 112, 107.9, 111.5),  # 09:30 FIRST ELIGIBLE: green body 85%, upper wick 12%, close above the ceiling
                        (111.5, 118, 111, 117.5)]  # 09:35 later and stronger: must NOT replace the first


def test_the_first_eligible_candle_is_chosen_and_a_later_stronger_one_is_ignored():
    c, recs = pdr(RETEST_THEN_ELIGIBLE)
    conf = confirmed(recs, "PDR")
    assert hm(conf[0].signal_timestamp) == "09:35"  # candle 09:30 closes at 09:35: activated at ITS close, not later
    assert conf[0].signal_candle_close == 111.5
    d = D.pdr_setup_diagnostics(c, SC)
    assert d["first_eligible_signal_time"] == "09:35" and D.compare_with_engine(d, recs, "PDR")["verdict"] == "ENGINE_ON_FIRST_ELIGIBLE_CANDLE"
    reasons = {r["candle_start"]: r["reason_not_eligible"] for r in d["cycles"][0]["candidates"]}
    assert "CLOSE_NOT_ABOVE_CEILING" in reasons["09:25"] and "RETEST_CANDLE" in reasons["09:20"]
    assert d["zone_floor"] == 104 and d["zone_ceiling"] == 108 and d["open_strictly_above_ceiling"] and d["first_zone_touch_candle_start"] == "09:20"


def test_a_candle_that_would_qualify_before_the_retest_is_not_an_entry():
    today = [(112, 120, 111.5, 119), (119, 121, 118.5, 120.5)] + RETEST_THEN_ELIGIBLE[1:]  # two strong green candles far above the zone first: no retest has happened
    c, recs = pdr(today)
    conf = confirmed(recs, "PDR")
    assert conf and hm(conf[0].signal_timestamp) == "09:40"  # never at 09:20 / 09:25 (the strong candles before the retest) or on the retest candle itself
    d = D.pdr_setup_diagnostics(c, SC)
    assert d["first_zone_touch_candle_start"] == "09:25" and d["first_eligible_signal_time"] == "09:40"


def test_the_retest_candle_itself_is_not_a_confirmation_by_the_preserved_convention_and_is_labelled():
    today = [(112, 113, 110, 111), (107, 112, 106.5, 111),  # 09:20 retest candle that ITSELF qualifies (green 73%, upper wick 18%, close above)
             (111, 112.5, 110.8, 112.2)]  # 09:25 qualifies too: the first eligible CONFIRMATION candle
    c, recs = pdr(today)
    conf = confirmed(recs, "PDR")
    assert hm(conf[0].signal_timestamp) == "09:30"  # the candle after the retest candle, not the retest candle (09:25)
    d = D.pdr_setup_diagnostics(c, SC)
    assert d["cycles"][0]["interaction_candle_would_qualify"] is True and "PDR-A07" in d["interaction_convention"]


def test_no_setup_without_an_open_strictly_above_the_zone_ceiling():
    c = ctx(RETEST_THEN_ELIGIBLE, prev=PREV_PDR, open_price=108.0)  # open == ceiling
    from nifty_trading.strategies.pdr_body import PDRBodyStrategy
    recs = PDRBodyStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision).evaluate_session(c)
    assert not confirmed(recs) and recs[0].invalidation_reason == "OPEN_NOT_STRICTLY_ABOVE_ZONE"
    assert D.pdr_setup_diagnostics(c, SC)["status"] == "NOT_ARMED_OPEN_NOT_STRICTLY_ABOVE_ZONE"


def test_several_pdr_patterns_on_one_candle_give_one_signal_and_all_are_recorded():
    today = [(112, 113, 110, 111), (111, 111.5, 107, 108.5),
             (107.2, 112, 105.0, 111.9)]  # green body, lower wick 2.2 >= 2 x body? body 4.7, wick 2.2: no; use a hammer-like shape instead below
    today[2] = (110.0, 111.0, 104.0, 110.8)  # lower wick 6.0 >= 2x body 0.8, close in the top of the range, tiny upper wick: rejection AND hammer
    c, recs = pdr(today)
    conf = confirmed(recs, "PDR")
    assert len(conf) == 1 and set(conf[0].reference_levels["patterns_passed"]) >= {"LOWER_PRICE_REJECTION", "HAMMER"}


def test_pdr_signals_use_only_closed_candles_prefix_equals_full_run():
    from nifty_trading.strategies.pdr_body import PDRBodyStrategy
    eng = PDRBodyStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    full = ctx(RETEST_THEN_ELIGIBLE, prev=PREV_PDR, open_price=112.0)
    f = [hm(r.signal_timestamp) for r in confirmed(eng.evaluate_session(full))]
    for n in range(1, len(RETEST_THEN_ELIGIBLE) + 1):
        pre = [hm(r.signal_timestamp) for r in confirmed(eng.evaluate_session(full.prefix(n)))]
        assert pre == [t for t in f if t <= hm(full.candles["bar_end"].iloc[n - 1])][:len(pre)] and (len(pre) == 0 or pre[0] == f[0])


# ======================================================================= PDS: first eligible confirmation, Method 3 sequencing
PREV_PDS = {"cands": [(100, 102, 96, 101), (101, 101.5, 95, 100), (100, 100.5, 96, 99.5)], "close": 99.0}  # lowest low = candle 1 (95): zone [95, 101]


def pds(today):
    c = ctx(today, prev=PREV_PDS, open_price=90.0)
    eng = PDSStrategy(proposals=SC.proposals, trade=SC.trade)
    return c, eng.evaluate_session(c)


def test_pds_method_1_activates_on_the_first_red_candle_at_the_zone_and_does_not_wait_for_another():
    today = [(90, 92, 89, 91), (91, 96, 90.5, 95.5),  # 09:20 first touch (green)
             (95.5, 97, 92, 92.5),  # 09:25 first RED candle at the zone: body 3 of 5 = 60%, lower wick 10% -> strong: Method 1
             (92.5, 99, 91, 91.2)]  # a later strong red candle: ignored
    c, recs = pds(today)
    conf = confirmed(recs, "PDS")
    assert [r.method for r in conf][:1] == ["Method 1"] and hm(conf[0].signal_timestamp) == "09:30"
    d = D.pds_setup_diagnostics(c, SC)
    assert d["first_eligible_method"] == "Method 1" and d["first_eligible_signal_time"] == "09:30" and D.compare_with_engine(d, recs, "PDS")["verdict"] == "ENGINE_ON_FIRST_ELIGIBLE_CANDLE"


def test_pds_method_3_never_enters_on_the_weak_first_candle_and_takes_the_earliest_support_break():
    today = [(90, 92, 89, 91), (91, 96, 90.5, 95.5),
             (97, 98, 95.2, 96.5),  # 09:25 first red candle at the zone but WEAK (body 18%): not taken (quality rule); Method 3 path
             (96.5, 96.8, 94.5, 95.0),  # 09:30 low 94.5
             (95.0, 96.0, 94.8, 95.8),  # 09:35 low 94.8 -> candle 09:30 is a pivot low (small support 94.5), confirmed once 09:35 has closed
             (95.8, 96.0, 93.0, 93.5),  # 09:40 closes 93.5 < 94.5: the EARLIEST completed candle satisfying the break -> Method 3
             (93.5, 94.0, 92.0, 92.5)]  # a later break: not preferred
    c, recs = pds(today)
    conf = confirmed(recs, "PDS")
    assert [r.method for r in conf][:1] == ["Method 3"] and hm(conf[0].signal_timestamp) == "09:45"
    assert all(hm(r.signal_timestamp) != "09:30" for r in conf)  # not on the weak candle (09:25 closes at 09:30)
    d = D.pds_setup_diagnostics(c, SC)
    assert d["first_eligible_method"] == "Method 3" and any(r.get("role") == "FIRST_RED_CANDLE_AT_ZONE" and r.get("outcome", "").startswith("WEAK") for r in d["candidates"])


def test_no_pds_entry_before_the_zone_is_retested_from_below():
    today = [(90, 92, 80, 81), (81, 84, 79, 80)]  # falls away from the zone, never retests it
    c, recs = pds(today)
    assert not confirmed(recs, "PDS") and D.pds_setup_diagnostics(c, SC)["status"] == "ARMED_NO_ZONE_RETEST"


def test_pds_co_confirmation_is_recorded_without_creating_a_second_signal(monkeypatch):
    today = [(90, 92, 89, 91), (91, 96, 90.5, 95.5), (95.5, 97, 92, 92.5)]
    c = ctx(today, prev=PREV_PDS, open_price=90.0)
    base = PDSStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)
    co = PDSCoConfirmStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)
    assert [key(r) for r in base] == [key(r) for r in co] and not any(r.concurrent_methods for r in co)  # strong candle and pin bar are mutually exclusive with the current thresholds
    import nifty_trading.strategies.pds_first_eligible as mod
    monkeypatch.setattr(mod, "bearish_pin", lambda c_, p_: True)  # force the second method to apply to prove the recording path
    forced = PDSCoConfirmStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)
    m1 = [r for r in forced if r.signal_status == "CONFIRMED" and r.method == "Method 1"]
    assert len(m1) == 1 and m1[0].concurrent_methods == ["Method 2"] and FLAG in m1[0].flags and len(confirmed(forced, "PDS")) == len(confirmed(base, "PDS"))


# ======================================================================= IRF: first red candle candidates (synthetic)
IRF_DAY = [(100, 110, 99, 105),  # IRH 110
           (105, 115, 104, 114),  # breakout close 114 > 110
           (114, 118, 113, 117),  # extension (high 118 > 115)
           (117, 118.5, 111, 112),  # FIRST RED candle after the extension: low 111, body low 112
           (112, 114, 110.5, 111.5),  # red: closes 111.5 < body low 112 (breaks BODY_LOW) but above low 111
           (111.5, 113, 109, 110.8),  # closes 110.8 < 111 (breaks LOW)
           (110.8, 111.2, 108, 108.5)]  # a later red candle


def irf(support_ref, today=IRF_DAY):
    c = ctx(today)
    return confirmed(IRFFirstRedStrategy(proposals=SC.proposals, trade=SC.trade, support_ref=support_ref).evaluate_session(c), "IRF")


def test_first_red_candle_candidates_use_that_candle_and_never_a_later_one():
    low = [r for r in irf("FIRST_RED_LOW") if r.method == "Method 2A"]
    body = [r for r in irf("FIRST_RED_BODY_LOW") if r.method == "Method 2A"]
    assert hm(low[0].signal_timestamp) == "09:45" and low[0].reference_levels["recent_support"] == 111 and low[0].reference_levels["support_candle_index"] == 3 and low[0].reference_levels["red_candle_index"] == 3
    assert hm(body[0].signal_timestamp) == "09:40" and body[0].reference_levels["recent_support"] == 112 and body[0].reference_levels["support_candle_index"] == 3  # the same reference candle, a different level definition
    assert body[0].reference_levels["support_ref"] == "BODY_LOW" or body[0].reference_levels["support_ref"] == "FIRST_RED_BODY_LOW"
    assert all(r.reference_levels["support_candle_index"] == 3 for r in low + body)  # the reference candle is never replaced by the later red candles


def test_baseline_mode_of_the_candidate_engine_is_the_frozen_engine_on_synthetic_candles_and_scope_is_2a_only():
    c = ctx(IRF_DAY)
    base = [key(r) for r in IRFStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c)]
    same = [key(r) for r in IRFFirstRedStrategy(proposals=SC.proposals, trade=SC.trade, support_ref="BASELINE_SWING").evaluate_session(c)]
    assert base == same
    cand = IRFFirstRedStrategy(proposals=SC.proposals, trade=SC.trade, support_ref="FIRST_RED_LOW").evaluate_session(c)
    other = lambda rs: [key(r) for r in rs if r.signal_status == "CONFIRMED" and r.method in ("Method 1", "Method 3")]  # noqa: E731
    assert other(cand) == other(IRFStrategy(proposals=SC.proposals, trade=SC.trade).evaluate_session(c))  # Method 1 and Method 3 are history-independent and untouched
    with pytest.raises(ValueError):
        IRFFirstRedStrategy(proposals=SC.proposals, trade=SC.trade, support_ref="MADE_UP")


# ======================================================================= IRF: EMA distance and running low (synthetic)
def test_ema_measurements_and_the_ema_between_entry_and_target_1():
    cands = [(100, 110, 99, 105), (105, 108, 96, 100)]
    c = ctx(cands, ema=[80.0, 80.0])
    cs = to_candles(c.candles)
    m = D.irf_measurements(c, cs, cs[1].end, fill_open=99.0)
    assert m["ema200"] == 80.0 and m["close_minus_ema"] == 20.0 and m["entry_minus_ema"] == 19.0 and m["t1_level"] == 72.0 and m["ema_between_entry_and_t1"] is True and m["ema_minus_t1"] == 8.0
    assert m["E1_close_gap_below_ema_28"] and m["E2_entry_gap_below_ema_28"] and m["E1_27"] and not m["E1_between_27_and_28"]
    far = D.irf_measurements(ctx(cands, ema=[60.0, 60.0]), cs, cs[1].end, 99.0)
    assert far["ema_between_entry_and_t1"] is False and not far["E1_close_gap_below_ema_28"]
    c2 = ctx([(100, 110, 99, 105), (105, 108, 96, 107.5)], ema=[80.0, 80.0])
    edge = D.irf_measurements(c2, to_candles(c2.candles), to_candles(c2.candles)[1].end, fill_open=107.5)
    assert edge["close_minus_ema"] == 27.5 and edge["E1_between_27_and_28"] and not edge["E1_27"] and edge["E1_close_gap_below_ema_28"]  # 27 and 28 differ here: the alternative readings are not interchangeable
    nan = D.irf_measurements(ctx(cands), cs, cs[1].end, 99.0)
    assert nan["ema200"] is None and "close_minus_ema" not in nan  # EMA not available: no value is invented


def test_running_low_uses_only_candles_closed_before_the_decision_and_never_the_final_daily_low():
    cands = [(100, 110, 99, 105), (105, 108, 96, 100), (100, 101, 90, 91), (91, 92, 50, 51)]  # the day's FINAL low (50) is made after the first signal
    c = ctx(cands)
    cs = to_candles(c.candles)
    m = D.irf_measurements(c, cs, cs[1].end, fill_open=99.5)
    assert m["running_low_before_signal_candle"] == 99 and m["running_low_including_signal_candle"] == 96 and m["n_closed_candles_used"] == 2
    assert not m["D1_entry_at_or_below_running_low"] and not m["D2_close_below_running_low_before"]
    later = D.irf_measurements(c, cs, cs[2].end, fill_open=91.0)
    assert later["running_low_before_signal_candle"] == 96 and later["D2_close_below_running_low_before"] and later["D1_entry_at_or_below_running_low"] and later["D4_t1_beyond_running_low"]
    other = D.irf_measurements(ctx(cands[:3]), to_candles(ctx(cands[:3]).candles), cs[2].end, 91.0)
    assert other["running_low_before_signal_candle"] == later["running_low_before_signal_candle"]  # dropping the future candles changes nothing: no look-ahead


def test_day_low_readings_d6_d7_d8_use_only_closed_candles():
    cands = [(100, 110, 99, 105), (105, 106, 95, 96), (96, 97, 94, 95), (95, 96, 80, 81)]  # IRL = 99; the 2nd candle closes below it
    prev = [(120, 130, 100.5, 125)]
    c = ctx(cands, prev={"cands": prev, "close": 125})
    cs = to_candles(c.candles)
    m = D.irf_measurements(c, cs, cs[2].end, fill_open=94.0)
    assert m["irl"] == 99 and m["D6_running_low_already_below_irl"] and m["D7_earlier_close_below_irl"] and m["D8_entry_below_previous_day_low"]
    early = D.irf_measurements(c, cs, cs[1].end, fill_open=105.0)
    assert not early["D6_running_low_already_below_irl"] and not early["D7_earlier_close_below_irl"] and not early["D8_entry_below_previous_day_low"]  # the candle being decided is not yet 'earlier'


def test_candidate_class_defaults_to_the_frozen_behaviour():
    from nifty_trading.strategies.irf_candidates import IRFFirstRedStrategy
    assert IRFFirstRedStrategy(proposals=SC.proposals, trade=SC.trade).support_ref == "BASELINE_SWING"


# ======================================================================= ORB audit categories
def test_orb_cause_categories_follow_the_first_failing_rule():
    def row(colour, ff):
        return {"first_candle": {"colour": colour}, "directions": {"LONG": {"first_failing_rule": ff}, "SHORT": {"first_failing_rule": ff}}}
    assert D.orb_cause_category(row("GREEN", {"Method 1": "NO_SETUP: first candle did not break and close beyond the previous-day high 1", "Method 2": "TRENDLINE_NOT_SUPPORTIVE", "Gap/200DMA": "NO_SETUP: no gap"})) == "METHOD2_TRENDLINE"
    assert D.orb_cause_category(row("RED", {"Method 1": "CANDLE_QUALITY(not a strong body / wick too large)", "Method 2": "CANDLE_QUALITY", "Gap/200DMA": "NO_SETUP"})) == "STRONG_CANDLE_THRESHOLD"
    assert D.orb_cause_category(row("GREEN", {"Method 1": "TREND:EMA_PREV_SESSION_CLOSE wrong side", "Method 2": "TREND:x", "Gap/200DMA": "NO_SETUP"})) == "EMA_REQUIREMENT"
    assert D.orb_cause_category(row("GREEN", {"Method 1": "NO_SETUP: first candle did not break and close beyond the previous-day high 1", "Method 2": "NO_SETUP: x", "Gap/200DMA": "NO_SETUP"})).startswith("LEVEL_CONSTRUCTION")
    assert D.orb_cause_category(row("GREEN", {"Method 1": "CONFIRMED", "Method 2": "x", "Gap/200DMA": "y"})) == "ENGINE_SIGNAL_EXISTS"
    # Method 1 (level broken, candle too weak) outranks Method 2's trendline: the methods are taken in order
    assert D.orb_cause_category(row("GREEN", {"Method 1": "CANDLE_QUALITY(not a strong body / wick too large)", "Method 2": "TRENDLINE_NOT_SUPPORTIVE", "Gap/200DMA": "NO_SETUP"})) == "STRONG_CANDLE_THRESHOLD"


# ======================================================================= configurations
def test_configurations_are_separately_selectable_and_replace_only_their_own_slot():
    assert set(F.CONFIGS) == {"phase36-frozen", "phase52-approved", "phase52-cand-orb-colour", "phase52-cand-irf-first-red-low", "phase52-cand-irf-first-red-body-low"}
    assert F.CONFIGS["phase36-frozen"].authority == "ACTIVE_REFERENCE" and F.CONFIGS["phase52-approved"].authority == "USER_APPROVED_VERIFIED"
    assert all(F.CONFIGS[k].authority == "CANDIDATE_NOT_APPROVED" for k in F.CONFIGS if "cand" in k)
    names = {k: [type(e).__name__ for e in F.make_engines52(k, SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)] for k in F.CONFIGS}
    frozen = ["IRFStrategy", "ORBStrategy", "PDRBodyStrategy", "PDSStrategy", "RFStrategy"]
    assert names["phase36-frozen"] == frozen == [type(e).__name__ for e in P.make_engines(SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)]
    assert names["phase52-approved"] == ["IRFStrategy", "ORBStrategy", "PDRBodyStrategy", "PDSCoConfirmStrategy", "RFStrategy"]
    assert names["phase52-cand-orb-colour"] == ["IRFStrategy", "ORBColourStrategy", "PDRBodyStrategy", "PDSStrategy", "RFStrategy"]
    assert names["phase52-cand-irf-first-red-low"][0] == "IRFFirstRedStrategy" and names["phase52-cand-irf-first-red-body-low"][0] == "IRFFirstRedStrategy"
    assert all(n[4] == "RFStrategy" for n in names.values())  # RF is never replaced


def test_no_calendar_date_is_hardcoded_in_the_new_production_modules():
    for f in ("src/nifty_trading/strategies/irf_candidates.py", "src/nifty_trading/strategies/pds_first_eligible.py", "src/nifty_trading/research/phase52.py", "src/nifty_trading/research/phase52_diag.py"):
        assert not re.search(r"20[12]\d-\d\d-\d\d|date\(20[12]\d", (ROOT / f).read_text()), f


# ======================================================================= regression on the real sessions
@pytest.fixture(scope="module")
def real():
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    m1 = load_one_minute()
    ctxs, _infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    return ctxs


@pytest.fixture(scope="module")
def frozen_signals(real):
    return F.signals_for(real, SC, "phase36-frozen")


def test_the_frozen_configuration_reproduces_the_phase_36_confirmed_signals(real, frozen_signals):
    ref = {(s["date"], s["strategy"], s["method"], s["direction"], s["time"]) for s in rows(ROOT / "reports/phase3/phase36_body_based_pdr/all_strategy_signals.csv")}
    got = {(str(d), r.strategy, r.method, r.direction, hm(r.signal_timestamp)) for d, rs in frozen_signals.items() for r in confirmed(rs)}
    assert got == ref and len(got) > 1000


def test_the_approved_configuration_equals_the_frozen_signals_and_baseline_mode_irf_is_identical(real, frozen_signals):
    appr = F.signals_for(real, SC, "phase52-approved")
    assert {d: [key(r) for r in rs] for d, rs in frozen_signals.items()} == {d: [key(r) for r in rs] for d, rs in appr.items()}
    e0, e1 = IRFStrategy(proposals=SC.proposals, trade=SC.trade), IRFFirstRedStrategy(proposals=SC.proposals, trade=SC.trade, support_ref="BASELINE_SWING")
    assert all([key(r) for r in e0.evaluate_session(c)] == [key(r) for r in e1.evaluate_session(c)] for c in real.values())


def test_no_real_session_has_a_late_pdr_or_pds_entry(real, frozen_signals):
    verdicts = set()
    for d, c in real.items():
        verdicts.add(D.compare_with_engine(D.pdr_setup_diagnostics(c, SC), frozen_signals[d], "PDR")["verdict"])
        verdicts.add(D.compare_with_engine(D.pds_setup_diagnostics(c, SC), frozen_signals[d], "PDS")["verdict"])
    assert verdicts <= {"ENGINE_ON_FIRST_ELIGIBLE_CANDLE", "NO_SIGNAL_EITHER"}


def test_candidates_change_only_their_own_strategy_and_rf_never_changes(real, frozen_signals):
    for k, own in (("phase52-cand-orb-colour", "ORB"), ("phase52-cand-irf-first-red-low", "IRF"), ("phase52-cand-irf-first-red-body-low", "IRF")):
        s = F.signals_for(real, SC, k)
        for d in real:
            for strat in ("IRF", "ORB", "PDR", "PDS", "RF"):
                if strat != own:
                    assert [key(r) for r in frozen_signals[d] if r.strategy == strat] == [key(r) for r in s[d] if r.strategy == strat]


# ======================================================================= delivered bundle
needs_outputs = pytest.mark.skipif(not (OUT / "before_after_signals.csv").exists(), reason="run scripts/phase52_run.py first")


@needs_outputs
def test_before_after_rows_belong_to_candidates_only_and_the_approved_config_has_no_signal_change():
    ba = rows(OUT / "before_after_signals.csv")
    assert ba and all(r["config"].startswith("phase52-cand") or r["change"] == "ANNOTATION_ONLY" for r in ba)
    assert not [r for r in ba if r["config"] == "phase52-approved" and r["change"] in ("REMOVED", "ADDED", "TIME_SHIFTED_EARLIER", "TIME_SHIFTED_LATER")]
    assert all(r["rule_cause"] for r in ba)


@needs_outputs
def test_dated_comparison_has_one_row_per_phase51_observation_and_no_unapproved_rule_is_called_resolved():
    dc = rows(OUT / "dated_corrections_comparison.csv")
    assert len(dc) == 42 and {r["correction_id"] for r in dc} == {r["correction_id"] for r in rows(ROOT / "reports/phase5/phase51_author_corrections/all_author_corrections.csv")}
    for r in dc:
        if r["topic"] in ("IRF_FIRST_RED_CANDLE", "IRF_EMA_28", "IRF_DAY_LOW"):
            assert r["phase52_resolves"].startswith("NO")


@needs_outputs
def test_the_phase51_37_reading_disagreements_are_all_covered_by_the_first_red_comparison():
    fr = rows(OUT / "irf_first_red_comparison.csv")
    flagged = json.loads((ROOT / "reports/phase5/phase51_author_corrections/population_impact.json").read_text())["irf_flags"]["first_red_reading_differs"]["trades"]
    assert len(flagged) == 37 and set(flagged) <= {r["trade_id"] for r in fr} and len(fr) == 42


@needs_outputs
def test_irf_diagnostics_cover_every_confirmed_irf_signal_and_never_use_future_information():
    d = rows(OUT / "irf_signal_diagnostics.csv")
    allsig = [r for r in rows(OUT / "all_confirmed_signals.csv") if r["config"] == "phase36-frozen" and r["strategy"] == "IRF"]
    assert len(d) == len(allsig) and all("D2_close_below_running_low_before" in r for r in d)
    for r in d:
        if r["running_low_before_signal_candle"]:
            assert float(r["running_low_before_signal_candle"]) >= float(r["running_low_including_signal_candle"])


# ======================================================================= preservation
snap_path = OUT / "before_snapshot.json"
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE52_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE52_ALLOW_LATER_EDITS=1")


@needs_snapshot
def test_every_baseline_file_data_report_and_frozen_strategy_is_byte_identical_to_the_pre_phase52_snapshot():
    snap = json.loads(snap_path.read_text())["hashes"]
    changed = [p for p, h in snap.items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    assert changed == []
    fr = json.loads((ROOT / "reports/phase4/strategy_freeze.json").read_text())
    assert all(sha(ROOT / p) == h for p, h in fr["active_file_hashes"].items())
    assert math.isfinite(len(snap))
