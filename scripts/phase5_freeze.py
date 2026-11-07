"""Phase 5: record the FROZEN strategy configuration, hash the NIFTY artefacts that must not change, and list the index-specific hardcoding found in the code base.

  python scripts/phase5_freeze.py --snapshot   write reports/phase5/before_snapshot.json (SHA-256 of every git-tracked file, of data/processed/nifty50*, data/phase4, data/raw/phase4_*, reports/phase3, reports/phase4)
  python scripts/phase5_freeze.py --verify     compare the current state with that snapshot (any NIFTY file added, removed or changed is listed) and with reports/phase4/strategy_freeze.json
  python scripts/phase5_freeze.py --config     write reports/phase5/configuration_snapshot.json (frozen parameters, hashes of the active strategy files, the engineering changes, the hardcoding inventory)
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "reports" / "phase5"
SNAP = OUT / "before_snapshot.json"
GUARDED_DIRS = ["data/processed/nifty50", "data/processed/nifty50_daily", "data/processed/nifty50_warmup", "data/phase4", "data/raw/phase4_5paisa", "data/raw/phase4_technovusin", "reports/phase3", "reports/phase4"]
# index-specific hardcoding found by reading the code (file:line, what it is, how Phase 5 deals with it WITHOUT editing the file)
HARDCODING = [
    {"where": "src/nifty_trading/strategies/base.py:33 and :281", "what": "INSTRUMENT = 'NIFTY 50 ...' and instrument='NIFTY 50' on every Signal record", "handling": "label only; the rendered texts and CSV values are relabelled in phase5.relabel(); the signal logic never reads it"},
    {"where": "src/nifty_trading/strategies/rule_data.py:156,334,335,341,422,423", "what": "rule texts mention NIFTY 50 / 65 units per lot", "handling": "provenance of the frozen rules (the source documents); kept verbatim in rule references, instrument phrases relabelled in outputs"},
    {"where": "src/nifty_trading/strategies/params.py:309", "what": "6 lots x 65 = 390 units (3 + 3)", "handling": "unchanged; 390 is a fixed per-index comparison multiplier, not a contract size for BANKNIFTY or SENSEX"},
    {"where": "src/nifty_trading/data/sessions.py:95,105,113", "what": "default loaders read data/processed/nifty50, nifty50_warmup, nifty50_daily", "handling": "not used by Phase 5: build_session_contexts() takes data frames, which phase4_data.build_window_data() passes from the index-specific processed namespace"},
    {"where": "src/nifty_trading/research/phase32_build.py:78,96", "what": "partition_of() and provenance() default to the nifty50 layout", "handling": "build() accepts partition_fn and provenance_override (the Phase 4 extension); Phase 5 passes its own"},
    {"where": "src/nifty_trading/data/market_calendar.py", "what": "closing-auction regime id 'NSE_CLOSING_AUCTION_SESSION' from the NSE calendar file", "handling": "Phase 5 writes a calendar per index DERIVED from that index's own data; the regime entry is added only when the index's own data show the freeze pattern (reports/phase5/<index>/data/closing_auction_evidence.json)"},
    {"where": "src/nifty_trading/instruments/resolver.py:50-110, data/downloader.py:195-262, data/storage.py", "what": "resolve_nifty50_index(), scrip 999920000 / exchange N, 'nifty50' partitions", "handling": "not used: scripts/phase5_discover.py resolves each index from the broker master by name and exchange and verifies the identity with probes"},
    {"where": "src/nifty_trading/core/risk.py:13", "what": "max_position_size 1800 = 50 NIFTY lots", "handling": "not used by any backtest"},
]
ENGINEERING_CHANGES = [
    "NEW src/nifty_trading/research/phase5_data.py (index registry, loaders, Parquet-ZSTD writers), phase5.py (windows, run, write), phase5_options.py (journal block), phase5_report.py (tables)",
    "NEW scripts/phase5_discover.py, phase5_fetch.py, phase5_build_data.py, phase5_run.py, phase5_compare.py, phase5_freeze.py, phase5_options_probe.py, phase5_docs.py, phase5_independent_audit.py",
    "NO existing source file was edited in Phase 5 (strategies, controller, execution, session construction, the Phase 3.2 framework and the Phase 4 modules are byte-identical to the Phase 4 freeze)",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hash_tree() -> dict[str, str]:
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    out = {f: sha(ROOT / f) for f in files if (ROOT / f).is_file() and not f.endswith(".DS_Store")}
    for d in GUARDED_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.name != ".DS_Store":
                out[p.relative_to(ROOT).as_posix()] = sha(p)
    return out


def phase4_run_module():
    spec = importlib.util.spec_from_file_location("phase4_run", ROOT / "scripts" / "phase4_run.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--config", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.snapshot:
        if SNAP.exists():
            print("before_snapshot.json already exists; it is the BEFORE state and is never overwritten", file=sys.stderr)
            return 2
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
        h = hash_tree()
        SNAP.write_text(json.dumps({"taken_utc": datetime.now(timezone.utc).isoformat(), "git_head": head, "untracked_or_modified_at_snapshot": dirty, "files": len(h), "hashes": h}, indent=0, sort_keys=True))
        print(f"snapshot written: {len(h)} files, git head {head[:10]}")
    if a.verify:
        snap = json.loads(SNAP.read_text())["hashes"]
        now = hash_tree()
        changed = sorted(k for k in snap if k in now and snap[k] != now[k])
        removed = sorted(k for k in snap if k not in now)
        added = sorted(k for k in now if k not in snap and any(k.startswith(d) for d in GUARDED_DIRS))
        print(f"files in snapshot {len(snap)}; changed {len(changed)}, removed {len(removed)}, added inside NIFTY / earlier-phase directories {len(added)}")
        for k in (changed + removed + added)[:20]:
            print("  ", k)
        fr = phase4_run_module().verify_freeze()
        print("frozen configuration verified:", fr["frozen_configuration_id"])
        return 0 if not (changed or removed or added) else 1
    if a.config:
        fr = phase4_run_module().verify_freeze()
        cfg = {"phase": "5.0", "generated_utc": datetime.now(timezone.utc).isoformat(), "frozen_configuration_id": fr["frozen_configuration_id"], "freeze_record": "reports/phase4/strategy_freeze.json (Phase 4; unchanged)", "parameters": fr["parameters"],
               "active_file_hashes_verified_now": {p: sha(ROOT / p) for p in fr["active_file_hashes"]}, "active_file_hashes_equal_freeze": all(sha(ROOT / p) == h for p, h in fr["active_file_hashes"].items()),
               "stops_targets": {"unit": "index points, the NIFTY values, NOT scaled to the index level", "initial_stop": {"ORB": 30, "IRF": 35, "PDR": 35, "PDS": 35, "RF": 35}, "target_1": 27, "target_2": {"IRF": 60, "ORB": 60, "PDR": 70, "PDS": 70, "RF": 60},
                                 "post_t1_stop": "entry -/+ 6 points", "entry_cutoff": "13:00 IST", "max_trades_per_day": 2, "second_trade": "PDR/PDS only, after an initial full stop before T1"},
               "units": "390 = 6 x 65, a fixed comparison multiplier for index-point P&L in rupees; NOT a contract size for BANKNIFTY or SENSEX", "engineering_changes": ENGINEERING_CHANGES, "index_specific_hardcoding_inventory": HARDCODING,
               "multi_symbol_support_verified": "build_session_contexts() and phase32_build.build(data=...) accept data frames and a partition function; no strategy file reads an instrument identifier (see inventory)",
               "nifty_preservation": "reports/phase5/before_snapshot.json (taken before any Phase 5 output existed) and `python scripts/phase5_freeze.py --verify`"}
        (OUT / "configuration_snapshot.json").write_text(json.dumps(cfg, indent=1, default=str))
        print("configuration_snapshot.json written; active strategy files equal the freeze:", cfg["active_file_hashes_equal_freeze"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
