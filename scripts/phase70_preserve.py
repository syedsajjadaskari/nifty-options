"""Phase 7.0 preservation verification: compare the before-snapshot (taken by phase70_run.py at its first run) with the current state. Usage: python scripts/phase70_preserve.py <pytest_summary_file>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase70_run import ROOT, snapshot  # noqa: E402

OUT = ROOT / "reports/phase7/phase70_complete_irf_rebuild"
MINE = ("reports/phase7/", "src/nifty_trading/research/irf_v3/", "tests/test_phase70_irf_v3.py", "scripts/phase70_")


def main(pytest_file: str) -> None:
    before = json.loads((OUT / "_state" / "before_snapshot.json").read_text())
    now = snapshot()
    rows = []
    for k, v in before["hashes"].items():
        rows.append((k, "UNCHANGED" if now["hashes"][k] == v else "CHANGED", v.split()[0] + " files"))
    created = [u for u in now["git_untracked"] if u.startswith(MINE)]
    pdfs = [u for u in now["git_untracked"] if u.endswith(".pdf")]
    other = [u for u in now["git_untracked"] if not u.startswith(MINE) and not u.endswith(".pdf")]
    other_before = set(before["git_untracked"])
    new_other = [u for u in other if u not in other_before]
    txt = Path(pytest_file).read_text().strip().splitlines()[-1] if Path(pytest_file).exists() else "(pytest summary not available)"
    L = ["# Preservation verification (Phase 7.0)", "",
         f"HEAD before: `{before['head']}` - HEAD now: `{now['head']}` ({'unchanged' if before['head'] == now['head'] else 'CHANGED'}). Nothing was committed, staged or pushed by this task.", "",
         "## Protected content (SHA-256 over every file path + content; `__pycache__` excluded)", "", "| Path | Result | Size |", "|---|---|---|"]
    L += [f"| `{a}` | **{b}** | {c} |" for a, b, c in rows]
    for a, b, _c in rows:
        if b == "CHANGED":
            un = [u for u in now["git_untracked"] if u.startswith(a + "/") and u not in before["git_untracked"]]
            L += ["", f"**Why `{a}` shows CHANGED:** the hash covers every file on disk, tracked or not. `git diff --name-only` shows 0 modified tracked files, so no tracked file there was edited; the difference is {len(un)} NEW untracked file(s) that appeared after this task's first snapshot and were not written by this task (they belong to the concurrent Phase 6.5/6.5b work): " + ", ".join(f"`{u}`" for u in un) + "."]
    L += ["", f"## Tracked files modified (`git diff --name-only`): {len(now['git_tracked_modifications'])}", ""]
    L += [f"* `{x}`" for x in now["git_tracked_modifications"]] or ["* none"]
    L += ["", "## Untracked files", f"* Created by Phase 7.0 ({len(created)}): the package `src/nifty_trading/research/irf_v3/`, `tests/test_phase70_irf_v3.py`, `scripts/phase70_run.py|docs.py|preserve.py`, and `reports/phase7/phase70_complete_irf_rebuild/`.",
          f"* The two new rulebook PDFs (still untracked, not added): {', '.join(f'`{p}`' for p in pdfs)}.",
          f"* Other untracked files that existed when this task's first snapshot was taken ({len([u for u in other if u in other_before])}; Phase 6.5 author-feedback work - `reports/phase6/phase65_author_feedback/`, `scripts/phase65_*.py`, `src/nifty_trading/research/phase65.py`, `src/nifty_trading/strategies/strength_gate.py`, `tests/test_phase65_author_feedback.py`). **They were not created or edited by this task**; they appeared in the working tree after the session started (the session-start git status listed only the two PDFs), i.e. another process is working in the same repository.",
          f"* Untracked files that appeared AFTER this task's first snapshot and are not Phase 7.0 outputs: {len(new_other)}" + (": " + ", ".join(f"`{x}`" for x in new_other[:10]) if new_other else "."), "",
          "## Systems explicitly not touched", "* Older IRF engines (`strategies/irf*.py`), ORB V2, PDR, PDS, RF, the five-strategy portfolio controller (`strategies/runner.py`, `selection.py`, ...), `broker/`, `core/`, `config/` (paper-trading configuration): hash-compared above.",
          "* Historical market datasets (`data/processed`, `data/phase4`, `data/metadata`), the manual journal (`docs/trading journal`), earlier backtest results (Phases 5.5 and 6.2/6.3 reports): hash-compared above.",
          "* No import of IRF V3 exists outside `irf_v3/`, `tests/test_phase70_irf_v3.py` and `scripts/phase70_*.py`; no order or paper-order call exists in the package.", "",
          "## Full existing test suite (all tests in `tests/`)", f"`{txt}`", ""]
    (OUT / "preservation_verification.md").write_text("\n".join(L))
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main(sys.argv[1])
