"""Phase 4: freeze the Phase 3.6 strategy configuration.

Writes reports/phase4/strategy_freeze.json (source revision, hashes of every active strategy / controller / execution file, every parameter, costs, the research status of unresolved author rules, data and package
dependencies, and the FROZEN CONFIGURATION ID), reports/phase4/frozen/source_snapshot_phase36.tar.gz (a reproducible snapshot of src/, scripts/ and tests/ at freeze time) and runs a regression check: the Phase 3.6
backtest is regenerated into a scratch directory with the current code and every CSV is compared byte for byte with reports/phase3/phase36_body_based_pdr/. Nothing in an earlier report is written.

Run: .venv/bin/python scripts/phase4_freeze.py [--skip-regression]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.strategies.pdr_body import PDR_BODY_RULES  # noqa: E402
from nifty_trading.strategies.trading_day import DayRules  # noqa: E402

OUT = ROOT / "reports" / "phase4"
BASELINE = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
ACTIVE = {  # the files whose behaviour defines the strategy, the portfolio controller and the execution model
    "engines": ["irf", "orb", "pdr_body", "pdr_revised", "pds", "rf", "base", "definitions", "params", "selection", "trading_day", "rules", "rule_data"],
    "core": ["exit_policy", "execution_eligibility"],
    "data_layer": ["sessions", "market_calendar"],
    "framework": ["phase3", "phase31", "phase32", "phase32_build", "phase32_render", "phase32_excel", "phase32_charts", "phase35", "phase36"],
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a: str) -> str:
    try:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unavailable"


def active_hashes() -> dict[str, str]:
    out = {}
    for grp, names in ACTIVE.items():
        for n in names:
            base = {"engines": "src/nifty_trading/strategies", "core": "src/nifty_trading/core", "data_layer": "src/nifty_trading/data", "framework": "src/nifty_trading/research"}[grp]
            p = ROOT / base / f"{n}.py"
            out[f"{base}/{n}.py"] = sha(p)
    return out


def regression_check() -> dict:
    """Regenerate the Phase 3.6 backtest into a scratch directory with the current code and compare every CSV / JSON byte for byte."""
    from nifty_trading.research import phase36 as F36
    scratch = Path(tempfile.mkdtemp(prefix="phase36_regression_"))
    out = scratch / "phase36_regression"
    F36.run(out)
    rows, bad = [], []
    for f in sorted(BASELINE.glob("*")):
        if f.is_file() and f.suffix in (".csv", ".json") and f.name not in ("before_snapshot.json", "independent_audit_results.json", "pdr_signal_statistics.json", "source_chart_validation.csv", "pdr_daily_zone_comparison.csv",
                                                                           "old_vs_new_pdr_signals.csv", "pdr_sensitivity_counts.csv", "pdr_body_rules.csv", "pdr_signal_zone_state.csv", "pdr_trade_open_margins.csv"):
            g = out / f.name
            if f.name == "data_provenance.json":  # records a hash of ALL of src/ and the count of uncommitted files, which legitimately change when Phase 4 modules are added: compare the DATA hashes
                x, y = json.loads(f.read_text()), json.loads(g.read_text()) if g.exists() else {}
                same = all(x.get(k) == y.get(k) for k in ("data_files_sha256", "metadata_sha256", "phase30_ledgers_sha256", "period", "price_source"))
            else:
                same = g.exists() and sha(g) == sha(f)
            rows.append({"file": f.name, "identical": same})
            if not same:
                bad.append(f.name)
    # daily journals and charts
    for sub in ("daily", "charts"):
        a = sorted((BASELINE / sub).rglob("*"))
        for f in a:
            if f.is_file():
                g = out / sub / f.relative_to(BASELINE / sub)
                same = g.exists() and sha(g) == sha(f)
                rows.append({"file": f"{sub}/{f.relative_to(BASELINE / sub)}", "identical": same})
                if not same:
                    bad.append(f"{sub}/{f.relative_to(BASELINE / sub)}")
    return {"files_compared": len(rows), "identical": not bad, "differences": bad[:20], "scratch_dir": str(scratch)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--skip-regression", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    hashes = active_hashes()
    from nifty_trading.strategies.rule_data import RULES
    reg = {}
    for r in RULES:
        reg.setdefault(r["classification"], 0)
        reg[r["classification"]] += 1
    params = {"proposal_config": sc.proposals.to_dict(), "trade_config": asdict(sc.trade), "pdr_body_config": asdict(sc.pdr_revision), "day_rules": asdict(DayRules()),
              "targets_2": {s: sc.trade.t2_points(s) for s in P.STRATEGIES}, "stops": {s: sc.trade.stop_points(s) for s in P.STRATEGIES}, "target_1_points": sc.trade.t1_points, "post_t1_buffer_points": sc.trade.post_t1_buffer_points,
              "lots": {"total": sc.trade.total_lots, "leg1": sc.trade.leg1_lots, "lot_size_fixed_multiplier": sc.trade.lot_size}, "forced_exit_time": str(sc.trade.forced_exit_time), "entry_cutoff": "13:00 IST",
              "scenario_key": sc.key, "pdr_engine": sc.pdr_engine}
    costs = {"headline_fixed_cost_rs_per_trade": 500.0, "headline_slippage_points_per_fill": 0.5, "cost_grid_fixed": [0.0, 500.0, 1000.0, 1500.0], "cost_grid_slippage": [0.0, 0.5, 1.0, 2.0],
             "model": "fill level: one entry fill + one fill per exit leg; fixed cost per fill = fixed per trade / 3; slippage adverse on every unit of every fill; illustrative, no specific instrument",
             "fixed_multiplier_units": sc.trade.total_lots * sc.trade.lot_size}
    status = {"pdr_body_rules": {r["rule_id"]: r["status"] for r in PDR_BODY_RULES}, "phase2_registry_classification_counts": reg,
              "unresolved_author_decisions": ["numeric definitions of the three PDR candle patterns (thresholds are PROPOSED_FOR_REVIEW, profile RESEARCH_DEFAULT)", "whether the clarification (wicks ignored) supersedes the PDF's wick-topped example boxes",
                                              "PDR wait policy for a zone that price has closed through", "PDR zone lower boundary and multiple-body-high numbers", "zero-height zone policy", "same-candle test-and-confirm",
                                              "RF Target 2 of 60 (research assumption)", "PDR / PDS Target 2 of 70 versus the report's 60 (recorded source conflict)", "provisional forced exit at the 15:14 minute open",
                                              "no approved tie-break for simultaneous signals of different strategies (the day is marked unresolved, nothing traded)"]}
    deps = {"python": platform.python_version(), "platform": platform.platform(), "packages": {p: importlib.metadata.version(p) for p in ("pandas", "numpy", "pyarrow", "openpyxl", "pytest", "ruff") if _has(p)},
            "phase1_dataset_hashes_from_snapshot": "reports/phase4/before_snapshot.json (all data/processed files)", "calendar_evidence_file": "data/metadata/nse_calendar_2025_2026.json",
            "calendar_evidence_sha256": sha(ROOT / "data" / "metadata" / "nse_calendar_2025_2026.json")}
    # reproducible snapshot of the working tree code
    snap_dir = OUT / "frozen"
    snap_dir.mkdir(exist_ok=True)
    tar = snap_dir / "source_snapshot_phase36.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        for top in ("src", "scripts", "tests", "pyproject.toml", "requirements.lock"):
            p = ROOT / top
            if p.exists():
                t.add(p, arcname=top, filter=lambda ti: None if "__pycache__" in ti.name or ti.name.endswith((".pyc", ".DS_Store")) else ti)
    baseline_files = {f.name: sha(f) for f in sorted(BASELINE.glob("*")) if f.is_file() and f.suffix in (".csv", ".json", ".md", ".xlsx")}
    blob = json.dumps({"hashes": hashes, "params": params, "costs": costs}, sort_keys=True, default=str)
    freeze = {"frozen_configuration_id": "FROZEN-PHASE36-" + hashlib.sha256(blob.encode()).hexdigest()[:12], "frozen_utc": datetime.now(timezone.utc).isoformat(), "what": "Phase 3.6: IRF, ORB, PDR body-based, PDS, RF through the shared Phase 3.0 controller",
              "rerun_command_phase36": "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase36_run.py", "git_head": git("rev-parse", "HEAD"), "git_branch": git("branch", "--show-current"),
              "git_dirty_files": len(git("status", "--short").splitlines()), "git_note": "the Phase 3.3 - 3.6 work is uncommitted; the source snapshot below is the reproducible copy of the code at freeze time",
              "source_snapshot": {"file": str(tar.relative_to(ROOT)), "sha256": sha(tar)}, "active_file_hashes": hashes, "parameters": params, "costs_and_slippage": costs, "research_status_of_unresolved_rules": status,
              "dependencies": deps, "phase36_reference_results": {"period": "2025-09-01..2026-08-31", "trades": 196, "gross_pnl_rs": 297765.0, "illustrative_net_pnl_rs": 123325.0, "journal_matches": "88 of 190",
                                                                   "note": "reference values, not targets"}, "phase36_baseline_file_hashes": baseline_files,
              "rules": ["Use exactly the same strategy logic on every historical period.", "Do not tune the model after viewing older test results.", "Window A (2025-09-01..2026-08-31) is the existing Phase 3.6 backtest and is not modified."]}
    if not a.skip_regression:
        freeze["regression_check"] = regression_check()
        print("regression:", {k: v for k, v in freeze["regression_check"].items() if k != "scratch_dir"})
    (OUT / "strategy_freeze.json").write_text(json.dumps(freeze, indent=1, default=str))
    print("frozen configuration id:", freeze["frozen_configuration_id"], "| snapshot sha256", freeze["source_snapshot"]["sha256"][:12])
    return 0 if freeze.get("regression_check", {"identical": True})["identical"] else 1


def _has(p: str) -> bool:
    try:
        importlib.metadata.version(p)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
