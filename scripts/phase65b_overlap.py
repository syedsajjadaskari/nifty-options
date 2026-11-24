"""Phase 6.5 continuation: READ-ONLY inventory of the concurrently developed Phase 7.0 IRF V3 work and a signal-level comparison with the Phase 6.5 detectors. Nothing under irf_v3/, reports/phase7/ or scripts/phase70_* is
written, copied, imported or executed; only file metadata, source text (ast) and their published CSV/JSON outputs are read at the moment of the run (they may change afterwards)."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nifty_trading.research.orb_v2.reporting import md_table  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R65 = ROOT / "reports" / "phase6" / "phase65_author_feedback"
V3 = ROOT / "src" / "nifty_trading" / "research" / "irf_v3"
P7 = ROOT / "reports" / "phase7" / "phase70_complete_irf_rebuild"
DOCS = ROOT / "docs" / "strategy_docs"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sigs(path: Path):
    return list(csv.DictReader(path.open(newline="")))


def main() -> int:  # noqa: C901
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    files = [{"file": p.name, "bytes": p.stat().st_size, "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M"), "sha256": sha(p)[:12]} for p in sorted(V3.glob("*.py"))]
    defs = {}
    for fn in ("method1.py", "method2.py", "signal_engine.py", "config.py"):
        tree = ast.parse((V3 / fn).read_text())
        defs[fn] = [f"{n.name}({', '.join(a.arg for a in n.args.args)})" for n in tree.body if isinstance(n, ast.FunctionDef)][:8]
    n_reports = sum(1 for _ in (ROOT / "reports" / "phase7").rglob("*") if _.is_file())
    audit = json.loads((P7 / "audit_results.json").read_text()) if (P7 / "audit_results.json").exists() else {}
    mism = sum(v.get("mismatches", 0) for v in audit.values()) if audit else None
    cmp_rows, summary = [], {}
    sig7 = pd.DataFrame(sigs(P7 / "combined_irf_signals.csv"))
    sig7 = sig7[(sig7.window == "A") & sig7.status.str.contains("SIGNAL", na=False)] if len(sig7) else sig7
    mine = pd.read_csv(R65 / "irf_new_methods_vs_existing.csv", dtype=str, keep_default_na=False)
    mine = mine[mine.window == "A"].set_index("date")
    for meth, col, tag in (("IRF_V3_METHOD_1", "new_m1_time", "M1"), ("IRF_V3_METHOD_2", "new_m2_time", "M2")):
        s7 = sig7[sig7.method == meth]
        theirs = {r.date: r.signal_timestamp[11:16] for r in s7.itertuples()} if len(s7) else {}
        ours = {d: r[col] for d, r in mine.iterrows() if r[col]}
        both = set(theirs) & set(ours)
        same = sum(1 for d in both if theirs[d] == ours[d])
        for d in sorted(set(theirs) | set(ours)):
            cmp_rows.append({"method": tag, "date": d, "phase65_detector_time": ours.get(d, ""), "phase70_signal_time": theirs.get(d, ""), "relation": "SAME" if d in both and theirs[d] == ours[d] else ("DIFFERENT_TIME" if d in both else ("PHASE65_ONLY" if d in ours else "PHASE70_ONLY"))})
        summary[tag] = {"phase65_signals": len(ours), "phase70_signals": len(theirs), "same_date_same_time": same, "same_date_different_time": len(both) - same, "phase65_only": len(set(ours) - set(theirs)), "phase70_only": len(set(theirs) - set(ours))}
    pd.DataFrame(cmp_rows).to_csv(R65 / "phase7_signal_comparison.csv", index=False)
    uq = (P7 / "unresolved_author_questions.md").read_text().splitlines()[:30] if (P7 / "unresolved_author_questions.md").exists() else []
    (R65 / "phase7_irf_overlap_inventory.md").write_text("\n".join([
        "# Phase 7.0 IRF V3 overlap inventory (read-only)", "", f"Taken {now}. The Phase 7.0 files are owned by another process and may still be changing; nothing here modifies, copies, stages, imports or executes them, and Phase 6.5 integrates none of their outputs.", "",
        "## Source documents (shared by both efforts)", "", "| document | sha256 |", "|---|---|", f"| IRF_Inverse_Retest_Failure_Rulebook.pdf (Method 1) | `{sha(DOCS / 'IRF_Inverse_Retest_Failure_Rulebook.pdf')}` |", f"| IRF_Method2_First_Red_Candle_Rulebook.pdf (Method 2) | `{sha(DOCS / 'IRF_Method2_First_Red_Candle_Rulebook.pdf')}` |", "",
        "## Phase 6.5 interfaces (detectors only)", "", "* `research/phase65.new_irf_method1(cs, cutoff='13:00') -> dict | None`: level = first-candle high; first later close back below it after any earlier close above it; entry reference = failure close; times are candle END times.",
        "* `research/phase65.new_irf_method2(cs, cutoff='13:00', breakout_candle_may_be_first_red=False) -> dict | None`: Level B = open of the first red candle after the rally breakout; second breakout then failure close. Detectors and a standalone hypothetical diagnostic only: **no engine, no controller integration, no backtest of the new methods as specified**.", "",
        "## Phase 7.0 files observed", "", f"`src/nifty_trading/research/irf_v3/` ({len(files)} modules), `reports/phase7/` ({n_reports} files), `scripts/phase70_run.py`, `scripts/phase70_docs.py`, `scripts/phase70_preserve.py`, `tests/test_phase70_irf_v3.py`.", "", md_table(files), "",
        "Top-level callables (from the source text): " + "; ".join(f"`{k}`: {', '.join(v)}" for k, v in defs.items()), "", "## Phase 7.0's own published test / audit results (not re-run by Phase 6.5)", "",
        f"`audit_results.json` reports an independent re-implementation with **{mism} mismatches** over its scenarios; its README states a three-implementation structure (production state machines, a separate NumPy/resample audit, reports). Phase 6.5 did not run their tests (running them would write into their package directory) and does not vouch for these numbers.", "",
        "## Signal-level comparison with the Phase 6.5 detectors (window 2025-09..2026-08, to the extent both publish a signal)", "", md_table([{"method": k, **v} for k, v in summary.items()]), "",
        "Differences are expected where the two efforts read the rulebooks differently (eligibility statuses, cutoff handling, the 'breakout candle may be the first red candle' convention, level-tie conventions). `phase7_signal_comparison.csv` lists every date. "
        "**The two implementations are NOT claimed to agree**: the comparison above is a read of their published CSV at the time stated; where times differ nobody has determined which reading is intended.", "",
        "## Potential overlap and unresolved interpretation differences", "", "* Both detect the same two methods from the same two PDFs; Phase 7.0 additionally implements execution, backtests and a journal reconciliation, Phase 6.5 does not.", "* Rule choices to be reconciled by the owner: whether the Method 2 breakout candle itself can be the first red candle; whether the 13:00 cutoff applies to the candle end or the fill; stop 35 vs 40; same-candle stop/target order; end-of-day exit.",
        "* Phase 7.0's own list of open questions (first lines, read-only):", "", *[f"  > {x}" for x in uq[:22]], "", "The final integration decision belongs to the owner. Neither effort's signals feed the combined portfolio."]))
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
