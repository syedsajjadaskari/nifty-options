"""Phase 4: run the FROZEN Phase 3.6 five-strategy portfolio over historical windows and write reports/phase4/.

The strategy is not configurable: ``--strategy-config phase36-frozen`` is the only accepted value and the run is REFUSED if any file hashed in the freeze (strategies, controller, execution, session construction, scenario and report framework) or any parameter differs from
reports/phase4/strategy_freeze.json. Only the date range and the data source can be chosen.

Windows
  three-year   Window B  2022-09-01..2025-08-31, 5paisa minutes (the three annual slices are reported separately by the comparison step)
  2018         Window C  2018-01-01..2018-12-31, secondary-vendor minutes (EXPLORATORY: no other vendor has 2018 minutes)
  2019         Window D  2019: 5paisa minutes 2019-03-01..2019-12-31 (PARTIAL YEAR) and the secondary vendor's full calendar year (EXPLORATORY)
  all          B, the secondary-vendor sensitivity run of B, C and both D runs, then the multi-period comparison, robustness, cost sensitivity and the workbook
  custom       --start/--end/--minute-source/--window-id for any other range the processed data covers

Examples (macOS terminal, from anywhere)
  cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
  python scripts/phase4_run.py --strategy-config phase36-frozen --window three-year
  python scripts/phase4_run.py --strategy-config phase36-frozen --window 2018
  python scripts/phase4_run.py --strategy-config phase36-frozen --window 2019
  python scripts/phase4_run.py --strategy-config phase36-frozen --window all          # full multi-period comparison
  python scripts/phase4_run.py --strategy-config phase36-frozen --window custom --window-id X --start 2023-01-02 --end 2023-06-30 --minute-source 5paisa

Prerequisite (once): scripts/phase4_fetch_5paisa.py, scripts/phase4_fetch_secondary.py, scripts/phase4_build_data.py (data retrieval and validation). No credentials are needed to run the backtests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase4 as F  # noqa: E402
from nifty_trading.research import phase4_data as D  # noqa: E402

FREEZE = ROOT / "reports" / "phase4" / "strategy_freeze.json"
WINDOW_SETS = {"three-year": ["B"], "2018": ["C"], "2019": ["D_5P", "D_TV"], "all": ["B", "B_TV", "C", "D_5P", "D_TV"]}
SOURCES = {"5paisa": D.SRC_5P_MIN, "secondary": D.SRC_TV_MIN}
GUARDED = ()  # empty: EVERY file hashed in the freeze (engines, controller, execution, session construction, scenario and the Phase 3.2 build / render framework) is checked


def verify_freeze() -> dict:
    """Refuse to run unless the strategy-defining files and every parameter equal the freeze record."""
    if not FREEZE.exists():
        raise SystemExit("reports/phase4/strategy_freeze.json is missing: run scripts/phase4_freeze.py first")
    fr = json.loads(FREEZE.read_text())
    bad = []
    for path, h in fr["active_file_hashes"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != h:
            bad.append(path)
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    from dataclasses import asdict

    from nifty_trading.strategies.trading_day import DayRules
    cur = {"proposal_config": sc.proposals.to_dict(), "trade_config": asdict(sc.trade), "pdr_body_config": asdict(sc.pdr_revision), "day_rules": asdict(DayRules())}
    for k, v in cur.items():
        if json.dumps(v, sort_keys=True, default=str) != json.dumps(fr["parameters"][k], sort_keys=True, default=str):
            bad.append(f"parameters.{k}")
    if bad:
        raise SystemExit(f"FROZEN CONFIGURATION VIOLATED ({fr['frozen_configuration_id']}): {bad}")
    return fr


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--strategy-config", required=True, choices=["phase36-frozen"], help="the frozen Phase 3.6 configuration (the only choice; verified against reports/phase4/strategy_freeze.json)")
    ap.add_argument("--window", required=True, choices=["three-year", "2018", "2019", "all", "custom"])
    ap.add_argument("--window-id", default="custom", help="identifier of a custom window (output sub-directory)")
    ap.add_argument("--start", type=date.fromisoformat, help="custom window start (YYYY-MM-DD)")
    ap.add_argument("--end", type=date.fromisoformat, help="custom window end (YYYY-MM-DD)")
    ap.add_argument("--minute-source", choices=sorted(SOURCES), default="5paisa", help="minute-data source of a custom window (the daily series is always 5paisa)")
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "phase4", help="output directory (must be a reports/phase4* directory)")
    ap.add_argument("--no-compare", action="store_true", help="with --window all: skip the comparison / workbook step")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    out = a.out if a.out.is_absolute() else Path.cwd() / a.out
    if not out.name.startswith("phase4") and out.name != "phase4":
        print(f"refusing to write outside a reports/phase4* directory: {out}", file=sys.stderr)
        return 2
    fr = verify_freeze()
    print(f"frozen configuration verified: {fr['frozen_configuration_id']}")
    if a.window == "custom":
        if not (a.start and a.end):
            print("--window custom needs --start and --end", file=sys.stderr)
            return 2
        specs = [F.RunSpec(a.window_id, f"custom window {a.start}..{a.end} ({a.minute_source} minutes)", a.start, a.end, SOURCES[a.minute_source], status="CUSTOM")]
    else:
        specs = [F.SPECS[w] for w in WINDOW_SETS[a.window]]
    for spec in specs:
        t0 = time.time()
        b, wd = F.run_window(spec)
        F.write_window(b, spec, out)
        gross = sum(float(t["gross_pnl_rs"]) for t in b.trades)
        print(f"{spec.window_id} [{spec.status}] {spec.start}..{spec.end}: {len(b.days)} sessions, {len(b.trades)} trades, gross Rs {gross:,.0f} (fixed 390-unit multiplier), "
              f"recomputation mismatches {sum(1 for t in b.trades if t['recomputation_mismatches'])}, {time.time() - t0:.0f}s")
    if a.window == "all" and not a.no_compare:
        from nifty_trading.research import phase4_report as R
        R.build_all(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
