"""Independent package consistency and preservation checks. No simulation."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"


def rd(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def main():
    s = json.loads((OUT / "audit_summary.json").read_text())
    checks, limitations = [], []

    def check(name, passed, observed):
        checks.append({"check": name, "passed": bool(passed), "observed": observed})

    required = ["README.md", "orb_original_source_rules.md", "orb_source_to_code_mapping.csv", "orb_implementation_line_by_line.md", "orb_all_entry_predicates.csv", "orb_13_handwritten_disputes.csv", "orb_all_manual_journal_dates.csv", "orb_vs_irf_selection_timeline.csv", "orb_missing_trade_root_causes.csv", "orb_level_construction_comparison.md", "orb_moving_average_investigation.md", "orb_candle_strength_investigation.md", "orb_candidate_signal_differences.csv", "orb_implementation_defects.md", "orb_required_author_clarifications.md", "ORB_Forensic_Verification.xlsx", "charts", "daily"]
    check("Requested evidence artifacts exist", all((OUT / n).exists() for n in required), required)
    dates = rd("orb_all_manual_journal_dates.csv")
    dispute = rd("orb_13_handwritten_disputes.csv")
    check("Journal date rows 89 per configuration", all(len([r for r in dates if r["config"] == k]) == 89 for k in "ABC"), len(dates))
    check("13 distinct handwritten dates per configuration", all(len({r["date"] for r in dispute if r["config"] == k}) == 13 for k in "ABC"), len(dispute))
    check("No author direction or exact level invented", all(r["manual_direction"] == "UNKNOWN" and r["manual_level"] == "UNKNOWN" for r in dates), len(dates))
    focus = {r["date"] for r in dates} | {r["date"] for r in dispute}
    check("Every focus date has daily page", all((OUT / "daily" / f"{d}.md").exists() for d in focus), len(focus))
    eval_dates = {r["date"] for r in rd("orb_method_paths.csv")}
    check("Every evaluable focus date has raw1m/5m/prior5/chart", all(all((OUT / folder / f"{d}{suffix}").exists() for folder, suffix in (("daily", "_1m.csv"), ("daily", "_5m.csv"), ("daily", "_prior5_sessions.csv"), ("charts", ".svg"))) for d in eval_dates), len(eval_dates))
    malformed = []
    for path in (OUT / "charts").glob("*.svg"):
        try:
            ET.parse(path)
        except ET.ParseError:
            malformed.append(path.name)
    check("All SVGs parse", not malformed, malformed)
    for key in ("independent_signal_parity_failures", "orb_prefix_failures", "stored_signal_disagreements", "ledger_signal_or_fill_failures", "first_selection_failures"):
        check(key, not s[key], s[key])
    check("Nearest-inner reconstruction independently matches optional engine across all247 sessions", s.get("nearest_inner_independent_parity_sessions") == 247, s.get("nearest_inner_independent_parity_sessions"))
    check("Independent raw5m OHLC and EMA checks", not s["data_verification"]["failures"], s["data_verification"])
    # Snapshot identity is evidence, not accepted by assertion: compare each
    # actual file with its frozen-source hash and current input manifest.
    manifest = json.loads((ROOT / "reports/phase5/phase55_combined_backtest/configuration_manifest.json").read_text())
    drift = []
    for key in ("frozen_active_file_hashes", "phase5_candidate_file_hashes"):
        for name, digest in manifest[key].items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            if actual != digest:
                drift.append(name)
    check("Frozen and candidate strategy files match original Phase5.5 manifest", not drift, drift)
    input_drift = [r["path"] for r in rd("source_inventory.csv") if hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest() != r["sha256"]]
    check("Audited PDFs, journal, data and ledgers unchanged since measured", not input_drift, input_drift)
    # Verify original ledger exits and protective distances against actual bars;
    # do not decide which exit would occur, or calculate any outcomes/P&L.
    with open(ROOT / "reports/phase5/phase55_combined_backtest/all_executed_trades.csv", newline="") as f:
        ledger = list(csv.DictReader(f))
    exit_issues, target_issues, conservative_target_fills = [], [], []
    for d in eval_dates:
        raw = pd.read_csv(OUT / "daily" / f"{d}_1m.csv")
        raw["clock"] = raw.timestamp.str.slice(11, 16)
        for t in [r for r in ledger if r["date"] == d]:
            sign = 1 if t["direction"] == "LONG" else -1
            entry = float(t["entry_price"])
            stop = 30 if t["strategy"] == "ORB" else 35
            t2 = 70 if t["strategy"] in ("PDR", "PDS") else 60
            if any(abs(float(t[key])-value) > 1e-7 for key, value in (("initial_stop", entry-sign*stop), ("target_1", entry+sign*27), ("target_2", entry+sign*t2))):
                target_issues.append(t["config"]+" "+t["trade_id"])
            for leg in (1, 2):
                clock, px = t[f"leg{leg}_exit_time"], t[f"leg{leg}_exit_price"]
                if not clock or not px:
                    continue
                bar = raw[raw.clock == clock]
                within = len(bar) == 1 and float(bar.low.iloc[0])-1e-7 <= float(px) <= float(bar.high.iloc[0])+1e-7
                if not within:
                    target_level = float(t["target_1"] if leg == 1 else t["target_2"])
                    expected_gap_target = (len(bar) == 1 and abs(float(px)-target_level) < 1e-7
                                           and sign * (float(bar.open.iloc[0])-target_level) > 0)
                    detail = {"config": t["config"], "trade": t["trade_id"], "date": d, "leg": leg, "clock": clock, "ledger_price": px,
                              "bar_open": float(bar.open.iloc[0]) if len(bar) else None,
                              "bar_high": float(bar.high.iloc[0]) if len(bar) else None,
                              "bar_low": float(bar.low.iloc[0]) if len(bar) else None}
                    if expected_gap_target:
                        conservative_target_fills.append({**detail, "interpretation": "Existing conservative target-at-level fill outside gap bar; not an observed traded price", "source": "core/exit_policy.py:229"})
                    else:
                        exit_issues.append(detail)
    check("Chart ledger stop and T1/T2 arithmetic", not target_issues, target_issues)
    check("Chart exit prices satisfy raw-bar range or documented conservative gap-target convention", not exit_issues, {"unexpected": exit_issues, "conservative_target_fills": len(conservative_target_fills)})
    if conservative_target_fills:
        with open(OUT / "ledger_target_gap_conventions.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(conservative_target_fills[0]))
            w.writeheader()
            w.writerows(conservative_target_fills)
    # XLSX read-only verification is allowed; authoring remains artifact-tool.
    value_book = openpyxl.load_workbook(OUT / "ORB_Forensic_Verification.xlsx", read_only=True, data_only=True)
    formula_book = openpyxl.load_workbook(OUT / "ORB_Forensic_Verification.xlsx", read_only=False, data_only=False)
    expected = json.loads((OUT / "workbook_data.json").read_text())["expected"]
    actual = {k: [value_book["Overview"].cell(i+5, j).value for j in range(2, 10)] for i, k in enumerate("ABC")}
    check("Exported XLSX cached summary equals independent counts", actual == expected, actual)
    check("Exported XLSX retains COUNTIFS formulas", all(str(formula_book["Overview"].cell(i, 2).value).startswith("=COUNTIFS(") for i in (5, 6, 7)), "B5:B7")
    check("Exported XLSX Journal has all267 configuration/date rows", formula_book["Journal"].max_row == 271, formula_book["Journal"].max_row)
    payload = json.loads((OUT / "workbook_data.json").read_text())
    expected_candidate_rows = len(next(x for x in payload["sheets"] if x["name"] == "Candidates")["rows"])
    check("Exported workbook includes every isolated candidate difference", formula_book["Candidates"].max_row == expected_candidate_rows + 4, {"expected": expected_candidate_rows, "actual": formula_book["Candidates"].max_row - 4})
    errors = []
    for ws in value_book:
        for row in ws.iter_rows():
            for c in row:
                if c.data_type == "e":
                    errors.append((ws.title, c.coordinate, c.value))
    check("Exported XLSX has no error cells", not errors, errors[:10])
    check("Workbook table freezes retained", formula_book["Journal"].freeze_panes is not None, str(formula_book["Journal"].freeze_panes))
    value_book.close()
    formula_book.close()
    tests = (OUT / "pytest_full.log").read_text()
    ruff = (OUT / "ruff_full.log").read_text()
    complete = re.search(r"^.*\d+ passed.*in [\d.]+s.*$", tests, flags=re.MULTILINE)
    check("Full pytest suite finished successfully", bool(complete) and not any(word in complete.group(0) for word in (" failed", " error")), complete.group(0) if complete else "STILL RUNNING")
    check("Full ruff check passes", "All checks passed!" in ruff, ruff.strip())
    limitations += [
        "The same investigator performed this independent reconstruction and self-review; no second human or agent review is claimed.",
        "No exact author direction, level, trendline or entry price is recorded for the13 disputes or journal rows. No profitability-based choice or objectively proven missed author trade is asserted.",
        "Gap figures support candle crossing, while part of wording supports open crossing; indicator identity and excessive extension remain unresolved.",
        "A/B/C strategy signals and first-entry choice were freshly verified. Existing ledger exits were range/arithmetic checked; no new exit walk, P&L or second-trade outcome calculation was run.",
        "The requested full pytest suite includes existing baseline historical-regression tests. No candidate profitability backtest or new profitability report was run.",
        "Six ledger target fills (two ORB trades repeated in A/B/C) lie outside their exit minute's traded range because the existing model conservatively fills a gapped target at its level. These are model fills, not observed prices; ledger_target_gap_conventions.csv records the actual bars. Previous ledgers are preserved.",
        "All13 PDF source pages and6 handwritten pages were visually inspected. All7 workbook sheets were rendered/reviewed; four representative historical charts were inspected at full size. All87 SVGs were parsed and structurally checked, not87 separate human chart interpretations.",
        "Native Excel was not opened. Artifact-tool summary recalculation reacted to a changed Journal signal and was restored; exported cached counts/formulas were read back independently.",
        "Historical contexts use offline full-session quality checks. Real-time adapter/broker timing is outside the verified path; no paper/live orders were placed.",
        "Phase5.7 was concurrently developed by another process. This audit never writes its paths; changes by that other process are not attributed to this audit.",
    ]
    result = {"checks": checks, "limitations": limitations, "all_passed": all(r["passed"] for r in checks)}
    (OUT / "independent_review_results.json").write_text(json.dumps(result, indent=2))
    lines = ["# Independent verification and self-review", "", "Fresh reconstruction challenged the previous reports rather than accepting their conclusions. This file records a separate consistency review by the same investigator; no second reviewer is implied.", "", "| Check | Result | Observed |", "|---|---|---|"]
    lines += [f"| {r['check']} | {'PASS' if r['passed'] else 'PENDING/FAIL'} | {str(r['observed']).replace('|',';')} |" for r in checks]
    lines += ["", "## Material limitations", ""] + ["- "+x for x in limitations]
    lines += ["", "## Test interpretation", "", "New source-example tests cover both gap-diagram directions, the author's green-long correction, independent body geometry, first5m aggregation, incomplete bucket exclusion, EMA seed/prefix causality and confirmed-pivot availability. One strict xfail preserves a confirmed existing optional-wrapper metadata defect, intentionally left unfixed under the audit-only instruction. It is not treated as a passing implementation test. The one skipped test is the Phase3.4 snapshot-preservation test, explicitly superseded by the Phase3.5 snapshot test (`tests/test_phase34_pdr_revision.py:321`).",
              "", "Snapshot/default-equivalence tests elsewhere establish reproducibility, not author fidelity. Missing source tests require the author's exact price-axis examples with indicator settings and level/anchor drawings. No test can certify an undefined discretionary rule merely because signal counts match the journal."]
    (OUT / "independent_review.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"all_passed": result["all_passed"], "failed_or_pending": [r for r in checks if not r["passed"]]}, indent=2))


if __name__ == "__main__":
    main()
