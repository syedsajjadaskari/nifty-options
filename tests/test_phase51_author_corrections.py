"""Phase 5.1: the author's handwritten corrections. Unit tests for the opt-in ORB colour variant (regression: the frozen baseline is unchanged), the diagnostics that measure the author's wording, and the transcription;
file-level tests on the delivered bundle (every dated case reconciled, classifications valid, only AC27 implemented, the baseline byte-identical)."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import sys
from datetime import date
from pathlib import Path

import pytest

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase51 as F51
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_colour import REASON, ORBColourStrategy, colour_ok

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase51_author_corrections"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name + "_t", ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name + "_t"] = mod
    spec.loader.exec_module(mod)
    return mod


def rows(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def candle(start: str, o: float, h: float, low: float, c: float, ema: float | None = None, prior_low: float | None = None) -> dict:
    hh, mm = map(int, start.split(":"))
    end = f"{(hh * 60 + mm + 5) // 60:02d}:{(hh * 60 + mm + 5) % 60:02d}"
    rng = h - low
    return {"start": start, "end": end, "o": o, "h": h, "l": low, "c": c, "colour": "G" if c > o else ("R" if c < o else "D"), "body_pct": None if rng <= 0 else round(100 * abs(c - o) / rng, 1),
            "upper_wick_pct": None if rng <= 0 else round(100 * (h - max(o, c)) / rng, 1), "lower_wick_pct": None if rng <= 0 else round(100 * (min(o, c) - low) / rng, 1), "ema200": ema,
            "session_low_before_this_candle": prior_low, "close_below_prior_session_low": prior_low is not None and c < prior_low}


# ======================================================================= the opt-in ORB colour variant
def test_colour_rule_long_needs_green_and_short_needs_red():
    assert colour_ok("LONG", 100.0, 101.0) and not colour_ok("LONG", 100.0, 99.0) and not colour_ok("LONG", 100.0, 100.0)
    assert colour_ok("SHORT", 100.0, 99.0) and not colour_ok("SHORT", 100.0, 101.0) and not colour_ok("SHORT", 100.0, 100.0)
    assert not colour_ok("LONG", None, 101.0)


def test_the_variant_is_a_subclass_of_the_frozen_engine_and_leaves_the_frozen_module_untouched():
    assert issubclass(ORBColourStrategy, ORBStrategy) and ORBColourStrategy.STRATEGY == "ORB" and ORBColourStrategy._quality is ORBStrategy._quality
    fr = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    for k in fr["active_file_hashes"]:
        assert sha(ROOT / k) == fr["active_file_hashes"][k], k


def test_the_engine_factory_swap_is_scoped_and_restored():
    original = P.make_engines
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    with F51.orb_colour_engines():
        engines = P.make_engines(sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision)
        assert [type(e).__name__ for e in engines] == ["IRFStrategy", "ORBColourStrategy", "PDRBodyStrategy", "PDSStrategy", "RFStrategy"]
    assert P.make_engines is original
    assert [type(e).__name__ for e in P.make_engines(sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision)] == ["IRFStrategy", "ORBStrategy", "PDRBodyStrategy", "PDSStrategy", "RFStrategy"]


@pytest.fixture(scope="module")
def dataset():
    from nifty_trading.core.execution_eligibility import bars_from_frame
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    return ctxs, infos, {d: bars_from_frame(g) for d, g in m1.groupby("_d")}


def test_2025_11_27_the_red_candle_long_is_confirmed_by_the_baseline_and_invalidated_by_the_variant(dataset):
    ctxs, _i, _b = dataset
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    ctx = ctxs[date(2025, 11, 27)]
    base = {(r.method, r.direction): r for r in ORBStrategy(proposals=sc.proposals, trade=sc.trade).evaluate_session(ctx)}
    var = {(r.method, r.direction): r for r in ORBColourStrategy(proposals=sc.proposals, trade=sc.trade).evaluate_session(ctx)}
    k = ("Method 1", "LONG")
    assert base[k].signal_status == "CONFIRMED" and base[k].signal_candle_close < base[k].signal_candle_open  # the baseline admits a bearish first candle for a long
    assert var[k].signal_status == "INVALIDATED" and var[k].invalidation_reason == REASON and "PHASE51_COLOUR_RULE_APPLIED" in var[k].flags
    assert {kk: v.signal_status for kk, v in base.items() if kk != k} == {kk: v.signal_status for kk, v in var.items() if kk != k}  # nothing else changes


def test_across_the_whole_history_only_colour_contradicting_confirmations_change_and_the_baseline_reproduces_phase_36(dataset):
    ctxs, infos, bars = dataset
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    diff = F51.orb_signal_differences(ctxs, sc)
    assert [(r["date"], r["method"], r["direction"]) for r in diff] == [("2025-11-27", "Method 1", "LONG"), ("2026-01-05", "Method 1", "LONG"), ("2026-04-24", "Method 1", "SHORT")]
    for r in diff:
        assert r["baseline_status"] == "CONFIRMED" and r["variant_status"] == "INVALIDATED" and r["variant_reason"] == REASON
        up = r["first_candle_close"] > r["first_candle_open"]
        assert (r["direction"] == "LONG" and not up) or (r["direction"] == "SHORT" and up)
    base = P.run_scenario(sc, ctxs, infos, bars)
    ref = {(t["date"], t["trade_no_of_day"], t["strategy"], t["method"], t["direction"]) for t in rows(ROOT / "reports/phase3/phase36_body_based_pdr/all_trades_detailed.csv")}
    assert {(x["date"], str(x["trade_no"]), x["strategy"], x["method"], x["direction"]) for x in base.ledger} == ref and len(base.ledger) == 196  # the default path is the Phase 3.6 ledger


# ======================================================================= the diagnostics
def test_first_red_candle_reading_follows_the_authors_wording():
    D = load_script("phase51_diagnostics")
    cs = [candle("09:15", 100, 110, 100, 105), candle("09:20", 105, 115, 104, 114),  # IRH 110; breakout close 114
          candle("09:25", 114, 118, 113, 115),  # green
          candle("09:30", 115, 117, 112, 113),  # FIRST red candle fully above IRH: S = 112, R = 117
          candle("09:35", 113, 119, 113, 118),  # trades above R
          candle("09:40", 118, 118.5, 111, 111.5)]  # red, body 6.5/7.5 = 87%, closes below S = 112 and below R
    r = D.first_red_reading(cs)
    assert r["first_red_candle"] == "09:30" and r["support"] == 112 and r["resistance"] == 117
    assert r["entry"]["signal_time"] == "09:45" and r["entry"]["trigger"] == "SUPPORT_BREAK" and r["entry"]["body_pct"] > 60
    weak = cs[:5] + [candle("09:40", 118, 118.5, 111, 116.5)]  # red but body 1.5/7.5 = 20%, closes below R only
    assert D.first_red_reading(weak, body_min=60.0)["entry"] is None and D.first_red_reading(weak, body_min=0.0)["entry"]["trigger"] == "RESISTANCE_BREAK"


def test_irf_measures_report_ema_space_session_low_and_body():
    D = load_script("phase51_diagnostics")
    cs = [candle("09:15", 100, 110, 99, 105, ema=80), candle("09:20", 105, 108, 95, 96, ema=80, prior_low=99)]
    m = D.irf_trade_measures(cs, "09:25")
    assert m["close_below_prior_session_low"] and m["body_pct_below_60"] is False and m["ema_within_27_below_entry"] is True and m["entry_minus_ema"] == 16.0
    near = [candle("09:15", 100, 110, 99, 105, ema=80), candle("09:20", 105, 106, 90, 100, ema=80 + 0, prior_low=99)]
    n = D.irf_trade_measures(near, "09:25")
    assert n["entry_minus_ema"] == 20.0 and n["ema_within_27_below_entry"] and n["ema_between_entry_and_target1"]
    far = [candle("09:15", 100, 110, 99, 105, ema=60), candle("09:20", 105, 106, 90, 100, ema=60)]
    assert not D.irf_trade_measures(far, "09:25")["ema_within_27_below_entry"]


def test_first_green_candle_after_the_zone_test_may_be_the_testing_candle():
    D = load_script("phase51_diagnostics")
    cs = [candle("09:15", 110, 112, 108, 109), candle("09:20", 109, 116, 104, 115),  # green, low 104 <= ceiling 106 (tests the zone) and closes 115 > 106
          candle("09:25", 115, 118, 114, 117)]
    g = D.first_green_after_zone(cs, 100.0, 106.0)
    assert g["interaction_candle"] == "09:20" and g["first_green_close_above_ceiling"]["candle_start"] == "09:20" and g["first_green_close_above_ceiling"]["signal_time"] == "09:25"


# ======================================================================= transcription and delivered bundle
def test_transcription_counts_and_special_cases():
    T = load_script("phase51_transcription")
    rs = T.rows()
    dated = [r for r in rs if r["date"]]
    assert len(rs) == 42 and len(dated) == 40 and sum(1 for r in rs if r["status"] == "GENERAL_RULE") == 1 and sum(1 for r in rs if r["status"] == "GENERAL_RULE_INCOMPLETE") == 1
    assert [r["correction_id"] for r in rs if r["status"] == "CROSSED_OUT"] == ["AC23"]
    ac38 = next(r for r in rs if r["correction_id"] == "AC38")
    assert ac38["date"] == "2025-12-26" and "20251216" in ac38["trade_id_as_written"] and ac38["transcription_confidence"] == "medium"
    assert all(date.fromisoformat(r["date"]).weekday() < 5 for r in dated) and len({(r["date"], r["trade_no"]) for r in dated}) == 40


needs_outputs = pytest.mark.skipif(not (OUT / "correction_classifications.csv").exists(), reason="run the Phase 5.1 scripts first")


@needs_outputs
def test_every_observation_is_classified_with_valid_classes_and_nothing_is_called_a_defect_or_a_controller_error():
    cl = rows(OUT / "correction_classifications.csv")
    valid = {"MISSING_AUTHOR_RULE", "CANDLE_CONFIRMATION_MISMATCH", "SUPPORT_RESISTANCE_MISMATCH", "EMA_FILTER_MISMATCH", "ENTRY_TIMING_MISMATCH", "AUTHOR_DISCRETION_UNRESOLVED", "DATA_DIFFERENCE", "JOURNAL_INCONSISTENCY", "NO_DISCREPANCY_FOUND",
             "CONFIRMED_SOFTWARE_BUG", "WRONG_STRATEGY_SELECTION"}
    assert len(cl) == 42
    for r in cl:
        cs = [c for c in r["classifications"].split(";") if c]
        assert all(c in valid for c in cs) and (cs or r["correction_id"] == "AC23")
        assert "CONFIRMED_SOFTWARE_BUG" not in cs and "WRONG_STRATEGY_SELECTION" not in cs
        assert r["owner_approval_required"] or r["correction_id"] == "AC23"
    assert [r["correction_id"] for r in cl if r["implemented"] != "NO"] == ["AC27"]


@needs_outputs
def test_every_dated_case_has_a_report_a_chart_and_a_reconciliation_row_and_selection_cases_never_blame_the_controller():
    rec = rows(OUT / "date_by_date_reconciliation.csv")
    dated = [r for r in rows(OUT / "all_author_corrections.csv") if r["date"]]
    assert {r["correction_id"] for r in rec} == {r["correction_id"] for r in rows(OUT / "all_author_corrections.csv")}
    for r in dated:
        assert (OUT / "daily" / f"{r['date']}.md").exists() and (OUT / "charts" / f"{r['date']}.svg").exists()
    sel = rows(OUT / "strategy_selection_conflicts.csv")
    assert sel and all(r["verdict"].startswith("CONTROLLER_CORRECT") for r in sel)


@needs_outputs
def test_the_implemented_variant_changes_exactly_the_documented_signals():
    diff = rows(OUT / "before_after_signal_differences.csv")
    changed = [(r["date"], r["direction"]) for r in diff if r["rule"] == "ORB_COLOUR_AC27" and r["level"] == "ORB signal"]
    assert changed == [("2025-11-27", "LONG"), ("2026-01-05", "LONG"), ("2026-04-24", "SHORT")]
    assert all(r["status"].startswith(("IMPLEMENTED_OPT_IN", "NOT_IMPLEMENTED")) for r in diff)
    pop = json.loads((OUT / "population_impact.json").read_text())
    assert pop["phase36_trades"] == 196 and pop["orb_colour_regression_ledger_equals_phase36"] is True


@needs_outputs
def test_required_phase_51_files_exist():
    for n in ("README.md", "handwritten_corrections_transcribed.md", "all_author_corrections.csv", "date_by_date_reconciliation.csv", "correction_classifications.csv", "confirmed_software_defects.md", "new_author_rules.md", "proposed_rule_changes.md",
              "strategy_selection_conflicts.csv", "manual_journal_comparison.csv", "before_after_signal_differences.csv", "owner_approval_required.md", "independent_audit.md", "Author_Corrections_Verification.xlsx"):
        assert (OUT / n).exists(), n
    assert (OUT / "daily").is_dir() and (OUT / "charts").is_dir() and len(list((OUT / "pages").glob("page_*_full.png"))) == 6


# ======================================================================= preservation (one-time delivery check)
snap_path = OUT / "before_snapshot.json"
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE51_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE51_ALLOW_LATER_EDITS=1")


@needs_snapshot
def test_every_baseline_file_is_byte_identical_to_the_pre_phase51_snapshot():
    snap = json.loads(snap_path.read_text())["hashes"]
    changed = [p for p, h in snap.items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    assert changed == []
    for p in ("src/nifty_trading/strategies/orb.py", "src/nifty_trading/strategies/irf.py", "src/nifty_trading/strategies/pdr_body.py", "src/nifty_trading/strategies/trading_day.py", "reports/phase3/phase36_body_based_pdr/all_trades_detailed.csv"):
        assert p in snap
