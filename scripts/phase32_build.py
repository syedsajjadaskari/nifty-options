"""Phase 3.2: build the explainable backtest bundle and write reports/phase3/phase32/ (CSVs, daily journals, charts, Excel workbook, JSON snapshots).

READ-ONLY with respect to trading logic: it re-runs the Phase 3.0 baseline unchanged, verifies the re-run ledger against the frozen one, and never overwrites
an earlier phase's file. Run: .venv/bin/python scripts/phase32_build.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.research import phase32_build as B  # noqa: E402
from nifty_trading.research import phase32_render as RN  # noqa: E402
from nifty_trading.research.phase32_excel import write_workbook  # noqa: E402


def main() -> None:
    t0 = time.time()
    out = B.OUT
    out.mkdir(parents=True, exist_ok=True)
    b = B.build()
    print(f"bundle built in {time.time() - t0:.1f}s: {len(b.trades)} trades, {len(b.checks)} checks, {len(b.daily)} days; ledger identical to Phase 3.0: {b.ledger_check['identical']}")
    RN.write_all_csv(b, out)
    n_days = RN.write_daily(b, out)
    n_charts = RN.write_charts(b, out)
    RN.write_json(b, out)
    write_workbook(b, out / "NIFTY_Daily_Trade_Verification.xlsx")
    counts = {"trading_days": len(b.days), "trades": len(b.trades), "daily_journals": n_days, "charts": n_charts, "checks": len(b.checks), "legs": len(b.legs), "candle_rows": len(b.candles),
              "confirmed_signals": len(b.signals), "ignored": len(b.ignored), "rejected_or_incomplete": len(b.rejected), "manual_rows": sum(1 for c in b.manual_cmp if c["journal_row"] != ""),
              "extras": sum(1 for c in b.manual_cmp if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"), "issues": len(b.issues)}
    (out / "build_counts.json").write_text(json.dumps(counts, indent=2))
    print(json.dumps(counts))
    print(f"done in {time.time() - t0:.1f}s -> {out}")


if __name__ == "__main__":
    main()
