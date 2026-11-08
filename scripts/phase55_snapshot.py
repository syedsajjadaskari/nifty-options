"""Phase 5.5: record the baseline BEFORE any Phase 5.5 change, and verify it afterwards.

  python scripts/phase55_snapshot.py --snapshot   write reports/phase5/phase55_combined_backtest/before_snapshot.json: git head, git status, SHA-256 of every file under src, scripts, tests, docs, data, reports
                                                  (except the Phase 5.5 output directory and .DS_Store) - the strategy files, the frozen Phase 3.6 / 4 / 5 reports, the historical datasets, the manual journal and the handwritten PDF
  python scripts/phase55_snapshot.py --verify     list every file added, removed or changed since the snapshot (the only expected changes are the declared Phase 5.5 edits)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
OUTDIR2 = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
SNAP = OUTDIR / "before_snapshot.json"
TOP = ["src", "scripts", "tests", "docs", "data", "reports", "pyproject.toml"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def walk() -> dict[str, str]:
    out: dict[str, str] = {}
    for t in TOP:
        base = ROOT / t
        files = [base] if base.is_file() else sorted(base.rglob("*"))
        for p in files:
            if not p.is_file() or p.name == ".DS_Store" or "__pycache__" in p.parts or OUTDIR in p.parents or OUTDIR2 in p.parents:
                continue
            out[p.relative_to(ROOT).as_posix()] = sha(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if a.snapshot:
        if SNAP.exists():
            print("before_snapshot.json exists; it is the BEFORE state and is never overwritten", file=sys.stderr)
            return 2
        git = lambda *x: subprocess.run(["git", *x], cwd=ROOT, capture_output=True, text=True).stdout  # noqa: E731
        h = walk()
        SNAP.write_text(json.dumps({"taken_utc": datetime.now(timezone.utc).isoformat(), "git_head": git("rev-parse", "HEAD").strip(), "git_branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(), "git_status": git("status", "--short").splitlines(),
                                    "files": len(h), "hashes": h}, indent=0, sort_keys=True))
        print(f"snapshot: {len(h)} files")
    if a.verify:
        snap = json.loads(SNAP.read_text())["hashes"]
        now = walk()
        changed = sorted(k for k in snap if k in now and snap[k] != now[k])
        removed = sorted(k for k in snap if k not in now)
        added = sorted(k for k in now if k not in snap)
        print(f"snapshot files {len(snap)}; changed {len(changed)}, removed {len(removed)}, added {len(added)}")
        for lab, lst in (("changed", changed), ("removed", removed), ("added", added)):
            for k in lst[:40]:
                print(f"  {lab}: {k}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
