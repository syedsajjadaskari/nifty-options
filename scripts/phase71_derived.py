"""Phase 7.1 derived tables: PDR / PDS / candle-strength comparisons (Phase 6.5 research files read-only + this phase's portfolio runs), Phase 7.0 re-verification from the saved ledgers,
the EMA source-authority matrix, the rule registry and the configuration manifest."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase7/phase71_global_ema_and_final_validation"
R65 = ROOT / "reports/phase6/phase65_author_feedback"
R70 = ROOT / "reports/phase7/phase70_complete_irf_rebuild"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_sha(rel: str) -> str:
    p = ROOT / rel
    fs = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts)
    h = hashlib.sha256()
    for f in fs:
        h.update(str(f.relative_to(ROOT)).encode())
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return f"{len(fs)} files {h.hexdigest()}"


def main() -> None:
    wr = pd.read_csv(OUT / "strategy_win_rates.csv")
    full = pd.read_csv(OUT / "full_five_strategy_backtest.csv")
    # ---------------------------------------------------------------- PDR delayed cases (Phase 6.5 audit, preserved) + summary
    d = pd.read_csv(R65 / "pdr_215_delayed_cycles.csv")
    d.insert(0, "provenance", "Phase 6.5 pdr_215_delayed_cycles.csv (read-only copy); classification re-counted in Phase 7.1")
    d.to_csv(OUT / "pdr_215_delayed_cases.csv", index=False)
    summ = {"delayed_cases": len(d), "by_window": d.window.value_counts().to_dict(), "delay_category": d.delay_category.value_counts().to_dict(), "first_green_closes_above_ceiling_true": int((d.first_green_closes_above_ceiling == True).sum()),  # noqa: E712
            "retest_candle_green_and_above_ceiling_true": int((d.retest_candle_green_and_above_ceiling == True).sum()), "audit_classification_defects": int(d.audit_classification.str.contains("DEFECT").sum())}  # noqa: E712
    (OUT / "_state" / "pdr_delayed_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    # ---------------------------------------------------------------- PDR first vs second (signal level, Phase 6.5) + portfolio level (Phase 7.1)
    rows = []
    for v in "BCD":
        s = pd.read_csv(R65 / f"pdr_variant_{v}_signals.csv")
        for wn, g in s.groupby("window"):
            c = g.relation_to_baseline.value_counts().to_dict()
            rows.append({"section": "SIGNAL_LEVEL (Phase 6.5)", "variant": f"PDR-{v}", "window": wn, "cycles": len(g), **{f"relation_{k}": x for k, x in c.items()}})
    for k, lab in (("B", "B (baseline, PDR-A rules)"), ("G1", "PDR-B1"), ("G2", "PDR-B2"), ("G3", "PDR-C"), ("H", "PDR-D")):
        for wn in "AB":
            r = wr[(wr.config == k) & (wr.window == wn) & (wr.strategy == "PDR")].iloc[0]
            f = full[(full.config == k) & (full.window == wn)].iloc[0]
            rows.append({"section": "PORTFOLIO_LEVEL (Phase 7.1, IRF V3 base)", "variant": lab, "window": wn, "pdr_trades": r.executed_trades, "pdr_winners": r.winners, "pdr_losers": r.losers, "pdr_win_rate_pct": r.gross_win_rate_pct,
                         "pdr_profit_factor": r.profit_factor, "pdr_gross_points": r.gross_points, "portfolio_trades": f.trades, "portfolio_win_rate_pct": f.gross_win_rate_pct, "portfolio_gross_rs": f.gross_rs})
    pd.DataFrame(rows).to_csv(OUT / "pdr_first_vs_second_confirmation.csv", index=False)
    # ---------------------------------------------------------------- PDS
    pv = pd.read_csv(R65 / "pds_confirmation_variants.csv")
    rows = []
    for (wn, m), g in pv.groupby(["window", "pds_method"]):
        rows.append({"section": "SIGNAL_LEVEL (Phase 6.5)", "window": wn, "pds_method": m, "cycles": len(g), "second_eligible_exists": int(g.second_eligible_confirmation.notna().sum()), "mandatory_support_break_bypassed": int((g.mandatory_support_break_bypassed == True).sum())})  # noqa: E712
    for k, lab in (("B", "B (first-eligible PDS)"), ("I1", "I1 frozen numeric-threshold PDS"), ("I2", "I2 second confirmation (Methods 1/2)")):
        for wn in "AB":
            r = wr[(wr.config == k) & (wr.window == wn) & (wr.strategy == "PDS")].iloc[0]
            rows.append({"section": "PORTFOLIO_LEVEL (Phase 7.1)", "window": wn, "variant": lab, "pds_trades": r.executed_trades, "pds_winners": r.winners, "pds_losers": r.losers, "pds_win_rate_pct": r.gross_win_rate_pct,
                         "pds_profit_factor": r.profit_factor, "pds_gross_points": r.gross_points})
    pd.DataFrame(rows).to_csv(OUT / "pds_confirmation_comparison.csv", index=False)
    # ---------------------------------------------------------------- candle strength
    rows = []
    for k, lab in (("B", "none (baseline)"), ("J60", "60% body"), ("J70", "70% body"), ("JD", "pattern-aware")):
        for wn in "AB":
            f = full[(full.config == k) & (full.window == wn)].iloc[0]
            rows.append({"section": "PHASE 7.1 (IRF V3 base)", "variant": lab, "window": wn, "scope": "ALL", "trades": f.trades, "win_rate_pct": f.gross_win_rate_pct, "profit_factor": f.profit_factor, "gross_rs": f.gross_rs, "max_dd_rs": f.max_drawdown_rs})
            for s in ("IRF", "ORB", "PDR", "PDS", "RF"):
                r = wr[(wr.config == k) & (wr.window == wn) & (wr.strategy == s)].iloc[0]
                rows.append({"section": "PHASE 7.1 (IRF V3 base)", "variant": lab, "window": wn, "scope": s, "trades": r.executed_trades, "win_rate_pct": r.gross_win_rate_pct, "profit_factor": r.profit_factor, "gross_rs": r.gross_rs})
    old = pd.read_csv(R65 / "candle_strength_variants_performance.csv")
    for r in old[old.strategy == "ALL"].itertuples():
        rows.append({"section": "PHASE 6.5 reference (IRF V2 base; completed earlier, read-only)", "variant": {"A": "none", "B": "60% body", "C": "70% body", "D": "pattern-aware"}.get(r.variant, r.variant), "window": r.window, "scope": "ALL",
                     "trades": r.trades, "win_rate_pct": r.win_rate_pct, "profit_factor": r.profit_factor, "gross_rs": r.gross_rs, "max_dd_rs": r.max_drawdown_rs})
    pd.DataFrame(rows).to_csv(OUT / "candle_strength_reference_comparison.csv", index=False)
    # ---------------------------------------------------------------- Phase 7.0 re-verification from saved ledgers
    m1 = pd.read_csv(R70 / "method1_backtest.csv")
    m2 = pd.read_csv(R70 / "method2_backtest.csv")
    cb = pd.read_csv(R70 / "combined_irf_backtest.csv")
    js = pd.read_csv(R70 / "manual_journal_match_summary.csv").set_index("engine")
    rows = []
    for nm, df_ in (("Method 1", m1), ("Method 2", m2), ("Combined", cb)):
        for wn, sc in (("A", "SL40_T60"), ("A", "SL35_T60"), ("B", "SL40_T60")):
            g = df_[(df_.window == wn) & (df_.scenario == sc) & (df_.exit_status == "CLOSED")]
            w_ = g[g.gross_points > 0]
            lo = g[g.gross_points < 0]
            rows.append({"book": nm, "window": wn, "scenario": sc, "trades_recounted": len(g), "wins": len(w_), "win_rate_pct_recounted": round(100 * len(w_) / len(g), 2), "gross_points_recounted": round(g.gross_points.sum(), 2),
                         "profit_factor_recounted": round(w_.gross_points.sum() / abs(lo.gross_points.sum()), 3), "duplicate_dates": int(g.date.duplicated().sum())})
    for nm, key in (("Method 1", "M1"), ("Method 2", "M2"), ("Combined", "COMBINED")):
        rows.append({"book": nm, "window": "A", "scenario": "journal", "strict_matches_recounted": int(js.loc[key, "strict"]), "time_tolerant": int(js.loc[key, "time_tolerant_extra"]), "date_only": int(js.loc[key, "date_strategy_only"]), "manual_only": int(js.loc[key, "manual_only"])})
    pd.DataFrame(rows).to_csv(OUT / "irf_v3_final_diagnostics.csv", index=False)
    # ---------------------------------------------------------------- EMA source-authority matrix
    M = [
        ("IRF (Method 1 / 2, Phase 7.0 PDFs)", "IRF_Inverse_Retest_Failure_Rulebook.pdf p2; IRF_Method2_First_Red_Candle_Rulebook.pdf p2: 'IRF has no 200 EMA filter ... a SHORT can be taken whether price is above or below the 200 EMA'",
         "Applies to IRF (author message, undated, relayed by the owner)", "YES - direct contradiction of the explicit no-EMA statement; the PDFs say 'as you described it', i.e. an earlier description", "Owner: does the universal statement supersede the no-EMA statement for IRF V3?"),
        ("IRF (earlier: phone call + handwritten pages)", "reports/phase5/phase52_author_rules/author_call_clarifications.md C3: 'the gap between the EMA and the candle should be 28 points' (call); handwritten AC13/AC18 (docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf p3-4): 'EMA space less than 27 -> wait for the EMA break'",
         "27 (now universal)", "28 (call) vs 27 (handwritten) vs 27 (new) - the handwritten pages and the new statement agree on 27; the call said 28", "Owner: 27 or 28; distance definition"),
        ("ORB (Nifty_920_ORB_Rulebook docx / ORB_Strategy_Rulebook-2.pdf)", "200 EMA DIRECTION filter on the 5-minute chart: BUY only above, SELL only below; 'a fresh cross of the EMA is allowed' (9:15 candle may cross); close exactly on the EMA = no trade; 'near the EMA wait for a convincing close' (ORB pdf p5/p7)",
         "Additional 27-point rule for ORB", "POTENTIAL - a minimum-distance reading would reject fresh-cross entries the rulebook permits; the rulebook's 'near the EMA ... convincing close' wording is itself undefined", "Owner: is the 27-point rule the definition of 'near the EMA' for ORB? minimum or maximum?"),
        ("PDR (PDR_Strategy_Guide.pdf)", "no EMA / 200 text in the 4-page guide", "Applies to PDR", "No stated conflict; no baseline EMA rule exists", "Owner: confirm applicability and meaning (a trend-continuation retest strategy)"),
        ("PDS (PDS strategy.pdf)", "no EMA / 200 text in the 7-page guide", "Applies to PDS", "No stated conflict; no baseline EMA rule exists", "Owner: confirm applicability and meaning"),
        ("RF (RF strategy.pdf)", "200 EMA is 'a basic trend filter ... never the only proof of an uptrend' (p2, p4, p5, p8: 'established uptrend, not just above the EMA'); no distance number", "Applies to RF", "Potential: a different, qualitative use of the EMA", "Owner: does the 27-point gap add to or replace the trend filter?"),
    ]
    pd.DataFrame(M, columns=["strategy", "existing_EMA_rule_and_source", "new_27_point_statement", "possible_conflict", "decision_needed"]).to_csv(OUT / "ema_source_conflict_matrix.csv", index=False)
    # ---------------------------------------------------------------- manifest
    prot = ["src/nifty_trading/strategies/irf.py", "src/nifty_trading/strategies/irf_v2.py", "src/nifty_trading/strategies/irf_phase53.py", "src/nifty_trading/strategies/orb.py", "src/nifty_trading/strategies/pdr.py", "src/nifty_trading/strategies/pds.py", "src/nifty_trading/strategies/rf.py",
            "src/nifty_trading/strategies/runner.py", "src/nifty_trading/strategies/selection.py", "src/nifty_trading/core", "src/nifty_trading/research/orb_v2", "src/nifty_trading/research/irf_v3", "src/nifty_trading/research/phase71",
            "data/processed", "data/phase4", "data/phase71/processed", "data/raw/phase71_5paisa_nov2026", "docs/trading journal"]
    sys = __import__("sys")
    sys.path.insert(0, str(ROOT / "scripts"))
    import phase71_run as R

    man = {"phase": "7.1", "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
           "configurations": R.CONFIGS, "windows": {"A": "2025-09-01..2026-08-31 (5paisa, Phase 1/2 store)", "B": "2022-09-01..2025-08-31 (5paisa, Phase 4 store)"},
           "controller_and_exit": "frozen portfolio controller; 6 lots x 65 = 390 units; T1 +27 on 3 lots; T2 +60 (IRF/ORB/RF) / +70 (PDR/PDS) on 3 lots; stops ORB 30, others 35; post-T1 stop entry +/-6; entry cutoff 13:00; forced exit before 15:15; first valid signal of the day; max two trades; second trade only PDR/PDS after a full initial stop",
           "irf_v3_inputs": "Phase 7.0 method definitions (entry decision only) through research/phase71/irf_cycles.py (first cycle parity with irf_v3 on all 1964 session-methods) and irf_engine.py", "orb": "ORB V2-A provisional (Phase 6.2 adapter)",
           "pdr_pds_rf_base": "Phase 5.3 first-eligible PDR/PDS + frozen RF (Phase 6.2 configuration C slots)", "ema_configs": {k: R.ER.LABEL[v] for k, v in R.EMA_OF.items()},
           "sha256": {p: tree_sha(p) for p in prot}, "journal_sha256": sha(ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"),
           "source_pdfs": {p.name: sha(p) for p in sorted((ROOT / "docs/strategy_docs").glob("IRF_*Rulebook.pdf"))}, "phase65_inputs_read_only": sorted(x.name for x in R65.glob("pdr_*.csv")) + ["pds_confirmation_variants.csv", "candle_strength_variants_performance.csv"],
           "promotion": "NONE - no configuration is selected or promoted to paper trading"}
    (OUT / "configuration_manifest.json").write_text(json.dumps(man, indent=1))
    print("derived ok", summ)


if __name__ == "__main__":
    main()
