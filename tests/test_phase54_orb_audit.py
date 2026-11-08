"""Phase 5.4: ORB source audit. Unit tests of the candidate construction selectors, the first-candle measurements and the predicate matrix on synthetic candles; regression tests on the real 2025-26 sessions (the default
candidate engine equals the frozen ORB engine, the frozen ORB equals the Phase 3.6 signal table, every variant replaces only the ORB engine, the 13 disputed dates carry no confirmed ORB signal); read-only checks of the manual
journal counts; and file-level tests on the delivered bundle. No profit is computed anywhere."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pytest
from synthetic import ctx

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase54 as V
from nifty_trading.research import phase54_orb as O
from nifty_trading.strategies.definitions import Candle, to_candles
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_candidates import (
    INNER_LEVEL_DEFS,
    ORBCandidateStrategy,
    select_inner_level,
    trendline_supportive,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase54_orb_audit"
SC = P.combined_scenario("BODY_BASED_PHASE36")
T0 = datetime(2026, 1, 1, 9, 15)
NAN = float("nan")
D13 = ["2025-09-11", "2025-09-16", "2025-10-08", "2025-10-16", "2025-10-17", "2025-10-27", "2025-11-21", "2025-11-28", "2025-12-05", "2025-12-12", "2025-12-24", "2025-12-30", "2025-12-31"]


def cd(o, h, l, c, ema=NAN):  # noqa: E741
    return Candle(T0, T0, o, h, l, c, ema)


def key(r):
    return (r.strategy, r.method, r.direction, r.signal_status, None if r.signal_timestamp is None else r.signal_timestamp.isoformat(), r.invalidation_reason)


# ======================================================================= inner-level selectors (pure)
LEVELS = [110.0, 120.0, 105.0, 115.0]  # oldest first; the previous day's high is above all of them


@pytest.mark.parametrize(("definition", "candle", "expected"), [
    ("LATEST_FRACTAL_K2", cd(100, 118, 99, 117), 115.0),
    ("HIGHEST_FRACTAL_K2", cd(100, 118, 99, 117), 120.0),
    ("NEAREST_FRACTAL_FROM_OPEN_K2", cd(100, 118, 99, 117), 105.0),  # the first swing above the open of 100
    ("NEAREST_FRACTAL_FROM_OPEN_K2", cd(112, 118, 111, 117), 115.0),  # the open is already above 105 and 110
    ("HIGHEST_BROKEN_FRACTAL_K2", cd(100, 118, 99, 117), 115.0),  # 120 is not broken (high 118): the highest broken is 115
    ("HIGHEST_BROKEN_FRACTAL_K2", cd(100, 125, 99, 122), 120.0),
])
def test_long_inner_level_definitions_choose_the_documented_level(definition, candle, expected):
    assert select_inner_level(LEVELS, candle, True, definition) == expected


def test_short_definitions_mirror_the_long_ones_and_no_level_means_none():
    lv = [90.0, 80.0, 95.0, 85.0]
    c = cd(100, 101, 82, 83)
    assert select_inner_level(lv, c, False, "LATEST_FRACTAL_K2") == 85.0
    assert select_inner_level(lv, c, False, "HIGHEST_FRACTAL_K2") == 80.0  # the lowest support (nearest the major level)
    assert select_inner_level(lv, c, False, "NEAREST_FRACTAL_FROM_OPEN_K2") == 95.0  # the first swing below the open of 100
    assert select_inner_level(lv, c, False, "HIGHEST_BROKEN_FRACTAL_K2") == 85.0  # 80 is not broken (low 82)
    assert all(select_inner_level([], c, False, d) is None for d in INNER_LEVEL_DEFS)
    assert select_inner_level(LEVELS, cd(100, 101, 99, 100), True, "HIGHEST_BROKEN_FRACTAL_K2") is None  # nothing broken
    with pytest.raises(ValueError):
        select_inner_level(LEVELS, cd(100, 101, 99, 100), True, "MADE_UP")


def test_trendline_definitions_and_the_diagnostic_none():
    pcs = [cd(100, 101, 99, 100)] * 12
    # fractal lows at indices 2, 6, 9 with prices 98, 99, 98.5: the last two (6, 9) fall, the pair (2, 6) rises
    pcs = [cd(100, 101, 100 - (2 if i == 2 else 1 if i == 6 else 1.5 if i == 9 else 0), 100) for i in range(12)]
    c = cd(100, 103, 100, 102)
    ok_last, why_last, line = trendline_supportive(pcs, [2, 6, 9], c, True, "LAST_TWO_FRACTALS_K2")
    assert not ok_last and why_last == "TRENDLINE_NOT_SUPPORTIVE" and line is not None
    ok_any, why_any, _ = trendline_supportive(pcs, [2, 6, 9], c, True, "ANY_RISING_PAIR_OF_LAST_THREE_K2")
    assert ok_any and why_any == "TRENDLINE_SUPPORTIVE"  # the pair (2, 6) rises and the close is above its extrapolation
    assert trendline_supportive(pcs, [2, 6, 9], c, True, "NONE")[0] is True
    assert trendline_supportive(pcs, [9], c, True, "LAST_TWO_FRACTALS_K2")[1] == "NO_TRENDLINE"


# ======================================================================= first-candle measurements
def test_geometry_and_strength_margins_on_a_known_candle():
    c = cd(100, 110, 100, 108)  # green, range 10, body 8 (80%), upper wick 2 (20%), lower wick 0
    g = O.geometry(c)
    assert g["colour"] == "GREEN" and g["body_pct"] == 80.0 and g["upper_wick_pct"] == 20.0 and g["lower_wick_pct"] == 0.0 and g["close_location_pct"] == 80.0
    st = O.strength_table(c, True, SC.proposals)
    assert st["strong_MODERATE"] and st["strong_LOOSE"] and not st["strong_STRICT"]  # STRICT needs body >= 70% and opposite wick <= 15%
    assert st["body_margin_MODERATE"] == 20.0 and st["opp_wick_margin_MODERATE"] == 0.0  # exactly on the 20% boundary: inclusive
    assert st["opp_wick_margin_STRICT"] == -5.0
    red = O.strength_table(cd(108, 110, 100, 100), False, SC.proposals)
    assert red["strong_MODERATE"] is True and red["opposite_wick_pct"] == 0.0 and red["body_pct"] == 80.0 and red["colour"] == "RED"  # for a SHORT the wick against the trade is the LOWER wick: 0 here, so the body is strong
    assert O.geometry(cd(100, 100, 100, 100))["body_pct"] is None  # a zero-range candle has no percentages


PREV = {"cands": [(100, 104, 99, 103), (103, 109, 102, 108), (108, 108, 101, 102), (102, 105, 100, 104)], "close": 104.0, "ema_last": 98.0}  # the last close 104 is above its EMA 98


def test_predicate_matrix_orders_predicates_and_signs_the_margins():
    c = ctx([(104, 112, 104, 111), (111, 112, 110, 111.5)], prev=PREV, ema=[100.0, 100.5], open_price=104.0)
    pm = O.predicate_matrix(c, SC.proposals, True)
    m1 = {r["name"]: r for r in pm["Method 1"]}
    assert list(m1) == ["level_broken", "trend", "candle_quality"]
    assert m1["level_broken"]["pass"] is True and m1["level_broken"]["margin"] == 111 - 109  # the previous-day high is 109; the close is 2 beyond it
    assert m1["trend"]["pass"] is True and m1["candle_quality"]["pass"] is True
    short = O.predicate_matrix(c, SC.proposals, False)
    assert short["Method 1"][0]["pass"] is False and O.first_failing(short["Method 1"]) == "level_broken"
    assert [r["name"] for r in pm["Gap/200DMA"]] == ["gap_in_direction", "gap_crosses_200_average", "first_candle_closes_beyond_average", "candle_shape"]


def test_gap_crossing_readings_differ_only_when_the_open_sits_on_the_wrong_side_of_the_average():
    prev = {"cands": [(100, 101, 99, 100)] * 3, "close": 100.0, "ema_last": 101.0}  # previous close 100 below its average 101
    # open 100.95 is 0.05 BELOW the average 101.0 although the candle closes well above it
    c = ctx([(100.95, 106, 100.95, 105), (105, 106, 104, 105.5)], prev=prev, ema=[101.0, 101.2], open_price=100.95)
    r = O.gap_crossing_readings(c, SC.proposals, True)
    assert r["gap_in_direction"] and not r["frozen_crossing"] and r["alt_candle_crossing"] and r["differs"]
    c2 = ctx([(101.5, 106, 101.5, 105), (105, 106, 104, 105.5)], prev=prev, ema=[101.0, 101.2], open_price=101.5)
    r2 = O.gap_crossing_readings(c2, SC.proposals, True)
    assert r2["frozen_crossing"] and r2["alt_candle_crossing"] and not r2["differs"]


# ======================================================================= configuration safety
def test_variants_are_disabled_by_default_and_replace_only_the_orb_engine():
    assert type(V.make_orb_engine(V.FROZEN_KEY, SC.proposals, SC.trade)) is ORBStrategy
    frozen_engines = P.make_engines(SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)
    assert type(frozen_engines[1]) is ORBStrategy  # the frozen factory never uses a candidate
    from nifty_trading.research import phase52 as F52
    from nifty_trading.research import phase53 as F53
    for k in F53.CONFIGS:
        if k != "phase53-var-orb-colour":
            assert type(F53.make_engines53(k, SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)[1]) is ORBStrategy, k
    for k in F52.CONFIGS:
        if k != "phase52-cand-orb-colour":
            assert type(F52.make_engines52(k, SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)[1]) is ORBStrategy, k
    assert all(v.authority != "ACTIVE_REFERENCE" for k, v in V.VARIANTS.items() if k != V.FROZEN_KEY)
    assert isinstance(V.make_orb_engine("orb-var-inner-highest-fractal", SC.proposals, SC.trade), ORBCandidateStrategy)
    with pytest.raises(ValueError):
        ORBCandidateStrategy(proposals=SC.proposals, trade=SC.trade, inner_level_def="MADE_UP")


def test_no_calendar_date_is_hardcoded_in_the_new_production_modules():
    for f in ("src/nifty_trading/strategies/orb_candidates.py", "src/nifty_trading/research/phase54.py", "src/nifty_trading/research/phase54_orb.py"):
        assert not re.search(r"20\d\d-\d\d-\d\d", (ROOT / f).read_text()), f


# ======================================================================= real-data regression
@pytest.fixture(scope="module")
def real():
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    ctxs, _ = build_session_contexts(load_one_minute(), daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    return ctxs


def test_real_the_default_candidate_engine_and_every_frozen_default_equal_the_frozen_orb_engine(real):
    frozen = ORBStrategy(proposals=SC.proposals, trade=SC.trade)
    cand = ORBCandidateStrategy(proposals=SC.proposals, trade=SC.trade)
    from dataclasses import asdict
    for d, c in real.items():
        a, b = [asdict(r) for r in cand.evaluate_session(c)], [asdict(r) for r in frozen.evaluate_session(c)]
        assert a == b, d  # every field of every record (levels, state trace, proposals, flags) equals the frozen engine's


def test_real_the_frozen_orb_equals_the_phase_36_signal_table_and_the_13_dates_carry_no_confirmed_orb(real):
    sig = V.orb_signals_for(real, SC, V.FROZEN_KEY)
    conf = sorted((str(d), r.method, r.direction, f"{r.signal_timestamp:%H:%M}") for d, recs in sig.items() for r in recs if r.signal_status == "CONFIRMED")
    p36 = sorted((r["date"], r["method"], r["direction"], r["time"]) for r in csv.DictReader(open(ROOT / "reports" / "phase3" / "phase36_body_based_pdr" / "all_strategy_signals.csv", newline="")) if r["strategy"] == "ORB")
    assert conf == p36 and len(conf) == 53
    assert not [d for d in D13 if any(r.signal_status == "CONFIRMED" for r in sig[datetime.fromisoformat(d).date()])]
    for d in D13:  # the opening range is the 09:15-09:20 candle in every disputed session
        c = to_candles(real[datetime.fromisoformat(d).date()].candles)[0]
        assert f"{c.start:%H:%M}-{c.end:%H:%M}" == "09:15-09:20"


def test_real_variants_signal_only_orb_and_a_looser_gate_never_removes_a_frozen_signal(real):
    base = {(str(d), r.method, r.direction) for d, recs in V.orb_signals_for(real, SC, V.FROZEN_KEY).items() for r in recs if r.signal_status == "CONFIRMED"}
    for k in ("orb-var-strength-loose", "orb-var-trendline-none", "orb-var-trendline-any-pair"):  # loosening only one gate: every frozen signal stays
        got = {(str(d), r.method, r.direction) for d, recs in V.orb_signals_for(real, SC, k).items() for r in recs if r.signal_status == "CONFIRMED"}
        assert base <= got, k
    strict = {(str(d), r.method, r.direction) for d, recs in V.orb_signals_for(real, SC, "orb-var-strength-strict").items() for r in recs if r.signal_status == "CONFIRMED"}
    assert strict <= base  # a stricter profile can only remove signals


# ======================================================================= the manual journal (read only)
def test_journal_counts_are_read_from_the_original_workbook_without_changes():
    import openpyxl
    ws = openpyxl.load_workbook(ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", data_only=True).worksheets[0]
    rows = [r for r in ws.iter_rows(min_row=3, values_only=True) if r[0] is not None and r[1] is not None]
    assert len(rows) == 190 and sum(1 for r in rows if r[3] == "ORB") == 89 and sum(1 for r in rows if r[1].weekday() >= 5) == 5


# ======================================================================= bundle (skipped before the runner has produced it)
needs_bundle = pytest.mark.skipif(not (OUT / "orb_13_disputed_dates.csv").exists(), reason="Phase 5.4 bundle not generated yet")


@needs_bundle
def test_bundle_contains_every_required_deliverable():
    need = ["orb_complete_source_audit.md", "orb_source_rule_registry.csv", "orb_13_disputed_dates.csv", "orb_level_reconstruction.md", "orb_candle_strength_review.md", "orb_ema_trendline_review.md", "orb_author_corrections.md",
            "orb_rule_decision_matrix.md", "independent_audit.md"]
    assert [n for n in need if not (OUT / n).exists()] == [] and (OUT / "daily").is_dir() and (OUT / "charts").is_dir()
    assert sorted(p.stem for p in (OUT / "daily").glob("*.md")) == sorted(D13) and sorted(p.stem for p in (OUT / "charts").glob("*.svg")) == sorted(D13)


@needs_bundle
def test_baselined_files_are_byte_identical_to_the_before_snapshot():
    snap = json.loads((OUT / "before_snapshot.json").read_text())["hashes"]
    bad = [rel for rel, h in snap.items() if not (ROOT / rel).exists() or hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != h]
    assert all(b.endswith(".DS_Store") for b in bad), bad


def test_gap_candle_crossing_variant_admits_a_candle_whose_open_is_just_on_the_wrong_side_and_is_otherwise_the_frozen_setup():
    prev = {"cands": [(100, 101, 99, 100)] * 3, "close": 100.0, "ema_last": 101.0}
    c = ctx([(100.95, 106, 100.95, 105), (105, 106, 104, 105.5)], prev=prev, ema=[101.0, 101.2], open_price=100.95)
    frozen = ORBStrategy(proposals=SC.proposals, trade=SC.trade)
    cand = ORBCandidateStrategy(proposals=SC.proposals, trade=SC.trade, gap_crossing_def="CANDLE_CROSSES_AVERAGE")
    assert not [r for r in frozen.evaluate_session(c) if r.method == "Gap/200DMA"]
    got = [r for r in cand.evaluate_session(c) if r.method == "Gap/200DMA" and r.direction == "LONG"]
    assert got and got[0].signal_status == "CONFIRMED" and got[0].proposals_used["gap_crossing_def"] == "CANDLE_CROSSES_AVERAGE"
    # when the open is already beyond the average, both definitions agree exactly
    c2 = ctx([(101.5, 106, 101.5, 105.6), (105, 106, 104, 105.5)], prev=prev, ema=[101.0, 101.2], open_price=101.5)
    a = [r.signal_status for r in frozen.evaluate_session(c2) if r.method == "Gap/200DMA"]
    b = [r.signal_status for r in cand.evaluate_session(c2) if r.method == "Gap/200DMA"]
    assert a == b and a == ["CONFIRMED"]
