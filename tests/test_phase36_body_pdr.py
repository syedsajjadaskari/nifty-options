"""Phase 3.6: the body-based PDR engine (pdr_body.py). Synthetic fixtures test body-high zone construction (wicks ignored), the strictly-above-zone opening, the three confirmation alternatives,
the strict close rule, causality and the configuration labels; file-level tests check that nothing else changed (hash snapshot taken before the first Phase 3.6 edit) and that the delivered bundle is consistent."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from synthetic import ctx

from nifty_trading.strategies import PDRStrategy, ProposalConfig
from nifty_trading.strategies.definitions import Candle
from nifty_trading.strategies.pdr_body import (
    PDR_BODY_RULES,
    RULE_STATUS,
    PDRBodyConfig,
    PDRBodyStrategy,
    body_high,
    body_low,
    body_pivots,
    build_zone,
    build_zone_a,
    build_zone_b,
)
from nifty_trading.strategies.pdr_revised import PDRRevisedStrategy, classify_confirmation
from nifty_trading.strategies.pdr_revised import build_zone_a as wick_zone_a

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
T0 = datetime(2026, 1, 12, 9, 15)
PROPS = ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE", max_signals_per_session=99)
# previous session: the highest WICK is 110 (idx 2) but its body is only 101-105; body highs: 100, 101, 105, 105(idx 3 red candle opening at 105), 101, 102
PREV = {"cands": [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102)], "close": 102.0}
OPEN_CANDLE, TEST_CANDLE = (115, 120, 112, 118), (118, 119, 104, 106)  # gap up above the body ceiling 105, then a test that dips into the zone [101, 105]
GOOD = (104, 109, 103.5, 108)  # green body 73%, upper wick 18%, close 108 > 105


def mk(o, h, lo, c, start=T0):
    return Candle(start, start + timedelta(minutes=5), o, h, lo, c, float("nan"))


def cands(rows, t0=T0):
    return [mk(o, h, lo, c, t0 + timedelta(minutes=5 * k)) for k, (o, h, lo, c) in enumerate(rows)]


def records(rows, prev=PREV, **cfg):
    return PDRBodyStrategy(proposals=PROPS, revision=PDRBodyConfig(**cfg)).evaluate_session(ctx(rows, prev=prev))


def confirmed(rows, prev=PREV, **cfg):
    return [r for r in records(rows, prev, **cfg) if r.signal_status == "CONFIRMED"]


# ======================================================================= body highs and zones
def test_the_raw_wick_high_is_ignored_and_the_highest_body_high_is_the_ceiling():
    cs = cands(PREV["cands"])
    z = build_zone_a(cs)
    assert (body_high(cs[2]), body_low(cs[2])) == (105, 101)
    assert z.ceiling == 105 and z.floor == 101 and z.previous_day_wick_high == 110 and z.previous_day_body_high == 105
    assert "CEILING_BELOW_WICK_HIGH" in z.flags and z.members == (2,)  # first occurrence of the highest body high (idx 3 ties at 105)
    assert wick_zone_a(cs).ceiling == 110  # the Phase 3.4 / 3.5 engine used the wick: the two engines genuinely differ


def test_the_highest_body_high_can_belong_to_a_candle_that_does_not_have_the_highest_wick():
    rows = [(100, 101, 99, 100), (100, 120, 100, 101), (101, 108, 100, 107), (107, 109, 105, 106), (106, 107, 104, 105)]  # idx 1 has the highest wick (120) but body high 101; idx 2 has body high 107
    z = build_zone_a(cands(rows))
    assert z.ceiling == 107 and z.members == (2,) and z.previous_day_wick_high == 120


def test_an_isolated_wick_spike_above_repeated_body_highs_is_ignored_not_connected_or_flagged_as_a_body_spike():
    rows = [(100, 101, 99, 100), (100, 103, 99, 103.4), (103, 102, 100, 101), (101, 103.4, 100, 101), (101, 102, 100, 101), (101, 103.2, 100, 103.2), (103, 102, 100, 101), (101, 125, 99, 100), (100, 101, 99, 100)]
    cs = cands(rows)
    z = build_zone_b(cs, PDRBodyConfig(zone_candidate="B_MULTIPLE_BODY_HIGH_CLUSTER"))
    assert z.ceiling == 103.4 and z.previous_day_wick_high == 125 and z.kind == "MULTIPLE_BODY_HIGH_CLUSTER" and "BODY_SPIKE_ABOVE_SHELF" not in z.flags
    assert build_zone_a(cs).ceiling == 103.4  # the 125 wick never becomes the ceiling


def test_multiple_body_highs_are_connected_into_one_zone_whose_ceiling_is_the_highest_body_high():
    rows = [(100, 101, 99, 100), (100, 108, 99, 106), (101, 107, 100, 100.5), (101, 104, 100, 102), (102, 110, 101, 109), (101, 111, 100, 100.5), (101, 102, 99, 100)]  # body highs 106 (idx 1) and 109 (idx 4)
    z = build_zone_b(cands(rows), PDRBodyConfig(zone_candidate="B_MULTIPLE_BODY_HIGH_CLUSTER"))
    assert z.kind == "MULTIPLE_BODY_HIGH_CLUSTER" and z.members == (1, 4) and z.touches == 2 and z.ceiling == 109 and z.member_body_highs == (106, 109)
    assert z.floor == min(body_low(c) for c in (cands(rows)[1], cands(rows)[4])) == 100  # hull of the member bodies


def test_cluster_parameters_are_configurable_and_a_single_body_high_is_isolated():
    rows = [(100, 101, 99, 100), (100, 108, 99, 106), (101, 107, 100, 100.5), (101, 104, 100, 102), (102, 110, 101, 109), (101, 111, 100, 100.5), (101, 102, 99, 100)]
    cs = cands(rows)
    B = "B_MULTIPLE_BODY_HIGH_CLUSTER"
    assert build_zone_b(cs, PDRBodyConfig(zone_candidate=B, b_min_touches=3)).kind == "ISOLATED_BODY_HIGH"
    assert build_zone_b(cs, PDRBodyConfig(zone_candidate=B, b_tolerance_points=1.0)).kind == "ISOLATED_BODY_HIGH"  # 106 is 3 points below 109
    adjacent = cands([(100, 101, 99, 100), (100, 110, 99, 109), (109, 110, 99, 109), (101, 104, 100, 102), (102, 103, 101, 102)])  # two adjacent equal body highs are ONE push
    assert build_zone_b(adjacent, PDRBodyConfig(zone_candidate=B)).kind == "ISOLATED_BODY_HIGH"
    assert build_zone_b(adjacent, PDRBodyConfig(zone_candidate=B, b_min_separation_candles=1)).kind == "MULTIPLE_BODY_HIGH_CLUSTER"
    single = cands([(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (98, 99, 90, 95), (95, 96, 90, 92)])  # one push of body highs (idx 2-3), nothing else near it
    iso = build_zone_b(single, PDRBodyConfig(zone_candidate=B))
    a = build_zone_a(single)
    assert iso.kind == "ISOLATED_BODY_HIGH" and (iso.floor, iso.ceiling) == (a.floor, a.ceiling)


def test_a_lone_body_spike_above_a_shelf_is_kept_and_flagged_and_only_a_diagnostic_policy_drops_it():
    rows = [(100, 101, 99, 100), (100, 103, 99, 103), (103, 102, 100, 101), (101, 103.4, 100, 103.4), (103.4, 102, 100, 101), (101, 103.2, 100, 103.2), (103.2, 102, 100, 101), (101, 126, 99, 125), (125, 101, 99, 100), (100, 100.5, 99, 100)]
    cs = cands(rows)
    B = "B_MULTIPLE_BODY_HIGH_CLUSTER"
    z = build_zone_b(cs, PDRBodyConfig(zone_candidate=B))
    assert z.ceiling == 125 and z.kind == "ISOLATED_BODY_HIGH" and "BODY_SPIKE_ABOVE_SHELF" in z.flags  # a genuine highest body price is never silently discarded
    d = build_zone_b(cs, PDRBodyConfig(zone_candidate=B, b_spike_policy="EXCLUDE_ISOLATED_BODY_SPIKE_ABOVE_SHELF"))
    assert d.ceiling < d.previous_day_body_high and "HIGHEST_BODY_HIGH_EXCLUDED_BY_POLICY" in d.flags
    assert RULE_STATUS["PDR-B02e"] == "PROPOSED_FOR_REVIEW"


def test_body_pivots_are_non_strict_and_use_existing_neighbours_only():
    assert body_pivots(cands([(1, 5, 1, 4), (1, 5, 1, 4), (1, 5, 1, 3)]), 1) == [0, 1]


def test_every_zone_carries_boundaries_source_candles_body_highs_and_flags():
    z = build_zone(cands(PREV["cands"]), PDRBodyConfig())
    assert z.floor < z.ceiling and z.source_starts == (T0 + timedelta(minutes=10),) and z.member_body_highs == (105,) and z.notes and isinstance(z.flags, list)
    sig = confirmed([OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)])[0].reference_levels
    assert sig["zone_member_candle_starts"] and sig["zone_member_body_highs"] == [105] and sig["wick_ignored_points"] == 5 and sig["config_id"].startswith("PDRBODY-A-RESEARCH_DEFAULT")


# ======================================================================= zero-height zones
DOJI_PREV = {"cands": [(100, 101, 99, 100), (100, 102, 100, 101), (110, 112, 99, 110), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102)], "close": 102.0}  # the highest body high is a doji (o == c == 110)


def test_a_zero_height_zone_is_detected_and_by_default_left_unresolved_instead_of_inventing_a_width():
    z = build_zone_a(cands(DOJI_PREV["cands"]))
    assert z.zero_height and "ZERO_HEIGHT_ZONE" in z.flags and z.floor == z.ceiling == 110
    recs = records([(120, 125, 118, 123), (123, 124, 109, 111), (110, 116, 109, 115)], DOJI_PREV)
    assert [r.signal_status for r in recs] == ["INVALIDATED"] and recs[0].invalidation_reason == "ZERO_HEIGHT_ZONE_UNRESOLVED"
    line = records([(120, 125, 118, 123), (123, 124, 109, 111), (110, 116, 109, 115)], DOJI_PREV, zero_height_policy="TREAT_AS_LINE")
    assert any(r.signal_status == "CONFIRMED" for r in line)  # the sensitivity option treats it as a line


# ======================================================================= the opening requirement (AUTHOR_APPROVED)
@pytest.mark.parametrize("first,close,why", [((105, 112, 100, 108), 102.0, "open exactly at the ceiling"), ((103, 112, 100, 108), 102.0, "open inside the zone"), ((100, 112, 98, 108), 95.0, "open below the floor (still a gap up)")])
def test_an_open_at_inside_or_below_the_zone_rejects_the_setup(first, close, why):
    recs = records([first, TEST_CANDLE, GOOD, (108, 109, 107, 108)], {**PREV, "close": close})
    assert [r.signal_status for r in recs] == ["INVALIDATED"] and recs[0].invalidation_reason == "OPEN_NOT_STRICTLY_ABOVE_ZONE", why


def test_an_open_strictly_above_the_ceiling_is_accepted_even_one_tick_above():
    assert len(confirmed([(105.05, 112, 100, 108), TEST_CANDLE, GOOD, (108, 109, 107, 108)])) == 1


def test_the_open_condition_is_author_approved_and_the_open_anywhere_option_is_only_a_sensitivity():
    assert RULE_STATUS["PDR-B03"] == "AUTHOR_APPROVED" and PDRBodyConfig().open_vs_zone == "ABOVE_ZONE"
    assert len(confirmed([(103, 112, 100, 108), GOOD, (108, 109, 107, 108)], open_vs_zone="ANY")) == 1


def test_no_gap_up_means_no_setup_even_with_an_open_above_the_zone():
    prev = {**PREV, "close": 130.0}  # the official previous close is above today's open: not a gap up
    assert records([OPEN_CANDLE, TEST_CANDLE, GOOD], prev) == []


# ======================================================================= the three confirmation alternatives (AUTHOR_APPROVED) and the strict close rule
def classify(c):
    return classify_confirmation(mk(*c), 101, 105, PDRBodyConfig().pattern_config())


def test_a_good_green_body_confirms():
    [s] = confirmed([OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)])
    assert s.reference_levels["patterns_passed"] == ["GOOD_GREEN_BODY"] and s.reference_levels["close_minus_ceiling"] == 3
    assert s.signal_timestamp.strftime("%H:%M") == "09:30" and s.signal_candle_start.strftime("%H:%M") == "09:25"


def test_a_lower_price_rejection_candle_confirms_without_being_green():
    c = (108, 109.5, 98, 107)  # red; lower wick 9 >= 2 x body 1; close in the top 13% of the range; low reaches the zone; upper wick 22% so it is not a hammer
    assert classify(c)["patterns_passed"] == ["LOWER_PRICE_REJECTION"]
    [s] = confirmed([OPEN_CANDLE, TEST_CANDLE, c, (107, 108, 106, 107)])
    assert s.reference_levels["patterns_passed"] == ["LOWER_PRICE_REJECTION"] and c[3] < c[0]


def test_a_hammer_confirms_with_any_colour_and_one_signal_is_produced_when_several_patterns_pass():
    for c in ((106, 107, 100, 106.5), (106.5, 107, 100, 106)):  # green and red hammer
        assert "HAMMER" in classify(c)["patterns_passed"]
    sigs = confirmed([OPEN_CANDLE, TEST_CANDLE, (106, 107, 100, 106.5), (106.5, 107, 105.5, 106.5)])
    assert len(sigs) == 1 and set(sigs[0].reference_levels["patterns_passed"]) >= {"LOWER_PRICE_REJECTION", "HAMMER"}  # recorded together, one signal


def test_the_upper_wick_bearish_shape_is_not_a_hammer():
    assert "HAMMER" not in classify((106, 116, 105.8, 106.5))["patterns_passed"]


@pytest.mark.parametrize("c,why", [((103, 105.5, 102.5, 105), "close equal to the ceiling"), ((101, 104.5, 100.5, 104), "close inside the zone"), ((99, 100.5, 98.5, 100), "close below the floor")])
def test_a_close_not_strictly_above_the_ceiling_is_rejected_whatever_the_pattern(c, why):
    res = classify(c)
    assert not res["qualifies"] and not res["close_above_ceiling"], why
    assert confirmed([OPEN_CANDLE, TEST_CANDLE, c, (104, 105, 103, 104)]) == [], why


def test_a_lower_wick_may_penetrate_the_zone_when_the_close_is_above_the_ceiling():
    [s] = confirmed([OPEN_CANDLE, TEST_CANDLE, (106, 107, 99, 106.5), (106.5, 107, 106, 106.5)])  # low 99 is below the floor 101
    assert s.signal_candle_low < 101 and "HAMMER" in s.reference_levels["patterns_passed"]


def test_a_candle_that_passes_no_pattern_is_not_a_signal_even_above_the_ceiling():
    assert confirmed([OPEN_CANDLE, TEST_CANDLE, (106, 107, 105.8, 106.2), (106, 107, 105.5, 106)]) == []  # a thin 'doji-like' candle above the zone: no body, no rejection, no hammer


# ======================================================================= sequence, causality, previous-session-only data
def test_the_test_candle_cannot_confirm_itself_and_a_later_candle_is_needed():
    qualifying_test_candle = (104, 109, 103.5, 108)
    assert confirmed([OPEN_CANDLE, qualifying_test_candle, (108, 109, 107, 108)]) == []
    assert len(confirmed([OPEN_CANDLE, qualifying_test_candle, (108, 109, 107, 108)], confirmation_may_be_interaction_candle=True)) == 1


def test_no_look_ahead_a_signal_exists_only_once_its_candle_has_completed():
    rows = [OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)]
    c = ctx(rows, prev=PREV)
    eng = PDRBodyStrategy(proposals=PROPS)
    full = [r for r in eng.evaluate_session(c) if r.signal_status == "CONFIRMED"]
    assert [r.signal_candle_start.strftime("%H:%M") for r in full] == ["09:25"]
    for k in range(1, 5):
        part = [r for r in eng.evaluate_session(c.prefix(k)) if r.signal_status == "CONFIRMED"]
        assert [r.signal_timestamp for r in part] == ([full[0].signal_timestamp] if k >= 3 else [])
        assert all(r.signal_timestamp == r.signal_candle_start + timedelta(minutes=5) for r in part)


def test_the_zone_uses_only_the_completed_previous_session_not_todays_candles():
    base = confirmed([OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)])[0].reference_levels
    wild = confirmed([(115, 300, 112, 118), TEST_CANDLE, GOOD, (108, 109, 107, 108)])[0].reference_levels  # today's 300 wick / body must not move the zone
    assert (wild["zone_floor"], wild["zone_ceiling"]) == (base["zone_floor"], base["zone_ceiling"]) == (101, 105)


def test_a_data_gap_while_armed_invalidates_the_setup():
    from dataclasses import replace
    c = ctx([OPEN_CANDLE, TEST_CANDLE, (108, 109, 107, 108), GOOD], prev=PREV)
    recs = PDRBodyStrategy(proposals=PROPS).evaluate_session(replace(c, candles=c.candles.drop(index=2).reset_index(drop=True)))
    assert [r.invalidation_reason for r in recs if r.signal_status == "INVALIDATED"] == ["DATA_GAP"] and not [r for r in recs if r.signal_status == "CONFIRMED"]


def test_after_a_signal_the_setup_re_arms_on_a_new_test():
    sigs = confirmed([OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 104, 106), (105, 112, 104.5, 111)])
    assert [s.signal_candle_start.strftime("%H:%M") for s in sigs] == ["09:25", "09:35"]
    assert all(len(s.reference_levels["evaluations"]) == 1 for s in sigs)


# ======================================================================= labels: nothing invented is called author-approved
def test_invented_numbers_are_never_author_approved_and_the_author_statements_are_labelled_as_such():
    st = {r["rule_id"]: r["status"] for r in PDR_BODY_RULES}
    for rid in ("PDR-B01a", "PDR-B03", "PDR-B04", "PDR-B04a", "PDR-B05"):
        assert st[rid] == "AUTHOR_APPROVED", rid
    for rid in ("PDR-B02a", "PDR-B02b", "PDR-B02c", "PDR-B02d", "PDR-B02e", "PDR-B02f", "PDR-B02g", "PDR-B02h", "PDR-B04c", "PDR-B07"):
        assert st[rid] == "PROPOSED_FOR_REVIEW", rid
    assert st["PDR-B01b"] == st["PDR-B04b"] == st["PDR-B05a"] == "OWNER_INTERPRETATION"
    text = {r["rule_id"]: r["text"] for r in PDR_BODY_RULES}
    assert "strictly" not in text["PDR-B05"].lower() and "strictly" in text["PDR-B05a"].lower() and "NOT author-approved" in text["PDR-B04c"]


def test_every_signal_records_its_configuration_and_is_never_verified():
    [s] = confirmed([OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)])
    rev = s.execution_config["pdr_body"]
    assert rev["version"] == "PDR_BODY_PHASE36" and rev["config_id"] == s.reference_levels["config_id"] and rev["rule_status"]["PDR-B04c"] == "PROPOSED_FOR_REVIEW"
    assert s.verification_status != "VERIFIED" and "PDR-B04c" in s.rule_ids_unresolved and s.proposals_used["pdr_body"]["pattern_profile"] == "RESEARCH_DEFAULT"
    other = PDRBodyConfig(pattern_profile="EXAMPLE_LENIENT")
    assert other.config_id(PROPS) != PDRBodyConfig().config_id(PROPS) and PDRBodyConfig(zone_candidate="B_MULTIPLE_BODY_HIGH_CLUSTER").config_id(PROPS).startswith("PDRBODY-B-")


def test_the_two_earlier_pdr_engines_still_exist_and_still_differ_from_the_body_engine():
    rows = [OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)]
    c = ctx(rows, prev=PREV)
    old = [r for r in PDRRevisedStrategy(proposals=PROPS).evaluate_session(c) if r.signal_status == "CONFIRMED"]
    assert old == []  # Phase 3.5 ceiling 110: the close 108 is not above it
    assert len(confirmed(rows)) == 1  # Phase 3.6 ceiling 105: it is
    assert PDRStrategy(proposals=PROPS).STRATEGY == "PDR"


# ======================================================================= nothing else changed (one-time delivery check) and the delivered files
snap_path = OUT / "before_snapshot.json"
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE36_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE36_ALLOW_LATER_EDITS=1")
# Research modules this phase edits (engine selection, explainer, labels); reviewed in independent_audit.md.
ALLOWED = {"src/nifty_trading/research/phase3.py", "src/nifty_trading/research/phase31.py", "src/nifty_trading/research/phase32.py", "src/nifty_trading/research/phase32_build.py",
           "src/nifty_trading/research/phase32_render.py", "src/nifty_trading/research/phase32_excel.py", "scripts/phase35_run.py"}


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


@needs_snapshot
def test_data_earlier_reports_the_other_engines_both_earlier_pdr_engines_and_the_controller_are_byte_identical():
    snap = json.loads(snap_path.read_text())["files"]
    changed = [p for p, h in snap.items() if p not in ALLOWED and (not (ROOT / p).exists() or sha(p) != h)]
    assert changed == []
    for p in ("irf", "orb", "pds", "rf", "pdr", "pdr_revised", "trading_day", "selection", "base", "params", "definitions"):
        assert sha(f"src/nifty_trading/strategies/{p}.py") == snap[f"src/nifty_trading/strategies/{p}.py"], p
    assert sha("src/nifty_trading/core/exit_policy.py") == snap["src/nifty_trading/core/exit_policy.py"]


needs_outputs = pytest.mark.skipif(not (OUT / "all_trades_detailed.csv").exists(), reason="run scripts/phase36_run.py first")


def rows(n):
    with open(OUT / n, newline="") as f:
        return list(csv.DictReader(f))


@needs_outputs
def test_the_four_other_strategies_signal_streams_equal_the_phase_3_5_export():
    def keyset(path):
        with open(path, newline="") as f:
            return sorted((r["date"], r["time"], r["strategy"], r["method"], r["direction"], r["reference_close"]) for r in csv.DictReader(f) if r["strategy"] != "PDR")
    assert keyset(OUT / "all_strategy_signals.csv") == keyset(ROOT / "reports" / "phase3" / "phase35_combined" / "all_strategy_signals.csv")


@needs_outputs
def test_every_pdr_trade_has_a_body_zone_close_above_the_ceiling_and_a_body_config_id():
    pdr = [t for t in rows("all_trades_detailed.csv") if t["strategy"] == "PDR"]
    assert pdr
    for t in pdr:
        assert t["rule_configuration_id"].startswith("CFG-phase36_body_based-") and t["signal_verification_status"] != "VERIFIED"
    conds = [c for c in rows("entry_condition_details.csv") if c["rule_id"] == "PDR-B03" and c["result"] == "PASS"]
    assert len(conds) == len(pdr)


# ======================================================================= engine selection, CLI, explanation (Phase 3.6 integration)
def test_the_body_engine_replaces_only_the_pdr_slot_and_revised_keeps_its_phase_35_meaning():
    from nifty_trading.research import phase3 as P
    from nifty_trading.strategies import IRFStrategy, ORBStrategy, PDSStrategy, RFStrategy
    s = P.scenarios()["baseline"]
    es = P.make_engines(s.proposals, s.trade, "BODY_BASED_PHASE36", PDRBodyConfig())
    assert [type(e) for e in es] == [IRFStrategy, ORBStrategy, PDRBodyStrategy, PDSStrategy, RFStrategy]
    rev = P.make_engines(s.proposals, s.trade, "REVISED_PHASE34", None)
    assert type(rev[2]) is PDRRevisedStrategy  # `revised` still means the Phase 3.5 engine
    new, old = P.combined_scenario("BODY_BASED_PHASE36"), P.combined_scenario()
    assert new.proposals == s.proposals and new.trade == s.trade and new.key == "phase36_body_based" and old.key == "phase35_combined" and old.pdr_engine == "REVISED_PHASE34"
    assert isinstance(new.pdr_revision, PDRBodyConfig) and (new.pdr_revision.zone_candidate, new.pdr_revision.pattern_profile, new.pdr_revision.open_vs_zone) == ("A_HIGHEST_BODY_HIGH", "RESEARCH_DEFAULT", "ABOVE_ZONE")
    assert not hasattr(old.pdr_revision, "zero_height_policy")  # the Phase 3.5 configuration object is the untouched Phase 3.4 one


def test_the_cli_offers_body_based_without_changing_revised_and_refuses_to_overwrite_phase_35(capsys):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("phase35_run_for_36", ROOT / "scripts" / "phase35_run.py")
    cli = importlib.util.module_from_spec(spec)
    sys.modules["phase35_run_for_36"] = cli
    spec.loader.exec_module(cli)
    assert cli.ENGINES["revised"] == "REVISED_PHASE34" and cli.ENGINES["body-based"] == "BODY_BASED_PHASE36" and cli.ENGINES["legacy"] == "LEGACY"
    assert cli.parse_args([]).pdr_engine == "revised"  # the default is still the Phase 3.5 configuration
    assert cli.parse_args(["--pdr-engine", "body-based"]).pdr_engine == "body-based"
    assert cli.main(["--pdr-engine", "body-based", "--out", str(ROOT / "reports" / "phase3" / "phase35_combined")]) == 2
    assert "refusing" in capsys.readouterr().err
    wrapper = (ROOT / "scripts" / "phase36_run.py").read_text()
    assert '"--pdr-engine", "body-based"' in wrapper


def test_a_body_based_trade_is_explained_with_the_body_high_calculation_and_the_wick_shown_as_ignored():
    import test_phase32_explanations as E
    [(tr, ex, _)] = E.explain_all(PDRBodyStrategy, ctx([OPEN_CANDLE, TEST_CANDLE, GOOD, (108, 109, 107, 108)], prev=PREV))
    assert tr.signal.method == "PDR" and not ex.mismatches and not [c for c in ex.checks if c.result == "FAIL"]
    ids = {c.rule_id for c in ex.checks}
    assert {"PDR-004", "PDR-B01a", "PDR-B02", "PDR-B03", "PDR-B03b", "PDR-B04", "PDR-B04c", "PDR-B05", "PDR-B06", "PDR-B04x"} <= ids
    z = E.by_rule(ex, "PDR-B01a")[0]
    assert "Zone [101.00 (body low), 105.00 (body high)]" in z.observed and "ignored" in z.observed and "110.00" in z.observed and z.rule_status == "AUTHOR_APPROVED"
    o = E.by_rule(ex, "PDR-B03")[0]
    assert o.result == "PASS" and o.rule_status == "AUTHOR_APPROVED" and "open - ceiling = +10.00" in o.observed
    assert E.by_rule(ex, "PDR-B04c")[0].rule_status == "PROPOSED_FOR_REVIEW" and "not author-approved" in E.by_rule(ex, "PDR-B04c")[0].calculation
    assert "not approved by the strategy author" in ex.setup_summary and ex.levels["zone"][:2] == (101, 105)


def test_the_configuration_id_of_a_body_trade_differs_from_the_phase_35_and_phase_30_ids():
    from nifty_trading.research import phase32 as X
    s = ProposalConfig(trend_mode="EMA_PREV_SESSION_CLOSE", max_signals_per_session=99)
    from nifty_trading.strategies.params import DEFAULT_TRADE
    body_id = X.config_id(s, DEFAULT_TRADE, "phase36_body_based", PDRBodyConfig())
    assert body_id.startswith("CFG-phase36_body_based-") and body_id != X.config_id(s, DEFAULT_TRADE, "phase35_combined", None)


@needs_outputs
def test_every_required_phase_36_file_exists_and_each_trade_links_to_its_chart_and_journal():
    for n in ("README.md", "pdr_body_zone_rule_audit.md", "pdr_pattern_classification.md", "pdr_source_chart_validation.md", "old_vs_new_pdr_signals.csv", "backtest_summary.md", "all_trades_detailed.csv",
              "daily_summary.csv", "strategy_performance.csv", "manual_journal_comparison.csv", "entry_condition_details.csv", "exit_details.csv", "NIFTY_Daily_Trade_Verification.xlsx",
              "configuration_snapshot.json", "data_provenance.json", "independent_audit.md"):
        assert (OUT / n).exists(), n
    trades = rows("all_trades_detailed.csv")
    ids = [t["trade_id"] for t in trades]
    assert len(set(ids)) == len(ids) and all((OUT / "charts" / f"{i}.svg").exists() for i in ids)
    assert len(rows("daily_summary.csv")) == 247 and all((OUT / "daily" / r["date"][:7] / f"{r['date']}.md").exists() for r in rows("daily_summary.csv"))


@needs_outputs
def test_the_ledger_obeys_the_portfolio_rules_and_the_three_way_comparison_matches_the_ledgers():
    trades = rows("all_trades_detailed.csv")
    assert {t["strategy"] for t in trades} == {"IRF", "ORB", "PDR", "PDS", "RF"}
    by_day: dict[str, list[dict]] = {}
    for t in trades:
        by_day.setdefault(t["date"], []).append(t)
    for ts in by_day.values():
        assert len(ts) <= 2 and all(t["fill_timestamp"][-5:] <= "13:00" for t in ts)
        if len(ts) == 2:
            assert ts[1]["strategy"] in ("PDR", "PDS") and ts[0]["outcome"] == "INITIAL_FULL_STOP"
    for t in trades:
        assert t["qty_total"] == "390" and t["checks_fail"] == "0" and not t["recomputation_mismatches"] and t["signal_verification_status"] != "VERIFIED"
    three = {r["strategy"]: r for r in rows("comparison_3way_by_strategy.csv")}
    assert three["ALL"]["phase30_trades"] == "213" and three["ALL"]["phase35_trades"] == "198" and int(three["ALL"]["phase36_trades"]) == len(trades)
    assert abs(float(three["ALL"]["phase36_gross_rs"]) - sum(float(t["gross_pnl_rs"]) for t in trades)) < 0.01


@needs_outputs
def test_the_configuration_snapshot_labels_the_pdr_thresholds_as_provisional_and_the_open_rule_as_author_approved():
    cfg = json.loads((OUT / "configuration_snapshot.json").read_text())
    assert cfg["pdr_engine"] == "BODY_BASED_PHASE36" and cfg["pdr_body_config"]["open_vs_zone"] == "ABOVE_ZONE"
    assert cfg["pdr_body_rule_status"]["PDR-B03"] == "AUTHOR_APPROVED" and cfg["pdr_body_rule_status"]["PDR-B04c"] == "PROPOSED_FOR_REVIEW" and "NOT approved" in cfg["pdr_provisional_assumptions"]
    assert cfg["targets_2"]["PDR"] == 70.0 and cfg["stops"]["ORB"] == 30.0 and cfg["controller"]["entry_cutoff"] == "13:00:00 IST" and cfg["controller"]["max_entries_per_day"] == 2


@needs_outputs
def test_the_phase_35_results_directory_was_not_touched():
    snap = json.loads(snap_path.read_text())["files"]
    p35 = {k: h for k, h in snap.items() if k.startswith("reports/phase3/phase35_combined/")}
    assert len(p35) > 100 and all((ROOT / k).exists() and sha(k) == h for k, h in p35.items())


# ======================================================================= tests added after the independent review (survivors of its mutation run)
def test_the_body_high_of_a_red_candle_is_its_open_and_it_can_be_the_session_maximum():
    rows = [(100, 101, 99, 100), (100, 102, 100, 101), (110, 111, 100, 105), (105, 106, 98, 100), (98, 99, 90, 95)]  # idx 2 is red: body 105-110 (open 110), wick 111
    z = build_zone_a(cands(rows))
    assert z.ceiling == 110 and z.floor == 105 and z.members == (2,)  # a close-only body high would give 105


def test_the_test_candle_touch_is_inclusive_at_both_edges_and_uses_the_proximity_setting():
    base = [OPEN_CANDLE]
    assert len(confirmed(base + [(118, 119, 105, 106), GOOD, (108, 109, 107, 108)])) == 1  # low exactly at the ceiling 105
    assert confirmed(base + [(118, 119, 105.1, 106), GOOD, (108, 109, 107, 108)]) == []  # 0.1 above the ceiling is no test: the next candle becomes the test candle and cannot confirm itself
    just_above = base + [(118, 119, 105.5, 106), GOOD, (108, 109, 107, 108)]
    assert confirmed(just_above, proximity_points=0.0) == [] and len(confirmed(just_above, proximity_points=1.0)) == 1  # proximity widens the test
    assert len(confirmed([OPEN_CANDLE, (100, 101, 99, 100.5), (104, 109, 103.5, 108), (108, 109, 107, 108)])) == 1  # high exactly at the floor still touches
    assert confirmed([OPEN_CANDLE, (100, 100.9, 99, 100.5), GOOD, (108, 109, 107, 108)]) == []  # a candle entirely below the floor is no test


def test_only_the_enabled_patterns_can_confirm():
    hammer_rows = [OPEN_CANDLE, TEST_CANDLE, (106, 107, 100, 106.5), (106.5, 107, 105.5, 106.5)]
    assert len(confirmed(hammer_rows, patterns_enabled=("HAMMER",))) == 1 and confirmed(hammer_rows, patterns_enabled=("GOOD_GREEN_BODY",)) == []


def test_the_threshold_boundaries_of_the_green_body_and_the_hammer_body_position_are_inclusive():
    cfg = PDRBodyConfig().pattern_config()
    ok = classify_confirmation(mk(102, 110, 100, 108), 101, 105, cfg)["patterns"]["GOOD_GREEN_BODY"]  # body exactly 60%, upper wick exactly 20%
    low_body = classify_confirmation(mk(102.1, 110, 100, 108), 101, 105, cfg)["patterns"]["GOOD_GREEN_BODY"]  # body 59%
    assert ok["passed"] and not low_body["passed"]
    pos_ok = classify_confirmation(mk(106, 110, 100, 108), 101, 105, cfg)["patterns"]["HAMMER"]  # lower wick 6 = 3 x body 2, upper wick 20% -> fails the 10% cap: not a hammer
    h_ok = classify_confirmation(mk(106, 107, 100, 106.5), 101, 105, cfg)["patterns"]["HAMMER"]  # body bottom at 6/7 of the range
    h_low = classify_confirmation(mk(103, 107, 100, 103.5), 101, 105, cfg)["patterns"]["HAMMER"]  # body bottom at 3/7 = 43% of the range (< 60%)
    assert h_ok["passed"] and not h_low["passed"] and not pos_ok["passed"]


def test_the_ceiling_below_wick_flag_appears_only_when_a_wick_was_actually_ignored():
    with_wick = build_zone_a(cands(PREV["cands"]))
    no_wick = build_zone_a(cands([(100, 101, 99, 100), (100, 105, 100, 105), (105, 105, 98, 100)]))  # the highest body high equals the highest high: nothing to ignore
    assert "CEILING_BELOW_WICK_HIGH" in with_wick.flags and "CEILING_BELOW_WICK_HIGH" not in no_wick.flags


def test_every_trade_explanation_discloses_a_zone_that_price_closed_through_before_the_confirmation():
    import test_phase32_explanations as E
    rows = [OPEN_CANDLE, (118, 119, 90, 95), (95, 110, 94, 109), (108, 109, 104, 106), GOOD]  # the test candle closes at 95, BELOW the floor 101, then price returns above the ceiling
    got = E.explain_all(PDRBodyStrategy, ctx(rows, prev=PREV))
    assert got
    note = [c for c in got[0][1].checks if c.rule_id == "PDR-B07"][0]
    assert note.result == "UNRESOLVED" and "CLOSED BELOW the zone floor" in note.observed
