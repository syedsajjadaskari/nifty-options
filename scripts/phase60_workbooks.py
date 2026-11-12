"""Phase 6.0 stage 7: the two backtest / reconciliation workbooks, written from the CSV files so every sheet equals its CSV."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase60_common import OUT  # noqa: E402

from nifty_trading.research.orb_v2.reporting import write_workbook  # noqa: E402


def rows(name: str) -> list[dict]:
    p = OUT / name
    if not p.exists() or p.stat().st_size == 0:
        return []
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    for c in df.columns:
        conv = pd.to_numeric(df[c].replace("", pd.NA), errors="coerce")
        if conv.notna().sum() == (df[c] != "").sum() and (df[c] != "").any() and c not in ("date", "trade_id", "sheet_row", "journal_time_label", "journal_time"):
            df[c] = conv.astype(object).where(conv.notna(), "")
    return df.to_dict("records")


def main() -> int:
    manifest = json.loads((OUT / "orb_v2_configuration_manifest.json").read_text())
    cfg_rows = [{"config_id": cid, "sha256": m["config_sha256"], **{k: v for k, v in m["settings"].items() if k not in ("config_id",)}} for cid, m in manifest.items()]
    auth = [{"setting": k, "authority": v} for k, v in manifest["ORB-V2-A"]["authority"].items()]
    notes = {"purpose": "Standalone ORB V2 backtest: one 09:20 decision per session, one trade, 30-point stop / 60-point target. SYNTHETIC NIFTY index-point P&L x a declared 75 units; the index is not tradable; not option P&L.",
             "primary": "Window A 2025-09-01..2026-08-31 and window B 2022-09-01..2025-08-31 on 5paisa minutes. Sheets ending _TV are the secondary-vendor SENSITIVITY (never mixed with the primary).",
             "selection": "No configuration is selected, ranked or recommended. The windows are not untouched out-of-sample evidence.",
             "costs": "Rs 70 per completed trade is the owner's indicative estimate, not a verified bill; slippage is adverse points per side."}
    write_workbook(OUT / "ORB_V2_Complete_Backtest.xlsx", {
        "Configurations": cfg_rows, "Authority_labels": auth, "Performance": rows("configuration_performance.csv"), "Cost_sensitivity": rows("trade_cost_sensitivity.csv"), "Annual": rows("annual_performance.csv"), "Monthly": rows("monthly_performance.csv"),
        "Eligibility_categories": rows("performance_by_eligibility_category.csv"), "Trades": rows("all_orb_trades.csv"), "Exits": rows("all_orb_exits.csv"), "Signals_all_sessions": rows("all_orb_signals.csv"),
        "Trades_TV_sensitivity": rows("vendor_sensitivity_all_orb_trades.csv"), "Audit_discrepancies": rows("audit_discrepancies.csv")}, notes)
    write_workbook(OUT / "ORB_V2_Manual_Reconciliation.xlsx", {
        "Journal_89_ORB_rows": rows("orb_89_journal_rows.csv"), "Previously_missing_50": rows("orb_50_previously_missing_dates.csv"), "Handwritten_13": rows("orb_13_handwritten_disputes.csv"), "ORB_vs_IRF": rows("orb_vs_irf_timeline.csv"),
        "Strict_timing": rows("exact_or_strict_matches.csv"), "Time_tolerant": rows("time_tolerant_matches.csv"), "Date_strategy_only": rows("date_only_matches.csv"), "Manual_only": rows("manual_only.csv"), "Automated_only": rows("automated_only.csv"),
        "Root_causes": rows("mismatch_root_causes.csv")},
        {"evidence_limit": "The manual journal holds date, entry-time label, strategy and outcome only (no direction, price, level, exit time). A STRICT_TIMING match is date + strategy + time label; it is never an exact trade match.",
         "classes": "STRICT_TIMING, TIME_TOLERANT (within 10 minutes), DATE_STRATEGY_ONLY, MANUAL_ONLY, AUTOMATED_ONLY. Journal labels are not ground truth and no date was forced to trade.", "references": "Frozen ORB / IRF ledgers (Phase 5.5) were read only."})
    print("workbooks written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
