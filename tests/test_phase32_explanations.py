"""Phase 3.2: explainable backtest. Synthetic fixtures check the numbers and the wording of each strategy's entry explanation, the candle geometry, both exit legs,
the selection checks and the tamper detection; the delivered-output tests check the daily journals, the workbook, the source-bar traceability and that the
Phase 3.0 baseline is untouched. Real-data tests read the files written by ``scripts/phase32_build.py``."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from datetime import time
from pathlib import Path

import pytest
import test_phase23_day_controller as T
from synthetic import ctx

from nifty_trading.research import phase32 as X
from nifty_trading.strategies import (
    IRFStrategy,
    ORBStrategy,
    PDRStrategy,
    PDSStrategy,
    ProposalConfig,
    RFStrategy,
)
from nifty_trading.strategies.definitions import Candle, to_candles
from nifty_trading.strategies.params import TradeConfig
from nifty_trading.strategies.rules import RULE_BY_ID
from nifty_trading.strategies.trading_day import DayRules, run_trading_day

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase32"
P31 = ROOT / "reports" / "phase3" / "phase31"
BASE = ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE", pdr_zone_method="B_SWING_HIGH_REVERSAL", max_signals_per_session=99)
IR = (95, 100, 90, 98)  # IRH 100 / IRL 90


def candle(o, h, low, c, ema=float("nan")):
    return Candle(T.at("09:15"), T.at("09:20"), o, h, low, c, ema)


def explain_all(engine_cls, c, over=None, props=BASE, trade=None, rules=None):
    trade = trade or TradeConfig()
    recs = engine_cls(proposals=props, trade=trade).evaluate_session(c)
    bars = T.bars(over)
    res = run_trading_day(c.date, recs, bars, trade, rules or DayRules())
    inp = X.DayInputs(c.date, c, to_candles(c.candles), recs, res, bars, props, trade)
    return [(tr, X.explain_trade(c.date, tr, inp), inp) for tr in res.trades]


def by_rule(ex, rule_id, group=None):
    return [c for c in ex.checks if c.rule_id == rule_id and (group is None or c.group == group)]


# ======================================================================= candle geometry
@pytest.mark.rules("CANDLE-DEF-001", "ORB-CANDLE-001")
def test_the_strong_bullish_example_of_the_brief_is_reproduced_exactly():
    m = X.candle_metrics(candle(25000, 25050, 24995, 25045), BASE)
    assert m["range"] == 55 and m["body"] == 45 and m["upper_wick"] == 5 and m["lower_wick"] == 5
    assert round(m["body_pct"], 2) == 81.82 and round(m["upper_wick_pct"], 2) == 9.09 and m["direction"] == "BULLISH" and m["strong_bullish"] and not m["strong_bearish"]


@pytest.mark.rules("CANDLE-DEF-001")
def test_zero_range_candles_have_undefined_ratios_the_engine_convention_and_are_small():
    m = X.candle_metrics(candle(100, 100, 100, 100), BASE)
    assert m["zero_range"] and m["body_pct"] is None and m["upper_wick_pct"] is None and m["lower_wick_pct"] is None
    assert m["direction"] == "DOJI" and not m["strong_bullish"] and not m["strong_bearish"] and not m["bullish_pin"] and not m["bearish_pin"] and m["small_body_le_30pct"]


@pytest.mark.rules("CANDLE-DEF-001", "PDS-M2-001")
def test_bearish_pin_bar_reports_wick_to_body_ratio_and_close_location():
    c = candle(100, 112, 99, 101)  # red? no: close 101 > open 100 is bullish; use a bearish one below
    c = candle(104, 112, 99, 100)  # body 4, upper wick 8 (2.0x), close 1 above the low of a 13-range candle (7.7% from the low)
    m = X.candle_metrics(c, BASE)
    assert m["direction"] == "BEARISH" and m["upper_wick"] == 8 and m["bearish_pin_wick_to_body"] == 2.0
    assert round(m["close_position_from_low_pct"], 2) == round(100 / 13, 2) and m["bearish_pin"]
    assert not X.candle_metrics(candle(104, 107, 99, 100), BASE)["bearish_pin"]  # wick 3 < 2 x body 4


@pytest.mark.rules("CANDLE-DEF-001")
def test_the_small_candle_definition_is_the_configured_body_share_of_range():
    assert X.candle_metrics(candle(100, 110, 100, 103), BASE)["small_body_le_30pct"]  # 30%: on the boundary
    assert not X.candle_metrics(candle(100, 110, 100, 104), BASE)["small_body_le_30pct"]


# ======================================================================= IRF explanations
IR_M1 = [IR, (98, 104, 97, 103), (103, 103.5, 98, 99)]  # IRF p.6 worked example
M2A = [IR, (98, 104, 97, 103), (103, 106, 102, 105), (105, 106.5, 101, 102), (102, 105, 101.5, 104), (104, 104.2, 100.5, 100.8)]


def test_irf_method_1_entry_is_explained_with_the_real_candle_numbers():
    [(tr, ex, _)] = explain_all(IRFStrategy, ctx(IR_M1))
    assert tr.signal.method == "Method 1"
    assert not ex.mismatches and not [c for c in ex.checks if c.result == "FAIL"]
    b = by_rule(ex, "IRF-M1-001")[0]
    assert "close 103.00 is 3.00 points above IRH 100.00" in b.observed and b.result == "PASS"
    assert "range 7.00" in b.observed and "body 5.00 (71.43%)" in b.observed  # (98 -> 103; high 104, low 97)
    f = by_rule(ex, "IRF-M1-002")[0]
    assert "close 99.00" in f.observed and f.result == "PASS"
    assert "immediately following completed" in ex.setup_summary and "back inside the range" in ex.setup_summary and "100.00" in ex.setup_summary
    assert by_rule(ex, "IRF-GLOBAL-004")[0].result == "UNRESOLVED" and tr.signal.verification_status == "PROPOSAL_DEPENDENT"  # no IRF signal is ever called verified
    assert by_rule(ex, "IRF-M1-C001") == [] or by_rule(ex, "IRF-M1-C001")[0].rule_status == "CONFLICTING"


def test_irf_method_2a_explanation_names_the_support_pivot_and_the_chronology():
    [(tr, ex, _)] = explain_all(IRFStrategy, ctx(M2A))
    assert tr.signal.method == "Method 2A" and not ex.mismatches
    sup = by_rule(ex, "IRF-M2A-001")[0]
    assert "low 101.00" in sup.observed and sup.result == "PASS" and "neighbours' lows" in sup.observed
    assert by_rule(ex, "IRF-M2A-002")[0].result == "PASS" and "0.20 points below" in by_rule(ex, "IRF-M2A-002")[0].observed
    assert by_rule(ex, "IRF-M2-002")[0].result == "PASS" and by_rule(ex, "IRF-M2-003")[0].result == "PASS" and by_rule(ex, "IRF-M2-004")[0].result == "PASS"
    notes = [c for c in ex.checks if c.rule_id == "IRF-M2-006"]
    assert notes and all(c.result == "UNRESOLVED" for c in notes)  # no expiry in the source: disclosed, never passed
    roles = {r.role for r in ex.candles}
    assert {"initial_range_candle", "breakout_candle", "extension_candle", "red_candle", "support_pivot", "signal_candle"} <= roles


def test_irf_method_2b_discloses_when_the_push_is_the_trigger_candle_itself():
    m2b = [(24060.0, 24081.75, 24039.95, 24070.0), (24070.0, 24110.0, 24068.0, 24100.0), (24100.0, 24128.75, 24095.0, 24120.0), (24120.0, 24122.0, 24100.0, 24105.0),
           (24105.0, 24135.0, 24103.0, 24130.0), (24130.0, 24131.0, 24120.0, 24123.5)]
    [(tr, ex, _)] = explain_all(IRFStrategy, ctx(m2b))
    assert tr.signal.method == "Method 2B" and not ex.mismatches
    assert "24,128.75" in by_rule(ex, "IRF-M2B-001")[0].observed and by_rule(ex, "IRF-M2B-003")[0].result == "PASS"
    assert by_rule(ex, "IRF-M2B-002")[0].result == "PASS"


# ======================================================================= ORB / PDR / PDS / RF explanations
ORB_PREV = {"cands": [(23900, 24000, 23800, 23900)], "close": 23900.0, "ema_last": 23850.0}  # previous close 23900 above its EMA 23850: bullish


def test_orb_method_1_explains_level_provenance_trend_and_candle_strength():
    c0 = (24005, 24060, 24000, 24055)
    [(tr, ex, _)] = explain_all(ORBStrategy, ctx([c0, (24055, 24056, 24054, 24055)], prev=ORB_PREV, ema=23850.0))
    assert tr.signal.method == "Method 1" and not ex.mismatches
    lvl = by_rule(ex, "ORB-M1-LONG-001")[0]
    assert "previous-day high 24,000.00" in lvl.observed and "mechanical proxy" in lvl.why_it_matters and lvl.result == "PASS"
    assert "55.00 points" in by_rule(ex, "ORB-M1-LONG-002")[0].observed or "points beyond 24,000.00" in by_rule(ex, "ORB-M1-LONG-002")[0].observed
    tr_ = by_rule(ex, "ORB-TREND-001")[0]
    assert "close 23,900.00 vs EMA(200) 23,850.00" in tr_.observed and "50.00 points above" in tr_.observed and "variant A, EMA-only" in tr_.observed and tr_.result == "PASS"
    assert by_rule(ex, "TREND-SWING-001")[0].result == "NOT_APPLICABLE"  # swing structure is not part of variant A
    q = by_rule(ex, "ORB-M1-LONG-003")[0]
    assert "body >= 60% (observed 83.33%)" in q.observed and "upper wick <= 20% (observed 8.33%)" in q.observed and q.result == "PASS"
    assert "body occupied 83.33%" in ex.setup_summary and "EMA-only trend filter passed" in ex.setup_summary


def test_orb_structure_trend_variant_reports_the_actual_confirmed_swings():
    highs = [101, 103, 106, 102, 103, 104, 105, 110, 104, 105, 106, 107]
    lows = [99, 98, 100, 95, 99, 98, 100, 101, 97, 99, 100, 101]
    prev = {"cands": [(lo + 1, hi, lo, hi - 1) for hi, lo in zip(highs, lows, strict=True)], "close": 106.0, "ema_last": 90.0}  # swing highs 106 -> 110, swing lows 95 -> 97
    props = replace(BASE, trend_mode="STRUCTURE_EMA_SWING2")
    c = ctx([(110, 120, 109, 119), (119, 120, 118, 119)], prev=prev, ema=90.0)
    inp = X.DayInputs(c.date, c, to_candles(c.candles), [], None, [], props, TradeConfig())
    ex = X.Explanation("T")
    X.explain_trend(inp, ex, "LONG", ("ORB-TREND-001", "ORB-TREND-002"), "ORB")
    sw = [x for x in ex.checks if x.rule_id == "TREND-STRUCT-001"][0]
    assert sw.result == "PASS" and "SH 09:25 106.00; SH 09:50 110.00 | SL 09:30 95.00; SL 09:55 97.00" in sw.observed  # real pivot timestamps and prices
    assert sw.available_at.endswith("10:15")  # the previous session's last candle (the swings were confirmed long before that)
    assert [x for x in ex.checks if x.rule_id == "ORB-TREND-001"][0].result == "PASS"


PDR_PREV = {"cands": [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102)], "close": 102.0}


def test_pdr_explanation_shows_zone_provenance_and_states_that_the_hold_is_not_tested():
    cands = [(115, 120, 112, 118), (118, 119, 108, 109), (109, 113, 108, 112)]
    [(tr, ex, _)] = explain_all(PDRStrategy, ctx(cands, prev=PDR_PREV))
    assert tr.signal.method == "PDR" and not ex.mismatches
    z = by_rule(ex, "PDR-002")[0]
    assert "zone [105.00, 110.00]" in z.observed and "NOT the day high" not in z.observed  # the zone IS the previous day's high here
    assert "coincides with the day high" in z.observed and "engine recorded [105.00, 110.00]" in z.observed
    hold = [c for c in ex.checks if c.group == "NOTE" and c.rule_id == "PDR-007"][0]
    assert hold.result == "UNRESOLVED" and "does NOT test" in hold.required and "above the zone top" in hold.observed
    assert "does not check that the zone held" in ex.setup_summary
    assert by_rule(ex, "PDR-010")[0].result == "UNRESOLVED"  # reversal filter OFF


def test_pdr_zone_that_is_not_the_day_high_is_flagged_as_such():
    prev = {"cands": [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102), (102, 104, 101, 103), (103, 115, 102, 104),
                      (104, 106, 103, 105)], "close": 105.0}  # the absolute high 115 (idx 7) cannot be a CONFIRMED swing yet: the zone comes from the idx-2 swing high 110
    cands = [(120, 125, 118, 122), (122, 123, 108, 109), (109, 114, 108, 113)]
    [(tr, ex, _)] = explain_all(PDRStrategy, ctx(cands, prev=prev))
    z = by_rule(ex, "PDR-002")[0]
    assert tr.signal.signal_candle_start.strftime("%H:%M") == "09:25" and not ex.mismatches
    assert "zone [105.00, 110.00]" in z.observed and "the zone is NOT the day high (distance 5.00 points)" in z.observed and "absolute high 115.00" in z.observed


PDS_PREV = {"cands": [(24040, 24050, 24030, 24045), (24020, 24030, 24000, 24010), (24010, 24060, 24005, 24055)], "close": 24100.0}


def test_pds_method_1_reports_the_gap_the_zone_and_the_red_candle_numbers():
    cands = [(23950, 23960, 23940, 23945), (24010, 24015, 23960, 23965)]
    [(tr, ex, _)] = explain_all(PDSStrategy, ctx(cands, prev=PDS_PREV))
    assert tr.signal.method == "Method 1" and not ex.mismatches
    assert "gap DOWN" in by_rule(ex, "PDS-003")[0].observed and "-150.00 points" in by_rule(ex, "PDS-003")[0].observed
    z = by_rule(ex, "PDS-002")[0]
    assert "zone [24,000.00, 24,020.00]" in z.observed and z.result == "PASS"
    m1 = by_rule(ex, "PDS-M1-001")[0]
    assert "body >= 60%" in m1.calculation and m1.result == "PASS" and "the guide" in m1.why_it_matters.lower()


def test_pds_method_3_discloses_the_support_distance_and_that_the_guide_defines_no_near():
    cands = [(23950, 23960, 23940, 23945), (24010, 24012, 24004, 24006), (24006, 24008, 24000, 24005), (24005, 24010, 24003, 24009), (24009, 24010, 23980, 23985)]
    [(tr, ex, _)] = explain_all(PDSStrategy, ctx(cands, prev=PDS_PREV))
    assert tr.signal.method == "Method 3" and not ex.mismatches
    sup = [c for c in ex.checks if c.rule_id == "PDS-M3-001" and "support" in c.calculation][0]
    assert "distance below the zone floor" in sup.observed and "defines no distance" in sup.observed and sup.result == "PASS"
    assert by_rule(ex, "PDS-MISSING-001")[0].result == "UNRESOLVED"


RF_PREV = {"cands": [(24000, 24100, 23900, 24000)], "close": 24000.0, "ema_last": 23950.0}
RF_OK = [(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 24020, 23988, 24015)]


def test_rf_explanation_marks_direction_entry_and_target_as_not_source_verified():
    [(tr, ex, _)] = explain_all(RFStrategy, ctx(RF_OK, prev=RF_PREV, ema=23950.0))
    assert tr.signal.strategy == "RF" and not ex.mismatches
    assert "RF High 24,040.00, RF Low 24,000.00" in by_rule(ex, "RF-002")[0].observed
    assert "close 23,990.00 vs RF Low 24,000.00: 10.00 points below" in by_rule(ex, "RF-005")[0].observed
    for rid in ("RF-012", "RF-010", "RF-011"):
        assert by_rule(ex, rid)[0].result == "UNRESOLVED", rid
    assert "research proposal" in by_rule(ex, "RF-011")[0].observed


# ======================================================================= tamper detection: the explanation reports a disagreement, never hides it
def test_a_record_that_disagrees_with_the_recomputation_is_reported_as_a_failed_check():
    c = ctx([(24005, 24060, 24000, 24055), (24055, 24056, 24054, 24055)], prev=ORB_PREV, ema=23850.0)
    recs = ORBStrategy(proposals=BASE).evaluate_session(c)
    sig = next(r for r in recs if r.signal_status == "CONFIRMED")
    bad = replace(sig, reference_levels={**sig.reference_levels, "level_broken": 24001.0})
    bars = T.bars()
    res = run_trading_day(c.date, [bad], bars, TradeConfig(), DayRules())
    inp = X.DayInputs(c.date, c, to_candles(c.candles), [bad], res, bars, BASE, TradeConfig())
    ex = X.explain_trade(c.date, res.trades[0], inp)
    assert by_rule(ex, "ORB-M1-LONG-001")[0].result == "FAIL" and ex.mismatches


# ======================================================================= exits: both legs, ambiguity, forced exit, slippage
E = T.E


def orb_trade(over, trade=None):
    c = ctx([(24005, 24060, 24000, 24055), (24055, 24056, 24054, 24055)], prev=ORB_PREV, ema=23850.0)
    tradecfg = trade or TradeConfig()
    out = explain_all(ORBStrategy, c, over, trade=tradecfg)
    tr, ex, inp = out[0]
    legs, narrative, prog = X.explain_exits(c.date, tr, inp.bars, tradecfg)
    return tr, ex, legs, narrative, prog


def test_target_2_exits_both_legs_with_separate_pnl_and_source_bars():
    tr, _, legs, narr, _ = orb_trade({"09:30": (E, E + 27, E, E + 27), "10:00": (E, E + 60, E, E + 60)})
    assert tr.classification == "TARGET" and [lg.reason for lg in legs] == ["TARGET_1", "TARGET_2"]
    assert [lg.qty for lg in legs] == [195, 195] and legs[0].gross_pnl_rs == 27 * 195 and legs[1].gross_pnl_rs == 60 * 195
    assert sum(lg.gross_pnl_rs for lg in legs) == tr.result.pnl_rupees
    assert all(lg.source_bar is not None and lg.source_bar.ts == lg.exit_ts for lg in legs)
    assert "protective stop was set to" in narr and "entry - 6" in narr and "Target 2" in narr


def test_t1_then_the_adverse_6_point_stop_is_explained_with_the_timestamp_of_the_stop_change():
    tr, _, legs, narr, _ = orb_trade({"09:30": (E, E + 27, E, E + 27), "09:50": (E, E, E - 6, E - 6)})
    assert tr.classification == "T1_THEN_BUFFER_STOP" and legs[1].reason == "POST_T1_STOP_ENTRY_MINUS_PLUS_6"
    assert legs[1].exit_price == E - 6 and legs[1].gross_pnl_rs == -6 * 195 and legs[0].gross_pnl_rs == 27 * 195
    assert f"{tr.result.leg1_ts:%H:%M}" in narr and "entry - 6" in narr and "no trailing" in narr


def test_original_stop_before_t1_exits_both_legs_together():
    tr, _, legs, narr, _ = orb_trade({"09:40": (E, E, E - 30, E - 30)})
    assert tr.classification == "INITIAL_FULL_STOP" and len(legs) == 2 and {lg.reason for lg in legs} == {"ORIGINAL_STOP_BEFORE_T1"}
    assert sum(lg.gross_pnl_rs for lg in legs) == -30 * 390 and "before Target 1" in narr


def test_a_stop_and_target_in_the_same_minute_is_flagged_as_ambiguous_and_resolved_adversely():
    tr, _, legs, narr, _ = orb_trade({"09:40": (E, E + 27, E - 30, E)})
    assert tr.classification == "INITIAL_FULL_STOP" and all("SAME_BAR_AMBIGUITY" in lg.flags for lg in legs)
    assert "ambiguity" in narr.lower() and "both touched in one 1-minute bar" in narr


def test_a_gap_through_the_stop_records_the_adverse_fill_and_slippage():
    tr, _, legs, narr, _ = orb_trade({"09:40": (E - 40, E - 38, E - 42, E - 40)})
    assert tr.classification == "INITIAL_FULL_STOP" and legs[0].exit_price == E - 40 and legs[1].exit_price == E - 40  # the bar opened 10 points beyond the stop at E - 30
    assert legs[0].slippage_points == 10 and "adverse slippage 10.00 points" in legs[0].trigger_text and "slippage 10.00 points" in narr


def test_the_provisional_forced_exit_is_labelled_provisional_and_uses_the_minute_open():
    tr, _, legs, narr, _ = orb_trade({"15:14": (E + 5, E + 6, E + 4, E + 5)}, TradeConfig(forced_exit_time=time(15, 14)))
    assert tr.classification == "FORCED_EXIT" and legs[-1].reason == "FORCED_EXIT_1514_OPEN_PROVISIONAL" and "PROVISIONAL_FORCED_EXIT_15_14_OPEN" in legs[-1].flags
    assert legs[-1].exit_price == E + 5 and "PROVISIONAL" in narr


# ======================================================================= selection checks on controller-level records
def selection_checks(records, over=None, rules=None):
    bars = T.bars(over)
    res = run_trading_day(T.DAY, records, bars, TradeConfig(), rules or DayRules())
    c = ctx([(100, 101, 99, 100)] * 3)
    inp = X.DayInputs(T.DAY, c, to_candles(c.candles), records, res, bars, BASE, TradeConfig())
    out = []
    for tr in res.trades:
        ex = X.Explanation(X.trade_id_of(T.DAY, tr))
        X.explain_selection(inp, tr, ex)
        out.append((tr, ex))
    return out


def test_the_first_valid_signal_wins_and_later_signals_are_listed_in_the_selection_summary():
    [(tr, ex)] = selection_checks([T.sig("ORB", "09:20", method="Method 1"), T.sig("IRF", "09:35"), T.sig("PDR", "10:05")], {"09:40": (E, E + 27, E, E + 27), "10:00": (E, E + 60, E, E + 60)})
    assert tr.signal.strategy == "ORB" and by_rule(ex, "SEL-FIRST-001")[0].result == "PASS"
    assert "earliest executable signal" in ex.selection_summary and "IRF x1" in ex.selection_summary and "PDR x1" in ex.selection_summary


def test_the_second_trade_is_explained_by_the_original_full_stop_and_a_new_pdr_signal():
    out = selection_checks([T.sig("ORB", "09:20", method="Method 1"), T.sig("PDR", "09:30"), T.sig("PDR", "10:20")], T.LONG_SL30)
    assert [t.trade_no for t, _ in out] == [1, 2]
    ex2 = out[1][1]
    assert by_rule(ex2, "DAY-SL-001")[0].result == "PASS" and by_rule(ex2, "DAY-NOREUSE-001")[0].result == "PASS" and "second trade" in ex2.selection_summary
    assert "never reused" in by_rule(ex2, "DAY-NOREUSE-001")[0].observed


def test_the_cutoff_boundary_is_exactly_13_00_for_the_fill():
    [(tr, ex)] = selection_checks([T.sig("IRF", "12:59")])  # candle ends 12:59 -> fill 12:59
    assert by_rule(ex, "ENTRY-CUTOFF-001")[0].result == "PASS"
    [(tr, ex)] = selection_checks([T.sig("IRF", "13:00")])  # fill exactly 13:00:00 is still allowed
    assert tr.fill_timestamp.time() == time(13, 0) and by_rule(ex, "ENTRY-CUTOFF-001")[0].result == "PASS"
    assert selection_checks([T.sig("IRF", "13:01")]) == []  # a 13:01 fill is rejected by the controller: no trade, so nothing to explain


def test_a_same_minute_collision_leaves_no_trade_to_explain():
    assert selection_checks([T.sig("PDR", "09:35"), T.sig("RF", "09:35")]) == []


# ======================================================================= candles / checks are causal and traceable (synthetic)
def test_every_check_uses_a_registry_rule_and_a_valid_result_and_no_candle_is_later_than_the_signal():
    for engine, c, over in ((IRFStrategy, ctx(M2A), None), (ORBStrategy, ctx([(24005, 24060, 24000, 24055), (24055, 24056, 24054, 24055)], prev=ORB_PREV, ema=23850.0), None),
                            (RFStrategy, ctx(RF_OK, prev=RF_PREV, ema=23950.0), None)):
        for tr, ex, _ in explain_all(engine, c, over):
            for ch in ex.checks:
                assert ch.result in X.RESULTS and (ch.rule_id in RULE_BY_ID or ch.rule_id.startswith("NOTE-")), ch.rule_id
            for r in ex.candles:
                if r.session == "TODAY":
                    assert r.candle.end <= tr.signal.signal_timestamp, r.role


def test_every_rule_the_engine_recorded_as_satisfied_or_unresolved_has_an_explanation_line():
    """The explanation must reflect the engine's actual decision: each rule id on the signal record is covered by a check carrying observed values."""
    cases = ((IRFStrategy, ctx(IR_M1)), (IRFStrategy, ctx(M2A)), (ORBStrategy, ctx([(24005, 24060, 24000, 24055), (24055, 24056, 24054, 24055)], prev=ORB_PREV, ema=23850.0)),
             (PDRStrategy, ctx([(115, 120, 112, 118), (118, 119, 108, 109), (109, 113, 108, 112)], prev=PDR_PREV)),
             (PDSStrategy, ctx([(23950, 23960, 23940, 23945), (24010, 24015, 23960, 23965)], prev=PDS_PREV)), (RFStrategy, ctx(RF_OK, prev=RF_PREV, ema=23950.0)))
    for engine, c in cases:
        out = explain_all(engine, c)
        assert out, engine
        for tr, ex, _ in out:
            have = {ch.rule_id for ch in ex.checks}
            missing = [r for r in tr.signal.rule_ids_satisfied + tr.signal.rule_ids_unresolved if r not in have]
            assert not missing, (tr.signal.strategy, tr.signal.method, missing)


# ======================================================================= QA hardening (independent review)
@pytest.mark.rules("CANDLE-DEF-001")
def test_upper_and_lower_wick_percentages_are_not_interchangeable():
    m = X.candle_metrics(candle(100, 110, 98, 104), BASE)  # range 12, body 4, upper wick 6, lower wick 2
    assert m["upper_wick"] == 6 and m["lower_wick"] == 2
    assert round(m["upper_wick_pct"], 2) == 50.0 and round(m["lower_wick_pct"], 2) == 16.67 and round(m["body_pct"], 2) == 33.33


def test_rule_status_and_numeric_definition_status_come_from_the_registry_not_a_constant():
    assert X.rule_status("IRF-M1-001") == "SOURCE_VERIFIED" and X.rule_status("SEL-FIRST-001") == "USER_APPROVED"
    assert X.rule_status("PDR-012") == "PROPOSED_FOR_REVIEW" and X.rule_status("ORB-MA-001") == "CONFLICTING"
    assert X.rule_status("IRF-GLOBAL-004") == "UNRESOLVED" and X.rule_status("NOTE-X") == "NOT_A_RULE"
    assert X.definition_status("IRF-M1-001") == "EXPLICIT_IN_SOURCE" and X.definition_status("ORB-M1-LONG-003").startswith("QUALITATIVE_SOURCE")
    assert X.definition_status("SEL-FIRST-001") == "USER_APPROVED" and X.definition_status("NOTE-X") == "NOT_A_REGISTRY_RULE"


def test_a_short_trade_books_positive_pnl_when_price_falls():
    [(tr, ex, inp)] = explain_all(IRFStrategy, ctx(IR_M1), {"10:00": (E, E, E - 27, E - 27), "10:40": (E, E, E - 60, E - 60)})
    legs, narr, prog = X.explain_exits(T.DAY, tr, inp.bars, TradeConfig())
    assert tr.signal.direction == "SHORT" and tr.classification == "TARGET"
    assert legs[0].gross_pnl_rs == 27 * 195 and legs[1].gross_pnl_rs == 60 * 195 and sum(g.gross_pnl_rs for g in legs) == tr.result.pnl_rupees
    assert by_rule(ex, "EXE-T1-001")[0].calculation == "Target 1 = entry +/- 27 points" and by_rule(ex, "EXE-T1-001")[0].observed == f"T1 {X.px(E - 27)}"
    assert prog["max_favourable_points"] == 60 and prog["max_adverse_points"] == 0


def test_the_cutoff_and_first_signal_checks_can_fail():
    recs = [T.sig("IRF", "13:30")]
    bars = T.bars()
    res = run_trading_day(T.DAY, recs, bars, TradeConfig(), DayRules(entry_cutoff=time(14, 0)))  # a controller with a later cutoff trades a 13:30 fill
    c = ctx([(100, 101, 99, 100)] * 3)
    inp = X.DayInputs(T.DAY, c, to_candles(c.candles), recs, res, bars, BASE, TradeConfig())
    ex = X.Explanation("T")
    X.explain_selection(inp, res.trades[0], ex)
    assert by_rule(ex, "ENTRY-CUTOFF-001")[0].result == "FAIL"  # the explanation applies the approved 13:00 rule independently of the run
    recs2 = [T.sig("ORB", "09:20", method="Method 1")]
    res2 = run_trading_day(T.DAY, recs2, bars, TradeConfig(), DayRules())
    inp2 = X.DayInputs(T.DAY, c, to_candles(c.candles), recs2 + [T.sig("IRF", "09:10")], res2, bars, BASE, TradeConfig())  # an unexplained earlier signal exists
    ex2 = X.Explanation("T2")
    X.explain_selection(inp2, res2.trades[0], ex2)
    assert by_rule(ex2, "SEL-FIRST-001")[0].result == "FAIL"


def test_the_orb_pin_bar_route_is_disclosed_with_its_numbers_and_the_fidelity_flag():
    c0 = (24060, 24060, 23990, 24055)  # bearish? no: open 24060, close 24055 (red), long lower wick 65, body 5, close 5 from the high: pin bar, not a strong candle
    [(tr, ex, _)] = explain_all(ORBStrategy, ctx([c0, (24055, 24056, 24054, 24055)], prev=ORB_PREV, ema=23850.0))
    assert tr.signal.method == "Method 1" and tr.signal.direction == "LONG"
    assert "strong-candle test FAILED" in ex.setup_summary and "PIN-BAR alternative" in ex.setup_summary and "13.00 x the body" in ex.setup_summary
    assert "against the trade direction" in ex.setup_summary  # a red candle taken long: disclosed
    assert by_rule(ex, "ORB-M1-LONG-003")[0].source_fidelity.startswith("PIN_BAR_ROUTE_USED")


def test_irf_method_2b_flags_a_single_candle_push_as_an_engine_relaxation():
    m2b = [(24060.0, 24081.75, 24039.95, 24070.0), (24070.0, 24110.0, 24068.0, 24100.0), (24100.0, 24128.75, 24095.0, 24120.0), (24120.0, 24122.0, 24100.0, 24105.0),
           (24105.0, 24135.0, 24103.0, 24130.0), (24130.0, 24131.0, 24120.0, 24123.5)]
    [(_, ex, _)] = explain_all(IRFStrategy, ctx(m2b))
    assert by_rule(ex, "IRF-M2B-002")[0].source_fidelity == "FAITHFUL_TO_SOURCE_SEQUENCE"  # the push (24,135) is a candle BEFORE the red trigger here
    assert "State of the other four engines" in ex.selection_summary


# ======================================================================= delivered outputs (written by scripts/phase32_build.py)
needs_outputs = pytest.mark.skipif(not (OUT / "automated_trades_detailed.csv").exists(), reason="run scripts/phase32_build.py first")


def rows(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


@needs_outputs
def test_phase30_baseline_is_stable_the_rerun_ledger_is_identical_and_the_frozen_files_unchanged():
    prov = json.loads((OUT / "data_provenance.json").read_text())
    assert prov["phase30_ledger_check"]["identical"] and prov["phase30_ledger_check"]["n_differences"] == 0
    frozen = json.loads((P31 / "phase30_ledger_hashes.json").read_text())["hashes"]
    for rel, h in frozen.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h, rel


@needs_outputs
def test_prior_phase_figures_are_reverified_and_nothing_is_forced_towards_190():
    prov = json.loads((OUT / "data_provenance.json").read_text())["prior_figures_reverified"]
    assert prov["manual_rows"] == 190 and prov["exact"] + prov["time_shifted"] == 84 and prov["extras"] == 129 and prov["automated_trades"] == 213 and prov["classification_equal_to_phase31"]


@needs_outputs
def test_every_trade_is_fully_explained_with_entry_exit_and_traceable_prices():
    trades, checks, legs = rows("automated_trades_detailed.csv"), rows("trade_entry_conditions.csv"), rows("trade_exits_detailed.csv")
    assert len(trades) == 213
    ids = {t["trade_id"] for t in trades}
    assert len(ids) == 213
    for t in trades:
        assert t["setup_explanation"].strip() and t["selection_explanation"].strip() and t["exit_narrative"].strip(), t["trade_id"]
        assert t["entry_source_bar_ts"] == t["fill_timestamp"] and float(t["entry_bar_open"]) == float(t["entry_price"]) and t["entry_source_partition"].endswith("candles.parquet")
        assert int(t["checks_fail"]) == 0 and not t["recomputation_mismatches"], t["trade_id"]
    by_trade: dict[str, list[dict]] = {}
    for c in checks:
        by_trade.setdefault(c["trade_id"], []).append(c)
        assert c["rule_id"] in RULE_BY_ID or c["rule_id"].startswith("NOTE-"), c["rule_id"]
        assert c["observed"].strip() and c["calculation"].strip() and c["result"] in X.RESULTS
    assert set(by_trade) == ids and all(len(v) >= 8 for v in by_trade.values())
    by_leg: dict[str, list[dict]] = {}
    for g in legs:
        by_leg.setdefault(g["trade_id"], []).append(g)
    assert set(by_leg) == ids
    for t in trades:
        lg = by_leg[t["trade_id"]]
        assert [g["leg"] for g in lg] == ["1", "2"] and all(g["quantity"] == "195" for g in lg)
        if t["resolved"] == "True":
            for g in lg:
                assert g["exit_source_bar_ts"] == g["exit_time"] and g["exit_source_partition"].endswith("candles.parquet")
            assert abs(sum(float(g["gross_pnl_rs"]) for g in lg) - float(t["gross_pnl_rs"])) < 1e-6, t["trade_id"]


@needs_outputs
def test_the_p_and_l_columns_reconcile_with_the_phase30_ledger():
    trades = {(t["date"], t["trade_no_of_day"]): t for t in rows("automated_trades_detailed.csv")}
    with open(ROOT / "reports" / "phase3" / "baseline" / "trades.csv", newline="") as f:
        for r in csv.DictReader(f):
            t = trades[(r["date"], r["trade_no"])]
            assert float(t["gross_pnl_rs"]) == pytest.approx(float(r["gross_pnl_rs"]), abs=1e-4) and t["outcome"] == r["outcome"] and t["strategy"] == r["strategy"]  # exports are rounded to 6 decimals
            assert float(t["illustrative_net_pnl_rs"]) == pytest.approx(float(r["gross_pnl_rs"]) - 500 - 0.5 * 2 * 390, abs=1e-4)


@needs_outputs
def test_candles_used_in_an_explanation_are_never_later_than_the_signal():
    trades = {t["trade_id"]: t for t in rows("automated_trades_detailed.csv")}
    for c in rows("candle_analysis.csv"):
        t = trades[c["trade_id"]]
        assert c["available_at"] == c["candle_end"]
        if c["session"] == "TODAY":
            assert c["candle_end"] <= t["signal_confirmed_at"], (c["trade_id"], c["role"])
        else:
            assert c["candle_end"][:10] < t["date"], (c["trade_id"], c["role"])


@needs_outputs
def test_every_trading_day_has_a_journal_and_every_trade_appears_in_its_day_file():
    days = rows("daily_summary.csv")
    assert len(days) == 247
    trades = rows("automated_trades_detailed.csv")
    by_day: dict[str, list[str]] = {}
    for t in trades:
        by_day.setdefault(t["date"], []).append(t["trade_id"])
    for d in days:
        p = OUT / "daily" / d["date"][:7] / f"{d['date']}.md"
        assert p.exists(), d["date"]
        text = p.read_text()
        for sec in ("## A. Trading day overview", "## B. Daily strategy signal timeline", "## C. Detailed trade journals", "## D. Manual journal comparison", "## E. Daily conclusion"):
            assert sec in text, (d["date"], sec)
        assert int(d["executed_trades"]) == len(by_day.get(d["date"], []))
        for tid in by_day.get(d["date"], []):
            assert f"### {tid}:" in text and (OUT / "charts" / f"{tid}.svg").exists()
        assert d["owner_review_status"] == ""  # never auto-approved
    assert sum(len(v) for v in by_day.values()) == 213
    assert len(list((OUT / "charts").glob("*.svg"))) == 213


@needs_outputs
def test_manual_comparison_covers_every_journal_row_and_every_extra_automated_trade():
    cmp = rows("manual_vs_automated.csv")
    man = [c for c in cmp if c["journal_row"]]
    ext = [c for c in cmp if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"]
    assert len(man) == 190 and len({c["journal_row"] for c in man}) == 190
    matched = [c for c in man if c["match_classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
    assert len(matched) + len(ext) == 213 and len(matched) + (190 - len(matched)) == 190
    assert len({c["trade_id"] for c in matched}) == len(matched)  # no automated trade used twice
    for c in man:
        assert c["manual_entry_price"] == "NOT_RECORDED" and c["explanation"].strip() and c["owner_review_status"] == ""
        if c["match_classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH") and (c["root_cause_primary"] or "UNKNOWN") == "UNKNOWN":
            assert "UNKNOWN" in c["explanation"]  # undecidable causes are stated, not guessed


@needs_outputs
def test_the_excel_workbook_equals_the_csv_files_and_leaves_review_fields_blank():
    import openpyxl
    wb = openpyxl.load_workbook(OUT / "NIFTY_Daily_Trade_Verification.xlsx")
    required = ["Dashboard", "Daily Summary", "Automated Trades", "Entry Reasons", "Exit Details", "Candle Analysis", "Strategy Signals", "Ignored Signals", "Rejected Signals", "Manual Journal",
                "Journal Comparison", "Daily Review Checklist", "Rule Definitions"]
    assert wb.sheetnames[:13] == required
    pairs = {"Daily Summary": "daily_summary.csv", "Automated Trades": "automated_trades_detailed.csv", "Entry Reasons": "trade_entry_conditions.csv", "Exit Details": "trade_exits_detailed.csv",
             "Candle Analysis": "candle_analysis.csv", "Strategy Signals": "all_strategy_signals.csv", "Ignored Signals": "ignored_signals.csv", "Rejected Signals": "rejected_signals.csv",
             "Manual Journal": "manual_journal_normalized.csv", "Journal Comparison": "manual_vs_automated.csv"}

    def norm(v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "True" if v else "False"
        if isinstance(v, (int, float)):
            return f"{float(v):.6f}"
        return str(v)

    def norm_csv(s):
        try:
            return f"{float(s):.6f}"
        except ValueError:
            return {"TRUE": "True", "FALSE": "False"}.get(s, s)
    for sheet, name in pairs.items():
        ws = wb[sheet]
        data = rows(name)
        head = [c.value for c in ws[1]]
        assert ws.max_row - 1 == len(data), sheet
        assert ws.freeze_panes and ws.auto_filter.ref, sheet
        for ri, r in enumerate(data[:400], 2):  # every row of small sheets; the first 400 of the long ones (full equality is checked in the audit script)
            for ci, h in enumerate(head, 1):
                a, b = norm(ws.cell(row=ri, column=ci).value), norm_csv(r.get(h, ""))
                assert a == b or (norm_csv(a) == b) or a.replace("TRUE", "True").replace("FALSE", "False") == b, (sheet, ri, h, a, b)
    rv = wb["Daily Review Checklist"]
    head = [c.value for c in rv[1]]
    for key in ("owner_review_status", "reviewer", "reviewed_on", "owner_comment"):
        ci = head.index(key) + 1
        assert all(rv.cell(row=ri, column=ci).value in (None, "") for ri in range(2, rv.max_row + 1)), key


@needs_outputs
def test_configuration_snapshot_records_the_approved_rules_and_the_provisional_forced_exit():
    cfg = json.loads((OUT / "configuration_snapshot.json").read_text())
    assert cfg["stops"] == {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0} and cfg["targets_1"] == 27.0
    assert cfg["targets_2"] == {"IRF": 60.0, "ORB": 60.0, "PDR": 70.0, "PDS": 70.0, "RF": 60.0} and cfg["lots"] == {"total": 6, "leg1": 3, "lot_size": 65}
    assert "PROVISIONAL" in cfg["forced_exit"] and cfg["controller"]["tie_break"] is None and cfg["matching"]["pnl_used_for_matching"] is False
    prov = json.loads((OUT / "data_provenance.json").read_text())
    assert prov["data_files_sha256"] and prov["src_sha256"] and prov["timezone"] == "Asia/Kolkata"
