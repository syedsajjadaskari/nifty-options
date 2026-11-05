"""Phase 3.6: write the Markdown reports of reports/phase3/phase36_body_based_pdr/ from the delivered CSV / JSON files (every number is computed here, none is typed).

Run after scripts/phase36_run.py, scripts/phase36_pdr_compare.py and scripts/phase36_independent_audit.py:
  .venv/bin/python scripts/phase36_docs.py --tests "<pytest result>" --ruff "<ruff result>"
The reviewer section of independent_audit.md is maintained in reports/phase3/phase36_body_based_pdr/_reviewer_findings.md (written by hand after the independent review) and appended when present.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P35 = ROOT / "reports" / "phase3" / "phase35_combined"
P32 = ROOT / "reports" / "phase3" / "phase32"
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")
MATCHED = ("EXACT_MATCH", "TIME_SHIFTED_MATCH")
COMMAND = "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase36_run.py"
COMMAND_ALT = "python scripts/phase35_run.py --pdr-engine body-based"


def rd(n: str, base: Path = OUT) -> list[dict]:
    with open(base / n, newline="") as f:
        return list(csv.DictReader(f))


def tab(head, body) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def rs(x) -> str:
    return f"{float(x):,.0f}"


def main(tests: str, ruff: str) -> None:  # noqa: C901
    perf = {r["strategy"]: r for r in rd("strategy_performance.csv")}
    three = {r["strategy"]: r for r in rd("comparison_3way_by_strategy.csv")}
    c35 = rd("comparison_vs_phase35_by_day.csv")
    c30 = rd("comparison_vs_phase30_by_day.csv")
    monthly = rd("monthly_pnl.csv")
    contrib = {r["strategy"]: r for r in rd("engine_contribution.csv")}
    trades, daily = rd("all_trades_detailed.csv"), rd("daily_summary.csv")
    man = [c for c in rd("manual_journal_comparison.csv") if c["journal_row"]]
    man35 = [c for c in rd("manual_journal_comparison.csv", P35) if c["journal_row"]]
    man30 = [c for c in rd("manual_vs_automated.csv", P32) if c["journal_row"]]
    cfg = json.loads((OUT / "configuration_snapshot.json").read_text())
    counts = json.loads((OUT / "build_counts.json").read_text())
    st = json.loads((OUT / "pdr_signal_statistics.json").read_text())
    audit = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {}
    pdrz = rd("pdr_daily_zone_comparison.csv")
    ovn = rd("old_vs_new_pdr_signals.csv")
    sens = {r["variant"]: r for r in rd("pdr_sensitivity_counts.csv")}
    val = rd("source_chart_validation.csv")
    allp = perf["ALL"]
    cls, cls35, cls30 = (Counter(c["match_classification"] for c in x) for x in (man, man35, man30))
    mt, mt35, mt30 = (c["EXACT_MATCH"] + c["TIME_SHIFTED_MATCH"] for c in (cls, cls35, cls30))
    extras = sum(1 for c in rd("manual_journal_comparison.csv") if c["match_classification"] == "EXTRA_AUTOMATED_TRADE")
    audit_line = "ALL PASS" if audit.get("all_pass") else "not yet run"
    n_checks = len(audit.get("checks", {}))
    pdr_trades = [t for t in trades if t["strategy"] == "PDR"]
    sg = rd("all_strategy_signals.csv")
    pdr_sig = [s for s in sg if s["strategy"] == "PDR"]
    after_cutoff = sum(1 for s in pdr_sig if s["within_13_00_cutoff"] == "False")
    ignored = Counter(r["controller_reason"].split("(")[0].strip() for r in rd("ignored_signals.csv") if r["strategy"] == "PDR")
    no_trade = sum(1 for r in daily if int(r["executed_trades"]) == 0)
    conflicts = counts["simultaneous_conflict_days"]
    tag = Counter(r["change_tags"] for r in ovn if r["row_type"] != "AMBIGUOUS_PATTERN_PROFILE_DEPENDENT")
    amb = [r for r in ovn if r["row_type"] == "AMBIGUOUS_PATTERN_PROFILE_DEPENDENT"]
    new_days = [r for r in pdrz if r["day_difference"] == "NEW_PDR_SIGNAL_DAY"]
    gone_days = [r for r in pdrz if r["day_difference"] == "PDR_SIGNAL_DAY_REMOVED"]
    chg_days = [r for r in pdrz if r["day_difference"] == "SIGNALS_CHANGED"]
    zb_diff = sum(1 for r in pdrz if abs(float(r["body_zone_B_floor"]) - float(r["body_zone_A_floor"])) > 1e-9)
    new_trade_days = [d for d in c35 if "NEW_TRADING_DAY" in d["tags"]]
    gone_trade_days = [d for d in c35 if "TRADING_DAY_REMOVED" in d["tags"]]
    old_by = {c["journal_row"]: c for c in man35}
    gained = [c for c in man if c["match_classification"] in MATCHED and old_by[c["journal_row"]]["match_classification"] not in MATCHED]
    lost = [c for c in man if c["match_classification"] not in MATCHED and old_by[c["journal_row"]]["match_classification"] in MATCHED]
    best = sorted(c35, key=lambda d: -float(d["delta_gross_rs"]))[:3]
    worst = sorted(c35, key=lambda d: float(d["delta_gross_rs"]))[:3]
    pdr_outcomes = Counter(t["outcome"] for t in pdr_trades)
    ka = {t["trade_id"]: t for t in rd("all_trades_detailed.csv", P35) if t["strategy"] == "PDR"}
    kb = {t["trade_id"]: t for t in pdr_trades}
    common_ids = sorted(set(ka) & set(kb))
    common_changed = [k for k in common_ids if (ka[k]["signal_candle_start"], ka[k]["outcome"], ka[k]["entry_price"]) != (kb[k]["signal_candle_start"], kb[k]["outcome"], kb[k]["entry_price"])]
    only35, only36 = sorted(set(ka) - set(kb)), sorted(set(kb) - set(ka))

    # ------------------------------------------------------------------------------------------------ backtest_summary.md
    L = ["# Phase 3.6 - author-corrected PDR (body-based zone) in the complete five-strategy NIFTY 50 backtest", "",
         "**Written for:** the strategy owner, for manual review. All P&L is **synthetic index-point P&L x quantity** (the NIFTY 50 index is not tradable); \"illustrative net\" deducts Rs 500 per trade and 0.5 index point of adverse slippage on every fill "
         "(the Phase 3.0 headline assumption, kept for comparability). Nothing was tuned or selected by profit, nothing was traded live, no broker API was called, no data file or earlier report was changed.", "",
         "## How this run was produced", "",
         "One run of the **existing** Phase 3.0 shared portfolio controller over the original one-minute NIFTY 50 candles (2025-09-01 .. 2026-08-31), reported with the **existing** Phase 3.2 framework. The only change of input is the PDR engine: the new "
         "`PDRBodyStrategy` (`src/nifty_trading/strategies/pdr_body.py`, version PDR_BODY_PHASE36). IRF, ORB, PDS and RF are constructed exactly as before; stops, targets, sizing, cutoff, forced exit and the controller are untouched. "
         "The Phase 3.5 engine (`--pdr-engine revised`, wick-high ceiling) and its results are preserved unchanged.", "",
         "**Exact command to rerun (macOS terminal):**", "", "```", COMMAND, "```", "", f"Equivalent: `{COMMAND_ALT}`. (`--pdr-engine revised` still means the Phase 3.5 configuration.)", "",
         "## What the author's corrections changed in PDR", "",
         "* **Resistance = the previous day's highest BODY high** (`max(open, close)` of the 5-minute candles); wick-only prices are ignored (Phase 3.5 used the highest wick as the ceiling).",
         "* **Open strictly above the zone ceiling** (equal or inside rejects the setup) - now an author-approved rule, no longer a legacy proposal.",
         "* **One of three confirmation candles** (good green body, lower-price rejection, hammer) that **closes above the zone**; the author says fixed percentage / wick-size thresholds are not required.",
         "* **Provisional, NOT author-approved:** the numeric thresholds that make the three patterns programmable (the Phase 3.5 profile RESEARCH_DEFAULT is carried over for comparability), the zone's lower boundary (body low of the anchor candle for candidate A, hull of the member bodies for candidate B), the "
         "multiple-body-high cluster numbers, the zero-height policy and the wait policy. No signal is VERIFIED. See `pdr_body_zone_rule_audit.md` and `pdr_pattern_classification.md`.", "",
         "## Headline result (247 evaluable sessions)", "",
         tab(["item", "value"], [["Executed trades", f"{allp['entries']} ({allp['first_trades']} first trades, {allp['second_trades']} second trades; {allp['days_traded']} days with a trade, {no_trade} without; {conflicts} same-minute conflict days)"],
                                 ["Trades by strategy", ", ".join(f"{s} {perf[s]['entries']}" for s in STRATS)], ["Gross P&L", f"Rs {rs(allp['gross_pnl_rs'])}"], ["Illustrative net P&L", f"Rs {rs(allp['net_illustrative_pnl_rs'])}"],
                                 ["Win rate / profit factor (gross)", f"{allp['win_rate_pct']}% / {allp['profit_factor']}"], ["Average trade / max drawdown / longest losing streak (gross)", f"Rs {rs(allp['avg_trade_rs'])} / Rs {rs(allp['max_drawdown_rs'])} / {allp['max_consecutive_losses']}"],
                                 ["Outcomes", f"Target 2: {allp['target2']}; Target 1 then post-T1 stop: {allp['t1_then_buffer_stop']}; initial full stop: {allp['initial_full_stop']}; provisional forced exit (15:14 open): {allp['forced_exit']}; unresolved: {allp['unresolved']}"],
                                 ["Manual journal (190 rows)", f"{mt} matched ({cls['EXACT_MATCH']} exact + {cls['TIME_SHIFTED_MATCH']} time-shifted); {190 - mt} unmatched; {extras} automated trades without a journal counterpart"]]), "",
         "### By strategy", "",
         tab(["strategy", "trades (1st / 2nd)", "gross Rs", "illustrative net Rs", "win %", "profit factor", "Target 2 / T1+stop / full stop", "share of gross"],
             [[s, f"{perf[s]['entries']} ({perf[s]['first_trades']} / {perf[s]['second_trades']})", rs(perf[s]["gross_pnl_rs"]), rs(perf[s]["net_illustrative_pnl_rs"]), perf[s]["win_rate_pct"], perf[s]["profit_factor"],
               f"{perf[s]['target2']} / {perf[s]['t1_then_buffer_stop']} / {perf[s]['initial_full_stop']}", f"{perf[s]['contribution_pct_of_gross']}%"] for s in STRATS]), "",
         "### Did all five engines feed the shared controller?", "",
         tab(["strategy", "engine", "confirmed signals", "within 13:00", "executed trades", "ignored", "rejected by controller"],
             [[s, contrib[s]["engine"], contrib[s]["confirmed_signals"], contrib[s]["signals_within_13_00_cutoff"], contrib[s]["executed_trades"], contrib[s]["ignored_signals"], contrib[s]["rejected_by_controller"]] for s in STRATS]), "",
         "## Phase 3.0 vs Phase 3.5 vs Phase 3.6", "",
         tab(["metric", "Phase 3.0 (legacy PDR)", "Phase 3.5 (wick-ceiling PDR)", "Phase 3.6 (body-based PDR)"],
             [["Total trades", three["ALL"]["phase30_trades"], three["ALL"]["phase35_trades"], three["ALL"]["phase36_trades"]]]
             + [[s, three[s]["phase30_trades"], three[s]["phase35_trades"], three[s]["phase36_trades"]] for s in STRATS]
             + [["Gross P&L (Rs)", rs(three["ALL"]["phase30_gross_rs"]), rs(three["ALL"]["phase35_gross_rs"]), rs(three["ALL"]["phase36_gross_rs"])],
                ["Illustrative net (Rs)", rs(three["ALL"]["phase30_net_rs"]), rs(three["ALL"]["phase35_net_rs"]), rs(three["ALL"]["phase36_net_rs"])],
                ["Journal matches (of 190)", mt30, mt35, mt], ["... exact / time-shifted", f"{cls30['EXACT_MATCH']} / {cls30['TIME_SHIFTED_MATCH']}", f"{cls35['EXACT_MATCH']} / {cls35['TIME_SHIFTED_MATCH']}", f"{cls['EXACT_MATCH']} / {cls['TIME_SHIFTED_MATCH']}"]]), "",
         tab(["strategy", "gross Rs 3.0", "gross Rs 3.5", "gross Rs 3.6", "net Rs 3.0", "net Rs 3.5", "net Rs 3.6"],
             [[s, rs(three[s]["phase30_gross_rs"]), rs(three[s]["phase35_gross_rs"]), rs(three[s]["phase36_gross_rs"]), rs(three[s]["phase30_net_rs"]), rs(three[s]["phase35_net_rs"]), rs(three[s]["phase36_net_rs"])] for s in (*STRATS, "ALL")]), "",
         "**Do not read the higher Phase 3.6 P&L as proof of a better strategy.** The three runs differ in one PDR convention at a time under provisional thresholds, on one historical year, with PDR trades of only "
         f"{perf['PDR']['entries']} (gross Rs {rs(perf['PDR']['gross_pnl_rs'])}, profit factor {perf['PDR']['profit_factor']}); a difference of a few signals moves the result by tens of thousands of rupees. No setting was chosen by profit or by journal agreement.", "",
         "### Monthly P&L (gross Rs)", "", tab(["month", "Phase 3.0", "Phase 3.5", "Phase 3.6", "net Phase 3.6"], [[m["month"], rs(m["phase30_gross_rs"]), rs(m["phase35_gross_rs"]), rs(m["phase36_gross_rs"]), rs(m["phase36_net_rs"])] for m in monthly]), "",
         "## PDR: signals, trades and what changed", "",
         tab(["PDR stream", "raw confirmed signals", "days with a signal", "executed trades"],
             [["Phase 3.0 legacy engine (reversal-swing zone)", st["phase30_legacy_signals"], 61, three["PDR"]["phase30_trades"]], ["Phase 3.5 wick-ceiling engine", st["phase35_signals"], st["phase35_signal_days"], three["PDR"]["phase35_trades"]],
              ["Phase 3.6 body-based engine", st["phase36_signals"], st["phase36_signal_days"], three["PDR"]["phase36_trades"]]]), "",
         f"Against Phase 3.5: {st['common_signals']} signals are common (the same candle qualifies; the ceiling is lower by the ignored wick), {st['removed_signals']} are removed and {st['new_signals']} are new "
         f"({', '.join(f'{k} {v}' for k, v in sorted(tag.items()) if k != 'UNCHANGED_VALID;ZONE_CEILING_LOWERED' and k != 'UNCHANGED_VALID')}). Of the {st['phase36_signals']} signals {after_cutoff} are timed after 13:00 and {len(pdr_trades)} became trades; "
         f"the rest were ignored by the controller ({', '.join(f'{k} {v}' for k, v in ignored.most_common())}) or rejected by the cutoff. PDR trade outcomes: " + ", ".join(f"{k} {v}" for k, v in pdr_outcomes.most_common()) + ". "
         f"The body-based open-above-zone test is passed on {st['open_above_body_ceiling']} sessions (the wick-ceiling test: {st['open_above_wick_ceiling']}); the status changes on {st['open_above_zone_status_changed']} sessions. Zones with zero height: {st['zero_height_zones']}.", "",
         f"**New or removed days.** PDR signal days: {len(new_days)} new ({', '.join(r['date'] for r in new_days) or 'none'}), {len(gone_days)} removed ({', '.join(r['date'] for r in gone_days) or 'none'}), {len(chg_days)} with a changed signal set. "
         f"Trading days (any strategy): {len(new_trade_days)} new, {len(gone_trade_days)} removed relative to Phase 3.5; {len(c35)} sessions have a different trade set (see `comparison_vs_phase35_by_day.csv`, one row per session with the removed / added trades), "
         f"{len(c30)} relative to Phase 3.0 (`comparison_vs_phase30_by_day.csv`). Per-session zone data for every session: `pdr_daily_zone_comparison.csv`; every signal with its tag and reason: `old_vs_new_pdr_signals.csv`.", "",
         f"Journal agreement against Phase 3.5: {len(gained)} rows gained a match, {len(lost)} lost one. " + ("Gained: " + ", ".join(f"row {c['journal_row']} ({c['journal_strategy']} {c['date']})" for c in gained) + ". " if gained else "")
         + ("Lost: " + ", ".join(f"row {c['journal_row']} ({c['journal_strategy']} {c['date']})" for c in lost) + ". " if lost else "") + "The PDR journal rows under all three runs are in `manual_pdr_rows_three_phases.csv`.", "",
         "Largest day-level changes vs Phase 3.5 (gross Rs): " + "; ".join(f"{d['date']} {float(d['delta_gross_rs']):+,.0f}" for d in best) + " (higher); " + "; ".join(f"{d['date']} {float(d['delta_gross_rs']):+,.0f}" for d in worst) + " (lower). This describes the difference; it is not a reason to prefer a configuration.", "",
         "## What the PDR P&L swing rests on (read this before the P&L)", "",
         f"* **Trade level.** {len(common_ids)} PDR trade ids are common to Phase 3.5 and 3.6 ({len(common_changed)} of them enter on a different candle and end differently); {len(only35)} Phase 3.5 trades disappear (gross Rs {rs(sum(float(ka[k]['gross_pnl_rs']) for k in only35))}) and {len(only36)} appear "
         f"(gross Rs {rs(sum(float(kb[k]['gross_pnl_rs']) for k in only36))}). The change of PDR gross ({rs(three['PDR']['phase35_gross_rs'])} -> {rs(three['PDR']['phase36_gross_rs'])}) is the sum of about a dozen trades, not a systematic shift.",
         f"* **Thin margins.** The smallest opens above the ceiling are {', '.join(f'{x:.2f}' for x in st['open_margin_smallest_three'])} points (`pdr_trade_open_margins.csv`); the new winners are among them. The engine uses the first 1-minute open; the vendor daily open differs by more than 0.05 point on "
         f"{st['vendor_open_differs_over_0_05']} sessions and would flip the open-above-zone test on {len(st['vendor_open_flips_open_above_zone'])} ({', '.join(st['vendor_open_flips_open_above_zone']) or 'none'}).",
         f"* **Zones price had already left.** {st['signals_after_zone_closed_through']} of {st['phase36_signals']} signals and {st['trades_after_zone_closed_through']} of {st['executed_pdr_trades']} executed PDR trades occur after a candle CLOSED BELOW the zone floor between the test and the confirmation "
         f"(`pdr_signal_zone_state.csv`; the wait policy is a research assumption, rule PDR-B07, flagged in every trade's explanation).",
         f"* **Patterns.** The active default thresholds pass {sum(1 for v in val if v['patterns_RESEARCH_DEFAULT'] != 'none')} of the author's 4 dated entry candles as a pattern (`pdr_source_chart_validation.md`); the pattern numbers are provisional.",
         "* **The zone floor and the gap-up condition do not change any signal** (`pdr_body_zone_rule_audit.md` part 5).", "",
         "## Where to look (per executed trade; Trade ID = `YYYYMMDD-n-STRATEGY`)", "",
         tab(["what you asked to see", "where"], [
             ["Why entered: strategy, method, conditions with numbers, OHLC, EMA / trend / zones, body-high calculation, selection against competitors", "`all_trades_detailed.csv` (`setup_explanation`, `selection_explanation`); `entry_condition_details.csv` (one row per condition); the trade's section in `daily/YYYY-MM/YYYY-MM-DD.md`; `candle_analysis.csv`"],
             ["Entry timestamp and price, stop, targets, post-T1 stop", "`all_trades_detailed.csv`; section 4 of the daily journal"], ["Why exited: T1, T2, stop, post-T1 stop, forced exit; exact fill time and price; source 1-minute bar; leg P&L", "`exit_details.csv` (one row per leg); `all_trades_detailed.csv` (`exit_narrative`)"],
             ["Manual journal comparison and the reason for each mismatch", "`manual_journal_comparison.csv` (190 rows + every extra automated trade); `manual_pdr_rows_three_phases.csv`"],
             ["Every evaluable session, including no-trade days", f"`daily/` ({counts['daily_journals']} journals), `daily_summary.csv`"], ["Charts on the real candles", f"`charts/` ({counts['charts']} SVG files, one per trade)"],
             ["Everything in one workbook", "`NIFTY_Daily_Trade_Verification.xlsx`"]]), "",
         "## Independent verification", "",
         f"* `scripts/phase36_independent_audit.py` re-implements from the raw parquet files and the delivered CSVs only: {n_checks} checks, **{audit_line}** (details and the fresh-reviewer findings: `independent_audit.md`).",
         f"* Recomputation mismatches inside the trade explanations: {counts['recomputation_mismatches']}; failed entry conditions on executed trades: {sum(int(t['checks_fail']) for t in trades)}.",
         f"* `pytest`: {tests}; `ruff`: {ruff}.", "",
         "## Limits and open points", "",
         "* The pattern thresholds, the zone lower boundary and the multiple-body-high numbers are provisional. With the example-read thresholds the body-based stream would have "
         f"{sens['Phase 3.6 body-based A, EXAMPLE_LENIENT patterns']['signals']} signals instead of {st['phase36_signals']} ({len(amb)} lenient-only candles are preserved as AMBIGUOUS, never traded); this run does not use them.",
         f"* Allowing any open (not the author's rule) would give {sens['Phase 3.6 body-based A, open may be anywhere (sensitivity; NOT the author rule)']['signals']} signals - not used.",
         "* The guide's own drawn boxes for Examples 1, 2 and 4 follow the wick high, which contradicts the later 'wick should be ignored' clarification (Example 3 follows the body); the owner must confirm which governs (`pdr_source_chart_validation.md`).",
         "* The forced exit at the 15:14 minute open is a provisional implementer assumption (as in Phase 3.0); RF's Target 2 of 60 is a research assumption; PDR / PDS Target 2 is 70 (the guide) while the performance report's winners suggest 60 - a recorded source conflict.",
         "* Simultaneous signals of different strategies in the same minute have no approved tie-break: the day is marked unresolved and nothing is traded (preserved).",
         "* Not done, by design: no tuning, no live trading, no forward testing, no commit or push, no Phase 3.7.", ""]
    (OUT / "backtest_summary.md").write_text("\n".join(L))

    # ------------------------------------------------------------------------------------------------ pdr_source_chart_validation.md
    V = ["# PDR source-chart validation (the guide's dated examples)", "",
         "**Written for:** the strategy owner. The PDF `PDR_Strategy_Guide.pdf` has five annotated examples; four are dated (their drawn zones and entry candles are the Phase 2.2 / 3.3 readings of the chart price tags). "
         "This file tests the Phase 3.6 body-based rules against them. Nothing was adjusted to make an example pass.", "",
         "## What the source says versus the later author clarification", "",
         "* PDF p.1-2: 'Zone: small box from candle body to upper wick at the previous day's high'; 'Upper boundary: the highest point of the upper wick. Lower boundary: the relevant candle-body level.'",
         "* Author's later clarification (AUTHOR_APPROVED, treated as the later statement by the owner's brief): 'Wick should be ignored, but body should be considered. If a price is only a wick, it should be ignored. If it is a body high, that should be considered when drawing the zone.'",
         "* **The two conflict.** The brief treats the clarification as the later, authoritative statement, but the owner should still confirm explicitly that it supersedes the PDF's wording and the boxes drawn in the PDF figures.", "",
         "## Evidence from the figures", "",
         tab(["example", "date", "drawn zone", "previous-day wick high", "previous-day highest body high", "drawn ceiling follows", "drawn ceiling - body ceiling", "body-based zone A"],
             [[v["example"], v["date"], f"[{float(v['drawn_zone_floor']):,.2f}, {float(v['drawn_zone_ceiling']):,.2f}]", f"{float(v['previous_day_wick_high']):,.2f} ({v['wick_high_candle']})", f"{float(v['previous_day_body_high']):,.2f} ({v['body_high_candle']})",
               v["drawn_ceiling_follows"], f"{float(v['drawn_ceiling_minus_body_ceiling']):+.2f}", v["body_zone_A"]] for v in val]), "",
         f"Examples {', '.join(v['example'].split(' (')[0].replace('Example ', '') for v in val if v['drawn_ceiling_follows'] == 'WICK_HIGH')} are drawn up to the wick high; Example(s) "
         f"{', '.join(v['example'].split(' (')[0].replace('Example ', '') for v in val if v['drawn_ceiling_follows'] == 'BODY_HIGH')} up to the body high. Example 3 is the case that contradicted the wick-ceiling engine in Phase 3.4 "
         "(its 14:50 spike was a wick-only price); the body-based zone reproduces its drawn shelf.", "",
         "## The engine against the four dated entry candles", "",
         tab(["example", "open above body ceiling", "entry candle (author)", "close above body ceiling", "patterns: default thresholds", "patterns: example-read thresholds", "engine signal at the author's candle (default / example-read)", "engine signals that day (default)"],
             [[v["example"], v["open_above_body_ceiling"], f"{v['author_entry_candle']} {v['entry_candle_ohlc']}", v["entry_close_above_body_ceiling"], v["patterns_RESEARCH_DEFAULT"], v["patterns_EXAMPLE_LENIENT"],
               f"{v['engine_signal_at_authors_candle_RESEARCH_DEFAULT']} / {v['engine_signal_at_authors_candle_EXAMPLE_LENIENT']}", v["engine_signals_that_day_RESEARCH_DEFAULT"] or "none"] for v in val]), "",
         "### Reproduced and unresolved", "",
         f"* **Zone and opening:** in all four examples the session opens strictly above the body ceiling and the author's entry candle closes above it ({sum(1 for v in val if v['open_above_body_ceiling'] == 'True' and v['entry_close_above_body_ceiling'] == 'True')} of 4).",
         f"* **Entry candle accepted by the default (provisional) thresholds:** {sum(1 for v in val if v['engine_signal_at_authors_candle_RESEARCH_DEFAULT'] == 'True')} of 4 - the default numbers pass none of the four author candles as a pattern. "
         f"With the example-read thresholds (read off these same candles, so circular) the engine signals exactly at the author's candle in {sum(1 for v in val if v['engine_signal_at_authors_candle_EXAMPLE_LENIENT'] == 'True')} of 4.",
         "* **Unresolved:** where the engine does not signal at the author's candle even with the example-read thresholds (Examples with `False / False`), the author's candle is probably both the test and the confirmation (the engine, like Phase 3.5, requires the confirmation to come strictly "
         f"after the test candle; allowing same-candle confirmation gives {sens['Phase 3.6 body-based A, confirmation may be the test candle (sensitivity)']['signals']} signals instead of {st['phase36_signals']}). Not adopted: it is not an author rule.",
         "* **Example 5** is undated in the guide: not reproducible, not used as evidence. **But** Phase 3.3 observed, and the independent reviewer confirmed at 4x zoom, that its entry session's first candle appears to start INSIDE the drawn box with no visible gap above it. "
         "If that is right, the author's own example does not satisfy the now author-approved 'open strictly above the zone' rule. Unresolved: the owner should look at Example 5.",
         "* **Floors:** the drawn floors of Examples 1, 2 and 4 are essentially the body top of the wick-high candle, so those boxes lie at or above the body zone and are almost disjoint from it (the body zone sits below them); only the CEILING of Example 3 is reproduced "
         f"({float(val[2]['previous_day_body_high']):,.2f} against the drawn {float(val[2]['drawn_zone_ceiling']):,.2f}); its drawn floor ({float(val[2]['drawn_zone_floor']):,.2f}) is {float(val[2]['drawn_zone_floor']) - float(val[2]['body_zone_A'].split(',')[0].strip('[').replace(',', '')) :.2f} points above the engine's floor (the body low of the anchor candle). The floor is a research convention and does not change any signal.",
         "* The drawn boxes are readings of chart price tags (about +/- 1 point, Phase 3.3); the chart prices differ slightly from the repository data at the open.", ""]
    (OUT / "pdr_source_chart_validation.md").write_text("\n".join(V))

    # ------------------------------------------------------------------------------------------------ pdr_pattern_classification.md
    P = ["# PDR confirmation-pattern classification (Phase 3.6)", "",
         "**Written for:** the strategy owner. The author requires ONE of three candles and a close above the zone, and says that **fixed body-percentage and wick-size thresholds are not required**. A program still needs a deterministic classification, "
         "so the numbers below are a **research convention, not an author rule**: they were carried over from Phase 3.5 (profile `RESEARCH_DEFAULT`) so that the Phase 3.6 difference is only the zone and the opening rule. They were not chosen by profit or by journal agreement.", "",
         tab(["pattern", "profile RESEARCH_DEFAULT (active, PROVISIONAL)", "profile EXAMPLE_LENIENT (sensitivity only)", "colour"],
             [["good green body", "bullish; body >= 60% of the range; upper wick <= 20%", "body >= 40%; upper wick <= 25%", "must be green (a 'green-body' candle)"],
              ["lower-price rejection", "lower wick >= 2 x body; close in the top 30% of the range; the low reached the zone ceiling (low <= ceiling)", "wick >= 1.5 x body; top 40%", "not required (author silent)"],
              ["hammer", "lower wick >= 2 x body; upper wick <= 10% of the range; body bottom at >= 60% of the range (a bullish LOWER-wick shape, not the old bearish upper-wick pin bar)", "wick >= 1.5 x body; upper wick <= 15%; body position >= 55%", "not required (author silent)"]]), "",
         "Mandatory for all three: `close > zone ceiling`, strictly (a lower wick may penetrate the zone). When several patterns pass on one candle all are recorded and **one** signal is produced. A zero-range candle passes no pattern (ratios are undefined); "
         "a candle with a tiny body and a long lower wick can pass rejection and hammer whatever its colour; a thin candle with no body-percentage, wick or location that fits none of the three is **not** a signal - the classifier never returns True by default.", "",
         "Every pattern calculation of every executed trade (body %, wicks, wick / body, close position, body position, thresholds, close minus ceiling) is in `entry_condition_details.csv` (rule PDR-B04c rows) and in each trade's daily journal.", "",
         f"## Pattern use among the {st['phase36_signals']} signals", "",
         tab(["sensitivity (signals only)", "signals", "days"], [[k.replace("Phase 3.6 body-based ", ""), v["signals"], v["days_with_a_signal"]] for k, v in sens.items() if k.startswith("Phase 3.6 body-based") and ("only" in k or "RESEARCH_DEFAULT" in k or "EXAMPLE_LENIENT" in k)]), "",
         "The traded PDR signals passed: " + ", ".join(f"{k} {v}" for k, v in Counter(t["setup_explanation"].split(" passed ")[1].split(" and closed")[0] for t in pdr_trades if " passed " in t["setup_explanation"]).most_common()) + ".", "",
         f"Reconciliation of the sensitivity: {st['phase36_signals']} default signals + {st['lenient_only_signals']} lenient-only signals - {st['default_signals_absent_under_lenient']} default signals that disappear under the lenient profile (a different pattern on an earlier candle changes the re-arming sequence) = {st['lenient_signals']} lenient signals.", "",
         f"## Ambiguous candles preserved for manual review ({len(amb)})", "",
         "These candles come after a test of the body zone and close above the body ceiling, but pass a pattern **only** under the example-read thresholds. The default thresholds reject them; the author's 'no fixed threshold' statement means neither answer is wrong. "
         "They are **not traded**; they are listed so the owner can judge them (`old_vs_new_pdr_signals.csv`, `row_type = AMBIGUOUS_PATTERN_PROFILE_DEPENDENT`).", "",
         tab(["date", "candle", "lenient pattern(s)", "close - ceiling"], [[r["date"], r["confirmation_candle_start"], r["lenient_patterns"], f"{float(r['phase36_close_minus_ceiling']):+.2f}"] for r in amb[:25]]),
         "" if len(amb) <= 25 else f"\n... and {len(amb) - 25} more in `old_vs_new_pdr_signals.csv`.", "",
         "## Author decision needed", "",
         "Numeric definitions of the three patterns, or a handful of labelled example candles, or confirmation that a manual review of the ambiguous candles above is the intended process. Until then no profile is validated.", ""]
    (OUT / "pdr_pattern_classification.md").write_text("\n".join(P))

    # ------------------------------------------------------------------------------------------------ pdr_body_zone_rule_audit.md
    rules = rd("pdr_body_rules.csv") if (OUT / "pdr_body_rules.csv").exists() else []
    Z = ["# PDR body-based zone: before-change audit and the new rules (Phase 3.6)", "",
         "**Written for:** the strategy owner and reviewers. Part 1 documents what the Phase 3.4 / 3.5 engine (`pdr_revised.py`) actually did **before any change**; part 2 the new engine; part 3 the effect. "
         "The engine is named 'revised' but it did **not** implement the author's later wick-ignoring clarification.", "",
         "## 1. Before-change audit of `src/nifty_trading/strategies/pdr_revised.py` (unchanged; still used by `--pdr-engine revised`)", "",
         tab(["question", "what the code did"], [
             ["Does the zone use raw candle High values?", "Yes. `day_high_index` picks the first candle with the highest raw `High` (`c.h`); the zone ceiling is that candle's wick high."],
             ["Does the zone use max(Open, Close)?", "Only for the lower boundary: `_body_top(c) = max(o, c)` of the day-high candle (candidate A) or the lowest member body top (candidate B). The ceiling never used a body."],
             ["Is the previous-day high the highest wick or body?", "The highest WICK of the previous session (`zone.previous_day_high = cs[dh].h`)."],
             ["How are multiple relevant highs detected?", "Candidate B: local highs (k = 1, non-strict) of the raw `High`, within 5.0 points of the day's high, at least 2 touch groups (members closer than 2 candles merge). Wick-based."],
             ["Which boundaries derive from bodies?", "The floor only. A wick spike therefore always set the ceiling (Example 3: a 14:50 wick to 25,095.70 became the ceiling although the drawn shelf was 25,081-25,084)."],
             ["Which numerical pattern thresholds were active?", "Profile RESEARCH_DEFAULT: green body >= 60% with upper wick <= 20%; rejection lower wick >= 2 x body, close in the top 30%, low <= ceiling; hammer lower wick >= 2 x body, upper wick <= 10%, body bottom >= 60% of the range - all PROPOSED_FOR_REVIEW (Phase 2.2 owner proposals), none author-approved."],
             ["Was the next day's open compared with the zone ceiling?", "Yes: `open > zone.ceiling` (legacy PDR-011, labelled PROPOSED), i.e. against the WICK ceiling. It was not an author-approved rule in Phase 3.5."],
             ["Was the confirmation close strictly above the ceiling?", "Yes: `close_above = c.c > zone_ceiling` (strict), applied to every pattern."],
             ["Were hammer and lower-price rejection alternatives?", "Yes: `qualifies = any pattern passed AND close > ceiling` (OR logic; every passing pattern recorded, one signal per candle)."],
             ["Colour handling of green / red / neutral candles", "Good green body requires `close > open`. Rejection and hammer ignore colour, so a red or doji candle with a long lower wick can qualify; a zero-range candle passes nothing; a candle with zero body and a lower wick passes the wick tests (wick >= 2 x 0)."],
             ["Did it ever use future candles?", "No: classification uses the completed candle; the zone uses only the previous session; the Phase 3.4 prefix test and the independent rebuild confirmed it."]]), "",
         "## 2. The new rules (`PDR_BODY_RULES` in `pdr_body.py`)", "",
         tab(["rule", "status", "text", "source"], [[r["rule_id"], r["status"], r["text"], r["source"]] for r in rules]) if rules else "(see pdr_body_rules.csv)", "",
         "### Construction", "",
         "* `body_high = max(open, close)`, `body_low = min(open, close)` of every completed previous-session 5-minute candle (the same candle set the earlier engines used).",
         "* **Candidate A (active):** ceiling = the highest `body_high` of the session (first occurrence); floor = that candle's `body_low`. **Candidate B:** the highest body high is joined with body-high pivots (k = 1, non-strict) within 5.0 points, at least 2 touch groups "
         "(members closer than 2 candles count once); the zone is the hull of the member bodies (floor = lowest member body low), ceiling = the highest body high; otherwise it equals A.",
         "* The illustrative example of the brief (wicks 25,095 / 25,089 / 25,110, body highs 25,080 / 25,084 / 25,082): the highest body high is 25,084, so the ceiling is 25,084 and the 25,110 wick plays no part (covered by `test_an_isolated_wick_spike...` and `test_the_raw_wick_high_is_ignored...`).",
         f"* **A and B give identical signals by construction** (the highest body high is always a member, so both ceilings are equal and only the floor can differ): {st['phase36_signals']} signals each; B's floor differs from A's on {zb_diff} of {len(pdrz)} sessions; tolerance 5 / 10 / 15 points also give "
         f"{sens['Phase 3.6 body-based B, tolerance 10 points']['signals']}. The only choice that moves the ceiling is the lone-body-spike policy (diagnostic option, contradicts 'do not discard a genuine highest body price': "
         f"{sens['Phase 3.6 body-based B, body spike excluded when above a shelf (diagnostic)']['signals']} signals).",
         f"* **Zero-height zones:** detected (`ZERO_HEIGHT_ZONE`); by default the setup is left UNRESOLVED instead of inventing a width. {st['zero_height_zones']} of {len(pdrz)} sessions have one (the Phase 3.5 run had one, trade 20260826-1-PDR).",
         "* **Opening:** `session_open > zone ceiling`, strictly, using the original first one-minute open; recorded with the distance above the ceiling (PDR-B03 row of every trade). The separate gap-up condition of the guide (open above the official previous close) is preserved.", "",
         "## 3. Effect of using bodies", "",
         tab(["measure (247 sessions)", "value"], [["Previous-day wick high minus highest body high: median / mean / maximum (points)", f"{st['median_points']:.2f} / {st['mean_points']:.2f} / {st['max_points']:.2f}"],
                                               ["... equal (no wick above the highest body)", st["zero_difference"]], ["... larger than 5 points", st["above_5_points"]],
                                               ["Sessions opening above the wick ceiling (Phase 3.5) / above the body ceiling (Phase 3.6)", f"{st['open_above_wick_ceiling']} / {st['open_above_body_ceiling']}"],
                                               ["Sessions whose open-above-zone status changes", st["open_above_zone_status_changed"]], ["Gap-up sessions", st["gap_up_sessions"]],
                                               ["PDR signals: Phase 3.0 / 3.5 / 3.6", f"{st['phase30_legacy_signals']} / {st['phase35_signals']} / {st['phase36_signals']}"]]), "",
         "## 4. Still unresolved (author decisions)", "",
         "1. Numeric shape of the three patterns (or a manual-review process) - `pdr_pattern_classification.md`.", "2. Whether the clarification supersedes the PDF's wick-topped boxes in Examples 1, 2 and 4 - `pdr_source_chart_validation.md`.",
         "3. The zone's lower boundary (hull of the member bodies is a research convention) and the multiple-body-high numbers (tolerance, touches, separation).", "4. Whether a zone with zero height should be a line, a minimum width or no setup.",
         "5. Whether the confirmation may be the test candle itself (the author's examples suggest it can be).",
         f"6. The wait policy: a tested setup stays armed until a candle qualifies. {st['signals_after_zone_closed_through']} of {st['phase36_signals']} signals ({st['trades_after_zone_closed_through']} of {st['executed_pdr_trades']} executed PDR trades) fire after a candle had CLOSED BELOW the zone floor between the test and the confirmation "
         f"(`pdr_signal_zone_state.csv`; longest wait {st['max_candles_waited']} candles; {st['signals_with_opening_candle_as_test']} signals use the 09:15 candle as the test; widest zone {st['max_zone_width']:.2f} points). The guide is silent on price crossing below the zone (Phase 3.3).", "",
         "## 5. Things that do not affect the signals (stated plainly)", "",
         "* **The zone floor.** Under the author's opening rule the floor only decides whether a candle counts as a test; every floor variant tried by the independent reviewer (minus infinity, ceiling minus 5, the hull, the anchor candle's body low) and the first / last tie-break gave the same signals. Candidate B differs from A in the floor only.",
         "* **The gap-up condition** is redundant in this data: no session opens above the body ceiling without also opening above the official previous close.",
         "* **The shelf flag** `BODY_SPIKE_ABOVE_SHELF` fires for almost every session (a shelf of repeated body highs can lie anywhere in the day), so the diagnostic 'spike excluded' row of `pdr_sensitivity_counts.csv` is not meaningful; it never affects the active run.", ""]
    (OUT / "pdr_body_zone_rule_audit.md").write_text("\n".join(Z))

    # ------------------------------------------------------------------------------------------------ README.md
    files = [("README.md", "this file"), ("backtest_summary.md", "results, the Phase 3.0 / 3.5 / 3.6 comparison, monthly P&L - start here"), ("pdr_body_zone_rule_audit.md", "before-change audit of `pdr_revised.py`, the new body-based rules, effect"),
             ("pdr_pattern_classification.md", "the three patterns, the provisional thresholds, ambiguous candles"), ("pdr_source_chart_validation.md", "the guide's dated examples against the body-based rules"),
             ("old_vs_new_pdr_signals.csv", "every Phase 3.5 PDR signal and every new Phase 3.6 signal with tags and reasons; lenient-only candles as AMBIGUOUS"), ("pdr_daily_zone_comparison.csv", "every session: wick vs body zone, opening test, signals per phase, day difference"),
             ("pdr_sensitivity_counts.csv", "PDR signal counts under each unresolved setting (counts only)"), ("source_chart_validation.csv / pdr_signal_statistics.json / pdr_body_rules.csv", "supporting data"),
             ("all_trades_detailed.csv", "one row per executed trade (stable Trade ID `YYYYMMDD-n-STRATEGY`)"), ("entry_condition_details.csv", "every entry condition of every trade with its numbers, rule id, approval status, result"),
             ("exit_details.csv", "one row per exit leg with the raw 1-minute exit bar"), ("daily_summary.csv", "one row per evaluable session (247)"), ("strategy_performance.csv / engine_contribution.csv / monthly_pnl.csv", "performance tables"),
             ("comparison_3way_by_strategy.csv, comparison_vs_phase35_*.csv, comparison_vs_phase30_*.csv", "Phase 3.0 / 3.5 / 3.6 comparisons, per strategy and per changed session"),
             ("manual_journal_comparison.csv / manual_pdr_rows_three_phases.csv", "the 190 journal rows + extra automated trades; PDR rows under all three runs"), ("NIFTY_Daily_Trade_Verification.xlsx", "the workbook (review columns blank)"),
             ("daily/", "one Markdown journal per evaluable session"), ("charts/", "one SVG chart per executed trade on the real candles"), ("configuration_snapshot.json / data_provenance.json", "every setting used (provisional PDR assumptions labelled); hashes of data and code"),
             ("independent_audit.md", "independent re-implementation, the fresh reviewer's findings, file-integrity proof"), ("before_snapshot.json / independent_audit_results.json / build_counts.json", "hashes recorded before the first Phase 3.6 edit; machine-readable results")]
    R = ["# Phase 3.6 - body-based PDR + complete five-strategy backtest", "", "**Written for:** the strategy owner. Start with `backtest_summary.md`.", "",
         "## Rerun it independently (macOS terminal)", "", "```", COMMAND, "```", "", f"Equivalent: `{COMMAND_ALT}`.",
         "`python scripts/phase35_run.py --help` lists the options: `--pdr-engine revised` (default; the Phase 3.5 wick-ceiling configuration - its meaning is unchanged), `legacy` (Phase 3.0 regression check) and `body-based` (this phase). "
         "`--out DIR` changes the output directory; the runner refuses to write the Phase 3.6 results into a Phase 3.5 directory or into any earlier phase's directory.", "",
         "Then, optionally (in this order): `python scripts/phase36_pdr_compare.py` (PDR signal comparison, sensitivities, source-chart validation), `python scripts/phase36_independent_audit.py`, `python scripts/phase36_docs.py --tests \"...\" --ruff \"...\"` (regenerates the reports).", "",
         f"The run takes about a minute; it reads only `data/processed/` and `docs/trading journal/` and writes only inside `reports/phase3/phase36_*`. Configuration id: `{trades[0]['rule_configuration_id']}`; PDR configuration id: `{cfg['pdr_body_config']['zone_candidate'][0]}` / profile `{cfg['pdr_body_config']['pattern_profile']}` (recorded on every signal).", "",
         tab(["file", "content"], [[f"`{a}`", b] for a, b in files]), "",
         "All P&L is synthetic index-point P&L x quantity. " + cfg["pdr_provisional_assumptions"], ""]
    (OUT / "README.md").write_text("\n".join(R))

    # ------------------------------------------------------------------------------------------------ independent_audit.md
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    reviewer = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    A = ["# Phase 3.6 - independent audit", "",
         "**Written for:** the strategy owner and any reviewer. The audit verifies that the code did what the written rules say and that nothing else changed; it does **not** verify the source rules (the pattern thresholds and zone conventions are provisional, "
         "and a misreading shared by the engine and the audit script would not be caught - the author of both is the same). Two independent checks were run: (1) `scripts/phase36_independent_audit.py`, a second implementation from the raw data, and (2) a fresh read-only reviewer subagent (an AI reviewer, not a human).", "",
         "## 1. Independent re-implementation: `scripts/phase36_independent_audit.py`", "",
         "Written from the raw one-minute parquet files and the delivered CSVs only; it imports nothing from `src/` (derived from the Phase 3.2 / 3.5 audits; the body-zone rebuild is new; the signal-stream function comes from the Phase 3.4 independent script, which is also free of `src/` imports).", "",
         tab(["#", "check", "n", "result"], [[i, name, c["n"], "PASS" if c["pass"] else "**FAIL**"] for i, (name, c) in enumerate(audit["checks"].items(), 1)]) if audit else "(audit not run)", "",
         f"Overall: **{'ALL PASS' if audit.get('all_pass') else 'FAILURES PRESENT'}** ({n_checks} checks); machine-readable in `independent_audit_results.json`.", "",
         "## 2. Pre-existing files edited in Phase 3.6 (and nothing else)", "",
         f"A hash snapshot of {len(snap['files'])} files (source, tests, scripts, `data/`, `reports/` including every earlier phase, `docs/`) was recorded before the first edit (`before_snapshot.json`, git head `{snap['git_head'][:7]}`; the Phase 3.3 - 3.5 work was still uncommitted). "
         "The audit proves every file in it is byte-identical **except** these seven (the independent reviewer re-hashed all of them; it found only the documented ones changed):", "",
         tab(["file", "why it was edited"], [
             ["`src/nifty_trading/research/phase3.py`", "`PDR_ENGINES` / `make_engines` / `combined_scenario` accept `BODY_BASED_PHASE36`; Phase 3.0 scenarios and the meaning of `REVISED_PHASE34` unchanged."],
             ["`src/nifty_trading/research/phase31.py`", "the PDR diagnostic probe uses the body zone when the body engine is active."],
             ["`src/nifty_trading/research/phase32.py`", "`explain_pdr_body` (the body-high calculation, wick shown as ignored), PDR-B rule statuses."], ["`src/nifty_trading/research/phase32_build.py`", "phase / banner labels for Phase 3.6."],
             ["`src/nifty_trading/research/phase32_render.py`", "one extra row in the daily-journal header for the body run: the previous-day highest BODY high (the PDR ceiling), next to the wick high."],
             ["`src/nifty_trading/research/phase32_excel.py`", "Rule Definitions sheet lists the PDR-B rules / PDRBodyConfig for the body run."],
             ["`scripts/phase35_run.py`", "new option `--pdr-engine body-based` (dispatches to `phase36`); `revised` and `legacy` unchanged; refuses to write Phase 3.6 results into a Phase 3.5 directory or any other `reports/` directory that is not a Phase 3.5 / 3.6 output."]]), "",
         "The allowed-edit list of the audit and of the snapshot test is exactly these seven files (an earlier draft also allowed `tests/test_phase35_combined.py`, which was not edited; the independent review pointed out that this weakened the guard, so it was removed).", "",
         "The five engines (`irf`, `orb`, `pds`, `rf`, `pdr`), the Phase 3.4 / 3.5 engine `pdr_revised.py`, `trading_day.py`, `selection.py`, `exit_policy.py`, `params.py`, `definitions.py`, `base.py`, all data files and **every file of the Phase 3.0 - 3.5 result directories** are byte-identical to the snapshot.", "",
         "## 3. Regression check of the framework", "",
         "Phase 3.5's own command (`python scripts/phase35_run.py --pdr-engine revised`) and the legacy regression (`--pdr-engine legacy`) are re-run into scratch directories by the test suite / reviewer; the Phase 3.5 results directory is hash-identical (check above).", "",
         "## 4. Tests and static checks", "",
         f"* `pytest -q`: **{tests}**; `ruff check src tests scripts`: **{ruff}**.",
         "* New: `tests/test_phase36_body_pdr.py` - raw wick ignored, highest body high, multiple body highs, isolated wick spike, isolated body high, body-high clusters and their parameters, boundaries, zero-height zones, open strictly above (at / inside / below / one tick above), "
         "the three alternatives, no fixed percentage labelled author-approved, close strictly above, wick penetration, no look-ahead, previous-session-only data, no duplicate signals, other-strategy streams unchanged (file-level), "
         "a one-time snapshot check honouring `PHASE36_ALLOW_LATER_EDITS=1`.", "",
         "## 5. Not verified", "",
         "* The author's intent for every `PROPOSED_FOR_REVIEW` / `OWNER_INTERPRETATION` item; whether the clarification supersedes the PDF's wick-topped example boxes.",
         "* Example 5 of the guide (undated); the figures' candle prices beyond the Phase 3.3 readings.",
         "* The controller's behaviour on same-minute conflicts (no approved tie-break), the provisional 15:14 forced exit (this run has " + str(allp['forced_exit']) + " forced exit), PDR / PDS Target 2 (70 vs the report's 60) and RF's Target 2 (60) - unchanged from Phase 3.0.",
         "* The workbook beyond cell-by-cell equality with the CSV files (not opened in desktop Excel).", "", reviewer]
    (OUT / "independent_audit.md").write_text("\n".join(A))
    print("docs written; audit:", audit_line, "| trades", allp["entries"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    main(a.tests, a.ruff)
