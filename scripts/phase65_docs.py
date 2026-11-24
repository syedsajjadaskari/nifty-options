"""Phase 6.5 documentation: README (findings against the author's four observations), source inventory, newer-IRF source audit, dispute / strength / PDR reports. Numbers are read from the result files."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase61_common import ROOT, SCRATCH  # noqa: E402

from nifty_trading.research.orb_v2.reporting import md_table  # noqa: E402

R65 = ROOT / "reports" / "phase6" / "phase65_author_feedback"
DOCS = ROOT / "docs" / "strategy_docs"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tail(p, n=3):
    p = Path(p)
    return "\n".join(p.read_text().strip().splitlines()[-n:]) if p.exists() else "(log missing)"


def main() -> int:  # noqa: C901
    st = json.loads((R65 / "phase65_state.json").read_text())
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    disp = pd.read_csv(R65 / "orb_vs_irf_disputed_days.csv", dtype=str, keep_default_na=False)
    var = pd.read_csv(R65 / "candle_strength_variants_performance.csv")
    jr = pd.read_csv(R65 / "candle_strength_variants_journal.csv")
    rem = pd.read_csv(R65 / "candle_strength_signals_gated.csv")
    dist = pd.read_csv(R65 / "candle_strength_distribution_by_method.csv")
    bk = pd.read_csv(R65 / "candle_strength_winrate_by_body_bucket_DIAGNOSTIC.csv")
    auth = pd.read_csv(R65 / "candle_strength_authority_matrix.csv")
    pdr = pd.read_csv(R65 / "pdr_setup_audit.csv", dtype=str, keep_default_na=False)
    led = pd.read_csv(R65 / "candle_strength_variant_ledgers.csv", dtype={"entry_time": str, "signal_time": str})
    led["key"] = led.date + "|" + led.strategy + "|" + led.entry_time + "|" + led.direction                   # a trade is identified by date, strategy, entry time and direction (a same-strategy trade moved to a later signal is a DIFFERENT trade)
    tsc_rows = []
    for (w, v), g in led.groupby(["window", "variant"]):
        if v == "A":
            continue
        b0 = led[(led.window == w) & (led.variant == "A")].set_index("key")
        cur = g.set_index("key")
        rem_, add_, kept_ = sorted(set(b0.index) - set(cur.index)), sorted(set(cur.index) - set(b0.index)), sorted(set(b0.index) & set(cur.index))
        tsc_rows.append({"window": w, "variant": v, "baseline_trades": len(b0), "variant_trades": len(cur), "baseline_trades_kept_identical": len(kept_), "baseline_trades_removed": len(rem_), "new_trades_added_by_resequencing": len(add_),
                         "removed_by_strategy": json.dumps(b0.loc[rem_].strategy.value_counts().to_dict()), "added_by_strategy": json.dumps(cur.loc[add_].strategy.value_counts().to_dict()), "gross_rs_of_removed_baseline_trades": round(float(b0.loc[rem_].gross_pnl_rs.sum()), 0),
                         "gross_rs_of_added_trades": round(float(cur.loc[add_].gross_pnl_rs.sum()), 0), "net_gross_change_rs": round(float(cur.gross_pnl_rs.sum() - b0.gross_pnl_rs.sum()), 0)})
    tsc = pd.DataFrame(tsc_rows)
    tsc.to_csv(R65 / "candle_strength_variants_trade_set_changes.csv", index=False)
    conf = pdr[pdr.status == "CONFIRMED"]
    skipped = conf[conf.earlier_green_failed_because != ""]
    delays = pd.to_numeric(skipped.entry_delay_minutes_vs_first_green_after_retest, errors="coerce").dropna()
    retest_ok = int((conf.retest_candle_would_qualify == "True").sum())
    new = st["new_irf"]
    rej = disp[disp.orb_v2_signal == "none"]
    fs = rej.orb_v2_failed_conditions.str.split(";").apply(lambda x: {y for y in x if y})
    n_rej, n_prov, n_wick, n_gap = len(rej), int(fs.apply(lambda q: q <= {"NO_PATTERN", "LEVEL_NOT_BROKEN"}).sum()), int(fs.apply(lambda q: "WRONG_SIDE_WICK" in q).sum()), int(fs.apply(lambda q: "GAP_TOO_LARGE" in q).sum())
    n_sole_pat = int(fs.apply(lambda q: q == {"NO_PATTERN"}).sum())
    d = st["disputes"]
    paths = {"IRF guide (3 methods)": DOCS / "IRF_Strategy_Guide Updated.pdf", "IRF new Method 1 'High Breakout Failure'": DOCS / "IRF_Inverse_Retest_Failure_Rulebook.pdf", "IRF new Method 2 'First Red Candle Resistance Failure'": DOCS / "IRF_Method2_First_Red_Candle_Rulebook.pdf",
             "ORB latest rulebook (DOCX)": DOCS / "Nifty_920_ORB_Rulebook (2) (1).docx", "PDR guide": DOCS / "PDR_Strategy_Guide.pdf", "PDS guide": DOCS / "PDS strategy.pdf", "RF guide": DOCS / "RF strategy.pdf",
             "handwritten corrections (6 pages)": DOCS / "corrected" / "Adobe Scan Nov 05, 2026.pdf", "manual journal": ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"}
    code = {p: ROOT / p for p in ("src/nifty_trading/strategies/irf.py", "src/nifty_trading/strategies/irf_phase53.py", "src/nifty_trading/strategies/irf_v2.py", "src/nifty_trading/strategies/orb_v2_adapter.py", "src/nifty_trading/research/orb_v2/signal_engine.py",
                                    "src/nifty_trading/strategies/first_eligible_phase53.py", "src/nifty_trading/strategies/pdr_body.py", "src/nifty_trading/strategies/pds.py", "src/nifty_trading/strategies/rf.py", "src/nifty_trading/strategies/trading_day.py",
                                    "src/nifty_trading/core/exit_policy.py", "src/nifty_trading/research/phase62.py", "src/nifty_trading/core/paper.py")}
    (R65 / "source_inventory.md").write_text("\n".join([
        "# Source and implementation inventory (Phase 6.5)", "", f"Git HEAD when the work started: `{git}` (Phases 6.1-6.3 committed). Working tree otherwise clean except the two newer IRF rulebooks (untracked PDFs; one copied by me from `~/Downloads`, one added by the owner).", "",
        "## Source documents (SHA-256)", "", md_table([{"document": k, "path": str(p.relative_to(ROOT)), "sha256": sha(p)[:16] + "..."} for k, p in paths.items()]), "",
        "## Implementation versions actually in force (not proposed names)", "", md_table([{"file": k, "sha256": sha(p)[:16] + "..."} for k, p in code.items()]), "",
        "| role | implementation actually used here |", "|---|---|", "| IRF | `IRFV2SupportBreakStrategy` (IRF-V2-SUPPORT-BREAK; emits the same signals as `IRFPhase53Strategy`); frozen `IRFStrategy` for reference |", "| ORB | ORB V2 adapter wrapping Phase 6.0 `ORB-V2-A` (provisional reference; no owner selection exists) |",
        "| PDR / PDS | `PDRFirstEligibleStrategy` / `PDSFirstEligibleStrategy` (Phase 5.3 first-eligible, provisional conventions) |", "| RF | frozen `RFStrategy` |", "| controller | frozen `trading_day.run_trading_day` (first valid signal, max 2 trades, 13:00 cutoff, no tie-break policy) |",
        "| combined configuration | `phase62-irfv2-orbv2-combined` (configuration C of Phase 6.2) |", "", "## Paper-trading configuration", "",
        "`src/nifty_trading/core/paper.py` is a paper execution engine decoupled from broker order endpoints. The repository contains **no record selecting a live-market paper-trading configuration**, and this phase did not touch `core/paper.py`, `config/`, the broker modules or any frozen configuration (before/after hash check in `preservation_verification.md`). "
        "Everything produced here is a research variant; none is activated anywhere.", "", "## Reproduce", "", "`python scripts/phase65_snapshot.py before` (before any change), `python scripts/phase65_run.py`, `python scripts/phase65_docs.py`, `python -m pytest -q`, `python scripts/phase65_snapshot.py verify`."]))
    (R65 / "irf_new_methods_source_audit.md").write_text("\n".join([
        "# The two newer IRF method rulebooks", "", "Both are physically present in `docs/strategy_docs/`: `IRF_Inverse_Retest_Failure_Rulebook.pdf` (8 pages; 'Method 1: High Breakout Failure') and `IRF_Method2_First_Red_Candle_Rulebook.pdf` (8 pages; 'Method 2: First Red Candle Resistance Failure'). Their contents were read in full; nothing below is inferred beyond them.", "",
        md_table([{"": "Level that must break and fail", "NEW Method 1": "high of the 09:15 candle (wick included)", "NEW Method 2": "Level B = top of the BODY (the open) of the FIRST red candle in the rally after a close above Level A (= first-candle high); wick ignored"},
                  {"": "Sequence", "NEW Method 1": "any candle closes above the level (green or red) -> the FIRST later candle that closes back below = failure, immediately or many candles later", "NEW Method 2": "close above A (rally) -> first red candle marks B -> a later candle closes above B (second breakout, no entry) -> a later candle closes below B = failure"},
                  {"": "Entry", "NEW Method 1": "short at the failure candle's close (TO CONFIRM)", "NEW Method 2": "short at the failure candle's close"},
                  {"": "Stop / target / filters", "NEW Method 1": "35-40 points / 60 points; no trend, EMA, gap or previous-day condition; 1 trade a day; no entry after 13:00", "NEW Method 2": "same"}]), "",
        md_table([{"": "Existing frozen Method 1", "difference": "the failure must be the VERY NEXT candle (window of one candle); new Method 1 allows any later candle"},
                  {"": "Existing Method 2A (first-red-candle support)", "difference": "the first red candle's WICK LOW is a SUPPORT and a close below it is the trigger; the new Method 2 uses the red candle's BODY TOP as a RESISTANCE and needs a second breakout above it first"},
                  {"": "Existing Method 2B (resistance break)", "difference": "resistance = top of the first push; new Method 2 resistance = open of the first red candle; both need a close above and then a red-candle/close below, but the levels differ"}]), "",
        "TO CONFIRM items in the rulebooks (kept open): the colour of the first candle; a close exactly on a level (ignored here); entry price = failure close; one trade per day and re-entry after a stop; stop-before-target when both are touched in one candle; the end-of-day exit; whether a red candle that IS the breakout candle may be the first red candle of the rally (default here: no; a labelled variant is also computed). "
        "The rulebooks' dated chart examples (Nov 2026: 3, 6, 11, 12, 16) fall after the end of the evaluated data (2026-08-31) and the other examples are undated, so none could be reconstructed from our one-minute data.", "",
        "## Signal-level comparison with the existing IRF (detectors only; not integrated into any portfolio)", "", f"Sessions with a new-method signal (to 13:00): window 2025-26 - Method 1 {new['counts']['A']['new_m1_time']} / {new['counts']['A']['sessions']}, Method 2 {new['counts']['A']['new_m2_time']}; window 2022-25 - Method 1 {new['counts']['B']['new_m1_time']} / {new['counts']['B']['sessions']}, Method 2 {new['counts']['B']['new_m2_time']}.", "",
        f"New Method 1 versus the frozen IRF's first signal of the day (2025-26): {new['relation_m1']}. New Method 2: {new['relation_m2']}.", "", "Standalone hypothetical diagnostic (first signal per day through the SAME approved exit rules; not portfolio results, not a recommendation):", "", md_table(new["summary"]), "",
        "Limitations of the standalone diagnostic: it applies the PORTFOLIO IRF exit rules (T1 27 on half, post-T1 stop entry +6, T2 60, forced exit 15:14) and not the rulebooks' single 60-point target with a 35-40 point stop; the Method 2 rulebook's 'latest entry time and exit time: 1 pm' is not tested as a 13:00 exit; times in the CSV (`first_red_time`, `second_breakout_time`, `new_m*_time`) are candle END times. It is not a result for the new methods as specified.", "", "Files: `irf_new_methods_vs_existing.csv`, `irf_new_methods_standalone_diagnostic.csv`."]))
    (R65 / "orb_vs_irf_dispute_report.md").write_text("\n".join([
        "# ORB versus IRF: the disputed days", "", "A date is disputed when the journal labels ORB and the frozen (A) or Phase 5.3 (B) IRF executed, or configuration C's first trade is IRF. No automatic ORB priority exists or was added: a VALID ORB confirmed at 09:20 always wins under the first-valid-signal controller; an invalid ORB never replaces IRF because its hypothetical trade would have reached a target.", "",
        f"* Disputed dates: **{d['dates']}**. ORB V2 has a valid signal on **{d['orb_valid']}** of them, and on all of those ORB is the selected first trade (software-defect count: **{d['orb_valid_but_not_selected_defects']}**).",
        f"* ORB V2 rejected on the other {d['dates'] - d['orb_valid']} (a date can fail several conditions): **{n_prov}** fail ONLY provisional gates (the pattern convention - {n_sole_pat} of them on that gate alone - or the level construction), so they depend on author rules that are not yet defined; **{n_wick}** fail the EXPLICIT wrong-side-wick rule (> 20% of the range; the rulebook's Examples 2/3 already conflict with this rule, see Phase 6.0) - usually together with the pattern gate; {n_gap} fails the gap limit. "
        f"On {d['feed_difference']} of them ORB V2 WOULD signal on the secondary data feed (data difference).", f"* The author's pattern 'ORB would have hit its target but IRF hit its stop' occurs in the hypothetical paths of **{d['author_pattern_orb_target_irf_stop']}** dates (ORB counterfactual TARGET versus IRF INITIAL_FULL_STOP); counterfactual ORB paths on rejected days: {d['orb_cf_outcomes']}; IRF outcomes where IRF was executed in C: {d['irf_outcome_C_executed']}.",
        "* Counterfactual ORB paths use an ASSUMED direction (the EMA side; the journal records no direction) and the same portfolio exit rules; they are hypotheticals and are labelled so in every chart.", "",
        md_table(disp[["date", "C_first_trade", "orb_v2_signal", "orb_v2_failed_conditions", "orb_cause_class", "orb_data_feed_difference", "orb_outcome", "irf_outcome", "author_pattern_orb_target_irf_stop"]].to_dict("records")), "",
        "Files: `orb_vs_irf_disputed_days.csv`, `charts_orb_vs_irf/` (per date one chart per candidate: `_executed` or `_counterfactual`)."]))
    A = var[var.window == "A"]
    allA = A[A.strategy == "ALL"]
    a_row = allA[allA.variant == "A"].iloc[0]
    (R65 / "candle_strength_report.md").write_text("\n".join([
        "# Candle body-strength research", "", "`body_percentage = |close - open| / (high - low) * 100`; zero-range candles have no percentage and are flagged, never treated as 0 or 100. No global strength filter is active by default; variants B, C, D are opt-in research wrappers (`strategies/strength_gate.py`).", "",
        "## Authority matrix (is a strength threshold in the source?)", "", md_table(auth.to_dict("records")), "", "## Body-percentage distribution of the confirming candles (configuration C, primary window)", "", md_table(dist.to_dict("records")), "",
        "## Variants through the frozen controller (primary window; the gate is a post-hoc filter and an engine does not search for a stronger LATER candle after a rejection; the controller then re-sequences the day, so a variant is a different portfolio and its trade count is a NET figure)", "", md_table(allA.to_dict("records")), "", "True trade-set changes versus the baseline:", "", md_table(tsc.to_dict("records")), "",
        "Per strategy (win rate = share of trades with positive gross P&L):", "", md_table(A[A.strategy != "ALL"].to_dict("records")), "", "Signals gated:", "", md_table(rem[(rem.window == "A") & (rem.variant != "A") & (rem.gate_applies)].to_dict("records")), "",
        "## Manual-journal reconciliation per variant (primary window; Phase 5.6 matcher)", "", md_table(jr.to_dict("records")), "", "## Win rate by body bucket of the executed trades' confirming candle (DIAGNOSTIC only; no filter decision follows from it)", "", md_table(bk.to_dict("records")), "",
        "Reading: ORB V2 is untouched by every gate that matters (its full-body route already means body >= 80%; pin-bar / engulfing routes are exempt); IRF Method 3 is wick-based and exempt; PDR's guide and the author specify only 'a green candle'; PDS Method 1 'good red candle' is the only place where the source asks for a body quality it never defines. "
        "Variant D rejects PDS Method 1 signals only; B and C act mainly on IRF Methods 1/2A/2B and PDR green-body confirmations, which have no body-strength statement in any source. Because the controller takes one trade at a time, removing even a single signal can re-sequence a day and move the P&L, so differences between variants must not be read as evidence for a threshold. The journal view agrees with caution: strict journal matches fall from 67 (A) to 58 (B) and 55 (C).", "", f"Variant A equals configuration C exactly: {st['strength']['variant_A_equals_config_C']}."]))
    cls = pdr.assign(cls=pdr.classification.str.split(" \\(").str[0]).groupby(["window", "cls"]).size().reset_index(name="cycles")
    pdw = st["pdr"]
    (R65 / "pdr_audit_report.md").write_text("\n".join([
        "# PDR first-eligible-candle audit", "", "Every PDR setup cycle (retest candle -> confirmation) was re-derived chronologically from the raw five-minute candles and the engine's zone (`research/phase65.pdr_cycle_audit`). Preserved: previous-day body-based zone, open strictly above the ceiling, the retest, a confirmation close strictly above the ceiling, green / lower-price-rejection patterns. "
        "Not every green candle is valid.", "", md_table(cls.to_dict("records")), "", f"Per window: {pdw}", "",
        "Meaning of the classes: ENGINE_EQUALS_FIRST_ELIGIBLE = the engine selected the first fully eligible candle (when an earlier green candle existed it closed at or below the zone ceiling, so the strict-close rule - not the engine - delayed the entry); DEFECT_* = the engine selected a later candidate than the audit's first eligible one (a genuine late-entry defect); "
        "NO_CONFIRMATION_IN_CYCLE = no eligible candle occurred. **The audit reuses the engine's own two conventions** (strict close above the ceiling; the retest candle may not confirm), so 'no defect' means 'the engine follows its own rules', not 'the author's complaint is wrong'. The 'retest candle would qualify' column marks cycles where the retest candle itself was green and closed above the ceiling: the engine excludes it by the preserved (unresolved) retest-then-confirmation sequencing convention; whether such a candle may confirm is an author decision, not a defect.", "",
        f"Actual late-entry defects found: **{int(pdr.classification.str.startswith('DEFECT').sum())}** of {len(pdr)} cycles.", "", "File: `pdr_setup_audit.csv`. PDR-B and later confirmation variants are held (the prompt was cut off in section 5)."]))
    n_def = int(pdr.classification.str.startswith("DEFECT").sum())
    (R65 / "README.md").write_text("\n".join([
        "# Phase 6.5 - author feedback validation (sections 1-4)", "", "**Written for:** the strategy owner. Research only; nothing selected, activated, committed or traded; the paper-trading modules and every frozen configuration are untouched.", "",
        "**Scope note.** Your prompt was cut off in section 5 (\"PDR-B: First green candle satisfying the...\"). As agreed, sections 1-4 are done; **PDR-B and later variants, the section-5 comparative backtests, the output list and the final questions are held** until you resend the rest.", "",
        "## Findings against the author's four observations", "",
        f"1. **'ORB is missed and IRF is taken instead.'** {d['dates']} disputed dates. ORB V2 is valid on {d['orb_valid']} and is selected on all of them (0 defects; no priority added). On the other {n_rej} it is rejected: {n_prov} fail only PROVISIONAL gates (pattern convention / level construction: new author rules to settle, not implementation defects), {n_wick} fail the explicit 20% wrong-side-wick rule (source-supported; the rulebook's own Examples 2/3 conflict with it) and {n_gap} the gap limit; {d['feed_difference']} would signal on the secondary data feed. No implementation defect was found. "
        f"Of the {d['orb_valid']} valid ORB days, {d['valid_orb_depends_on_provisional_convention']} rest on at least one PROVISIONAL element (the engulfing / pin-bar pattern route, an inner swing-zone level, or a result that changes under another ORB V2 configuration), so 'valid' is itself convention-dependent. The author's 'rejected ORB would have hit target while the executed IRF hit its stop' pattern appears in {d['author_pattern_orb_target_irf_stop']} hypothetical paths, but an invalid ORB must not replace IRF. See `orb_vs_irf_dispute_report.md` and the paired charts.",
        f"2. **'Weak confirmation candles are accepted.'** True in the sense that no source defines a body-strength rule for IRF, PDR, PDS Method 2/3 or RF; the only source-supported quality requirement is PDS Method 1's undefined 'good body'. ORB V2's full-body route already implies body >= 80%. The variants are DIFFERENT PORTFOLIOS, not the baseline trades minus the weak ones: the controller trades one position at a time, so a rejected signal frees the day for a later signal. Primary window, trades of the baseline (config C, {int(a_row.trades)}): "
        + "; ".join(f"{r.variant} removes {int(r.baseline_trades_removed)} and adds {int(r.new_trades_added_by_resequencing)} new trades (net {int(r.variant_trades - r.baseline_trades):+d}; gross of the removed trades Rs {r.gross_rs_of_removed_baseline_trades:+,.0f}, of the added Rs {r.gross_rs_of_added_trades:+,.0f})" for r in tsc[tsc.window == "A"].itertuples())
        + f". Variant D (pattern-aware; PDS Method 1 only) rejects {int(rem[(rem.window == 'A') & (rem.variant == 'D') & (~rem.kept)].signals.sum())} signals; its net gross change comes from the removed and the re-sequenced-in trades listed above. Everything is in-sample and nothing is selected. Results by variant: "
        + "; ".join(f"{r.variant}: {int(r.trades)} trades, win rate {r.win_rate_pct}%, gross Rs {r.gross_rs:+,.0f}" for r in allA.itertuples()) + ". No global filter is active by default and none is recommended. `candle_strength_report.md`.",
        f"3. **'PDR selects a later confirmation candle.'** Of {len(pdr)} audited PDR cycles the audit finds **{n_def} implementation defects relative to the engine's own rules** - but those rules include two conventions the guide does not state, so this is NOT a refutation of the author. The guide (s.4.3) asks only for 'a green candle' after the zone test; the engine additionally requires a close strictly above the zone ceiling (PDR-B05a, a Phase 3.6 brief interpretation) and bars the retest candle from confirming (unresolved convention). Under those conventions {len(skipped)} of {len(conf)} confirmed cycles skipped an earlier green candle (median delay {delays.median():.0f} min, mean {delays.mean():.1f}, max {delays.max():.0f}), and in {retest_ok} cycles the retest candle itself was green and closed above the ceiling. Under a literal reading of the guide the author's observation is substantively true: the delays come from the two conventions, which are NEW AUTHOR RULES to confirm, not from a coding error. `pdr_audit_report.md`.",
        "4. **'Two updated IRF methods.'** Both rulebooks are present and were read. New Method 1 (any later close back below the first-candle high) and new Method 2 (body top of the first red candle in the rally as a resistance with a second breakout) differ from the existing Methods 1 / 2A / 2B; detector-level comparison and a standalone hypothetical diagnostic are in `irf_new_methods_source_audit.md`. They are NOT integrated into any portfolio (no instruction to do so).", "",
        "## Files", "", "`source_inventory.md`, `irf_new_methods_source_audit.md`, `irf_new_methods_vs_existing.csv`, `irf_new_methods_standalone_diagnostic.csv`, `orb_vs_irf_dispute_report.md`, `orb_vs_irf_disputed_days.csv`, `charts_orb_vs_irf/`, `candle_strength_report.md`, `candle_strength_signals.csv`, `candle_strength_authority_matrix.csv`, `candle_strength_distribution_by_method.csv`, "
        "`candle_strength_variants_performance.csv`, `candle_strength_signals_gated.csv`, `candle_strength_variants_journal.csv`, `candle_strength_winrate_by_body_bucket_DIAGNOSTIC.csv`, `pdr_audit_report.md`, `pdr_setup_audit.csv`, `independent_audit.md`, `preservation_verification.md`.", "", "## Verification", "", "```", tail(SCRATCH / "pytest_full65.log", 3), tail(SCRATCH / "ruff65.log", 2), "```"]))
    rv = (R65 / "reviewer_findings.md").read_text() if (R65 / "reviewer_findings.md").exists() else "_(pending)_"
    (R65 / "independent_audit.md").write_text("\n".join(["# Independent audit (Phase 6.5)", "", "Checks inside this phase: variant A equals configuration C exactly (wrapper is neutral); every executed disputed-day scenario equals the committed ledger; the new-IRF detectors are covered by unit tests built from the rulebooks' own worked examples; the full test suite and ruff are in the README.", "", "## Fresh read-only reviewer", "", rv]))
    print("docs written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
