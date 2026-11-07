"""Phase 5: run the FROZEN Phase 3.6 five-strategy portfolio on the BANKNIFTY and SENSEX INDEX prices and write reports/phase5/<index>/.

The strategy is not configurable: ``--strategy-config phase36-frozen`` is the only accepted value and the run is REFUSED if any file hashed in the Phase 4 freeze (strategies, controller, execution, session construction,
scenario and report framework) or any parameter differs from reports/phase4/strategy_freeze.json. Only the index, the date range and the data source can be chosen. Stops and targets stay the NIFTY index-POINT values.
Results are INDEX-POINT results; no option premium is used or estimated.

Windows (per index)
  main      M     2022-09-01..2026-08-31, 5paisa minutes (DATA window; annual slices are reported by the comparison step)
  vendor    MS    2022-09-01..2024-03-22, secondary-repository minutes (vendor-sensitivity run of the same dates)
  2018      C     2018-01-01..2018-12-31, secondary-repository minutes (EXPLORATORY: no other vendor has 2018 minutes)
  2019      D_5P  2019-03-01..2019-12-31, 5paisa minutes (PARTIAL YEAR)  and  D_TV 2019-01-01..2019-12-31, secondary minutes (EXPLORATORY)
  all       every window above
  custom    --start/--end/--minute-source/--window-id for any other range the processed data covers

Examples (macOS terminal)
  cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
  python scripts/phase5_run.py --index BANKNIFTY --strategy-config phase36-frozen --window all
  python scripts/phase5_run.py --index SENSEX --strategy-config phase36-frozen --window main
  python scripts/phase5_run.py --index BANKNIFTY --strategy-config phase36-frozen --window custom --window-id X --start 2023-01-02 --end 2023-06-30 --minute-source 5paisa --out reports/phase5_scratch

Prerequisite (once per index): scripts/phase5_discover.py, scripts/phase5_fetch.py, scripts/phase5_build_data.py. No credentials are needed to run the backtests.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
import warnings
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

from nifty_trading.research import phase5 as F5  # noqa: E402
from nifty_trading.research import phase5_data as D5  # noqa: E402
from nifty_trading.research.phase5_options import option_block  # noqa: E402

WINDOW_SETS = {"main": ["M"], "vendor": ["MS"], "2018": ["C"], "2019": ["D_5P", "D_TV"], "all": ["M", "MS", "C", "D_5P", "D_TV"]}


def verify_freeze(freeze_path: Path | None = None) -> dict:
    """The Phase 4 guard, reused unchanged (scripts/phase4_run.py): every hashed strategy / framework file and every parameter must equal reports/phase4/strategy_freeze.json
    (``freeze_path`` exists only so a test can point the guard at a tampered copy)."""
    spec = importlib.util.spec_from_file_location("phase4_run", ROOT / "scripts" / "phase4_run.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if freeze_path is not None:
        m.FREEZE = freeze_path
    return m.verify_freeze()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--index", required=True, choices=sorted(D5.INDEXES) + ["ALL"], help="index to run (ALL = both, one after the other, never combined)")
    ap.add_argument("--strategy-config", required=True, choices=["phase36-frozen"], help="the frozen Phase 3.6 configuration (the only choice; verified against reports/phase4/strategy_freeze.json)")
    ap.add_argument("--window", required=True, choices=["main", "vendor", "2018", "2019", "all", "custom"])
    ap.add_argument("--window-id", default="custom")
    ap.add_argument("--start", type=date.fromisoformat, help="custom window start (YYYY-MM-DD)")
    ap.add_argument("--end", type=date.fromisoformat, help="custom window end (YYYY-MM-DD)")
    ap.add_argument("--minute-source", choices=["5paisa", "secondary"], default="5paisa", help="minute-data source of a custom window (the daily series is always 5paisa)")
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "phase5", help="output directory (its name must start with 'phase5')")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    out = a.out if a.out.is_absolute() else Path.cwd() / a.out
    if not out.name.startswith("phase5"):
        print(f"refusing to write outside a reports/phase5* directory: {out}", file=sys.stderr)
        return 2
    fr = verify_freeze()
    print(f"frozen configuration verified: {fr['frozen_configuration_id']}")
    if a.window == "custom" and not (a.start and a.end):
        print("--window custom needs --start and --end", file=sys.stderr)
        return 2
    for name, ix in D5.INDEXES.items():
        if a.index not in ("ALL", name):
            continue
        if a.window == "custom":
            specs = [F5.RunSpec5(name, a.window_id, f"custom window {a.start}..{a.end} ({a.minute_source} minutes)", a.start, a.end, a.minute_source, "CUSTOM")]
        else:
            allspecs = F5.specs_for(name)
            specs = [allspecs[w] for w in WINDOW_SETS[a.window]]
        for spec in specs:
            t0 = time.time()
            b, _wd = F5.run_window(ix, spec)
            info = F5.write_window(b, ix, spec, out / ix.key, option_note=option_block)
            gross = sum(float(t["gross_pnl_rs"]) for t in b.trades)
            pts = sum(float(t["gross_pnl_points_weighted"]) for t in b.trades)
            print(f"{name} {spec.window_id} [{spec.status}] {spec.start}..{spec.end}: {len(b.days)} sessions, {len(b.trades)} trades, {pts:,.1f} weighted index points (fixed-390 Rs {gross:,.0f}, comparison device only), "
                  f"recomputation mismatches {sum(1 for t in b.trades if t['recomputation_mismatches'])}, {info['days']} journals, {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
