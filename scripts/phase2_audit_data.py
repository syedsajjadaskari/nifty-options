"""SUPERSEDED in Phase 2.1.

This script produced the Phase 2 dataset audit, whose "frozen-feed defect" diagnosis was WRONG: the frozen 15:15-15:29 window from
2026-08-03 is NSE's Closing Auction Session (real market structure). Use instead:

    python scripts/phase21_compare.py          # fresh-vs-stored, vendor 5m/daily, external closes, freeze pattern, archive integrity
    python scripts/phase21_build_manifests.py  # session-quality manifest (data/metadata/session_quality_manifest.json)

See docs/phase2/data_repair_report.md.
"""

import sys

if __name__ == "__main__":
    print(__doc__)
    sys.exit(0)
