"""Phase 6.5 continuation preservation tool (read-only on everything except its own JSON). Classifies every path by OWNER so concurrent work is neither hidden nor mistaken for corruption:

  EXTERNAL   Phase 7.0 files owned by another process (irf_v3/, reports/phase7/, scripts/phase70_*, tests/test_phase70_*): never written by Phase 6.5; their hashes are recorded for reference only
  PHASE65    files owned by Phase 6.5 (the checkpoint files and the continuation files)
  SOURCEDOC  untracked source documents (docs/strategy_docs/...)
  FROZEN     everything else (every pre-existing project file)
  python scripts/phase65b_snapshot.py before | verify
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase6" / "phase65_author_feedback"
SNAP = OUT / "continuation_before_snapshot.json"
ROOTS = ("data", "reports", "docs", "src", "tests", "scripts", "pyproject.toml", "README.md")
SKIP = {"__pycache__", ".DS_Store", "node_modules"}
EXTERNAL = ("src/nifty_trading/research/irf_v3/", "reports/phase7/", "scripts/phase70_", "tests/test_phase70_")
PHASE65 = ("reports/phase6/phase65_author_feedback/", "scripts/phase65", "src/nifty_trading/research/phase65", "src/nifty_trading/strategies/strength_gate.py", "src/nifty_trading/strategies/pdr_variants.py", "src/nifty_trading/strategies/pds_variants.py", "tests/test_phase65")
EXTERNAL71 = ("data/phase71/", "data/raw/phase71_", "scripts/phase71_", "src/nifty_trading/research/phase71/", "tests/test_phase71_")      # appeared during this run; not created by Phase 6.5 (its own created-file set is the PHASE65 prefixes)
SOURCEDOC = ("docs/strategy_docs/IRF_",)


def owner(rel: str) -> str:
    for tag, pre in (("EXTERNAL", EXTERNAL), ("EXTERNAL71", EXTERNAL71), ("PHASE65", PHASE65), ("SOURCEDOC", SOURCEDOC)):
        if rel.startswith(pre):
            return tag
    return "FROZEN"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def walk() -> dict[str, str]:
    out = {}
    for r in ROOTS:
        b = ROOT / r
        for p in ([b] if b.is_file() else sorted(b.rglob("*")) if b.exists() else []):
            if p.is_file() and not (SKIP & set(p.parts)):
                out[p.relative_to(ROOT).as_posix()] = sha(p)
    return out


def git(*a) -> list[str]:
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.splitlines()


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "before":
        snap = walk()
        SNAP.write_text(json.dumps({"git_head": git("rev-parse", "HEAD")[0], "tracked_dirty_at_start": git("diff", "--name-only", "HEAD"), "n_files": len(snap), "files": snap, "owners": {k: owner(k) for k in snap}}, sort_keys=True))
        from collections import Counter
        print("before:", len(snap), dict(Counter(owner(k) for k in snap)))
        return 0
    if mode == "verify":
        b = json.loads(SNAP.read_text())
        before, now = b["files"], walk()
        tracked = set(git("ls-files"))
        changed = sorted(k for k in before if k in now and now[k] != before[k])
        removed = sorted(k for k in before if k not in now)
        added = sorted(k for k in now if k not in before)
        cat = lambda ks, o: [k for k in ks if owner(k) == o]  # noqa: E731
        tracked_mod_now = set(git("diff", "--name-only", "HEAD"))
        res = {"git_head_start": b["git_head"], "git_head_now": git("rev-parse", "HEAD")[0], "files_before": len(before), "files_now": len(now),
               "1_tracked_files_modified_by_this_work": [k for k in tracked_mod_now if owner(k) == "PHASE65"],
               "2_tracked_files_modified_by_another_process_or_unattributed": [k for k in tracked_mod_now if owner(k) != "PHASE65"],
               "frozen_files_changed": cat(changed, "FROZEN"), "frozen_files_removed": cat(removed, "FROZEN"),
               "3_new_phase65_files": len(cat(added, "PHASE65")), "3b_phase65_files_edited_after_snapshot": len(cat(changed, "PHASE65")),
               "4_external_phase70_files": {"present": len([k for k in now if owner(k) == "EXTERNAL"]), "new_since_snapshot": len(cat(added, "EXTERNAL")), "changed_since_snapshot": len(cat(changed, "EXTERNAL")), "removed_since_snapshot": len(cat(removed, "EXTERNAL")),
                                           "note": "owned by another process; Phase 6.5 never writes there, so any change/addition is that process's own activity (attribution is by ownership, not by observation)"},
               "4b_external_phase71_files": {"present": len([k for k in now if owner(k) == "EXTERNAL71"]), "new_since_snapshot": len(cat(added, "EXTERNAL71")), "changed_since_snapshot": len(cat(changed, "EXTERNAL71")), "removed_since_snapshot": len(cat(removed, "EXTERNAL71")),
                                           "note": "a further externally owned effort (Phase 7.1: data/phase71/, scripts/phase71_*, research/phase71/, tests/test_phase71_*) that appeared during this run. Attributed by naming and by exclusion from Phase 6.5's own created files, not observed directly; never read, written or run by Phase 6.5"},
               "5_untracked_source_documents": [k for k in now if owner(k) == "SOURCEDOC" and k not in tracked], "6_genuinely_deleted_original_files": [k for k in removed if owner(k) in ("FROZEN", "SOURCEDOC")],
               "other_new_files_outside_known_owners": cat(added, "FROZEN")}
        res["frozen_baseline_intact"] = not res["frozen_files_changed"] and not res["frozen_files_removed"] and not res["other_new_files_outside_known_owners"] and not res["2_tracked_files_modified_by_another_process_or_unattributed"]
        e0, e1 = res["4_external_phase70_files"], res["4b_external_phase71_files"]
        parts = []
        if e0["changed_since_snapshot"] or e0["new_since_snapshot"]:
            parts.append(f"externally owned Phase 7.0 files changed during this run ({e0['changed_since_snapshot']} changed, {e0['new_since_snapshot']} new); Phase 6.5 only read their metadata, parsed source text and published outputs")
        if e1["present"]:
            parts.append(f"a further externally owned Phase 7.1 effort appeared during this run ({e1['present']} files); Phase 6.5 never read, wrote or ran them")
        res["limitation"] = ("; ".join(parts) + ". Those files are excluded from the frozen-baseline verdict, so no hash comparison of them against the start snapshot is possible.") if parts else "none"
        (OUT / "continuation_preservation_check.json").write_text(json.dumps(res, indent=1))
        print(json.dumps({k: (v if not isinstance(v, list) else (len(v), v[:5])) for k, v in res.items()}, indent=1))
        return 0 if res["frozen_baseline_intact"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
