"""Phase 5.5: unit tests of the cost / slippage arithmetic and the metrics on hand-built trades; configuration-factory tests (A is the frozen factory, B replaces only IRF / PDR / PDS, C differs from B only in the ORB engine; RF never changes);
and file-level tests on the delivered bundle (frozen reproduction, signal totals, controller limits, cost-sensitivity identities). All money is SYNTHETIC index-point P&L."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase55 as F55
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_candidates import ORBCandidateStrategy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
SC = P.combined_scenario("BODY_BASED_PHASE36")
needs_bundle = pytest.mark.skipif(not (OUT / "all_executed_trades.csv").exists(), reason="Phase 5.5 bundle not generated")


def row(gross=1000.0, leg1="27.0", leg2="60.0", q=390, **kw):
    r = {"qty_total": q, "qty_leg1": q // 2, "qty_leg2": q - q // 2, "leg1_exit_price": leg1, "leg2_exit_price": leg2, "gross_pnl_rs": gross, "date": "2026-01-01", "entry_time": "09:20", "trade_no": 1, "outcome": "TARGET",
         "gross_points_weighted": 2.0, "holding_minutes": 30, "t1_booked": "True", "ambiguities": 0}
    r.update(kw)
    return r


def csv_rows(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def test_fixed_cost_is_not_the_old_500_and_is_charged_once_per_trade():
    assert F55.FIXED_COST_RS == 70.0
    assert F55.net_pnl(row(), 70.0, 0.0) == 930.0
    assert F55.net_pnl(row(), 0.0, 0.0) == 1000.0


def test_slippage_is_applied_to_filled_units_without_double_counting():
    r = row()  # entry 390 + two exit legs 195 + 195 = 780 filled units
    assert F55.filled_units(r) == (390.0, 390.0)
    assert F55.net_pnl(r, 70.0, 0.25) == 1000.0 - 70.0 - 0.25 * 780
    assert F55.net_pnl(r, 70.0, 1.0) == 1000.0 - 70.0 - 780.0
    # a leg without an exit fill has no exit slippage
    r2 = row(leg2="")
    assert F55.filled_units(r2) == (390.0, 195.0)
    assert F55.net_pnl(r2, 0.0, 0.5) == 1000.0 - 0.5 * 585


def test_per_fill_sensitivity_charges_each_fill():
    assert F55.net_pnl(row(), 70.0, 0.0, per_fill=True) == 1000.0 - 3 * 70.0
    assert F55.net_pnl(row(leg2=""), 70.0, 0.0, per_fill=True) == 1000.0 - 2 * 70.0


def test_profit_factor_and_drawdown():
    assert F55.profit_factor([100, -50, 50, -50]) == 1.5
    assert F55.profit_factor([10, 20]) == float("inf")
    assert F55.profit_factor([]) is None
    assert F55.max_drawdown([10, -4, -3, 5, -20, 30]) == 22  # peak 10 -> trough -12
    assert F55.max_drawdown([5, 5]) == 0


def test_metrics_counts_and_order():
    rows = [row(gross=-500.0, outcome="INITIAL_FULL_STOP", date="2026-01-02"), row(gross=300.0, date="2026-01-01"), row(gross=100.0, trade_no=2, date="2026-01-01", entry_time="11:00", outcome="T1_THEN_BUFFER_STOP")]
    m = F55.metrics(rows)
    assert (m["trades"], m["first_trades"], m["second_trades"], m["winning_trades"], m["losing_trades"]) == (3, 2, 1, 2, 1)
    assert m["net_pnl_rs"] == -100.0 and m["initial_full_stops"] == 1 and m["t2_hits"] == 1
    assert [r["date"] for r in F55.trade_order(rows)] == ["2026-01-01", "2026-01-01", "2026-01-02"]
    assert F55.metrics(rows, 70.0, 0.0)["net_pnl_rs"] == -100.0 - 3 * 70.0


def test_cost_scenarios_are_the_specified_five():
    assert [(k, f, s) for k, _t, f, s in F55.COST_SCENARIOS] == [("A", 0.0, 0.0), ("B", 70.0, 0.0), ("C", 70.0, 0.25), ("D", 70.0, 0.5), ("E", 70.0, 1.0)]


def test_configuration_factories():
    a = F55.engines_for("A", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)
    b = F55.engines_for("B", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)
    c = F55.engines_for("C", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)
    ref = P.make_engines(SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision)
    assert [type(e) for e in a] == [type(e) for e in ref]
    assert type(a[1]) is ORBStrategy and type(b[1]) is ORBStrategy  # B does not touch ORB
    assert isinstance(c[1], ORBCandidateStrategy) and c[1].gap_crossing_def == "CANDLE_CROSSES_AVERAGE"
    assert c[1].inner_level_def == "LATEST_FRACTAL_K2" and c[1].trendline_def == "LAST_TWO_FRACTALS_K2"  # no inner-level / trendline variant
    assert [type(e).__name__ for e in b] == ["IRFPhase53Strategy", "ORBStrategy", "PDRFirstEligibleStrategy", "PDSFirstEligibleStrategy", "RFStrategy"]  # IRF / PDR / PDS replaced in B, ORB and RF untouched
    assert [type(e) for i, e in enumerate(b) if i != 1] == [type(e) for i, e in enumerate(c) if i != 1]  # C differs from B only in ORB
    assert type(a[4]) is type(b[4]) is type(c[4])  # RF never changes
    with pytest.raises(ValueError):
        F55.engines_for("Z", SC.proposals, SC.trade)


def test_patched_engines_restores_the_factory():
    from nifty_trading.research import phase31 as P31
    before = (P31.make_engines, P.make_engines)
    with F55.patched_engines("C"):
        assert P31.make_engines is not before[0]
    assert (P31.make_engines, P.make_engines) == before


@needs_bundle
def test_frozen_baseline_reproduced_and_signal_totals():
    st = json.loads((OUT / "phase55_state.json").read_text())
    fi = st["frozen_identity"]
    assert fi["frozen_configuration_id"] == fi["id_recomputed_from_stored_blob"] == "FROZEN-PHASE36-42cea2600bd4" and fi["active_files_verified"] == 26
    sig = csv_rows("all_confirmed_signals.csv")
    cnt = {k: Counter(s["strategy"] for s in sig if s["config"] == k) for k in "ABC"}
    assert dict(cnt["A"]) == {k: v for k, v in F55.EXPECTED_SIGNALS["A"].items() if k != "total"}
    assert dict(cnt["B"]) == {k: v for k, v in F55.EXPECTED_SIGNALS["B"].items() if k != "total"}
    assert dict(cnt["C"]) == {**dict(cnt["B"]), "ORB": cnt["B"]["ORB"] + 3}
    assert sum(cnt["A"].values()) == 1083 and sum(cnt["B"].values()) == 1109
    tr = csv_rows("all_executed_trades.csv")
    assert sum(1 for t in tr if t["config"] == "A") == 196


@needs_bundle
def test_controller_limits_hold_in_every_configuration():
    tr = csv_rows("all_executed_trades.csv")
    for k in "ABC":
        by = {}
        for t in [t for t in tr if t["config"] == k]:
            by.setdefault(t["date"], []).append(t)
            assert t["signal_confirmed_at"][-5:] <= "13:00"  # the 13:00 entry cutoff
        for d, ts in by.items():
            assert len(ts) <= 2, (k, d)
            if len(ts) == 2:
                ts.sort(key=lambda t: int(t["trade_no_of_day"]))
                assert ts[1]["fill_timestamp"] > ts[0]["leg2_exit_time"] or ts[1]["fill_timestamp"][-5:] >= ts[0]["leg2_exit_time"][-5:], (k, d)  # the second trade enters after the first has fully exited
                assert ts[1]["strategy"] in ("PDR", "PDS"), (k, d)
                assert ts[0]["outcome"] == "INITIAL_FULL_STOP", (k, d)
        assert all(t["qty_total"] == "390" for t in tr if t["config"] == k)


@needs_bundle
def test_cost_sensitivity_gross_equals_trade_ledger_and_costs_are_monotone():
    tr = csv_rows("all_executed_trades.csv")
    cs = csv_rows("cost_sensitivity.csv")
    assert cs
    for k in "ABC":
        gross = sum(float(t["gross_pnl_rs"]) for t in tr if t["config"] == k)
        rows = sorted((r for r in cs if r["config"] == k and r["cost_scenario"][:2] in ("A:", "B:", "C:", "D:", "E:")), key=lambda r: r["cost_scenario"][0])
        alt = [r for r in cs if r["config"] == k and r["cost_scenario"].startswith("ALT")]
        assert len(alt) == 1 and float(alt[0]["net_pnl_rs"]) <= float(rows[1]["net_pnl_rs"])  # per-fill reading never costs less than per-trade
        assert [r["cost_scenario"][0] for r in rows] == list("ABCDE")
        vals = [float(r["net_pnl_rs"]) for r in rows]
        assert abs(vals[0] - gross) < 0.5
        assert vals == sorted(vals, reverse=True)
        assert all(int(r["trades"]) == sum(1 for t in tr if t["config"] == k) for r in rows)


@needs_bundle
def test_every_trade_is_fully_resolved_with_exit_legs():
    tr = csv_rows("all_executed_trades.csv")
    assert all(t["outcome"] in ("TARGET", "INITIAL_FULL_STOP", "T1_THEN_BUFFER_STOP", "FORCED_EXIT") for t in tr)
    assert all(t["leg1_exit_price"] and t["leg2_exit_price"] for t in tr)  # no unresolved or auction-priced leg in this history
