"""Phase 6.1-6.3 documentation: configuration comparison (every differing date with its earliest causal reason), summaries, READMEs, the 6.2 workbook and the consolidated final report. Numbers are read from the result files."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase61_common import R61, R62, R63, SCRATCH, write_csv  # noqa: E402

from nifty_trading.research.orb_v2.reporting import md_table, write_workbook  # noqa: E402

CFG = ("A", "B", "C")


def jload(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else {}


def main() -> int:  # noqa: C901
    res = pickle.loads((SCRATCH / "results62.pkl").read_bytes())
    r63 = pickle.loads((SCRATCH / "results63.pkl").read_bytes())
    A = res["A"]
    s61, s62 = jload(R61 / "phase61_state.json"), jload(R62 / "phase62_state.json")
    perf = pd.read_csv(R62 / "strategy_performance.csv")
    cost = pd.read_csv(R62 / "cost_sensitivity.csv")
    ann = pd.read_csv(R62 / "annual_performance.csv")
    audit = jload(R62 / "execution_audit_summary.json")
    P = lambda w, k, s="ALL": perf[(perf.window == w) & (perf.config == k) & (perf.strategy == s)].iloc[0]  # noqa: E731
    # ------------------------------------------------------------------ configuration differences, every date (primary window)
    sig = {k: defaultdict(set) for k in CFG}
    for k in CFG:
        for s in A["signals"][k]:
            sig[k][s["date"]].add((s["time"], s["strategy"], s["method"], s["direction"]))
    tr = {k: defaultdict(list) for k in CFG}
    for k in CFG:
        for r in A["ledgers"][k]:
            tr[k][r["date"]].append(r)
    jrows = defaultdict(list)
    for r in r63["rows"]:
        jrows[r.date].append(r)
    stage = {}
    for k in CFG:
        for st, key in (("STRICT", "strict"), ("TIME_TOLERANT", "tolerant"), ("DATE_STRATEGY_ONLY", "date_only")):
            for _jid, tid in r63["detail_stage"][k][key]:
                stage[(k, tid)] = st
    desc = lambda k, d: "; ".join(f"{r['strategy']}/{r['method']} {r['direction']}@{r['entry_time']} {r['outcome']}" for r in sorted(tr[k].get(d, []), key=lambda x: (x["entry_time"], int(x["trade_no"])))) or "no trade"  # noqa: E731
    diffs = []
    kinds = Counter()
    for d in sorted(A["days"]["C"]):
        ds = str(d)
        a, b, c = desc("A", ds), desc("B", ds), desc("C", ds)
        if a == b == c:
            continue

        def first_change(x, y, ds=ds):
            dif = sorted(sig[x][ds] ^ sig[y][ds])
            return (f"{dif[0][0]} {dif[0][1]} {dif[0][2]} ({'only in ' + (x if dif[0] in sig[x][ds] else y)})") if dif else "none"
        fc_ab, fc_bc = first_change("A", "B"), first_change("B", "C")
        first = {k: sorted(tr[k].get(ds, []), key=lambda x: (x["entry_time"], int(x["trade_no"]))) for k in CFG}
        orb_early = bool(first["C"]) and first["C"][0]["strategy"] == "ORB" and not (first["B"] and first["B"][0]["strategy"] == "ORB" and first["B"][0]["entry_time"] == first["C"][0]["entry_time"])
        core = lambda k, ds=ds: sorted((r["strategy"], r["direction"], r["entry_time"], r["outcome"]) for r in tr[k].get(ds, []))  # noqa: E731
        orb_rej = {r["date"]: r["failed"] for r in A["orb_rejections"]}
        if b != c and core("B") == core("C"):
            reason, kind = "same trades in B and C; only the method label differs (no real change)", "B_vs_C: method label only"
        elif b != c:
            only = {s_[1] for s_ in sig["B"][ds] ^ sig["C"][ds]}
            fb, fcx = (first["B"][0] if first["B"] else None), (first["C"][0] if first["C"] else None)
            if fcx and fcx["strategy"] == "ORB" and not (fb and fb["strategy"] == "ORB"):
                reason, kind = f"ORB V2 qualified at 09:20 and took the first trade (B's first trade: {fb['strategy'] + '@' + fb['entry_time'] if fb else 'none'})", "B_vs_C: ORB V2 took the first trade"
            elif fb and fb["strategy"] == "ORB" and not any(r["strategy"] == "ORB" for r in first["C"]):
                reason, kind = f"legacy ORB traded at 09:20 in B; ORB V2 produced no signal (rejection: {orb_rej.get(ds, 'n/a')})", "B_vs_C: legacy ORB trade not reproduced by ORB V2"
            elif fb and fcx and fb["strategy"] == "ORB" and fcx["strategy"] == "ORB":
                reason, kind = "both traded ORB at 09:20 but with a different direction / outcome", "B_vs_C: ORB direction/outcome differs"
            elif only <= {"ORB"}:
                reason, kind = "ORB signal sets differ without changing the first trade", "B_vs_C: ORB signal difference, first trade unchanged"
            else:
                reason, kind = "downstream of the ORB V2 selection / second-trade eligibility (IRF V2 equals the Phase 5.3 IRF, so IRF V2 itself changes nothing between B and C)", "B_vs_C: downstream"
        else:
            reason, kind = "A vs B only (IRF first-red-low + 28-pt rule and PDR/PDS first-eligible)", "A_vs_B only"
        if a != b:
            ab_strats = {s[1] for s in sig["A"][ds] ^ sig["B"][ds]}
            reason_ab = "A->B first changed signal strategy: " + "/".join(sorted(ab_strats)) if ab_strats else "A->B: same signals, different selection"
        else:
            reason_ab = "A = B"
        n2 = {k: len(first[k]) for k in CFG}
        jr = "; ".join(f"{x.strategy}@{x.time_label} {x.outcome}" for x in jrows.get(ds, [])) or "no journal row"
        kinds[kind] += 1
        diffs.append({"date": ds, "A": a, "B": b, "C": c, "first_changed_signal_A_vs_B": fc_ab, "first_changed_signal_B_vs_C": fc_bc, "selected_first_A": f"{first['A'][0]['strategy']}@{first['A'][0]['entry_time']}" if first["A"] else "none",
                      "selected_first_B": f"{first['B'][0]['strategy']}@{first['B'][0]['entry_time']}" if first["B"] else "none", "selected_first_C": f"{first['C'][0]['strategy']}@{first['C'][0]['entry_time']}" if first["C"] else "none",
                      "orb_v2_qualified_earlier_in_C": orb_early, "trades_A_B_C": f"{n2['A']}/{n2['B']}/{n2['C']}", "second_trade_effect": "yes" if len({n2['A'], n2['B'], n2['C']}) > 1 else "no", "b_vs_c_kind": kind, "earliest_causal_reason_B_vs_C": reason, "earliest_causal_reason_A_vs_B": reason_ab,
                      "gross_rs_A": round(sum(float(r["gross_pnl_rs"]) for r in tr["A"].get(ds, [])), 0), "gross_rs_B": round(sum(float(r["gross_pnl_rs"]) for r in tr["B"].get(ds, [])), 0), "gross_rs_C": round(sum(float(r["gross_pnl_rs"]) for r in tr["C"].get(ds, [])), 0),
                      "journal_rows": jr, "journal_status_C": "; ".join(f"{t['strategy']}:{stage.get(('C', t['trade_id']), 'AUTOMATED_ONLY')}" for t in tr["C"].get(ds, [])) or "no C trade"})
    write_csv(R62 / "trade_differences_between_configurations.csv", diffs)
    # ------------------------------------------------------------------ 6.2 summary documents
    def fmt(k, w="A"):
        r = P(w, k)
        return {"config": k, "trades": int(r.trades), "win_rate_pct": r.win_rate_pct, "profit_factor": r.profit_factor, "gross_points": r.gross_points_total, "gross_rs": r.gross_synthetic_rs, "net_rs_70": r.net_rs_70_per_trade, "max_drawdown_rs": r.max_drawdown_rs}
    summ_rows = [fmt(k) for k in ("A", "B", "C", "D1", "D2")]
    strat_rows = [{k: v for k, v in r.items() if k in ("config", "strategy", "trades", "win_rate_pct", "profit_factor", "gross_points_total", "gross_synthetic_rs", "net_rs_70_per_trade", "max_drawdown_rs", "initial_stop_pct", "t1_pct", "t2_pct", "post_t1_stop_pct", "forced_exit_pct", "avg_holding_minutes")}
                  for r in perf[(perf.window == "A") & perf.config.isin(["A", "B", "C"])].to_dict("records")]
    cost_t = cost[(cost.window == "A") & cost.config.isin(["A", "B", "C"])].pivot(index="label", columns="config", values="net_pnl_rs").reset_index().to_dict("records")
    costB = cost[(cost.window == "B") & cost.config.isin(["A", "B", "C"])].pivot(index="label", columns="config", values="net_pnl_rs").reset_index().to_dict("records")
    annt = ann[ann.config.isin(["A", "B", "C"])].pivot_table(index=["window", "calendar_year"], columns="config", values="gross_rs").reset_index().to_dict("records")
    sc = {w: {k: s62["summary"][w][k]["signals"] for k in ("A", "B", "C")} for w in "AB"}
    orbC, orbA = P("A", "C", "ORB"), P("A", "A", "ORB")
    (R62 / "combined_backtest_summary.md").write_text("\n".join([
        "# Combined five-strategy backtest (Phase 6.2)", "", "**Synthetic NIFTY index-point P&L x 390 units (6 lots x 65; legs 195 + 195); the index is not tradable and this is NOT option profit. Research only: no orders, no configuration selected, not optimised, not out-of-sample.** "
        "The shared controller, exit policy, stops (IRF/PDR/PDS/RF 35, ORB 30), T1 27, T2 (IRF/ORB/RF 60, PDR/PDS 70), post-T1 stop entry -/+ 6, 13:00 cutoff and 15:14-open forced exit are the frozen ones; nothing was edited.", "",
        "A = Phase 3.6 frozen; B = Phase 5.3 author-corrected (legacy ORB); C = IRF V2 + ORB V2 (provisional ORB-V2-A; the standalone 30/60 exits are NOT used) + PDR/PDS first-eligible + RF; D1 = IRF V2 + legacy ORB (diagnostic: identical to B because IRF V2 == Phase 5.3 IRF); D2 = frozen IRF + ORB V2 (diagnostic attribution of the ORB change). "
        "D is attribution only, not a selection device.", "", "## Primary window 2025-09-01 .. 2026-08-31 (5paisa)", "", md_table(summ_rows), "",
        f"Confirmed signals A/B/C: {sc['A']['A']['total']} / {sc['A']['B']['total']} / {sc['A']['C']['total']} (IRF {sc['A']['A']['IRF']} / {sc['A']['B']['IRF']} / {sc['A']['C']['IRF']}; ORB {sc['A']['A']['ORB']} / {sc['A']['B']['ORB']} / {sc['A']['C']['ORB']}; PDR {sc['A']['A']['PDR']} / {sc['A']['B']['PDR']} / {sc['A']['C']['PDR']}; PDS {sc['A']['A']['PDS']} / {sc['A']['B']['PDS']} / {sc['A']['C']['PDS']}; RF {sc['A']['A']['RF']} / {sc['A']['B']['RF']} / {sc['A']['C']['RF']}).", "",
        "## Strategy contributions inside each portfolio (NOT standalone profits; they must not be added to a portfolio figure)", "", md_table(strat_rows), "",
        f"ORB V2 inside configuration C: {int(orbC.trades)} trades, gross {orbC.gross_points_total:+.2f} weighted points (Rs {orbC.gross_synthetic_rs:+,.0f}), profit factor {orbC.profit_factor}; the frozen ORB inside A: {int(orbA.trades)} trades, {orbA.gross_points_total:+.2f} points (Rs {orbA.gross_synthetic_rs:+,.0f}), profit factor {orbA.profit_factor}. "
        "The standalone ORB V2 backtest of Phase 6.0 (30/60 on one lot, 75 units) is a different exit model and is unchanged; the two must not be compared as if they were the same trades.", "", "## Cost scenarios, primary window (net synthetic Rs)", "", md_table(cost_t), "",
        "Rs 70 is the owner's indicative estimate (brokerage ~Rs 30 + charges ~Rs 40), not a verified bill. 'Per order fill' = Rs 70 on the entry and on each exit leg actually filled; slippage is adverse points on every unit of every fill (no unit charged twice). The old Rs 500 assumption is not used.", "",
        "## Robustness window 2022-09-01 .. 2025-08-31 (5paisa, Phase 4 store)", "", md_table([fmt(k, "B") for k in ("A", "B", "C", "D1", "D2")]), "", md_table(costB), "", "## Gross Rs by calendar year", "", md_table(annt), "",
        "Neither window is untouched out-of-sample (the 2025-26 window shaped earlier research; the 2022-25 window was used in Phases 4-5). Results differ strongly year to year in every configuration.", "",
        "## Controller states (primary window)", "", md_table([{"config": k, **s62["summary"]["A"][k]["sessions"]["final_states"], "sessions_with_a_trade": s62["summary"]["A"][k]["sessions"]["sessions_with_a_trade"]} for k in ("A", "B", "C")]), ""]))
    (R62 / "configuration_comparison.md").write_text("\n".join([
        "# Configuration comparison (A / B / C), with the earliest causal reason for every differing date", "", "No configuration is preferred. IRF V2 produces exactly the same signals as the Phase 5.3 IRF (the owner-approved first-red-low and 28-point rules were already implemented there), so every difference between B and C comes from ORB V2 and its consequences; "
        "every difference between A and B comes from the Phase 5.3 corrections. Dates where B and C list the same trades and differ only in the method label are not counted as changes.", "", f"Dates on which A, B and C differ (primary window): **{len(diffs)}** of {len(A['days']['C'])}. By kind: {dict(kinds)}.", "",
        "Reading the table: 'ORB V2 took the first trade' = ORB V2 signalled at 09:20 and the day's first trade was ORB in C but not in B; on other dates legacy ORB traded in B and ORB V2 did not signal. A later IRF or PDR/PDS trade that B took is then no longer available (one trade at a time; the second trade only after a full stop). "
        "The outcome difference on a date is therefore the path of different trades, not a statement that one rule earns more.", "", md_table(diffs[:60], ["date", "A", "B", "C", "earliest_causal_reason_B_vs_C", "first_changed_signal_B_vs_C", "gross_rs_B", "gross_rs_C", "journal_rows"]), "", f"(first 60 of {len(diffs)} shown; the complete list with the A-vs-B reason, second-trade effect and journal status is `trade_differences_between_configurations.csv`.)", "",
        "## Attribution by configuration D", "", md_table([fmt(k) for k in ("A", "B", "D1", "D2", "C")]), "", "D1 equals B (IRF V2 == Phase 5.3 IRF). D2 (frozen IRF + ORB V2) isolates the ORB change from A's IRF.", "", "Counts of dates by first trade: " + json.dumps({k: dict(Counter((tr[k][d][0]["strategy"] if tr[k].get(d) else "none") for d in {str(x) for x in A['days']['C']})) for k in CFG})]))
    audit_tot = {"trades": sum(v["trades"] for v in audit.values()), "verified": sum(v["fully_verified"] for v in audit.values()), "problems": sum(v["problems"] for v in audit.values())}
    chk = s62.get("reproduction", {})
    (R62 / "entry_exit_execution_audit.md").write_text("\n".join([
        "# Entry / exit execution audit", "", "Method: `scripts/phase62_audit.py` re-derives, from the RAW one-minute bars and with a separate NumPy simulator (it does not call `exit_policy` or `trading_day`), the entry price, all levels, both leg exits (price and minute), the outcome class, the same-minute-ambiguity flag and the gross rupee P&L of every executed trade.", "",
        md_table([{"window|config": k, **v} for k, v in audit.items()]), "", f"**{audit_tot['verified']} of {audit_tot['trades']} executed trades verified, {audit_tot['problems']} problems** (see `execution_audit_problems.csv`).", "",
        "Checks per trade: (1) the fill is the open of the 1-minute bar that starts when the signal candle ends (never before the signal is complete) and not after 13:00; (2) entry price = raw bar open; (3) stop / T1 / T2 / post-T1 levels = entry -/+ the strategy's distances (35 or 30; 27; 60 or 70; 6); (4) position 195 + 195; "
        "(5) the exit sequence under the documented conventions: stop before target in one bar (flagged), a bar opening through a stop fills at its open, targets at their level, Target 1 then Target 2 in one bar allowed, post-T1 stop = entry -/+ 6 with no trailing, forced exit at the 15:14 open, nothing at/after 15:15 or on a closing-auction bar; (6) P&L.", "",
        "Regression gates inside `phase62_run.py` (the run aborts otherwise): configuration A reproduces the Phase 5.5 ledger (" + f"{chk.get('A', {}).get('reproduced_trades')} trades, {chk.get('A', {}).get('mismatches')} mismatches), B reproduces the Phase 5.5 ledger ({chk.get('B', {}).get('reproduced_trades')} trades, {chk.get('B', {}).get('mismatches')} mismatches), "
        f"A on the 2022-25 window reproduces Phase 4 ({chk.get('window_B_A_vs_phase4', {}).get('now')} trades), D1 equals B on both windows.", "", "Same-minute ambiguities: " + str(sum(1 for r in pd.read_csv(R62 / "intrabar_ambiguities.csv").itertuples())) + " (all configurations and windows); each is resolved adversely by the predeclared conservative policy and listed in `intrabar_ambiguities.csv`.", "",
        "ORB V2 integration checks (`orb_v2_integration_checks.csv`): for every session the 09:15-09:20 candle of ORB V2 equals the controller's own session candle; every ORB V2 signal candle runs 09:15-09:20 and its fill is the 09:20 bar open."]))
    write_workbook(R62 / "Combined_Five_Strategy_Backtest.xlsx", {"Summary": [fmt(k, w) | {"window": w} for w in "AB" for k in ("A", "B", "C", "D1", "D2")], "Strategy_performance": perf.to_dict("records"), "Cost": cost.to_dict("records"), "Annual": ann.to_dict("records"), "Monthly": pd.read_csv(R62 / "monthly_performance.csv").to_dict("records"),
                                                                    "Trades": pd.read_csv(R62 / "all_executed_trades.csv").to_dict("records"), "Legs": pd.read_csv(R62 / "all_trade_legs.csv").to_dict("records"), "Differences_A_B_C": diffs,
                                                                    "Ambiguities": pd.read_csv(R62 / "intrabar_ambiguities.csv").to_dict("records"), "ORB_V2_rejections": pd.read_csv(R62 / "orb_v2_rejections_config_c.csv").to_dict("records"), "Audit": [{"window_config": k, **v} for k, v in audit.items()]},
                   {"purpose": "Combined five-strategy backtest, configurations A/B/C/D1/D2, synthetic index P&L x 390 units", "no_selection": "No configuration is selected or ranked", "windows": "A = 2025-09..2026-08 (primary); B = 2022-09..2025-08 (robustness); 5paisa only"})
    (R62 / "README.md").write_text("\n".join([
        "# Phase 6.2 - combined five-strategy backtest", "", "**Written for:** the strategy owner. Research only; synthetic index P&L; nothing selected, optimised, committed or traded.", "", "Start with `combined_backtest_summary.md`, then `configuration_comparison.md`. New combined configuration id: `phase62-irfv2-orbv2-combined` (configuration C), "
        "kept separate from the frozen configurations; its ORB V2 component is the provisional ORB-V2-A (no owner selection exists; no relaxed variant was combined).", "", "Files: `configuration_manifest.json`, `all_signals.csv`, `all_executed_trades.csv`, `all_trade_legs.csv`, `strategy_performance.csv`, `monthly_performance.csv`, `annual_performance.csv`, `cost_sensitivity.csv`, `intrabar_ambiguities.csv`, "
        "`strategy_signal_funnel.csv` (standalone signal funnels), `trade_differences_between_configurations.csv`, `orb_v2_rejections_config_c.csv`, `orb_v2_integration_checks.csv`, `execution_audit_*`, `Combined_Five_Strategy_Backtest.xlsx`, `daily/` (one report per evaluable session of configuration C), `charts/` (one chart per executed C trade; "
        "the 2022-25 robustness window has ledgers and tables but no per-trade charts).", "", "Reproduce: `python scripts/phase62_run.py && python scripts/phase63_run.py && python scripts/phase62_daily_charts.py && python scripts/phase62_audit.py && python scripts/phase62_docs.py`."]))
    # ------------------------------------------------------------------ 6.1 documents
    sc61 = s61["signal_comparison"]
    (R61 / "irf_source_reconstruction.md").write_text("\n".join([
        "# IRF source reconstruction (Phase 6.1)", "", "Source: `IRF_Strategy_Guide Updated.pdf` (14 pages; text in `docs/extracted_text/`). The worked examples in the guide use illustrative prices (the guide says so: 'Prices are illustrative only'; the resistance-break example quotes levels 'taken from a NIFTY 50 five-minute session' without a date), so they cannot be tied to a historical session; the dated evidence is the author's handwritten correction pages (Phase 5.3 transcription; not re-read here).", "",
        "Fixed parameters: first 5-minute candle 09:15-09:20 = initial range (IRH/IRL, wicks included); short only; target 60; stop 35 or 40 by the distance to the most recent green candle (the repository's baseline uses 35). Closes confirm; wicks never do.", "",
        md_table([{"method": "Method 1", "sequence": "close above IRH; the very next candle closes back inside the range", "level": "none (no support/resistance break required)", "entry": "close of the failure candle"},
                  {"method": "Method 2A", "sequence": "close above IRH -> extension -> red candle -> a candle closes below recent support", "level": "'a low formed by recent candles during the extension, such as a pullback low'", "entry": "close below that support"},
                  {"method": "Method 2B", "sequence": "close above IRH -> first push tops out (resistance) -> price trades back above it -> red candle -> a red candle closes back below the resistance", "level": "a RESISTANCE (top of the first push)", "entry": "close of that red candle"},
                  {"method": "Method 3", "sequence": "small candles inside the range -> red sweep candle with ~60-70% of its upper wick above IRH -> closes below recent support (compulsory)", "level": "'recent support formed by the preceding candles'", "entry": "close of the sweep candle"}]), "",
        "Trend / EMA: the guide contains no EMA or trend condition. The 28-point EMA clearance is an owner clarification (number approved; measure provisional). Rejections: a red candle alone, a wick-only break, no close above IRH, an immediate close back inside (that is Method 1), insisting on a support break for Method 2.", "",
        "Execution / risk: unresolved in the guide (trades per day, time window, re-arming: IRF-GLOBAL-004) are handled by the shared controller (one trade, second trade only after a full stop and only PDR/PDS, 13:00 cutoff)."]))
    (R61 / "irf_support_break_rule.md").write_text("\n".join([
        "# IRF-V2-SUPPORT-BREAK: the approved rule and its state machine", "", "**Owner-approved:** identify the first qualifying red candle that establishes support; its lowest wick price is the support; SELL after a SUBSEQUENT completed candle closes strictly below it; no retest required; the signal exists at the breaking candle's close and the earliest fill is afterwards.", "",
        "States (`SupportBreakMachine`, one per Method 2 attempt): AWAIT_EXTENSION -> AWAIT_RED_CANDLE -> SUPPORT_SET -> SUPPORT_BROKEN. Recorded: the attempt's activation (breakout close above IRH), the extension candle, the search start, the reference candle (time and OHLC), its wick-low support, every later completed candle's close versus the support, "
        "the first valid close strictly below, the confirmation time and the earliest executable fill (the open of the next one-minute bar). Every Method 2 attempt - including those that never signal - is in `irf_reference_candle_audit.csv`.", "",
        "Enforced (and unit-tested): no entry on a red candle alone; none before support exists; none on a wick-only break (the close decides); the reference candle can never be its own breaking candle; the first reference candle is never replaced by a later one; no retest is awaited; support comes only from the reference candle's own OHLC (never a later candle).", "",
        "Layers kept separate: OWNER_APPROVED (first red candle low, strict close, no retest, the number 28); SOURCE (breakout above IRH, extension, red candle, Methods 1/2B/3 as written); PROVISIONAL (the search start = AFTER the extension candle - the alternative AFTER_BREAKOUT is selectable but not active; the 28-point measure = nearest point of the signal candle's range to the EMA(200), inclusive; scope = all methods); UNRESOLVED (the day's-low restriction).", "",
        "Regression example from the brief (a unit test, not a historical trade): reference red candle O25150 H25162 L25110 C25125 -> support 25110; the next candle closing 25118 does NOT trigger; the following candle closing 25102 confirms; SELL signal at that candle's completion.", "",
        "Relation to Phase 5.3: Phase 5.3 already contained this rule for Method 2A as `IRFPhase53Strategy(support_ref='FIRST_RED_LOW')`; IRF V2 re-implements Method 2A as an explicit state machine with full audit output and is verified by an independent re-derivation. "
        f"**On both windows IRF V2 emits exactly the same confirmed signals as the Phase 5.3 IRF** (primary {sc61['A']['v2']} vs {sc61['A']['p53']}; 2022-25 {sc61['B']['v2']} vs {sc61['B']['p53']}); the change relative to the frozen Phase 3.6 IRF is therefore the Phase 5.3 change."]))
    (R61 / "irf_method_scope.md").write_text("\n".join([
        "# IRF method scope", "", md_table([{"method": "Method 1", "uses the first-red-candle support break?": "No", "why": "source: the very next candle closing back inside the range is the trigger; 'no support or resistance break is required'", "V2 treatment": "frozen mechanism"},
                                          {"method": "Method 2A", "uses the first-red-candle support break?": "YES", "why": "source: support = a low formed during the extension; the owner approved the first red candle's wick low as that support", "V2 treatment": "explicit state machine"},
                                          {"method": "Method 2B", "uses the first-red-candle support break?": "No", "why": "its reference is a RESISTANCE (top of the first push); the red candle confirms the failure, it does not create a level; extending the rule needs owner approval", "V2 treatment": "frozen mechanism"},
                                          {"method": "Method 3", "uses the first-red-candle support break?": "No", "why": "its support is 'formed by the preceding candles' and the sweep candle itself must close below it; a separate compulsory break", "V2 treatment": "frozen mechanism"}]), "",
        f"28-point EMA clearance: applied to all four methods (provisional scope; the guide has no EMA text). Rejected candidates in the primary window: {sc61['ema_rejections']} (by method {sc61['ema_rejections_by_method']}). Dated handwritten cases outside the approved scope (Method 2B) are reported as out of scope, not reconciled (`irf_handwritten_cases.csv`)."]))
    a61 = s61["independent_audit"]
    (R61 / "independent_audit.md").write_text("\n".join([
        "# Independent audit (Phase 6.1)", "", "`src/nifty_trading/research/irf_v2_audit.py` re-derives every Method 2 attempt and every Method 2A signal (<= 13:00, with the 28-point gate) from RAW five-minute candles built by the Phase 6.0 independent chain (pandas resample, recursive EMA) - not from the engine's state machine, the repository's candles or its EMA.", "",
        md_table([{"window": w, **v} for w, v in a61.items()]), "", "Declared shared pieces: the Method 2B resistance helper (`definitions.recent_resistance`, only to know when an attempt ends) and the proposal defaults. The first run disagreed on one 2022-25 session (2024-02-26): the audit lacked the frozen rule that a data gap (missing candles) invalidates an open attempt; the engine was right and the audit was corrected.", "",
        f"IRF V2 equals the Phase 5.3 IRF on both windows (same keys). Handwritten IRF cases: {s61['handwritten']}.", "", "## Reviewer", "", (Path(R62 / "reviewer_findings.md").read_text() if (R62 / "reviewer_findings.md").exists() else "_(reviewer report pending)_")]))
    st = s61["ema_diag_A"]
    ch = s61["signal_comparison"]["changes_frozen_to_v2"]
    (R61 / "README.md").write_text("\n".join([
        "# Phase 6.1 - IRF-V2-SUPPORT-BREAK", "", "**Written for:** the strategy owner. Signal level only (no fills or P&L here). Primary window 2025-09-01..2026-08-31; the 2022-25 window is in the CSVs.", "",
        f"* Confirmed IRF signals (all times): frozen Phase 3.6 {sc61['A']['frozen']}, Phase 5.3 {sc61['A']['p53']}, IRF V2 {sc61['A']['v2']}; V2 == Phase 5.3 exactly (both windows).", f"* Frozen -> V2: unchanged {ch.get('UNCHANGED', 0)}, same time but different support level {ch.get('SUPPORT_LEVEL_CHANGED_SAME_TIME', 0)}, removed {ch.get('REMOVED', 0)}, added {ch.get('ADDED', 0)}. "
        f"Removed by cause: {s61['signal_comparison']['removed_causes']}; added: {s61['signal_comparison']['added_causes']}. Method 2A first-signal shifts per session: {s61['signal_comparison']['method2a_shifts']}.", f"* EMA-28: {st['rejected']} candidate confirmations rejected (primary); on the {st['confirmed']} confirmed signals the EMA lies between the entry reference and Target 1 on {st['ema_between_entry_and_t1']} (never, because the 28-point range clearance keeps it beyond 28 points while T1 is 27).",
        f"* Day's-low restriction: NOT applied; a causal running-low diagnostic is recorded on every signal ({st['close_below_prior_running_low']} signals close below the prior running low).", f"* Independent audit: {a61}.", "", "Files: `irf_source_reconstruction.md`, `irf_support_break_rule.md`, `irf_method_scope.md`, `irf_reference_candle_audit.csv` (every Method 2 attempt), `irf_before_after_signals.csv`, `irf_handwritten_cases.csv`, `irf_ema_28_diagnostics.csv`, "
        "`audit_mismatches.csv`, `independent_audit.md`, `IRF_V2_Verification.xlsx`, `charts/` (dates where Method 2A changed and handwritten dates)."]))
    # ------------------------------------------------------------------ 6.3 README / audit
    (R63 / "README.md").write_text("\n".join([
        "# Phase 6.3 - reconciliation with the original manual journal", "", "**Written for:** the strategy owner. Read `exact_match_summary.md` first. The journal records only date, entry-time label, strategy and outcome, so no verified exact trade match is possible; strict / time-tolerant / date-only / manual-only / automated-only are reported separately for A, B, C and per strategy "
        "(Phase 5.6 matcher and tolerances, unchanged; one-to-one).", "", "Files: `manual_journal_source_audit.md`, `exact_match_summary.md`, `match_summary_by_strategy.csv`, `match_summary_by_config.csv`, `manual_vs_automated_matching.csv`, `strict_matches.csv`, `time_tolerant_matches.csv`, `date_only_matches.csv`, `manual_only.csv`, `automated_only.csv`, "
        "`wrong_strategy_dates.csv`, `orb_vs_irf_comparison.csv`, `irf_support_break_reconciliation.csv`, `handwritten_corrections_comparison.csv`, `mismatch_root_causes.csv`, `Manual_vs_Automated_Verification.xlsx`, `daily/` (every journal date), `charts/` (manual_only, orb_vs_irf, handwritten, changed_days, trade_links)."]))
    (R63 / "independent_audit.md").write_text("\n".join([
        "# Independent audit (Phase 6.3)", "", "* The journal workbook was re-read from the original file (SHA-256 in `manual_journal_source_audit.md`); counts agree with the Phase 5.6 audit.", "* Matching is one-to-one by construction (each journal row and each trade used once); `tests/test_phase63_reconciliation.py` re-checks this on the real outputs and re-derives the strict count with a separate pandas implementation.", "* Tolerances are the Phase 5.6 ones (strict 0 minutes; time-tolerant 15 minutes) and were not changed.", "",
        "## Reviewer", "", (Path(R62 / "reviewer_findings.md").read_text() if (R62 / "reviewer_findings.md").exists() else "_(reviewer report pending)_")]))
    (R62 / "independent_audit.md").write_text("\n".join([
        "# Independent audit (Phase 6.2)", "", f"1. Execution audit: {audit_tot['verified']} / {audit_tot['trades']} trades verified from raw bars by a separate simulator (see `entry_exit_execution_audit.md`).", f"2. Regression gates: A and B reproduce Phase 5.5, A reproduces Phase 4 on 2022-25, D1 == B ({chk}).", "3. ORB V2 integration: the opening candle equals the controller's candle on every session; fills at 09:20.",
        "4. Pytest and ruff results are in the final report.", "", "## Reviewer", "", (Path(R62 / "reviewer_findings.md").read_text() if (R62 / "reviewer_findings.md").exists() else "_(reviewer report pending)_")]))
    print({"diff_dates": len(diffs), "kinds": dict(kinds)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
