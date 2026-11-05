"""Phase 3.5: the combined five-strategy backtest with the revised PDR engine. Unit tests for the engine selection, the scenario definition, the command-line entry point and the
revised-PDR trade explanation; file-level tests check the delivered bundle and that nothing else changed (hash snapshot taken before the first Phase 3.5 edit)."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_phase32_explanations as E
from synthetic import ctx

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase32 as X
from nifty_trading.research import phase32_excel as XL
from nifty_trading.strategies import IRFStrategy, ORBStrategy, PDRStrategy, PDSStrategy, RFStrategy
from nifty_trading.strategies.pdr_revised import PDRRevisedStrategy, PDRRevisionConfig

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase35_combined"
PREV = E.PDR_PREV  # previous session: day high 110 (idx 2), zone A = [105, 110]


def load_cli():
    spec = importlib.util.spec_from_file_location("phase35_run", ROOT / "scripts" / "phase35_run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phase35_run"] = mod
    spec.loader.exec_module(mod)
    return mod


# ======================================================================= engine selection (the only functional change to the shared runner)
def test_legacy_selection_is_the_phase_3_0_engine_set_and_order():
    s = P.scenarios()["baseline"]
    es = P.make_engines(s.proposals, s.trade)
    assert [type(e) for e in es] == [IRFStrategy, ORBStrategy, PDRStrategy, PDSStrategy, RFStrategy]
    assert [type(e) for e in P.make_engines(s.proposals, s.trade, "LEGACY")] == [type(e) for e in es]


def test_revised_selection_swaps_only_the_pdr_slot_and_keeps_the_other_four_untouched():
    s = P.scenarios()["baseline"]
    es = P.make_engines(s.proposals, s.trade, "REVISED_PHASE34", PDRRevisionConfig())
    assert [type(e) for e in es] == [IRFStrategy, ORBStrategy, PDRRevisedStrategy, PDSStrategy, RFStrategy]
    assert [e.STRATEGY for e in es] == ["IRF", "ORB", "PDR", "PDS", "RF"]
    legacy = P.make_engines(s.proposals, s.trade)
    for a, b in zip(es, legacy, strict=True):
        if a.STRATEGY != "PDR":
            assert a.p == b.p and a.trade == b.trade  # identical configuration objects, not merely the same class


def test_an_unknown_pdr_engine_is_rejected():
    s = P.scenarios()["baseline"]
    with pytest.raises(ValueError):
        P.make_engines(s.proposals, s.trade, "SOMETHING_ELSE")


def test_the_combined_scenario_changes_nothing_but_the_pdr_engine():
    base, new = P.scenarios()["baseline"], P.combined_scenario()
    assert new.proposals == base.proposals and new.trade == base.trade  # stops, targets, lots, cutoff, forced exit, trend mode: all as in Phase 3.0
    assert new.pdr_engine == "REVISED_PHASE34" and new.key == "phase35_combined"
    rev = new.pdr_revision
    assert (rev.zone_candidate, rev.pattern_profile, rev.open_vs_zone) == ("A_DAY_HIGH_ANCHORED", "RESEARCH_DEFAULT", "ABOVE_ZONE")
    assert set(rev.patterns_enabled) == {"GOOD_GREEN_BODY", "LOWER_PRICE_REJECTION", "HAMMER"}
    leg = P.combined_scenario("LEGACY")
    assert leg.pdr_engine == "LEGACY" and leg.pdr_revision is None and leg.proposals == base.proposals and leg.trade == base.trade


def test_trade_rules_of_the_combined_scenario_are_the_approved_portfolio_rules():
    t = P.combined_scenario().trade
    assert (t.t1_points, t.total_lots, t.leg1_lots, t.post_t1_buffer_points) == (27.0, 6, 3, 6.0) and str(t.forced_exit_time) == "15:14:00"
    assert {s: t.t2_points(s) for s in P.STRATEGIES} == {"IRF": 60.0, "ORB": 60.0, "PDR": 70.0, "PDS": 70.0, "RF": 60.0}
    assert {s: t.stop_points(s) for s in P.STRATEGIES} == {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0}


def test_the_scenarios_dictionary_of_phase_3_0_is_unchanged_so_its_runner_still_writes_the_same_four_reports():
    assert list(P.scenarios()) == ["baseline", "ema_structure", "pdr_shelf", "sl40"]


# ======================================================================= command line
def test_cli_defaults_to_the_revised_engine_and_accepts_legacy_only_by_name():
    cli = load_cli()
    assert cli.parse_args([]).pdr_engine == "revised" and cli.ENGINES[cli.parse_args([]).pdr_engine] == "REVISED_PHASE34"
    assert cli.ENGINES[cli.parse_args(["--pdr-engine", "legacy"]).pdr_engine] == "LEGACY"
    with pytest.raises(SystemExit):
        cli.parse_args(["--pdr-engine", "bogus"])


def test_cli_refuses_to_write_into_an_earlier_phase_directory(capsys):
    cli = load_cli()
    for d in ("reports/phase3/baseline", "reports/phase3/phase32", "reports/phase3/phase34_pdr_revision"):
        assert cli.main(["--out", str(ROOT / d)]) == 2
    assert "refusing" in capsys.readouterr().err


# ======================================================================= the revised-PDR trade explanation
GAP_UP = [(115, 120, 112, 118), (118, 119, 108, 109), (109, 114, 108, 113)]  # open above the previous-day high 110, a test of the zone, then a green body closing at 113


def explain_revised(cands, prev=PREV):
    return E.explain_all(PDRRevisedStrategy, ctx(cands, prev=prev))


def test_a_revised_pdr_trade_is_explained_with_numbers_statuses_and_no_failed_check():
    [(tr, ex, _)] = explain_revised(GAP_UP)
    assert tr.signal.method == "PDR" and not ex.mismatches and not [c for c in ex.checks if c.result == "FAIL"]
    ids = {c.rule_id for c in ex.checks}
    assert {"PDR-004", "PDR-A01", "PDR-A03", "PDR-A03a", "PDR-A04", "PDR-A04a", "PDR-A04b", "PDR-A04c", "PDR-A05", "PDR-A06", "PDR-A04x"} <= ids
    z = E.by_rule(ex, "PDR-A01")[0]
    assert "zone [105.00 (body top), 110.00 (wick high)]" in z.observed and z.rule_status == "AUTHOR_APPROVED"
    close = E.by_rule(ex, "PDR-A05")[0]
    assert "close 113.00 vs zone ceiling 110.00: +3.00 points" in close.observed and close.result == "PASS"
    assert E.by_rule(ex, "PDR-A04a")[0].result == "PASS" and "body" in E.by_rule(ex, "PDR-A04a")[0].observed
    assert E.by_rule(ex, "PDR-A04b")[0].result == "NOT_APPLICABLE"  # a pattern that does not pass is not an error (OR logic)
    assert E.by_rule(ex, "PDR-A03a")[0].rule_status == "PROPOSED_FOR_REVIEW"  # the open-above-zone requirement is NOT presented as approved
    assert E.by_rule(ex, "PDR-A04x")[0].result == "UNRESOLVED" and "not approved by the strategy author" in ex.setup_summary
    assert ex.levels["zone"][:2] == (105, 110)


def test_the_legacy_explainer_is_still_used_for_the_legacy_engine():
    [(tr, ex, _)] = E.explain_all(PDRStrategy, ctx([(115, 120, 112, 118), (118, 119, 108, 109), (109, 113, 108, 112)], prev=PREV))
    assert "PDR-002" in {c.rule_id for c in ex.checks} and "PDR-A01" not in {c.rule_id for c in ex.checks}


def test_a_zero_height_zone_is_disclosed_as_unresolved_not_reported_as_a_failure():
    prev = {"cands": [(100, 101, 99, 100), (100, 102, 100, 101), (101, 110, 100, 110), (110, 106, 98, 100), (100, 104, 99, 101), (101, 103, 100, 102)], "close": 102.0}  # the day-high candle closes ON its high
    [(tr, ex, _)] = explain_revised([(115, 120, 112, 118), (118, 119, 108, 109), (109, 114, 108, 113)], prev)
    z = E.by_rule(ex, "PDR-003")[0]
    assert z.result == "UNRESOLVED" and "LINE" in z.observed and not ex.mismatches


def test_every_revision_rule_has_a_status_label_in_the_explainer_tables():
    for rid in ("PDR-A01", "PDR-A04", "PDR-A05", "PDR-A05a", "PDR-A03a", "PDR-A06"):
        assert X.rule_status(rid) in {"AUTHOR_APPROVED", "OWNER_INTERPRETATION", "PROPOSED_FOR_REVIEW", "USER_APPROVED", "PRESERVED_FROM_PHASE2"}
        assert X.definition_status(rid) != "NOT_A_REGISTRY_RULE" and X.rule_source(rid).startswith("PDR revision rules")


def test_the_configuration_id_changes_only_when_a_pdr_revision_is_supplied():
    s = P.scenarios()["baseline"]
    legacy_id = X.config_id(s.proposals, s.trade, "baseline")
    assert legacy_id == X.config_id(s.proposals, s.trade, "baseline", None)  # every earlier id is unchanged
    assert X.config_id(s.proposals, s.trade, "baseline", PDRRevisionConfig()) != legacy_id
    assert X.config_id(s.proposals, s.trade, "x", PDRRevisionConfig()) != X.config_id(s.proposals, s.trade, "x", replace(PDRRevisionConfig(), pattern_profile="EXAMPLE_LENIENT"))


# ======================================================================= Excel cell limit
def test_text_longer_than_the_excel_cell_limit_is_truncated_visibly_and_short_text_is_untouched():
    long = "x" * 40000
    cut = XL.cell_text(long)
    assert len(cut) <= 32767 and cut.endswith("full text in the CSV file]") and XL.cell_text("short") == "short" and XL.cell_text(12.5) == 12.5


# ======================================================================= delivered files
needs_outputs = pytest.mark.skipif(not (OUT / "all_trades_detailed.csv").exists(), reason="run scripts/phase35_run.py first")


def rows(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


@needs_outputs
def test_every_required_file_is_present_and_the_workbook_cells_respect_the_excel_limit():
    for n in ("backtest_summary.md", "daily_summary.csv", "all_trades_detailed.csv", "trade_entry_conditions.csv", "trade_exits_detailed.csv", "manual_journal_comparison.csv", "strategy_performance.csv",
              "NIFTY_Daily_Trade_Verification.xlsx", "configuration_snapshot.json", "independent_audit.md"):
        assert (OUT / n).exists(), n
    assert (OUT / "daily").is_dir() and (OUT / "charts").is_dir()
    import openpyxl
    wb = openpyxl.load_workbook(OUT / "NIFTY_Daily_Trade_Verification.xlsx", read_only=True)
    longest = max((len(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str)), default=0)
    assert longest <= 32767


@needs_outputs
def test_one_journal_per_evaluable_session_and_one_chart_per_executed_trade():
    daily, trades = rows("daily_summary.csv"), rows("all_trades_detailed.csv")
    assert len(daily) == 247 and all((OUT / "daily" / r["date"][:7] / f"{r['date']}.md").exists() for r in daily)
    assert all((OUT / "charts" / f"{t['trade_id']}.svg").exists() for t in trades)
    assert len(list((OUT / "charts").glob("*.svg"))) == len(trades)


@needs_outputs
def test_the_ledger_obeys_the_portfolio_rules_and_every_strategy_was_traded():
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
        assert t["qty_total"] == "390" and t["qty_leg1"] == "195" and t["checks_fail"] == "0" and not t["recomputation_mismatches"]
        assert t["signal_verification_status"] != "VERIFIED"  # nothing is presented as source-verified while rules rest on proposals


@needs_outputs
def test_strategy_performance_adds_up_and_the_comparison_names_both_runs():
    perf = {r["strategy"]: r for r in rows("strategy_performance.csv")}
    trades = rows("all_trades_detailed.csv")
    assert int(perf["ALL"]["entries"]) == len(trades) == sum(int(perf[s]["entries"]) for s in P.STRATEGIES)
    assert abs(float(perf["ALL"]["gross_pnl_rs"]) - sum(float(t["gross_pnl_rs"]) for t in trades)) < 0.01
    cmp = {r["strategy"]: r for r in rows("comparison_vs_phase30.csv")}
    assert cmp["ALL"]["phase30_trades"] == "213" and int(cmp["ALL"]["phase35_trades"]) == len(trades)
    assert cmp["IRF"]["delta_trades"] == str(int(cmp["IRF"]["phase35_trades"]) - int(cmp["IRF"]["phase30_trades"]))


@needs_outputs
def test_the_configuration_snapshot_labels_the_pdr_assumptions_as_provisional_and_not_author_approved():
    cfg = json.loads((OUT / "configuration_snapshot.json").read_text())
    assert cfg["pdr_engine"] == "REVISED_PHASE34" and cfg["pdr_revision_config"]["zone_candidate"] == "A_DAY_HIGH_ANCHORED"
    assert "NOT" in cfg["pdr_provisional_assumptions"] or "provisional" in cfg["pdr_provisional_assumptions"]
    assert cfg["pdr_revision_rule_status"]["PDR-A03a"] == "PROPOSED_FOR_REVIEW" and cfg["pdr_revision_rule_status"]["PDR-A05"] == "AUTHOR_APPROVED"
    assert cfg["targets_2"]["PDR"] == 70.0 and cfg["stops"]["ORB"] == 30.0 and cfg["controller"]["entry_cutoff"] == "13:00:00 IST" and cfg["controller"]["max_entries_per_day"] == 2


# ======================================================================= nothing else changed (one-time delivery check)
snap_path = OUT / "before_snapshot.json"
ALLOWED = {"src/nifty_trading/research/phase3.py", "src/nifty_trading/research/phase31.py", "src/nifty_trading/research/phase32.py", "src/nifty_trading/research/phase32_build.py",
           "src/nifty_trading/research/phase32_render.py", "src/nifty_trading/research/phase32_excel.py", "tests/test_phase34_pdr_revision.py"}
# One-time delivery check; a later phase that legitimately edits earlier files should set PHASE35_ALLOW_LATER_EDITS=1 (or retire the test) and must not refresh the snapshot.
needs_snapshot = pytest.mark.skipif(not snap_path.exists() or os.environ.get("PHASE35_ALLOW_LATER_EDITS") == "1", reason="before_snapshot.json missing or PHASE35_ALLOW_LATER_EDITS=1")


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


@needs_snapshot
def test_data_earlier_reports_engines_and_the_controller_are_byte_identical_to_the_pre_phase35_snapshot():
    snap = json.loads(snap_path.read_text())["files"]
    changed = [p for p, h in snap.items() if p not in ALLOWED and (not (ROOT / p).exists() or sha(p) != h)]
    assert changed == []
    for p in ("src/nifty_trading/strategies/irf.py", "src/nifty_trading/strategies/orb.py", "src/nifty_trading/strategies/pds.py", "src/nifty_trading/strategies/rf.py", "src/nifty_trading/strategies/pdr.py",
              "src/nifty_trading/strategies/pdr_revised.py", "src/nifty_trading/strategies/trading_day.py", "src/nifty_trading/core/exit_policy.py"):
        assert sha(p) == snap[p], p
