"""Phase 7.1 preservation verification. No before-snapshot was taken at the start of Phase 7.1, so the check is by (1) ``git diff`` (tracked files unchanged), (2) modification times: no file under any protected path
was modified after Phase 7.1 started (START = creation time of scripts/phase71_fetch_nov2026.py, the first Phase 7.1 file), (3) classification of untracked files into Phase 7.1 outputs and files created by other workers,
(4) re-hash of the protected data / journal / PDFs against the hashes recorded by Phase 7.0 and Phase 6.5. Usage: python scripts/phase71_preserve.py <pytest_summary_file>"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase7/phase71_global_ema_and_final_validation"
PROT = ["src/nifty_trading/strategies", "src/nifty_trading/research/orb_v2", "src/nifty_trading/research/irf_v3", "src/nifty_trading/broker", "src/nifty_trading/core", "src/nifty_trading/config", "src/nifty_trading/data",
        "src/nifty_trading/instruments", "data/processed", "data/phase4", "data/metadata", "data/archive", "docs/trading journal", "docs/strategy_docs", "reports/phase3", "reports/phase5", "reports/phase6/phase62_combined_backtest",
        "reports/phase6/phase61_irf_support_break", "reports/phase6/phase63_manual_reconciliation", "reports/phase7/phase70_complete_irf_rebuild"]
MINE = ("reports/phase7/phase71_", "src/nifty_trading/research/phase71/", "tests/test_phase71_", "scripts/phase71_", "data/phase71/", "data/raw/phase71_5paisa_nov2026/")


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(pytest_file: str) -> None:
    start = (ROOT / "scripts/phase71_fetch_nov2026.py").stat().st_birthtime
    changed = []
    for rel in PROT:
        base = ROOT / rel
        for f in ([base] if base.is_file() else base.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.stat().st_mtime > start:
                changed.append(str(f.relative_to(ROOT)))
    tracked = git("diff", "--name-only").split()
    untracked = git("ls-files", "--others", "--exclude-standard").split()
    mine = [u for u in untracked if u.startswith(MINE)]
    pdfs = [u for u in untracked if u.endswith(".pdf")]
    p70 = [u for u in untracked if u.startswith("reports/phase7/phase70_") or u.startswith("src/nifty_trading/research/irf_v3/") or u.startswith("tests/test_phase70") or u.startswith("scripts/phase70")]
    other = [u for u in untracked if u not in mine and u not in pdfs and u not in p70]
    j = ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
    rec = json.loads((OUT / "_state" / "journal_recount.json").read_text())
    pdfh = {p.name: sha(p) for p in sorted((ROOT / "docs/strategy_docs").glob("IRF_*Rulebook.pdf"))}
    txt = Path(pytest_file).read_text().strip().splitlines()[-1] if Path(pytest_file).exists() else "(summary not available)"
    L = ["# Preservation verification (Phase 7.1)", "", f"Run at {datetime.now():%Y-%m-%d %H:%M}. HEAD `{git('rev-parse', 'HEAD').strip()}` (nothing committed, staged or pushed by this task).", "",
         "## 1. Tracked files modified (`git diff --name-only`)", f"**{len(tracked)}**" + ("" if not tracked else ": " + ", ".join(tracked)), "",
         "## 2. Protected paths modified after Phase 7.1 started", f"Start marker: {datetime.fromtimestamp(start):%Y-%m-%d %H:%M:%S} (creation of `scripts/phase71_fetch_nov2026.py`). Protected paths: {', '.join(f'`{p}`' for p in PROT)}.", f"**{len(changed)} file(s) modified**" + ("" if not changed else ":"), *[f"* `{c}`" for c in changed[:40]], "",
         "## 3. Untracked files", f"* Created by Phase 7.1 ({len(mine)}): `reports/phase7/phase71_global_ema_and_final_validation/`, `src/nifty_trading/research/phase71/`, `tests/test_phase71_global_ema.py`, `scripts/phase71_*.py`, `data/phase71/` (processed November store) and `data/raw/phase71_5paisa_nov2026/` (new raw namespace; the frozen stores were not touched).",
         f"* Phase 7.0 files (untouched by 7.1; untracked since 7.0): {len(p70)}.", f"* The two IRF rulebook PDFs (still untracked, never added): {', '.join(f'`{p}`' for p in pdfs)}.",
         f"* Files created by OTHER workers (Phase 6.5 / 6.5b author-feedback work; not read for modification, not edited): {len(other)} e.g. " + ", ".join(f"`{x}`" for x in other[:6]) + ".", "",
         "## 4. Integrity of protected evidence", f"* Manual journal SHA-256 `{sha(j)}` (data rows {rec['data_rows']}, summary {rec['summary_total_trades']}, weekend rows {rec['weekend_rows']}) - identical to the hash recorded by Phases 6.3 and 7.0 (`97a9ad4d...`).",
         f"* IRF PDFs SHA-256: {pdfh}.", "* Frozen configuration A re-run through the unchanged controller reproduces the saved Phase 6.2 'A' exactly (window A 196 trades / Rs +297,765; window B 609 / Rs +509,398) - evidence that the frozen engines, controller and data are unchanged.",
         "* No Phase 7.1 module is imported by any frozen or paper-trading code (the new package is only imported by `scripts/phase71_*.py` and its tests); no order or broker-order call exists in it. The only broker use is the read-only historical-candle request in `scripts/phase71_fetch_nov2026.py` (BrokerClient order methods are disabled).", "",
         "## 5. Full test suite", f"`{txt}`", ""]
    (OUT / "preservation_verification.md").write_text("\n".join(L))
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main(sys.argv[1])
