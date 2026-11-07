"""Phase 5: the frozen Phase 3.6 rules on BANKNIFTY and SENSEX index prices. Unit tests (index registry, windows, CLI, freeze enforcement, label handling, option-feasibility block, secondary-source loader, calendar
derivation, closing-auction detection, metrics, vendor sensitivity) on synthetic data; file-level tests on the delivered bundle (source columns and hashes, annual slices, journals, absence of any option number,
workbook, preservation of every NIFTY artefact)."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from nifty_trading.research import phase5 as F5
from nifty_trading.research import phase5_data as D5
from nifty_trading.research import phase5_report as R5
from nifty_trading.research.phase5_options import option_block

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5"


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


def minute_frame(day: date, start="09:15", n=375, base=100.0, step=0.01) -> pd.DataFrame:
    t0 = pd.Timestamp(f"{day} {start}", tz="Asia/Kolkata")
    close = [base + step * i for i in range(n)]
    return pd.DataFrame({"timestamp": [t0 + pd.Timedelta(minutes=i) for i in range(n)], "open": [c - 0.005 for c in close], "high": [c + 0.02 for c in close], "low": [c - 0.02 for c in close], "close": close, "volume": 0})


# ======================================================================= registry and windows
def test_the_index_registry_never_reuses_nifty_identifiers_or_directories():
    assert set(D5.INDEXES) == {"BANKNIFTY", "SENSEX"}
    for name, ix in D5.INDEXES.items():
        for p in (ix.raw_5p, ix.raw_sec_root, ix.proc, ix.instrument_file, ix.calendar_file):
            assert ix.key in str(p) and "nifty50" not in str(p) and "phase4" not in str(p), (name, p)
        assert len({ix.src_5p_min, ix.src_5p_daily, ix.src_sec_min}) == 3 and name in ix.src_5p_min
    assert D5.INDEXES["BANKNIFTY"].exchange_label == "NSE" and D5.INDEXES["SENSEX"].exchange_label == "BSE"


def test_windows_are_the_requested_periods_and_labelled_honestly():
    for name in D5.INDEXES:
        s = F5.specs_for(name)
        assert (s["M"].start, s["M"].end, s["M"].status, s["M"].minute_source) == (date(2022, 9, 1), date(2026, 8, 31), "DATA_VALIDATED", "5paisa")
        assert (s["C"].start, s["C"].end, s["C"].status, s["C"].minute_source) == (date(2018, 1, 1), date(2018, 12, 31), "EXPLORATORY", "secondary")
        assert s["D_5P"].status == "PARTIAL_YEAR" and s["D_5P"].start == date(2019, 3, 1) and s["D_TV"].status == "EXPLORATORY" and s["D_TV"].start == date(2019, 1, 1)
        assert s["MS"].status == "VENDOR_SENSITIVITY" and s["MS"].end == date(2024, 3, 22)
    assert "2018-03-08" in F5.specs_for("SENSEX")["C"].note and "2018-03-08" not in F5.specs_for("BANKNIFTY")["C"].note


def test_5paisa_minute_months_cover_the_main_window_plus_a_warmup_month_and_2019_from_march():
    assert D5.MINUTE_MONTHS_5P == [((2019, 3), (2019, 12)), ((2022, 8), (2026, 8))] and D5.DAILY_RANGE[0] == date(2017, 1, 1)


# ======================================================================= CLI and freeze
def test_cli_requires_index_and_the_frozen_config_and_offers_every_documented_window():
    cli = load_script("phase5_run")
    with pytest.raises(SystemExit):
        cli.parse_args(["--window", "all"])
    with pytest.raises(SystemExit):
        cli.parse_args(["--index", "BANKNIFTY", "--strategy-config", "other", "--window", "all"])
    with pytest.raises(SystemExit):
        cli.parse_args(["--index", "NIFTY", "--strategy-config", "phase36-frozen", "--window", "all"])  # NIFTY is not run by Phase 5
    for idx in ("BANKNIFTY", "SENSEX", "ALL"):
        for w in ("main", "vendor", "2018", "2019", "all", "custom"):
            assert cli.parse_args(["--index", idx, "--strategy-config", "phase36-frozen", "--window", w]).window == w
    assert cli.WINDOW_SETS["2019"] == ["D_5P", "D_TV"] and set(cli.WINDOW_SETS["all"]) == {"M", "MS", "C", "D_5P", "D_TV"}


def test_cli_refuses_a_foreign_output_directory_and_a_custom_window_needs_dates(capsys):
    cli = load_script("phase5_run")
    assert cli.main(["--index", "BANKNIFTY", "--strategy-config", "phase36-frozen", "--window", "main", "--out", str(ROOT / "reports" / "phase4")]) == 2
    assert cli.main(["--index", "BANKNIFTY", "--strategy-config", "phase36-frozen", "--window", "custom", "--out", str(OUT)]) == 2
    err = capsys.readouterr().err
    assert "refusing" in err and "--start" in err


def test_the_freeze_guard_is_the_phase4_guard_and_a_changed_file_or_parameter_stops_the_run(tmp_path):
    cli = load_script("phase5_run")
    fr = cli.verify_freeze()
    assert fr["frozen_configuration_id"].startswith("FROZEN-PHASE36-") and fr["parameters"]["stops"]["ORB"] == 30.0 and fr["parameters"]["targets_2"]["PDS"] == 70.0
    t = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    key = next(k for k in t["active_file_hashes"] if k.endswith("strategies/pdr_body.py"))
    t["active_file_hashes"][key] = "0" * 64
    p = tmp_path / "f.json"
    p.write_text(json.dumps(t))
    with pytest.raises(SystemExit) as e:
        cli.verify_freeze(p)
    assert "VIOLATED" in str(e.value) and "pdr_body.py" in str(e.value)
    t = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    t["parameters"]["trade_config"]["t1_points"] = 99.0
    p.write_text(json.dumps(t))
    with pytest.raises(SystemExit) as e2:
        cli.verify_freeze(p)
    assert "parameters.trade_config" in str(e2.value)


def test_the_phase5_run_does_not_edit_or_wrap_the_strategy_it_uses_the_phase36_scenario_unchanged():
    from nifty_trading.research import phase3 as P
    from nifty_trading.research import phase4 as F4
    assert F4.frozen_scenario() == P.combined_scenario("BODY_BASED_PHASE36")
    src = (ROOT / "src/nifty_trading/research/phase5.py").read_text()
    assert "F4.frozen_scenario()" in src and "stop" not in src.lower().split("def run_window")[1].split("def _rl_rows")[0].replace("stops", "")  # no stop / target value appears in the run function


# ======================================================================= labels and the option block
def test_relabel_changes_the_instrument_phrases_only_and_keeps_source_document_names():
    ix = D5.INDEXES["BANKNIFTY"]
    s = F5.relabel("Synthetic NIFTY 50 index-point P&L. Source: NIFTY_System_Trading_Strategy_Performance.docx. original NIFTY 50 one-minute bars. P&L = NIFTY spot points x quantity. BANKNIFTY stays.", ix)
    assert "BANKNIFTY index-point P&L" in s and "NIFTY_System_Trading_Strategy_Performance.docx" in s and "NIFTY 50" not in s and "NIFTY spot" not in s and "BANKNIFTY BANKNIFTY" not in s
    assert F5.relabel("instrument NIFTY 50 (index, not directly tradable; points are synthetic)", D5.INDEXES["SENSEX"]).startswith("instrument SENSEX (S&P BSE Sensex index")


def test_the_option_block_maps_direction_to_a_long_option_and_contains_no_number_that_looks_like_an_option_price():
    ix = D5.INDEXES["SENSEX"]
    none = option_block([], ix, None)
    assert "No index-signal trade" in none
    txt = option_block([{"trade_id": "20240102-1-IRF", "strategy": "IRF", "direction": "LONG"}, {"trade_id": "20240102-2-PDS", "strategy": "PDS", "direction": "SHORT"}], ix, None)
    assert "BUY CALL (CE)" in txt and "BUY PUT (PE)" in txt and "| no | no | no |" in txt and "not an option result" in txt
    assert not re.search(r"premium\s*[:=]?\s*\d|option P&L\s*[:=]?\s*[-+]?\d|strike\s*[:=]?\s*\d|expiry\s*[:=]?\s*\d{4}", txt, re.I)


# ======================================================================= secondary-source loader and calendar
class FakeIndex(D5.IndexSpec):
    root: Path = Path("/nonexistent")

    @property
    def raw_sec_root(self) -> Path:  # type: ignore[override]
        return self.root


def test_the_secondary_loader_parses_dd_mm_yyyy_localises_to_ist_removes_identical_duplicates_and_records_the_raw_file(tmp_path):
    ix = FakeIndex("fake", "FAKE", "Fake", "NSE", "x/y", "f.csv", ("Date", "Time"))
    object.__setattr__(ix, "root", tmp_path)
    d = tmp_path / "abc123"
    d.mkdir()
    csv_text = "Instrument,Date,Time,Open,High,Low,Close\nFake,02-01-2024,9:15:00,100.123,101,99,100\nFake,02-01-2024,09:15:00,100.123,101,99,100\nFake,02-01-2024,9:16:00,100,102,99,101\n"
    (d / "f.csv").write_text(csv_text)
    h = sha(d / "f.csv")
    (d / "manifest.json").write_text(json.dumps({"commit_sha": "abc123", "commit_date": "2024-01-01", "repository": "r", "repo_license_spdx": "MIT", "files": {"f.csv": {"status": "OK", "sha256": h, "git_blob_sha": "x", "bytes": len(csv_text)}}}))
    df, info = D5.load_secondary_minutes(ix)
    assert len(df) == 2 and str(df["timestamp"].dt.tz) == "Asia/Kolkata" and df["timestamp"].iloc[0].strftime("%H:%M") == "09:15"
    assert info["duplicate_rows_removed"] == 1 and info["conflicting_duplicate_timestamps"] == 0 and df["raw_file"].eq("f.csv").all() and info["raw_files"] == {"f.csv": h}
    assert df["open"].iloc[0] == 100.12  # prices are held to two decimals
    (d / "f.csv").write_text(csv_text + "x")  # a changed raw file is refused
    with pytest.raises(AssertionError):
        D5.load_secondary_minutes(ix)


def test_a_vendor_defect_in_one_source_is_not_a_special_session_but_an_evening_session_in_every_source_is():
    days = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
    daily = pd.DataFrame({"date": days, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})
    a = pd.concat([minute_frame(days[0]), minute_frame(days[1], start="09:19", n=371), minute_frame(days[2], start="18:15", n=60)], ignore_index=True)  # source A misses the opening bars on 3 Jan, evening session on 4 Jan
    b = pd.concat([minute_frame(days[0]), minute_frame(days[1]), minute_frame(days[2], start="18:15", n=60)], ignore_index=True)
    cov = {"A": [(days[0], days[2])], "B": [(days[0], days[2])]}
    cal, meta = D5.derive_calendar_index(daily, {"A": a, "B": b}, days[0], days[2], cov)
    assert days[1] not in cal.special_sessions and [x["date"] for x in meta["opening_bar_defects"]] == ["2024-01-03"]
    assert days[2] in cal.special_sessions and cal.special_sessions[days[2]].evaluable_by_strategies is False


def test_the_closing_auction_pattern_is_detected_only_when_15_16_to_15_26_is_one_flat_price():
    mod = load_script("phase5_build_data")
    frames = []
    for d, frozen in ((date(2026, 7, 1), False), (date(2026, 8, 3), True), (date(2026, 8, 4), True)):
        f = minute_frame(d)
        if frozen:
            m = (f["timestamp"].dt.hour * 60 + f["timestamp"].dt.minute)
            sel = (m >= 15 * 60 + 16) & (m <= 15 * 60 + 26)
            for c in ("open", "high", "low", "close"):
                f.loc[sel, c] = 123.0
        frames.append(f)
    ev = mod.closing_auction_evidence(pd.concat(frames, ignore_index=True))
    assert (ev["frozen_pattern_before"], ev["sessions_before_2026_08_03"], ev["frozen_pattern_from"], ev["sessions_from_2026_08_03"]) == (0, 1, 2, 2) and ev["first_session_with_pattern"] == "2026-08-03"


# ======================================================================= metrics
def fake_trade(i, strat, pts_, outcome, d="2024-01-02", direction="LONG", entry=50000.0):
    return {"trade_id": f"{d.replace('-', '')}-{i}-{strat}", "date": d, "fill_timestamp": f"{d} 10:{i:02d}", "trade_no_of_day": "1", "strategy": strat, "direction": direction, "outcome": outcome, "bars_held": "10", "entry_price": str(entry),
            "initial_stop": str(entry - 35), "target_1": str(entry + 27), "target_2": str(entry + 60), "gross_pnl_points_weighted": str(pts_), "gross_pnl_rs": str(pts_ * 390), "illustrative_net_pnl_rs": str(pts_ * 390 - 1000), "qty_total": "390"}


def test_index_metrics_use_points_drawdown_profit_factor_and_the_relative_scale_of_the_stop():
    tr = [fake_trade(1, "IRF", 30.0, "TARGET"), fake_trade(2, "IRF", -35.0, "INITIAL_FULL_STOP"), fake_trade(3, "ORB", -35.0, "INITIAL_FULL_STOP"), fake_trade(4, "PDR", 13.5, "T1_THEN_BUFFER_STOP")]
    legs = [{"trade_id": t["trade_id"], "leg": "1", "exit_reason": "TARGET_1" if t["outcome"] != "INITIAL_FULL_STOP" else "ORIGINAL_STOP_BEFORE_T1"} for t in tr] + \
           [{"trade_id": t["trade_id"], "leg": "2", "exit_reason": {"TARGET": "TARGET_2", "T1_THEN_BUFFER_STOP": "POST_T1_STOP_ENTRY_MINUS_PLUS_6"}.get(t["outcome"], "ORIGINAL_STOP_BEFORE_T1")} for t in tr]
    daily = [{"date": "2024-01-02", "confirmed_signals": "6", "fully_valid_signals": "5", "day_end_portfolio_state": "UNRESOLVED_EXECUTION"}]
    m = R5.metrics(tr, legs, daily, [], [{"strategy": "PDR", "failure_reason": "OPEN_NOT_STRICTLY_ABOVE_ZONE(x)"}])
    assert m["executed_trades"] == 4 and m["gross_index_points"] == pytest.approx(-26.5) and m["win_rate_pct"] == 50.0 and m["profit_factor_points"] == pytest.approx(43.5 / 70.0, abs=1e-4)
    assert m["max_drawdown_index_points"] == 70.0 and m["max_consecutive_losses"] == 2 and m["same_minute_conflict_days"] == 1 and m["t1_reached_pct"] == 50.0 and m["t2_reached_pct"] == 25.0 and m["initial_full_stop_pct"] == 50.0
    assert m["stop_pct_of_index"] == pytest.approx(35 / 50000 * 100, abs=1e-4) and m["t1_pct_of_index"] == pytest.approx(27 / 50000 * 100, abs=1e-4) and m["pdr_open_not_above_zone"] == 1
    assert m["gross_rs_fixed_390_synthetic"] == pytest.approx(-26.5 * 390)  # points x 390 = the synthetic rupee figure


def test_vendor_sensitivity_counts_identical_trades_and_those_only_one_source_has():
    base = fake_trade(1, "IRF", 10.0, "TARGET")
    for t in (base,):
        t.update({"method": "M1", "signal_candle_end": "10:01"})
    other = {**fake_trade(2, "RF", -35.0, "INITIAL_FULL_STOP"), "method": "M2", "signal_candle_end": "11:00"}
    only_b = {**fake_trade(3, "ORB", 5.0, "TARGET", d="2024-01-03"), "method": "M1", "signal_candle_end": "09:50"}
    day = lambda d: {"date": d}  # noqa: E731
    w = {"M": {"trades": [base, other], "daily": [day("2024-01-02"), day("2024-01-03")], "signals": []}, "MS": {"trades": [base, only_b], "daily": [day("2024-01-02"), day("2024-01-03")], "signals": []}}
    w["D_5P"], w["D_TV"] = {"trades": [], "daily": [], "signals": []}, {"trades": [], "daily": [], "signals": []}
    r = R5.vendor_sensitivity("BANKNIFTY", w)[0]
    assert (r["identical_trade_signals"], r["trades_only_5paisa"], r["trades_only_secondary"]) == (1, 1, 1) and r["points_on_trades_only_5paisa"] == -35.0 and r["points_on_trades_only_secondary"] == 5.0


def test_the_cumulative_chart_is_drawn_from_the_given_series():
    svg = R5.line_chart_svg({"NIFTY": [("2023-01-02", 0.0), ("2023-06-01", 100.0)], "BANKNIFTY": [("2023-01-02", 0.0), ("2023-06-01", -50.0)]}, "t", "points")
    assert svg.count("<polyline") == 2 and "NIFTY" in svg and "BANKNIFTY" in svg


# ======================================================================= delivered bundle (file level)
needs_outputs = pytest.mark.skipif(not (OUT / "comparison" / "cross_index_by_period.csv").exists(), reason="run scripts/phase5_run.py and phase5_compare.py first")


@needs_outputs
@pytest.mark.parametrize("name", ["BANKNIFTY", "SENSEX"])
def test_every_trade_records_index_source_ids_and_the_hash_of_the_real_partition_and_raw_files(name):
    ix = D5.INDEXES[name]
    for w, spec in F5.specs_for(name).items():
        src = F5.minute_source_id(ix, spec)
        sm = D5.source_manifest(ix, src)
        for t in rows(OUT / ix.key / "windows" / w / "all_trades_detailed.csv"):
            assert t["index"] == name and t["data_source_id"] == src and t["daily_source_id"] == ix.src_5p_daily
            assert sha(ROOT / t["data_source_partition"]) == t["data_source_partition_sha256"]
            rf = sm["partitions"][t["data_source_partition"]]["raw_files"]
            assert rf and t["raw_source_sha256"] == ";".join(sm["raw_files"][f] for f in rf)


@needs_outputs
@pytest.mark.parametrize("name", ["BANKNIFTY", "SENSEX"])
def test_every_evaluated_session_has_a_journal_with_the_option_block_and_no_option_number(name):
    ix = D5.INDEXES[name]
    n = 0
    for w in F5.specs_for(name):
        for d in rows(OUT / ix.key / "windows" / w / "daily_summary.csv"):
            txt = (OUT / ix.key / "daily" / w / d["date"][:7] / f"{d['date']}.md").read_text()
            n += 1
            assert "Option-execution feasibility" in txt and "NIFTY 50" not in txt
            assert not re.search(r"premium\s*[:=]?\s*\d|option P&L\s*[:=]?\s*[-+]?\d|strike\s*[:=]?\s*\d|expiry\s*[:=]?\s*\d{4}", txt.split("Option-execution feasibility")[-1], re.I)
    assert n > 1500
    cols = rows(OUT / ix.key / "trade_level_signals.csv")[0].keys()
    assert not [c for c in cols if re.search(r"option|premium|strike|delta", c, re.I)]


@needs_outputs
@pytest.mark.parametrize("name", ["BANKNIFTY", "SENSEX"])
def test_annual_slices_add_up_and_every_period_including_the_loss_making_ones_is_reported(name):
    a = {r["row_id"]: r for r in rows(OUT / name.lower() / "annual_comparison.csv")}
    assert {"M_2022_23", "M_2023_24", "M_2024_25", "M_2025_26", "M_ALL", "MS_2022_09_2024_03", "C_2018", "D_2019_5P_PARTIAL", "D_2019_SECONDARY"} <= set(a)
    parts = [a[k] for k in ("M_2022_23", "M_2023_24", "M_2024_25", "M_2025_26")]
    assert sum(int(p["executed_trades"]) for p in parts) == int(a["M_ALL"]["executed_trades"])
    assert sum(float(p["gross_index_points"]) for p in parts) == pytest.approx(float(a["M_ALL"]["gross_index_points"]), abs=0.02)
    assert a["M_ALL"]["status"] == "DATA_VALIDATED" and a["C_2018"]["status"] == "EXPLORATORY" and a["D_2019_5P_PARTIAL"]["status"] == "PARTIAL_YEAR"
    for r in a.values():
        assert float(r["gross_rs_fixed_390_synthetic"]) == pytest.approx(float(r["gross_index_points"]) * 390, abs=2.0)  # points are rounded to 0.01 in the table (0.005 x 390 = 1.95)


@needs_outputs
def test_the_cross_index_comparison_uses_the_phase4_and_phase36_nifty_tables_unchanged():
    ref = next(r for r in rows(OUT / "comparison" / "cross_index_by_period.csv") if r["index"] == "NIFTY" and r["row_id"] == "M_ALL")
    a = rows(ROOT / "reports/phase3/phase36_body_based_pdr/all_trades_detailed.csv")
    b = rows(ROOT / "reports/phase4/windows/B/all_trades_detailed.csv")
    assert int(ref["executed_trades"]) == len(a) + len(b) == 805
    assert float(ref["gross_index_points"]) == pytest.approx(sum(float(t["gross_pnl_points_weighted"]) for t in a + b), abs=0.02)


@needs_outputs
def test_required_phase_5_files_exist():
    top = ["README.md", "data_discovery.md", "data_quality_report.md", "cross_index_comparison.md", "independent_audit.md", "configuration_snapshot.json", "data_provenance.json", "before_snapshot.json"]
    per = ["annual_comparison.csv", "trade_level_signals.csv", "daily_summary.csv", "strategy_performance.csv", "entry_explanations.csv", "exit_explanations.csv", "cost_sensitivity.csv", "vendor_sensitivity.csv"]
    for n in top:
        assert (OUT / n).exists(), n
    for name in ("banknifty", "sensex"):
        for n in per + [f"{name}_backtest_summary.md", f"{name.upper()}_Daily_Verification.xlsx"]:
            assert (OUT / name / n).exists(), (name, n)
        assert (OUT / name / "daily").is_dir() and (OUT / name / "charts").is_dir()
    for n in ("option_data_availability.md", "option_contract_selection_decisions.md", "option_probe_results.json"):
        assert (OUT / "options_feasibility" / n).exists(), n
    assert (OUT / "comparison" / "cross_index_comparison.md").exists()


# ======================================================================= preservation (one-time delivery check)
snap_path = OUT / "before_snapshot.json"
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE5_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE5_ALLOW_LATER_EDITS=1")


@needs_snapshot
def test_every_nifty_artefact_every_earlier_report_and_every_tracked_file_is_byte_identical_to_the_pre_phase5_snapshot():
    snap = json.loads(snap_path.read_text())["hashes"]
    changed = [p for p, h in snap.items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    assert changed == []
    for p in ("irf", "orb", "pds", "rf", "pdr", "pdr_body", "trading_day", "selection", "base", "params", "definitions"):
        assert f"src/nifty_trading/strategies/{p}.py" in snap
    fr = json.loads((ROOT / "reports/phase4/strategy_freeze.json").read_text())
    assert all(sha(ROOT / p) == h for p, h in fr["active_file_hashes"].items())

