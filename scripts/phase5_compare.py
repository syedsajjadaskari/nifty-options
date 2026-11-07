"""Phase 5: rebuild the per-index tables, the cross-index comparison (NIFTY vs BANKNIFTY vs SENSEX over comparable dates) and the two verification workbooks from the CSV files that scripts/phase5_run.py wrote.

NIFTY reference rows are READ from reports/phase4/windows/* and the unchanged Phase 3.6 directory (reports/phase3/phase36_body_based_pdr); nothing there is modified.

Usage:  python scripts/phase5_compare.py
Needs:  python scripts/phase5_run.py --index BANKNIFTY --strategy-config phase36-frozen --window all   (and the same for SENSEX)
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

from nifty_trading.research import phase5_report as R  # noqa: E402


def main() -> int:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    info = R.build_all()
    for i in ("BANKNIFTY", "SENSEX"):
        print("workbook:", R.write_index_workbook(i))
    print("comparison tables:", info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
