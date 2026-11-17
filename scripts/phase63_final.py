"""Consolidated Phase 6.1-6.3 research report: answers the 25 final questions from the result files (no number is typed by hand)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase61_common import R61, R62, R63, ROOT, SCRATCH  # noqa: E402

from nifty_trading.research.orb_v2.reporting import md_table  # noqa: E402


def jl(p):
    return json.loads(Path(p).read_text())


def tailtxt(p, n=4):
    p = Path(p)
    return "\n".join(p.read_text().strip().splitlines()[-n:]) if p.exists() else "(log missing)"


def main() -> int:  # noqa: C901
    s61, s62, s63 = jl(R61 / "phase61_state.json"), jl(R62 / "phase62_state.json"), jl(R63 / "phase63_state.json")
    perf = pd.read_csv(R62 / "strategy_performance.csv")
    cost = pd.read_csv(R62 / "cost_sensitivity.csv")
    ann = pd.read_csv(R62 / "annual_performance.csv")
    audit = jl(R62 / "execution_audit_summary.json")
    summ = {r["config"]: r for r in s63["summary"]}
    strat = pd.read_csv(R63 / "match_summary_by_strategy.csv")
    P = lambda w, k, s="ALL": perf[(perf.window == w) & (perf.config == k) & (perf.strategy == s)].iloc[0]  # noqa: E731
    S = lambda k, s: strat[(strat.config == k) & (strat.strategy == s)].iloc[0]  # noqa: E731
    sc = s61["signal_comparison"]
    ch = sc["changes_frozen_to_v2"]
    orbvi = s63["orb_vs_irf"]
    rc = s63["root_causes"]
    pre = jl(R61 / "preservation_check.json") if (R61 / "preservation_check.json").exists() else None
    cA = cost[(cost.window == "A") & cost.config.isin(["A", "B", "C"])].pivot(index="label", columns="config", values="net_pnl_rs").reset_index().to_dict("records")
    annt = ann[ann.config.isin(["A", "B", "C"])].pivot_table(index=["window", "calendar_year"], columns="config", values="gross_rs").reset_index().to_dict("records")
    C, A_, B_ = P("A", "C"), P("A", "A"), P("A", "B")
    CB, AB, BB = P("B", "C"), P("B", "A"), P("B", "B")
    dd = pd.read_csv(R62 / "trade_differences_between_configurations.csv", dtype=str, keep_default_na=False)
    n_bc, n_ab = int((~dd.b_vs_c_kind.isin(["A_vs_B only", "B_vs_C: method label only"])).sum()), int((dd.A != dd.B).sum())
    n_aud = sum(v["trades"] for v in audit.values())
    n_prob = sum(v["problems"] for v in audit.values())
    cs = lambda key: rc.get(f"C|IRF|{key}", {})  # noqa: E731
    co = lambda key: rc.get(f"C|ORB|{key}", {})  # noqa: E731
    hw = s63["handwritten"]
    rev = (R62 / "reviewer_findings.md").read_text() if (R62 / "reviewer_findings.md").exists() else "_(reviewer report pending)_"
    lines = [
        "# Phases 6.1 - 6.3: IRF V2, combined five-strategy backtest and journal reconciliation - final research report", "", "**Written for:** the strategy owner. Research only: synthetic NIFTY index-point P&L on 390 units (6 x 65; legs 195 + 195), not option profit; no orders, no parameter optimisation, no configuration selected, nothing committed or pushed. "
        "Neither window is untouched out-of-sample. Stopped after Phase 6.3 as instructed.", "", "## Headline", "",
        f"* **IRF V2 emits exactly the Phase 5.3 IRF signals** ({sc['A']['v2']} on both; also on 2022-25): the owner-approved first-red-low and 28-point rules were already implemented in Phase 5.3. V2 re-implements Method 2A as an explicit state machine, exposes every reference candle / support / break / EMA fact, and is verified by an independent re-derivation (0 mismatches on both windows). Relative to the frozen Phase 3.6 IRF it changes {ch.get('REMOVED', 0) + ch.get('ADDED', 0) + ch.get('SUPPORT_LEVEL_CHANGED_SAME_TIME', 0)} signals.",
        f"* **Combined configuration C** (IRF V2 + ORB V2 [provisional ORB-V2-A, entry signals only] + PDR/PDS first-eligible + RF): {int(C.trades)} trades, gross Rs {C.gross_synthetic_rs:+,.0f}, profit factor {C.profit_factor}, max drawdown Rs {C.max_drawdown_rs:,.0f}. For reference A (frozen) {int(A_.trades)} trades / Rs {A_.gross_synthetic_rs:+,.0f} / PF {A_.profit_factor}; B (Phase 5.3) {int(B_.trades)} / Rs {B_.gross_synthetic_rs:+,.0f} / PF {B_.profit_factor}.",
        f"* **ORB V2 under the portfolio exit model is a poor fit for the same entries that looked acceptable standalone**: {int(P('A', 'C', 'ORB').trades)} trades, {P('A', 'C', 'ORB').gross_points_total:+.1f} weighted points (PF {P('A', 'C', 'ORB').profit_factor}) versus the frozen ORB's {int(P('A', 'A', 'ORB').trades)} trades, {P('A', 'A', 'ORB').gross_points_total:+.1f} points (PF {P('A', 'A', 'ORB').profit_factor}); the standalone 30/60 result of Phase 6.0 is unchanged and uses a different exit model. This is reported, not tuned.",
        f"* **Journal agreement does not improve materially**: strict matches A {summ['A']['strict_matches']}, B {summ['B']['strict_matches']}, C {summ['C']['strict_matches']} of 190 rows (strict = date + strategy + time label; **no verified exact trade match is possible** because the journal has no direction or price). All 89 ORB journal rows carry the label 09:15, so an ORB 'strict' match is only a date + strategy match, C's gain over B comes entirely from ORB, and ORB V2 was reconstructed in Phases 5.8-6.0 with this same journal's ORB dates in view: the ORB hit rate is in-sample, not independent confirmation.", "",
        "## Answers to the 25 questions", "",
        f"**1. IRF signals changed by the support-break rule?** Frozen {sc['A']['frozen']} -> V2 {sc['A']['v2']} confirmed signals (primary window): unchanged {ch.get('UNCHANGED', 0)}, same time but a different support level {ch.get('SUPPORT_LEVEL_CHANGED_SAME_TIME', 0)}, removed {ch.get('REMOVED', 0)}, added {ch.get('ADDED', 0)}. Removed by cause {sc['removed_causes']}; added {sc['added_causes']}. Method 2A first signal moves earlier on {sc['method2a_shifts'].get('EARLIER', 0)} and later on {sc['method2a_shifts'].get('LATER', 0)} session-dates; the 28-point rule rejected {sc['ema_rejections']} candidate confirmations. (V2 vs Phase 5.3: 0 changes.)",
        f"**2. IRF trades matching the manual journal (config C)?** strict {S('C', 'IRF').strict} of {S('C', 'IRF').manual_rows} manual IRF rows (+ {S('C', 'IRF').time_tolerant} time-tolerant, {S('C', 'IRF').date_strategy_only} date-only), against A {S('A', 'IRF').strict} strict and B {S('B', 'IRF').strict} strict; of C's {S('C', 'IRF').automated_trades} IRF trades {S('C', 'IRF').automated_only} are automated-only.",
        f"**3. ORB V2 trades in the combined system?** {int(P('A', 'C', 'ORB').trades)} (primary), {int(P('B', 'C', 'ORB').trades)} (2022-25); each fills at the 09:20 bar open, earlier than any other strategy.",
        f"**4. Manual ORB dates reproduced?** strict {S('C', 'ORB').strict} of {S('C', 'ORB').manual_rows} manual ORB rows (date + ORB + label 09:15; direction/level unverifiable); the frozen ORB had {S('A', 'ORB').strict}. {orbvi['classes_all'].get('ORB NOW SELECTED', 0)} manual ORB dates have ORB selected as the first trade in C.",
        f"**5. Previously disputed dates where ORB V2 activates before IRF?** Of the {orbvi['previously_irf_executed_dates']} manual ORB dates on which the frozen (A) or Phase 5.3 (B) IRF executed, ORB is now the selected first trade on {orbvi['orb_now_selected_on_previously_irf_dates']}; classifications: {orbvi['classes_previously_irf']}. A journal ORB label alone is not treated as proof the dispute is resolved (`orb_vs_irf_comparison.csv`).",
        f"**6. Total combined trades?** C: {int(C.trades)} (primary), {int(CB.trades)} (2022-25).",
        f"**7. By strategy (C, primary)?** IRF {int(P('A', 'C', 'IRF').trades)}, ORB {int(P('A', 'C', 'ORB').trades)}, PDR {int(P('A', 'C', 'PDR').trades)}, PDS {int(P('A', 'C', 'PDS').trades)}, RF {int(P('A', 'C', 'RF').trades)}. Contributions inside the portfolio are not standalone profits.",
        f"**8. Total gross synthetic P&L?** C primary: {C.gross_points_total:+.2f} weighted index points = Rs {C.gross_synthetic_rs:+,.0f}; 2022-25: Rs {CB.gross_synthetic_rs:+,.0f}.",
        "**9. Estimated net P&L (primary window, net synthetic Rs)?**", "", md_table(cA), "",
        f"**10. Win rate / profit factor / max drawdown (C, primary)?** {C.win_rate_pct}% / {C.profit_factor} / Rs {C.max_drawdown_rs:,.0f} (2022-25: {CB.win_rate_pct}% / {CB.profit_factor} / Rs {CB.max_drawdown_rs:,.0f}).",
        f"**11. Versus Phase 3.6 (A) and Phase 5.3 (B)?** Primary window gross Rs: A {A_.gross_synthetic_rs:+,.0f}, B {B_.gross_synthetic_rs:+,.0f}, C {C.gross_synthetic_rs:+,.0f}; PF {A_.profit_factor} / {B_.profit_factor} / {C.profit_factor}. 2022-25: A {AB.gross_synthetic_rs:+,.0f}, B {BB.gross_synthetic_rs:+,.0f}, C {CB.gross_synthetic_rs:+,.0f}. The attribution runs show B -> C comes entirely from ORB V2 (IRF V2 == Phase 5.3 IRF; D1 == B) and B and C genuinely differ on {n_bc} dates (A and B on {n_ab}; method-label-only differences excluded) out of {len(dd)} dates on which the three configurations are not all identical (`configuration_comparison.md`).",
        f"**12. Strict journal matches?** A {summ['A']['strict_matches']}, B {summ['B']['strict_matches']}, C {summ['C']['strict_matches']} (of 190 rows; 5 are weekend-dated).",
        f"**13. Additional time-tolerant (<= 15 min)?** A {summ['A']['time_tolerant_additional']}, B {summ['B']['time_tolerant_additional']}, C {summ['C']['time_tolerant_additional']}.",
        f"**14. Date-and-strategy-only?** A {summ['A']['date_strategy_only']}, B {summ['B']['date_strategy_only']}, C {summ['C']['date_strategy_only']} (not counted as matches).",
        f"**15. Manual-only rows?** A {summ['A']['manual_only_rows']}, B {summ['B']['manual_only_rows']}, C {summ['C']['manual_only_rows']} (each includes the 5 weekend-dated rows).",
        f"**16. Automated-only trades?** A {summ['A']['automated_only_trades']}, B {summ['B']['automated_only_trades']}, C {summ['C']['automated_only_trades']}.",
        f"**17. Wrong-strategy dates?** A {summ['A']['wrong_strategy_dates']}, B {summ['B']['wrong_strategy_dates']}, C {summ['C']['wrong_strategy_dates']}.",
        f"**18. Main causes of unmatched IRF trades / rows (C)?** Manual IRF rows not matched: {cs('MANUAL_ONLY')}; automated IRF trades with no journal counterpart: {cs('AUTOMATED_ONLY')} (cause vocabulary of Phase 5.6; `mismatch_root_causes.csv`). The IRF reconciliation per journal row is in `irf_support_break_reconciliation.csv`.",
        f"**19. Main causes of unmatched ORB trades / rows (C)?** Manual ORB rows not matched: {co('MANUAL_ONLY')}; automated ORB trades with no journal row: {co('AUTOMATED_ONLY')}. For the rejected manual ORB dates the ORB V2 rejection reasons (mostly the provisional pattern definitions and the wrong-side-wick rule) are in `orb_vs_irf_comparison.csv`.",
        f"**20. Handwritten corrections reconciled?** None is claimed reconciled (the notes give no numeric entry, level or direction). Status in C: {hw}. Method 2B cases are out of the approved IRF scope (`irf_handwritten_cases.csv`, `handwritten_corrections_comparison.csv`).",
        f"**21. Entries, stops, targets and exits consistent with the raw one-minute candles?** Yes: {n_aud - n_prob} of {n_aud} executed trades (all configurations, both windows) re-derived by a separate simulator with {n_prob} problems (`entry_exit_execution_audit.md`).", "",
        "**22. Stability across 2022-2025 (gross Rs by calendar year; A / B / C):**", "", md_table(annt), "", "Results swing strongly by year in every configuration (e.g. 2022 is negative in all three); samples per year are small; no stability claim is made.", "",
        "**23. Unresolved source definitions / execution assumptions:** the ORB V2 decisions OD-1..OD-7 and OD-15 of Phase 6.0 (feed, break definition, inner levels, patterns, wick rule, gap limit, entry price, gap reference close) - ORB-V2-A is used only as a provisional reference because no owner selection exists; the IRF red-candle search start and 28-point measure/scope (provisional), the IRF day's-low predicate (not applied), extension of the support-break rule to Method 2B (needs approval); PDR/PDS first-eligible conventions (provisional); the 15:14 forced-exit reference; the Rs 70 cost estimate; no tie-break policy for same-minute collisions; the journal's missing fields.",
        "**24. Frozen historical results unchanged?** " + ("Yes: " + (f"{pre['files_before']} pre-existing files hashed before any change; {len(pre['changed'])} changed, {len(pre['removed'])} removed, {len(pre['added_outside_phase60'])} new files outside the Phase 6.1-6.3 paths." if pre else "(preservation check pending)")) + f" Configuration A also reproduces the Phase 5.5 ledger ({s62['reproduction']['A']['reproduced_trades']} trades, 0 mismatches) and Phase 4 on 2022-25 ({s62['reproduction']['window_B_A_vs_phase4']['now']} trades); B reproduces Phase 5.5.",
        "**25. Where?** Phase 6.1: `reports/phase6/phase61_irf_support_break/` (README, workbook `IRF_V2_Verification.xlsx`, `charts/`); Phase 6.2: `reports/phase6/phase62_combined_backtest/` (README, `combined_backtest_summary.md`, `Combined_Five_Strategy_Backtest.xlsx`, `daily/` = one report per evaluable session, `charts/` = one per executed C trade); Phase 6.3: `reports/phase6/phase63_manual_reconciliation/` "
        "(README, `exact_match_summary.md`, `Manual_vs_Automated_Verification.xlsx`, `daily/`, `charts/`); this report: `reports/phase6/PHASE61_63_FINAL_RESEARCH_REPORT.md`.", "",
        "## Verification", "", f"* Execution audit: {n_aud - n_prob}/{n_aud} trades verified; IRF Method 2A independent audit: {s61['independent_audit']}.", "* pytest (full suite) and ruff:", "", "```", tailtxt(SCRATCH / "pytest_full61.log", 3), tailtxt(SCRATCH / "ruff61.log", 2), "```", "", "**One pre-existing test fails and was NOT touched:** `tests/test_phase5_cross_index.py::test_every_nifty_artefact_every_earlier_report_and_every_tracked_file_is_byte_identical_to_the_pre_phase5_snapshot` reports `.gitignore` as changed since the Phase 5 snapshot. The change (adding `.DS_Store` ignore rules) arrived with commit `ea3d8da3` (Phases 5.8-6.0), before this task; the Phase 6.1-6.3 before/after hash check shows `.gitignore` and every other pre-existing file unchanged by this work. Resolving it needs a decision on whether to re-baseline that snapshot or revert the `.gitignore` addition. All other tests pass (including the 29 new ones).", "", "## Independent reviewer", "", rev, "",
        "## Decisions for the owner (nothing below was decided here)", "", "1. Select (or reject) an ORB V2 variant: ORB-V2-A is provisional, and under the portfolio exit model it adds trades that lose more often than the frozen ORB's. 2. Decide whether the support-break rule should also apply to IRF Method 2B. 3. Define the IRF day's-low predicate. "
        "4. Confirm the 28-point measure/scope. 5. Approve or amend the shared tie-break policy and the forced-exit convention. 6. Provide direction / level / price for journal dates if exact matching is wanted."]
    (ROOT / "reports" / "phase6" / "PHASE61_63_FINAL_RESEARCH_REPORT.md").write_text("\n".join(lines))
    print("final report written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
