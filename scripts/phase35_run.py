"""Phase 3.5: run the complete five-strategy NIFTY 50 backtest (IRF, ORB, PDR, PDS, RF) through the shared portfolio controller and write reports/phase3/phase35_combined/.

Reuses the existing Phase 3.0 runner and the Phase 3.2 report framework; the only choice is which PDR engine feeds the controller:

  --pdr-engine revised   (default) the Phase 3.4 revised engine (previous-day-high zone, green body OR lower-price rejection OR hammer, close strictly above the zone ceiling;
                         provisional thresholds and open-above-zone assumption - NOT approved by the strategy author)
  --pdr-engine legacy    the Phase 3.0 legacy engine: re-runs the Phase 3.0 baseline and checks that it reproduces the frozen ledger (writes to reports/phase3/phase35_legacy_check/)
  --pdr-engine body-based the Phase 3.6 author-corrected BODY-BASED engine (wicks ignored, open strictly above the zone; provisional pattern thresholds). `revised` keeps its Phase 3.5 meaning
                         (wick-high ceiling). Writes to reports/phase3/phase36_body_based_pdr/ (scripts/phase36_run.py is a shortcut for this option)

Run (macOS terminal, from anywhere):
  cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase35_run.py --pdr-engine revised

No parameter is tuned, nothing is traded live, no broker API is called, no data file is written.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.research import phase35 as F  # noqa: E402
from nifty_trading.research import phase36 as F36  # noqa: E402

ENGINES = {"revised": "REVISED_PHASE34", "legacy": "LEGACY", "body-based": "BODY_BASED_PHASE36"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdr-engine", choices=sorted(ENGINES), default="revised", help="which PDR engine feeds the shared controller (default: revised = Phase 3.4 engine)")
    ap.add_argument("--out", type=Path, default=None, help="output directory (default: reports/phase3/phase35_combined; phase35_legacy_check for legacy; phase36_body_based_pdr for body-based)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    engine = ENGINES[a.pdr_engine]
    out = a.out
    if out is not None and not out.is_absolute():
        out = Path.cwd() / out
    if out is not None and ROOT / "reports" in out.resolve().parents and not out.name.startswith(("phase35", "phase36")):
        print(f"refusing to write into a reports directory that is not a Phase 3.5 / 3.6 output: {out}", file=sys.stderr)
        return 2
    if out is not None and out.name in ("baseline", "ema_structure", "pdr_shelf", "sl40", "phase31", "phase32", "phase33_pdr_audit", "phase34_pdr_revision"):
        print(f"refusing to write into an earlier phase's directory: {out}", file=sys.stderr)
        return 2
    if engine == "BODY_BASED_PHASE36":
        if out is not None and out.name.startswith("phase35"):
            print(f"refusing to write the Phase 3.6 results into a Phase 3.5 directory: {out}", file=sys.stderr)
            return 2
        res = F36.run(out)
        c = res["counts"]
        allp = next(r for r in res["perf"] if r["strategy"] == "ALL")
        print(f"PDR engine: {engine}; sessions evaluated: {c['trading_days']}; executed trades: {c['trades']} ({F.by_strategy_text(res['perf'])})")
        print(f"gross P&L Rs {allp['gross_pnl_rs']:,.2f}; illustrative net Rs {allp['net_illustrative_pnl_rs']:,.2f}; profit factor {allp['profit_factor']}")
        print(f"manual journal: {c['journal_exact']} exact + {c['journal_time_shifted']} time-shifted of {c['manual_rows']} rows")
        print(f"recomputation mismatches in the trade explanations: {c['recomputation_mismatches']}; same-minute conflict days: {c['simultaneous_conflict_days']}")
        print(f"written to {res['out']} in {res['seconds']:.1f}s")
        return 0
    res = F.run(engine, out)
    c = res["counts"]
    allp = next(r for r in res["perf"] if r["strategy"] == "ALL")
    print(f"PDR engine: {engine}; sessions evaluated: {c['trading_days']}; executed trades: {c['trades']} ({F.by_strategy_text(res['perf'])})")
    print(f"gross P&L Rs {allp['gross_pnl_rs']:,.2f}; illustrative net Rs {allp['net_illustrative_pnl_rs']:,.2f}; profit factor {allp['profit_factor']}")
    m = res["manual"]
    print(f"manual journal: {m['phase35_exact']} exact + {m['phase35_time_shifted']} time-shifted of {m['manual_rows']} rows (Phase 3.0 baseline: {m['phase30_exact']} + {m['phase30_time_shifted']})")
    print(f"ledger identical to the frozen Phase 3.0 ledger: {c['ledger_identical_to_phase30']} ({c['ledger_differences_vs_phase30']} field differences)")
    print(f"recomputation mismatches in the trade explanations: {c['recomputation_mismatches']}")
    print(f"written to {res['out']} in {res['seconds']:.1f}s")
    if engine == "LEGACY" and not c["ledger_identical_to_phase30"]:
        print("REGRESSION: the legacy run does not reproduce the Phase 3.0 ledger", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
