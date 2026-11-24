"""Phase 6.5 tests: candle-strength metrics (zero range explicit), the two newer IRF methods (rulebook worked examples, order, closes-only, cutoff, gap), the strength-gate exemptions and scope, the wrapper engine,
the independent PDR cycle audit, and invariants of the produced outputs (no valid ORB ever loses the first-valid-signal selection; counterfactuals are labelled; variant A equals configuration C)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from nifty_trading.research import phase65 as H
from nifty_trading.strategies.definitions import Candle
from nifty_trading.strategies.strength_gate import StrengthGateEngine, gate_decision

ROOT = Path(__file__).resolve().parents[1]
R65 = ROOT / "reports" / "phase6" / "phase65_author_feedback"
T0 = datetime(2025, 9, 16, 9, 15)


def mk(i, o, h, l, c):  # noqa: E741
    s = T0 + timedelta(minutes=5 * i)
    return Candle(s, s + timedelta(minutes=5), o, h, l, c, float("nan"))


# ----------------------------------------------------------------------------------------------------------------- metrics
def test_body_percentage_formula_zero_range_and_geometry():
    m = H.candle_metrics(100, 110, 90, 108)
    assert m["colour"] == "GREEN" and m["body_pct"] == 40.0 and m["upper_wick_pct"] == 10.0 and m["lower_wick_pct"] == 50.0 and m["close_location_pct"] == 90.0 and not m["zero_range"]
    z = H.candle_metrics(100, 100, 100, 100)
    assert z["zero_range"] and z["body_pct"] is None and z["upper_wick_pct"] is None and H.geometric_pattern(z, "LONG") == "ZERO_RANGE"       # never silently 0 or 100
    assert H.candle_metrics(100, 105, 95, 100)["colour"] == "DOJI"
    assert H.geometric_pattern(H.candle_metrics(100, 110, 90, 108), "LONG").startswith("HAMMER_LIKE")
    assert H.geometric_pattern(H.candle_metrics(100, 110, 99, 109), "LONG") == "STRONG_BODY"


# ----------------------------------------------------------------------------------------------------------------- new IRF Method 1
def test_new_method1_breakout_then_any_later_close_below_enters_at_that_close():
    cs = [mk(0, 25000, 25035, 24996, 25020), mk(1, 25020, 25050, 25018, 25048), mk(2, 25048, 25060, 25045, 25055), mk(3, 25055, 25056, 25025, 25030)]
    s = H.new_irf_method1(cs)
    assert s["index"] == 3 and s["entry_reference"] == 25030 and s["level_a"] == 25035 and s["breakout_time"] == "09:25" and s["within_cutoff"]        # several closes above first: the failure may come many candles later


def test_new_method1_order_wicks_and_exact_level_rules():
    below_first = [mk(0, 25000, 25035, 24996, 25020), mk(1, 25020, 25030, 25000, 25010), mk(2, 25010, 25034, 25005, 25030)]
    assert H.new_irf_method1(below_first) is None                                                       # a close below with no earlier close above is not a signal
    wick = [mk(0, 25000, 25035, 24996, 25020), mk(1, 25020, 25060, 25018, 25030), mk(2, 25030, 25031, 25010, 25012)]
    assert H.new_irf_method1(wick) is None                                                              # a wick above the level without a close above is not a breakout
    exact = [mk(0, 25000, 25035, 24996, 25020), mk(1, 25020, 25050, 25018, 25048), mk(2, 25048, 25049, 25030, 25035), mk(3, 25035, 25036, 25020, 25025)]
    assert H.new_irf_method1(exact)["index"] == 3                                                       # a close exactly on the level is ignored (TO CONFIRM)
    late = [mk(0, 25000, 25035, 24996, 25020)] + [mk(i, 25040, 25050, 25038, 25045) for i in range(1, 50)] + [mk(50, 25045, 25046, 25020, 25025)]
    assert H.new_irf_method1(late)["within_cutoff"] is False                                           # the candle ending 13:30 is after the 13:00 cutoff


def test_new_method1_missing_candle_resets_an_open_breakout():
    cs = [mk(0, 25000, 25035, 24996, 25020), mk(1, 25020, 25050, 25018, 25048), mk(3, 25040, 25041, 25020, 25025), mk(4, 25025, 25030, 25010, 25012)]   # candle 2 missing
    assert H.new_irf_method1(cs) is None


# ----------------------------------------------------------------------------------------------------------------- new IRF Method 2 (rulebook worked example: Level A 25,085, first red candle open 25,094)
def test_new_method2_rulebook_example_levels_and_sequence():
    cs = [mk(0, 25050, 25085, 25045, 25070),          # Level A = 25,085 (green first candle)
          mk(1, 25070, 25092, 25068, 25090),          # rally breakout: closes above A (green)
          mk(2, 25090, 25100, 25089, 25094),          # green rally candle
          mk(3, 25094, 25096, 25090, 25092),          # FIRST red candle: open 25,094, close 25,092 -> Level B = 25,094
          mk(4, 25092, 25110, 25091, 25105),          # second breakout: closes above B (no entry)
          mk(5, 25105, 25106, 25080, 25088)]          # failure: closes back below B -> SHORT at the close
    s = H.new_irf_method2(cs)
    assert s["level_a"] == 25085 and s["level_b"] == 25094 and s["index"] == 5 and s["entry_reference"] == 25088 and s["first_red_time"] == "09:35"


def test_new_method2_ignores_a_red_candle_before_the_breakout_and_later_red_candles_never_replace_level_b():
    cs = [mk(0, 25050, 25085, 25045, 25070), mk(1, 25070, 25080, 25040, 25060),           # second candle RED but before any close above A -> ignored
          mk(2, 25060, 25100, 25058, 25095),                                              # rally breakout
          mk(3, 25095, 25098, 25090, 25092),                                              # FIRST red in the rally: B = 25,095
          mk(4, 25092, 25130, 25090, 25128), mk(5, 25128, 25131, 25110, 25112),          # later red candle (open 25,128) must NOT replace B; 25,128 close is above B = second breakout
          mk(6, 25112, 25115, 25090, 25092)]                                              # closes below 25,095 -> failure
    s = H.new_irf_method2(cs)
    assert s["level_b"] == 25095 and s["index"] == 6


def test_new_method2_requires_every_step_in_order():
    no_second = [mk(0, 25050, 25085, 25045, 25070), mk(1, 25070, 25092, 25068, 25090), mk(2, 25090, 25096, 25085, 25088), mk(3, 25088, 25089, 25070, 25075)]    # red candle sets B=25090; never closes above B; falls
    assert H.new_irf_method2(no_second) is None                                                         # a close below B with no earlier close above B is not a signal
    no_red = [mk(0, 25050, 25085, 25045, 25070), mk(1, 25070, 25092, 25068, 25090), mk(2, 25090, 25110, 25089, 25108), mk(3, 25108, 25130, 25107, 25128)]
    assert H.new_irf_method2(no_red) is None
    variant = [mk(0, 25050, 25085, 25045, 25070), mk(1, 25095, 25100, 25080, 25090),               # breakout candle is itself RED (open 25,095)
               mk(2, 25090, 25110, 25089, 25108), mk(3, 25108, 25109, 25070, 25080)]
    assert H.new_irf_method2(variant) is None                                                           # default convention: the breakout candle is not 'in the rally'
    assert H.new_irf_method2(variant, breakout_candle_may_be_first_red=True)["level_b"] == 25095


# ----------------------------------------------------------------------------------------------------------------- strength gate
def rec(strategy, method, direction, **lv):
    return SimpleNamespace(strategy=strategy, method=method, direction=direction, reference_levels=lv)


WEAK_RED = H.candle_metrics(100, 110, 95, 98)          # body 3/15 = 20 %
STRONG_RED = H.candle_metrics(110, 111, 99, 100)       # body 10/12 = 83 %
MID_RED = H.candle_metrics(110, 111, 96, 100)          # body 10/15 = 66.7 %


def test_gate_variants_b_c_apply_only_to_directional_body_candles_and_respect_the_thresholds():
    assert gate_decision("A", rec("IRF", "Method 2B", "SHORT"), WEAK_RED)[:2] == (False, True)
    assert gate_decision("B", rec("IRF", "Method 2B", "SHORT"), WEAK_RED)[:2] == (True, False)
    assert gate_decision("B", rec("IRF", "Method 2B", "SHORT"), MID_RED)[:2] == (True, True) and gate_decision("C", rec("IRF", "Method 2B", "SHORT"), MID_RED)[:2] == (True, False)
    assert gate_decision("C", rec("IRF", "Method 2B", "SHORT"), STRONG_RED)[:2] == (True, True)
    green = H.candle_metrics(100, 111, 99, 101)
    assert gate_decision("B", rec("IRF", "Method 2B", "SHORT"), green)[:2] == (False, True)          # colour against the direction: not a directional-body confirmation, not gated


def test_hammer_shooting_star_rejection_and_the_irf_method3_sweep_are_never_rejected_for_a_small_body():
    assert gate_decision("B", rec("IRF", "Method 3", "SHORT"), WEAK_RED)[:2] == (False, True)        # its 60-70% is the UPPER-WICK share, not a body rule
    assert gate_decision("C", rec("PDR", "PDR", "LONG", patterns_passed=["LOWER_PRICE_REJECTION"]), H.candle_metrics(100, 101, 90, 100.5))[:2] == (False, True)
    assert gate_decision("B", rec("PDR", "PDR", "LONG", patterns_passed=["GOOD_GREEN_BODY"]), H.candle_metrics(100, 112, 99, 103))[:2] == (True, False)
    assert gate_decision("B", rec("PDS", "Method 2", "SHORT"), WEAK_RED)[:2] == (False, True) and gate_decision("B", rec("PDS", "Method 3", "SHORT"), WEAK_RED)[:2] == (False, True)
    assert gate_decision("B", rec("ORB", "ORB-V2", "SHORT", patterns_matched="pin_bar"), WEAK_RED)[:2] == (False, True)
    assert gate_decision("B", rec("ORB", "ORB-V2", "SHORT", patterns_matched="engulfing+full_body"), WEAK_RED)[:2] == (False, True)


def test_variant_d_is_pattern_aware_and_touches_only_methods_whose_source_calls_for_a_strong_body():
    assert gate_decision("D", rec("PDS", "Method 1", "SHORT"), WEAK_RED)[:2] == (True, False)         # 'good red candle'
    assert gate_decision("D", rec("PDS", "Method 1", "SHORT"), STRONG_RED)[:2] == (True, True)
    for s, mth in (("IRF", "Method 2B"), ("PDR", "PDR"), ("RF", "RF"), ("IRF", "Method 1")):
        assert gate_decision("D", rec(s, mth, "SHORT" if s == "IRF" else "LONG"), WEAK_RED)[:2] == (False, True)
    assert gate_decision("D", rec("ORB", "ORB-V2", "SHORT", patterns_matched="full_body"), STRONG_RED)[:2] == (True, True)      # a full-body ORB candle always has body >= 80%


def test_zero_range_candle_fails_the_gate_where_it_applies_and_is_logged():
    z = H.candle_metrics(100, 100, 100, 100)
    assert gate_decision("B", rec("RF", "RF", "SHORT"), z)[:2] == (False, True)        # a doji / zero-range candle is not a directional-body candle under B/C: the gate does not apply
    assert gate_decision("D", rec("PDS", "Method 1", "SHORT"), z)[:2] == (True, False) and "zero-range" in gate_decision("D", rec("PDS", "Method 1", "SHORT"), z)[2]


def test_wrapper_engine_invalidates_weak_confirmations_and_variant_a_is_neutral():
    cand = pd.DataFrame({"bar_start": [pd.Timestamp("2025-09-16 09:15")], "open": [100.0], "high": [110.0], "low": [95.0], "close": [98.0]})     # weak red candle (20% body)
    r = SimpleNamespace(strategy="IRF", method="Method 2B", direction="SHORT", signal_status="CONFIRMED", signal_candle_start=pd.Timestamp("2025-09-16 09:15"), signal_timestamp=pd.Timestamp("2025-09-16 09:20"),
                        signal_date=pd.Timestamp("2025-09-16").date(), reference_levels={}, invalidation_reason=None)
    inner = SimpleNamespace(STRATEGY="IRF", evaluate_session=lambda ctx: [r])
    assert StrengthGateEngine(inner, "A").evaluate_session(SimpleNamespace(candles=cand))[0].signal_status == "CONFIRMED"
    e = StrengthGateEngine(inner, "B")
    out = e.evaluate_session(SimpleNamespace(candles=cand))
    assert out[0].signal_status == "INVALIDATED" and "BODY_STRENGTH_VARIANT_B" in out[0].invalidation_reason and e.log[0]["kept"] is False


# ----------------------------------------------------------------------------------------------------------------- PDR cycle audit
def zone_cs():
    # zone [100, 102]; candle 0 retests (range meets the zone); 1: green closing AT the ceiling (ineligible: strict); 2: green closing above (first eligible); 3: another eligible
    return [mk(0, 101, 103, 99, 100.5), mk(1, 100.5, 102.5, 100.0, 102.0), mk(2, 102.0, 104.0, 101.8, 103.5), mk(3, 103.5, 105.0, 103.0, 104.5)]


def test_pdr_audit_confirms_the_first_eligible_candle_and_explains_an_earlier_green_that_failed_the_strict_close():
    a = H.pdr_cycle_audit(zone_cs(), 100.0, 102.0, "09:15", "09:25")
    assert a["first_green_after_retest"] == "09:20" and a["first_green_closing_above_ceiling"] == "09:25" and a["first_fully_eligible"] == "09:25" and a["next_eligible_after_engine"] == "09:30"
    assert a["classification"].startswith("ENGINE_EQUALS_FIRST_ELIGIBLE") and "earlier green" in a["classification"] and a["earlier_green_failed_because"] == "closed at or below the zone ceiling"


def test_pdr_audit_flags_a_late_entry_defect_and_a_missed_candidate():
    late = H.pdr_cycle_audit(zone_cs(), 100.0, 102.0, "09:15", "09:30")
    assert late["classification"] == "DEFECT_ENGINE_NOT_FIRST_ELIGIBLE"
    missed = H.pdr_cycle_audit(zone_cs(), 100.0, 102.0, "09:15", None)
    assert missed["classification"] == "DEFECT_ENGINE_MISSED_AN_ELIGIBLE_CANDLE"


def test_pdr_audit_reports_the_retest_candle_convention_without_changing_the_selection():
    cs = [mk(0, 100.0, 105.0, 99.0, 104.0)] + zone_cs()[2:]            # the retest candle itself is green and closes above the ceiling
    a = H.pdr_cycle_audit(cs, 100.0, 102.0, "09:15", "09:25")
    assert a["retest_candle_would_qualify"] is True and "convention_note" in a and a["classification"].startswith("ENGINE_EQUALS_FIRST_ELIGIBLE")


# ----------------------------------------------------------------------------------------------------------------- output invariants
needs = pytest.mark.skipif(not (R65 / "phase65_state.json").exists(), reason="Phase 6.5 outputs not generated")


@needs
def test_no_valid_orb_signal_ever_loses_to_irf_and_counterfactuals_are_labelled():
    d = pd.read_csv(R65 / "orb_vs_irf_disputed_days.csv", dtype=str, keep_default_na=False)
    assert (d.software_defect_valid_orb_not_selected == "False").all()
    valid = d[d.orb_v2_signal != "none"]
    assert len(valid) > 0 and valid.C_first_trade.str.startswith("ORB@09:20").all()                    # first valid signal wins: every valid 09:20 ORB is the first trade in C (read from the ledger)
    assert d.controller_rule.eq("first valid signal wins; no ORB/IRF priority").all()
    cf = d[d.orb_path.str.startswith("COUNTERFACTUAL")]
    assert len(cf) > 0 and cf.orb_v2_signal.eq("none").all()                                            # an invalid ORB is only ever a labelled hypothetical
    assert list((R65 / "charts_orb_vs_irf").glob("*_counterfactual.svg"))
    for f in (R65 / "charts_orb_vs_irf").glob("*_counterfactual.svg"):
        assert "COUNTERFACTUAL" in f.read_text()


@needs
def test_variant_a_equals_configuration_c_and_strength_gates_are_opt_in_research_variants():
    s = json.loads((R65 / "phase65_state.json").read_text())
    assert s["strength"]["variant_A_equals_config_C"] is True
    am = pd.read_csv(R65 / "candle_strength_authority_matrix.csv", dtype=str, keep_default_na=False)
    m3 = am[am.method.str.contains("Method 3 \\(sweep\\)")].iloc[0]
    assert "UPPER WICK" in m3.body_strength_in_source and "NOT_A_BODY_RULE" in m3.threshold_status
    assert set(am.threshold_status.str.split(" ").str[0]) <= {"DIAGNOSTIC_ONLY", "NOT_A_BODY_RULE", "SOURCE_SUPPORTED", "AUTHOR_PROPOSED", "SOURCE_SUPPORTED_REQUIREMENT,"}


@needs
def test_pdr_audit_classes_are_known_and_no_unexplained_late_entry_exists():
    a = pd.read_csv(R65 / "pdr_setup_audit.csv", dtype=str, keep_default_na=False)
    known = ("ENGINE_EQUALS_FIRST_ELIGIBLE", "NO_CONFIRMATION_IN_CYCLE")
    assert a.classification.map(lambda x: x.startswith(known)).all() and len(a) > 20          # a DEFECT_ row would fail this test
    early = a[a.classification.str.contains("earlier green")]
    assert (early.earlier_green_failed_because != "").all()                                    # the 'earlier green' label is only used when an earlier green candle really existed


def test_new_method2_gap_reset_and_cutoff_and_new_method1_cutoff_flag():
    cs = [mk(0, 25050, 25085, 25045, 25070), mk(1, 25070, 25092, 25068, 25090), mk(2, 25090, 25096, 25085, 25088), mk(4, 25088, 25120, 25087, 25118), mk(5, 25118, 25119, 25080, 25085)]    # candle 3 missing after the first red candle
    assert H.new_irf_method2(cs) is None                                                                  # a missing candle resets the open sequence
    late = [mk(0, 25050, 25085, 25045, 25070), mk(1, 25070, 25092, 25068, 25090), mk(2, 25090, 25096, 25085, 25088), mk(3, 25088, 25120, 25087, 25118)] + [mk(i, 25118, 25125, 25110, 25120) for i in range(4, 50)] + [mk(50, 25120, 25121, 25080, 25085)]
    s = H.new_irf_method2(late)
    assert s is not None and s["within_cutoff"] is False and s["level_b"] == 25090
