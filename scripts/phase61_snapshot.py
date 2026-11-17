"""Phase 6.1-6.3 preservation snapshot / verification (read-only on everything except its own output file).

  python scripts/phase60_snapshot.py before      # hash every existing file under the protected roots -> before_snapshot.json
  python scripts/phase60_snapshot.py verify      # re-hash and prove no pre-existing file changed or disappeared

Pre-existing files must be byte-identical afterwards. New files are allowed only under the Phase 6.0 prefixes in ALLOWED_NEW.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase6" / "phase61_irf_support_break"
SNAP = OUT / "before_snapshot.json"
ROOTS = ("data", "reports", "docs", "src", "tests", "scripts", "pyproject.toml", "README.md")
SKIP_PARTS = {"__pycache__", ".DS_Store", "node_modules"}
ALLOWED_NEW = ("reports/phase6/phase61_irf_support_break/", "reports/phase6/phase62_combined_backtest/", "reports/phase6/phase63_manual_reconciliation/", "reports/phase6/PHASE61_63", "src/nifty_trading/research/irf_v2", "src/nifty_trading/strategies/irf_v2.py", "src/nifty_trading/strategies/orb_v2_adapter.py", "src/nifty_trading/research/phase6", "tests/test_phase61_", "tests/test_phase62_", "tests/test_phase63_", "scripts/phase61_", "scripts/phase62_", "scripts/phase63_")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk() -> dict[str, str]:
    out: dict[str, str] = {}
    for r in ROOTS:
        base = ROOT / r
        files = [base] if base.is_file() else sorted(base.rglob("*")) if base.exists() else []
        for p in files:
            if not p.is_file() or SKIP_PARTS & set(p.parts):
                continue
            rel = p.relative_to(ROOT).as_posix()
            if rel.startswith(("reports/phase6/phase61_", "reports/phase6/phase62_", "reports/phase6/phase63_", "reports/phase6/PHASE61_63")):
                continue
            out[rel] = sha(p)
    return out


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "before":
        OUT.mkdir(parents=True, exist_ok=True)
        snap = walk()
        SNAP.write_text(json.dumps({"n_files": len(snap), "roots": ROOTS, "files": snap}, indent=0, sort_keys=True))
        print(f"before snapshot: {len(snap)} files -> {SNAP.relative_to(ROOT)}")
        return 0
    if mode == "verify":
        before = json.loads(SNAP.read_text())["files"]
        now = walk()
        changed_all = sorted(k for k in before if k in now and now[k] != before[k])
        own_edited = [k for k in changed_all if k.startswith(ALLOWED_NEW)]          # Phase 6.1-6.3 files that already existed when the snapshot was taken (this script) and were edited later
        changed = [k for k in changed_all if not k.startswith(ALLOWED_NEW)]
        removed = sorted(k for k in before if k not in now)
        added = sorted(k for k in now if k not in before)
        bad_added = [k for k in added if not k.startswith(ALLOWED_NEW)]
        res = {"files_before": len(before), "files_now": len(now), "changed": changed, "own_phase61_63_files_edited_after_snapshot": own_edited, "removed": removed, "added_total": len(added), "added_outside_phase60": bad_added,
               "added_phase60_by_prefix": {p: sum(1 for k in added if k.startswith(p)) for p in ALLOWED_NEW}, "preserved": not changed and not removed and not bad_added}
        (OUT / "preservation_check.json").write_text(json.dumps(res, indent=1))
        print(json.dumps({k: (v if not isinstance(v, list) else v[:10]) for k, v in res.items()}, indent=1))
        return 0 if res["preserved"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
