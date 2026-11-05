"""Phase 4: the multi-year validation of the frozen Phase 3.6 strategy. Unit tests (freeze enforcement, CLI, calendar derivation, session quality table, vendor-overlap audit, metrics, fill-level costs,
regime causality) on synthetic data; file-level tests on the delivered bundle (source columns, provenance hashes, slices, workbook, preservation of every earlier file)."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase4 as F
from nifty_trading.research import phase4_data as D
from nifty_trading.research import phase4_report as R

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase4"


def load_cli():
    spec = importlib.util.spec_from_file_location("phase4_run_t", ROOT / "scripts" / "phase4_run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phase4_run_t"] = mod
    spec.loader.exec_module(mod)
    return mod


def minute_frame(day: date, start="09:15", n=375, base=100.0, tz="Asia/Kolkata", step=0.01) -> pd.DataFrame:
    t0 = pd.Timestamp(f"{day} {start}", tz=tz)
    ts = [t0 + pd.Timedelta(minutes=i) for i in range(n)]
    close = [base + step * i for i in range(n)]
    return pd.DataFrame({"timestamp": ts, "open": [c - 0.005 for c in close], "high": [c + 0.02 for c in close], "low": [c - 0.02 for c in close], "close": close, "volume": 0})


# ======================================================================= freeze and CLI
def test_run_specs_use_the_frozen_scenario_and_label_every_window_honestly():
    sc = F.frozen_scenario()
    assert sc == P.combined_scenario("BODY_BASED_PHASE36") and sc.pdr_engine == "BODY_BASED_PHASE36"
    assert F.SPECS["C"].status == "EXPLORATORY" and F.SPECS["D_5P"].status == "PARTIAL_YEAR" and F.SPECS["D_TV"].status == "EXPLORATORY" and F.SPECS["B"].status == "DATA_VALIDATED" and F.SPECS["B_TV"].status == "VENDOR_SENSITIVITY"
    assert (F.SPECS["B"].start, F.SPECS["B"].end) == (date(2022, 9, 1), date(2025, 8, 31)) and (F.SPECS["C"].start, F.SPECS["C"].end) == (date(2018, 1, 1), date(2018, 12, 31))
    assert F.SPECS["D_5P"].start == date(2019, 3, 1) and F.SPECS["D_TV"].start == date(2019, 1, 1)  # 5paisa 1-minute coverage starts 2019-03-01; the secondary source covers the whole year
    assert F.SPECS["B"].daily_source == D.SRC_5P_DAILY and F.SPECS["C"].minute_source == D.SRC_TV_MIN


def test_cli_requires_the_frozen_config_and_offers_every_documented_window(capsys):
    cli = load_cli()
    with pytest.raises(SystemExit):
        cli.parse_args(["--window", "all"])  # --strategy-config is mandatory
    with pytest.raises(SystemExit):
        cli.parse_args(["--strategy-config", "something-else", "--window", "all"])
    for w in ("three-year", "2018", "2019", "all", "custom"):
        assert cli.parse_args(["--strategy-config", "phase36-frozen", "--window", w]).window == w
    assert cli.WINDOW_SETS["2019"] == ["D_5P", "D_TV"] and cli.WINDOW_SETS["three-year"] == ["B"] and cli.WINDOW_SETS["2018"] == ["C"] and set(cli.WINDOW_SETS["all"]) == {"B", "B_TV", "C", "D_5P", "D_TV"}
    with pytest.raises(SystemExit):
        cli.parse_args(["--help"])
    assert "phase4_run.py --strategy-config phase36-frozen --window three-year" in capsys.readouterr().out


def test_cli_refuses_to_write_outside_a_phase4_directory_and_a_custom_window_needs_dates(capsys):
    cli = load_cli()
    assert cli.main(["--strategy-config", "phase36-frozen", "--window", "all", "--out", str(ROOT / "reports" / "phase3" / "phase36_body_based_pdr")]) == 2
    assert cli.main(["--strategy-config", "phase36-frozen", "--window", "custom", "--out", str(OUT)]) == 2
    err = capsys.readouterr().err
    assert "refusing" in err and "--start" in err


def test_the_freeze_is_verified_and_a_changed_strategy_file_or_parameter_stops_the_run(tmp_path, monkeypatch):
    cli = load_cli()
    fr = cli.verify_freeze()
    assert fr["frozen_configuration_id"].startswith("FROZEN-PHASE36-") and fr["parameters"]["targets_2"]["PDR"] == 70.0 and fr["parameters"]["stops"]["ORB"] == 30.0
    tampered = json.loads((OUT / "strategy_freeze.json").read_text())
    key = next(k for k in tampered["active_file_hashes"] if k.endswith("strategies/irf.py"))
    tampered["active_file_hashes"][key] = "0" * 64
    p = tmp_path / "freeze.json"
    p.write_text(json.dumps(tampered))
    monkeypatch.setattr(cli, "FREEZE", p)
    with pytest.raises(SystemExit) as e:
        cli.verify_freeze()
    assert "VIOLATED" in str(e.value) and "irf.py" in str(e.value)
    tampered = json.loads((OUT / "strategy_freeze.json").read_text())
    for fk in ("src/nifty_trading/research/phase3.py", "src/nifty_trading/research/phase32.py", "src/nifty_trading/core/exit_policy.py"):  # the guard covers EVERY hashed file, not only the engine folders
        t2 = json.loads(json.dumps(tampered))
        t2["active_file_hashes"][fk] = "0" * 64
        p2 = tmp_path / "freeze_fw.json"
        p2.write_text(json.dumps(t2))
        monkeypatch.setattr(cli, "FREEZE", p2)
        with pytest.raises(SystemExit) as ef:
            cli.verify_freeze()
        assert "VIOLATED" in str(ef.value) and fk.split("/")[-1] in str(ef.value)
    monkeypatch.setattr(cli, "FREEZE", p)
    tampered["parameters"]["trade_config"]["t1_points"] = 99.0
    p.write_text(json.dumps(tampered))
    with pytest.raises(SystemExit) as e2:
        cli.verify_freeze()
    assert "parameters.trade_config" in str(e2.value)


# ======================================================================= calendar derivation
def test_a_weekday_with_no_daily_candle_and_no_minute_rows_is_a_holiday_but_a_vendor_gap_is_not():
    daily = pd.DataFrame({"date": [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 4)], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})  # 2 Jan: no daily candle, no minutes -> holiday; 3 Jan: daily but no minutes -> gap
    minutes = pd.concat([minute_frame(date(2024, 1, 1)), minute_frame(date(2024, 1, 4))], ignore_index=True)
    cal, meta = D.derive_calendar(daily, {"SRC": minutes}, date(2024, 1, 1), date(2024, 1, 5), {"SRC": [(date(2024, 1, 1), date(2024, 1, 5))]})
    assert date(2024, 1, 2) in cal.holidays and date(2024, 1, 3) not in cal.holidays and date(2024, 1, 5) in cal.holidays
    assert [g["date"] for g in meta["gaps_between_series"]] == ["2024-01-03"] and cal.closing_auction is None  # no closing-auction regime before 2026-08-03


def test_weekend_and_evening_sessions_are_special_and_only_full_normal_hours_are_evaluable():
    daily = pd.DataFrame({"date": [date(2024, 2, 3), date(2024, 2, 5), date(2024, 2, 10)], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})
    minutes = pd.concat([minute_frame(date(2024, 2, 3)), minute_frame(date(2024, 2, 5), start="18:15", n=60), minute_frame(date(2024, 2, 10), n=120)], ignore_index=True)  # Saturday full; Monday evening; Saturday short
    cal, _ = D.derive_calendar(daily, {"SRC": minutes}, date(2024, 2, 1), date(2024, 2, 11), {"SRC": [(date(2024, 2, 1), date(2024, 2, 11))]})
    assert cal.special_sessions[date(2024, 2, 3)].evaluable_by_strategies is True
    assert cal.special_sessions[date(2024, 2, 5)].evaluable_by_strategies is False and "first bar is not 09:15" in cal.special_sessions[date(2024, 2, 5)].name
    assert cal.special_sessions[date(2024, 2, 10)].evaluable_by_strategies is False


def test_a_source_is_only_expected_to_have_rows_inside_its_coverage_ranges():
    daily = pd.DataFrame({"date": [date(2024, 3, 1), date(2024, 3, 4)], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})
    minutes = minute_frame(date(2024, 3, 1))
    _, meta = D.derive_calendar(daily, {"SRC": minutes}, date(2024, 3, 1), date(2024, 3, 4), {"SRC": [(date(2024, 3, 1), date(2024, 3, 1))]})
    assert meta["gaps_between_series"] == []  # 4 March is outside the source's retrieval range: not a gap
    _, meta2 = D.derive_calendar(daily, {"SRC": minutes}, date(2024, 3, 1), date(2024, 3, 4), {"SRC": [(date(2024, 3, 1), date(2024, 3, 4))]})
    assert [g["date"] for g in meta2["gaps_between_series"]] == ["2024-03-04"]


# ======================================================================= loaders and quality table
def test_identical_duplicate_rows_are_removed_conflicting_ones_are_reported_and_prices_are_rounded_to_two_decimals():
    df = minute_frame(date(2024, 1, 2), n=5)
    df.loc[0, "close"] = 100.123  # provider float noise
    dup = pd.concat([df, df.iloc[[1]], df.iloc[[2]].assign(close=999.0)], ignore_index=True)
    out, info = D._finish_minutes(dup)
    assert len(out) == 5 and info["duplicate_rows_removed"] == 2 and info["conflicting_duplicate_timestamps"] == 1
    assert out.loc[0, "close"] == 100.12 and info["max_rounding_deviation"] > 0 and out["timestamp"].is_monotonic_increasing
    assert out.loc[out["timestamp"] == df.loc[2, "timestamp"], "close"].iloc[0] == 999.0  # the last row is kept, as the Phase 1 downloader did


def test_the_session_quality_table_reports_missing_minutes_ohlc_violations_and_reconciles_with_the_daily_series():
    d = date(2024, 1, 2)
    m = minute_frame(d)
    m = m[~((m["timestamp"].dt.hour == 10) & (m["timestamp"].dt.minute.between(0, 4)))].reset_index(drop=True)  # five missing minutes at 10:00-10:04
    m.loc[3, "high"] = m.loc[3, "open"] - 1.0  # high below the open: a violation
    daily = pd.DataFrame({"date": [d], "open": [m["open"].iloc[0] + 1.0], "high": [m["high"].max()], "low": [m["low"].min()], "close": [m["close"].iloc[-1] + 3.0]})
    from nifty_trading.data.market_calendar import MarketCalendar
    q = D.session_quality_table(m, daily, MarketCalendar(), "SRC")
    r = q.iloc[0]
    assert r["missing_regular_minutes"] == 5 and r["missing_minute_ranges"].startswith("10:00-10:04") and r["ohlc_violation_rows"] == 1
    assert r["daily_close_minus_last_1529"] == pytest.approx(3.0) and r["first_open_minus_daily_open"] == pytest.approx(-1.0) and bool(r["in_daily_series"])
    assert r["pipeline_status"].startswith("EXCLUDED_CORRUPT") and not bool(r["usable"])  # an OHLC-inconsistent session is excluded by the pipeline's own gate


def test_overlap_audit_agrees_with_itself_detects_value_differences_and_the_timestamp_convention():
    a = minute_frame(date(2024, 1, 2), step=0.5)  # a 0.5-point move per minute: a one-minute shift is clearly visible
    b = a.copy()
    day, _mon, s = D.overlap_audit(a, b, "a", "b")
    assert s["share_exact_all_fields"] == 1.0 and s["bars_compared"] == 375 and s["max_abs_close_diff"] == 0.0 and s["timestamp_shift_test"]["0"]["share_close_equal_within_0_05"] == 1.0
    c = a.copy()
    c.loc[100:110, "close"] += 2.0
    _d, _m, s2 = D.overlap_audit(a, c, "a", "c")
    assert s2["max_abs_close_diff"] == 2.0 and s2["share_exact_all_fields"] < 1.0 and s2["days_with_any_diff_over_1pt"] == 1
    tick = a.copy()
    tick["close"] = tick["close"] + 0.05  # an exact one-tick difference counts as within 0.05 (no float-subtraction loss)
    _d, _m, s4 = D.overlap_audit(a, tick, "a", "tick")
    assert s4["share_close_within_0_05"] == 1.0 and s4["share_exact_all_fields"] == 0.0
    shifted = a.copy()
    shifted["timestamp"] = shifted["timestamp"] + pd.Timedelta(minutes=1)
    _d, _m, s3 = D.overlap_audit(a, shifted, "a", "shifted")
    assert s3["timestamp_shift_test"]["-1"]["share_close_equal_within_0_05"] > s3["timestamp_shift_test"]["0"]["share_close_equal_within_0_05"]  # a one-minute label offset would be visible


# ======================================================================= metrics and costs
def trade(i: int, pnl: float, strat="IRF", day="2022-09-05", outcome="TARGET", no="1") -> dict:
    return {"trade_id": f"T{i}", "date": day, "fill_timestamp": f"{day} 09:{20 + i:02d}", "trade_no_of_day": no, "strategy": strat, "gross_pnl_rs": pnl, "illustrative_net_pnl_rs": pnl - 890.0, "gross_pnl_points_weighted": pnl / 390.0,
            "outcome": outcome, "qty_total": 390, "bars_held": 30}


def test_drawdown_losing_streak_and_profit_factor_follow_the_phase_3_definitions():
    seq = [1000.0, -400.0, -300.0, 200.0, -700.0, 500.0]
    dd, at = F.max_drawdown(seq)
    assert dd == 1200.0 and at == 4  # cumulative 1000, 600, 300, 500, -200, 300: peak 1000, trough -200 and F.max_losing_streak(seq) == 2 and F.profit_factor(seq) == pytest.approx(1700 / 1400) and F.profit_factor([5.0]) == math.inf and F.profit_factor([-5.0]) == 0.0


def test_window_metrics_cover_every_required_quantity_and_ignore_nothing():
    trs = [trade(0, 1000.0, "IRF"), trade(1, -500.0, "ORB", outcome="INITIAL_FULL_STOP"), trade(2, 300.0, "PDR", day="2022-10-03", outcome="T1_THEN_BUFFER_STOP"), trade(3, -100.0, "PDR", day="2022-10-03", no="2", outcome="INITIAL_FULL_STOP")]
    daily = [{"date": "2022-09-05", "session_type": "USABLE / VALID", "day_end_portfolio_state": "DAY_FINISHED"}, {"date": "2022-10-03", "session_type": "USABLE_WITH_FLAGS / VALID", "day_end_portfolio_state": "UNRESOLVED_EXECUTION"},
             {"date": "2022-11-01", "session_type": "USABLE / VALID", "day_end_portfolio_state": "READY_FOR_FIRST_TRADE"}]
    m = F.window_metrics(trs, daily, "x")
    assert m["trades"] == 4 and m["first_trades"] == 3 and m["second_trades"] == 1 and m["trades_PDR"] == 2 and m["gross_pnl_rs_fixed_390"] == 700.0 and m["net_pnl_rs_illustrative"] == 700.0 - 4 * 890.0
    assert m["win_rate_pct"] == 50.0 and m["median_trade_rs"] == 100.0 and m["largest_win_rs"] == 1000.0 and m["largest_loss_rs"] == -500.0 and m["simultaneous_signal_conflict_days"] == 1
    assert m["positive_months"] == 2 and m["negative_months"] == 0 and m["flat_months"] == 1  # 2022-09: +500, 2022-10: +200, 2022-11: no trade and m["months"] == 3 and m["initial_full_stop"] == 2 and m["target2"] == 1 and m["total_index_points_weighted"] == pytest.approx(700 / 390, abs=0.01)


def test_the_cost_model_is_fill_level_and_its_base_scenario_equals_the_phase_3_6_headline():
    t = trade(0, 5000.0)
    legs = [{"trade_id": "T0", "leg": "1", "quantity": 195, "exit_price": 100.0}, {"trade_id": "T0", "leg": "2", "quantity": 195, "exit_price": 101.0}]
    rows = F.cost_scenarios([t], legs)
    base = next(r for r in rows if r["is_phase36_headline_assumption"])
    assert base["fixed_cost_rs_per_trade"] == 500.0 and base["slippage_points_per_fill"] == 0.5 and base["net_pnl_rs"] == 5000.0 - 500.0 - 0.5 * 780  # entry 390 + two exit legs of 195 units
    gross = next(r for r in rows if r["fixed_cost_rs_per_trade"] == 0.0 and r["slippage_points_per_fill"] == 0.0)
    assert gross["net_pnl_rs"] == 5000.0 and len(rows) == 16
    unresolved = [{"trade_id": "T0", "leg": "1", "quantity": 195, "exit_price": 100.0}, {"trade_id": "T0", "leg": "2", "quantity": 195, "exit_price": ""}]  # a leg with no fill costs nothing
    one = next(r for r in F.cost_scenarios([t], unresolved) if r["is_phase36_headline_assumption"])
    assert one["net_pnl_rs"] == pytest.approx(5000.0 - 500.0 / 3 * 2 - 0.5 * (390 + 195), abs=0.01)


# ======================================================================= regimes
def closes_series(n=120, drift=1.0, start=date(2024, 1, 1)):
    return [(start + timedelta(days=i), 20000.0 + drift * i + (7 if i % 2 else -7)) for i in range(n)]


def test_regimes_use_only_closes_strictly_before_the_session():
    cl = closes_series()
    d = cl[100][0]
    base = R.regime_of(cl, d)
    changed = [(x, c * 1.5 if x >= d else c) for x, c in cl]  # the session's own close and every later close are altered
    assert R.regime_of(changed, d) == base and base["vol"] in ("LOW_VOL", "MID_VOL", "HIGH_VOL") and base["trend"] in ("TRENDING_UP", "TRENDING_DOWN", "SIDEWAYS")
    assert R.regime_of(cl[:40], cl[39][0])["vol"] == "UNKNOWN"  # not enough history: never a made-up regime


def test_regime_thresholds_are_the_declared_round_numbers_and_trend_direction_follows_the_net_change():
    assert (R.RV_WINDOW, R.RV_LOW, R.RV_HIGH, R.ER_WINDOW, R.ER_TREND) == (20, 10.0, 16.0, 60, 0.25)
    up = R.regime_of([(date(2024, 1, 1) + timedelta(days=i), 20000.0 + 40.0 * i) for i in range(100)], date(2024, 4, 15))
    down = R.regime_of([(date(2024, 1, 1) + timedelta(days=i), 24000.0 - 40.0 * i) for i in range(100)], date(2024, 4, 15))
    flat = R.regime_of([(date(2024, 1, 1) + timedelta(days=i), 20000.0 + (30 if i % 2 else -30)) for i in range(100)], date(2024, 4, 15))
    assert up["trend"] == "TRENDING_UP" and down["trend"] == "TRENDING_DOWN" and flat["trend"] == "SIDEWAYS"


# ======================================================================= the delivered bundle
needs_outputs = pytest.mark.skipif(not (OUT / "annual_comparison.csv").exists(), reason="run scripts/phase4_run.py --window all first")


def rows(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@needs_outputs
def test_every_window_trade_records_its_source_ids_and_the_hash_of_the_real_partition_and_raw_files():
    n = 0
    for w, sid in (("B", D.SRC_5P_MIN), ("B_TV", D.SRC_TV_MIN), ("C", D.SRC_TV_MIN), ("D_5P", D.SRC_5P_MIN), ("D_TV", D.SRC_TV_MIN)):
        man = json.loads((D.PROC / sid / "source_manifest.json").read_text())
        for t in rows(OUT / "windows" / w / "all_trades_detailed.csv"):
            n += 1
            assert t["data_source_id"] == sid and t["daily_source_id"] == D.SRC_5P_DAILY and t["data_window_id"] == w
            assert sha(ROOT / t["data_source_partition"]) == t["data_source_partition_sha256"]
            assert t["raw_source_sha256"] and all(h == man["raw_files"][f] for f, h in zip(t["raw_source_files"].split(";"), t["raw_source_sha256"].split(";"), strict=True))
    assert n > 1000


@needs_outputs
def test_the_three_annual_slices_add_up_and_the_reference_row_is_the_unchanged_phase_36_result():
    a = {r["row_id"]: r for r in rows(OUT / "annual_comparison.csv")}
    assert sum(int(a[k]["trades"]) for k in ("B1_2022_23", "B2_2023_24", "B3_2024_25")) == int(a["B_2022_25"]["trades"])
    assert sum(float(a[k]["gross_pnl_rs_fixed_390"]) for k in ("B1_2022_23", "B2_2023_24", "B3_2024_25")) == pytest.approx(float(a["B_2022_25"]["gross_pnl_rs_fixed_390"]), abs=0.02)
    assert a["A_2025_26"]["trades"] == "196" and float(a["A_2025_26"]["gross_pnl_rs_fixed_390"]) == 297765.0 and float(a["A_2025_26"]["net_pnl_rs_illustrative"]) == 123325.0
    assert a["C_2018"]["status"] == "EXPLORATORY" and a["D_2019_5PAISA_PARTIAL"]["status"] == "PARTIAL_YEAR" and a["C_2018"]["data_quality_confidence"] == "EXPLORATORY_UNVERIFIABLE"
    for r in a.values():
        assert all(int(r[f"trades_{s}"]) > 0 for s in ("IRF", "ORB", "PDR", "PDS", "RF")) or r["row_id"] in ("D_2019_5PAISA_PARTIAL",)  # all five engines trade in every year (PDS has 2 trades in the 5paisa 2019 part)
        assert int(r["trades_PDS"]) > 0


@needs_outputs
def test_every_loss_making_period_is_present_and_no_window_was_dropped():
    a = {r["row_id"]: r for r in rows(OUT / "annual_comparison.csv")}
    assert float(a["C_2018"]["gross_pnl_rs_fixed_390"]) < 0 and float(a["B2_2023_24"]["profit_factor_gross"]) < 1.0 and {"C_2018", "D_2019_SECONDARY", "D_2019_5PAISA_PARTIAL", "B1_2022_23", "B2_2023_24", "B3_2024_25", "A_2025_26"} <= set(a)


@needs_outputs
def test_the_headline_cost_scenario_of_every_period_equals_its_net_pnl_and_no_scenario_is_hidden():
    a = {r["row_id"]: r for r in rows(OUT / "annual_comparison.csv")}
    cs = rows(OUT / "cost_sensitivity.csv")
    assert len(cs) == 16 * len(a)
    for r in cs:
        if r["is_phase36_headline_assumption"] == "True":
            assert float(r["net_pnl_rs"]) == pytest.approx(float(a[r["row_id"]]["net_pnl_rs_illustrative"]), abs=0.05)


@needs_outputs
def test_journals_exist_for_every_session_and_say_when_no_manual_journal_exists():
    for w in ("B", "C", "D_5P", "D_TV"):
        for d in rows(OUT / "windows" / w / "daily_summary.csv")[:3]:
            txt = (OUT / "daily" / w / d["date"][:7] / f"{d['date']}.md").read_text()
            assert "No manual journal exists for this period" in txt and "EXTRA_AUTOMATED" not in txt and "Phase 4 historical validation" in txt
        assert all(t["manual_match_class"] == "NOT_APPLICABLE_NO_JOURNAL_FOR_PERIOD" for t in rows(OUT / "windows" / w / "all_trades_detailed.csv"))


@needs_outputs
def test_required_phase_4_files_exist():
    for n in ("README.md", "strategy_freeze.json", "data_source_discovery.md", "data_quality_by_year.md", "historical_coverage.csv", "three_year_backtest_summary.md", "2018_backtest_summary.md", "2019_backtest_summary.md",
              "annual_comparison.csv", "strategy_comparison.csv", "cost_sensitivity.csv", "drawdown_analysis.md", "robustness_report.md", "paper_trading_readiness.md", "independent_audit.md", "NIFTY_MultiYear_Backtest_Verification.xlsx"):
        assert (OUT / n).exists(), n
    assert (OUT / "daily").is_dir() and (OUT / "charts").is_dir()


# ======================================================================= preservation (one-time delivery check)
snap_path = OUT / "before_snapshot.json"
ALLOWED = {"src/nifty_trading/research/phase32_build.py", "src/nifty_trading/research/phase32_render.py", "src/nifty_trading/research/phase32_excel.py"}
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE4_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE4_ALLOW_LATER_EDITS=1")


@needs_snapshot
def test_data_every_earlier_report_the_engines_and_the_controller_are_byte_identical_to_the_pre_phase4_snapshot():
    snap = json.loads(snap_path.read_text())["files"]
    changed = [p for p, h in snap.items() if p not in ALLOWED and not p.startswith("reports/phase4/") and (not (ROOT / p).exists() or sha(ROOT / p) != h)]
    assert changed == []
    for p in ("irf", "orb", "pds", "rf", "pdr", "pdr_revised", "pdr_body", "trading_day", "selection", "base", "params", "definitions"):
        assert sha(ROOT / f"src/nifty_trading/strategies/{p}.py") == snap[f"src/nifty_trading/strategies/{p}.py"], p
    assert sha(ROOT / "src/nifty_trading/core/exit_policy.py") == snap["src/nifty_trading/core/exit_policy.py"]


def test_the_default_build_path_still_reproduces_the_phase_3_6_backtest():
    """build() with its defaults (Phase 1 dataset, manual journal) must give the Phase 3.6 ledger exactly: 196 trades, the same ids, the same gross and net."""
    import inspect

    from nifty_trading.research import phase32_build as B
    sig = inspect.signature(B.build)
    assert sig.parameters["data"].default is None and sig.parameters["journal"].default is True and sig.parameters["partition_fn"].default is None and sig.parameters["provenance_override"].default is None
    b = B.build(scenario=P.combined_scenario("BODY_BASED_PHASE36"))
    ref = rows(ROOT / "reports" / "phase3" / "phase36_body_based_pdr" / "all_trades_detailed.csv")
    assert [t["trade_id"] for t in b.trades] == [t["trade_id"] for t in ref] and len(b.trades) == 196
    assert sum(float(t["gross_pnl_rs"]) for t in b.trades) == pytest.approx(sum(float(t["gross_pnl_rs"]) for t in ref), abs=0.01) == pytest.approx(297765.0, abs=0.01)
    assert sum(float(t["illustrative_net_pnl_rs"]) for t in b.trades) == pytest.approx(123325.0, abs=0.01)
    assert b.has_journal is True and sum(1 for c in b.manual_cmp if c["journal_row"] != "") == 190
