"""Phase 6.2 combined-portfolio tests: the ORB V2 adapter (entry signals only, provenance, 09:20), the cost model (per trade vs per fill, slippage on actual fills), the independent execution simulator, and invariants of the
published ledgers (controller rules, position split, distances, cutoff, second-trade rule, configuration separation)."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from nifty_trading.research import phase55 as X
from nifty_trading.research.orb_v2 import config as OC
from nifty_trading.research.orb_v2 import signal_engine as SE
from nifty_trading.strategies.orb_v2_adapter import ORBV2Strategy

ROOT = Path(__file__).resolve().parents[1]
R62 = ROOT / "reports" / "phase6" / "phase62_combined_backtest"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
from test_phase60_orb_v2 import _prev, sd_for  # noqa: E402

needs = pytest.mark.skipif(not (R62 / "all_executed_trades.csv").exists(), reason="Phase 6.2 outputs not generated")


def fake_ctx(sd):
    tz = "Asia/Kolkata"
    o = sd.opening
    cand = pd.DataFrame({"bar_start": [pd.Timestamp(o["start"]).tz_localize(tz)], "bar_end": [pd.Timestamp(o["confirmed_at"]).tz_localize(tz)], "open": [o["open"]], "high": [o["high"]], "low": [o["low"]], "close": [o["close"]], "ema200_5m": [sd.ema_now]})
    return SimpleNamespace(date=sd.date, info=SimpleNamespace(usable=True, quality=SimpleNamespace(value="VALID"), status=SimpleNamespace(value="USABLE"), reasons=()), candles=cand, data_flags=(), previous=None)


def buy_session():
    prev = _prev([24990 - i % 3 for i in range(75)])
    return sd_for(opening=(25000, 25040.5, 24999.5, 25040), ema_now=24900, prev_candles=prev, prev_close=24990)


def test_adapter_emits_a_confirmed_orb_signal_at_0920_with_provenance_and_never_verified():
    sd = buy_session()
    dec = SE.evaluate_session(sd, OC.A)
    assert dec.signal == "BUY"
    eng = ORBV2Strategy({sd.date: (dec, sd)}, OC.A)
    recs = eng.evaluate_session(fake_ctx(sd))
    assert len(recs) == 1
    r = recs[0]
    assert r.strategy == "ORB" and r.direction == "LONG" and r.signal_status == "CONFIRMED" and f"{r.signal_timestamp:%H:%M}" == "09:20" and f"{r.signal_candle_start:%H:%M}" == "09:15"
    assert r.verification_status == "RESEARCH_VARIANT" and r.execution_config["entry_rule_status"] == "RESEARCH_VARIANT" and r.reference_price_is_fill is False
    lv = r.reference_levels
    assert lv["orb_v2_config_id"] == "ORB-V2-A" and lv["standalone_30_60_exit_ledger_used"] is False and lv["entry_reference_price"] == 25040 and "OD-2" in lv["unresolved_assumptions"]
    assert r.execution_config["stop_distance"] == 30.0 and r.execution_config["target_2"] == 60.0 and r.execution_config["target_1"] == 27.0   # the PORTFOLIO exit model, not a standalone ledger
    assert any(f == "ORB_V2_PROVISIONAL_CONFIGURATION" for f in r.flags)
    assert eng.integration_checks[0]["opening_candle_equals_context"] is True and eng.integration_checks[0]["signal_candle_09_15_to_09_20"] is True


def test_adapter_returns_no_signal_for_a_rejected_session_and_logs_why():
    sd = sd_for(opening=(25400, 25460, 25395, 25398), ema_now=24900, prev_close=24990)
    dec = SE.evaluate_session(sd, OC.A)
    eng = ORBV2Strategy({sd.date: (dec, sd)}, OC.A)
    assert eng.evaluate_session(fake_ctx(sd)) == [] and "GAP_TOO_LARGE" in eng.rejections[0]["failed"]


def test_adapter_marks_sessions_orb_v2_could_not_evaluate_as_not_evaluated():
    sd = buy_session()
    eng = ORBV2Strategy({sd.date: (None, "NO_PREVIOUS_SESSION")}, OC.A)
    r = eng.evaluate_session(fake_ctx(sd))
    assert len(r) == 1 and r[0].signal_status == "NOT_EVALUATED"


def test_cost_model_per_trade_per_fill_and_slippage_on_actual_filled_units():
    row = {"gross_pnl_rs": 10000.0, "qty_total": 390, "qty_leg1": 195, "qty_leg2": 195, "leg1_exit_price": 100.0, "leg2_exit_price": 110.0}
    assert X.net_pnl(row, 70.0, 0.0) == 9930.0
    assert X.net_pnl(row, 70.0, 0.0, per_fill=True) == 10000.0 - 210.0                      # entry + two exit legs
    assert X.net_pnl(row, 70.0, 0.5) == 10000.0 - 70.0 - 0.5 * (390 + 390)                  # 390 entry units + 195 + 195 exit units
    unresolved = dict(row, leg2_exit_price="")
    assert X.net_pnl(unresolved, 0.0, 1.0) == 10000.0 - 1.0 * (390 + 195)                   # a leg without a fill is not charged


def sim_mod():
    return importlib.import_module("phase62_audit")


def day_frame(mods=None):
    idx = pd.date_range("2025-09-16 09:15", "2025-09-16 15:29", freq="1min")
    df = pd.DataFrame({"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0}, index=idx)
    for hm, v in (mods or {}).items():
        df.loc[pd.Timestamp(f"2025-09-16 {hm}"), ["open", "high", "low", "close"]] = v
    df["ts"] = df.index
    return df.reset_index(drop=True)


def test_independent_simulator_two_leg_paths_and_forced_exit():
    S = sim_mod()
    e = 100.0
    full = S.sim(day_frame({"10:00": (100, 101, 64, 65)}), "LONG", "IRF", 9 * 60 + 20, 195, 195, False)                # stop 65 (35 below)
    assert full["outcome"] == "INITIAL_FULL_STOP" and full["l1"] == 65.0 and full["pnl"] == -35.0 * 390
    t1_stop = S.sim(day_frame({"10:00": (100, 127.5, 99.5, 127), "10:05": (127, 127.5, 93.0, 94)}), "LONG", "IRF", 9 * 60 + 20, 195, 195, False)
    assert t1_stop["outcome"] == "T1_THEN_BUFFER_STOP" and t1_stop["l1"] == e + 27 and t1_stop["l2"] == e - 6 and abs(t1_stop["pnl"] - (27 * 195 - 6 * 195)) < 1e-9
    target = S.sim(day_frame({"10:00": (100, 127.5, 99.5, 127), "10:20": (127, 161, 126, 160)}), "LONG", "IRF", 9 * 60 + 20, 195, 195, False)
    assert target["outcome"] == "TARGET" and target["l2"] == e + 60 and abs(target["pnl"] - (27 + 60) * 195) < 1e-9
    pdr_t2 = S.sim(day_frame({"10:00": (100, 127.5, 99.5, 127), "10:20": (127, 171, 126, 170)}), "LONG", "PDR", 9 * 60 + 20, 195, 195, False)
    assert pdr_t2["outcome"] == "TARGET" and pdr_t2["l2"] == e + 70                                                        # PDR/PDS target 2 = 70
    orb_stop = S.sim(day_frame({"10:00": (100, 131, 99.5, 130)}), "SHORT", "ORB", 9 * 60 + 20, 195, 195, False)             # SHORT ORB: stop 30 ABOVE the entry
    assert orb_stop["outcome"] == "INITIAL_FULL_STOP" and orb_stop["l1"] == 130.0 and orb_stop["pnl"] == -30.0 * 390
    orb_t1 = S.sim(day_frame({"10:00": (100, 101, 69, 70)}), "SHORT", "ORB", 9 * 60 + 20, 195, 195, False)                  # T1 at 73 touched; post-T1 stop 106 and T2 40 untouched -> forced exit at the 15:14 open
    assert orb_t1["outcome"] == "FORCED_EXIT" and orb_t1["l1"] == 73.0 and orb_t1["l2"] == 100.0 and abs(orb_t1["pnl"] - 27.0 * 195) < 1e-9
    forced = S.sim(day_frame({"15:14": (103, 104, 102, 103)}), "LONG", "RF", 9 * 60 + 20, 195, 195, False)
    assert forced["outcome"] == "FORCED_EXIT" and forced["l2"] == 103.0 and forced["pnl"] == 3.0 * 390
    same_min = S.sim(day_frame({"10:00": (100, 130, 60, 100)}), "LONG", "IRF", 9 * 60 + 20, 195, 195, False)
    assert same_min["outcome"] == "INITIAL_FULL_STOP" and same_min["amb"] >= 1                                              # stop before target, flagged


# ---------------------------------------------------------------------------------------------------------------- published ledger invariants
STOP = {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0}
T2 = {"IRF": 60.0, "ORB": 60.0, "PDR": 70.0, "PDS": 70.0, "RF": 60.0}


@pytest.fixture(scope="module")
def ledger():
    if not (R62 / "all_executed_trades.csv").exists():
        pytest.skip("Phase 6.2 outputs not generated")
    return pd.read_csv(R62 / "all_executed_trades.csv", dtype={"leg1_exit_time": str, "leg2_exit_time": str, "entry_time": str, "signal_time": str})


@needs
def test_every_published_trade_follows_the_position_distance_and_timing_rules(ledger):
    for r in ledger.itertuples():
        s = 1 if r.direction == "LONG" else -1
        assert (r.qty_total, r.qty_leg1, r.qty_leg2) == (390, 195, 195)
        assert abs(r.stop_level - (r.entry_price - s * STOP[r.strategy])) < 1e-6 and abs(r.t1_level - (r.entry_price + s * 27)) < 1e-6 and abs(r.t2_level - (r.entry_price + s * T2[r.strategy])) < 1e-6
        assert r.entry_time <= "13:00" and r.entry_time == r.signal_time                    # the fill is the bar that starts when the signal candle ends
        if r.outcome in ("T1_THEN_BUFFER_STOP", "TARGET"):
            assert abs(r.post_t1_stop_level - (r.entry_price - s * 6)) < 1e-6              # post-T1 stop: entry -/+ 6, never exact breakeven
        assert r.leg2_exit_time <= "15:14"                                                  # nothing at or after 15:15


@needs
def test_controller_rules_max_two_trades_second_only_pdr_pds_after_a_full_stop(ledger):
    for (_, _, _), g in ledger.groupby(["window", "config", "date"]):
        g = g.sort_values("trade_no")
        assert len(g) <= 2
        if len(g) == 2:
            first, second = g.iloc[0], g.iloc[1]
            assert first.outcome == "INITIAL_FULL_STOP" and second.strategy in ("PDR", "PDS")
            assert second.entry_time > first.leg2_exit_time                                  # strictly after the first trade's full-stop minute (never the same minute)


@needs
def test_orb_v2_trades_in_c_are_0920_entries_equal_to_the_phase60_signals_and_configurations_are_separate(ledger):
    c = ledger[(ledger.window == "A") & (ledger.config == "C")]
    orb = c[c.strategy == "ORB"]
    assert (orb.signal_time == "09:20").all() and (orb.entry_time == "09:20").all()
    p60 = pd.read_csv(ROOT / "reports/phase6/phase60_orb_from_scratch/all_orb_signals.csv")
    p60 = p60[(p60.config_id == "ORB-V2-A") & (p60.window == "A") & p60.signal.isin(["BUY", "SELL"])]
    assert set(orb.date) == set(p60.date) and len(orb) == len(p60)                              # the ORB V2 entry signals are imported exactly (39)
    for dt, d in zip(orb.date, orb.direction, strict=True):
        assert d == ("LONG" if p60[p60.date == dt].signal.iloc[0] == "BUY" else "SHORT")
    a = ledger[(ledger.window == "A") & (ledger.config == "A")]
    assert len(a) == 196 and abs(a.gross_pnl_rs.sum() - 297765.0) < 1e-6                         # the frozen configuration is untouched
    d1, b = ledger[(ledger.window == "A") & (ledger.config == "D1")], ledger[(ledger.window == "A") & (ledger.config == "B")]
    assert sorted(d1.trade_id) == sorted(b.trade_id) and abs(d1.gross_pnl_rs.sum() - b.gross_pnl_rs.sum()) < 1e-6


@needs
def test_manifest_labels_orb_v2_as_a_provisional_reference_and_keeps_the_cost_scenarios():
    m = json.loads((R62 / "configuration_manifest.json").read_text())
    assert m["orb_v2"]["config_id"] == "ORB-V2-A" and "PROVISIONAL" in m["orb_v2"]["selection"] and m["old_fixed_500_assumption"] == "NOT USED"
    assert [c["id"] for c in m["cost_scenarios"]] == ["GROSS", "C70_TRADE", "C70_FILL", "C70_S025", "C70_S05", "C70_S1"]
    assert m["position"]["total_units"] == 390 and m["new_combined_configuration_id"] == "phase62-irfv2-orbv2-combined"


@needs
def test_independent_execution_audit_found_no_problems():
    s = json.loads((R62 / "execution_audit_summary.json").read_text())
    assert sum(v["trades"] for v in s.values()) > 3000 and sum(v["problems"] for v in s.values()) == 0
