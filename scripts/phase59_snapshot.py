"""Hash existing sources and previous reports before Phase 5.9 writes."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase59_orb_author_validation"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "before_hashes.json"
    if target.exists():
        raise SystemExit("Snapshot already exists; refusing to replace the original baseline")
    selected = []
    roots = ["src", "tests", "scripts", "docs/strategy_docs", "docs/trading journal", "data/processed",
             "reports/phase3/phase36_body_based_pdr", "reports/phase5"]
    for folder in roots:
        for p in (ROOT / folder).rglob("*"):
            if not p.is_file() or p.is_symlink() or OUT in p.parents or "node_modules" in p.parts or "__pycache__" in p.parts or p.name == ".DS_Store":
                continue
            if "phase59" in p.name:
                continue
            selected.append(p)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(selected))}
    target.write_text(json.dumps({"files": hashes, "scope": roots}, indent=2))
    print(f"Preserved original hashes for {len(hashes)} files")


if __name__ == "__main__":
    main()
