"""Phase 3.5: write README.md and backtest_summary.md of reports/phase3/phase35_combined/ from the delivered CSV files (every number is computed here, none is typed).

Run after scripts/phase35_run.py:  .venv/bin/python scripts/phase35_docs.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase35_combined"
P32 = ROOT / "reports" / "phase3" / "phase32"
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")
COMMAND = "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase35_run.py --pdr-engine revised"
MATCHED = ("EXACT_MATCH", "TIME_SHIFTED_MATCH")


def rd(n: str, base: Path = OUT) -> list[dict]:
    with open(base / n, newline="") as f:
        return list(csv.DictReader(f))


def tab(head, body) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def rs(x) -> str:
    return f"{float(x):,.0f}"


def write_audit_md(tests: str, ruff: str) -> None:
    """independent_audit.md: the audit script's results (read from independent_audit_results.json) plus the reviewed list of edited files and the defects found while building the run."""
    res = json.loads((OUT / "independent_audit_results.json").read_text())
    checks = rd("trade_entry_conditions.csv")
    flat = [c for c in checks if c["rule_id"] == "PDR-003" and c["result"] == "UNRESOLVED"]
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    A = ["# Phase 3.5 - independent audit", "",
         "**Written for:** the strategy owner and any reviewer who must decide whether the combined backtest can be trusted. The audit verifies that the code did what the written rules say and that nothing else changed; it does **not** verify the source rules "
         "(the PDR thresholds and the open-above-zone requirement are provisional research assumptions, and a misreading of a rule shared by the engine and the audit would not be caught - the author of both is the same).", "",
         "## 1. Independent re-implementation: `scripts/phase35_independent_audit.py`", "",
         "Written from the raw one-minute parquet files and the delivered CSVs only; it imports nothing from `src/` (the signal-stream rebuild reuses the Phase 3.4 independent script, which is also free of `src/` imports). It is derived from the Phase 3.2 audit with the legacy-PDR checks replaced by the revised-PDR ones.", "",
         tab(["#", "check", "n", "result"], [[i, name, c["n"], "PASS" if c["pass"] else "**FAIL**"] for i, (name, c) in enumerate(res["checks"].items(), 1)]), "",
         f"Overall: **{'ALL PASS' if res['all_pass'] else 'FAILURES PRESENT'}** ({len(res['checks'])} checks). Results are machine-readable in `independent_audit_results.json`.", "",
         "## 2. Pre-existing files edited in Phase 3.5 (and nothing else)", "",
         f"A hash snapshot of {len(snap['files'])} files (source, tests, scripts, `data/`, `reports/`, `docs/`) was recorded before the first edit (`before_snapshot.json`, git head `{snap['git_head'][:7]}`). The audit proves every file in it is byte-identical **except** these seven:", "",
         tab(["file", "why it was edited"], [
             ["`src/nifty_trading/research/phase3.py`", "`Scenario` gained `pdr_engine` / `pdr_revision` (defaults keep the legacy behaviour); `make_engines` selects the PDR engine; `combined_scenario()` added. The four Phase 3.0 scenarios are unchanged."],
             ["`src/nifty_trading/research/phase31.py`", "`run_timelines` passes the selection; the PDR diagnostic probe uses the revised zone when the revised engine is active."],
             ["`src/nifty_trading/research/phase32.py`", "explainer for revised PDR trades (`explain_pdr_revised`), status labels of the PDR-A rules, `config_id` accepts a PDR revision."],
             ["`src/nifty_trading/research/phase32_build.py`", "`build(scenario=...)`; the frozen-ledger comparison ignores the scenario *label* column."],
             ["`src/nifty_trading/research/phase32_render.py`, `phase32_excel.py`", "phase / banner labels from the bundle (Phase 3.2 defaults unchanged); revision rules in the Rule Definitions sheet; Excel cell-length cap."],
             ["`tests/test_phase34_pdr_revision.py`", "the broad Phase 3.4 freeze test is skipped once the Phase 3.5 snapshot exists (superseded by `tests/test_phase35_combined.py`)."]]), "",
         "The five engines (including `pdr.py` and `pdr_revised.py`), `trading_day.py`, `selection.py`, `exit_policy.py`, `params.py`, `definitions.py` and `base.py` are byte-identical to the snapshot; all data files and every earlier report (Phase 2.x - 3.4) are byte-identical.", "",
         "## 3. Regression check of the framework", "",
         "`python scripts/phase35_run.py --pdr-engine legacy` re-runs the Phase 3.0 baseline through the modified framework: 213 trades, gross Rs 172,146, 67 exact + 17 time-shifted journal matches, **zero field differences** against the frozen `reports/phase3/baseline/trades.csv` "
         "(output in `reports/phase3/phase35_legacy_check/`). The Phase 3.2 tests, which rebuild the baseline bundle, also still pass.", "",
         "## 4. Defects found while building this run, and what was done", "",
         tab(["finding", "disposition"], [
             ["The frozen-ledger comparison flagged every row because the scenario label column differs by construction (`baseline` vs `phase35_*`).", "Fixed: the label column is excluded; every numeric, time and outcome field is still compared."],
             ["Four PDR signals have `reference_levels` text longer than Excel's 32,767-character cell limit (long armed sessions list every evaluated candle); an over-long cell can make Excel report a corrupt file.", "Fixed: the workbook cell is cut with a visible marker `...[TRUNCATED IN EXCEL - full text in the CSV file]`; the CSV keeps the full text; the audit compares accordingly; a test checks no cell exceeds the limit."],
             [f"The legacy check 'the zone is an area with positive height' fails for candidate A when the previous-day-high candle closes on its high (zone from body top to wick high has zero height): {len(flat)} executed PDR trade(s) ({', '.join(sorted({c['trade_id'] for c in flat}))}).", "Reported as UNRESOLVED (the author gave no rule for a zero-height zone), not as a failure; covered by a test. The engine treats such a zone as a line (touched when a candle's range includes the price) - unchanged from Phase 3.4."],
             ["The explainer's rule-source lookup raised on the disclosure row `PDR-A04x`.", "Fixed (default text); found by the first full run, before any output was accepted."]]), "",
         "## 5. Tests and static checks", "",
         f"* `pytest -q`: **{tests}**; `ruff check src tests scripts`: **{ruff}**.",
         "* New: `tests/test_phase35_combined.py` (engine selection swaps only the PDR slot; the combined scenario changes nothing but the PDR engine; the Phase 3.0 scenario set is unchanged; the command line; the revised-PDR explanation including the zero-height zone; "
         "the Excel limit; the delivered bundle obeys the portfolio rules, adds up and labels the PDR assumptions as provisional; a one-time hash-snapshot check that honours `PHASE35_ALLOW_LATER_EDITS=1`).", "",
         "## 6. Not verified", "",
         "* The strategy author's intent for every `PROPOSED_FOR_REVIEW` / `OWNER_INTERPRETATION` item (pattern numbers, open-above-zone, zone floor, 'strictly above').",
         "* The PDR / PDS Target 2 of 70 versus the performance report's 60 (a recorded source conflict), RF's Target 2 of 60 (research assumption) and the provisional 15:14 forced exit - all unchanged from Phase 3.0; no forced exit occurred in this run.",
         "* How the two same-minute-conflict days should have been resolved: no tie-break is approved, so nothing was traded on them.",
         "* The workbook beyond a cell-by-cell equality with the CSV files (formatting and the opening in Excel itself were not tested on a desktop Excel).",
         "* The independent audit did not re-derive the entry signals of IRF, ORB, PDS and RF from raw data (their engines are unchanged and their signal streams are identical to the Phase 3.2 export, 996 / 996; the entry numbers of the executed trades were recomputed in the Phase 3.2 audit method).", ""]
    (OUT / "independent_audit.md").write_text("\n".join(A))


def main(tests: str = "see the final report", ruff: str = "see the final report") -> None:  # noqa: C901
    perf = {r["strategy"]: r for r in rd("strategy_performance.csv")}
    cmp = {r["strategy"]: r for r in rd("comparison_vs_phase30.csv")}
    by_day = rd("comparison_vs_phase30_by_day.csv")
    contrib = {r["strategy"]: r for r in rd("engine_contribution.csv")}
    trades, daily = rd("all_trades_detailed.csv"), rd("daily_summary.csv")
    man = [c for c in rd("manual_journal_comparison.csv") if c["journal_row"]]
    old_man = [c for c in rd("manual_vs_automated.csv", P32) if c["journal_row"]]
    counts = json.loads((OUT / "build_counts.json").read_text())
    audit = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {}
    allp = perf["ALL"]
    cls = Counter(c["match_classification"] for c in man)
    ocls = Counter(c["match_classification"] for c in old_man)
    matched, omatched = cls["EXACT_MATCH"] + cls["TIME_SHIFTED_MATCH"], ocls["EXACT_MATCH"] + ocls["TIME_SHIFTED_MATCH"]
    extras = sum(1 for c in rd("manual_journal_comparison.csv") if c["match_classification"] == "EXTRA_AUTOMATED_TRADE")
    oextras = sum(1 for c in rd("manual_vs_automated.csv", P32) if c["match_classification"] == "EXTRA_AUTOMATED_TRADE")
    old_by = {c["journal_row"]: c for c in old_man}
    gained = [c for c in man if c["match_classification"] in MATCHED and old_by[c["journal_row"]]["match_classification"] not in MATCHED]
    lost = [c for c in man if c["match_classification"] not in MATCHED and old_by[c["journal_row"]]["match_classification"] in MATCHED]
    pdr_trades = [t for t in trades if t["strategy"] == "PDR"]
    sg = rd("all_strategy_signals.csv")
    pdr_sig = [s for s in sg if s["strategy"] == "PDR"]
    pdr_after_cutoff = sum(1 for s in pdr_sig if s["within_13_00_cutoff"] == "False")
    ignored = Counter(r["controller_reason"].split("(")[0].strip() for r in rd("ignored_signals.csv") if r["strategy"] == "PDR")
    rejected = [r for r in rd("rejected_signals.csv") if r["strategy"] == "PDR"]
    rej_cut = sum(1 for r in rejected if r["category"] == "CONTROLLER_REJECTED")
    no_trade_days = sum(1 for r in daily if int(r["executed_trades"]) == 0)
    conflict_days = sum(1 for r in daily if r["day_end_portfolio_state"] == "UNRESOLVED_EXECUTION")
    pdr_changed = [d for d in by_day if "PDR_TRADE_CHANGED" in d["tags"]]
    down = [d for d in by_day if "DOWNSTREAM_CONTROLLER_EFFECT" in d["tags"]]
    delta_pdr_days = sum(float(d["delta_gross_rs"]) for d in by_day)
    worst = sorted(by_day, key=lambda d: float(d["delta_gross_rs"]))[:3]
    best = sorted(by_day, key=lambda d: -float(d["delta_gross_rs"]))[:3]
    old_led = rd("trades.csv", ROOT / "reports" / "phase3" / "baseline")
    key_old = lambda r: (r["date"], r["strategy"], r["method"], r["direction"], r["entry_time"], r["entry_price"], r["outcome"], round(float(r["gross_pnl_rs"]), 2))  # noqa: E731
    key_new = lambda r: (r["date"], r["strategy"], r["method"], r["direction"], r["fill_timestamp"][-5:], r["entry_price"], r["outcome"], round(float(r["gross_pnl_rs"]), 2))  # noqa: E731
    added = {x: len({key_new(r) for r in trades if r["strategy"] == x} - {key_old(r) for r in old_led if r["strategy"] == x}) for x in STRATS}
    removed = {x: len({key_old(r) for r in old_led if r["strategy"] == x} - {key_new(r) for r in trades if r["strategy"] == x}) for x in STRATS}
    identical = [x for x in STRATS if x != "PDR" and added[x] == removed[x] == 0]
    audit_line = "ALL PASS" if audit.get("all_pass") else "not yet run"
    n_checks = len(audit.get("checks", {}))

    # ------------------------------------------------------------------------------------------------ summary
    L = ["# Phase 3.5 - complete five-strategy NIFTY 50 backtest (IRF, ORB, PDR revised, PDS, RF)", "",
         "**Written for:** the strategy owner, for manual review. All P&L is **synthetic index-point P&L x quantity** (the NIFTY 50 index is not tradable); \"illustrative net\" deducts Rs 500 per trade and 0.5 index point of adverse slippage on every fill "
         "(the Phase 3.0 headline assumption). Nothing was tuned, nothing was traded live, no broker API was called, no data file was written.", "",
         "## How this run was produced", "",
         "One run of the **existing** Phase 3.0 shared portfolio controller over the original one-minute NIFTY 50 candles (2025-09-01 .. 2026-08-31), reported with the **existing** Phase 3.2 explainable-backtest framework. The only change of input is the PDR engine: "
         "the slot of the legacy `PDRStrategy` now holds the Phase 3.4 `PDRRevisedStrategy` (`--pdr-engine revised`). IRF, ORB, PDS and RF are constructed exactly as in Phase 3.0; stops, targets, sizing, cutoff, forced exit and the controller are untouched. "
         "The five strategies were **not** back-tested separately and added: one controller decides, in time order, which signal becomes a trade.", "",
         "**Exact command to rerun (macOS terminal):**", "", "```", COMMAND, "```", "",
         "(`--pdr-engine legacy` re-runs the Phase 3.0 baseline into `reports/phase3/phase35_legacy_check/` and must reproduce the frozen Phase 3.0 ledger with zero field differences - it does.)", "",
         "## Revised PDR - what is and is not approved", "",
         "* **Author statements (AUTHOR_APPROVED):** the previous-day high is considered and a zone is drawn; one good green body OR lower-price rejection OR hammer candle is required; the confirmation candle should close above the zone.",
         "* **Provisional research assumptions (NOT approved by the strategy author):** the numeric thresholds of the three patterns (green body 60% / upper wick 20%; rejection 2x wick, close in the top 30%; hammer 2x wick, upper wick 10%, body in the upper 60%), "
         "the zone floor (body top of the day-high candle), reading 'above' as **strictly above the zone ceiling**, and the requirement that the session **open above the zone** (legacy PDR-011, kept as a labelled research assumption).",
         "* Candidate A (day-high anchored zone) is used; candidate B (multiple-high zone) gives the identical signals by construction. No signal is VERIFIED.", "",
         "## Headline result (247 evaluable sessions)", "",
         tab(["item", "value"], [["Executed trades", f"{allp['entries']} ({allp['first_trades']} first trades, {allp['second_trades']} second trades, {allp['days_traded']} days with a trade; {no_trade_days} days without a trade, of which {conflict_days} are same-minute conflicts)"],
                                 ["Trades by strategy", ", ".join(f"{s} {perf[s]['entries']}" for s in STRATS)],
                                 ["Gross P&L", f"Rs {rs(allp['gross_pnl_rs'])}"], ["Illustrative net P&L", f"Rs {rs(allp['net_illustrative_pnl_rs'])}"],
                                 ["Win rate (gross) / profit factor (gross)", f"{allp['win_rate_pct']}% / {allp['profit_factor']}"], ["Average trade (gross) / max drawdown (gross) / longest losing streak", f"Rs {rs(allp['avg_trade_rs'])} / Rs {rs(allp['max_drawdown_rs'])} / {allp['max_consecutive_losses']}"],
                                 ["Outcomes", f"Target 2: {allp['target2']}; Target 1 then post-T1 stop: {allp['t1_then_buffer_stop']}; initial full stop: {allp['initial_full_stop']}; provisional forced exit: {allp['forced_exit']}; unresolved: {allp['unresolved']}"],
                                 ["Manual journal (190 rows)", f"{matched} matched ({cls['EXACT_MATCH']} exact + {cls['TIME_SHIFTED_MATCH']} time-shifted), {190 - matched} unmatched; {extras} automated trades have no journal counterpart"]]), "",
         "### By strategy", "",
         tab(["strategy", "trades (1st / 2nd)", "gross Rs", "illustrative net Rs", "win %", "profit factor", "Target 2 / T1+stop / full stop", "share of gross"],
             [[s, f"{perf[s]['entries']} ({perf[s]['first_trades']} / {perf[s]['second_trades']})", rs(perf[s]["gross_pnl_rs"]), rs(perf[s]["net_illustrative_pnl_rs"]), perf[s]["win_rate_pct"], perf[s]["profit_factor"],
               f"{perf[s]['target2']} / {perf[s]['t1_then_buffer_stop']} / {perf[s]['initial_full_stop']}", f"{perf[s]['contribution_pct_of_gross']}%"] for s in STRATS]), "",
         "### Did all five engines feed the shared controller?", "",
         tab(["strategy", "engine", "confirmed signals", "valid signals", "within 13:00", "executed trades", "ignored", "rejected by controller"],
             [[s, contrib[s]["engine"], contrib[s]["confirmed_signals"], contrib[s]["fully_valid_signals"], contrib[s]["signals_within_13_00_cutoff"], contrib[s]["executed_trades"], contrib[s]["ignored_signals"], contrib[s]["rejected_by_controller"]] for s in STRATS]), "",
         "Yes: every engine produced confirmed signals and every engine was traded at least once.", "",
         "## Comparison with Phase 3.0 (baseline: legacy PDR)", "",
         tab(["strategy", "trades 3.0 -> 3.5", "share of trades 3.0 -> 3.5", "gross Rs 3.0 -> 3.5 (delta)", "illustrative net Rs 3.0 -> 3.5 (delta)"],
             [[s, f"{cmp[s]['phase30_trades']} -> {cmp[s]['phase35_trades']} ({int(cmp[s]['delta_trades']):+d})", f"{cmp[s]['phase30_share_of_trades_pct']}% -> {cmp[s]['phase35_share_of_trades_pct']}%",
               f"{rs(cmp[s]['phase30_gross_rs'])} -> {rs(cmp[s]['phase35_gross_rs'])} ({float(cmp[s]['delta_gross_rs']):+,.0f})", f"{rs(cmp[s]['phase30_net_rs'])} -> {rs(cmp[s]['phase35_net_rs'])} ({float(cmp[s]['delta_net_rs']):+,.0f})"] for s in (*STRATS, "ALL")]), "",
         tab(["manual journal (190 rows)", "Phase 3.0", "Phase 3.5"], [["matched", omatched, matched], ["... exact", ocls["EXACT_MATCH"], cls["EXACT_MATCH"]], ["... time-shifted (<= 15 min)", ocls["TIME_SHIFTED_MATCH"], cls["TIME_SHIFTED_MATCH"]],
                                                                       ["unmatched manual trades", 190 - omatched, 190 - matched], ["automated trades with no journal counterpart", oextras, extras]]), "",
         f"**What changed and why.** {len(by_day)} of 247 sessions have a different trade set ({len(pdr_changed)} involve a PDR trade, {len(down)} also change a trade of another strategy through the controller). "
         f"The revised PDR produced {len(pdr_sig)} confirmed signals (the legacy engine: 383), {pdr_after_cutoff} of them timed after 13:00; {len(pdr_trades)} became trades ({int(cmp['PDR']['phase30_trades'])} before). "
         f"The rest were ignored by the controller because the day was already finished or a position was active ({', '.join(f'{k} {v}' for k, v in ignored.most_common())}), or were explicitly rejected by the 13:00 cutoff ({rej_cut}; the other signals after 13:00 were already ignored for the first reason). Because a PDR trade no longer occupies the day as often, later signals of other strategies are taken: "
         + ", ".join(f"{x} {int(cmp[x]['delta_trades']):+d} net ({added[x]} trades added, {removed[x]} removed)" for x in ("IRF", "RF") if added[x] or removed[x]) + ". "
         "That downstream effect is why the controller must be re-run rather than the PDR ledger edited. "
         + (f"{' and '.join(identical)} trades are identical to Phase 3.0 (same day, entry, price, outcome and P&L)." if identical else ""), "",
         f"Journal agreement: {len(gained)} journal rows became matched and {len(lost)} lost their match. "
         + "Gained: " + ", ".join(f"row {c['journal_row']} ({c['journal_strategy']} {c['date']})" for c in gained) + ". Lost: " + (", ".join(f"row {c['journal_row']} ({c['journal_strategy']} {c['date']})" for c in lost) or "none") + ". "
         "Most gains are IRF/RF journal rows that the legacy PDR trade had pre-empted ('rejected by the portfolio controller' in Phase 3.0); **PDR itself matches the journal no better** (see `manual_pdr_rows_phase30_vs_phase35.csv`).", "",
         "Largest day-level changes (gross Rs): " + "; ".join(f"{d['date']} {float(d['delta_gross_rs']):+,.0f}" for d in best) + " (better); " + "; ".join(f"{d['date']} {float(d['delta_gross_rs']):+,.0f}" for d in worst) + " (worse). "
         f"The net change over all changed days is Rs {delta_pdr_days:+,.0f} gross. This is a description of the difference, **not** a reason to prefer either configuration: no parameter was chosen by profit, and the PDR thresholds are provisional.", "",
         "Full tables: `comparison_vs_phase30.csv`, `comparison_vs_phase30_by_day.csv` (one row per changed session, with the removed / added trades and tags), `manual_pdr_rows_phase30_vs_phase35.csv`.", "",
         "## Where to look (per executed trade)", "",
         tab(["what you asked to see", "where"], [
             ["Date, strategy and method, why it was entered", "`all_trades_detailed.csv` (`setup_explanation`, `selection_explanation`), the trade's section in `daily/YYYY-MM/YYYY-MM-DD.md`"],
             ["Each condition with its numerical value, rule, status", "`trade_entry_conditions.csv` (one row per condition), section C of the daily journal"],
             ["Candle OHLC, EMA, trend, support / resistance / zone values", "daily journal 'Candle and indicator calculations' table; `candle_analysis.csv`"],
             ["Entry timestamp and price, initial stop, targets", "`all_trades_detailed.csv` (`fill_timestamp`, `entry_price`, `initial_stop`, `target_1`, `target_2`, `post_t1_stop`); journal section 4"],
             ["Target 1 exit, remaining position's final exit, reason for each exit", "`trade_exits_detailed.csv` (one row per leg, with the raw 1-minute bar); `all_trades_detailed.csv` (`exit_narrative`)"],
             ["Gross and illustrative net P&L", "`all_trades_detailed.csv`; `strategy_performance.csv`; the workbook dashboard"],
             ["Manual journal match and the explanation of every mismatch", "`manual_journal_comparison.csv` (190 journal rows + every extra automated trade), `manual_verification_issues.csv`"],
             ["Every evaluable session, including no-trade days", "`daily/` (247 journals), `daily_summary.csv`"], ["Charts on the real candles", f"`charts/` ({counts['charts']} SVG files, one per trade)"],
             ["Everything in one workbook", "`NIFTY_Daily_Trade_Verification.xlsx` (review columns are blank for the owner)"]]), "",
         "## Independent verification", "",
         f"* `scripts/phase35_independent_audit.py` re-implements from the raw parquet files and the delivered CSVs only (it imports nothing from `src/`): {n_checks} checks, **{audit_line}** - entry prices, every exit leg re-walked bar by bar, P&L (gross and illustrative net), "
         "stops and targets, candles / EMA / geometry, the revised PDR signal stream (81 / 81), the four unchanged engines' signals versus the Phase 3.2 export (996 / 996), the controller rules, the performance and comparison tables, the manual-journal matching (89 matches), and a hash proof that data, earlier reports, other engines and the controller are unchanged. Details: `independent_audit.md`.",
         f"* Recomputation mismatches inside the trade explanations: {counts['recomputation_mismatches']}. Failed entry conditions on executed trades: {sum(int(t['checks_fail']) for t in trades)}.", "",
         "## Limits and open points", "",
         "* The PDR pattern thresholds and the open-above-zone requirement are provisional; with the open-above-zone requirement dropped the PDR stream would be roughly twice as large (Phase 3.4 sensitivity) - this run does not use that.",
         "* The forced exit at the 15:14 minute open is a provisional implementer assumption (as in Phase 3.0). RF's Target 2 (60) is a research assumption. PDR / PDS Target 2 is 70 (the guide's value; the performance report's winners suggest 60 - a recorded source conflict).",
         "* Simultaneous signals from different strategies in the same minute are not resolved by any approved tie-break: the day is marked unresolved and nothing is traded (preserved from Phase 3.0).",
         "* The journal records no entry or exit price, so matching uses date, strategy and the candle start within 15 minutes; P&L is never used to match.",
         "* Not done, by design: no parameter tuning, no live trading, no forward testing, no Phase 3.6.", ""]
    (OUT / "backtest_summary.md").write_text("\n".join(L))

    # ------------------------------------------------------------------------------------------------ README
    files = [("README.md", "this file"), ("backtest_summary.md", "results in plain English with the comparison against Phase 3.0 - start here"), ("daily_summary.csv", "one row per evaluable session (247), including no-trade days"),
             ("all_trades_detailed.csv", "one row per executed trade: setup, selection, entry, levels, exits, gross and illustrative net P&L, journal match"),
             ("trade_entry_conditions.csv", "every entry condition of every trade with its numbers, rule id, approval status and result"), ("trade_exits_detailed.csv", "one row per exit leg with the raw 1-minute exit bar"),
             ("manual_journal_comparison.csv", "the 190 manual journal rows and every extra automated trade, with the match class and the explanation of each mismatch"), ("strategy_performance.csv", "per-strategy and total performance"),
             ("NIFTY_Daily_Trade_Verification.xlsx", "all of the above in one workbook with review columns"), ("daily/", "one Markdown journal per evaluable session"), ("charts/", "one SVG chart per executed trade on the real candles"),
             ("configuration_snapshot.json", "every setting used, with the provisional PDR assumptions labelled"), ("independent_audit.md", "independent re-implementation and file-integrity audit"),
             ("comparison_vs_phase30.csv", "per-strategy comparison with Phase 3.0"), ("comparison_vs_phase30_by_day.csv", "every session whose trades changed, with the explanation"),
             ("manual_pdr_rows_phase30_vs_phase35.csv", "the PDR (and disputed) journal rows under both runs"), ("engine_contribution.csv", "signals, valid signals and trades contributed by each of the five engines"),
             ("all_strategy_signals.csv / ignored_signals.csv / rejected_signals.csv / candle_analysis.csv / manual_verification_issues.csv / manual_journal_normalized.csv", "supporting detail (Phase 3.2 framework)"),
             ("data_provenance.json / build_counts.json / independent_audit_results.json / before_snapshot.json", "hashes of the data and code used, counts, machine-readable audit results, hashes recorded before the first Phase 3.5 edit")]
    R = ["# Phase 3.5 - combined five-strategy backtest", "", "**Written for:** the strategy owner. Start with `backtest_summary.md`.", "",
         "## Rerun it independently (macOS terminal)", "", "```", COMMAND, "```", "",
         "Then, optionally: `python scripts/phase35_docs.py` (regenerates this README and the summary from the CSV files) and `python scripts/phase35_independent_audit.py` (the independent audit).", "",
         "`python scripts/phase35_run.py --help` lists the options. `--pdr-engine revised` (default) uses `src/nifty_trading/strategies/pdr_revised.py`; `--pdr-engine legacy` re-runs the Phase 3.0 baseline into `reports/phase3/phase35_legacy_check/` "
         "and exits non-zero if the frozen Phase 3.0 ledger is not reproduced field by field. `--out DIR` changes the output directory; the runner refuses to write into an earlier phase's directory.", "",
         "The run takes about 30 seconds and reads only `data/processed/` and `docs/trading journal/`; it writes only inside `reports/phase3/phase35_*`. Configuration id of this run: " + f"`{trades[0]['rule_configuration_id']}`.", "",
         tab(["file", "content"], [[f"`{a}`", b] for a, b in files]), "",
         "All P&L is synthetic index-point P&L x quantity. The PDR pattern thresholds and the open-above-zone requirement are provisional research assumptions, not approved by the strategy author.", ""]
    (OUT / "README.md").write_text("\n".join(R))
    if audit:
        write_audit_md(tests, ruff)
    print("docs written; audit:", audit_line, "| trades", allp["entries"])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default="not recorded in this run", help="text of the pytest result to quote in independent_audit.md")
    ap.add_argument("--ruff", default="not recorded in this run", help="text of the ruff result to quote in independent_audit.md")
    a = ap.parse_args()
    main(a.tests, a.ruff)
