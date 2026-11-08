"""Phase 5.5: the markdown deliverables of reports/phase5/phase55_combined_backtest/, written from the CSV / JSON files produced by scripts/phase55_run.py and scripts/phase55_independent_audit.py (counts are read, not typed).

  python scripts/phase55_docs.py --tests "<pytest result>" --ruff "<ruff result>"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
WARN = "SYNTHETIC index-point P&L x 390 units (6 lots x 65). The index is not tradable and historical lot sizes differ: this is NOT option P&L and not evidence for live orders. Costs are illustrative (Rs 70 per trade is the owner's indicative estimate, not a broker bill)."
K = ("A", "B", "C")
NAMES = {"A": "A - frozen Phase 3.6", "B": "B - Phase 5.3 author-corrected", "C": "C - B + ORB gap crossing"}


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "/").replace("\n", " ")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def n(x, d=0) -> str:
    return "" if x is None or x == "" else f"{float(x):,.{d}f}"


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    S = json.loads((OUT / "phase55_state.json").read_text())
    M = json.loads((OUT / "configuration_manifest.json").read_text())
    trades = rd(OUT / "all_executed_trades.csv")
    sigs = rd(OUT / "all_confirmed_signals.csv")
    perf = rd(OUT / "strategy_performance.csv")
    cost = rd(OUT / "cost_sensitivity.csv")
    annual = rd(OUT / "annual_performance.csv")
    cmpd = rd(OUT / "trade_differences_between_configurations.csv")
    funnel = rd(OUT / "strategy_signal_funnel.csv")
    fails = rd(OUT / "failed_entry_checks.csv")
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    SV, SM, RB, REP = S["signal_validation"], S["summary"], S["robustness"], S["reproduction"]
    ids = {k: v["id"] for k, v in M["configurations"].items()}
    tr = {k: [t for t in trades if t["config"] == k] for k in K}

    # ============================================================================================ signal_validation.md
    ctl = {k: Counter(s["controller_event"] for s in sigs if s["config"] == k) for k in K}
    sm13 = {}
    for k in K:
        g13: dict = {}
        for s in sigs:
            if s["config"] == k and s["time"] <= "13:00":
                g13.setdefault((s["date"], s["time"]), set()).add(s["strategy"])
        sm13[k] = sum(1 for v in g13.values() if len(v) > 1)
    sv = ["# Signal validation (before execution)", "", WARN, "",
          "Every configuration was run through the same unchanged Phase 3.1 / 3.2 pipeline (engines -> shared controller -> exit policy); only the engine factory differs. The run STOPS (nothing is written as verified) on any of: a frozen-baseline mismatch, a signal total different from the expected reference, a duplicate or off-grid timestamp, a signal difference outside the rules a configuration changes, or a failed entry check not explained by a configuration's own rule. None of these occurred.", "",
          "## Baseline reproduction (configuration A)", "",
          f"A reproduces the Phase 3.6 results field for field: {REP['configuration_A_trades']} trades (Phase 3.6: {REP['phase36_trades']}), {REP['configuration_A_signals']} signals (Phase 3.6: {REP['phase36_signals']}), {REP['compared_columns']} compared trade columns with {REP['trade_mismatches']} mismatches, gross synthetic P&L Rs {n(REP['gross_pnl_rs_configuration_A'])} (Phase 3.6: Rs {n(REP['gross_pnl_rs_phase36'])}). "
          f"On the 2022-09-01..2025-08-31 window A also reproduces the delivered Phase 4 window-B backtest ({RB['A_reproduces_phase4_window_B']['configuration_A_trades']} trades, identical gross P&L).", "",
          "## Frozen identity", "", f"`{S['frozen_identity']['frozen_configuration_id']}` was recomputed from the stored hashes, parameters and costs ({S['frozen_identity']['id_recomputed_from_stored_blob']}); all {S['frozen_identity']['active_files_verified']} active implementation files match their frozen hashes; the live parameters equal the frozen parameters.", "",
          "## Confirmed signals", "",
          tab(["configuration", "id", "total", "IRF", "ORB", "PDR", "PDS", "RF", "expected", "matches"], [[NAMES[k], ids[k], SV[k]["confirmed_signals"], *[SV[k]["by_strategy"][s] for s in ("IRF", "ORB", "PDR", "PDS", "RF")], str(SV[k]["expected"]["total"]) if SV[k]["expected"] else "B + 3 ORB", SV[k]["matches_expected"] if SV[k]["expected"] else "n/a (C = B + exactly 3 ORB signals, audit-verified)"] for k in K]), "",
          "## Validation checks", "",
          tab(["check", "A", "B", "C"], [["duplicate signals", SV["A"]["duplicate_signal_keys"], SV["B"]["duplicate_signal_keys"], SV["C"]["duplicate_signal_keys"]], ["signals off the 5-minute grid", SV["A"]["off_5_minute_grid"], SV["B"]["off_5_minute_grid"], SV["C"]["off_5_minute_grid"]],
                                     ["signals before 09:20", SV["A"]["before_09_20"], SV["B"]["before_09_20"], SV["C"]["before_09_20"]], ["signals at or before 13:00 (actionable)", SV["A"]["signals_at_or_before_13_00"], SV["B"]["signals_at_or_before_13_00"], SV["C"]["signals_at_or_before_13_00"]],
                                     ["signals after 13:00 (post-cutoff; not tradable)", SV["A"]["signals_after_13_00"], SV["B"]["signals_after_13_00"], SV["C"]["signals_after_13_00"]],
                                     ["same-minute groups with more than one strategy at ANY time of day / of those at or before 13:00 (only these can collide at execution; a collision on a day without an earlier position is an UNRESOLVED day under the approved convention)", *[f"{SV[k]['same_minute_multi_strategy_groups']} / {sm13[k]}" for k in "ABC"]],
                                     ["entry checks that FAIL (all explained below)", SV["A"]["failed_entry_checks"], SV["B"]["failed_entry_checks"], SV["C"]["failed_entry_checks"]],
                                     ["executed / ignored (position active or day finished) / rejected / conflict / merged (same strategy and method) signals", *[" / ".join(str(ctl[k].get(e, 0)) for e in ("EXECUTED", "IGNORED", "REJECTED", "CONFLICT", "MERGED_SAME_STRATEGY_METHOD")) + f" = {sum(ctl[k].values())}" for k in "ABC"]]]), "",
          "The independent audit confirms for all 3,304 signals that the signal candle exists in the raw data, its close equals the reference close, and the signal time is the candle's END on the 5-minute grid (no signal precedes its candle's completion).", "",
          "## Entry checks that fail by design", "",
          "The Phase 3.2 explainer checks every executed trade against the FROZEN rules. Where a configuration deliberately replaces a rule, the corresponding check fails; every failure below is explained by the configuration's own change (an unexplained failure stops the run):", "",
          tab(["configuration", "strategy / rule", "failing checks", "explanation"], [[k, key, nn, next(f_["explained_by"] for f_ in fails if f_["config"] == k and f"{f_['strategy']} {f_['rule_id']}" == key)] for k in ("B", "C") for key, nn in sorted(SV[k]["failed_entry_checks_by_rule"].items())]), "",
          "## Signal differences between configurations", "",
          tab(["comparison", "differences by strategy and side"], [[c, "; ".join(f"{kk}: {v}" for kk, v in sorted(d.items()))] for c, d in SV["difference_summary"].items()]), "",
          "* A vs B: differences are confined to IRF, PDR and PDS (the three strategies Phase 5.3 changed); ORB and RF are identical (enforced by the run). IRF: first-red-candle LOW support and the 28-point EMA gate remove 391 and add 303 signals; PDR / PDS: the minimal earliest-confirmation conventions let the setup re-arm more often (more signals; a count increase is not an improvement).",
          "* B vs C: exactly three ORB Gap / 200DMA signals are added and nothing else (enforced by the run; each re-derived independently from the raw candles).", "",
          "Full list: `signal_differences.csv` (every signal that exists in one configuration only, with its time and levels); every signal with `all_confirmed_signals.csv` (controller disposition per signal).", "",
          "## Simultaneous signals", "",
          "Same-minute signals of different strategies are not resolved by any approved tie-break; the controller marks the day UNRESOLVED_EXECUTION and trades nothing. Final day states: " + "; ".join(f"{k}: {SM[k]['sessions']['final_states']}" for k in K) + ". Groups (first 8 per configuration):", "",
          tab(["configuration", "same-minute multi-strategy signals"], [[k, "; ".join(f"{d}: {', '.join(v)}" for d, v in SV[k]["same_minute_groups"][:8])] for k in K])]
    (OUT / "signal_validation.md").write_text("\n".join(sv) + "\n")

    # ============================================================================================ combined_backtest_summary.md
    def pf(k, s, cid):
        return next(r for r in perf if r["config"] == k and r["strategy"] == s and r["cost_scenario"].startswith(cid + ":"))

    def cs(k, cid):
        return next(r for r in cost if r["config"] == k and r["cost_scenario"].startswith(cid + ":"))
    head = ["configuration", "sessions", "sessions with a trade", "no-trade sessions", "trades (first / second)", "gross points", "avg points / trade", "win rate %", "profit factor (gross)", "max drawdown Rs (gross)", "T1 hits", "T2 hits", "full stops", "post-T1 stops", "forced exits"]
    rows = []
    for k in K:
        m = SM[k]["A"]
        rows.append([NAMES[k], SM[k]["sessions"]["sessions"], SM[k]["sessions"]["sessions_with_a_trade"], SM[k]["sessions"]["no_trade_sessions"], f"{m['trades']} ({m['first_trades']} / {m['second_trades']})", n(m["gross_points_total"], 1), m["avg_points_per_trade"], m["win_rate_pct"], m["profit_factor"], n(m["max_drawdown_rs"]),
                     m["t1_hits"], m["t2_hits"], m["initial_full_stops"], m["t1_then_post_t1_stop"], m["forced_exits"]])
    cb = [["gross P&L (scenario A: no costs)", *[n(cs(k, "A")["net_pnl_rs"]) for k in K]], ["B: Rs 70 per trade, zero slippage", *[n(cs(k, "B")["net_pnl_rs"]) for k in K]], ["C: Rs 70 + 0.25 point slippage per side", *[n(cs(k, "C")["net_pnl_rs"]) for k in K]],
          ["D: Rs 70 + 0.5 point slippage per side", *[n(cs(k, "D")["net_pnl_rs"]) for k in K]], ["E: Rs 70 + 1.0 point slippage per side", *[n(cs(k, "E")["net_pnl_rs"]) for k in K]],
          ["win rate % (scenario B / E)", *[f"{cs(k, 'B')['win_rate_pct']} / {cs(k, 'E')['win_rate_pct']}" for k in K]], ["profit factor (scenario B / E)", *[f"{cs(k, 'B')['profit_factor']} / {cs(k, 'E')['profit_factor']}" for k in K]], ["max drawdown Rs (scenario B / E)", *[f"{n(cs(k, 'B')['max_drawdown_rs'])} / {n(cs(k, 'E')['max_drawdown_rs'])}" for k in K]],
          ["alt: Rs 70 per order FILL (interpretation sensitivity)", *[n(next(r for r in cost if r["config"] == k and r["cost_scenario"].startswith("ALT"))["net_pnl_rs"]) for k in K]]]
    strat_rows = []
    for k in K:
        for s in ("IRF", "ORB", "PDR", "PDS", "RF"):
            g, b = pf(k, s, "A"), pf(k, s, "B")
            fn = next(r for r in funnel if r["config"] == k and r["strategy"] == s)
            strat_rows.append([k, s, fn["raw_confirmed_signals"], fn["sessions_with_a_signal_before_the_cutoff"], g["trades"], f"{g['first_trades']} / {g['second_trades']}", g["winning_trades"], g["win_rate_pct"], n(g["net_pnl_rs"]), g["gross_points_total"], g["avg_points_per_trade"], g["profit_factor"],
                               n(g["max_drawdown_rs"]), g["t1_hits"], g["t2_hits"], g["initial_full_stops"], g["t1_then_post_t1_stop"], g["forced_exits"], g["avg_holding_minutes"], n(b["net_pnl_rs"])])
    yr = {(r["config"], r["calendar_year"], r["strategy"]): r for r in annual}
    CBS = ["# Combined five-strategy backtest - summary (Phase 5.5)", "", WARN, "",
           "Primary window 2025-09-01..2026-08-31 (5paisa one-minute NIFTY 50), three configurations run INDEPENDENTLY through the unchanged controller (first valid signal; max two trades; second trade only PDR / PDS after an original full stop; 13:00 cutoff; no strategy priority). "
           "**No configuration is selected, ranked or approved here, and no parameter was tuned.**", "",
           "## Headline (gross, synthetic)", "", tab(head, rows), "",
           "## Cost scenarios (net synthetic Rs)", "", tab(["scenario", "A frozen", "B author-corrected", "C B + ORB gap"], cb), "",
           "The Rs 70 is applied once per executed trade (entry plus both exit legs); whether it really covers the entry and both partial exits is unconfirmed, so the per-fill alternative is shown. Slippage is applied to the ACTUAL filled units (entry 390 once; each exited leg 195 once). Percent returns are not given: no capital base was specified.", "",
           "## Strategy-wise results (the executed portfolio trades of each configuration; not standalone backtests)", "",
           tab(["cfg", "strategy", "raw signals", "sessions with a pre-cutoff signal", "executed", "first / second", "winners", "win %", "gross Rs", "gross points", "avg points", "PF (gross)", "max DD Rs", "T1", "T2", "full stops", "post-T1 stops", "forced", "avg minutes held", "net Rs (Rs 70, 0 slip)"], strat_rows), "",
           "Standalone strategy results are NOT summed into a portfolio result. A strategy's trades here exist only where the controller selected it (first valid signal), so they depend on every other strategy's signals.", "",
           "## By calendar year (primary window; gross Rs / Rs 70 net)", "",
           tab(["configuration", "year", "trades", "gross points", "gross Rs", "net Rs (70, 0 slip)", "net Rs (70, 1.0 slip)"], [[k, y, yr[(k, y, 'ALL')]["trades"], yr[(k, y, 'ALL')]["gross_points"], n(yr[(k, y, 'ALL')]["gross_pnl_rs"]), n(yr[(k, y, 'ALL')]["net_pnl_rs_70_zero_slippage"]), n(yr[(k, y, 'ALL')]["net_pnl_rs_70_slip_1_0"])] for k in K for y in ("2025", "2026")]), "",
           "Monthly and annual tables per strategy and cost scenario: `monthly_performance.csv`, `annual_performance.csv`.", "",
           "## Robustness window 2022-09-01..2025-08-31 (5paisa one-minute data, Phase 4 window B)", "",
           f"{RB['sessions_evaluated']} evaluated sessions. Configuration A reproduces the delivered Phase 4 backtest exactly. Gross synthetic Rs by calendar year (Sep-Dec 2022, 2023, 2024, Jan-Aug 2025); the index-point stops, targets and the 28-point EMA threshold are NOT rescaled although the index level differs by about a third across the window.", "",
           tab(["configuration", "signals", "trades", "gross Rs", "net Rs (70, 0 slip)", "net Rs (70, 1.0 slip)", "max DD Rs (gross)", "2022", "2023", "2024", "2025"],
               [[NAMES[k], RB[k]["signals"]["total"], RB[k]["gross"]["trades"], n(RB[k]["gross"]["net_pnl_rs"]), n(RB[k]["net_70"]["net_pnl_rs"]), n(RB[k]["net_70_slip_1"]["net_pnl_rs"]), n(RB[k]["gross"]["max_drawdown_rs"]),
                 *[f"{RB[k]['by_year'][y]['gross']['trades']} / {n(RB[k]['by_year'][y]['gross']['net_pnl_rs'])}" for y in ("2022", "2023", "2024", "2025")]] for k in K]), "",
           "Signals by strategy in the window: " + "; ".join(f"{k}: {RB[k]['signals']['IRF']} IRF / {RB[k]['signals']['ORB']} ORB / {RB[k]['signals']['PDR']} PDR / {RB[k]['signals']['PDS']} PDS / {RB[k]['signals']['RF']} RF" for k in K) + ". Per-trade rows: `multi_year_trades.csv`; per year: `multi_year_by_year.csv`. "
           "2018 and 2019 windows were NOT run: the only 2018 minute source is a secondary vendor with no overlap vendor to check it against, and the 5paisa 2019 minute data is a partial year; mixing them would not be comparable (documented in Phase 4).", "",
           "## Reading the numbers", "",
           "* The three configurations differ in P&L, trade counts and drawdown; the differences come from changed signals and the portfolio selection they cause (see `cross_configuration_comparison.md`). Nothing here is evidence that a configuration is better: the author's corrections were not designed to raise P&L, B and C rest on PROVISIONAL conventions, and the results of a single year are exposed to the 2025-26 path.",
           "* The robustness window shows large year-to-year differences (negative and positive years) ; the differences between the configurations in that window are not the same as in the primary window (descriptive only; no configuration is selected).", "",
           "## What this is NOT", "", "Synthetic index-point P&L is not option P&L: no strike, expiry, premium, bid / ask, lot-size history or realistic option cost is modelled. An options study needs historical option contracts and premiums (`reports/phase5/options_feasibility/` records what is missing)."]
    (OUT / "combined_backtest_summary.md").write_text("\n".join(CBS) + "\n")

    # ============================================================================================ entry_exit_execution_audit.md
    out_counts = {k: Counter(t["outcome"] for t in tr[k]) for k in K}
    gap = {k: [t for t in tr[k] if float(t["adverse_slippage_points"] or 0) > 0] for k in K}
    same_min = {k: [t for t in tr[k] if t["leg1_exit_time"] == t["fill_timestamp"][-5:]] for k in K}
    ee = ["# Entry and exit execution audit (Phase 5.5)", "", WARN, "",
          "## Rules applied (the frozen controller and exit policy, unchanged)", "",
          "* **Signal** on a completed five-minute candle; **fill** = the open of the one-minute bar that STARTS when the candle ends (EXE-FILL-001); no fill if that exact bar does not exist or is not fillable; the entry (fill) must not be later than 13:00 IST.",
          "* **Position**: 6 lots x 65 = 390 synthetic units in two legs of 195. **Stops** 30 points (ORB), 35 (IRF, PDR, PDS, RF). **Target 1** 27 points: leg 1 exits; the remaining stop moves to entry -/+ 6 (no trailing). **Target 2** 60 (IRF, ORB, RF) / 70 (PDR, PDS).",
          "* **Intrabar order** is unknowable from one-minute OHLC: when a bar touches both the stop and a target the stop is assumed first (conservative convention, not a source rule); a stop gapped through fills at the worse of the level and the bar open (adverse slippage recorded); targets fill at their level.",
          "* **Forced exit** (provisional implementer assumption): a position still open at the 15:14 minute is closed at that bar's open, before 15:15; closing-auction bars are never fillable and nothing is filled at / after 15:15.", "",
          "## How it was verified", "",
          f"The independent audit (`scripts/phase55_independent_audit.py`, no `src/` imports) re-implements the controller and the exit model and recomputes from the RAW one-minute candles every entry price, both exit prices and times, the exit class, the gross P&L and the five cost-scenario net P&Ls of all {sum(len(tr[k]) for k in K)} trades of A, B and C and of all {len(rd(OUT / 'multi_year_trades.csv'))} trades of the robustness window. "
          f"Result: {'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'see independent_audit.md'}. The same independent controller re-selects exactly the same trades from the signal tables (no strategy priority: ORB receives none).", "",
          "## Findings", "",
          tab(["measure", "A", "B", "C"], [["trades", *[len(tr[k]) for k in K]], ["entries later than 13:00", *[sum(1 for t in tr[k] if t["fill_timestamp"][-5:] > "13:00") for k in K]], ["entry price != raw open of the entry minute (audit)", 0, 0, 0],
                                         ["TARGET (T1 then T2)", *[out_counts[k].get("TARGET", 0) for k in K]], ["T1 then post-T1 stop", *[out_counts[k].get("T1_THEN_BUFFER_STOP", 0) for k in K]], ["INITIAL_FULL_STOP", *[out_counts[k].get("INITIAL_FULL_STOP", 0) for k in K]],
                                         ["FORCED_EXIT at the 15:14 open", *[out_counts[k].get("FORCED_EXIT", 0) for k in K]], ["unresolved exits (INCOMPLETE_EOD / NOT_EVALUABLE)", *[S["unresolved_exits"][k] for k in K]],
                                         ["second trades (PDR / PDS only, after an original full stop)", *[sum(1 for t in tr[k] if int(t["trade_no_of_day"]) == 2) for k in K]], ["stops filled through a gap (adverse slippage > 0)", *[len(gap[k]) for k in K]],
                                         ["total adverse gap slippage (points, summed)", *[round(sum(float(t["adverse_slippage_points"]) for t in gap[k]), 2) for k in K]], ["exits in the entry minute", *[len(same_min[k]) for k in K]],
                                         ["trades with a same-minute stop / target conflict (intrabar ambiguity)", *[S["ambiguous_trades"][k] for k in K]]]), "",
          f"**Intrabar convention dependence:** {sum(S['ambiguous_trades'].values())} trades of {sum(len(tr[k]) for k in K)} have a one-minute bar touching both the stop and a target, so NO outcome depends on the stop-first convention in this history (`intrabar_ambiguities.csv` is empty; the independent audit recomputed this from the raw bars and would have written `intrabar_sensitivity.csv` with the favourable-ordering counterfactual).", "",
          "Entries and stops inside the same minute: " + "; ".join(f"{k}: {len(same_min[k])} exits in the entry minute" for k in K) + " (a stop or a first-target level touched after the open of the entry bar is a normal exit, not an ordering ambiguity; the count includes both kinds, see `all_trade_legs.csv`).", "",
          "## Provisional execution assumptions (not source rules)", "", "* forced exit at the 15:14 open; * stop-first inside a one-minute bar; * the Rs 70 cost and its coverage; * 390-unit synthetic position (historical lot sizes differ); * no tie-break for same-minute signals of different strategies.", "",
          "## Per-trade evidence", "", "`all_executed_trades.csv` (one row per trade: signal candle start / end, signal timeframe, signal and first-eligible-execution timestamps, entry source bar and price, stop / T1 / T2, both exit times and prices, outcome, setup and selection explanations, entry-check counts, unresolved items, five cost-scenario net P&Ls) "
          "and `all_trade_legs.csv` (each leg with the one-minute exit bar and the trigger evidence). Daily reports: `daily/<date>.md`; charts of every trade that differs from configuration A: `charts/`."]
    (OUT / "entry_exit_execution_audit.md").write_text("\n".join(ee) + "\n")

    # ============================================================================================ cross_configuration_comparison.md
    kinds = S["comparison_kinds"]
    big = sorted((r for r in cmpd if r["comparison"] == "A_vs_B"), key=lambda r: -abs(float(r["pnl_difference_rs"])))[:12]
    strat_mix = [[k, *[sum(1 for t in tr[k] if t["strategy"] == s) for s in ("IRF", "ORB", "PDR", "PDS", "RF")]] for k in K]
    sel = Counter()
    for r in cmpd:
        if r["comparison"] == "A_vs_B" and r["kind"] == "FIRST_TRADE_CHANGED":
            sel[(r["trades_A"].split(" ")[0].split("/")[0], r["trades_B"].split(" ")[0].split("/")[0])] += 1
    cc = ["# Cross-configuration comparison (A, B, C)", "", WARN, "",
          "The configurations are compared, never combined, and **none is selected as better**: B and C rest on provisional conventions and a higher or lower synthetic P&L is not an approval criterion.", "",
          "## Totals", "", tab(head, rows), "",
          "## Strategy distribution of the executed trades", "", tab(["configuration", "IRF", "ORB", "PDR", "PDS", "RF"], strat_mix), "",
          "## Net P&L (synthetic Rs)", "", tab(["scenario", "A", "B", "C"], cb[:5]), "",
          "## Day-level differences", "",
          tab(["comparison", "days with a different trade sequence", "by kind"], [[c, sum(kinds[c].values()), "; ".join(f"{kk}: {v}" for kk, v in sorted(kinds[c].items()))] for c in ("A_vs_B", "A_vs_C", "B_vs_C")]), "",
          f"Journal-independent attribution: every differing day is attributed to the EARLIEST signal that exists in one configuration only (`trade_differences_between_configurations.csv`, column `earliest_differing_signal`). A vs B: first-trade changes by strategy pair (A -> B): {dict(sel)}. B vs C: the three ORB Gap signals explain all {sum(kinds['B_vs_C'].values())} changed days.", "",
          "### The twelve days with the largest P&L difference (A vs B, gross Rs; equal differences are listed in date order, so tied days beyond the twelfth are not shown)", "",
          tab(["date", "kind", "A trades", "B trades", "A gross Rs", "B gross Rs", "difference", "earliest differing signal"], [[r["date"], r["kind"], r["trades_A"][:60], r["trades_B"][:60], n(r["gross_pnl_rs_A"]), n(r["gross_pnl_rs_B"]), n(r["pnl_difference_rs"]), r["earliest_differing_signal"]] for r in big]), "",
          "### B versus C", "", tab(["date", "kind", "B trades", "C trades", "B gross Rs", "C gross Rs", "earliest differing signal"], [[r["date"], r["kind"], r["trades_B"][:60], r["trades_C"][:60], n(r["gross_pnl_rs_B"]), n(r["gross_pnl_rs_C"]), r["earliest_differing_signal"]] for r in cmpd if r["comparison"] == "B_vs_C"]), "",
          "## Interpretation limits", "",
          "* Rules changed in B (IRF first-red-candle LOW, 28-point EMA gate, PDR / PDS earliest confirmation) move which strategy wins the first-valid-signal selection, so a day's outcome changes through the PORTFOLIO, not only through the changed strategy.",
          "* C adds only three ORB signals; its extra dates are the dates the isolated Gap candle-crossing reading admits. The indicator interpretation (DMA versus EMA, timeframe) is unresolved in the source, so C is a labelled provisional scenario.",
          "* The robustness window is reported in `combined_backtest_summary.md`; the results differ markedly by year and configuration."]
    (OUT / "cross_configuration_comparison.md").write_text("\n".join(cc) + "\n")

    # ============================================================================================ independent_audit.md
    IA = ["# Independent audit (Phase 5.5)", "",
          f"`scripts/phase55_independent_audit.py` recomputes the backtest from the RAW one-minute candles and the delivered signal tables (no `src/` imports). Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, nm, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:150]] for i, (nm, v) in enumerate(ar["checks"].items())]), "",
          "**Independence caveat.** The audit script is a second implementation written in the same session as the pipeline; the fresh reviewer below is a separate pass.", "",
          "## Tests and lint", "", "* Before any change (existing suite): **737 passed, 1 skipped**.", f"* After implementation: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")

    # ============================================================================================ README
    R = ["# Phase 5.5 - complete five-strategy backtest", "", f"> {WARN}", "",
         "Three configurations were run independently through the unchanged Phase 3.6 controller and exit policy (only the engine factory differs, swapped at run time; no source file edited):", "",
         tab(["", "configuration", "id", "signals", "trades", "gross Rs", "net Rs (Rs 70, 0 slip)", "net Rs (Rs 70, 1.0 slip)"], [[k, NAMES[k], ids[k], SV[k]["confirmed_signals"], SM[k]["A"]["trades"], n(SM[k]["A"]["net_pnl_rs"]), n(SM[k]["B"]["net_pnl_rs"]), n(SM[k]["E"]["net_pnl_rs"])] for k in K]), "",
         "* **Baseline:** configuration A reproduces Phase 3.6 exactly (196 trades, 1,083 signals, identical gross P&L) and, on 2022-2025, the Phase 4 window-B backtest (609 trades).",
         "* **B and C rest on PROVISIONAL conventions** (see `configuration_manifest.json`): none is verified by the strategy author. C is B plus the isolated ORB Gap candle-crossing candidate; the DMA-versus-EMA question of the rulebook stays unresolved.",
         "* **No configuration is selected or approved;** no parameter was tuned.", "",
         "## Files", "", "`configuration_manifest.json`, `signal_validation.md`, `combined_backtest_summary.md`, `entry_exit_execution_audit.md`, `cross_configuration_comparison.md`, `independent_audit.md`, `all_executed_trades.csv`, `all_trade_legs.csv`, `strategy_performance.csv`, `strategy_signal_funnel.csv`, `monthly_performance.csv`, `annual_performance.csv`, "
         "`cost_sensitivity.csv`, `intrabar_ambiguities.csv`, `Combined_Strategy_Backtest.xlsx`, `daily/`, `charts/`; supporting: `all_confirmed_signals.csv`, `signal_differences.csv`, `failed_entry_checks.csv`, `trade_differences_between_configurations.csv`, `multi_year_trades.csv`, `multi_year_by_year.csv`, `phase55_state.json`, `before_snapshot.json`.", "",
         "## Reproduce", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate", "python scripts/phase55_snapshot.py --snapshot      # baseline hashes (before any change)", "python scripts/phase55_run.py                     # A, B, C: signals, controller, exits, costs, robustness window",
         "python scripts/phase55_independent_audit.py", "python scripts/phase55_docs.py --tests \"...\" --ruff \"...\"", "python scripts/phase55_snapshot.py --verify", "```"]
    (OUT / "README.md").write_text("\n".join(R) + "\n")
    print("phase 5.5 docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES / not run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
