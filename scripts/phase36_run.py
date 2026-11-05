"""Phase 3.6 shortcut: run the complete five-strategy backtest with the author-corrected BODY-BASED PDR engine and write reports/phase3/phase36_body_based_pdr/.

Equivalent to:  python scripts/phase35_run.py --pdr-engine body-based

  cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase36_run.py

`--pdr-engine revised` of scripts/phase35_run.py keeps its Phase 3.5 meaning (wick-high ceiling). No parameter is tuned; nothing is traded live.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase35_run  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(phase35_run.main(["--pdr-engine", "body-based", *sys.argv[1:]]))
