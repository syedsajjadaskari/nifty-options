"""Phase 3.4: the revised PDR engine (author-approved rules). Synthetic fixtures test zone construction, the three confirmation patterns, the strict close-above-ceiling rule and causality;
file-level tests check that nothing outside the new engine changed (hash snapshot taken before Phase 3.4) and that the delivered comparison files are consistent."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from synthetic import ctx

from nifty_trading.strategies import PDRStrategy, ProposalConfig
from nifty_trading.strategies.definitions import Candle
from nifty_trading.strategies.pdr_revised import (
    PDR_REVISION_RULES,
    PROFILES,
    RULE_STATUS,
    PDRRevisedStrategy,
    PDRRevisionConfig,
    build_zone_a,
    build_zone_b,
    classify_confirmation,
    good_green_body,
    hammer,
    local_highs,
    lower_price_rejection,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase34_pdr_revision"
T0 = datetime(2026, 1, 12, 9, 15)
PROPS = ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE", max_signals_per_session=99)
PREV = {"cands": [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102)], "close": 102.0}  # day high 110 (idx 2); zone A = [105, 110]
OPEN_CANDLE, TEST_CANDLE = (115, 120, 112, 118), (118, 119, 108, 109)  # gap up above the zone, then a test that overlaps it


def mk(o, h, lo, c, start=T0):
    return Candle(start, start + timedelta(minutes=5), o, h, lo, c, float("nan"))


def cands(rows, t0=T0):
    return [mk(o, h, lo, c, t0 + timedelta(minutes=5 * k)) for k, (o, h, lo, c) in enumerate(rows)]


def run(confirm, candidate="A", **cfg):
    c = ctx([OPEN_CANDLE, TEST_CANDLE, confirm, (113, 114, 112, 113)], prev=PREV)
    eng = PDRRevisedStrategy(proposals=PROPS, revision=PDRRevisionConfig(zone_candidate={"A": "A_DAY_HIGH_ANCHORED", "B": "B_MULTIPLE_HIGH_CLUSTER"}[candidate], **cfg))
    return [r for r in eng.evaluate_session(c) if r.signal_status == "CONFIRMED"]


# ======================================================================= zones
def test_zone_a_is_anchored_to_the_previous_day_high_with_the_body_to_wick_convention():
    z = build_zone_a(cands(PREV["cands"]))
    assert (z.floor, z.ceiling, z.previous_day_high, z.members) == (105, 110, 110, (2,)) and z.kind == "DAY_HIGH_CANDLE"


def test_an_unrelated_lower_reversal_swing_never_replaces_the_previous_day_high():
    rows = [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102), (102, 107, 101, 103), (103, 104, 100, 101), (101, 102, 99, 100), (100, 101, 99, 100)]
    cs = cands(rows)
    assert build_zone_a(cs).ceiling == 110 and build_zone_b(cs, PDRRevisionConfig()).ceiling == 110  # the 107 swing with a red follower is a different (legacy) answer


MULTI = [(100, 101, 99, 100), (100, 108, 99, 100), (100, 103, 99, 101), (101, 104, 100, 102), (102, 110, 101, 103), (103, 105, 100, 101), (101, 102, 99, 100)]  # highs 108 (idx 1) and 110 (idx 4) within 5 points


def test_repeated_highs_are_connected_into_one_zone_that_keeps_the_day_high_as_its_ceiling():
    z = build_zone_b(cands(MULTI), PDRRevisionConfig())
    assert z.kind == "MULTIPLE_HIGH_CLUSTER" and z.members == (1, 4) and z.touches == 2 and z.ceiling == 110
    assert z.floor == min(max(100, 100), max(103, 102)) == 100  # lowest member body top (the idx-1 candle's body top is 100)


def test_cluster_behaviour_depends_on_touch_count_tolerance_and_separation():
    cs = cands(MULTI)
    assert build_zone_b(cs, PDRRevisionConfig(b_min_touches=3)).kind == "ISOLATED_DAY_HIGH"  # two touches are not 'multiple' when three are required
    assert build_zone_b(cs, PDRRevisionConfig(b_tolerance_points=1.0)).kind == "ISOLATED_DAY_HIGH"  # 108 is 2 points below 110
    adjacent = cands([(100, 101, 99, 100), (100, 110, 99, 100), (100, 110, 99, 101), (101, 104, 100, 102), (102, 103, 101, 102)])  # two adjacent equal highs form ONE push
    assert build_zone_b(adjacent, PDRRevisionConfig()).kind == "ISOLATED_DAY_HIGH"
    assert build_zone_b(adjacent, PDRRevisionConfig(b_min_separation_candles=1)).kind == "MULTIPLE_HIGH_CLUSTER"


def test_a_single_isolated_high_gives_the_same_zone_in_both_candidates():
    cs = cands(PREV["cands"])
    a, b = build_zone_a(cs), build_zone_b(cs, PDRRevisionConfig())
    assert b.kind == "ISOLATED_DAY_HIGH" and (a.floor, a.ceiling) == (b.floor, b.ceiling)


SHELF_SPIKE = [(100, 101, 99, 100), (100, 103, 99, 101), (101, 102, 100, 101), (101, 103.4, 100, 101), (101, 102, 100, 101), (101, 103.2, 100, 101), (101, 102, 100, 101), (101, 125, 99, 100), (100, 101, 99, 100), (100, 100.5, 99, 100)]


def test_a_narrow_shelf_below_an_isolated_higher_spike_keeps_the_spike_and_documents_the_discrepancy():
    z = build_zone_b(cands(SHELF_SPIKE), PDRRevisionConfig())
    assert z.ceiling == 125 and z.kind == "ISOLATED_DAY_HIGH" and "SPIKE_ABOVE_SHELF" in z.flags and any("shelf of" in n for n in z.notes)


def test_the_spike_handling_policy_is_an_explicit_unresolved_option_that_flags_the_contradiction():
    z = build_zone_b(cands(SHELF_SPIKE), PDRRevisionConfig(b_spike_policy="EXCLUDE_ISOLATED_SPIKE_ABOVE_SHELF"))
    assert z.ceiling < z.previous_day_high and "DAY_HIGH_EXCLUDED_BY_POLICY" in z.flags and z.kind == "SHELF_EXCLUDING_SPIKE"
    assert RULE_STATUS["PDR-A02e"] == "PROPOSED_FOR_REVIEW" and RULE_STATUS["PDR-A02"] == "AUTHOR_APPROVED"


def test_local_highs_are_non_strict_and_use_only_existing_neighbours():
    assert local_highs(cands([(1, 5, 1, 2), (1, 5, 1, 2), (1, 4, 1, 2)]), 1) == [0, 1]


# ======================================================================= the close rule (PDR-A05)
def test_a_close_strictly_above_the_zone_ceiling_confirms_with_a_good_green_body():
    [s] = run((109, 114, 108, 113))  # body 4/6 = 67%, upper wick 1/6 = 17%, close 113 > 110
    assert s.reference_levels["patterns_passed"] == ["GOOD_GREEN_BODY"] and s.reference_levels["close_minus_ceiling"] == 3 and s.signal_timestamp.strftime("%H:%M") == "09:30" and s.signal_candle_start.strftime("%H:%M") == "09:25"


@pytest.mark.parametrize("confirm,why", [((107, 110.5, 106.5, 110), "close equal to the ceiling"), ((105, 108.5, 104.5, 108), "close inside the zone"), ((100, 104.5, 99.5, 104), "close below the floor")])
def test_a_close_that_is_not_strictly_above_the_ceiling_is_rejected_even_when_a_pattern_passes(confirm, why):
    res = classify_confirmation(mk(*confirm), 105, 110, PDRRevisionConfig())
    assert res["patterns"]["GOOD_GREEN_BODY"]["passed"], why  # the shape is fine ...
    assert not res["qualifies"] and not res["close_above_ceiling"] and run(confirm) == [], why  # ... but the close rule overrides every pattern


def test_a_lower_wick_may_penetrate_the_zone_if_the_candle_closes_above_the_ceiling():
    [s] = run((111, 112, 100, 111.5))  # low 100 is below the floor 105; hammer; close 111.5 > 110
    assert "HAMMER" in s.reference_levels["patterns_passed"] and s.signal_candle_low < 105


# ======================================================================= the three patterns (PDR-A04, OR logic)
def test_a_lower_price_rejection_candle_confirms_without_being_green():
    c = (112, 113.5, 102, 111)  # bearish; lower wick 9 >= 2 x body 1; close in the top 22% of the range; low inside the zone area; upper wick 13% so it is not a hammer
    [s] = run(c)
    assert s.reference_levels["patterns_passed"] == ["LOWER_PRICE_REJECTION"] and c[3] < c[0]


def test_a_hammer_confirms_and_the_wick_orientation_is_lower_not_upper():
    assert hammer(mk(111, 112, 100, 111.5), PRESET)["passed"]
    assert not hammer(mk(111, 120, 110.8, 111.5), PRESET)["passed"]  # a long UPPER wick (inverted hammer / shooting star) is not a hammer
    assert not hammer(mk(111, 112, 100, 100.2), PRESET)["passed"]  # body at the bottom of the range


PRESET = PDRRevisionConfig().thresholds


def test_several_passing_patterns_on_one_candle_record_all_of_them_but_produce_one_signal():
    sigs = run((111, 112, 100, 111.5))  # hammer AND lower-price rejection
    assert len(sigs) == 1 and set(sigs[0].reference_levels["patterns_passed"]) >= {"LOWER_PRICE_REJECTION", "HAMMER"}


def test_zero_range_candles_pass_no_pattern_and_never_divide_by_zero():
    res = classify_confirmation(mk(112, 112, 112, 112), 105, 110, PDRRevisionConfig())
    assert not res["patterns_passed"] and not res["qualifies"] and res["close_above_ceiling"]


# ======================================================================= pattern shapes: colour, boundaries, thresholds (QA mutation review)
TH = PDRRevisionConfig().thresholds
LEN = PROFILES["EXAMPLE_LENIENT"]


def test_a_red_hammer_and_a_red_rejection_candle_are_valid_but_a_red_candle_is_never_a_good_green_body():
    assert hammer(mk(111.5, 112, 100, 111), TH)["passed"]  # bearish hammer: the author did not require green
    assert lower_price_rejection(mk(111.5, 112, 100, 111), 110, 0.0, TH)["passed"]
    red_body = mk(113, 113.5, 108, 108.3)  # body 85%, tiny upper wick, but RED
    assert not good_green_body(red_body, TH)["passed"] and good_green_body(mk(108.3, 113.5, 108, 113), TH)["passed"]


def test_the_green_body_thresholds_are_inclusive_at_the_boundary_and_limit_the_upper_wick():
    assert good_green_body(mk(102, 110, 100, 108), TH)["passed"]  # body exactly 60%, upper wick exactly 20%
    assert not good_green_body(mk(102, 110, 100, 107.9), TH)["passed"]  # body 59%
    assert not good_green_body(mk(100, 110, 100, 107), TH)["passed"]  # body 70% but upper wick 30%
    assert not good_green_body(mk(100, 110, 100, 107), LEN)["passed"]  # ... also over the lenient 25% limit


def test_the_rejection_candle_needs_the_low_to_reach_the_zone_and_the_close_in_the_top_part():
    c = mk(113, 113.5, 111, 113.2)  # wick 2 >= 2 x body 0.2, close near the high, but the low (111) never reaches the ceiling 110
    assert not lower_price_rejection(c, 110, 0.0, TH)["passed"] and lower_price_rejection(c, 110, 1.0, TH)["passed"] and lower_price_rejection(mk(113, 113.5, 109.5, 113.2), 110, 0.0, TH)["passed"]
    weak_close = mk(105, 110.2, 100, 105.2)  # long lower wick but the close sits in the middle of the range (49% from the high)
    assert not lower_price_rejection(weak_close, 110, 0.0, TH)["passed"]


def test_the_hammer_wick_must_be_twice_the_body_by_default_and_the_lenient_profile_is_what_is_documented():
    c = mk(111, 112, 109.5, 112)  # lower wick 1.5 x the body, no upper wick, body in the upper 60% of the range
    assert not hammer(c, TH)["passed"] and hammer(c, LEN)["passed"]
    assert LEN == {"green_body_min": 0.40, "green_upper_wick_max": 0.25, "reject_wick_to_body_min": 1.5, "reject_close_fraction_max": 0.40, "hammer_wick_to_body_min": 1.5,
                   "hammer_upper_wick_max": 0.15, "hammer_body_position_min": 0.55}


def test_the_default_profile_agrees_with_the_phase_2_2_owner_proposals_in_params():
    from nifty_trading.strategies.params import PIN_BAR, STRONG_CANDLE
    assert TH["green_body_min"] == STRONG_CANDLE["MODERATE"]["body_ratio_min"] and TH["green_upper_wick_max"] == STRONG_CANDLE["MODERATE"]["opposite_wick_ratio_max"]
    assert TH["reject_wick_to_body_min"] == PIN_BAR["OWNER_2X_CLOSE30"]["wick_to_body_min"] and TH["reject_close_fraction_max"] == PIN_BAR["OWNER_2X_CLOSE30"]["close_fraction_max"]


# ======================================================================= the preserved sequence rules (PDR-A03 / A03a / A03b / A07)
def all_records(rows, prev=PREV, **cfg):
    return PDRRevisedStrategy(proposals=PROPS, revision=PDRRevisionConfig(**cfg)).evaluate_session(ctx(rows, prev=prev))


def confirmed(rows, **cfg):
    return [r for r in all_records(rows, **cfg) if r.signal_status == "CONFIRMED"]


GOOD = (109, 114, 108, 113)  # green body, close 113 > ceiling 110


def test_pdr_011_the_open_must_be_strictly_above_the_zone_ceiling_unless_the_sensitivity_option_is_chosen():
    for first in [(108, 115, 106, 114), (110, 115, 106, 114)]:  # the open is inside the zone / exactly at the ceiling
        recs = all_records([first, TEST_CANDLE, GOOD, (113, 114, 112, 113)])
        assert [r.signal_status for r in recs] == ["INVALIDATED"] and recs[0].invalidation_reason == "GAP_UP_OPEN_NOT_ABOVE_ZONE"
    assert len(confirmed([(110, 115, 106, 114), GOOD, (113, 114, 112, 113)], open_vs_zone="ANY")) == 1  # sensitivity: any open (candle 0 overlaps the zone and is the test candle)
    assert len(confirmed([OPEN_CANDLE, TEST_CANDLE, GOOD, (113, 114, 112, 113)])) == 1


def test_no_gap_up_means_no_setup_at_all_even_when_every_other_condition_holds():
    assert all_records([(101, 120, 100, 118), TEST_CANDLE, GOOD], open_vs_zone="ANY") == []  # open 101 is below the official previous close 102


def test_the_interaction_test_uses_the_whole_zone_range_inclusively():
    touch = (118, 119, 110, 111)  # low == ceiling counts as a test
    assert len(confirmed([OPEN_CANDLE, touch, GOOD, (113, 114, 112, 113)])) == 1
    near = (118, 119, 110.1, 111)  # low just above the ceiling: no test; the next candle becomes the test candle and cannot confirm itself
    assert confirmed([OPEN_CANDLE, near, GOOD, (113, 114, 112, 113)]) == []
    below = (100, 104, 99, 101)  # the whole candle lies below the floor: not an interaction with the zone
    assert confirmed([OPEN_CANDLE, below, GOOD, (113, 114, 112, 113)]) == []


def test_the_test_candle_itself_cannot_confirm_unless_that_legacy_rule_is_switched_off():
    qualifying_test_candle = (108, 114, 107, 113)  # overlaps the zone AND is a good green body closing above it
    rows = [OPEN_CANDLE, qualifying_test_candle, (113, 114, 112, 113)]
    assert confirmed(rows) == []
    assert len(confirmed(rows, confirmation_may_be_interaction_candle=True)) == 1


def test_a_data_gap_while_armed_invalidates_the_setup_and_it_does_not_confirm_across_the_gap():
    c = ctx([OPEN_CANDLE, TEST_CANDLE, (113, 114, 112, 113), GOOD], prev=PREV)
    df = c.candles.drop(index=2).reset_index(drop=True)  # the 09:25 candle is missing
    recs = PDRRevisedStrategy(proposals=PROPS).evaluate_session(replace(c, candles=df))
    assert [r.invalidation_reason for r in recs if r.signal_status == "INVALIDATED"] == ["DATA_GAP"] and not [r for r in recs if r.signal_status == "CONFIRMED"]


def test_after_a_signal_the_setup_re_arms_on_a_new_test_and_the_second_signal_has_its_own_evidence():
    rows = [OPEN_CANDLE, TEST_CANDLE, GOOD, (113, 114, 109, 111), (110, 116, 109.5, 115)]
    sigs = confirmed(rows)
    assert [s.signal_candle_start.strftime("%H:%M") for s in sigs] == ["09:25", "09:35"]
    assert len(sigs[0].reference_levels["evaluations"]) == 1 and len(sigs[1].reference_levels["evaluations"]) == 1  # the evidence list is reset after each signal


def test_equal_day_highs_anchor_the_zone_at_the_first_candle_and_the_b_lower_bound_option_is_honoured():
    tie = cands([(100, 101, 99, 100), (100, 110, 99, 103), (103, 104, 100, 102), (102, 110, 101, 108), (108, 109, 100, 101)])
    assert build_zone_a(tie).floor == 103  # first candle (body top 103), not the second (body top 108)
    z = build_zone_b(cands(MULTI), PDRRevisionConfig(b_lower_bound="DAY_HIGH_CANDLE_BODY_TOP"))
    assert z.floor == 103 and build_zone_b(cands(MULTI), PDRRevisionConfig()).floor == 100


def test_candidates_a_and_b_share_one_ceiling_so_they_cannot_produce_different_signals_under_the_preserved_open_rule():
    cs = cands(MULTI)
    assert build_zone_a(cs).ceiling == build_zone_b(cs, PDRRevisionConfig()).ceiling == 110 and build_zone_a(cs).floor != build_zone_b(cs, PDRRevisionConfig()).floor
    prev = {"cands": MULTI, "close": 101.0}
    rows = [(112, 121, 111, 120), (120, 121, 109, 111), (108, 115, 107, 114), (114, 115, 113, 114)]
    sa = [r.signal_candle_start for r in all_records(rows, prev=prev) if r.signal_status == "CONFIRMED"]
    sb = [r.signal_candle_start for r in all_records(rows, prev=prev, zone_candidate="B_MULTIPLE_HIGH_CLUSTER") if r.signal_status == "CONFIRMED"]
    assert sa == sb and sa


# ======================================================================= causality
def test_no_look_ahead_a_signal_is_available_only_when_its_candle_has_completed():
    c = ctx([OPEN_CANDLE, TEST_CANDLE, (109, 114, 108, 113), (113, 114, 112, 113)], prev=PREV)
    eng = PDRRevisedStrategy(proposals=PROPS)
    full = [r for r in eng.evaluate_session(c) if r.signal_status == "CONFIRMED"]
    assert [r.signal_candle_start.strftime("%H:%M") for r in full] == ["09:25"]
    for k in range(1, 5):
        part = [r for r in eng.evaluate_session(c.prefix(k)) if r.signal_status == "CONFIRMED"]
        assert [r.signal_timestamp for r in part] == ([full[0].signal_timestamp] if k >= 3 else [])  # no signal before the confirmation candle exists
        assert all(r.signal_timestamp == r.signal_candle_start + timedelta(minutes=5) for r in part)


def test_the_zone_uses_the_previous_session_only():
    base = run((109, 114, 108, 113))[0].reference_levels
    c = ctx([(115, 300, 112, 118), TEST_CANDLE, (109, 114, 108, 113), (113, 114, 112, 113)], prev=PREV)  # today's wild high must not move the zone
    lv = [r for r in PDRRevisedStrategy(proposals=PROPS).evaluate_session(c) if r.signal_status == "CONFIRMED"][0].reference_levels
    assert (lv["zone_floor"], lv["zone_ceiling"]) == (base["zone_floor"], base["zone_ceiling"]) == (105, 110)


def test_every_signal_records_its_configuration_candidate_and_rule_statuses():
    [s] = run((109, 114, 108, 113))
    rev = s.execution_config["pdr_revision"]
    assert rev["config_id"].startswith("PDRREV-A-RESEARCH_DEFAULT") and rev["zone_candidate"] == "A_DAY_HIGH_ANCHORED"
    assert rev["rule_status"]["PDR-A05"] == "AUTHOR_APPROVED" and rev["rule_status"]["PDR-A04a"] == "PROPOSED_FOR_REVIEW" and s.verification_status != "VERIFIED"
    assert "PDR-A04b" in s.rule_ids_unresolved and s.reference_levels["config_id"] == rev["config_id"]
    assert all(r["status"] in {"AUTHOR_APPROVED", "PROPOSED_FOR_REVIEW", "USER_APPROVED", "PRESERVED_FROM_PHASE2", "OWNER_INTERPRETATION"} for r in PDR_REVISION_RULES)


def test_the_legacy_engine_is_untouched_and_still_fires_on_any_green_candle_after_the_test():
    c = ctx([OPEN_CANDLE, TEST_CANDLE, (108, 109, 107, 108.5), (113, 114, 112, 113)], prev=PREV)  # a weak green candle that closes INSIDE the zone
    legacy = [r for r in PDRStrategy(proposals=replace(PROPS, pdr_zone_method="B_SWING_HIGH_REVERSAL")).evaluate_session(c) if r.signal_status == "CONFIRMED"]
    assert legacy and legacy[0].signal_candle_start.strftime("%H:%M") == "09:25"  # legacy rule: zone touched, then the first later green candle
    assert run((108, 109, 107, 108.5)) == []  # the revised engine rejects the same candle (close inside the zone)


# ======================================================================= nothing else changed
snap_path = OUT / "before_snapshot.json"
# One-time delivery check: it proves Phase 3.4 changed nothing but the new engine. It fails on any LATER legitimate edit of an earlier file (for example in Phase 3.5); that phase should set
# PHASE34_ALLOW_LATER_EDITS=1 (or retire these tests) rather than refresh the snapshot, which must keep describing the state before Phase 3.4.
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE34_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE34_ALLOW_LATER_EDITS=1")


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


@needs_snapshot
@pytest.mark.parametrize("prefix", ["src/nifty_trading/strategies/irf.py", "src/nifty_trading/strategies/orb.py", "src/nifty_trading/strategies/pds.py", "src/nifty_trading/strategies/rf.py",
                                    "src/nifty_trading/strategies/pdr.py", "src/nifty_trading/strategies/trading_day.py", "src/nifty_trading/strategies/selection.py", "src/nifty_trading/core/exit_policy.py",
                                    "src/nifty_trading/core/execution_eligibility.py", "src/nifty_trading/strategies/params.py", "src/nifty_trading/strategies/definitions.py", "src/nifty_trading/strategies/base.py"])
def test_other_engines_the_controller_stops_targets_and_shared_definitions_are_byte_identical_to_the_snapshot(prefix):
    snap = json.loads(snap_path.read_text())["files"]
    assert sha(prefix) == snap[prefix]


# Phase 3.5 deliberately edits the research modules (engine selection, explainer), so the broad Phase 3.4 freeze is superseded by the Phase 3.5 freeze (tests/test_phase35_combined.py)
# once reports/phase3/phase35_combined/before_snapshot.json exists. The per-engine / controller / stops hash tests below stay active.
superseded = pytest.mark.skipif((OUT.parent / "phase35_combined" / "before_snapshot.json").exists(), reason="superseded by the Phase 3.5 snapshot test")


@needs_snapshot
@superseded
def test_no_source_test_or_script_file_that_existed_before_changed_and_all_data_and_phase3_reports_are_identical():
    snap = json.loads(snap_path.read_text())["files"]
    changed = [p for p, h in snap.items() if (p.startswith(("src/", "tests/", "scripts/", "data/", "reports/phase3/", "docs/strategy_docs/", "docs/trading journal/")) and (ROOT / p).exists() and sha(p) != h)]
    assert changed == []
    missing = [p for p in snap if p.startswith(("data/processed", "reports/phase3/")) and not (ROOT / p).exists()]
    assert missing == []


@needs_snapshot
def test_stops_targets_position_size_and_the_cutoff_defaults_are_unchanged():
    from nifty_trading.core.execution_eligibility import ENTRY_CUTOFF
    from nifty_trading.strategies.params import DEFAULT_TRADE
    t = DEFAULT_TRADE
    assert (t.t1_points, t.stop_points("PDR"), t.t2_points("PDR"), t.total_lots, t.leg1_lots, t.lot_size, t.post_t1_buffer_points) == (27.0, 35.0, 70.0, 6, 3, 65, 6.0) and str(ENTRY_CUTOFF) == "13:00:00"


# ======================================================================= delivered files
needs_outputs = pytest.mark.skipif(not (OUT / "pdr_daily_signal_comparison.csv").exists(), reason="run scripts/phase34_run.py first")


def rows(n):
    with open(OUT / n, newline="") as f:
        return list(csv.DictReader(f))


@needs_outputs
def test_the_daily_comparison_covers_every_session_for_both_candidates_with_a_config_id_and_tags():
    d = rows("pdr_daily_signal_comparison.csv")
    assert len(d) == 2 * len({r["date"] for r in d}) == 494 and {r["candidate"] for r in d} == {"A", "B"}
    assert all(r["config_id"].startswith("PDRREV-") and r["change_tags"] and r["reason_for_difference"] for r in d)
    allowed = {"UNCHANGED_VALID", "UNCHANGED_INVALID", "REMOVED_BY_CLOSE_RULE", "REMOVED_BY_ZONE_SELECTION", "REMOVED_BY_PATTERN_RULE", "NEWLY_VALID_ZONE", "NEWLY_VALID_PATTERN", "UNRESOLVED_ZONE",
               "DATA_OR_IMPLEMENTATION_ISSUE", "SEQUENCE_STATE_DIFFERENCE"}
    assert {t for r in d for t in r["change_tags"].split(";")} <= allowed


@needs_outputs
def test_every_revised_signal_closes_strictly_above_its_ceiling_and_has_a_pattern_and_a_causal_fill():
    ev = [r for r in rows("pdr_entry_condition_details.csv") if r["decision"] == "SIGNAL_CONFIRMED"]
    assert ev
    for r in ev:
        assert float(r["close"]) > float(r["zone_ceiling"]) and r["patterns_passed"] and r["close_strictly_above_ceiling"] == "True"
        start = int(r["evaluated_candle_start"][:2]) * 60 + int(r["evaluated_candle_start"][3:])
        fill = int(r["synthetic_fill_timestamp"][-5:-3]) * 60 + int(r["synthetic_fill_timestamp"][-2:])
        assert r["entry_eligibility"] == "ELIGIBLE" and fill == start + 5  # fill = open of the 1-minute bar that starts when the 5-minute candle ends
    for r in rows("old_vs_new_pdr_signals.csv"):
        if r["row_type"] == "NEW_SIGNAL":
            assert float(r["close_minus_new_ceiling"]) > 0 and r["patterns_passed"] and r["config_id"].startswith("PDRREV-")


@needs_outputs
def test_all_old_signals_and_all_54_old_trades_are_compared_for_both_candidates():
    s = rows("old_vs_new_pdr_signals.csv")
    old = [r for r in s if r["row_type"] == "OLD_SIGNAL"]
    assert len(old) == 2 * 383 and len({r["old_trade_id"] for r in old if r["old_trade_id"]}) == 54
    for r in old:
        assert r["change_tags"] and r["reason"] and r["portfolio_note"]


@needs_outputs
def test_the_journal_2x2_table_covers_both_candidates_and_both_open_rules_and_a_equals_b():
    j = rows("pdr_journal_agreement_2x2.csv")
    assert len(j) == 8 and {r["candidate"] for r in j} == {"A", "B"} and all(r["journal_pdr_rows"] == "8" and "circular" in r["caveat"] for r in j)
    key = lambda r: (r["pattern_thresholds"], r["open_rule"])  # noqa: E731
    assert {key(r): (r["exact"], r["shifted_within_15_min"]) for r in j if r["candidate"] == "A"} == {key(r): (r["exact"], r["shifted_within_15_min"]) for r in j if r["candidate"] == "B"}


@needs_outputs
def test_the_session_that_was_not_evaluated_does_not_present_informational_zone_columns_as_a_result():
    ne = [r for r in rows("pdr_daily_signal_comparison.csv") if r["date"] == "2025-10-23"]
    assert len(ne) == 2 and all(r["gap_up"] == "" and r["open_above_zone_ceiling"] == "" and r["retest_condition"].startswith("NOT EVALUATED") and "DATA_OR_IMPLEMENTATION_ISSUE" in r["change_tags"] for r in ne)


def test_author_words_and_the_briefs_readings_are_separate_rule_rows():
    status = {r["rule_id"]: r["status"] for r in PDR_REVISION_RULES}
    assert status["PDR-A01"] == status["PDR-A04"] == status["PDR-A05"] == "AUTHOR_APPROVED"
    assert status["PDR-A01a"] == status["PDR-A04z"] == status["PDR-A05a"] == "OWNER_INTERPRETATION"
    assert all(status[r] == "PROPOSED_FOR_REVIEW" for r in ("PDR-A02g", "PDR-A02h", "PDR-A02i", "PDR-A03b", "PDR-A05b"))
    text = {r["rule_id"]: r["text"] for r in PDR_REVISION_RULES}
    assert "strictly" not in text["PDR-A05"].lower() and "strictly" in text["PDR-A05a"].lower()
