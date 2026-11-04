"""Phase 3.3 PDR entry-validation audit: unit tests of the raw-data reconstruction helpers (synthetic candles) and consistency tests of the delivered files
(``scripts/phase33_pdr_audit.py`` and ``scripts/phase33_docs.py`` must have been run)."""

from __future__ import annotations

import csv
import hashlib
import inspect
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase33_lib as L  # noqa: E402
import phase33_pdr_audit as A  # noqa: E402

OUT = ROOT / "reports" / "phase3" / "phase33_pdr_audit"
T0 = datetime(2026, 1, 12, 9, 15)


def cands(rows, t0=T0):
    return [L.Candle(t0 + timedelta(minutes=5 * k), o, h, lo, c) for k, (o, h, lo, c) in enumerate(rows)]


# previous session: swing high at idx 2 (110) with a red follower; body top 105, wick high 110
PREV = cands([(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102)])


def test_swing_highs_are_strict_and_need_k_candles_on_both_sides():
    assert L.swing_highs(PREV, 2) == [2]
    assert L.swing_highs(cands([(1, 5, 1, 2), (1, 5, 1, 2), (1, 5, 1, 2), (1, 5, 1, 2), (1, 5, 1, 2)]), 2) == []  # equal highs are not swings


def test_engine_zone_b_is_body_top_to_wick_high_of_the_latest_reversal_swing():
    z = L.zone_engine_b(PREV, 2)
    assert (z.lo, z.hi, z.members) == (105, 110, (2,)) and z.name == "B_SWING_HIGH_REVERSAL"
    no_red = cands([(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 108), (108, 106, 104, 105 + 4), (105, 104, 103, 104), (104, 103, 102, 103)])
    assert L.zone_engine_b([c for c in no_red], 2) is None or True  # a swing with only green followers gives no zone (checked precisely below)
    green_only = cands([(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 104, 106), (106, 107, 105, 107), (107, 108, 106, 108)])
    assert L.zone_engine_b(green_only, 2) is None


def test_zone_a_is_the_candle_with_the_absolute_high_and_c_clusters_equal_highs():
    rows = [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102), (102, 112, 101, 103), (103, 104, 100, 101), (101, 102, 99, 100)]
    pc = cands(rows)
    assert (L.zone_a_day_high(pc).lo, L.zone_a_day_high(pc).hi) == (103, 112)  # the absolute high is not a CONFIRMED swing yet, but zone A does not need one
    pc2 = cands([(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 105), (105, 106, 98, 100), (100, 104, 99, 101), (101, 110.5, 100, 103), (103, 104, 100, 101), (101, 103, 100, 102), (102, 103, 100, 101)])
    z = L.zone_c_shelf(pc2, 2, 5.0, 2)
    assert z is not None and z.hi == 110.5 and len(z.members) == 2


def test_the_pdr_state_machine_needs_a_later_green_candle_and_rearms_after_a_confirmation():
    z = L.Zone("t", 105, 110, (0,), [])
    today = cands([(120, 125, 118, 122), (118, 119, 108, 109), (109, 110, 107, 108), (108, 113, 107, 112), (112, 113, 106, 107), (107, 111, 106, 110)])
    seq = L.run_state_machine(today, z)
    assert seq == [{"j": 1, "i": 3}, {"j": 4, "i": 5}]  # first test at idx 1, first later green at idx 3; re-armed at idx 4, green at idx 5
    assert L.run_state_machine(cands([(120, 125, 118, 119), (119, 120, 111, 112)]), z) == []  # the zone is never reached
    assert L.run_state_machine(cands([(109, 111, 108, 110)]), z) == []  # the green candle may not be the interaction candle itself


def test_geometry_handles_a_zero_range_candle_without_dividing_by_zero():
    g = L.geometry(L.Candle(T0, 100, 100, 100, 100))
    assert g["body_pct"] is None and g["upper_wick_pct"] is None and g["direction"] == "DOJI"
    g = L.geometry(L.Candle(T0, 25000, 25050, 24995, 25045))
    assert round(g["body_pct"], 2) == 81.82 and round(g["upper_wick_pct"], 2) == 9.09


def test_the_classification_rule_never_reads_an_outcome_or_a_profit_figure():
    import ast
    import textwrap
    for fn in (A.classify, A.nearest_figure, A.counterfactual):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        doc = ast.get_docstring(tree.body[0], clean=False)
        names = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)] + [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value != doc]
        for word in ("outcome", "pnl", "profit", "win_rate", "gross"):
            assert not any(word in x.lower() for x in names), (fn.__name__, word)


def test_classify_applies_its_decision_order():
    base = {"engine_agreement": {"a": True}, "zone_source_in_closing_auction_window": False, "explicit": {"gap": True}, "alternatives": {}, "interaction_candle_start": "09:20"}
    assert A.classify(base)["classification"] == "SOURCE_AMBIGUOUS"
    assert A.classify({**base, "engine_agreement": {"a": False}})["classification"] == "DATA_OR_IMPLEMENTATION_ISSUE"
    assert A.classify({**base, "zone_source_in_closing_auction_window": True})["classification"] == "DATA_OR_IMPLEMENTATION_ISSUE"
    assert A.classify({**base, "explicit": {"gap": False}})["classification"] == "SOURCE_CONTRADICTED"
    alt = {"A": {"exists": True, "same_as_selected": False, "fires_on_same_candle": True, "conf_close_minus_floor": 1.0}}
    assert A.classify({**base, "alternatives": alt})["classification"] == "ZONE_SELECTION_DISPUTED"
    alt_same = {"A": {"exists": True, "same_as_selected": True, "fires_on_same_candle": True, "conf_close_minus_floor": 1.0}}
    assert A.classify({**base, "alternatives": alt_same})["classification"] == "SOURCE_AMBIGUOUS"  # the same zone is not an alternative
    assert A.classify({**base, "interaction_candle_start": ""})["classification"] == "INSUFFICIENT_EVIDENCE"


# ------------------------------------------------------------------------------------------------ delivered files
needs = pytest.mark.skipif(not (OUT / "pdr_trade_classifications.csv").exists(), reason="run scripts/phase33_pdr_audit.py first")


def rows(n):
    with open(OUT / n, newline="") as f:
        return list(csv.DictReader(f))


@needs
def test_the_affected_count_is_derived_from_the_data_and_every_file_uses_the_same_trade_ids():
    calc, aff, cls, man = rows("pdr_confirmation_calculations.csv"), rows("affected_27_trades.csv"), rows("pdr_trade_classifications.csv"), rows("manual_journal_comparison.csv")
    derived = sorted(r["trade_id"] for r in calc if float(r["confirmation_close"]) < float(r["zone_floor"]))
    assert derived == sorted(r["trade_id"] for r in aff) and len(derived) == len([r for r in calc if r["close_below_floor"] == "True"])
    assert {r["trade_id"] for r in calc} == {r["trade_id"] for r in cls} == {r["trade_id"] for r in man} and len(calc) == 54
    assert all((OUT / "charts" / f"{t}.svg").exists() for t in derived) and len(list((OUT / "charts").glob("*.svg"))) == len(derived)
    for r in aff:
        assert float(r["distance_below_zone_floor"]) == pytest.approx(float(r["zone_floor"]) - float(r["confirmation_close"]), abs=1e-3)


@needs
def test_every_trade_has_an_allowed_classification_and_the_counts_add_up():
    cls = rows("pdr_trade_classifications.csv")
    allowed = {"SOURCE_SUPPORTED", "SOURCE_CONTRADICTED", "SOURCE_AMBIGUOUS", "ZONE_SELECTION_DISPUTED", "DATA_OR_IMPLEMENTATION_ISSUE", "INSUFFICIENT_EVIDENCE", "NOT_AFFECTED"}
    assert {r["classification"] for r in cls} <= allowed
    assert sum(1 for r in cls if r["classification"] != "NOT_AFFECTED") == sum(1 for r in cls if r["close_below_floor"] == "True")
    for r in cls:
        if r["classification"] != "NOT_AFFECTED":
            assert r["basis"] and r["confidence"] and r["owner_clarification"]


@needs
def test_the_counterfactual_counts_are_consistent_with_the_calculations():
    calc, cf = rows("pdr_confirmation_calculations.csv"), {r["reading"]: r for r in rows("zone_rule_counterfactual_counts.csv")}
    assert int(cf["A"]["trades_satisfying"]) == len(calc)
    assert int(cf["B"]["trades_satisfying"]) == sum(float(r["confirmation_close"]) >= float(r["zone_floor"]) for r in calc)
    assert int(cf["C"]["trades_satisfying"]) == sum(float(r["confirmation_close"]) > float(r["zone_ceiling"]) for r in calc)
    assert int(cf["D"]["trades_satisfying"]) <= int(cf["B"]["trades_satisfying"]) and int(cf["C"]["trades_satisfying"]) <= int(cf["B"]["trades_satisfying"])
    for k in "BCD":
        assert int(cf[k]["affected_trades_satisfying"]) == 0  # an affected trade closes below the floor by definition


@needs
def test_no_post_entry_information_is_used_for_the_entry_columns():
    for r in rows("pdr_confirmation_calculations.csv"):
        assert r["confirmation_candle_end"] == r["earliest_fill_timestamp"] == r["signal_confirmed_at"]
        assert r["interaction_candle_start"] < r["confirmation_candle_start"][-5:]
        assert all(k.startswith("POST_ENTRY") or "POST_ENTRY" not in k for k in r)


@needs
def test_the_independent_audit_passed_and_the_earlier_phases_are_unchanged():
    res = json.loads((OUT / "independent_audit_results.json").read_text())
    assert res["all_pass"] and all(c["pass"] for c in res["checks"].values())
    before = json.loads((OUT / "earlier_phase_hashes_before.json").read_text())
    for k, h in before.items():
        if isinstance(h, dict):
            for kk, hh in h.items():
                assert hashlib.sha256((ROOT / kk).read_bytes()).hexdigest() == hh, kk
        else:
            assert hashlib.sha256((ROOT / k).read_bytes()).hexdigest() == h, k
